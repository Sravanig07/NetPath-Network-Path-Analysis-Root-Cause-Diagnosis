from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from backend.app.config import settings
from backend.app.database.session import init_db
from backend.app.api.router import api_router
from backend.app.observability.logging import setup_logging

# Configure structured JSON logging
setup_logging(settings.LOG_LEVEL)
logger = logging.getLogger("netpath.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing NetPath Diagnostic Platform...")
    init_db()
    yield
    logger.info("NetPath Diagnostic Platform shutting down.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Deterministic Network Path Analysis & Root-Cause Diagnosis Platform",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Prometheus metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Include API v1 routes
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/", tags=["Root"])
def root():
    return {
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "online",
        "docs": "/docs",
        "metrics": "/metrics",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
