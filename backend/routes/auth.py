from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
import database
from models import User
from utils import JWTHandler, PasswordHandler

router = APIRouter()


class UserLogin(BaseModel):
    username: str
    password: str


class UserCreate(UserLogin):
    is_house_owner: bool = False


@router.post("/auth/register", summary="User Registration")
async def register_user(user_create: UserCreate):
    """
    User registration.
    """
    db_user = database.get_user_by_username(username=user_create.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    hashed_password = PasswordHandler.get_hashed_password(user_create.password)
    user = User(
        username=user_create.username,
        password_hash=hashed_password,
        is_house_owner=user_create.is_house_owner,
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
