import pytest
from backend.app.analysis.scoring import ScoringEngine
from backend.app.analysis.recommendation import RecommendationEngine
from backend.app.schemas.analysis import EvidenceItemSchema


def test_scoring_engine_additive_weights():
    items = [
        EvidenceItemSchema(weight=3, description="DNS degradation", metric_name="dns_latency_ms"),
        EvidenceItemSchema(weight=2, description="HTTP latency > P95", metric_name="http_latency_ms"),
        EvidenceItemSchema(weight=1, description="Nominal lower layer", metric_name="tcp_connect"),
    ]
    score = ScoringEngine.calculate_score(items)
    assert score == 6


def test_recommendation_engine_categories():
    engine = RecommendationEngine()
    recs_dns = engine.generate("DNS_FAILURE", "DNS", "DNS failed")
    assert len(recs_dns) >= 3
    assert any("dig" in r.action_text or "nameserver" in r.action_text for r in recs_dns)

    recs_http_lat = engine.generate("HTTP_APPLICATION_LATENCY", "HTTP", "Slow app")
    assert len(recs_http_lat) >= 3
    assert any("APM" in r.action_text or "thread" in r.action_text for r in recs_http_lat)

    recs_tcp = engine.generate("TCP_CONNECTIVITY_FAILURE", "TCP", "Port dead")
    assert any("ss -tulpn" in r.action_text for r in recs_tcp)
