from __future__ import annotations

import asyncio
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session, joinedload

from backend.app.database.session import get_db
from backend.app.models.session import DiagnosticSession
from backend.app.models.target import Target
from backend.app.models.diagnosis import Diagnosis
from backend.app.schemas.diagnostic import SessionCreateRequest
from backend.app.schemas.analysis import (
    DiagnosticSessionDetailResponse,
    DiagnosisSchema,
    EvidenceItemSchema,
    RecommendationSchema,
    IncidentTimelineEventSchema,
    DependencyGraphResponse,
)
from backend.app.services.diagnostic_service import DiagnosticService
from backend.app.security.ssrf import SSRFValidationError

router = APIRouter(prefix="/diagnostics", tags=["Diagnostics"])
diagnostic_service = DiagnosticService()


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_diagnostic_session(
    payload: SessionCreateRequest,
    db: Session = Depends(get_db)
):
    """
    Initiates a new deterministic diagnostic session for a target URL.
    Can execute in background (default) or wait synchronously.
    """
    try:
        target = diagnostic_service.get_or_create_target(db, payload.url)
    except SSRFValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"SSRF validation blocked request: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid URL or hostname: {str(e)}"
        )

    session_id = str(uuid.uuid4())
    correlation_id = f"corr-{uuid.uuid4().hex[:12]}"

    session = DiagnosticSession(
        id=session_id,
        target_id=target.id,
        correlation_id=correlation_id,
        status="RUNNING" if payload.wait else "PENDING",
    )
    db.add(session)
    db.commit()

    if payload.wait:
        # Run synchronously and return completed session
        diagnostic_service.execute_diagnostic_sync(session_id, payload.url)
        return {"session_id": session_id, "correlation_id": correlation_id, "status": "COMPLETED"}
    else:
        # Run in background asyncio task
        asyncio.create_task(diagnostic_service.execute_diagnostic_async(session_id, payload.url))
        return {
            "session_id": session_id,
            "correlation_id": correlation_id,
            "status": "PENDING",
            "message": "Diagnostic session initiated in background.",
        }


@router.get("", response_model=List[DiagnosticSessionDetailResponse])
def list_diagnostic_sessions(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    target_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """List recent diagnostic sessions with pagination."""
    query = (
        select(DiagnosticSession)
        .options(
            joinedload(DiagnosticSession.target),
            joinedload(DiagnosticSession.diagnosis),
        )
        .order_by(desc(DiagnosticSession.started_at))
    )
    if target_id:
        query = query.where(DiagnosticSession.target_id == target_id)

    sessions = db.execute(query.offset(offset).limit(limit)).unique().scalars().all()
    # Serialize properly
    return [build_session_detail_response(s) for s in sessions]


@router.get("/{session_id}", response_model=DiagnosticSessionDetailResponse)
def get_diagnostic_session(session_id: str, db: Session = Depends(get_db)):
    """Fetch full diagnostic session details by ID."""
    session = fetch_session_with_relations(db, session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Diagnostic session not found")
    return build_session_detail_response(session)


@router.get("/{session_id}/timeline", response_model=List[IncidentTimelineEventSchema])
def get_session_timeline(session_id: str, db: Session = Depends(get_db)):
    """Retrieve chronologically ordered incident timeline events for a session."""
    session = fetch_session_with_relations(db, session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Diagnostic session not found")
    events = sorted(session.timeline_events, key=lambda e: e.timestamp)
    return [IncidentTimelineEventSchema.model_validate(e) for e in events]


@router.get("/{session_id}/diagnosis", response_model=Optional[DiagnosisSchema])
def get_session_diagnosis(session_id: str, db: Session = Depends(get_db)):
    """Retrieve deterministic root-cause diagnosis for a session."""
    session = fetch_session_with_relations(db, session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Diagnostic session not found")
    if not session.diagnosis:
        return None
    return DiagnosisSchema.model_validate(session.diagnosis)


@router.get("/{session_id}/evidence", response_model=List[EvidenceItemSchema])
def get_session_evidence(session_id: str, db: Session = Depends(get_db)):
    """Retrieve explainable evidence items with score weights."""
    session = fetch_session_with_relations(db, session_id)
    if not session or not session.diagnosis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found for session")
    return [EvidenceItemSchema.model_validate(ev) for ev in session.diagnosis.evidence_items]


@router.get("/{session_id}/recommendations", response_model=List[RecommendationSchema])
def get_session_recommendations(session_id: str, db: Session = Depends(get_db)):
    """Retrieve actionable investigation and remediation steps."""
    session = fetch_session_with_relations(db, session_id)
    if not session or not session.diagnosis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recommendations not found for session")
    recs = sorted(session.diagnosis.recommendations, key=lambda r: r.action_order)
    return [RecommendationSchema.model_validate(r) for r in recs]


@router.get("/{session_id}/graph", response_model=DependencyGraphResponse)
def get_session_graph(session_id: str, db: Session = Depends(get_db)):
    """Retrieve interactive dependency DAG graph for the session."""
    session = fetch_session_with_relations(db, session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    dns_dict = {
        "status": session.dns_result.status if session.dns_result else "UNKNOWN",
        "latency_ms": session.dns_result.latency_ms if session.dns_result else 0.0,
        "addresses": session.dns_result.addresses.get("ips", []) if session.dns_result and session.dns_result.addresses else [],
    } if session.dns_result else None

    tcp_dict = {
        "status": session.tcp_result.status if session.tcp_result else "UNKNOWN",
        "destination_ip": session.tcp_result.destination_ip if session.tcp_result else "Unknown",
        "connect_latency_ms": session.tcp_result.connect_latency_ms if session.tcp_result else 0.0,
    } if session.tcp_result else None

    tls_dict = {
        "status": session.tls_result.status if session.tls_result else "UNKNOWN",
        "handshake_latency_ms": session.tls_result.handshake_latency_ms if session.tls_result else 0.0,
        "cipher": session.tls_result.cipher if session.tls_result else None,
        "days_to_expiration": session.tls_result.days_to_expiration if session.tls_result else None,
    } if session.tls_result else None

    http_dict = {
        "status": session.http_result.status if session.http_result else "UNKNOWN",
        "status_code": session.http_result.status_code if session.http_result else None,
        "total_latency_ms": session.http_result.total_latency_ms if session.http_result else 0.0,
    } if session.http_result else None

    diag_schema = DiagnosisSchema.model_validate(session.diagnosis) if session.diagnosis else DiagnosisSchema(
        category="INSUFFICIENT_EVIDENCE",
        severity="INFO",
        evidence_score=0,
        affected_layer="None",
        summary="No diagnosis",
    )

    return diagnostic_service.diagnosis_engine.build_dependency_graph(
        dns_res=dns_dict,
        tcp_res=tcp_dict,
        tls_res=tls_dict,
        http_res=http_dict,
        network_hops=[],
        system_metric=None,
        diagnosis=diag_schema,
    )


def fetch_session_with_relations(db: Session, session_id: str) -> Optional[DiagnosticSession]:
    query = (
        select(DiagnosticSession)
        .where(DiagnosticSession.id == session_id)
        .options(
            joinedload(DiagnosticSession.target),
            joinedload(DiagnosticSession.dns_result),
            joinedload(DiagnosticSession.tcp_result),
            joinedload(DiagnosticSession.tls_result),
            joinedload(DiagnosticSession.http_result),
            joinedload(DiagnosticSession.network_hops),
            joinedload(DiagnosticSession.system_metric),
            joinedload(DiagnosticSession.anomalies),
            joinedload(DiagnosticSession.diagnosis).joinedload(Diagnosis.evidence_items),
            joinedload(DiagnosticSession.diagnosis).joinedload(Diagnosis.recommendations),
            joinedload(DiagnosticSession.timeline_events),
        )
    )
    return db.execute(query).unique().scalar_one_or_none()


def build_session_detail_response(session: DiagnosticSession) -> DiagnosticSessionDetailResponse:
    dns_res = None
    if session.dns_result:
        dns_res = {
            "resolver": session.dns_result.resolver,
            "latency_ms": session.dns_result.latency_ms,
            "record_type": session.dns_result.record_type,
            "addresses": session.dns_result.addresses.get("ips", []) if session.dns_result.addresses else [],
            "status": session.dns_result.status,
            "error_message": session.dns_result.error_message,
        }

    return DiagnosticSessionDetailResponse(
        id=session.id,
        target=session.target,
        correlation_id=session.correlation_id,
        status=session.status,
        started_at=session.started_at,
        completed_at=session.completed_at,
        duration_ms=session.duration_ms,
        error_message=session.error_message,
        dns_result=dns_res,
        tcp_result=session.tcp_result,
        tls_result=session.tls_result,
        http_result=session.http_result,
        network_hops=session.network_hops or [],
        system_metric=session.system_metric,
        anomalies=session.anomalies or [],
        diagnosis=session.diagnosis,
        timeline_events=session.timeline_events or [],
    )
