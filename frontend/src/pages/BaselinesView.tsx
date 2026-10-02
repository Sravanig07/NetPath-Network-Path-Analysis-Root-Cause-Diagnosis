import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { TargetStatusSummary, TargetBaselineResponse } from '../types/diagnostic';
import { BarChart2, RefreshCw, AlertCircle, CheckCircle2 } from 'lucide-react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Legend,
} from 'recharts';

interface BaselinesViewProps {
  initialTargetId?: number | null;
}

export const BaselinesView: React.FC<BaselinesViewProps> = ({ initialTargetId }) => {
  const [targets, setTargets] = useState<TargetStatusSummary[]>([]);
  const [selectedTargetId, setSelectedTargetId] = useState<number | null>(initialTargetId || null);
  const [baselineData, setBaselineData] = useState<TargetBaselineResponse | null>(null);
  const [metricHistory, setMetricHistory] = useState<any[]>([]);
  const [activeMetric, setActiveMetric] = useState('http_latency_ms');
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    api.listTargets().then((list) => {
      setTargets(list);
      if (!selectedTargetId && list.length > 0) {
        setSelectedTargetId(list[0].target.id);
      }
    });
  }, []);

  const loadTargetBaselines = async (targetId: number) => {
    setIsLoading(true);
    try {
      const [bData, hData] = await Promise.all([
        api.getBaselines(targetId),
        api.getMetricHistory(targetId, activeMetric, 30).catch(() => ({ points: [] })),
      ]);
      setBaselineData(bData);
      const chartPoints = (hData.points || []).map((pt: any) => ({
        timestamp: new Date(pt.recorded_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
        value: pt.value,
      }));
      setMetricHistory(chartPoints);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (selectedTargetId) {
      loadTargetBaselines(selectedTargetId);
    }
  }, [selectedTargetId, activeMetric]);

  return (
    <div className="space-y-6 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header & Target Selector */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <BarChart2 className="w-6 h-6 text-cyan-400" /> Historical Baselines & Percentiles
          </h1>
          <p className="text-sm text-slate-400">
            P50, P95, and P99 statistical thresholds stored in MySQL with sample size safeguards.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <select
            value={selectedTargetId || ''}
            onChange={(e) => setSelectedTargetId(Number(e.target.value))}
            className="px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-cyan-500 font-mono"
          >
            {targets.map((t) => (
              <option key={t.target.id} value={t.target.id}>
                {t.target.url}
              </option>
            ))}
          </select>

          <button
            onClick={() => selectedTargetId && loadTargetBaselines(selectedTargetId)}
            className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700"
            title="Refresh"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="py-16 text-center text-slate-500">
          <RefreshCw className="w-6 h-6 text-cyan-400 animate-spin mx-auto mb-2" />
          Loading baseline calculations...
        </div>
      ) : baselineData ? (
        <div className="space-y-6">
          {/* Baseline Metric Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {Object.entries(baselineData.metrics).map(([mName, stats]) => (
              <div
                key={mName}
                onClick={() => setActiveMetric(mName)}
                className={`p-4 rounded-xl bg-[#0b1324] border transition-all cursor-pointer ${
                  activeMetric === mName
                    ? 'border-cyan-500/60 shadow-lg shadow-cyan-500/10 bg-slate-900/60'
                    : 'border-slate-800/80 hover:border-slate-700'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-mono font-semibold text-slate-300 truncate">
                    {mName.replace('_ms', '')}
                  </span>
                  {stats.is_sufficient_evidence ? (
                    <span className="flex items-center gap-1 text-[10px] text-emerald-400 font-mono">
                      <CheckCircle2 className="w-3 h-3" /> Valid ({stats.count})
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 text-[10px] text-amber-400 font-mono" title="Under 10 samples">
                      <AlertCircle className="w-3 h-3" /> &lt;10 samples
                    </span>
                  )}
                </div>

                <div className="grid grid-cols-3 gap-2 mt-3 pt-2 border-t border-slate-800/80 text-center font-mono">
                  <div>
                    <div className="text-[10px] text-slate-500">P50</div>
                    <div className="text-xs font-bold text-slate-200">{stats.p50} ms</div>
                  </div>
                  <div>
                    <div className="text-[10px] text-amber-500/80 font-semibold">P95</div>
                    <div className="text-xs font-bold text-amber-400">{stats.p95} ms</div>
                  </div>
                  <div>
                    <div className="text-[10px] text-rose-500/80 font-semibold">P99</div>
                    <div className="text-xs font-bold text-rose-400">{stats.p99} ms</div>
                  </div>
                </div>

                <div className="flex justify-between items-center text-[10px] font-mono text-slate-500 mt-2">
                  <span>Mean: {stats.mean}ms</span>
                  <span>StdDev: ±{stats.std_dev}ms</span>
                </div>
              </div>
            ))}
          </div>

          {/* Time Series History Chart */}
          <div className="bg-[#0b1324] border border-slate-800/80 rounded-xl p-5 shadow-xl space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold uppercase tracking-wider text-slate-300 font-mono">
                  {activeMetric} — Historical Sample Trend
                </h3>
                <p className="text-xs text-slate-400">Sequential telemetry observations</p>
              </div>
              <span className="text-xs font-mono text-cyan-400 bg-cyan-950/40 border border-cyan-800/50 px-2.5 py-0.5 rounded">
                P95 Baseline: {baselineData.metrics[activeMetric]?.p95 || 0} ms
              </span>
            </div>

            <div className="h-72 w-full">
              {metricHistory.length === 0 ? (
                <div className="flex items-center justify-center h-full text-xs text-slate-500">
                  No historical samples recorded for this metric yet.
                </div>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={metricHistory} margin={{ top: 10, right: 20, left: -20, bottom: 10 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis dataKey="timestamp" stroke="#64748b" fontSize={11} tickLine={false} />
                    <YAxis stroke="#64748b" fontSize={11} tickLine={false} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#0f172a',
                        borderColor: '#334155',
                        borderRadius: '8px',
                        fontSize: '12px',
                        color: '#f8fafc',
                      }}
                      formatter={(val: number) => [`${val.toFixed(1)} ms`, 'Latency']}
                    />
                    <Line
                      type="monotone"
                      dataKey="value"
                      stroke="#06b6d4"
                      strokeWidth={2}
                      dot={{ r: 3, fill: '#06b6d4' }}
                      activeDot={{ r: 5 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>
        </div>
      ) : (
        <div className="py-12 text-center text-slate-500">
          Select or register a target to view baseline calculations.
        </div>
      )}
    </div>
  );
};
