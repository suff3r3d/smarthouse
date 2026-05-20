from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import database
from routes.deps import require_auth
from utils.jwt import JWTHandler

router = APIRouter()


class SchedulePayloadBase(BaseModel):
    feed_key: str
    value: str
    trigger_time: datetime


class ScheduleCreate(SchedulePayloadBase):
    auth_token: str


class ScheduleUpdate(BaseModel):
    auth_token: str
    feed_key: Optional[str] = None
    value: Optional[str] = None
    trigger_time: Optional[datetime] = None


class ScheduleOut(SchedulePayloadBase):
    setting_profile_id: int
    id: int

    class Config:
        orm_mode = True


@router.get("/schedules", summary="List All Schedules", response_model=List[ScheduleOut])
async def list_schedules(
    auth: dict = Depends(require_auth),
    feed_key: Optional[str] = None,
):
    """
    Get a list of all schedules.
    """
    profile_ids = auth["setting_profile_ids"]
    device_id: Optional[int] = None
    if feed_key is not None:
        device_id = database.get_device_id_by_feed_key(feed_key)
        if device_id is None:
            return []

    schedules = database.list_schedules_by_profile_ids(profile_ids=profile_ids, device_id=device_id)
    result = []
    for schedule in schedules:
        schedule_feed_key = database.get_device_feed_key_by_id(schedule.device_id)
        result.append(
            {
                "id": schedule.id,
                "setting_profile_id": schedule.setting_profile_id,
                "feed_key": schedule_feed_key,
                "value": schedule.value,
                "trigger_time": schedule.trigger_time,
            }
        )
    return result


@router.post("/schedules", summary="Create a New Schedule", response_model=ScheduleOut)
async def create_schedule(payload: ScheduleCreate):
    """
    Create a new schedule for a device.
    """
    decoded = JWTHandler.decode(payload.auth_token)
    if not decoded:
        raise HTTPException(status_code=401, detail="Invalid auth token")
    user_id = int(decoded.get("sub", 0))
    user = database.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid auth token")

    if not user.is_house_owner:
        raise HTTPException(status_code=403, detail="Only house owner can edit")

    current_profile_id = database.get_current_setting_profile_id_by_user_id(user.id)
    if current_profile_id is None:
        raise HTTPException(status_code=400, detail="Current setting profile not found for user")

    try:
        device_id = database.get_device_id_by_feed_key(payload.feed_key)
        if device_id is None:
            raise HTTPException(status_code=400, detail=f"Invalid feed_key: {payload.feed_key}")

        schedule = database.create_schedule(
            setting_profile_id=current_profile_id,
            device_id=device_id,
            value=payload.value,
            trigger_time=payload.trigger_time,
        )
        return {
            "id": schedule.id,
            "setting_profile_id": schedule.setting_profile_id,
            "feed_key": database.get_device_feed_key_by_id(schedule.device_id),
            "value": schedule.value,
            "trigger_time": schedule.trigger_time,
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid schedule payload: {exc}")


@router.get("/schedules/{schedule_id}", summary="Get Specific Schedule", response_model=ScheduleOut)
async def get_schedule(schedule_id: int, auth: dict = Depends(require_auth)):
    """
    Get details of a specific schedule.
    """
    profile_ids = auth["setting_profile_ids"]
    schedule = database.get_schedule_by_id(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    if schedule.setting_profile_id not in profile_ids:
        raise HTTPException(status_code=403, detail="Schedule does not belong to authenticated user")
    return {
        "id": schedule.id,
        "setting_profile_id": schedule.setting_profile_id,
        "feed_key": database.get_device_feed_key_by_id(schedule.device_id),
        "value": schedule.value,
        "trigger_time": schedule.trigger_time,
    }


@router.put("/schedules/{schedule_id}", summary="Update a Schedule", response_model=ScheduleOut)
async def update_schedule(
    schedule_id: int,
    payload: ScheduleUpdate,
):
    """
    Update a schedule.
    """
    decoded = JWTHandler.decode(payload.auth_token)
    if not decoded:
        raise HTTPException(status_code=401, detail="Invalid auth token")
    user_id = int(decoded.get("sub", 0))
    user = database.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid auth token")

    if not user.is_house_owner:
        raise HTTPException(status_code=403, detail="Only house owner can edit")

    profile_ids = database.get_setting_profile_ids_by_user_id(user.id)
    existing_schedule = database.get_schedule_by_id(schedule_id)
    if not existing_schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    if existing_schedule.setting_profile_id not in profile_ids:
        raise HTTPException(status_code=403, detail="Schedule does not belong to authenticated user")

    device_id: Optional[int] = None
    if payload.feed_key is not None:
        device_id = database.get_device_id_by_feed_key(payload.feed_key)
        if device_id is None:
            raise HTTPException(status_code=400, detail=f"Invalid feed_key: {payload.feed_key}")

    schedule = database.update_schedule(
        schedule_id,
        device_id=device_id,
        value=payload.value,
        trigger_time=payload.trigger_time,
    )
    return {
        "id": schedule.id,
        "setting_profile_id": schedule.setting_profile_id,
        "feed_key": database.get_device_feed_key_by_id(schedule.device_id),
        "value": schedule.value,
        "trigger_time": schedule.trigger_time,
    }
