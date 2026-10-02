from __future__ import annotations

import json
from typing import List, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "NetPath — Deterministic Network Path Analysis & Root-Cause Diagnosis Platform"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    
    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # Database
    # Default is MySQL 8 as required. Can fall back to SQLite when MySQL is not running.
    DATABASE_URL: str = Field(
        default="mysql+pymysql://netpath_user:netpath_password@mysql:3306/netpath_db",
        description="SQLAlchemy Database connection URI"
    )
    SQL_ECHO: bool = False

    # Security & SSRF
    ALLOW_PRIVATE_IPS: bool = False
    ALLOWLISTED_HOSTS: List[str] = [
        "test-service-a",
        "test-service-b",
        "test-service-c"
    ]
    
    # Analysis & Diagnostic Settings
    PROBE_TIMEOUT_SECONDS: float = 8.0
    MIN_BASELINE_SAMPLES: int = 10
    BASELINE_LOOKBACK_SAMPLES: int = 100
    
    # Scoring weights
    SCORE_DNS_ANOMALY: int = 3
    SCORE_TCP_FAILURE: int = 4
    SCORE_TCP_DEGRADATION: int = 2
    SCORE_TLS_FAILURE: int = 4
    SCORE_TLS_EXPIRING: int = 3
    SCORE_HTTP_ERROR: int = 4
    SCORE_HTTP_LATENCY: int = 3
    SCORE_PACKET_LOSS: int = 3
    SCORE_BASELINE_VIOLATION: int = 2
    SCORE_INTERFACE_DROPS: int = 2

    # CORS
    CORS_ORIGINS: List[str] = ["*"]

    @field_validator("ALLOWLISTED_HOSTS", mode="before")
    def assemble_allowlist(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return [i.strip() for i in v.split(",") if i.strip()]
        return v

    @field_validator("CORS_ORIGINS", mode="before")
    def assemble_cors(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return [i.strip() for i in v.split(",") if i.strip()]
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
