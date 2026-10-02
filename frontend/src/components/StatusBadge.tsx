import React from 'react';

interface StatusBadgeProps {
  status: string;
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, className = '' }) => {
  const norm = (status || '').toUpperCase();

  let colorClasses = 'bg-slate-800 text-slate-400 border-slate-700';

  if (['SUCCESS', 'NORMAL', 'OK', 'COMPLETED', 'INFO', 'LOW'].includes(norm)) {
    colorClasses = 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
  } else if (['DEGRADED', 'MEDIUM', 'TLS_CERTIFICATE_EXPIRING', 'WARNING'].includes(norm)) {
    colorClasses = 'bg-amber-500/10 text-amber-400 border-amber-500/30';
  } else if (['FAILED', 'CRITICAL', 'HIGH', 'DNS_FAILURE', 'TCP_CONNECTIVITY_FAILURE', 'TLS_FAILURE', 'HTTP_APPLICATION_ERROR', 'NETWORK_PACKET_LOSS'].includes(norm)) {
    colorClasses = 'bg-rose-500/10 text-rose-400 border-rose-500/30 animate-pulse';
  } else if (['PENDING', 'RUNNING'].includes(norm)) {
    colorClasses = 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30';
  }

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold tracking-wide border ${colorClasses} ${className}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${['SUCCESS', 'NORMAL', 'COMPLETED'].includes(norm) ? 'bg-emerald-400' : ['DEGRADED', 'MEDIUM'].includes(norm) ? 'bg-amber-400' : ['FAILED', 'CRITICAL', 'HIGH'].includes(norm) ? 'bg-rose-400' : 'bg-cyan-400'}`} />
      {norm}
    </span>
  );
};
