import React, { useState } from 'react';
import { api } from '../api/client';
import { Beaker, Play, Loader2, AlertTriangle, ShieldAlert, Clock, CheckCircle2, Zap } from 'lucide-react';

interface FailureLabProps {
  onSelectSession: (sessionId: string) => void;
}

export const FailureLab: React.FC<FailureLabProps> = ({ onSelectSession }) => {
  const [runningScenario, setRunningScenario] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const scenarios = [
    {
      id: 'scenario-1',
      title: 'Scenario 1: HTTP Application Latency Spike',
      target: 'http://localhost:8001/slow?delay=2.0',
      expectedRca: 'HTTP_APPLICATION_LATENCY',
      expectedLayer: 'HTTP Application',
      description: 'Simulates a slow backend database or thread pool contention. Lower layers (DNS, TCP, TLS) complete nominally, but HTTP response takes 2,000ms, breaching historical P95 baseline.',
      icon: Clock,
      color: 'amber',
    },
    {
      id: 'scenario-2',
      title: 'Scenario 2: HTTP Internal Server Error (500)',
      target: 'http://localhost:8002/error?code=500',
      expectedRca: 'HTTP_APPLICATION_ERROR',
      expectedLayer: 'HTTP Application',
      description: 'Simulates an uncaught exception or internal database error. Network connection succeeds cleanly, but server returns HTTP 500.',
      icon: ShieldAlert,
      color: 'rose',
    },
    {
      id: 'scenario-3',
      title: 'Scenario 3: Bad Gateway (502) Upstream Failure',
      target: 'http://localhost:8002/error?code=502',
      expectedRca: 'HTTP_APPLICATION_ERROR',
      expectedLayer: 'HTTP Application',
      description: 'Simulates a reverse proxy failing to communicate with upstream application servers, returning HTTP 502.',
      icon: AlertTriangle,
      color: 'rose',
    },
    {
      id: 'scenario-4',
      title: 'Scenario 4: TCP Connectivity Failure (Port Dead / Refused)',
      target: 'http://localhost:9999',
      expectedRca: 'TCP_CONNECTIVITY_FAILURE',
      expectedLayer: 'TCP Handshake',
      description: 'Simulates target daemon being down or blocked by firewall. DNS resolves, but TCP SYN packet receives immediate RST or connection timeout.',
      icon: Zap,
      color: 'rose',
    },
    {
      id: 'scenario-5',
      title: 'Scenario 5: DNS Resolution Failure (NXDOMAIN)',
      target: 'http://non-existent-subdomain-99214.example.com',
      expectedRca: 'DNS_FAILURE',
      expectedLayer: 'DNS Resolution',
      description: 'Simulates misconfigured DNS record or expired domain. DNS resolution returns NXDOMAIN, suppressing downstream TCP/HTTP checks.',
      icon: AlertTriangle,
      color: 'blue',
    },
    {
      id: 'scenario-6',
      title: 'Scenario 6: HTTP 429 Rate Limiting',
      target: 'http://localhost:8003/rate-limit',
      expectedRca: 'HTTP_APPLICATION_ERROR',
      expectedLayer: 'HTTP Application',
      description: 'Simulates API rate limiter returning HTTP 429 Too Many Requests with Retry-After header.',
      icon: AlertTriangle,
      color: 'amber',
    },
  ];

  const handleRunScenario = async (scenario: typeof scenarios[0]) => {
    setRunningScenario(scenario.id);
    setErrorMsg(null);
    try {
      // Execute synchronous diagnostic probe
      const res = await api.createDiagnostic(scenario.target, true);
      setRunningScenario(null);
      onSelectSession(res.session_id);
    } catch (err: any) {
      setRunningScenario(null);
      setErrorMsg(err.message || 'Failure simulation probe failed');
    }
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="p-6 rounded-2xl bg-[#0b1324] border border-cyan-500/20 shadow-2xl space-y-2">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 text-xs font-semibold">
          <Beaker className="w-3.5 h-3.5" /> Controlled Failure Lab
        </div>
        <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight text-white">
          Simulate Network Faults & Verify Deterministic RCA
        </h1>
        <p className="text-sm text-slate-300 max-w-3xl">
          Trigger controlled real-world failure scenarios against containerized mock services to verify that NetPath correctly isolates the primary affected layer and outputs explainable evidence.
        </p>
      </div>

      {errorMsg && (
        <div className="p-4 rounded-xl bg-rose-950/30 border border-rose-800/40 text-rose-300 text-xs font-mono">
          {errorMsg}
        </div>
      )}

      {/* Scenarios Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {scenarios.map((sc) => {
          const Icon = sc.icon;
          const isTriggering = runningScenario === sc.id;
          return (
            <div
              key={sc.id}
              className="bg-[#0b1324] border border-slate-800/80 rounded-xl p-6 shadow-xl flex flex-col justify-between hover:border-slate-700 transition-all space-y-5"
            >
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="p-2 rounded-lg bg-slate-900 border border-slate-800">
                      <Icon className="w-4 h-4 text-cyan-400" />
                    </div>
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
                      Fault Injection
                    </span>
                  </div>
                  <span className="px-2.5 py-0.5 rounded-full text-[11px] font-mono font-semibold bg-cyan-950/60 border border-cyan-800/50 text-cyan-300">
                    {sc.expectedLayer}
                  </span>
                </div>

                <h3 className="text-base font-bold text-white font-sans">{sc.title}</h3>
                <p className="text-xs text-slate-300 leading-relaxed">{sc.description}</p>

                <div className="p-2.5 rounded-lg bg-slate-950/70 border border-slate-800/60 font-mono text-xs space-y-1">
                  <div className="text-slate-400 text-[10px] uppercase">Target Endpoint:</div>
                  <div className="text-cyan-300 truncate">{sc.target}</div>
                </div>

                <div className="flex items-center gap-2 text-xs font-mono">
                  <span className="text-slate-500">Expected Root Cause:</span>
                  <span className="font-bold text-emerald-400">{sc.expectedRca}</span>
                </div>
              </div>

              <button
                onClick={() => handleRunScenario(sc)}
                disabled={Boolean(runningScenario)}
                className="w-full py-2.5 px-4 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-semibold text-xs transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-md shadow-cyan-500/10 flex items-center justify-center gap-2"
              >
                {isTriggering ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Executing Probes & Diagnosing...</span>
                  </>
                ) : (
                  <>
                    <Play className="w-3.5 h-3.5 fill-current" />
                    <span>Inject Fault & Diagnose</span>
                  </>
                )}
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
};
