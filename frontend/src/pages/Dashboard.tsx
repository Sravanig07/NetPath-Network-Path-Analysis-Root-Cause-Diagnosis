import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { TargetStatusSummary, DiagnosticSessionDetail } from '../types/diagnostic';
import { StatusBadge } from '../components/StatusBadge';
import { Activity, ShieldAlert, CheckCircle2, ArrowRight, Play, Loader2, Sparkles, Server } from 'lucide-react';

interface DashboardProps {
  onSelectSession: (sessionId: string) => void;
  onNavigateTab: (tab: string) => void;
}

export const Dashboard: React.FC<DashboardProps> = ({ onSelectSession, onNavigateTab }) => {
  const [urlInput, setUrlInput] = useState('');
  const [isRunning, setIsRunning] = useState(false);
  const [targets, setTargets] = useState<TargetStatusSummary[]>([]);
  const [recentSessions, setRecentSessions] = useState<DiagnosticSessionDetail[]>([]);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const loadData = async () => {
    try {
      const [tList, sList] = await Promise.all([
        api.listTargets().catch(() => []),
        api.listDiagnostics(10).catch(() => []),
      ]);
      setTargets(tList);
      setRecentSessions(sList);
    } catch (err: any) {
      console.error('Error loading dashboard data:', err);
    }
  };

  useEffect(() => {
    loadData();
    const timer = setInterval(loadData, 5000);
    return () => clearInterval(timer);
  }, []);

  const handleRunDiagnostic = async (targetUrl?: string) => {
    const target = targetUrl || urlInput;
    if (!target) return;
    setIsRunning(true);
    setErrorMsg(null);
    try {
      // Synchronously wait for diagnostic so user immediately sees results
      const res = await api.createDiagnostic(target, true);
      setIsRunning(false);
      setUrlInput('');
      onSelectSession(res.session_id);
    } catch (err: any) {
      setIsRunning(false);
      setErrorMsg(err.message || 'Diagnostic execution failed');
    }
  };

  // KPI calculations
  const totalSessions = recentSessions.length;
  const healthyCount = targets.filter(t => t.latest_status === 'COMPLETED' && (!t.latest_severity || t.latest_severity === 'INFO' || t.latest_severity === 'LOW')).length;
  const degradedCount = targets.filter(t => t.latest_severity === 'MEDIUM' || t.latest_severity === 'HIGH').length;
  const criticalCount = targets.filter(t => t.latest_severity === 'CRITICAL' || t.latest_status === 'FAILED').length;

  return (
    <div className="space-y-8 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Hero Quick Probe Bar */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-slate-900 via-[#0d1627] to-slate-900 border border-cyan-500/20 p-6 md:p-8 shadow-2xl">
        <div className="max-w-3xl space-y-3 mb-6">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 text-xs font-semibold">
            <Sparkles className="w-3.5 h-3.5" /> Deterministic Root-Cause Engine Active
          </div>
          <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight text-white">
            Analyze Network Path & Diagnose Root Cause
          </h1>
          <p className="text-sm text-slate-300">
            Dissect target endpoints through DNS, TCP handshake, TLS negotiation, HTTP latency, intermediate network hops, and host system telemetry.
          </p>
        </div>

        {/* Input Bar */}
        <div className="flex flex-col sm:flex-row items-center gap-3 max-w-3xl">
          <div className="relative flex-1 w-full">
            <input
              type="text"
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
              placeholder="e.g. https://example.com or http://test-service-a:8001/slow"
              className="w-full px-4 py-3 rounded-xl bg-slate-950/80 border border-slate-700/80 text-white placeholder-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500 font-mono shadow-inner"
              onKeyDown={(e) => e.key === 'Enter' && handleRunDiagnostic()}
            />
          </div>
          <button
            onClick={() => handleRunDiagnostic()}
            disabled={isRunning || !urlInput.trim()}
            className="w-full sm:w-auto px-6 py-3 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-semibold text-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-cyan-500/25 flex items-center justify-center gap-2 shrink-0"
          >
            {isRunning ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Diagnosing Layers...</span>
              </>
            ) : (
              <>
                <Play className="w-4 h-4 fill-current" />
                <span>Run Diagnostic</span>
              </>
            )}
          </button>
        </div>

        {errorMsg && (
          <div className="mt-3 text-xs text-rose-400 bg-rose-950/30 border border-rose-800/40 p-2.5 rounded-lg max-w-3xl">
            {errorMsg}
          </div>
        )}

        {/* Quick Launch Shortcuts */}
        <div className="flex flex-wrap items-center gap-2 mt-4 text-xs text-slate-400">
          <span>Quick Lab Probes:</span>
          <button
            onClick={() => handleRunDiagnostic('http://localhost:8001/slow?delay=2')}
            className="px-2.5 py-1 rounded bg-slate-800/80 hover:bg-slate-700 border border-slate-700 font-mono text-cyan-300"
          >
            test-service-a /slow (Latency)
          </button>
          <button
            onClick={() => handleRunDiagnostic('http://localhost:8002/error?code=500')}
            className="px-2.5 py-1 rounded bg-slate-800/80 hover:bg-slate-700 border border-slate-700 font-mono text-rose-300"
          >
            test-service-b /error (500)
          </button>
          <button
            onClick={() => handleRunDiagnostic('https://google.com')}
            className="px-2.5 py-1 rounded bg-slate-800/80 hover:bg-slate-700 border border-slate-700 font-mono text-emerald-300"
          >
            https://google.com
          </button>
        </div>
      </div>

      {/* KPI Stat Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-5 rounded-xl bg-[#0b1324] border border-slate-800/80 shadow-lg">
          <div className="flex items-center justify-between">
            <span className="text-xs uppercase font-mono text-slate-400">Monitored Targets</span>
            <Server className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-3xl font-extrabold text-white mt-2 font-mono">{targets.length}</div>
          <span className="text-[11px] text-slate-500">Configured endpoints</span>
        </div>

        <div className="p-5 rounded-xl bg-[#0b1324] border border-slate-800/80 shadow-lg">
          <div className="flex items-center justify-between">
            <span className="text-xs uppercase font-mono text-slate-400">Healthy Targets</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-3xl font-extrabold text-emerald-400 mt-2 font-mono">{healthyCount}</div>
          <span className="text-[11px] text-slate-500">Nominal performance</span>
        </div>

        <div className="p-5 rounded-xl bg-[#0b1324] border border-slate-800/80 shadow-lg">
          <div className="flex items-center justify-between">
            <span className="text-xs uppercase font-mono text-slate-400">Degraded Targets</span>
            <Activity className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-3xl font-extrabold text-amber-400 mt-2 font-mono">{degradedCount}</div>
          <span className="text-[11px] text-slate-500">Latency / Expiring certs</span>
        </div>

        <div className="p-5 rounded-xl bg-[#0b1324] border border-slate-800/80 shadow-lg">
          <div className="flex items-center justify-between">
            <span className="text-xs uppercase font-mono text-slate-400">Critical Outages</span>
            <ShieldAlert className="w-4 h-4 text-rose-400" />
          </div>
          <div className="text-3xl font-extrabold text-rose-400 mt-2 font-mono">{criticalCount}</div>
          <span className="text-[11px] text-slate-500">Active root causes</span>
        </div>
      </div>

      {/* Recent Diagnostic Sessions Table */}
      <div className="bg-[#0b1324] border border-slate-800/80 rounded-xl p-5 shadow-xl">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate-200">
              Recent Diagnostic Sessions
            </h3>
            <p className="text-xs text-slate-400">Deterministic root-cause results and historical records</p>
          </div>
          <button
            onClick={() => onNavigateTab('history')}
            className="text-xs text-cyan-400 hover:text-cyan-300 font-semibold flex items-center gap-1"
          >
            <span>View All Replays</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 uppercase font-mono">
                <th className="py-3 px-3">Target Endpoint</th>
                <th className="py-3 px-3">Status</th>
                <th className="py-3 px-3">Root Cause Diagnosis</th>
                <th className="py-3 px-3 text-center">Score</th>
                <th className="py-3 px-3">Duration</th>
                <th className="py-3 px-3">Timestamp</th>
                <th className="py-3 px-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-sans">
              {recentSessions.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-6 text-center text-slate-500">
                    No diagnostic sessions yet. Trigger a diagnostic above to begin analysis!
                  </td>
                </tr>
              ) : (
                recentSessions.map((session) => (
                  <tr key={session.id} className="hover:bg-slate-900/50 transition-colors">
                    <td className="py-3 px-3 font-mono font-medium text-slate-200 truncate max-w-xs">
                      {session.target.url}
                    </td>
                    <td className="py-3 px-3">
                      <StatusBadge status={session.status} />
                    </td>
                    <td className="py-3 px-3">
                      {session.diagnosis ? (
                        <div className="flex items-center gap-2">
                          <StatusBadge status={session.diagnosis.severity} />
                          <span className="font-mono font-semibold text-slate-200">
                            {session.diagnosis.category}
                          </span>
                        </div>
                      ) : (
                        <span className="text-slate-500 italic">Pending analysis</span>
                      )}
                    </td>
                    <td className="py-3 px-3 text-center font-mono font-bold text-cyan-400">
                      {session.diagnosis ? session.diagnosis.evidence_score : '-'}
                    </td>
                    <td className="py-3 px-3 font-mono text-slate-400">
                      {session.duration_ms ? `${session.duration_ms.toFixed(0)} ms` : '-'}
                    </td>
                    <td className="py-3 px-3 text-slate-400 font-mono">
                      {new Date(session.started_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                    </td>
                    <td className="py-3 px-3 text-right">
                      <button
                        onClick={() => onSelectSession(session.id)}
                        className="px-2.5 py-1 rounded bg-slate-800 hover:bg-cyan-900/40 hover:text-cyan-300 text-slate-300 transition-colors border border-slate-700 font-semibold"
                      >
                        Inspect RCA
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
