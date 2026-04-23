from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import database
from routes.deps import require_auth

router = APIRouter()


class SchedulePayloadBase(BaseModel):
    setting_profile_id: int
    device_id: int
    action: Literal["TURN_ON", "TURN_OFF", "SET_VALUE"]
    payload: Optional[Dict[str, Any]] = None
    trigger_time: datetime


class ScheduleCreate(SchedulePayloadBase):
    pass


class ScheduleUpdate(BaseModel):
    setting_profile_id: Optional[int] = None
    device_id: Optional[int] = None
    action: Optional[Literal["TURN_ON", "TURN_OFF", "SET_VALUE"]] = None
    payload: Optional[Dict[str, Any]] = None
    trigger_time: Optional[datetime] = None


class ScheduleOut(SchedulePayloadBase):
    id: int

    class Config:
        orm_mode = True


@router.get("/schedules", summary="List All Schedules", response_model=List[ScheduleOut])
async def list_schedules(
    auth: dict = Depends(require_auth),
    device_id: Optional[int] = None,
):
    """
    Get a list of all schedules.
    """
    profile_ids = auth["setting_profile_ids"]
    return database.list_schedules_by_profile_ids(profile_ids=profile_ids, device_id=device_id)


@router.post("/schedules", summary="Create a New Schedule", response_model=ScheduleOut)
async def create_schedule(payload: ScheduleCreate, auth: dict = Depends(require_auth)):
    """
    Create a new schedule for a device.
    """
    if not auth["user"].is_house_owner:
        raise HTTPException(status_code=403, detail="Only house owner can edit")

    profile_ids = auth["setting_profile_ids"]
    if payload.setting_profile_id not in profile_ids:
        raise HTTPException(status_code=403, detail="setting_profile_id does not belong to authenticated user")

    try:
        return database.create_schedule(
            setting_profile_id=payload.setting_profile_id,
            device_id=payload.device_id,
            action=payload.action,
            payload=payload.payload,
            trigger_time=payload.trigger_time,
        )
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
    return schedule


@router.put("/schedules/{schedule_id}", summary="Update a Schedule", response_model=ScheduleOut)
async def update_schedule(
    schedule_id: int,
    payload: ScheduleUpdate,
    auth: dict = Depends(require_auth),
):
    """
    Update a schedule.
    """
    if not auth["user"].is_house_owner:
        raise HTTPException(status_code=403, detail="Only house owner can edit")

    profile_ids = auth["setting_profile_ids"]
    existing_schedule = database.get_schedule_by_id(schedule_id)
    if not existing_schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    if existing_schedule.setting_profile_id not in profile_ids:
        raise HTTPException(status_code=403, detail="Schedule does not belong to authenticated user")
    if payload.setting_profile_id is not None and payload.setting_profile_id not in profile_ids:
        raise HTTPException(status_code=403, detail="setting_profile_id does not belong to authenticated user")

    schedule = database.update_schedule(
        schedule_id,
        setting_profile_id=payload.setting_profile_id,
        device_id=payload.device_id,
        action=payload.action,
        payload=payload.payload,
        trigger_time=payload.trigger_time,
    )
    return schedule
