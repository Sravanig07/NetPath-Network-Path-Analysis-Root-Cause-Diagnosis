from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base

if TYPE_CHECKING:
    from backend.app.models.target import Target
    from backend.app.models.layer_results import (
        DnsResult,
        TcpResult,
        TlsResult,
        HttpResult,
        NetworkHop,
        SystemMetric,
    )
    from backend.app.models.diagnosis import Anomaly, Diagnosis, IncidentEvent


class DiagnosticSession(Base):
    __tablename__ = "diagnostic_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    target_id: Mapped[int] = mapped_column(Integer, ForeignKey("targets.id", ondelete="CASCADE"), nullable=False, index=True)
    correlation_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="PENDING", index=True, nullable=False)  # PENDING, RUNNING, COMPLETED, FAILED
    started_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    duration_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    target: Mapped["Target"] = relationship("Target", back_populates="sessions")
    dns_result: Mapped[Optional["DnsResult"]] = relationship("DnsResult", uselist=False, back_populates="session", cascade="all, delete-orphan")
    tcp_result: Mapped[Optional["TcpResult"]] = relationship("TcpResult", uselist=False, back_populates="session", cascade="all, delete-orphan")
    tls_result: Mapped[Optional["TlsResult"]] = relationship("TlsResult", uselist=False, back_populates="session", cascade="all, delete-orphan")
    http_result: Mapped[Optional["HttpResult"]] = relationship("HttpResult", uselist=False, back_populates="session", cascade="all, delete-orphan")
    network_hops: Mapped[List["NetworkHop"]] = relationship("NetworkHop", back_populates="session", cascade="all, delete-orphan")
    system_metric: Mapped[Optional["SystemMetric"]] = relationship("SystemMetric", uselist=False, back_populates="session", cascade="all, delete-orphan")
    anomalies: Mapped[List["Anomaly"]] = relationship("Anomaly", back_populates="session", cascade="all, delete-orphan")
    diagnosis: Mapped[Optional["Diagnosis"]] = relationship("Diagnosis", uselist=False, back_populates="session", cascade="all, delete-orphan")
    timeline_events: Mapped[List["IncidentEvent"]] = relationship("IncidentEvent", back_populates="session", cascade="all, delete-orphan")
