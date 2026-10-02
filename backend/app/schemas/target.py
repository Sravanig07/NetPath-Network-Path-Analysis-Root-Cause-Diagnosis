from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class TargetBase(BaseModel):
    url: str = Field(..., description="Target service URL (e.g., https://example.com or http://test-service-a:8001)")


class TargetCreate(TargetBase):
    pass


class TargetRead(TargetBase):
    id: int
    hostname: str
    port: int
    scheme: str
    path: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TargetStatusSummary(BaseModel):
    target: TargetRead
    total_sessions: int
    latest_status: str
    latest_diagnosis: Optional[str] = None
    latest_severity: Optional[str] = None
    dns_status: str
    tcp_status: str
    tls_status: str
    http_status: str
    network_status: str
    system_status: str
    last_diagnosed_at: Optional[datetime] = None
