from __future__ import annotations

from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel


class MetricPercentileStats(BaseModel):
    metric_name: str
    count: int
    min: float
    max: float
    mean: float
    median: float
    p50: float
    p95: float
    p99: float
    std_dev: float
    is_sufficient_evidence: bool  # False if count < MIN_BASELINE_SAMPLES


class TargetBaselineResponse(BaseModel):
    target_id: int
    url: str
    hostname: str
    sample_count: int
    metrics: Dict[str, MetricPercentileStats]


class MetricHistoryPoint(BaseModel):
    recorded_at: datetime
    value: float


class MetricHistoryResponse(BaseModel):
    target_id: int
    metric_name: str
    points: List[MetricHistoryPoint]
