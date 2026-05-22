import re

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

import database
from models import User
from routes.deps import require_auth
from utils import JWTHandler, PasswordHandler

router = APIRouter()

_PASSWORD_RE = re.compile(
    r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()\-_=+\[\]{}|;:\'",.<>?/\\`~]).{8,}$'
)


class UserLogin(BaseModel):
    username: str
    password: str


class UserCreate(UserLogin):
    pass


class ChangePasswordPayload(BaseModel):
    current_password: str
    new_password: str
    confirm_new_password: str


@router.post("/auth/register", summary="User Registration")
async def register_user(user_create: UserCreate, auth: dict = Depends(require_auth)):
    """
    User registration.
    """
    request_user = auth["user"]
    if request_user is None or not request_user.is_house_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only house owner can create accounts",
        )

    db_user = database.get_user_by_username(username=user_create.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    hashed_password = PasswordHandler.get_hashed_password(user_create.password)
    user = User(
        username=user_create.username,
        password_hash=hashed_password,
        is_house_owner=False,
        house_owner_id=request_user.id,
    )
    database.create_user(user)
    return {"message": "User registered successfully"}


@router.post("/auth/login", summary="User Login")
async def login_for_access_token(user_login: UserLogin):
    """
    User login to get a token.
    """
    user = database.get_user_by_username(user_login.username)
    if not user or not PasswordHandler.verify_password(user_login.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = JWTHandler.sign(user_id=str(user.id))
    return {"access_token": access_token, "token_type": "bearer"}


@router.put("/auth/change-password", summary="Change Password")
async def change_password(payload: ChangePasswordPayload, auth: dict = Depends(require_auth)):
    """
    Change the authenticated user's password.
    New password must be ≥8 chars and contain uppercase, lowercase, digit, and special character.
    """
    user = auth["user"]

    if not PasswordHandler.verify_password(payload.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    if payload.new_password != payload.confirm_new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password and confirmation do not match",
        )

    if not _PASSWORD_RE.match(payload.new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "New password must be at least 8 characters and contain "
                "uppercase, lowercase, digit, and special character"
            ),
        )

    new_hash = PasswordHandler.get_hashed_password(payload.new_password)
    database.update_user_password(user.id, new_hash)
    return {"message": "Password changed successfully"}
