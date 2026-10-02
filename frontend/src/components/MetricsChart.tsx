import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Legend,
} from 'recharts';
import { DnsResult, TcpResult, TlsResult, HttpResult } from '../types/diagnostic';

interface MetricsChartProps {
  dns: DnsResult | null;
  tcp: TcpResult | null;
  tls: TlsResult | null;
  http: HttpResult | null;
}

export const MetricsChart: React.FC<MetricsChartProps> = ({ dns, tcp, tls, http }) => {
  const data = [
    {
      layer: 'DNS Resolution',
      duration_ms: dns ? dns.latency_ms : 0,
      fill: '#3b82f6',
    },
    {
      layer: 'TCP Connect',
      duration_ms: tcp ? tcp.connect_latency_ms : 0,
      fill: '#8b5cf6',
    },
    {
      layer: 'TLS Handshake',
      duration_ms: tls ? tls.handshake_latency_ms : 0,
      fill: '#10b981',
    },
    {
      layer: 'HTTP TTFB',
      duration_ms: http ? http.ttfb_ms : 0,
      fill: '#06b6d4',
    },
    {
      layer: 'HTTP Total',
      duration_ms: http ? http.total_latency_ms : 0,
      fill: '#f43f5e',
    },
  ];

  return (
    <div className="bg-[#0b1324] border border-slate-800/80 rounded-xl p-5 shadow-xl">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-bold uppercase tracking-wider text-slate-300">
            Layer Latency Profile (ms)
          </h3>
          <p className="text-xs text-slate-400">Granular duration breakdown across network layers</p>
        </div>
      </div>

      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
            <XAxis
              dataKey="layer"
              stroke="#64748b"
              fontSize={11}
              tickLine={false}
              angle={-15}
              textAnchor="end"
            />
            <YAxis stroke="#64748b" fontSize={11} tickLine={false} />
            <Tooltip
              contentStyle={{
                backgroundColor: '#0f172a',
                borderColor: '#334155',
                borderRadius: '8px',
                fontSize: '12px',
                color: '#f8fafc',
              }}
              formatter={(val: number) => [`${val.toFixed(1)} ms`, 'Duration']}
            />
            <Bar dataKey="duration_ms" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
