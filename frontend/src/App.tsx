import React, { useState } from 'react';
import { Navbar } from './components/Navbar';
import { Dashboard } from './pages/Dashboard';
import { TargetView } from './pages/TargetView';
import { DiagnosticDetail } from './pages/DiagnosticDetail';
import { IncidentHistory } from './pages/IncidentHistory';
import { BaselinesView } from './pages/BaselinesView';
import { FailureLab } from './pages/FailureLab';

export const App: React.FC = () => {
  const [currentTab, setCurrentTab] = useState('dashboard');
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [selectedTargetId, setSelectedTargetId] = useState<number | null>(null);

  const handleSelectSession = (sessionId: string) => {
    setSelectedSessionId(sessionId);
    setCurrentTab('detail');
  };

  const handleViewBaselines = (targetId: number) => {
    setSelectedTargetId(targetId);
    setCurrentTab('baselines');
  };

  return (
    <div className="min-h-screen bg-[#070b14] text-slate-100 flex flex-col selection:bg-cyan-500/30 selection:text-cyan-200">
      <Navbar currentTab={currentTab} onSelectTab={(tab) => setCurrentTab(tab)} />

      <main className="flex-1 pb-16">
        {currentTab === 'dashboard' && (
          <Dashboard
            onSelectSession={handleSelectSession}
            onNavigateTab={(tab) => setCurrentTab(tab)}
          />
        )}

        {currentTab === 'targets' && (
          <TargetView
            onSelectSession={handleSelectSession}
            onViewBaselines={handleViewBaselines}
          />
        )}

        {currentTab === 'detail' && selectedSessionId && (
          <DiagnosticDetail
            sessionId={selectedSessionId}
            onBack={() => setCurrentTab('dashboard')}
          />
        )}

        {currentTab === 'history' && (
          <IncidentHistory onSelectSession={handleSelectSession} />
        )}

        {currentTab === 'baselines' && (
          <BaselinesView initialTargetId={selectedTargetId} />
        )}

        {currentTab === 'lab' && (
          <FailureLab onSelectSession={handleSelectSession} />
        )}
      </main>

      <footer className="border-t border-slate-800/80 py-6 text-center text-xs text-slate-500 font-mono">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>NetPath — Deterministic Network Path Analysis & Root-Cause Diagnosis Platform</span>
          <span>FastAPI • MySQL 8 • Prometheus • Grafana • React</span>
        </div>
      </footer>
    </div>
  );
};
