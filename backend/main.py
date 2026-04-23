import database
import threading
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from routes.api import router as api_router
from utils import AdafruitIO, JWTHandler

logger = logging.getLogger("device_poller")


def _device_polling_worker(stop_event: threading.Event) -> None:
    print("[device-poller] started", flush=True)
    while not stop_event.is_set():
        try:
            devices = asyncio.run(AdafruitIO().get_all_devices())
            for device in devices:
                device_name = device.get("name") or device.get("key") or "unknown"
                print(f"{device_name}: {device.get('last_data')}", flush=True)
        except Exception as exc:
            logger.exception("Device polling error: %s", exc)
        stop_event.wait(60)
    print("[device-poller] stopped", flush=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.device_poll_stop_event = threading.Event()
    app.state.device_poll_thread = threading.Thread(
        target=_device_polling_worker,
        args=(app.state.device_poll_stop_event,),
        daemon=True,
        name="device-polling-thread",
    )
    app.state.device_poll_thread.start()
    await database.connect()
    yield
    app.state.device_poll_stop_event.set()
    app.state.device_poll_thread.join(timeout=5)
    await database.disconnect()

app = FastAPI(lifespan=lifespan)

app.include_router(api_router, prefix="/api")


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

    return await call_next(request)

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
