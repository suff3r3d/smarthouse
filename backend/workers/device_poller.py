import asyncio
import logging
import threading

import database
from utils import AdafruitIO

logger = logging.getLogger("device_poller")


def device_polling_worker(stop_event: threading.Event) -> None:
    print("[device-poller] started", flush=True)
    while not stop_event.is_set():
        try:
            devices = asyncio.run(AdafruitIO().get_all_devices())
            database.sync_feed_latest_values(devices)
            for device in devices:
                device_name = device.get("name") or device.get("key") or "unknown"
                print(f"{device_name}: {device.get('last_data')}", flush=True)
        except Exception as exc:
            logger.exception("Device polling error: %s", exc)
        stop_event.wait(60)
    print("[device-poller] stopped", flush=True)

