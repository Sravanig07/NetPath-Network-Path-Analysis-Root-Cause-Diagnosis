from __future__ import annotations

from datetime import datetime
from typing import List, TYPE_CHECKING
from sqlalchemy import String, Integer, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base

if TYPE_CHECKING:
    from backend.app.models.session import DiagnosticSession
    from backend.app.models.layer_results import MetricSample


class Target(Base):
    __tablename__ = "targets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    url: Mapped[str] = mapped_column(String(512), unique=True, index=True, nullable=False)
    hostname: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False, default=443)
    scheme: Mapped[str] = mapped_column(String(10), nullable=False, default="https")
    path: Mapped[str] = mapped_column(String(255), nullable=False, default="/")
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    sessions: Mapped[List["DiagnosticSession"]] = relationship(
        "DiagnosticSession", back_populates="target", cascade="all, delete-orphan"
    )
    metric_samples: Mapped[List["MetricSample"]] = relationship(
        "MetricSample", back_populates="target", cascade="all, delete-orphan"
    )
