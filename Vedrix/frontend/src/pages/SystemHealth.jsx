import { useState, useEffect, useCallback } from 'react';
import {
  Activity,
  Database,
  Server,
  Cpu,
  Clock,
  AlertTriangle,
  CheckCircle,
  XCircle,
  RefreshCcw,
  Zap,
  Shield,
  HardDrive,
  Network
} from 'lucide-react';
import apiClient from '../services/api';
import { useNavigate } from 'react-router-dom';

const SystemHealth = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [health, setHealth] = useState(null);
  const [aiHealth, setAiHealth] = useState(null);
  const [auditStats, setAuditStats] = useState(null);
  const [teamAnalytics, setTeamAnalytics] = useState(null);
  const [error, setError] = useState('');
  const [lastRefresh, setLastRefresh] = useState(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError('');

      const [healthRes, aiRes, auditRes, analyticsRes] = await Promise.allSettled([
        apiClient.get('/health/ready'),
        apiClient.get('/admin/ai-health'),
        apiClient.get('/admin/audit-logs/stats'),
        apiClient.get('/admin/analytics/team'),
      ]);

      if (healthRes.status === 'fulfilled') {
        setHealth(healthRes.value.data);
      } else {
        setError('Failed to fetch system health');
      }

      if (aiRes.status === 'fulfilled') {
        setAiHealth(aiRes.value.data);
      }

      if (auditRes.status === 'fulfilled') {
        setAuditStats(auditRes.value.data);
      }

      if (analyticsRes.status === 'fulfilled') {
        setTeamAnalytics(analyticsRes.value.data);
      }

      setLastRefresh(new Date());
    } catch {
      setError('Failed to fetch system data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchData();
    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const getStatusIcon = (status) => {
    if (status === 'healthy' || status === 'Healthy') {
      return <CheckCircle className="text-emerald-400" size={20} />;
    }
    if (status === 'degraded') {
      return <AlertTriangle className="text-amber-400" size={20} />;
    }
    return <XCircle className="text-red-400" size={20} />;
  };

  const getStatusColor = (status) => {
    if (status === 'healthy' || status === 'Healthy') return 'text-emerald-400';
    if (status === 'degraded') return 'text-amber-400';
    return 'text-red-400';
  };

  const getProviderStatus = (providerName) => {
    if (!aiHealth?.circuit_breakers) return 'unknown';
    const cb = aiHealth.circuit_breakers[providerName];
    if (!cb) return 'unknown';
    return cb.state === 'CLOSED' ? 'healthy' : cb.state === 'OPEN' ? 'down' : 'degraded';
  };

  if (loading && !health) {
    return (
      <div className="min-h-screen bg-[#020617] flex items-center justify-center">
        <div className="text-center">
          <RefreshCcw size={32} className="animate-spin text-purple-400 mx-auto mb-4" />
          <p className="text-slate-400">Loading system health...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#020617] text-white">
      <div className="max-w-7xl mx-auto px-8 py-10">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight">System Health</h1>
            <p className="text-slate-500 mt-1">Real-time monitoring of system components and AI providers</p>
          </div>
          <div className="flex items-center space-x-3">
            <button
              onClick={() => navigate('/admin')}
              className="flex items-center space-x-2 bg-white/5 border border-white/10 text-slate-300 px-4 py-2 rounded-xl text-sm font-bold hover:bg-white/10 transition-all"
            >
              <span>Back to Admin</span>
            </button>
            <button
              onClick={fetchData}
              disabled={loading}
              className="flex items-center space-x-2 bg-purple-600/10 border border-purple-500/20 text-purple-400 px-4 py-2 rounded-xl text-sm font-bold hover:bg-purple-600/20 transition-all disabled:opacity-50"
            >
              <RefreshCcw size={16} className={loading ? 'animate-spin' : ''} />
              <span>Refresh</span>
            </button>
          </div>
        </div>

        {error && (
          <div className="mb-6 p-4 rounded-xl text-sm font-bold border bg-red-500/10 border-red-500/20 text-red-400">
            {error}
          </div>
        )}

        {lastRefresh && (
          <div className="mb-6 text-xs text-slate-500">
            Last updated: {lastRefresh.toLocaleTimeString()}
          </div>
        )}

        {/* Core Services */}
        <div className="mb-8">
          <h2 className="text-xl font-bold mb-4 flex items-center">
            <Server className="mr-2 text-purple-400" size={20} />
            Core Services
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Database */}
            <div className="bg-white/2 border border-white/5 p-6 rounded-2xl">
              <div className="flex items-center justify-between mb-4">
                <div className="w-10 h-10 bg-white/5 rounded-xl flex items-center justify-center">
                  <Database className="text-cyan-400" size={20} />
                </div>
                {getStatusIcon(health?.checks?.database)}
              </div>
              <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Database</p>
              <p className={`text-lg font-bold ${getStatusColor(health?.checks?.database)}`}>
                {health?.checks?.database || 'Unknown'}
              </p>
            </div>

            {/* API Service */}
            <div className="bg-white/2 border border-white/5 p-6 rounded-2xl">
              <div className="flex items-center justify-between mb-4">
                <div className="w-10 h-10 bg-white/5 rounded-xl flex items-center justify-center">
                  <Network className="text-emerald-400" size={20} />
                </div>
                {getStatusIcon(health?.status)}
              </div>
              <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest">API Service</p>
              <p className={`text-lg font-bold ${getStatusColor(health?.status)}`}>
                {health?.status || 'Unknown'}
              </p>
            </div>

            {/* Version */}
            <div className="bg-white/2 border border-white/5 p-6 rounded-2xl">
              <div className="flex items-center justify-between mb-4">
                <div className="w-10 h-10 bg-white/5 rounded-xl flex items-center justify-center">
                  <Shield className="text-violet-400" size={20} />
                </div>
              </div>
              <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Version</p>
              <p className="text-lg font-bold text-white">{health?.version || '1.0.0'}</p>
            </div>

            {/* Service Name */}
            <div className="bg-white/2 border border-white/5 p-6 rounded-2xl">
              <div className="flex items-center justify-between mb-4">
                <div className="w-10 h-10 bg-white/5 rounded-xl flex items-center justify-center">
                  <Cpu className="text-amber-400" size={20} />
                </div>
              </div>
              <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Service</p>
              <p className="text-lg font-bold text-white">{health?.service || 'vedrix-backend'}</p>
            </div>
          </div>
        </div>

        {/* AI Providers */}
        {aiHealth && (
          <div className="mb-8">
            <h2 className="text-xl font-bold mb-4 flex items-center">
              <Zap className="mr-2 text-amber-400" size={20} />
              AI Providers
            </h2>
            <div className="bg-white/2 border border-white/5 rounded-3xl overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left">
                  <thead>
                    <tr className="text-[10px] font-black text-slate-500 uppercase tracking-widest border-b border-white/5">
                      <th className="px-8 py-4">Provider</th>
                      <th className="px-8 py-4">Status</th>
                      <th className="px-8 py-4">Circuit Breaker</th>
                      <th className="px-8 py-4">Description</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {aiHealth.routes && Object.entries(aiHealth.routes).map(([taskType, route]) => (
                      <tr key={taskType} className="hover:bg-white/[0.03] transition-colors">
                        <td className="px-8 py-5">
                          <p className="font-bold text-white text-sm">{taskType}</p>
                        </td>
                        <td className="px-8 py-5">
                          {route.providers.map((provider, idx) => {
                            const providerName = provider.split('/')[0];
                            const status = getProviderStatus(providerName);
                            return (
                              <span key={idx} className={`inline-flex items-center px-2 py-1 rounded-full text-[9px] font-black uppercase mr-2 ${
                                status === 'healthy' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                                status === 'degraded' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' :
                                'bg-red-500/10 text-red-400 border border-red-500/20'
                              }`}>
                                {provider}
                              </span>
                            );
                          })}
                        </td>
                        <td className="px-8 py-5">
                          {aiHealth.circuit_breakers && Object.entries(aiHealth.circuit_breakers).map(([name, cb]) => (
                            <div key={name} className="text-xs text-slate-400">
                              <span className="font-bold text-white">{name}:</span> {cb.state}
                              {cb.failure_count > 0 && (
                                <span className="text-red-400 ml-2">({cb.failure_count} failures)</span>
                              )}
                            </div>
                          ))}
                        </td>
                        <td className="px-8 py-5 text-sm text-slate-400">{route.description}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* Audit Statistics */}
        {auditStats && (
          <div className="mb-8">
            <h2 className="text-xl font-bold mb-4 flex items-center">
              <Activity className="mr-2 text-emerald-400" size={20} />
              Audit Statistics
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
              <div className="bg-white/2 border border-white/5 p-6 rounded-2xl">
                <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Total Logs</p>
                <p className="text-2xl font-bold text-white">{auditStats.total_logs}</p>
              </div>
              <div className="bg-white/2 border border-white/5 p-6 rounded-2xl">
                <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Last 24h</p>
                <p className="text-2xl font-bold text-emerald-400">{auditStats.recent_24h}</p>
              </div>
              <div className="bg-white/2 border border-white/5 p-6 rounded-2xl">
                <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Top Action</p>
                <p className="text-sm font-bold text-white truncate">
                  {auditStats.top_actions[0]?.action || 'N/A'}
                </p>
              </div>
              <div className="bg-white/2 border border-white/5 p-6 rounded-2xl">
                <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Active Users</p>
                <p className="text-2xl font-bold text-white">{auditStats.top_users.length}</p>
              </div>
            </div>

            {/* Top Actions */}
            {auditStats.top_actions.length > 0 && (
              <div className="bg-white/2 border border-white/5 rounded-3xl overflow-hidden">
                <div className="px-8 py-4 border-b border-white/5">
                  <h3 className="font-bold text-white text-sm">Top Actions</h3>
                </div>
                <div className="p-6">
                  <div className="space-y-3">
                    {auditStats.top_actions.slice(0, 5).map((action, idx) => (
                      <div key={idx} className="flex items-center justify-between">
                        <span className="text-sm text-slate-300 font-mono">{action.action}</span>
                        <span className="text-sm font-bold text-purple-400">{action.count}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Platform Metrics */}
        {teamAnalytics && (
          <div className="mb-8">
            <h2 className="text-xl font-bold mb-4 flex items-center">
              <HardDrive className="mr-2 text-cyan-400" size={20} />
              Platform Metrics
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-white/2 border border-white/5 p-6 rounded-2xl">
                <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Total Sessions</p>
                <p className="text-2xl font-bold text-white">{teamAnalytics.summary.total_sessions}</p>
              </div>
              <div className="bg-white/2 border border-white/5 p-6 rounded-2xl">
                <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Completed</p>
                <p className="text-2xl font-bold text-emerald-400">{teamAnalytics.summary.completed_sessions}</p>
              </div>
              <div className="bg-white/2 border border-white/5 p-6 rounded-2xl">
                <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Avg Score</p>
                <p className="text-2xl font-bold text-white">{teamAnalytics.summary.avg_score}</p>
              </div>
              <div className="bg-white/2 border border-white/5 p-6 rounded-2xl">
                <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Pass Rate</p>
                <p className="text-2xl font-bold text-white">{teamAnalytics.summary.pass_rate}%</p>
              </div>
            </div>
          </div>
        )}

        {/* System Info */}
        <div className="bg-white/2 border border-white/5 rounded-3xl p-6">
          <h3 className="font-bold text-white mb-4 flex items-center">
            <Clock className="mr-2 text-slate-400" size={16} />
            System Information
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Environment</p>
              <p className="text-white font-bold">{import.meta.env.MODE || 'development'}</p>
            </div>
            <div>
              <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest">API URL</p>
              <p className="text-white font-bold truncate">{import.meta.env.VITE_API_URL || 'http://localhost:8000'}</p>
            </div>
            <div>
              <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Auto Refresh</p>
              <p className="text-emerald-400 font-bold">Every 30s</p>
            </div>
            <div>
              <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Status</p>
              <p className={`font-bold ${getStatusColor(health?.status)}`}>
                {health?.status || 'Checking...'}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SystemHealth;
