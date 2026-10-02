from __future__ import annotations

from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base

if TYPE_CHECKING:
    from backend.app.models.session import DiagnosticSession


class Anomaly(Base):
    __tablename__ = "anomalies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("diagnostic_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    metric_name: Mapped[str] = mapped_column(String(64), nullable=False)
    observed_value: Mapped[float] = mapped_column(Float, nullable=False)
    expected_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    baseline_reference: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)  # e.g., "P95: 230ms"
    severity: Mapped[str] = mapped_column(String(32), default="MEDIUM")  # LOW, MEDIUM, HIGH, CRITICAL
    rule_triggered: Mapped[str] = mapped_column(String(128), nullable=False)
    evidence_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)

    session: Mapped["DiagnosticSession"] = relationship("DiagnosticSession", back_populates="anomalies")


class Diagnosis(Base):
    __tablename__ = "diagnoses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("diagnostic_sessions.id", ondelete="CASCADE"), nullable=False, unique=True)
    category: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    # DNS_FAILURE, DNS_DEGRADATION, TCP_CONNECTIVITY_FAILURE, TCP_DEGRADATION,
    # TLS_FAILURE, TLS_CERTIFICATE_EXPIRING, HTTP_APPLICATION_ERROR, HTTP_APPLICATION_LATENCY,
    # NETWORK_PACKET_LOSS, NETWORK_LATENCY, NETWORK_INTERFACE_ERRORS, RESOURCE_PRESSURE, INSUFFICIENT_EVIDENCE
    severity: Mapped[str] = mapped_column(String(32), default="HIGH")  # INFO, LOW, MEDIUM, HIGH, CRITICAL
    evidence_score: Mapped[int] = mapped_column(Integer, default=0)
    affected_layer: Mapped[str] = mapped_column(String(64), nullable=False)  # DNS, TCP, TLS, HTTP, Network, System
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)

    session: Mapped["DiagnosticSession"] = relationship("DiagnosticSession", back_populates="diagnosis")
    evidence_items: Mapped[List["DiagnosisEvidence"]] = relationship("DiagnosisEvidence", back_populates="diagnosis", cascade="all, delete-orphan")
    recommendations: Mapped[List["Recommendation"]] = relationship("Recommendation", back_populates="diagnosis", cascade="all, delete-orphan")


class DiagnosisEvidence(Base):
    __tablename__ = "diagnosis_evidence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    diagnosis_id: Mapped[int] = mapped_column(Integer, ForeignKey("diagnoses.id", ondelete="CASCADE"), nullable=False, index=True)
    weight: Mapped[int] = mapped_column(Integer, default=1)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    metric_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    diagnosis: Mapped["Diagnosis"] = relationship("Diagnosis", back_populates="evidence_items")


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    diagnosis_id: Mapped[int] = mapped_column(Integer, ForeignKey("diagnoses.id", ondelete="CASCADE"), nullable=False, index=True)
    action_order: Mapped[int] = mapped_column(Integer, default=1)
    action_text: Mapped[str] = mapped_column(Text, nullable=False)

    diagnosis: Mapped["Diagnosis"] = relationship("Diagnosis", back_populates="recommendations")


class IncidentEvent(Base):
    __tablename__ = "incident_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("diagnostic_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)  # START, FINISH, ANOMALY, DIAGNOSIS
    layer: Mapped[str] = mapped_column(String(32), nullable=False)  # DNS, TCP, TLS, HTTP, Network, System, Analysis
    message: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="SUCCESS")  # SUCCESS, DEGRADED, FAILED, INFO

    session: Mapped["DiagnosticSession"] = relationship("DiagnosticSession", back_populates="timeline_events")
