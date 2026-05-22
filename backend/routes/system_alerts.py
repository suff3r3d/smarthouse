from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

import database
from routes.deps import require_auth

router = APIRouter()


@router.get("/system/mode", summary="Get System Mode")
async def get_system_mode(auth: dict = Depends(require_auth)):
    """
    Return the current away mode and automation mode status for the authenticated user's profile.
    """
    user = auth["user"]
    profile_id = database.get_current_setting_profile_id_by_user_id(user.id)
    if profile_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current setting profile not found for user",
        )
    data = database.get_mode_settings(profile_id)
    return {
        "away_mode": data["away_mode"],
        "automation_mode": data["automation_mode"],
        "door_auto_lock": data["door_auto_lock"],
        "door_auto_lock_delay_sec": data["door_auto_lock_delay_sec"],
    }


@router.get("/alerts/list", summary="List Alerts")
async def list_alerts(
    since: Optional[datetime] = None,
    feed_key: Optional[str] = None,
):
    """
    Get a list of alerts.
    """
    try:
        alerts = database.list_alerts(limit=100, since=since, feed_key=feed_key)
        return {"alerts": alerts, "count": len(alerts)}
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch alerts from database: {exc}",
        )
