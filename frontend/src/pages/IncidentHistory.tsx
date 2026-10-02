import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { DiagnosticSessionDetail } from '../types/diagnostic';
import { StatusBadge } from '../components/StatusBadge';
import { History, Search, RefreshCw, Filter } from 'lucide-react';

interface IncidentHistoryProps {
  onSelectSession: (sessionId: string) => void;
}

export const IncidentHistory: React.FC<IncidentHistoryProps> = ({ onSelectSession }) => {
  const [sessions, setSessions] = useState<DiagnosticSessionDetail[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [severityFilter, setSeverityFilter] = useState('ALL');
  const [isLoading, setIsLoading] = useState(true);

  const loadSessions = async () => {
    setIsLoading(true);
    try {
      const data = await api.listDiagnostics(50);
      setSessions(data);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadSessions();
  }, []);

  const filteredSessions = sessions.filter((s) => {
    const matchesSearch =
      s.target.url.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (s.diagnosis?.category.toLowerCase() || '').includes(searchQuery.toLowerCase()) ||
      s.correlation_id.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesSeverity =
      severityFilter === 'ALL' || (s.diagnosis?.severity.toUpperCase() === severityFilter.toUpperCase());

    return matchesSearch && matchesSeverity;
  });

  return (
    <div className="space-y-6 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <History className="w-6 h-6 text-cyan-400" /> Incident Replay Log
          </h1>
          <p className="text-sm text-slate-400">
            Historical diagnostic runs, original telemetry, baseline snapshots, and root-cause attributions.
          </p>
        </div>

        <button
          onClick={loadSessions}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 border border-slate-700 self-start sm:self-auto"
        >
          <RefreshCw className="w-3.5 h-3.5" /> Refresh
        </button>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-col sm:flex-row gap-3 p-4 rounded-xl bg-[#0b1324] border border-slate-800/80">
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by URL, diagnosis, or correlation ID..."
            className="w-full pl-9 pr-4 py-2 rounded-lg bg-slate-900 border border-slate-700 text-xs text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-cyan-500 font-mono"
          />
        </div>

        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-slate-400" />
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-cyan-500 font-semibold"
          >
            <option value="ALL">All Severities</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
            <option value="INFO">Nominal (Info)</option>
          </select>
        </div>
      </div>

      {/* Sessions Table */}
      <div className="bg-[#0b1324] border border-slate-800/80 rounded-xl overflow-hidden shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 uppercase font-mono bg-slate-900/40">
                <th className="py-3 px-4">Correlation ID / Target</th>
                <th className="py-3 px-3">Status</th>
                <th className="py-3 px-3">Root Cause Diagnosis</th>
                <th className="py-3 px-3 text-center">Score</th>
                <th className="py-3 px-3">Duration</th>
                <th className="py-3 px-3">Timestamp</th>
                <th className="py-3 px-4 text-right">Replay</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-sans">
              {isLoading ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-500">
                    <RefreshCw className="w-5 h-5 text-cyan-400 animate-spin mx-auto mb-2" />
                    Loading incident replays...
                  </td>
                </tr>
              ) : filteredSessions.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-500">
                    No historical incidents match the current filters.
                  </td>
                </tr>
              ) : (
                filteredSessions.map((session) => (
                  <tr key={session.id} className="hover:bg-slate-900/50 transition-colors">
                    <td className="py-3.5 px-4 font-mono">
                      <div className="text-cyan-400 font-semibold text-[11px]">{session.correlation_id}</div>
                      <div className="text-slate-300 font-medium truncate max-w-sm">{session.target.url}</div>
                    </td>
                    <td className="py-3.5 px-3">
                      <StatusBadge status={session.status} />
                    </td>
                    <td className="py-3.5 px-3">
                      {session.diagnosis ? (
                        <div className="flex items-center gap-2">
                          <StatusBadge status={session.diagnosis.severity} />
                          <span className="font-mono font-semibold text-slate-200">
                            {session.diagnosis.category}
                          </span>
                        </div>
                      ) : (
                        <span className="text-slate-500 italic">None</span>
                      )}
                    </td>
                    <td className="py-3.5 px-3 text-center font-mono font-bold text-cyan-400">
                      {session.diagnosis ? session.diagnosis.evidence_score : '-'}
                    </td>
                    <td className="py-3.5 px-3 font-mono text-slate-400">
                      {session.duration_ms ? `${session.duration_ms.toFixed(0)} ms` : '-'}
                    </td>
                    <td className="py-3.5 px-3 font-mono text-slate-400">
                      {new Date(session.started_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'medium' })}
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <button
                        onClick={() => onSelectSession(session.id)}
                        className="px-3 py-1 rounded bg-slate-800 hover:bg-cyan-900/40 hover:text-cyan-300 text-slate-300 transition-colors border border-slate-700 font-semibold"
                      >
                        Open Replay
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
