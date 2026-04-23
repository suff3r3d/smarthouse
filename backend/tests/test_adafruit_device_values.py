import importlib.util
import json
import os
import re
import unittest
from pathlib import Path
from unittest.mock import patch


def load_adafruit_module():
    module_path = Path(__file__).resolve().parents[1] / "utils" / "adafruit.py"
    spec = importlib.util.spec_from_file_location("adafruit_live_module", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_aio_credentials():
    username = os.getenv("AIO_USERNAME")
    key = os.getenv("AIO_KEY")
    if username and key:
        return username, key

    config_path = (
        Path(__file__).resolve().parents[2]
        / "Smart_Home_DADN_HK252"
        / "src"
        / "services"
        / "adafruitIO.js"
    )
    text = config_path.read_text(encoding="utf-8")
    username_match = re.search(r"USERNAME:\s*'([^']+)'", text)
    key_match = re.search(r"KEY:\s*'([^']+)'", text)
    if not username_match or not key_match:
        raise RuntimeError("Could not load Adafruit IO credentials from environment or frontend config")
    return username_match.group(1), key_match.group(1)


class AdafruitIODeviceValueInspectionTests(unittest.IsolatedAsyncioTestCase):
    async def test_print_device_last_values(self):
        adafruit = load_adafruit_module()
        username, key = load_aio_credentials()

        with patch.dict(os.environ, {"AIO_USERNAME": username, "AIO_KEY": key}, clear=False):
            aio = adafruit.AdafruitIO()
            devices = await aio.get_all_devices()

        self.assertIsInstance(devices, list)
        self.assertGreater(len(devices), 0)

        simplified_devices = []
        for device in sorted(devices, key=lambda item: item.get("key") or ""):
            last_data = device.get("last_data") or {}
            simplified_devices.append(
                {
                    "key": device.get("key"),
                    "name": device.get("name"),
                    "last_value": device.get("last_value"),
                    "last_recorded_at": last_data.get("created_at"),
                }
            )

        print(f"Fetched {len(simplified_devices)} devices from Adafruit IO")
        print(json.dumps(simplified_devices, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()
