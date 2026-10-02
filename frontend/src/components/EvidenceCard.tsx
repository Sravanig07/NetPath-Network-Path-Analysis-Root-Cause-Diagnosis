import React from 'react';
import { Diagnosis, Anomaly } from '../types/diagnostic';
import { StatusBadge } from './StatusBadge';
import { ShieldAlert, CheckCircle, Zap, AlertCircle } from 'lucide-react';

interface EvidenceCardProps {
  diagnosis: Diagnosis | null;
  anomalies: Anomaly[];
}

export const EvidenceCard: React.FC<EvidenceCardProps> = ({ diagnosis, anomalies }) => {
  if (!diagnosis) {
    return (
      <div className="bg-[#0b1324] border border-slate-800 rounded-xl p-5 text-center text-slate-400">
        No diagnosis recorded for this session.
      </div>
    );
  }

  return (
    <div className="bg-[#0b1324] border border-slate-800/80 rounded-xl p-5 shadow-xl space-y-5">
      {/* Root Cause Header Banner */}
      <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="text-xs uppercase font-mono tracking-wider text-slate-400">
              Deterministic Root Cause
            </span>
            <StatusBadge status={diagnosis.severity} />
          </div>
          <h2 className="text-xl font-bold font-mono tracking-tight text-white flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-cyan-400" />
            {diagnosis.category}
          </h2>
          <p className="text-sm text-slate-300 leading-relaxed max-w-2xl">
            {diagnosis.summary}
          </p>
        </div>

        {/* Evidence Score Card */}
        <div className="flex flex-col items-center justify-center px-5 py-3 rounded-lg bg-[#070b14] border border-cyan-500/30 shadow-inner">
          <span className="text-[10px] uppercase font-mono tracking-wider text-cyan-400">
            Evidence Score
          </span>
          <div className="text-3xl font-extrabold text-cyan-300 font-mono">
            {diagnosis.evidence_score}
          </div>
          <span className="text-[10px] text-slate-400">Explainable Weight</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Itemized Evidence Points */}
        <div className="p-4 rounded-xl bg-slate-900/40 border border-slate-800/80">
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300 mb-3 flex items-center gap-2">
            <Zap className="w-4 h-4 text-amber-400" /> Layer Evidence Attributions
          </h4>
          <div className="space-y-2">
            {diagnosis.evidence_items.map((item, idx) => (
              <div
                key={idx}
                className="flex items-start gap-2.5 p-2 rounded-lg bg-slate-950/60 border border-slate-800/60 text-xs"
              >
                <span className="px-1.5 py-0.5 rounded bg-amber-500/10 border border-amber-500/30 text-amber-400 font-mono font-bold shrink-0">
                  +{item.weight}
                </span>
                <span className="text-slate-300 leading-tight">
                  {item.description}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Anomalies Detected */}
        <div className="p-4 rounded-xl bg-slate-900/40 border border-slate-800/80">
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300 mb-3 flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-400" /> Anomalies Detected ({anomalies.length})
          </h4>
          {anomalies.length === 0 ? (
            <div className="flex items-center gap-2 text-xs text-emerald-400 p-3 rounded-lg bg-emerald-950/20 border border-emerald-800/40">
              <CheckCircle className="w-4 h-4" />
              <span>No statistical baseline deviations or threshold breaches detected.</span>
            </div>
          ) : (
            <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
              {anomalies.map((anom, idx) => (
                <div
                  key={idx}
                  className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/60 text-xs space-y-1"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono font-semibold text-rose-300">
                      {anom.rule_triggered}
                    </span>
                    <StatusBadge status={anom.severity} />
                  </div>
                  <p className="text-slate-300 text-[11px]">{anom.evidence_text}</p>
                  {anom.baseline_reference && (
                    <div className="text-[10px] font-mono text-slate-400">
                      Baseline: {anom.baseline_reference} (Observed: {anom.observed_value})
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
