from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

import database
from routes.deps import require_auth
from routes.feed_types import SENSOR_FEEDS, is_sensor_feed
from utils import JWTHandler

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


class SensorAuthPayload(BaseModel):
    auth_token: str


class SensorHistoryPayload(BaseModel):
    auth_token: str
    feed_key: str
    start_time: datetime
    end_time: datetime


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


@router.post("/sensors/history", summary="Get Historical Sensor Data")
async def get_sensor_history(payload: SensorHistoryPayload):
    """
    Get historical sensor data with time-based filtering.
    """
    decoded = JWTHandler.decode(payload.auth_token)
    if not decoded:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid auth token",
        )

    if not is_sensor_feed(payload.feed_key):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"'{payload.feed_key}' is not a sensor feed",
        )

    if payload.start_time > payload.end_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_time must be less than or equal to end_time",
        )

    try:
        data = database.get_sensor_timeseries(
            feed_key=payload.feed_key,
            start_time=payload.start_time,
            end_time=payload.end_time,
        )
        return data
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch sensor history: {exc}",
        )


@router.get("/sensors/export", summary="Export Historical Data")
async def export_sensor_data():
    """
    Export historical data to a file (e.g., CSV, Excel).
    """
    pass
