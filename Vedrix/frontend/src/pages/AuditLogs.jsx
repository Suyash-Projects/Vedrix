import { useState, useEffect, useCallback } from 'react';
import {
  FileText,
  Filter,
  User,
  Globe,
  RefreshCcw,
  ChevronLeft,
  ChevronRight,
  Eye
} from 'lucide-react';
import apiClient from '../services/api';
import { useNavigate } from 'react-router-dom';
import useToastStore from '../store/useToastStore';

const AuditLogs = () => {
  const navigate = useNavigate();
  const addToast = useToastStore((s) => s.addToast);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filters, setFilters] = useState({
    user_id: '',
    action: '',
    start_date: '',
    end_date: '',
    limit: 50,
    offset: 0,
  });
  const [stats, setStats] = useState(null);
  const [showFilters, setShowFilters] = useState(false);

  const fetchLogs = useCallback(async () => {
    try {
      setLoading(true);
      setError('');

      const params = {};
      if (filters.user_id) params.user_id = filters.user_id;
      if (filters.action) params.action = filters.action;
      if (filters.start_date) params.start_date = filters.start_date;
      if (filters.end_date) params.end_date = filters.end_date;
      params.limit = filters.limit;
      params.offset = filters.offset;

      const [logsRes, statsRes] = await Promise.allSettled([
        apiClient.get('/admin/audit-logs', { params }),
        apiClient.get('/admin/audit-logs/stats'),
      ]);

      if (logsRes.status === 'fulfilled') {
        setLogs(logsRes.value.data);
      } else {
        setError('Failed to fetch audit logs');
      }

      if (statsRes.status === 'fulfilled') {
        setStats(statsRes.value.data);
      }
    } catch {
      setError('Failed to fetch audit logs');
    } finally {
      setLoading(false);
    }
  }, [filters.user_id, filters.action, filters.start_date, filters.end_date, filters.limit, filters.offset]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchLogs();
  }, [fetchLogs]);

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  const applyFilters = () => {
    setFilters(prev => ({ ...prev, offset: 0 }));
    fetchLogs();
  };

  const clearFilters = () => {
    setFilters({
      user_id: '',
      action: '',
      start_date: '',
      end_date: '',
      limit: 50,
      offset: 0,
    });
    fetchLogs();
  };

  const handleNextPage = () => {
    setFilters(prev => ({ ...prev, offset: prev.offset + prev.limit }));
  };

  const handlePrevPage = () => {
    setFilters(prev => ({ ...prev, offset: Math.max(0, prev.offset - prev.limit) }));
  };

  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleString();
  };

  const getActionBadge = (action) => {
    if (action.includes('POST') || action.includes('create')) {
      return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
    }
    if (action.includes('PUT') || action.includes('PATCH') || action.includes('update')) {
      return 'bg-amber-500/10 text-amber-400 border-amber-500/20';
    }
    if (action.includes('DELETE') || action.includes('delete')) {
      return 'bg-red-500/10 text-red-400 border-red-500/20';
    }
    return 'bg-slate-500/10 text-slate-400 border-slate-500/20';
  };

  if (loading && logs.length === 0) {
    return (
      <div className="min-h-screen bg-[#020617] flex items-center justify-center">
        <div className="text-center">
          <RefreshCcw size={32} className="animate-spin text-purple-400 mx-auto mb-4" />
          <p className="text-slate-400">Loading audit logs...</p>
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
            <h1 className="text-3xl font-extrabold tracking-tight">Audit Logs</h1>
            <p className="text-slate-500 mt-1">Track all system actions and user activity</p>
          </div>
          <div className="flex items-center space-x-3">
            <button
              onClick={() => navigate('/admin')}
              className="flex items-center space-x-2 bg-white/5 border border-white/10 text-slate-300 px-4 py-2 rounded-xl text-sm font-bold hover:bg-white/10 transition-all"
            >
              <span>Back to Admin</span>
            </button>
            <button
              onClick={fetchLogs}
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

        {/* Stats Cards */}
        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
            <div className="bg-white/2 border border-white/5 p-6 rounded-2xl">
              <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Total Logs</p>
              <p className="text-2xl font-bold text-white">{stats.total_logs}</p>
            </div>
            <div className="bg-white/2 border border-white/5 p-6 rounded-2xl">
              <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Last 24h</p>
              <p className="text-2xl font-bold text-emerald-400">{stats.recent_24h}</p>
            </div>
            <div className="bg-white/2 border border-white/5 p-6 rounded-2xl">
              <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Top Action</p>
              <p className="text-sm font-bold text-white truncate">
                {stats.top_actions[0]?.action || 'N/A'}
              </p>
            </div>
            <div className="bg-white/2 border border-white/5 p-6 rounded-2xl">
              <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Active Users</p>
              <p className="text-2xl font-bold text-white">{stats.top_users.length}</p>
            </div>
          </div>
        )}

        {/* Filters */}
        <div className="mb-6">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className="flex items-center space-x-2 bg-white/5 border border-white/10 text-slate-300 px-4 py-2 rounded-xl text-sm font-bold hover:bg-white/10 transition-all"
          >
            <Filter size={16} />
            <span>{showFilters ? 'Hide Filters' : 'Show Filters'}</span>
          </button>

          {showFilters && (
            <div className="mt-4 bg-white/2 border border-white/5 rounded-2xl p-6">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <div>
                  <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500 mb-1.5">
                    User ID
                  </label>
                  <input
                    type="number"
                    value={filters.user_id}
                    onChange={(e) => handleFilterChange('user_id', e.target.value)}
                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-slate-500 focus:ring-1 focus:ring-purple-500 outline-none"
                    placeholder="Filter by user ID"
                  />
                </div>
                <div>
                  <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500 mb-1.5">
                    Action
                  </label>
                  <input
                    type="text"
                    value={filters.action}
                    onChange={(e) => handleFilterChange('action', e.target.value)}
                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-slate-500 focus:ring-1 focus:ring-purple-500 outline-none"
                    placeholder="Filter by action"
                  />
                </div>
                <div>
                  <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500 mb-1.5">
                    Start Date
                  </label>
                  <input
                    type="datetime-local"
                    value={filters.start_date}
                    onChange={(e) => handleFilterChange('start_date', e.target.value)}
                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-slate-500 focus:ring-1 focus:ring-purple-500 outline-none"
                  />
                </div>
                <div>
                  <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500 mb-1.5">
                    End Date
                  </label>
                  <input
                    type="datetime-local"
                    value={filters.end_date}
                    onChange={(e) => handleFilterChange('end_date', e.target.value)}
                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-slate-500 focus:ring-1 focus:ring-purple-500 outline-none"
                  />
                </div>
              </div>
              <div className="flex justify-end space-x-3 mt-4">
                <button
                  onClick={clearFilters}
                  className="px-6 py-3 bg-white/5 hover:bg-white/10 text-slate-400 rounded-xl text-sm font-bold transition-all"
                >
                  Clear
                </button>
                <button
                  onClick={applyFilters}
                  className="px-6 py-3 bg-purple-600 hover:bg-purple-500 text-white rounded-xl text-sm font-bold shadow-lg shadow-purple-900/30 transition-all active:scale-95"
                >
                  Apply Filters
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Logs Table */}
        <div className="bg-white/2 border border-white/5 rounded-3xl overflow-hidden">
          <div className="px-8 py-6 border-b border-white/5 flex justify-between items-center">
            <h2 className="font-bold text-white flex items-center">
              <FileText size={18} className="mr-2 text-purple-400" />
              Audit Log Entries ({logs.length})
            </h2>
          </div>

          {logs.length === 0 ? (
            <div className="p-12 text-center text-slate-500">No audit logs found.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead>
                  <tr className="text-[10px] font-black text-slate-500 uppercase tracking-widest border-b border-white/5">
                    <th className="px-8 py-4">Timestamp</th>
                    <th className="px-8 py-4">User</th>
                    <th className="px-8 py-4">Action</th>
                    <th className="px-8 py-4">Target</th>
                    <th className="px-8 py-4">IP Address</th>
                    <th className="px-8 py-4">Status</th>
                    <th className="px-8 py-4 text-right">Details</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {logs.map((log) => (
                    <tr key={log.id} className="hover:bg-white/[0.03] transition-colors">
                      <td className="px-8 py-5 text-sm text-slate-400 font-mono">
                        {formatTimestamp(log.timestamp)}
                      </td>
                      <td className="px-8 py-5">
                        {log.user_id ? (
                          <div className="flex items-center space-x-2">
                            <User size={14} className="text-slate-500" />
                            <span className="text-sm text-white font-bold">User #{log.user_id}</span>
                          </div>
                        ) : (
                          <span className="text-sm text-slate-500">Anonymous</span>
                        )}
                      </td>
                      <td className="px-8 py-5">
                        <span className={`px-2 py-1 rounded-full text-[9px] font-black uppercase border ${getActionBadge(log.action)}`}>
                          {log.action}
                        </span>
                      </td>
                      <td className="px-8 py-5 text-sm text-slate-300 font-mono truncate max-w-xs">
                        {log.target}
                      </td>
                      <td className="px-8 py-5">
                        <div className="flex items-center space-x-2">
                          <Globe size={14} className="text-slate-500" />
                          <span className="text-sm text-slate-400">{log.ip_address || 'N/A'}</span>
                        </div>
                      </td>
                      <td className="px-8 py-5">
                        {log.status_code ? (
                          <span className={`text-sm font-bold ${
                            log.status_code < 300 ? 'text-emerald-400' : 'text-red-400'
                          }`}>
                            {log.status_code}
                          </span>
                        ) : (
                          <span className="text-sm text-slate-500">—</span>
                        )}
                      </td>
                      <td className="px-8 py-5 text-right">
                        {log.details && (
                          <button
                            onClick={() => addToast({ type: 'info', title: 'Log details', message: log.details, duration: 8000 })}
                            className="text-slate-500 hover:text-purple-400 p-1.5 rounded-lg hover:bg-purple-500/10 transition-colors"
                            title="View details"
                          >
                            <Eye size={14} />
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination */}
          <div className="px-8 py-4 border-t border-white/5 flex justify-between items-center">
            <p className="text-sm text-slate-500">
              Showing {logs.length} logs (offset: {filters.offset})
            </p>
            <div className="flex items-center space-x-2">
              <button
                onClick={handlePrevPage}
                disabled={filters.offset === 0}
                className="flex items-center space-x-1 bg-white/5 border border-white/10 text-slate-300 px-3 py-2 rounded-lg text-sm font-bold hover:bg-white/10 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronLeft size={16} />
                <span>Previous</span>
              </button>
              <button
                onClick={handleNextPage}
                disabled={logs.length < filters.limit}
                className="flex items-center space-x-1 bg-white/5 border border-white/10 text-slate-300 px-3 py-2 rounded-lg text-sm font-bold hover:bg-white/10 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <span>Next</span>
                <ChevronRight size={16} />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AuditLogs;
