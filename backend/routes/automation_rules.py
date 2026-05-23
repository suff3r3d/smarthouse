from typing import List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator

import database
from routes.deps import require_auth

router = APIRouter()

_VALID_DAYS = {"MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"}


def _parse_days(value: Union[str, List[str]]) -> List[str]:
    """Accept either a JSON array or a comma-separated string, return uppercase list."""
    if isinstance(value, str):
        return [d.strip().upper() for d in value.split(",") if d.strip()]
    return [d.strip().upper() for d in value if d.strip()]


class AutomationRuleCreate(BaseModel):
    feed_key: str
    value: str
    time_of_day: str
    days_of_week: Union[str, List[str]]
    enabled: bool = True

    @field_validator("days_of_week", mode="before")
    @classmethod
    def parse_days(cls, v):
        return _parse_days(v)


class AutomationRuleUpdate(BaseModel):
    value: Optional[str] = None
    time_of_day: Optional[str] = None
    days_of_week: Optional[Union[str, List[str]]] = None
    enabled: Optional[bool] = None

    @field_validator("days_of_week", mode="before")
    @classmethod
    def parse_days(cls, v):
        if v is None:
            return v
        return _parse_days(v)


def _validate_time(t: str) -> None:
    try:
        parts = t.split(":")
        assert len(parts) == 2
        h, m = int(parts[0]), int(parts[1])
        assert 0 <= h <= 23 and 0 <= m <= 59
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="time_of_day must be HH:MM (e.g. '08:30')",
        )


def _validate_days(days: List[str]) -> None:
    if not days:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="days_of_week must not be empty",
        )
    invalid = [d for d in days if d not in _VALID_DAYS]
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid day(s): {invalid}. Allowed: MON TUE WED THU FRI SAT SUN",
        )


def _resolve_profile_id(auth: dict) -> int:
    user = auth["user"]
    profile_id = database.get_current_setting_profile_id_by_user_id(user.id)
    if profile_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current setting profile not found",
        )
    return profile_id


def _resolve_device_id(feed_key: str) -> int:
    device_id = database.get_device_id_by_feed_key(feed_key)
    if device_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device with feed_key '{feed_key}' not found",
        )
    return device_id


@router.get("/automation/rules", summary="List Automation Rules")
async def list_automation_rules(auth: dict = Depends(require_auth)):
    """
    List all automation rules for the authenticated user's current setting profile.
    """
    profile_id = _resolve_profile_id(auth)
    rules = database.list_automation_rules(profile_id)
    return {"rules": rules, "count": len(rules)}


@router.post("/automation/rules", summary="Create Automation Rule")
async def create_automation_rule(payload: AutomationRuleCreate, auth: dict = Depends(require_auth)):
    """
    Create a recurring automation rule.

    - **feed_key**: device feed key (e.g. "lb1", "door", "rgb", "light-pwm")
    - **value**: value to publish — door: OPEN|CLOSE|LOCKED; lb1: 0-100; light-pwm: 0-100; rgb: R,G,B
    - **time_of_day**: "HH:MM" in server local time
    - **days_of_week**: JSON array ["MON","WED"] or comma-separated string "Mon,Wed,Fri"
    """
    user = auth["user"]
    if not user.is_house_owner:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only house owner can create rules")

    _validate_time(payload.time_of_day)
    _validate_days(payload.days_of_week)

    profile_id = _resolve_profile_id(auth)
    device_id = _resolve_device_id(payload.feed_key)

    try:
        rule = database.create_automation_rule(
            setting_profile_id=profile_id,
            device_id=device_id,
            value=payload.value,
            time_of_day=payload.time_of_day,
            days_of_week=",".join(payload.days_of_week),
            enabled=payload.enabled,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create rule: {exc}",
        )
    return rule


@router.put("/automation/rules/{rule_id}", summary="Update Automation Rule")
async def update_automation_rule(rule_id: int, payload: AutomationRuleUpdate, auth: dict = Depends(require_auth)):
    user = auth["user"]
    if not user.is_house_owner:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only house owner can edit rules")

    if payload.time_of_day is not None:
        _validate_time(payload.time_of_day)
    if payload.days_of_week is not None:
        _validate_days(payload.days_of_week)

    profile_id = _resolve_profile_id(auth)
    rule = database.get_automation_rule_by_id(rule_id)
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    if str(rule["setting_profile_id"]) != str(profile_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Rule does not belong to your profile")

    days_str = ",".join(payload.days_of_week) if payload.days_of_week is not None else None
    updated = database.update_automation_rule(
        rule_id,
        value=payload.value,
        time_of_day=payload.time_of_day,
        days_of_week=days_str,
        enabled=payload.enabled,
    )
    return updated


@router.delete("/automation/rules/{rule_id}", summary="Delete Automation Rule")
async def delete_automation_rule(rule_id: int, auth: dict = Depends(require_auth)):
    user = auth["user"]
    if not user.is_house_owner:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only house owner can delete rules")

    profile_id = _resolve_profile_id(auth)
    rule = database.get_automation_rule_by_id(rule_id)
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")
    if str(rule["setting_profile_id"]) != str(profile_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Rule does not belong to your profile")

    database.delete_automation_rule(rule_id)
    return {"message": "Rule deleted"}
