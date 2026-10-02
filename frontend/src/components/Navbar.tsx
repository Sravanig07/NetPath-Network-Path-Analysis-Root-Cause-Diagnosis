import React from 'react';
import { Activity, ShieldAlert, Cpu, History, BarChart2, Beaker, Server } from 'lucide-react';

interface NavbarProps {
  currentTab: string;
  onSelectTab: (tab: string) => void;
}

export const Navbar: React.FC<NavbarProps> = ({ currentTab, onSelectTab }) => {
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: Activity },
    { id: 'targets', label: 'Targets', icon: Server },
    { id: 'history', label: 'Incident Replay', icon: History },
    { id: 'baselines', label: 'Baselines & Trends', icon: BarChart2 },
    { id: 'lab', label: 'Failure Lab', icon: Beaker },
  ];

  return (
    <header className="sticky top-0 z-50 bg-[#070b14]/90 backdrop-blur-md border-b border-slate-800/80">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Brand */}
          <div className="flex items-center gap-3 cursor-pointer" onClick={() => onSelectTab('dashboard')}>
            <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20">
              <Activity className="w-5 h-5 text-white" />
            </div>
            <div>
              <span className="text-lg font-bold tracking-tight bg-gradient-to-r from-white via-slate-200 to-cyan-400 bg-clip-text text-transparent">
                NetPath
              </span>
              <span className="hidden sm:inline-block ml-2 text-xs px-2 py-0.5 rounded bg-cyan-950/80 border border-cyan-800/50 text-cyan-400 font-mono">
                RCA Platform
              </span>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="flex items-center space-x-1 sm:space-x-2">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = currentTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => onSelectTab(item.id)}
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                    isActive
                      ? 'bg-slate-800/90 text-cyan-400 border border-cyan-500/30 shadow-sm'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span className="hidden md:inline">{item.label}</span>
                </button>
              );
            })}
          </nav>

          {/* Observability Links */}
          <div className="flex items-center gap-3">
            <a
              href="http://localhost:3001"
              target="_blank"
              rel="noreferrer"
              className="text-xs text-slate-400 hover:text-cyan-400 flex items-center gap-1 border border-slate-800 hover:border-cyan-800/60 px-2.5 py-1 rounded bg-slate-900/60 transition-colors"
            >
              <BarChart2 className="w-3.5 h-3.5 text-amber-400" />
              <span>Grafana</span>
            </a>
            <a
              href="/metrics"
              target="_blank"
              rel="noreferrer"
              className="text-xs text-slate-400 hover:text-cyan-400 flex items-center gap-1 border border-slate-800 hover:border-cyan-800/60 px-2.5 py-1 rounded bg-slate-900/60 transition-colors font-mono"
            >
              /metrics
            </a>
          </div>
        </div>
      </div>
    </header>
  );
};
