from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from backend.app.analysis.baseline import BaselineEngine
from backend.app.analysis.anomaly import AnomalyEngine
from backend.app.analysis.correlation import CorrelationEngine
from backend.app.analysis.scoring import ScoringEngine
from backend.app.analysis.recommendation import RecommendationEngine
from backend.app.schemas.analysis import (
    DiagnosisSchema,
    DependencyGraphNode,
    DependencyGraphEdge,
    DependencyGraphResponse,
    IncidentTimelineEventSchema,
)

logger = logging.getLogger("netpath.analysis.diagnosis")


class DiagnosisEngine:
    """
    Main deterministic root-cause diagnosis engine combining collectors output,
    historical baselines, anomaly detection, multi-layer correlation, and scoring.
    """

    def __init__(self) -> None:
        self.baseline_engine = BaselineEngine()
        self.anomaly_engine = AnomalyEngine()
        self.correlation_engine = CorrelationEngine()
        self.scoring_engine = ScoringEngine()
        self.recommendation_engine = RecommendationEngine()

    def diagnose(
        self,
        db: Session,
        target_id: int,
        dns_res: Optional[Dict[str, Any]],
        tcp_res: Optional[Dict[str, Any]],
        tls_res: Optional[Dict[str, Any]],
        http_res: Optional[Dict[str, Any]],
        network_hops: List[Dict[str, Any]],
        system_metric: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Executes complete deterministic diagnosis pipeline.
        Returns dictionary with:
        - diagnosis (DiagnosisSchema)
        - anomalies (List[AnomalySchema])
        - dependency_graph (DependencyGraphResponse)
        """
        # 1. Fetch historical baselines
        baselines = self.baseline_engine.get_target_baselines(db, target_id)

        # 2. Detect multi-layer anomalies
        anomalies = self.anomaly_engine.detect_anomalies(
            dns_res=dns_res,
            tcp_res=tcp_res,
            tls_res=tls_res,
            http_res=http_res,
            network_hops=network_hops,
            system_metric=system_metric,
            baselines=baselines,
        )

        # 3. Correlate across layers
        category, severity, affected_layer, summary, evidence_items = (
            self.correlation_engine.correlate(
                dns_res=dns_res,
                tcp_res=tcp_res,
                tls_res=tls_res,
                http_res=http_res,
                network_hops=network_hops,
                system_metric=system_metric,
                anomalies=anomalies,
            )
        )

        # 4. Calculate explainable Evidence Score
        evidence_score = self.scoring_engine.calculate_score(evidence_items)

        # 5. Generate actionable recommendations
        recommendations = self.recommendation_engine.generate(
            category=category,
            affected_layer=affected_layer,
            summary=summary,
        )

        diagnosis_schema = DiagnosisSchema(
            category=category,
            severity=severity,
            evidence_score=evidence_score,
            affected_layer=affected_layer,
            summary=summary,
            evidence_items=evidence_items,
            recommendations=recommendations,
        )

        # 6. Generate Dependency Graph
        dep_graph = self.build_dependency_graph(
            dns_res=dns_res,
            tcp_res=tcp_res,
            tls_res=tls_res,
            http_res=http_res,
            network_hops=network_hops,
            system_metric=system_metric,
            diagnosis=diagnosis_schema,
        )

        return {
            "diagnosis": diagnosis_schema,
            "anomalies": anomalies,
            "dependency_graph": dep_graph,
            "baselines": baselines,
        }

    def build_dependency_graph(
        self,
        dns_res: Optional[Dict[str, Any]],
        tcp_res: Optional[Dict[str, Any]],
        tls_res: Optional[Dict[str, Any]],
        http_res: Optional[Dict[str, Any]],
        network_hops: List[Dict[str, Any]],
        system_metric: Optional[Dict[str, Any]],
        diagnosis: DiagnosisSchema,
    ) -> DependencyGraphResponse:
        """Constructs DAG nodes and edges representing the full network request path."""
        nodes: List[DependencyGraphNode] = []
        edges: List[DependencyGraphEdge] = []

        # Client Node
        nodes.append(
            DependencyGraphNode(
                id="client",
                label="Client Agent",
                layer="Client",
                status="NORMAL",
                details={"host": "NetPath Engine"},
            )
        )

        # DNS Node
        dns_status = "NORMAL"
        if dns_res:
            if dns_res.get("status") == "DNS_FAILURE":
                dns_status = "FAILED"
            elif dns_res.get("status") == "DNS_DEGRADATION":
                dns_status = "DEGRADED"
        else:
            dns_status = "UNKNOWN"

        nodes.append(
            DependencyGraphNode(
                id="dns",
                label="DNS Resolver",
                layer="DNS",
                status=dns_status,
                details=dns_res or {},
            )
        )
        edges.append(DependencyGraphEdge(source="client", target="dns", label="Query"))

        # Destination IP Node
        dest_ip = (tcp_res or {}).get("destination_ip") or ((dns_res or {}).get("addresses") or ["Unresolved"])[0]
        nodes.append(
            DependencyGraphNode(
                id="destination_ip",
                label=f"IP: {dest_ip}",
                layer="Network",
                status="FAILED" if dns_status == "FAILED" else "NORMAL",
                details={"ip": dest_ip},
            )
        )
        edges.append(DependencyGraphEdge(source="dns", target="destination_ip", label="Resolved"))

        # TCP Node
        tcp_status = "NORMAL"
        if tcp_res:
            if tcp_res.get("status") == "TCP_CONNECTIVITY_FAILURE":
                tcp_status = "FAILED"
            elif tcp_res.get("status") == "TCP_DEGRADATION":
                tcp_status = "DEGRADED"
        elif dns_status == "FAILED":
            tcp_status = "UNKNOWN"

        nodes.append(
            DependencyGraphNode(
                id="tcp",
                label="TCP Handshake",
                layer="TCP",
                status=tcp_status,
                details=tcp_res or {},
            )
        )
        edges.append(DependencyGraphEdge(source="destination_ip", target="tcp", label="SYN/ACK"))

        prev_node = "tcp"

        # TLS Node (if present/HTTPS)
        if tls_res:
            tls_status = "NORMAL"
            if tls_res.get("status") == "TLS_FAILURE":
                tls_status = "FAILED"
            elif tls_res.get("status") == "TLS_CERTIFICATE_EXPIRING":
                tls_status = "DEGRADED"
            elif tcp_status == "FAILED":
                tls_status = "UNKNOWN"

            nodes.append(
                DependencyGraphNode(
                    id="tls",
                    label="TLS Handshake",
                    layer="TLS",
                    status=tls_status,
                    details=tls_res or {},
                )
            )
            edges.append(DependencyGraphEdge(source=prev_node, target="tls", label="SSL Wrap"))
            prev_node = "tls"

        # HTTP Node
        http_status = "NORMAL"
        if http_res:
            if http_res.get("status") == "HTTP_APPLICATION_ERROR":
                http_status = "FAILED"
            elif http_res.get("status") == "HTTP_APPLICATION_LATENCY":
                http_status = "DEGRADED"
        elif tcp_status == "FAILED" or dns_status == "FAILED":
            http_status = "UNKNOWN"

        nodes.append(
            DependencyGraphNode(
                id="http",
                label="HTTP Application",
                layer="HTTP",
                status=http_status,
                details=http_res or {},
            )
        )
        edges.append(DependencyGraphEdge(source=prev_node, target="http", label="Request/Response"))

        return DependencyGraphResponse(nodes=nodes, edges=edges)
