import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch


def load_sensors_route_module():
    module_path = Path(__file__).resolve().parents[1] / "routes" / "sensors.py"
    spec = importlib.util.spec_from_file_location("sensors_route_module", module_path)
    assert spec and spec.loader

    stub_utils = types.ModuleType("utils")

    class StubJWTHandler:
        @staticmethod
        def decode(_token):
            return None

    class StubAdafruitIO:
        async def get_feed_value(self, _feed_key):
            return None

        async def get_all_devices(self):
            return []

    stub_utils.JWTHandler = StubJWTHandler
    stub_utils.AdafruitIO = StubAdafruitIO

    stub_feed_types = types.ModuleType("routes.feed_types")
    stub_feed_types.SENSOR_FEEDS = {"temperature", "humidity", "rain", "gas", "themis"}
    stub_feed_types.is_sensor_feed = lambda feed_key: feed_key in stub_feed_types.SENSOR_FEEDS

    previous_utils = sys.modules.get("utils")
    previous_feed_types = sys.modules.get("routes.feed_types")
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


class SensorGetValueApiTests(unittest.IsolatedAsyncioTestCase):
    async def test_get_sensor_value_success(self):
        sensors_module = load_sensors_route_module()

        with patch.object(sensors_module.JWTHandler, "decode", return_value={"sub": "1"}), patch.object(
            sensors_module, "AdafruitIO"
        ) as mock_aio_cls:
            mock_aio = mock_aio_cls.return_value
            mock_aio.get_feed_value = AsyncMock(return_value="29.50")

            payload = sensors_module.SensorAuthPayload(auth_token="valid-token")
            response = await sensors_module.get_sensor_value("temperature", payload)

        self.assertEqual(response, "29.50")
        mock_aio.get_feed_value.assert_awaited_once_with("temperature")

    async def test_get_sensor_value_rejects_device_feed(self):
        sensors_module = load_sensors_route_module()
        payload = sensors_module.SensorAuthPayload(auth_token="valid-token")

        with patch.object(sensors_module.JWTHandler, "decode", return_value={"sub": "1"}):
            with self.assertRaises(sensors_module.HTTPException) as context:
                await sensors_module.get_sensor_value("door", payload)

        self.assertEqual(context.exception.status_code, 400)

    async def test_get_sensor_value_invalid_token_returns_401(self):
        sensors_module = load_sensors_route_module()
        payload = sensors_module.SensorAuthPayload(auth_token="bad-token")

        with patch.object(sensors_module.JWTHandler, "decode", return_value=None):
            with self.assertRaises(sensors_module.HTTPException) as context:
                await sensors_module.get_sensor_value("temperature", payload)

        self.assertEqual(context.exception.status_code, 401)
        self.assertEqual(context.exception.detail, "Invalid auth token")


if __name__ == "__main__":
    unittest.main()
