import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { DiagnosticSessionDetail, DependencyGraphResponse } from '../types/diagnostic';
import { StatusBadge } from '../components/StatusBadge';
import { DependencyGraph } from '../components/DependencyGraph';
import { EvidenceCard } from '../components/EvidenceCard';
import { RecommendationPanel } from '../components/RecommendationPanel';
import { IncidentTimeline } from '../components/IncidentTimeline';
import { MetricsChart } from '../components/MetricsChart';
import { ArrowLeft, RefreshCw, Cpu, Server, Network, Shield, Clock } from 'lucide-react';

interface DiagnosticDetailProps {
  sessionId: string;
  onBack: () => void;
}

export const DiagnosticDetail: React.FC<DiagnosticDetailProps> = ({ sessionId, onBack }) => {
  const [session, setSession] = useState<DiagnosticSessionDetail | null>(null);
  const [graphData, setGraphData] = useState<DependencyGraphResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const loadSession = async () => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const [sData, gData] = await Promise.all([
        api.getDiagnostic(sessionId),
        api.getGraph(sessionId).catch(() => ({ nodes: [], edges: [] })),
      ]);
      setSession(sData);
      setGraphData(gData);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to load diagnostic session');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadSession();
  }, [sessionId]);

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
        <RefreshCw className="w-8 h-8 text-cyan-400 animate-spin" />
        <p className="text-sm text-slate-400">Loading diagnostic replay session...</p>
      </div>
    );
  }

  if (errorMsg || !session) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-8 space-y-4">
        <button onClick={onBack} className="flex items-center gap-2 text-xs text-slate-400 hover:text-white">
          <ArrowLeft className="w-4 h-4" /> Back
        </button>
        <div className="p-6 rounded-xl bg-rose-950/20 border border-rose-800/40 text-rose-300">
          <h3 className="font-bold text-base mb-1">Session Not Found or Load Error</h3>
          <p className="text-xs">{errorMsg || 'Could not retrieve session details.'}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Top Header & Breadcrumbs */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800/80 pb-5">
        <div className="space-y-1">
          <button
            onClick={onBack}
            className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-cyan-400 transition-colors mb-2"
          >
            <ArrowLeft className="w-3.5 h-3.5" /> Back to Dashboard
          </button>
          <div className="flex items-center gap-3">
            <h1 className="text-xl md:text-2xl font-bold font-mono text-white tracking-tight">
              {session.target.url}
            </h1>
            <StatusBadge status={session.status} />
          </div>
          <div className="flex flex-wrap items-center gap-3 text-xs text-slate-400 font-mono mt-1">
            <span>Session: {session.id.slice(0, 8)}</span>
            <span>•</span>
            <span>Correlation ID: {session.correlation_id}</span>
            <span>•</span>
            <span>Duration: {session.duration_ms ? `${session.duration_ms.toFixed(0)} ms` : '-'}</span>
            <span>•</span>
            <span>Probed: {new Date(session.started_at).toLocaleString()}</span>
          </div>
        </div>

        <button
          onClick={loadSession}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 border border-slate-700 self-start sm:self-auto"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Refresh Replay</span>
        </button>
      </div>

      {/* 1. Request Path Dependency Graph */}
      {graphData && graphData.nodes.length > 0 && (
        <DependencyGraph nodes={graphData.nodes} edges={graphData.edges} />
      )}

      {/* 2. Deterministic Root Cause & Evidence Score */}
      <EvidenceCard diagnosis={session.diagnosis} anomalies={session.anomalies} />

      {/* 3. Actionable Recommendations */}
      {session.diagnosis && session.diagnosis.recommendations.length > 0 && (
        <RecommendationPanel recommendations={session.diagnosis.recommendations} />
      )}

      {/* 4. Layer Latency Chart & Network Path Hops */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <MetricsChart
          dns={session.dns_result}
          tcp={session.tcp_result}
          tls={session.tls_result}
          http={session.http_result}
        />

        {/* Network Path Hops Table */}
        <div className="bg-[#0b1324] border border-slate-800/80 rounded-xl p-5 shadow-xl">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
                <Network className="w-4 h-4 text-indigo-400" /> Network Path Hops
              </h3>
              <p className="text-xs text-slate-400">Intermediate routing hops and loss statistics</p>
            </div>
            <span className="text-xs font-mono text-slate-400">
              {session.network_hops.length} Hops
            </span>
          </div>

          <div className="overflow-x-auto max-h-60">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 font-mono">
                  <th className="py-2 px-2">Hop</th>
                  <th className="py-2 px-2">IP / Host</th>
                  <th className="py-2 px-2">RTT</th>
                  <th className="py-2 px-2">Packet Loss</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {session.network_hops.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="py-4 text-center text-slate-500 font-sans">
                      No intermediate hops recorded.
                    </td>
                  </tr>
                ) : (
                  session.network_hops.map((hop) => (
                    <tr key={hop.hop_number} className="hover:bg-slate-900/40">
                      <td className="py-2 px-2 font-bold text-cyan-400">#{hop.hop_number}</td>
                      <td className="py-2 px-2 text-slate-200">
                        {hop.is_timeout ? (
                          <span className="text-slate-500 italic">* * * (Timeout / Filtered)</span>
                        ) : (
                          hop.ip_address || hop.hostname || 'Responsive'
                        )}
                      </td>
                      <td className="py-2 px-2">
                        {hop.rtt_ms !== null ? `${hop.rtt_ms.toFixed(1)} ms` : '-'}
                      </td>
                      <td className="py-2 px-2">
                        {hop.packet_loss_pct > 0 ? (
                          <span className="text-rose-400 font-bold">{hop.packet_loss_pct}%</span>
                        ) : (
                          <span className="text-emerald-400">0%</span>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* 5. Host Linux Telemetry & Incident Timeline */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Host Telemetry */}
        <div className="bg-[#0b1324] border border-slate-800/80 rounded-xl p-5 shadow-xl space-y-4">
          <div>
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
              <Cpu className="w-4 h-4 text-cyan-400" /> Host System Telemetry
            </h3>
            <p className="text-xs text-slate-400">Local node resources during probe</p>
          </div>

          {session.system_metric ? (
            <div className="space-y-3 text-xs font-mono">
              <div className="flex items-center justify-between p-2 rounded bg-slate-900/60 border border-slate-800">
                <span className="text-slate-400">CPU Utilization</span>
                <span className={`font-bold ${session.system_metric.cpu_pct > 80 ? 'text-rose-400' : 'text-slate-200'}`}>
                  {session.system_metric.cpu_pct}%
                </span>
              </div>

              <div className="flex items-center justify-between p-2 rounded bg-slate-900/60 border border-slate-800">
                <span className="text-slate-400">Memory Utilization</span>
                <span className={`font-bold ${session.system_metric.memory_pct > 80 ? 'text-rose-400' : 'text-slate-200'}`}>
                  {session.system_metric.memory_pct}%
                </span>
              </div>

              <div className="flex items-center justify-between p-2 rounded bg-slate-900/60 border border-slate-800">
                <span className="text-slate-400">Load Average (1m / 5m)</span>
                <span className="text-slate-200 font-bold">
                  {session.system_metric.load_1m} / {session.system_metric.load_5m}
                </span>
              </div>

              <div className="flex items-center justify-between p-2 rounded bg-slate-900/60 border border-slate-800">
                <span className="text-slate-400">Interface Errors (In/Out)</span>
                <span className={`font-bold ${session.system_metric.net_errin > 0 ? 'text-rose-400' : 'text-slate-200'}`}>
                  {session.system_metric.net_errin} / {session.system_metric.net_errout}
                </span>
              </div>

              <div className="flex items-center justify-between p-2 rounded bg-slate-900/60 border border-slate-800">
                <span className="text-slate-400">Interface Drops (In/Out)</span>
                <span className={`font-bold ${session.system_metric.net_dropin > 0 ? 'text-amber-400' : 'text-slate-200'}`}>
                  {session.system_metric.net_dropin} / {session.system_metric.net_dropout}
                </span>
              </div>
            </div>
          ) : (
            <div className="text-xs text-slate-500 italic">No host metrics recorded.</div>
          )}
        </div>

        {/* Timeline Events */}
        <div className="lg:col-span-2">
          <IncidentTimeline events={session.timeline_events} />
        </div>
      </div>
    </div>
  );
};
