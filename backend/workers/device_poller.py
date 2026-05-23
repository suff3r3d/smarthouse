import asyncio
import logging
import threading
from datetime import datetime, timezone
from typing import Any

import database
from utils import AdafruitIO

logger = logging.getLogger("device_poller")

# Maps Python weekday() (0=Monday) to the day abbreviation used in automation_rules.days_of_week
_WEEKDAY_MAP = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]

# Tracks the last minute string ("YYYY-MM-DD HH:MM") each rule was executed.
# Persists in memory for the lifetime of the worker thread.
_rule_last_executed: dict[int, str] = {}


def _to_float(value: Any) -> float | None:
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None


def _is_trueish(value: Any) -> bool:
    text = str(value).strip().lower()
    return text in {"1", "true", "on", "open", "detected", "motion"}


def _generate_alerts_from_feeds(feeds: list[dict[str, Any]]) -> None:
    feed_map = {str(feed.get("key")): feed for feed in feeds if feed.get("key")}
    thresholds = database.get_admin_alert_thresholds()
    gas_threshold = thresholds["gas_upper_threshold"]
    temp_upper_threshold = thresholds["temp_upper_threshold"]
    temp_lower_threshold = thresholds["temp_lower_threshold"]
    humidity_upper_threshold = thresholds["humidity_upper_threshold"]
    humidity_lower_threshold = thresholds["humidity_lower_threshold"]
    light_lower_threshold = thresholds["light_lower_threshold"]

    gas_value = _to_float((feed_map.get("gas") or {}).get("last_value"))
    if gas_value is not None and gas_value >= gas_threshold:
        database.create_alert(
            alert_type="GAS_LEAK",
            message=f"Gas concentration is high ({gas_value} compared to {gas_threshold}).",
            feed_key="gas",
        )

    temp_value = _to_float((feed_map.get("temperature") or {}).get("last_value"))
    if temp_value is not None and temp_value >= temp_upper_threshold:
        database.create_alert(
            alert_type="HIGH_TEMPERATURE",
            message=f"Temperature is too high ({temp_value}C compared to {temp_upper_threshold}).",
            feed_key="temperature",
        )

    if temp_value is not None and temp_value <= temp_lower_threshold:
        database.create_alert(
            alert_type="LOW_TEMPERATURE",
            message=f"Temperature is too low ({temp_value}C compared to {temp_lower_threshold}).",
            feed_key="temperature",
        )

    humidity_value = _to_float((feed_map.get("humidity") or {}).get("last_value"))
    if humidity_value is not None and humidity_value >= humidity_upper_threshold:
        database.create_alert(
            alert_type="WARNING",
            message=f"Humidity is too high ({humidity_value}% compared to {humidity_upper_threshold}%).",
            feed_key="humidity",
        )

    if humidity_value is not None and humidity_value <= humidity_lower_threshold:
        database.create_alert(
            alert_type="WARNING",
            message=f"Humidity is too low ({humidity_value}% compared to {humidity_lower_threshold}%).",
            feed_key="humidity",
        )

    light_value = _to_float((feed_map.get("themis") or {}).get("last_value"))
    if light_value is not None and light_value <= light_lower_threshold:
        database.create_alert(
            alert_type="LOW_LIGHT",
            message=f"Light intensity is too low ({light_value} compared to {light_lower_threshold}).",
            feed_key="themis",
        )

    pir_value = (feed_map.get("pir") or {}).get("last_value")
    if _is_trueish(pir_value):
        database.create_alert(
            alert_type="MOTION_DETECTED",
            message=f"Motion detected by PIR sensor (value={pir_value}).",
            feed_key="pir",
        )

    door_value = (feed_map.get("door") or {}).get("last_value")
    if _is_trueish(door_value):
        database.create_alert(
            alert_type="DOOR_FORCED_OPEN",
            message=f"Door is open (value={door_value}).",
            feed_key="door",
        )


def _run_door_auto_lock(settings: dict[str, Any], aio: AdafruitIO) -> None:
    """Lock the door if it has been OPEN longer than the configured delay."""
    delay_sec = settings.get("door_auto_lock_delay_sec") or 120
    door = database.get_device_info_by_feed_key("door")
    if not door:
        return
    if str(door.get("value") or "").upper() != "OPEN":
        return
    last_record_time = door.get("last_record_time")
    if not last_record_time:
        return

    now_utc = datetime.now(timezone.utc)
    if last_record_time.tzinfo is None:
        last_record_time = last_record_time.replace(tzinfo=timezone.utc)
    elapsed = (now_utc - last_record_time).total_seconds()

    if elapsed >= delay_sec:
        try:
            asyncio.run(aio.publish_feed("door", "LOCKED"))
            print(f"[automation] Door auto-locked after {elapsed:.0f}s", flush=True)
        except Exception as exc:
            logger.warning("Door auto-lock failed: %s", exc)


def _run_automation_rules(aio: AdafruitIO) -> None:
    """Execute any automation rules whose time+day match the current moment."""
    now = datetime.now()
    current_minute = now.strftime("%Y-%m-%d %H:%M")
    current_day = _WEEKDAY_MAP[now.weekday()]   # "MON" … "SUN"
    current_time = now.strftime("%H:%M")         # "HH:MM"

    print(current_time, flush=True)

    rules = database.list_all_active_automation_rules()
    for rule in rules:
        if current_day not in rule.get("days_of_week", []):
            continue
        if rule.get("time_of_day", "")[:5] != current_time:
            continue
        rule_id = rule["id"]
        if _rule_last_executed.get(rule_id) == current_minute:
            continue  # already fired this minute
        try:
            print(f'{rule['feed_key']}, {rule['value']}', flush=True)
            asyncio.run(aio.publish_feed(rule["feed_key"], rule["value"]))
            _rule_last_executed[rule_id] = current_minute
            print(
                f"[automation] Rule {rule_id} fired: {rule['feed_key']} = {rule['value']}",
                flush=True,
            )
        except Exception as exc:
            logger.warning("Automation rule %s failed: %s", rule_id, exc)


def device_polling_worker(stop_event: threading.Event) -> None:
    print("[device-poller] started", flush=True)
    while not stop_event.is_set():
        try:
            aio = AdafruitIO()
            devices = asyncio.run(aio.get_all_devices())
            database.sync_feed_latest_values(devices)
            _generate_alerts_from_feeds(devices)
            for device in devices:
                device_name = device.get("name") or device.get("key") or "unknown"
                # print(f"{device_name}: {device.get('last_data')}", flush=True)

            # Automation: run only when automation_mode is on and away_mode is off.
            # (away_mode takes precedence — devices are already in locked/off state.)
            settings = database.get_active_automation_settings()
            print(settings, flush=True)
            if settings and not settings.get("away_mode"):
                if settings.get("door_auto_lock"):
                    _run_door_auto_lock(settings, aio)
                print(f'[device_polling_worker] start handling schedules', flush=True)
                _run_automation_rules(aio)

        except Exception as exc:
            logger.exception("Device polling error: %s", exc)
        stop_event.wait(5)
    print("[device-poller] stopped", flush=True)
