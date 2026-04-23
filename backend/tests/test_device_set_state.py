import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch


def load_devices_route_module():
    module_path = Path(__file__).resolve().parents[1] / "routes" / "devices.py"
    spec = importlib.util.spec_from_file_location("devices_route_module", module_path)
    assert spec and spec.loader

    # Provide a lightweight stub for `utils` so this test does not depend
    # on full backend runtime dependencies.
    stub_utils = types.ModuleType("utils")

    class StubJWTHandler:
        @staticmethod
        def decode(_token):
            return None

    class StubAdafruitIO:
        async def publish_feed(self, _feed_key, _value):
            return {}

    stub_utils.JWTHandler = StubJWTHandler
    stub_utils.AdafruitIO = StubAdafruitIO

    previous_utils = sys.modules.get("utils")
    previous_feed_types = sys.modules.get("routes.feed_types")
    stub_feed_types = types.ModuleType("routes.feed_types")
    stub_feed_types.DEVICE_FEEDS = {"door", "lb1", "pir", "rgb", "light-pwm"}
    stub_feed_types.is_device_feed = lambda feed_key: feed_key in stub_feed_types.DEVICE_FEEDS

    sys.modules["utils"] = stub_utils
    sys.modules["routes.feed_types"] = stub_feed_types
    try:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        if previous_utils is not None:
            sys.modules["utils"] = previous_utils
        else:
            del sys.modules["utils"]
        if previous_feed_types is not None:
            sys.modules["routes.feed_types"] = previous_feed_types
        else:
            del sys.modules["routes.feed_types"]


class DeviceSetStateApiTests(unittest.IsolatedAsyncioTestCase):
    async def test_set_state_success(self):
        devices_module = load_devices_route_module()

        with patch.object(devices_module.JWTHandler, "decode", return_value={"sub": "1"}), patch.object(
            devices_module, "AdafruitIO"
        ) as mock_aio_cls:
            mock_aio = mock_aio_cls.return_value
            mock_aio.publish_feed = AsyncMock(return_value={"id": "123", "value": "29.50"})

            payload = devices_module.DeviceSetStatePayload(auth_token="valid-token", state="29.50")
            response = await devices_module.set_device_state("door", payload)

        self.assertEqual(response["message"], "Device state updated successfully")
        self.assertEqual(response["device_id"], "door")
        self.assertEqual(response["state"], "29.50")
        self.assertEqual(response["data"], {"id": "123", "value": "29.50"})
        mock_aio.publish_feed.assert_awaited_once_with("door", "29.50")

    async def test_set_state_invalid_token_returns_401(self):
        devices_module = load_devices_route_module()
        payload = devices_module.DeviceSetStatePayload(auth_token="bad-token", state="OFF")

        with patch.object(devices_module.JWTHandler, "decode", return_value=None):
            with self.assertRaises(devices_module.HTTPException) as context:
                await devices_module.set_device_state("door", payload)

        self.assertEqual(context.exception.status_code, 401)
        self.assertEqual(context.exception.detail, "Invalid auth token")

    async def test_get_state_success(self):
        devices_module = load_devices_route_module()

        with patch.object(devices_module.JWTHandler, "decode", return_value={"sub": "1"}), patch.object(
            devices_module, "AdafruitIO"
        ) as mock_aio_cls:
            mock_aio = mock_aio_cls.return_value
            mock_aio.get_feed_value = AsyncMock(return_value="28.00")

            payload = devices_module.DeviceAuthPayload(auth_token="valid-token")
            response = await devices_module.get_device_state("door", payload)

        self.assertEqual(response, "28.00")
        mock_aio.get_feed_value.assert_awaited_once_with("door")

    async def test_get_state_invalid_token_returns_401(self):
        devices_module = load_devices_route_module()
        payload = devices_module.DeviceAuthPayload(auth_token="bad-token")

        with patch.object(devices_module.JWTHandler, "decode", return_value=None):
            with self.assertRaises(devices_module.HTTPException) as context:
                await devices_module.get_device_state("door", payload)

        self.assertEqual(context.exception.status_code, 401)
        self.assertEqual(context.exception.detail, "Invalid auth token")

    async def test_set_state_rejects_sensor_feed(self):
        devices_module = load_devices_route_module()
        payload = devices_module.DeviceSetStatePayload(auth_token="valid-token", state="29.50")

        with patch.object(devices_module.JWTHandler, "decode", return_value={"sub": "1"}):
            with self.assertRaises(devices_module.HTTPException) as context:
                await devices_module.set_device_state("temperature", payload)

        self.assertEqual(context.exception.status_code, 400)

    async def test_get_state_rejects_sensor_feed(self):
        devices_module = load_devices_route_module()
        payload = devices_module.DeviceAuthPayload(auth_token="valid-token")

        with patch.object(devices_module.JWTHandler, "decode", return_value={"sub": "1"}):
            with self.assertRaises(devices_module.HTTPException) as context:
                await devices_module.get_device_state("temperature", payload)

        self.assertEqual(context.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
