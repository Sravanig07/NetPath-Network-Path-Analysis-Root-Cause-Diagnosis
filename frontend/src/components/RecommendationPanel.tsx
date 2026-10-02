import React, { useState } from 'react';
import { Recommendation } from '../types/diagnostic';
import { CheckSquare, Copy, Check } from 'lucide-react';

interface RecommendationPanelProps {
  recommendations: Recommendation[];
}

export const RecommendationPanel: React.FC<RecommendationPanelProps> = ({ recommendations }) => {
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null);

  const handleCopy = (text: string, idx: number) => {
    navigator.clipboard.writeText(text);
    setCopiedIdx(idx);
    setTimeout(() => setCopiedIdx(null), 2000);
  };

  return (
    <div className="bg-[#0b1324] border border-slate-800/80 rounded-xl p-5 shadow-xl">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
            <CheckSquare className="w-4 h-4 text-emerald-400" /> Actionable Investigation Actions
          </h3>
          <p className="text-xs text-slate-400">Targeted remediation checklist derived from deterministic evidence</p>
        </div>
        <span className="text-xs font-mono text-emerald-400 bg-emerald-950/40 border border-emerald-800/50 px-2 py-0.5 rounded">
          {recommendations.length} Steps
        </span>
      </div>

      <div className="space-y-3">
        {recommendations.map((rec, idx) => (
          <div
            key={idx}
            className="flex items-start justify-between gap-3 p-3.5 rounded-lg bg-slate-900/60 border border-slate-800 hover:border-slate-700 transition-colors"
          >
            <div className="flex items-start gap-3">
              <span className="w-6 h-6 rounded-md bg-slate-800 border border-slate-700 text-cyan-400 font-mono text-xs font-bold flex items-center justify-center shrink-0 mt-0.5">
                {rec.action_order || idx + 1}
              </span>
              <p className="text-xs text-slate-200 leading-relaxed font-sans">
                {rec.action_text}
              </p>
            </div>

            <button
              onClick={() => handleCopy(rec.action_text, idx)}
              className="p-1.5 rounded bg-slate-800/60 hover:bg-slate-700 text-slate-400 hover:text-white transition-colors shrink-0"
              title="Copy action text"
            >
              {copiedIdx === idx ? (
                <Check className="w-3.5 h-3.5 text-emerald-400" />
              ) : (
                <Copy className="w-3.5 h-3.5" />
              )}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};
