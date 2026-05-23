from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

import database
from routes.deps import require_auth
from utils import AdafruitIO

router = APIRouter()

# Devices commanded when away mode is activated: feed_key → value
_AWAY_DEVICE_STATES: dict[str, str] = {
    "door": "LOCKED",
    "lb1": "0",
    "light-pwm": "0",
    "rgb": "0,0,0",
}


def _resolve_profile_id(auth: dict) -> int:
    user = auth["user"]
    profile_id = database.get_current_setting_profile_id_by_user_id(user.id)
    if profile_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current setting profile not found for user",
        )
    return profile_id


class AwayModePayload(BaseModel):
    enabled: bool


class AutomationModePayload(BaseModel):
    enabled: Optional[bool] = None
    door_auto_lock: Optional[bool] = None
    door_auto_lock_delay_sec: Optional[int] = None


@router.get("/modes/away", summary="Get Away Mode Status")
async def get_away_mode(auth: dict = Depends(require_auth)):
    profile_id = _resolve_profile_id(auth)
    data = database.get_mode_settings(profile_id)
    return {"away_mode": data["away_mode"]}


@router.put("/modes/away", summary="Set Away Mode")
async def set_away_mode(payload: AwayModePayload, auth: dict = Depends(require_auth)):
    """
    Enable or disable away mode.
    Enabling immediately locks the door and turns off all controllable lights.
    """
    user = auth["user"]
    if not user.is_house_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only house owner can change away mode",
        )
    profile_id = _resolve_profile_id(auth)
    database.update_away_mode(profile_id, payload.enabled)

    warnings: list[str] = []
    if payload.enabled:
        aio = AdafruitIO()
        for feed_key, value in _AWAY_DEVICE_STATES.items():
            try:
                await aio.publish_feed(feed_key, value)
            except Exception as exc:
                warnings.append(f"{feed_key}: {exc}")

    resp: dict = {"away_mode": payload.enabled, "message": "Away mode " + ("enabled" if payload.enabled else "disabled")}
    if warnings:
        resp["warnings"] = warnings
    return resp


@router.get("/modes/automation", summary="Get Automation Mode Settings")
async def get_automation_mode(auth: dict = Depends(require_auth)):
    profile_id = _resolve_profile_id(auth)
    data = database.get_mode_settings(profile_id)
    return {
        "automation_mode": data["automation_mode"],
        "door_auto_lock": data["door_auto_lock"],
        "door_auto_lock_delay_sec": data["door_auto_lock_delay_sec"],
    }


@router.put("/modes/automation", summary="Set Automation Mode")
async def set_automation_mode(payload: AutomationModePayload, auth: dict = Depends(require_auth)):
    """
    Toggle automation mode and configure door auto-lock.
    door_auto_lock_delay_sec: seconds after the door opens before it is auto-locked (min 10).
    """
    user = auth["user"]
    if not user.is_house_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only house owner can change automation mode",
        )
    if payload.door_auto_lock_delay_sec is not None and payload.door_auto_lock_delay_sec < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="door_auto_lock_delay_sec must be at least 10 seconds",
        )
    profile_id = _resolve_profile_id(auth)
    database.update_automation_mode(
        profile_id,
        enabled=payload.enabled,
        door_auto_lock=payload.door_auto_lock,
        door_auto_lock_delay_sec=payload.door_auto_lock_delay_sec,
    )
    return {"message": "Automation settings updated"}
