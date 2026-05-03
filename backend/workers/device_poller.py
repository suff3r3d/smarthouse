import asyncio
import logging
import threading
from typing import Any

import database
from utils import AdafruitIO

logger = logging.getLogger("device_poller")


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


def device_polling_worker(stop_event: threading.Event) -> None:
    print("[device-poller] started", flush=True)
    while not stop_event.is_set():
        try:
            devices = asyncio.run(AdafruitIO().get_all_devices())
            database.sync_feed_latest_values(devices)
            _generate_alerts_from_feeds(devices)
            for device in devices:
                device_name = device.get("name") or device.get("key") or "unknown"
                print(f"{device_name}: {device.get('last_data')}", flush=True)
        except Exception as exc:
            logger.exception("Device polling error: %s", exc)
        stop_event.wait(60)
    print("[device-poller] stopped", flush=True)
