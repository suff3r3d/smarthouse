from fastapi import APIRouter

from routes.auth import router as auth_router
from routes.devices import router as devices_router
from routes.misc import router as misc_router
from routes.schedules import router as schedules_router
from routes.sensors import router as sensors_router
from routes.setting_profiles import router as setting_profiles_router
from routes.system_alerts import router as system_alerts_router
from routes.users import router as users_router

router = APIRouter()

router.include_router(misc_router)
router.include_router(auth_router)
router.include_router(users_router)
router.include_router(sensors_router)
router.include_router(devices_router)
router.include_router(schedules_router)
router.include_router(setting_profiles_router)
router.include_router(system_alerts_router)
