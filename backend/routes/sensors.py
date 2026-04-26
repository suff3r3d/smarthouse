from fastapi import APIRouter, Depends, HTTPException, status

import database
from routes.deps import require_auth
from routes.feed_types import SENSOR_FEEDS, is_sensor_feed

router = APIRouter()


@router.get("/sensors", summary="List All Sensors")
async def list_sensors():
    """
    Get a list of environment sensors and their current values.
    """
    try:
        sensors = database.list_sensors_from_db()
        sensors = [sensor for sensor in sensors if (sensor.get("feed_key") or "") in SENSOR_FEEDS]
        return {"sensors": sensors, "count": len(sensors)}
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch sensors from database: {exc}",
        )


@router.get("/sensors/{sensor_id}/get_value", summary="Get Sensor Value")
async def get_sensor_value(sensor_id: str, auth: dict = Depends(require_auth)):
    """
    Get only the current value of a sensor feed.
    """
    if not is_sensor_feed(sensor_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"'{sensor_id}' is not a sensor feed",
        )

    value = database.get_sensor_value_by_feed_key(sensor_id)
    if value is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No stored value found for sensor '{sensor_id}'",
        )
    return value


@router.get("/sensors/latest", summary="Get Latest Sensor Data")
async def get_latest_sensor_data():
    """
    Get the latest data from all sensors (real-time dashboard).
    """
    pass


@router.get("/sensors/history", summary="Get Historical Sensor Data")
async def get_sensor_history():
    """
    Get historical sensor data with time-based filtering.
    """
    pass


@router.get("/sensors/export", summary="Export Historical Data")
async def export_sensor_data():
    """
    Export historical data to a file (e.g., CSV, Excel).
    """
    pass
