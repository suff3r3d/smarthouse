from fastapi import APIRouter, Depends, HTTPException, status

import database
from routes.deps import require_auth

router = APIRouter()


@router.get("/users", summary="List Family Members")
async def list_users(auth: dict = Depends(require_auth)):
    """
    List all users in the household with their role.
    Available to both homeowner and family members.
    """
    try:
        users = database.list_all_users()
        return {"users": users, "count": len(users)}
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch users: {exc}",
        )


@router.delete("/users/{user_id}", summary="Delete Family Member")
async def delete_user(user_id: int, auth: dict = Depends(require_auth)):
    """
    Delete a family member account. Homeowner only. Cannot delete the homeowner.
    """
    request_user = auth["user"]
    if not request_user.is_house_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only house owner can delete accounts",
        )

    target = database.get_user_by_id(user_id)
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    if target.is_house_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete the house owner account",
        )

    database.delete_user(user_id)
    return {"message": "Family member deleted successfully"}
