from __future__ import annotations

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session, joinedload

from backend.app.database.session import get_db
from backend.app.models.target import Target
from backend.app.models.session import DiagnosticSession
from backend.app.schemas.target import TargetCreate, TargetRead, TargetStatusSummary
from backend.app.services.diagnostic_service import DiagnosticService
from backend.app.security.ssrf import SSRFValidationError

router = APIRouter(prefix="/targets", tags=["Targets"])
diagnostic_service = DiagnosticService()


@router.get("", response_model=List[TargetStatusSummary])
def list_targets(db: Session = Depends(get_db)):
    """List all registered targets with their latest health statuses across all 6 layers."""
    targets = db.execute(select(Target).order_by(desc(Target.created_at))).scalars().all()
    summaries = []

    for target in targets:
        # Fetch latest diagnostic session for target
        latest_session = (
            db.execute(
                select(DiagnosticSession)
                .where(DiagnosticSession.target_id == target.id)
                .options(
                    joinedload(DiagnosticSession.dns_result),
                    joinedload(DiagnosticSession.tcp_result),
                    joinedload(DiagnosticSession.tls_result),
                    joinedload(DiagnosticSession.http_result),
                    joinedload(DiagnosticSession.system_metric),
                    joinedload(DiagnosticSession.diagnosis),
                )
                .order_by(desc(DiagnosticSession.started_at))
            )
            .unique()
            .scalars()
            .first()
        )

        total_sessions = db.execute(
            select(func.count(DiagnosticSession.id)).where(DiagnosticSession.target_id == target.id)
        ).scalar() or 0

        dns_status = latest_session.dns_result.status if (latest_session and latest_session.dns_result) else "UNKNOWN"
        tcp_status = latest_session.tcp_result.status if (latest_session and latest_session.tcp_result) else "UNKNOWN"
        tls_status = latest_session.tls_result.status if (latest_session and latest_session.tls_result) else "UNKNOWN"
        http_status = latest_session.http_result.status if (latest_session and latest_session.http_result) else "UNKNOWN"
        sys_status = latest_session.system_metric.status if (latest_session and latest_session.system_metric) else "UNKNOWN"
        net_status = "SUCCESS" if (latest_session and latest_session.network_hops) else "UNKNOWN"

        latest_diag_cat = latest_session.diagnosis.category if (latest_session and latest_session.diagnosis) else None
        latest_diag_sev = latest_session.diagnosis.severity if (latest_session and latest_session.diagnosis) else None

        summaries.append(
            TargetStatusSummary(
                target=target,
                total_sessions=total_sessions,
                latest_status=latest_session.status if latest_session else "NEVER_RUN",
                latest_diagnosis=latest_diag_cat,
                latest_severity=latest_diag_sev,
                dns_status=dns_status,
                tcp_status=tcp_status,
                tls_status=tls_status,
                http_status=http_status,
                network_status=net_status,
                system_status=sys_status,
                last_diagnosed_at=latest_session.completed_at if latest_session else None,
            )
        )

    return summaries


@router.post("", response_model=TargetRead, status_code=status.HTTP_201_CREATED)
def create_target(payload: TargetCreate, db: Session = Depends(get_db)):
    """Add a new target to monitor."""
    try:
        target = diagnostic_service.get_or_create_target(db, payload.url)
        return target
    except SSRFValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"SSRF validation blocked request: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{target_id}", response_model=TargetRead)
def get_target(target_id: int, db: Session = Depends(get_db)):
    target = db.execute(select(Target).where(Target.id == target_id)).scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target not found")
    return target
