from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, status

import database

router = APIRouter()


@router.get("/system/mode", summary="Get System Mode")
async def get_system_mode():
    """
    Get the current system mode (e.g., "Home" or "Away").
    """
    pass


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
