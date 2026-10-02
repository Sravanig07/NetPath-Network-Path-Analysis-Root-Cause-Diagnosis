from __future__ import annotations

from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Integer, Float, Boolean, DateTime, ForeignKey, Text, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base

if TYPE_CHECKING:
    from backend.app.models.session import DiagnosticSession
    from backend.app.models.target import Target


class DnsResult(Base):
    __tablename__ = "dns_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("diagnostic_sessions.id", ondelete="CASCADE"), nullable=False, unique=True)
    resolver: Mapped[str] = mapped_column(String(128), default="system")
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    record_type: Mapped[str] = mapped_column(String(16), default="A")
    addresses: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # List of resolved IPs
    status: Mapped[str] = mapped_column(String(32), default="SUCCESS")  # SUCCESS, DNS_FAILURE, DNS_DEGRADATION
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    session: Mapped["DiagnosticSession"] = relationship("DiagnosticSession", back_populates="dns_result")


class TcpResult(Base):
    __tablename__ = "tcp_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("diagnostic_sessions.id", ondelete="CASCADE"), nullable=False, unique=True)
    destination_ip: Mapped[str] = mapped_column(String(64), nullable=False)
    destination_port: Mapped[int] = mapped_column(Integer, nullable=False)
    connect_latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(32), default="SUCCESS")  # SUCCESS, TCP_CONNECTIVITY_FAILURE, TCP_DEGRADATION
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    session: Mapped["DiagnosticSession"] = relationship("DiagnosticSession", back_populates="tcp_result")


class TlsResult(Base):
    __tablename__ = "tls_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("diagnostic_sessions.id", ondelete="CASCADE"), nullable=False, unique=True)
    tls_version: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    cipher: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    cert_subject: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    cert_issuer: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    cert_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    days_to_expiration: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    handshake_latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(32), default="SUCCESS")  # SUCCESS, TLS_FAILURE, TLS_CERTIFICATE_EXPIRING
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    session: Mapped["DiagnosticSession"] = relationship("DiagnosticSession", back_populates="tls_result")


class HttpResult(Base):
    __tablename__ = "http_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("diagnostic_sessions.id", ondelete="CASCADE"), nullable=False, unique=True)
    status_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ttfb_ms: Mapped[float] = mapped_column(Float, default=0.0)
    total_latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    response_bytes: Mapped[int] = mapped_column(Integer, default=0)
    redirect_count: Mapped[int] = mapped_column(Integer, default=0)
    headers: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="SUCCESS")  # SUCCESS, HTTP_APPLICATION_ERROR, HTTP_APPLICATION_LATENCY
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    session: Mapped["DiagnosticSession"] = relationship("DiagnosticSession", back_populates="http_result")


class NetworkHop(Base):
    __tablename__ = "network_hops"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("diagnostic_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    hop_number: Mapped[int] = mapped_column(Integer, nullable=False)
    ip_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    hostname: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    rtt_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_timeout: Mapped[bool] = mapped_column(Boolean, default=False)
    packet_loss_pct: Mapped[float] = mapped_column(Float, default=0.0)

    session: Mapped["DiagnosticSession"] = relationship("DiagnosticSession", back_populates="network_hops")


class SystemMetric(Base):
    __tablename__ = "system_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("diagnostic_sessions.id", ondelete="CASCADE"), nullable=False, unique=True)
    cpu_pct: Mapped[float] = mapped_column(Float, default=0.0)
    memory_pct: Mapped[float] = mapped_column(Float, default=0.0)
    load_1m: Mapped[float] = mapped_column(Float, default=0.0)
    load_5m: Mapped[float] = mapped_column(Float, default=0.0)
    load_15m: Mapped[float] = mapped_column(Float, default=0.0)
    net_bytes_sent: Mapped[int] = mapped_column(Integer, default=0)
    net_bytes_recv: Mapped[int] = mapped_column(Integer, default=0)
    net_errin: Mapped[int] = mapped_column(Integer, default=0)
    net_errout: Mapped[int] = mapped_column(Integer, default=0)
    net_dropin: Mapped[int] = mapped_column(Integer, default=0)
    net_dropout: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default="SUCCESS")  # SUCCESS, RESOURCE_PRESSURE, NETWORK_INTERFACE_ERRORS

    session: Mapped["DiagnosticSession"] = relationship("DiagnosticSession", back_populates="system_metric")


class MetricSample(Base):
    __tablename__ = "metric_samples"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    target_id: Mapped[int] = mapped_column(Integer, ForeignKey("targets.id", ondelete="CASCADE"), nullable=False, index=True)
    metric_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # dns_latency_ms, tcp_latency_ms, tls_latency_ms, http_latency_ms
    value: Mapped[float] = mapped_column(Float, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False, index=True)

    target: Mapped["Target"] = relationship("Target", back_populates="metric_samples")
