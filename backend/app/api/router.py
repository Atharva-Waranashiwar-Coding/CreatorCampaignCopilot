from fastapi import APIRouter

from app.api.routes.auth import router as auth_router
from app.api.routes.brands import router as brands_router
from app.api.routes.briefs import router as briefs_router
from app.api.routes.campaigns import router as campaigns_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.drafts import router as drafts_router
from app.api.routes.health import router as health_router
from app.api.routes.projects import router as projects_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(brands_router, prefix="/brands", tags=["brands"])
api_router.include_router(projects_router, prefix="/projects", tags=["projects"])
api_router.include_router(campaigns_router, prefix="/campaigns", tags=["campaigns"])
api_router.include_router(briefs_router, tags=["briefs"])
api_router.include_router(drafts_router, prefix="/drafts", tags=["drafts"])
