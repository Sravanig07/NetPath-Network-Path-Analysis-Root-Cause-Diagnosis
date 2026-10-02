from __future__ import annotations

from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.models.target import Target
from backend.app.models.layer_results import MetricSample
from backend.app.analysis.baseline import BaselineEngine
from backend.app.schemas.metrics import TargetBaselineResponse, MetricHistoryResponse, MetricHistoryPoint

router = APIRouter(prefix="/metrics", tags=["Metrics & Baselines"])
baseline_engine = BaselineEngine()


@router.get("/baselines/{target_id}", response_model=TargetBaselineResponse)
def get_target_baselines(target_id: int, db: Session = Depends(get_db)):
    """Fetch statistical P50/P95/P99 baseline distributions for a target."""
    target = db.execute(select(Target).where(Target.id == target_id)).scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")

    baselines = baseline_engine.get_target_baselines(db, target_id)
    total_samples = db.execute(
        select(MetricSample).where(MetricSample.target_id == target_id)
    ).scalars().all()

    return TargetBaselineResponse(
        target_id=target.id,
        url=target.url,
        hostname=target.hostname,
        sample_count=len(total_samples),
        metrics=baselines,
    )


@router.get("/history/{target_id}", response_model=MetricHistoryResponse)
def get_metric_history(
    target_id: int,
    metric_name: str = Query("http_latency_ms", description="Metric to retrieve: dns_latency_ms, tcp_latency_ms, tls_latency_ms, http_latency_ms, http_ttfb_ms"),
    limit: int = Query(50, ge=5, le=200),
    db: Session = Depends(get_db)
):
    """Retrieve historical time-series points for graphing."""
    target = db.execute(select(Target).where(Target.id == target_id)).scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")

    samples = (
        db.execute(
            select(MetricSample)
            .where(MetricSample.target_id == target_id, MetricSample.metric_name == metric_name)
            .order_by(desc(MetricSample.recorded_at))
            .limit(limit)
        )
        .scalars()
        .all()
    )

    points = [MetricHistoryPoint(recorded_at=s.recorded_at, value=s.value) for s in reversed(samples)]
    return MetricHistoryResponse(target_id=target_id, metric_name=metric_name, points=points)
