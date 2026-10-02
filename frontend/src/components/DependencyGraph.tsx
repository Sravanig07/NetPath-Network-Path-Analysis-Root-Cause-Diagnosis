import React from 'react';
import { DependencyGraphNode, DependencyGraphEdge } from '../types/diagnostic';
import { Globe, Server, ShieldCheck, Cpu, ArrowRight, CheckCircle2, AlertTriangle, XCircle, HelpCircle } from 'lucide-react';

interface DependencyGraphProps {
  nodes: DependencyGraphNode[];
  edges: DependencyGraphEdge[];
  onSelectNode?: (node: DependencyGraphNode) => void;
  selectedNodeId?: string | null;
}

export const DependencyGraph: React.FC<DependencyGraphProps> = ({
  nodes,
  edges,
  onSelectNode,
  selectedNodeId,
}) => {
  const getNodeIcon = (layer: string) => {
    switch (layer.toUpperCase()) {
      case 'CLIENT':
        return <Cpu className="w-5 h-5 text-cyan-400" />;
      case 'DNS':
        return <Globe className="w-5 h-5 text-blue-400" />;
      case 'NETWORK':
        return <Server className="w-5 h-5 text-indigo-400" />;
      case 'TCP':
        return <Server className="w-5 h-5 text-violet-400" />;
      case 'TLS':
        return <ShieldCheck className="w-5 h-5 text-emerald-400" />;
      case 'HTTP':
        return <Globe className="w-5 h-5 text-teal-400" />;
      default:
        return <Cpu className="w-5 h-5 text-slate-400" />;
    }
  };

  const getStatusBorder = (status: string) => {
    switch (status) {
      case 'NORMAL':
        return 'border-emerald-500/40 bg-emerald-950/20 text-emerald-300';
      case 'DEGRADED':
        return 'border-amber-500/50 bg-amber-950/20 text-amber-300 animate-pulse';
      case 'FAILED':
        return 'border-rose-500/60 bg-rose-950/30 text-rose-300 animate-pulse';
      default:
        return 'border-slate-800 bg-slate-900/40 text-slate-400';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'NORMAL':
        return <CheckCircle2 className="w-4 h-4 text-emerald-400" />;
      case 'DEGRADED':
        return <AlertTriangle className="w-4 h-4 text-amber-400" />;
      case 'FAILED':
        return <XCircle className="w-4 h-4 text-rose-400" />;
      default:
        return <HelpCircle className="w-4 h-4 text-slate-500" />;
    }
  };

  return (
    <div className="bg-[#0b1324] border border-slate-800/80 rounded-xl p-5 shadow-xl">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-bold uppercase tracking-wider text-slate-300">
            Request Path Dependency Graph
          </h3>
          <p className="text-xs text-slate-400">Deterministic multi-layer execution traversal</p>
        </div>
        <div className="flex items-center gap-3 text-xs">
          <span className="flex items-center gap-1.5 text-emerald-400">
            <span className="w-2 h-2 rounded-full bg-emerald-500" /> Normal
          </span>
          <span className="flex items-center gap-1.5 text-amber-400">
            <span className="w-2 h-2 rounded-full bg-amber-500" /> Degraded
          </span>
          <span className="flex items-center gap-1.5 text-rose-400">
            <span className="w-2 h-2 rounded-full bg-rose-500" /> Failed
          </span>
        </div>
      </div>

      {/* Nodes visual flow */}
      <div className="flex flex-wrap items-center justify-center gap-3 py-6 overflow-x-auto">
        {nodes.map((node, index) => {
          const isSelected = selectedNodeId === node.id;
          return (
            <React.Fragment key={node.id}>
              <div
                onClick={() => onSelectNode && onSelectNode(node)}
                className={`relative flex flex-col items-center justify-center p-3.5 rounded-xl border transition-all cursor-pointer min-w-[140px] ${getStatusBorder(
                  node.status
                )} ${
                  isSelected
                    ? 'ring-2 ring-cyan-400 shadow-lg shadow-cyan-500/20 scale-105'
                    : 'hover:border-slate-600 hover:scale-102'
                }`}
              >
                <div className="flex items-center justify-between w-full mb-2">
                  <div className="p-1.5 rounded-md bg-slate-900/80 border border-slate-700/60">
                    {getNodeIcon(node.layer)}
                  </div>
                  <div>{getStatusIcon(node.status)}</div>
                </div>

                <div className="text-center w-full">
                  <div className="text-xs font-semibold tracking-wide text-slate-200 truncate">
                    {node.label}
                  </div>
                  <div className="text-[10px] uppercase font-mono text-slate-400 mt-0.5">
                    {node.layer}
                  </div>
                </div>

                {/* Sub-label metrics if available */}
                {node.details && (
                  <div className="mt-2 pt-1.5 border-t border-slate-800/80 w-full text-center">
                    {node.details.latency_ms !== undefined && (
                      <span className="text-[11px] font-mono text-cyan-300 font-medium">
                        {node.details.latency_ms} ms
                      </span>
                    )}
                    {node.details.connect_latency_ms !== undefined && (
                      <span className="text-[11px] font-mono text-cyan-300 font-medium">
                        {node.details.connect_latency_ms} ms
                      </span>
                    )}
                    {node.details.handshake_latency_ms !== undefined && (
                      <span className="text-[11px] font-mono text-cyan-300 font-medium">
                        {node.details.handshake_latency_ms} ms
                      </span>
                    )}
                    {node.details.total_latency_ms !== undefined && (
                      <span className="text-[11px] font-mono text-cyan-300 font-medium">
                        {node.details.total_latency_ms} ms
                      </span>
                    )}
                  </div>
                )}
              </div>

              {index < nodes.length - 1 && (
                <div className="flex items-center text-slate-600">
                  <ArrowRight className="w-5 h-5 text-slate-600" />
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
};
