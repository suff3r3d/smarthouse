import httpx
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from routes.feed_types import SENSOR_FEEDS, is_sensor_feed
from utils import AdafruitIO, JWTHandler

router = APIRouter()


class SensorAuthPayload(BaseModel):
    auth_token: str


@router.get("/sensors", summary="List All Sensors")
async def list_sensors():
    """
    Get a list of environment sensors and their current values.
    """
    try:
        aio = AdafruitIO()
        all_feeds = await aio.get_all_devices()
        sensors = [feed for feed in all_feeds if (feed.get("key") or "") in SENSOR_FEEDS]
        return {"sensors": sensors, "count": len(sensors)}
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch sensors from Adafruit IO: {exc}",
        )


@router.post("/sensors/{sensor_id}/get_value", summary="Get Sensor Value")
async def get_sensor_value(sensor_id: str, payload: SensorAuthPayload):
    """
    Get only the current value of a sensor feed.
    """
    decoded = JWTHandler.decode(payload.auth_token)
    if not decoded:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid auth token",
        )
    if not is_sensor_feed(sensor_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"'{sensor_id}' is not a sensor feed",
        )

    try:
        aio = AdafruitIO()
        return await aio.get_feed_value(sensor_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to get sensor value from Adafruit IO: {exc}",
        )


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
