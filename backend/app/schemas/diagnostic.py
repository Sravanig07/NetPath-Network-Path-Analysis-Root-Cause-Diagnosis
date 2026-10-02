from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class SessionCreateRequest(BaseModel):
    url: str = Field(..., description="Target service URL to diagnose")
    wait: bool = Field(default=False, description="If true, wait synchronously for diagnosis completion")


class DnsResultSchema(BaseModel):
    resolver: str = "system"
    latency_ms: float = 0.0
    record_type: str = "A"
    addresses: List[str] = Field(default_factory=list)
    status: str = "SUCCESS"
    error_message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class TcpResultSchema(BaseModel):
    destination_ip: str
    destination_port: int
    connect_latency_ms: float = 0.0
    status: str = "SUCCESS"
    error_message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class TlsResultSchema(BaseModel):
    tls_version: Optional[str] = None
    cipher: Optional[str] = None
    cert_subject: Optional[str] = None
    cert_issuer: Optional[str] = None
    cert_expires_at: Optional[datetime] = None
    days_to_expiration: Optional[int] = None
    handshake_latency_ms: float = 0.0
    is_valid: bool = True
    status: str = "SUCCESS"
    error_message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class HttpResultSchema(BaseModel):
    status_code: Optional[int] = None
    ttfb_ms: float = 0.0
    total_latency_ms: float = 0.0
    response_bytes: int = 0
    redirect_count: int = 0
    headers: Optional[Dict[str, Any]] = None
    status: str = "SUCCESS"
    error_message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class NetworkHopSchema(BaseModel):
    hop_number: int
    ip_address: Optional[str] = None
    hostname: Optional[str] = None
    rtt_ms: Optional[float] = None
    is_timeout: bool = False
    packet_loss_pct: float = 0.0

    model_config = ConfigDict(from_attributes=True)


class SystemMetricSchema(BaseModel):
    cpu_pct: float = 0.0
    memory_pct: float = 0.0
    load_1m: float = 0.0
    load_5m: float = 0.0
    load_15m: float = 0.0
    net_bytes_sent: int = 0
    net_bytes_recv: int = 0
    net_errin: int = 0
    net_errout: int = 0
    net_dropin: int = 0
    net_dropout: int = 0
    status: str = "SUCCESS"

    model_config = ConfigDict(from_attributes=True)
