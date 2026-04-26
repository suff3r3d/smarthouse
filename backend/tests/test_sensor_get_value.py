import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


def load_sensors_route_module():
    module_path = Path(__file__).resolve().parents[1] / "routes" / "sensors.py"
    spec = importlib.util.spec_from_file_location("sensors_route_module", module_path)
    assert spec and spec.loader

    stub_database = types.ModuleType("database")
    stub_database.get_sensor_value_by_feed_key = lambda _feed_key: None
    stub_database.list_sensors_from_db = lambda: []

    stub_feed_types = types.ModuleType("routes.feed_types")
    stub_feed_types.SENSOR_FEEDS = {"temperature", "humidity", "rain", "gas", "themis"}
    stub_feed_types.is_sensor_feed = lambda feed_key: feed_key in stub_feed_types.SENSOR_FEEDS

    stub_deps = types.ModuleType("routes.deps")
    stub_deps.require_auth = lambda _request=None: {"user": {"id": 1}, "setting_profile_ids": []}

    previous_database = sys.modules.get("database")
    previous_feed_types = sys.modules.get("routes.feed_types")
    previous_deps = sys.modules.get("routes.deps")
    sys.modules["database"] = stub_database
    sys.modules["routes.feed_types"] = stub_feed_types
    sys.modules["routes.deps"] = stub_deps
    try:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        if previous_database is not None:
            sys.modules["database"] = previous_database
        else:
            del sys.modules["database"]
        if previous_feed_types is not None:
            sys.modules["routes.feed_types"] = previous_feed_types
        else:
            del sys.modules["routes.feed_types"]
        if previous_deps is not None:
            sys.modules["routes.deps"] = previous_deps
        else:
            del sys.modules["routes.deps"]


class SensorGetValueApiTests(unittest.IsolatedAsyncioTestCase):
    async def test_get_sensor_value_success(self):
        sensors_module = load_sensors_route_module()

        with patch.object(
            sensors_module.database, "get_sensor_value_by_feed_key", return_value="29.50"
        ) as mock_get_value:
            response = await sensors_module.get_sensor_value(
                "temperature", auth={"user": {"id": 1}, "setting_profile_ids": []}
            )

        self.assertEqual(response, "29.50")
        mock_get_value.assert_called_once_with("temperature")

    async def test_get_sensor_value_rejects_device_feed(self):
        sensors_module = load_sensors_route_module()
        with self.assertRaises(sensors_module.HTTPException) as context:
            await sensors_module.get_sensor_value("door", auth={"user": {"id": 1}, "setting_profile_ids": []})

        self.assertEqual(context.exception.status_code, 400)

    async def test_get_sensor_value_not_found_returns_404(self):
        sensors_module = load_sensors_route_module()
        with patch.object(
            sensors_module.database, "get_sensor_value_by_feed_key", return_value=None
        ):
            with self.assertRaises(sensors_module.HTTPException) as context:
                await sensors_module.get_sensor_value(
                    "temperature", auth={"user": {"id": 1}, "setting_profile_ids": []}
                )

        self.assertEqual(context.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
