from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session
from backend.app.database.session import get_db

router = APIRouter(tags=["Health & Probes"])


@router.get("/health")
def health_check():
    """Liveness probe."""
    return {"status": "healthy", "service": "NetPath Engine"}


@router.get("/ready")
def readiness_check(db: Session = Depends(get_db)):
    """Readiness probe verifying database connectivity."""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ready", "database": "connected"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection error: {str(e)}"
        )
