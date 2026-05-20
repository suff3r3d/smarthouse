import asyncio
import logging
import threading
from datetime import datetime, timezone

import database
from utils import AdafruitIO

logger = logging.getLogger("scheduler")


async def _run_due_schedules() -> None:
    now = datetime.now(timezone.utc)
    due_schedules = database.list_due_schedules(now)
    if not due_schedules:
        return

    aio = AdafruitIO()
    for schedule in due_schedules:
        schedule_id = schedule["id"]
        feed_key = schedule.get("feed_key")
        setting_profile_id = schedule.get("setting_profile_id")
        away_mode = bool(schedule.get("away_mode"))

        if away_mode:
            logger.info(
                "Skipping schedule id=%s because setting_profile_id=%s has away_mode=true",
                schedule_id,
                setting_profile_id,
            )
            continue

        if not feed_key:
            logger.warning("Skipping schedule id=%s because device feed_key is missing", schedule_id)
            continue

        try:
            await aio.publish_feed(feed_key, schedule.get("value"))
            database.delete_schedule(schedule_id)
            logger.info("Executed schedule id=%s feed_key=%s", schedule_id, feed_key)
        except Exception as exc:
            logger.exception("Failed to execute schedule id=%s: %s", schedule_id, exc)


def scheduler_worker(stop_event: threading.Event) -> None:
    print("[scheduler] started", flush=True)
    print(f"[scheduler] now: {datetime.now(timezone.utc)}")
    while not stop_event.is_set():
        try:
            asyncio.run(_run_due_schedules())
        except Exception as exc:
            logger.exception("Scheduler error: %s", exc)
        stop_event.wait(1)
    print("[scheduler] stopped", flush=True)

