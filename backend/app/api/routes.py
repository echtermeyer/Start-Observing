from fastapi import APIRouter

from app.api.visualizations import router as viz_router
from app.api.datasets import router as datasets_router
from app.api.auth import router as auth_router
from app.api.insights import router as insights_router
from app.api.alerts import router as alerts_router
from app.api.chat import router as chat_router
from app.api.settings import router as settings_router

router = APIRouter()

router.include_router(auth_router, prefix="/auth", tags=["auth"])
router.include_router(datasets_router, prefix="/datasets", tags=["datasets"])
router.include_router(viz_router, prefix="/visualizations", tags=["visualizations"])
router.include_router(insights_router, prefix="/insights", tags=["insights"])
router.include_router(alerts_router, prefix="/alerts", tags=["alerts"])
router.include_router(chat_router, prefix="/chat", tags=["chat"])
router.include_router(settings_router, prefix="/settings", tags=["settings"])
