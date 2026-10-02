from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from backend.app.schemas.target import TargetRead
from backend.app.schemas.diagnostic import (
    DnsResultSchema,
    TcpResultSchema,
    TlsResultSchema,
    HttpResultSchema,
    NetworkHopSchema,
    SystemMetricSchema,
)


class AnomalySchema(BaseModel):
    id: Optional[int] = None
    metric_name: str
    observed_value: float
    expected_value: Optional[float] = None
    baseline_reference: Optional[str] = None
    severity: str
    rule_triggered: str
    evidence_text: str
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class EvidenceItemSchema(BaseModel):
    id: Optional[int] = None
    weight: int
    description: str
    metric_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class RecommendationSchema(BaseModel):
    id: Optional[int] = None
    action_order: int
    action_text: str

    model_config = ConfigDict(from_attributes=True)


class DiagnosisSchema(BaseModel):
    category: str
    severity: str
    evidence_score: int
    affected_layer: str
    summary: str
    created_at: Optional[datetime] = None
    evidence_items: List[EvidenceItemSchema] = Field(default_factory=list)
    recommendations: List[RecommendationSchema] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class IncidentTimelineEventSchema(BaseModel):
    id: Optional[int] = None
    timestamp: datetime
    event_type: str
    layer: str
    message: str
    status: str

    model_config = ConfigDict(from_attributes=True)


class DependencyGraphNode(BaseModel):
    id: str
    label: str
    layer: str
    status: str  # NORMAL, DEGRADED, FAILED, UNKNOWN
    details: Dict[str, Any] = Field(default_factory=dict)


class DependencyGraphEdge(BaseModel):
    source: str
    target: str
    label: Optional[str] = None


class DependencyGraphResponse(BaseModel):
    nodes: List[DependencyGraphNode]
    edges: List[DependencyGraphEdge]


class DiagnosticSessionDetailResponse(BaseModel):
    id: str
    target: TargetRead
    correlation_id: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: Optional[float] = None
    error_message: Optional[str] = None

    dns_result: Optional[DnsResultSchema] = None
    tcp_result: Optional[TcpResultSchema] = None
    tls_result: Optional[TlsResultSchema] = None
    http_result: Optional[HttpResultSchema] = None
    network_hops: List[NetworkHopSchema] = Field(default_factory=list)
    system_metric: Optional[SystemMetricSchema] = None

    anomalies: List[AnomalySchema] = Field(default_factory=list)
    diagnosis: Optional[DiagnosisSchema] = None
    timeline_events: List[IncidentTimelineEventSchema] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
