from fastapi import APIRouter

router = APIRouter()


@router.get("/users", summary="List all users")
async def list_users():
    """
    List all users (for privileged users).
    """
    pass
