import {
  Target,
  TargetStatusSummary,
  DiagnosticSessionDetail,
  DependencyGraphResponse,
  TargetBaselineResponse,
  IncidentTimelineEvent,
  Diagnosis,
  EvidenceItem,
  Recommendation,
} from '../types/diagnostic';

const API_BASE = '/api/v1';

export const api = {
  // Diagnostics
  createDiagnostic: async (url: string, wait = false): Promise<{ session_id: string; correlation_id: string; status: string }> => {
    const res = await fetch(`${API_BASE}/diagnostics`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url, wait }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Diagnostic request failed' }));
      throw new Error(err.detail || 'Failed to trigger diagnostic');
    }
    return res.json();
  },

  getDiagnostic: async (sessionId: string): Promise<DiagnosticSessionDetail> => {
    const res = await fetch(`${API_BASE}/diagnostics/${sessionId}`);
    if (!res.ok) throw new Error('Failed to fetch diagnostic session');
    return res.json();
  },

  listDiagnostics: async (limit = 20, targetId?: number): Promise<DiagnosticSessionDetail[]> => {
    const params = new URLSearchParams({ limit: String(limit) });
    if (targetId) params.append('target_id', String(targetId));
    const res = await fetch(`${API_BASE}/diagnostics?${params.toString()}`);
    if (!res.ok) throw new Error('Failed to list diagnostic sessions');
    return res.json();
  },

  getTimeline: async (sessionId: string): Promise<IncidentTimelineEvent[]> => {
    const res = await fetch(`${API_BASE}/diagnostics/${sessionId}/timeline`);
    if (!res.ok) throw new Error('Failed to fetch session timeline');
    return res.json();
  },

  getGraph: async (sessionId: string): Promise<DependencyGraphResponse> => {
    const res = await fetch(`${API_BASE}/diagnostics/${sessionId}/graph`);
    if (!res.ok) throw new Error('Failed to fetch session graph');
    return res.json();
  },

  getDiagnosis: async (sessionId: string): Promise<Diagnosis> => {
    const res = await fetch(`${API_BASE}/diagnostics/${sessionId}/diagnosis`);
    if (!res.ok) throw new Error('Failed to fetch diagnosis');
    return res.json();
  },

  getEvidence: async (sessionId: string): Promise<EvidenceItem[]> => {
    const res = await fetch(`${API_BASE}/diagnostics/${sessionId}/evidence`);
    if (!res.ok) throw new Error('Failed to fetch evidence');
    return res.json();
  },

  getRecommendations: async (sessionId: string): Promise<Recommendation[]> => {
    const res = await fetch(`${API_BASE}/diagnostics/${sessionId}/recommendations`);
    if (!res.ok) throw new Error('Failed to fetch recommendations');
    return res.json();
  },

  // Targets
  listTargets: async (): Promise<TargetStatusSummary[]> => {
    const res = await fetch(`${API_BASE}/targets`);
    if (!res.ok) throw new Error('Failed to fetch targets');
    return res.json();
  },

  createTarget: async (url: string): Promise<Target> => {
    const res = await fetch(`${API_BASE}/targets`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to create target' }));
      throw new Error(err.detail || 'Target creation failed');
    }
    return res.json();
  },

  // Metrics & Baselines
  getBaselines: async (targetId: number): Promise<TargetBaselineResponse> => {
    const res = await fetch(`${API_BASE}/metrics/baselines/${targetId}`);
    if (!res.ok) throw new Error('Failed to fetch baselines');
    return res.json();
  },

  getMetricHistory: async (targetId: number, metricName: string, limit = 50) => {
    const res = await fetch(`${API_BASE}/metrics/history/${targetId}?metric_name=${metricName}&limit=${limit}`);
    if (!res.ok) throw new Error('Failed to fetch metric history');
    return res.json();
  },
};
