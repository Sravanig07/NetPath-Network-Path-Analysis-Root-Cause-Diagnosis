from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseCollector(ABC):
    """Abstract base class for all diagnostic collectors."""

    def __init__(self, timeout_seconds: float = 8.0) -> None:
        self.timeout_seconds = timeout_seconds

    @abstractmethod
    def collect(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Execute diagnostic measurement and return normalized dictionary result."""
        pass

    @staticmethod
    def current_time_ms() -> float:
        """High-resolution monotonic timer in milliseconds."""
        return time.perf_counter() * 1000.0
