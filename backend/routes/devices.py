from datetime import datetime
from typing import Any, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

import database
from routes.deps import require_auth
from routes.feed_types import DEVICE_FEEDS, is_device_feed
from utils import AdafruitIO, JWTHandler

router = APIRouter()


class DeviceSetStatePayload(BaseModel):
    auth_token: str
    state: Any


class DeviceAuthPayload(BaseModel):
    auth_token: str


class DeviceUpdatePayload(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None


@router.get("/devices", summary="List All Devices")
async def list_devices():
    """
    Get a list of all controllable devices and their current states.
    """
    try:
        devices = database.list_devices_from_db()
        devices = [device for device in devices if (device.get("feed_key") or "") in DEVICE_FEEDS]
        return {"devices": devices, "count": len(devices)}
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch devices from database: {exc}",
        )


@router.post("/devices/{device_id}/set_state", summary="Set Device State")
async def set_device_state(device_id: str, payload: DeviceSetStatePayload):
    """
    Set a specific state for a device by publishing to its Adafruit feed.
    """
    decoded = JWTHandler.decode(payload.auth_token)
    if not decoded:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid auth token",
        )
    if not is_device_feed(device_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"'{device_id}' is not a controllable device feed",
        )

    try:
        aio = AdafruitIO()
        data = await aio.publish_feed(device_id, payload.state)
        return {
            "message": "Device state updated successfully",
            "device_id": device_id,
            "state": payload.state,
            "data": data,
        }
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to set device state on Adafruit IO: {exc}",
        )


@router.get("/devices/{device_id}/get_state", summary="Get Device State")
async def get_device_state(device_id: str, payload: DeviceAuthPayload):
    """
    Get only the current state value of a device feed.
    """
    decoded = JWTHandler.decode(payload.auth_token)
    if not decoded:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid auth token",
        )
    if not is_device_feed(device_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"'{device_id}' is not a controllable device feed",
        )

    try:
        value = database.get_device_value_by_feed_key(device_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get device value from database: {exc}",
        )

    if value is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No stored value found for device '{device_id}'",
        )
    return value


@router.patch("/devices/{device_id}", summary="Update Device Name/Location")
async def update_device(device_id: str, payload: DeviceUpdatePayload, auth: dict = Depends(require_auth)):
    """
    Update a device's display name and/or room location. Homeowner only.
    """
    user = auth["user"]
    if not user.is_house_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only house owner can edit devices",
        )

    if payload.name is None and payload.location is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide at least one field to update: name or location",
        )

    try:
        updated = database.update_device_info(device_id, name=payload.name, location=payload.location)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update device: {exc}",
        )

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device '{device_id}' not found",
        )
    return {"message": "Device updated successfully", "device": updated}


@router.get("/device-data", summary="Get Device Activity for Chart")
async def get_device_chart_data(
    feed_key: str,
    start_time: datetime,
    end_time: datetime,
    auth: dict = Depends(require_auth),
):
    """
    Get time-series activity data for a device feed within a period.
    Returns {feed_key, data: [{timestamp, value}], count} ordered by timestamp ascending.
    """
    if not is_device_feed(feed_key):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"'{feed_key}' is not a known device feed",
        )
    if start_time > end_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_time must be less than or equal to end_time",
        )
    try:
        data = database.get_sensor_timeseries(
            feed_key=feed_key,
            start_time=start_time,
            end_time=end_time,
        )
        return {"feed_key": feed_key, "data": data, "count": len(data)}
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch device activity: {exc}",
        )
