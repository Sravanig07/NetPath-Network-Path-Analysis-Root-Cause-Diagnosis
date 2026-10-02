from __future__ import annotations

import math
import statistics
from typing import Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.models.layer_results import MetricSample
from backend.app.schemas.metrics import MetricPercentileStats


class BaselineEngine:
    """
    Computes statistical baseline distributions (min, max, mean, median, P50, P95, P99, std_dev)
    from historical samples stored in MySQL.
    Enforces minimum sample size safeguards to prevent false positives.
    """

    def __init__(self, min_samples: Optional[int] = None, lookback_samples: Optional[int] = None) -> None:
        self.min_samples = min_samples if min_samples is not None else settings.MIN_BASELINE_SAMPLES
        self.lookback_samples = lookback_samples if lookback_samples is not None else settings.BASELINE_LOOKBACK_SAMPLES

    def calculate_stats(self, values: List[float], metric_name: str) -> MetricPercentileStats:
        count = len(values)
        if count == 0:
            return MetricPercentileStats(
                metric_name=metric_name,
                count=0,
                min=0.0,
                max=0.0,
                mean=0.0,
                median=0.0,
                p50=0.0,
                p95=0.0,
                p99=0.0,
                std_dev=0.0,
                is_sufficient_evidence=False,
            )

        sorted_vals = sorted(values)
        min_val = sorted_vals[0]
        max_val = sorted_vals[-1]
        mean_val = statistics.mean(sorted_vals)
        median_val = statistics.median(sorted_vals)
        std_dev = statistics.stdev(sorted_vals) if count > 1 else 0.0

        p50 = self._percentile(sorted_vals, 0.50)
        p95 = self._percentile(sorted_vals, 0.95)
        p99 = self._percentile(sorted_vals, 0.99)

        return MetricPercentileStats(
            metric_name=metric_name,
            count=count,
            min=round(min_val, 2),
            max=round(max_val, 2),
            mean=round(mean_val, 2),
            median=round(median_val, 2),
            p50=round(p50, 2),
            p95=round(p95, 2),
            p99=round(p99, 2),
            std_dev=round(std_dev, 2),
            is_sufficient_evidence=(count >= self.min_samples),
        )

    def get_target_baselines(self, db: Session, target_id: int) -> Dict[str, MetricPercentileStats]:
        """Fetch historical samples for a target and calculate baselines for each metric."""
        metric_names = [
            "dns_latency_ms",
            "tcp_latency_ms",
            "tls_latency_ms",
            "http_latency_ms",
            "http_ttfb_ms",
        ]
        baselines: Dict[str, MetricPercentileStats] = {}

        for m_name in metric_names:
            stmt = (
                select(MetricSample.value)
                .where(MetricSample.target_id == target_id, MetricSample.metric_name == m_name)
                .order_by(MetricSample.recorded_at.desc())
                .limit(self.lookback_samples)
            )
            rows = db.execute(stmt).scalars().all()
            baselines[m_name] = self.calculate_stats(list(rows), m_name)

        return baselines

    @staticmethod
    def _percentile(sorted_list: List[float], p: float) -> float:
        """Calculate percentile using nearest-rank / linear interpolation."""
        if not sorted_list:
            return 0.0
        if len(sorted_list) == 1:
            return sorted_list[0]
        k = (len(sorted_list) - 1) * p
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return sorted_list[int(k)]
        d0 = sorted_list[int(f)] * (c - k)
        d1 = sorted_list[int(c)] * (k - f)
        return d0 + d1
