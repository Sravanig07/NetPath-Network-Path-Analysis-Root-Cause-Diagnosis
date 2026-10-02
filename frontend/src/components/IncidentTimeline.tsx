import React from 'react';
import { IncidentTimelineEvent } from '../types/diagnostic';
import { Clock, CheckCircle2, AlertTriangle, XCircle, Info } from 'lucide-react';

interface IncidentTimelineProps {
  events: IncidentTimelineEvent[];
}

export const IncidentTimeline: React.FC<IncidentTimelineProps> = ({ events }) => {
  const getEventIcon = (status: string) => {
    switch (status) {
      case 'SUCCESS':
        return <CheckCircle2 className="w-4 h-4 text-emerald-400" />;
      case 'DEGRADED':
        return <AlertTriangle className="w-4 h-4 text-amber-400" />;
      case 'FAILED':
        return <XCircle className="w-4 h-4 text-rose-400" />;
      default:
        return <Info className="w-4 h-4 text-cyan-400" />;
    }
  };

  const getLayerColor = (layer: string) => {
    switch (layer.toUpperCase()) {
      case 'DNS':
        return 'text-blue-400 bg-blue-950/40 border-blue-800/50';
      case 'TCP':
        return 'text-violet-400 bg-violet-950/40 border-violet-800/50';
      case 'TLS':
        return 'text-emerald-400 bg-emerald-950/40 border-emerald-800/50';
      case 'HTTP':
        return 'text-teal-400 bg-teal-950/40 border-teal-800/50';
      case 'NETWORK':
        return 'text-indigo-400 bg-indigo-950/40 border-indigo-800/50';
      case 'SYSTEM':
        return 'text-amber-400 bg-amber-950/40 border-amber-800/50';
      case 'ANALYSIS':
        return 'text-cyan-400 bg-cyan-950/40 border-cyan-800/50';
      default:
        return 'text-slate-400 bg-slate-900 border-slate-800';
    }
  };

  const formatTimestamp = (ts: string) => {
    try {
      const d = new Date(ts);
      const timeStr = d.toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
      const ms = String(d.getMilliseconds()).padStart(3, '0');
      return `${timeStr}.${ms}`;
    } catch {
      return ts;
    }
  };

  return (
    <div className="bg-[#0b1324] border border-slate-800/80 rounded-xl p-5 shadow-xl">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
            <Clock className="w-4 h-4 text-cyan-400" /> Incident Timeline
          </h3>
          <p className="text-xs text-slate-400">High-resolution chronological event execution</p>
        </div>
        <span className="text-xs font-mono text-slate-400 px-2 py-0.5 rounded bg-slate-900 border border-slate-800">
          {events.length} events
        </span>
      </div>

      <div className="relative pl-6 space-y-4 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-800">
        {events.map((ev, idx) => (
          <div key={idx} className="relative group">
            {/* Timeline dot */}
            <div className="absolute -left-[27px] top-1 bg-[#0b1324] p-0.5 rounded-full border border-slate-700">
              {getEventIcon(ev.status)}
            </div>

            <div className="p-3 rounded-lg bg-slate-900/50 border border-slate-800/70 hover:border-slate-700 transition-colors">
              <div className="flex items-center justify-between gap-2 mb-1">
                <div className="flex items-center gap-2">
                  <span className={`text-[10px] font-mono px-2 py-0.5 rounded border uppercase font-bold ${getLayerColor(ev.layer)}`}>
                    {ev.layer}
                  </span>
                  <span className="text-xs font-mono font-semibold text-slate-200">
                    {ev.event_type}
                  </span>
                </div>
                <span className="text-[11px] font-mono text-slate-400">
                  {formatTimestamp(ev.timestamp)}
                </span>
              </div>
              <p className="text-xs text-slate-300 leading-relaxed">
                {ev.message}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
