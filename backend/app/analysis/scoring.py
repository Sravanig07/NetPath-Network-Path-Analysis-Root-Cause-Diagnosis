from __future__ import annotations

from typing import List
from backend.app.schemas.analysis import EvidenceItemSchema


class ScoringEngine:
    """
    Computes explainable Evidence Score from aggregated multi-layer evidence.
    Does NOT present scores as machine learning probability.
    """

    @staticmethod
    def calculate_score(evidence_items: List[EvidenceItemSchema]) -> int:
        score = sum(item.weight for item in evidence_items)
        return max(0, score)
