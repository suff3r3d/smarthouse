from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, root_validator

import database
from utils import JWTHandler

router = APIRouter()


class ThresholdsGetPayload(BaseModel):
    auth_token: str

    @root_validator(pre=True)
    def validate_supported_fields(cls, values):
        allowed_fields = {"auth_token"}
        for key in values.keys():
            if key not in allowed_fields:
                raise ValueError(f"{key} không tồn tại")
        return values


class ThresholdsUpdatePayload(BaseModel):
    auth_token: str
    temp_lower_threshold: Optional[float] = None
    temp_upper_threshold: Optional[float] = None
    humidity_lower_threshold: Optional[float] = None
    humidity_upper_threshold: Optional[float] = None
    gas_upper_threshold: Optional[float] = None
    light_lower_threshold: Optional[float] = None

    @root_validator(pre=True)
    def validate_supported_fields(cls, values):
        allowed_fields = {
            "auth_token",
            "temp_lower_threshold",
            "temp_upper_threshold",
            "humidity_lower_threshold",
            "humidity_upper_threshold",
            "gas_upper_threshold",
            "light_lower_threshold",
        }
        for key in values.keys():
            if key not in allowed_fields:
                raise ValueError(f"{key} không tồn tại")
        return values


def _resolve_current_setting_profile_id(auth_token: str) -> int:
    decoded = JWTHandler.decode(auth_token)
    if not decoded:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid auth token",
        )

    sub = decoded.get("sub")
    try:
        user_id = int(sub)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid auth token",
        )

    user = database.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid auth token",
        )

    setting_profile_id = database.get_current_setting_profile_id_by_user_id(user.id)
    if setting_profile_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current setting profile not found for user",
        )
    return setting_profile_id


@router.post("/setting-profiles/current/thresholds", summary="Get Current Setting Profile Thresholds")
async def get_current_thresholds(payload: ThresholdsGetPayload):
    setting_profile_id = _resolve_current_setting_profile_id(payload.auth_token)
    data = database.get_setting_profile_thresholds(setting_profile_id)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Setting profile not found",
        )
    return data


@router.put("/setting-profiles/current/thresholds", summary="Update Current Setting Profile Thresholds")
async def update_current_thresholds(payload: ThresholdsUpdatePayload):
    setting_profile_id = _resolve_current_setting_profile_id(payload.auth_token)

    temp_lower = payload.temp_lower_threshold
    temp_upper = payload.temp_upper_threshold
    humidity_lower = payload.humidity_lower_threshold
    humidity_upper = payload.humidity_upper_threshold

    # If one side is missing in the request, use current DB values for pair checks.
    current = database.get_setting_profile_thresholds(setting_profile_id)
    if not current:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Setting profile not found",
        )
    if temp_lower is None:
        temp_lower = float(current["temp_lower_threshold"])
    if temp_upper is None:
        temp_upper = float(current["temp_upper_threshold"])
    if humidity_lower is None:
        humidity_lower = float(current["humidity_lower_threshold"])
    if humidity_upper is None:
        humidity_upper = float(current["humidity_upper_threshold"])

    if temp_lower >= temp_upper:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="temp_lower_threshold must be less than temp_upper_threshold",
        )
    if humidity_lower >= humidity_upper:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="humidity_lower_threshold must be less than humidity_upper_threshold",
        )
    if payload.gas_upper_threshold is not None and payload.gas_upper_threshold < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="gas_upper_threshold must be >= 0",
        )
    if payload.light_lower_threshold is not None and payload.light_lower_threshold < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="light_lower_threshold must be >= 0",
        )

    data = database.update_setting_profile_thresholds(
        setting_profile_id=setting_profile_id,
        temp_lower_threshold=payload.temp_lower_threshold,
        temp_upper_threshold=payload.temp_upper_threshold,
        humidity_lower_threshold=payload.humidity_lower_threshold,
        humidity_upper_threshold=payload.humidity_upper_threshold,
        gas_upper_threshold=payload.gas_upper_threshold,
        light_lower_threshold=payload.light_lower_threshold,
    )
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Setting profile not found",
        )
    return True
