import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { TargetStatusSummary } from '../types/diagnostic';
import { StatusBadge } from '../components/StatusBadge';
import { Server, Play, RefreshCw, Plus, Globe } from 'lucide-react';

interface TargetViewProps {
  onSelectSession: (sessionId: string) => void;
  onViewBaselines: (targetId: number) => void;
}

export const TargetView: React.FC<TargetViewProps> = ({ onSelectSession, onViewBaselines }) => {
  const [targets, setTargets] = useState<TargetStatusSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [newUrl, setNewUrl] = useState('');
  const [triggeringUrl, setTriggeringUrl] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const loadTargets = async () => {
    setIsLoading(true);
    try {
      const data = await api.listTargets();
      setTargets(data);
    } catch (err: any) {
      setErrorMsg(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadTargets();
  }, []);

  const handleAddTarget = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newUrl.trim()) return;
    setErrorMsg(null);
    try {
      await api.createTarget(newUrl.trim());
      setNewUrl('');
      loadTargets();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to add target');
    }
  };

  const handleProbeTarget = async (url: string) => {
    setTriggeringUrl(url);
    try {
      const res = await api.createDiagnostic(url, true);
      setTriggeringUrl(null);
      onSelectSession(res.session_id);
    } catch (err: any) {
      setTriggeringUrl(null);
      setErrorMsg(err.message || 'Diagnostic failed');
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <Server className="w-6 h-6 text-cyan-400" /> Monitored Targets
          </h1>
          <p className="text-sm text-slate-400">
            Per-layer health across DNS, TCP, TLS, HTTP, Network, and Host metrics.
          </p>
        </div>

        {/* Add Target Form */}
        <form onSubmit={handleAddTarget} className="flex items-center gap-2">
          <input
            type="text"
            value={newUrl}
            onChange={(e) => setNewUrl(e.target.value)}
            placeholder="Add new URL (e.g. https://api.github.com)"
            className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-xs font-mono text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-cyan-500 w-64"
          />
          <button
            type="submit"
            className="px-3 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold flex items-center gap-1"
          >
            <Plus className="w-3.5 h-3.5" /> Add
          </button>
        </form>
      </div>

      {errorMsg && (
        <div className="p-3 rounded-lg bg-rose-950/30 border border-rose-800/40 text-rose-400 text-xs">
          {errorMsg}
        </div>
      )}

      {/* Targets Table */}
      <div className="bg-[#0b1324] border border-slate-800/80 rounded-xl overflow-hidden shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 uppercase font-mono bg-slate-900/40">
                <th className="py-3 px-4">Target Endpoint</th>
                <th className="py-3 px-3 text-center">DNS</th>
                <th className="py-3 px-3 text-center">TCP</th>
                <th className="py-3 px-3 text-center">TLS</th>
                <th className="py-3 px-3 text-center">HTTP</th>
                <th className="py-3 px-3 text-center">Network</th>
                <th className="py-3 px-3 text-center">System</th>
                <th className="py-3 px-3 text-center">Latest Diagnosis</th>
                <th className="py-3 px-3 text-center">Sessions</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-sans">
              {isLoading ? (
                <tr>
                  <td colSpan={10} className="py-8 text-center text-slate-500">
                    <RefreshCw className="w-5 h-5 text-cyan-400 animate-spin mx-auto mb-2" />
                    Loading monitored endpoints...
                  </td>
                </tr>
              ) : targets.length === 0 ? (
                <tr>
                  <td colSpan={10} className="py-8 text-center text-slate-500">
                    No targets registered yet. Add one above or run a diagnostic probe from the Dashboard!
                  </td>
                </tr>
              ) : (
                targets.map((item) => (
                  <tr key={item.target.id} className="hover:bg-slate-900/50 transition-colors">
                    <td className="py-3.5 px-4 font-mono font-medium text-slate-200">
                      <div>{item.target.url}</div>
                      <div className="text-[10px] text-slate-500 font-sans">
                        Last diagnosed: {item.last_diagnosed_at ? new Date(item.last_diagnosed_at).toLocaleTimeString() : 'Never'}
                      </div>
                    </td>
                    <td className="py-3.5 px-3 text-center">
                      <StatusBadge status={item.dns_status} />
                    </td>
                    <td className="py-3.5 px-3 text-center">
                      <StatusBadge status={item.tcp_status} />
                    </td>
                    <td className="py-3.5 px-3 text-center">
                      <StatusBadge status={item.tls_status} />
                    </td>
                    <td className="py-3.5 px-3 text-center">
                      <StatusBadge status={item.http_status} />
                    </td>
                    <td className="py-3.5 px-3 text-center">
                      <StatusBadge status={item.network_status} />
                    </td>
                    <td className="py-3.5 px-3 text-center">
                      <StatusBadge status={item.system_status} />
                    </td>
                    <td className="py-3.5 px-3 text-center">
                      {item.latest_diagnosis ? (
                        <span className="font-mono text-xs font-semibold text-slate-300">
                          {item.latest_diagnosis}
                        </span>
                      ) : (
                        <span className="text-slate-500 italic">None</span>
                      )}
                    </td>
                    <td className="py-3.5 px-3 text-center font-mono font-bold text-cyan-400">
                      {item.total_sessions}
                    </td>
                    <td className="py-3.5 px-4 text-right space-x-2">
                      <button
                        onClick={() => onViewBaselines(item.target.id)}
                        className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 font-semibold"
                      >
                        Baselines
                      </button>
                      <button
                        onClick={() => handleProbeTarget(item.target.url)}
                        disabled={triggeringUrl === item.target.url}
                        className="px-2.5 py-1 rounded bg-cyan-600/80 hover:bg-cyan-500 text-white font-semibold transition-colors disabled:opacity-50 inline-flex items-center gap-1"
                      >
                        {triggeringUrl === item.target.url ? (
                          <RefreshCw className="w-3 h-3 animate-spin" />
                        ) : (
                          <Play className="w-3 h-3 fill-current" />
                        )}
                        <span>Probe</span>
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
