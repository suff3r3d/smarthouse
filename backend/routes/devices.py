from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from routes.feed_types import DEVICE_FEEDS, is_device_feed
from utils import AdafruitIO, JWTHandler

router = APIRouter()


class DeviceSetStatePayload(BaseModel):
    auth_token: str
    state: Any


class DeviceAuthPayload(BaseModel):
    auth_token: str


@router.get("/devices", summary="List All Devices")
async def list_devices():
    """
    Get a list of all controllable devices and their current states.
    """
    try:
        aio = AdafruitIO()
        all_feeds = await aio.get_all_devices()
        devices = [feed for feed in all_feeds if (feed.get("key") or "") in DEVICE_FEEDS]
        return {"devices": devices, "count": len(devices)}
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch devices from Adafruit IO: {exc}",
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


@router.post("/devices/{device_id}/get_state", summary="Get Device State")
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
        aio = AdafruitIO()
        return await aio.get_feed_value(device_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to get device value from Adafruit IO: {exc}",
        )
