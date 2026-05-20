import database
import threading
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from routes.api import router as api_router
from utils import JWTHandler
from workers import device_polling_worker, scheduler_worker

@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.connect()

    app.state.device_poll_stop_event = threading.Event()
    app.state.device_poll_thread = threading.Thread(
        target=device_polling_worker,
        args=(app.state.device_poll_stop_event,),
        daemon=True,
        name="device-polling-thread",
    )
    app.state.device_poll_thread.start()

    app.state.scheduler_stop_event = threading.Event()
    app.state.scheduler_thread = threading.Thread(
        target=scheduler_worker,
        args=(app.state.scheduler_stop_event,),
        daemon=True,
        name="scheduler-thread",
    )
    app.state.scheduler_thread.start()
    yield

    app.state.scheduler_stop_event.set()
    app.state.scheduler_thread.join(timeout=5)

    app.state.device_poll_stop_event.set()
    app.state.device_poll_thread.join(timeout=5)
    await database.disconnect()

app = FastAPI(lifespan=lifespan)

app.include_router(api_router, prefix="/api")


def _copy_response_headers(response):
    return {
        key: value
        for key, value in response.headers.items()
        if key.lower() not in {"content-length", "content-type"}
    }


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "message": str(exc.detail)},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"success": False, "message": str(exc.errors())},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(_request: Request, _exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"success": False, "message": "Internal server error"},
    )


@app.middleware("http")
async def auth_context_middleware(request: Request, call_next):
    request.state.auth_user = None
    request.state.setting_profile_ids = []
    request.state.auth_error = None

    auth_token = request.headers.get("auth-token")
    if not auth_token:
        authorization = request.headers.get("authorization", "")
        if authorization.lower().startswith("bearer "):
            auth_token = authorization[7:].strip()
    if not auth_token:
        content_type = request.headers.get("content-type", "").lower()
        if "application/json" in content_type:
            try:
                body = await request.json()
            except Exception:
                body = None
            if isinstance(body, dict):
                body_token = body.get("auth_token")
                if isinstance(body_token, str) and body_token.strip():
                    auth_token = body_token.strip()

    if auth_token:
        decoded = JWTHandler.decode(auth_token)
        if not decoded:
            request.state.auth_error = "Invalid auth token"
        else:
            user_id = decoded.get("sub")
            try:
                user_id = int(user_id)
            except (TypeError, ValueError):
                request.state.auth_error = "Invalid auth token"
            else:
                user = database.get_user_by_id(user_id)
                if not user:
                    request.state.auth_error = "User not found"
                else:
                    request.state.auth_user = user
                    request.state.setting_profile_ids = database.get_setting_profile_ids_by_user_id(user.id)

    response = await call_next(request)

    content_type = response.headers.get("content-type", "").lower()
    if "application/json" not in content_type or response.status_code == 204:
        return response

    body = b""
    async for chunk in response.body_iterator:
        body += chunk

    try:
        payload = json.loads(body.decode() if body else "null")
    except Exception:
        payload = None

    if isinstance(payload, dict) and "success" in payload and (
        "data" in payload or "message" in payload
    ):
        return JSONResponse(
            status_code=response.status_code,
            content=payload,
            headers=_copy_response_headers(response),
        )

    if 200 <= response.status_code < 400:
        wrapped = {"success": True, "data": payload}
    else:
        message = payload.get("detail") if isinstance(payload, dict) else payload
        wrapped = {"success": False, "message": message or "Request failed"}

    return JSONResponse(
        status_code=response.status_code,
        content=wrapped,
        headers=_copy_response_headers(response),
    )

@app.get("/")
async def root():
    return {"message": "Smart House FastAPI server is running!"}

# @app.get("/db-test")
# async def test_db():
#     try:
#         await database.engine.execute(text("SELECT 1"))
#         return {"status": "Database connection successful"}
#     except Exception as e:
#         return {"status": "Database connection failed", "error": str(e)}

@app.get("/get-user-by-username")
def get_user_by_username_endpoint(username: str):
  user = database.get_user_by_username(username)
  return user
