from __future__ import annotations

from fastapi import APIRouter
from backend.app.api.v1.diagnostics import router as diagnostics_router
from backend.app.api.v1.targets import router as targets_router
from backend.app.api.v1.metrics import router as metrics_router
from backend.app.api.v1.health import router as health_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(diagnostics_router)
api_router.include_router(targets_router)
api_router.include_router(metrics_router)
