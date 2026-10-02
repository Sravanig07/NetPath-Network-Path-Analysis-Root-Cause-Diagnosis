export interface Target {
  id: number;
  url: string;
  hostname: string;
  port: number;
  scheme: string;
  path: string;
  created_at: string;
  updated_at: string;
}

export interface TargetStatusSummary {
  target: Target;
  total_sessions: number;
  latest_status: string;
  latest_diagnosis: string | null;
  latest_severity: string | null;
  dns_status: string;
  tcp_status: string;
  tls_status: string;
  http_status: string;
  network_status: string;
  system_status: string;
  last_diagnosed_at: string | null;
}

export interface DnsResult {
  resolver: string;
  latency_ms: number;
  record_type: string;
  addresses: string[];
  status: string;
  error_message: string | null;
}

export interface TcpResult {
  destination_ip: string;
  destination_port: number;
  connect_latency_ms: number;
  status: string;
  error_message: string | null;
}

export interface TlsResult {
  tls_version: string | null;
  cipher: string | null;
  cert_subject: string | null;
  cert_issuer: string | null;
  cert_expires_at: string | null;
  days_to_expiration: number | null;
  handshake_latency_ms: number;
  is_valid: boolean;
  status: string;
  error_message: string | null;
}

export interface HttpResult {
  status_code: number | null;
  ttfb_ms: number;
  total_latency_ms: number;
  response_bytes: number;
  redirect_count: number;
  headers: Record<string, any> | null;
  status: string;
  error_message: string | null;
}

export interface NetworkHop {
  hop_number: number;
  ip_address: string | null;
  hostname: string | null;
  rtt_ms: number | null;
  is_timeout: boolean;
  packet_loss_pct: number;
}

export interface SystemMetric {
  cpu_pct: number;
  memory_pct: number;
  load_1m: number;
  load_5m: number;
  load_15m: number;
  net_bytes_sent: number;
  net_bytes_recv: number;
  net_errin: number;
  net_errout: number;
  net_dropin: number;
  net_dropout: number;
  status: string;
}

export interface Anomaly {
  id?: number;
  metric_name: string;
  observed_value: number;
  expected_value: number | null;
  baseline_reference: string | null;
  severity: string;
  rule_triggered: string;
  evidence_text: string;
  created_at?: string;
}

export interface EvidenceItem {
  id?: number;
  weight: number;
  description: string;
  metric_name: string | null;
}

export interface Recommendation {
  id?: number;
  action_order: number;
  action_text: string;
}

export interface Diagnosis {
  category: string;
  severity: string;
  evidence_score: number;
  affected_layer: string;
  summary: string;
  created_at?: string;
  evidence_items: EvidenceItem[];
  recommendations: Recommendation[];
}

export interface IncidentTimelineEvent {
  id?: number;
  timestamp: string;
  event_type: string;
  layer: string;
  message: string;
  status: string;
}

export interface DiagnosticSessionDetail {
  id: string;
  target: Target;
  correlation_id: string;
  status: string;
  started_at: string;
  completed_at: string | null;
  duration_ms: number | null;
  error_message: string | null;

  dns_result: DnsResult | null;
  tcp_result: TcpResult | null;
  tls_result: TlsResult | null;
  http_result: HttpResult | null;
  network_hops: NetworkHop[];
  system_metric: SystemMetric | null;

  anomalies: Anomaly[];
  diagnosis: Diagnosis | null;
  timeline_events: IncidentTimelineEvent[];
}

export interface DependencyGraphNode {
  id: string;
  label: string;
  layer: string;
  status: 'NORMAL' | 'DEGRADED' | 'FAILED' | 'UNKNOWN';
  details: Record<string, any>;
}

export interface DependencyGraphEdge {
  source: string;
  target: string;
  label?: string;
}

export interface DependencyGraphResponse {
  nodes: DependencyGraphNode[];
  edges: DependencyGraphEdge[];
}

export interface MetricPercentileStats {
  metric_name: string;
  count: number;
  min: number;
  max: number;
  mean: number;
  median: number;
  p50: number;
  p95: number;
  p99: number;
  std_dev: number;
  is_sufficient_evidence: boolean;
}

export interface TargetBaselineResponse {
  target_id: number;
  url: string;
  hostname: string;
  sample_count: number;
  metrics: Record<string, MetricPercentileStats>;
}
