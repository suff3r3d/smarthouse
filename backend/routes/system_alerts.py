from fastapi import APIRouter

router = APIRouter()


@router.get("/system/mode", summary="Get System Mode")
async def get_system_mode():
    """
    Get the current system mode (e.g., "Home" or "Away").
    """
    pass


@router.get("/alerts", summary="List Recent Alerts")
async def get_alerts():
    """
    Get a list of recent alerts.
    """
    pass
