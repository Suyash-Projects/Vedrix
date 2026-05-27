import { useState, useEffect, useCallback, Fragment } from 'react';
import { motion } from 'framer-motion';
import { Search, Download, ChevronDown, ChevronRight, RefreshCw, Activity, Filter } from 'lucide-react';
import apiClient from '../services/api';

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: 'easeOut' } }
};

const AGENT_COLORS = [
  'text-purple-400', 'text-emerald-400', 'text-amber-400', 'text-blue-400',
  'text-pink-400', 'text-cyan-400', 'text-orange-400', 'text-indigo-400',
];

const getAgentColor = (name, agentMap) => {
  if (!agentMap.has(name)) {
    agentMap.set(name, AGENT_COLORS[agentMap.size % AGENT_COLORS.length]);
  }
  return agentMap.get(name);
};

const ObservabilityPanel = () => {
  const [traces, setTraces] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [expandedRow, setExpandedRow] = useState(null);
  const [filters, setFilters] = useState({
    agent_name: '',
    session_id: '',
    action_type: '',
    date_from: '',
    date_to: '',
  });
  const [agentNames, setAgentNames] = useState([]);
  const [actionTypes, setActionTypes] = useState([]);
  const [showFilters, setShowFilters] = useState(false);
  const agentColorMap = new Map();

  const fetchTraces = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      params.append('page', page);
      params.append('per_page', 20);
      if (filters.agent_name) params.append('agent_name', filters.agent_name);
      if (filters.session_id) params.append('session_id', filters.session_id);
      if (filters.action_type) params.append('action_type', filters.action_type);
      if (filters.date_from) params.append('date_from', filters.date_from);
      if (filters.date_to) params.append('date_to', filters.date_to);

      const res = await apiClient.get(`/admin/audit-trail?${params.toString()}`);
      const data = res.data;
      setTraces(data.entries || data.traces || data || []);
      setTotalPages(data.total_pages || 1);
      // Extract unique agent names and action types for filters
      const entries = data.entries || data.traces || data || [];
      const names = [...new Set(entries.map(e => e.agent_name).filter(Boolean))];
      const types = [...new Set(entries.map(e => e.action_type).filter(Boolean))];
      if (names.length) setAgentNames(prev => [...new Set([...prev, ...names])]);
      if (types.length) setActionTypes(prev => [...new Set([...prev, ...types])]);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load audit trail');
    } finally {
      setLoading(false);
    }
  }, [page, filters]);

  useEffect(() => {
    Promise.resolve().then(() => {
      fetchTraces();
    });
  }, [fetchTraces]);

  const handleExport = async (sessionId) => {
    try {
      const res = await apiClient.get(`/admin/audit-trail/export/${sessionId}`, {
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `audit-trail-${sessionId}.json`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      console.error('Export failed:', err);
    }
  };

  if (error && !traces.length) {
    return (
      <div className="min-h-screen bg-[#020617] text-white flex items-center justify-center">
        <div className="text-center space-y-4">
          <p className="text-red-400 text-lg font-bold">{error}</p>
          <button onClick={fetchTraces}
            className="inline-flex items-center gap-2 bg-purple-600 hover:bg-purple-500 text-white font-bold px-6 py-3 rounded-2xl transition-all"
            aria-label="Retry loading audit trail"
          >
            <RefreshCw size={16} /> Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#020617] text-white font-sans">
      <div className="fixed bottom-0 left-[-5%] w-[30%] h-[40%] bg-indigo-900/10 blur-[150px] rounded-full pointer-events-none" />

      <div className="max-w-7xl mx-auto px-8 py-12 space-y-8 relative z-10">
        {/* Header */}
        <motion.div variants={fadeUp} initial="hidden" animate="visible">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 bg-gradient-to-tr from-purple-600 to-indigo-400 rounded-2xl flex items-center justify-center shadow-xl shadow-purple-900/30">
                <Activity size={24} className="text-white" />
              </div>
              <div>
                <h1 className="text-3xl font-black text-white tracking-tight">Audit Trail</h1>
                <p className="text-slate-500 text-sm">Agent observability and trace inspection</p>
              </div>
            </div>
            <button
              onClick={() => setShowFilters(!showFilters)}
              className="flex items-center gap-2 bg-white/5 border border-white/10 px-4 py-2.5 rounded-xl text-slate-300 hover:bg-white/10 transition-all text-sm font-bold"
            >
              <Filter size={14} /> Filters
            </button>
          </div>
        </motion.div>

        {/* Filters */}
        {showFilters && (
          <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }}
            className="bg-white/[0.03] border border-white/5 rounded-3xl p-6"
          >
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
              <div>
                <label className="block text-[10px] font-black text-slate-500 uppercase tracking-widest mb-1">Agent</label>
                <select value={filters.agent_name} onChange={e => setFilters({...filters, agent_name: e.target.value})}
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-white text-sm outline-none focus:ring-2 focus:ring-purple-500"
                  aria-label="Filter by agent name"
                >
                  <option value="">All Agents</option>
                  {agentNames.map(n => <option key={n} value={n}>{n}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-[10px] font-black text-slate-500 uppercase tracking-widest mb-1">Session ID</label>
                <div className="relative">
                  <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                  <input value={filters.session_id} onChange={e => setFilters({...filters, session_id: e.target.value})}
                    className="w-full bg-white/5 border border-white/10 rounded-xl pl-9 pr-3 py-2 text-white text-sm outline-none focus:ring-2 focus:ring-purple-500"
                    placeholder="Search..." aria-label="Filter by session ID"
                  />
                </div>
              </div>
              <div>
                <label className="block text-[10px] font-black text-slate-500 uppercase tracking-widest mb-1">Action Type</label>
                <select value={filters.action_type} onChange={e => setFilters({...filters, action_type: e.target.value})}
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-white text-sm outline-none focus:ring-2 focus:ring-purple-500"
                  aria-label="Filter by action type"
                >
                  <option value="">All Types</option>
                  {actionTypes.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-[10px] font-black text-slate-500 uppercase tracking-widest mb-1">From</label>
                <input type="date" value={filters.date_from} onChange={e => setFilters({...filters, date_from: e.target.value})}
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-white text-sm outline-none focus:ring-2 focus:ring-purple-500"
                  aria-label="Filter from date"
                />
              </div>
              <div>
                <label className="block text-[10px] font-black text-slate-500 uppercase tracking-widest mb-1">To</label>
                <input type="date" value={filters.date_to} onChange={e => setFilters({...filters, date_to: e.target.value})}
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-white text-sm outline-none focus:ring-2 focus:ring-purple-500"
                  aria-label="Filter to date"
                />
              </div>
            </div>
          </motion.div>
        )}

        {/* Table */}
        <div className="bg-white/[0.03] border border-white/5 rounded-3xl overflow-hidden">
          {loading ? (
            <div className="p-8 space-y-3">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="h-12 bg-white/5 rounded-xl animate-pulse" />
              ))}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left" role="table">
                <thead>
                  <tr className="border-b border-white/5">
                    <th className="px-6 py-4 text-[10px] font-black text-slate-500 uppercase tracking-widest" />
                    <th className="px-6 py-4 text-[10px] font-black text-slate-500 uppercase tracking-widest">Agent</th>
                    <th className="px-6 py-4 text-[10px] font-black text-slate-500 uppercase tracking-widest">Action</th>
                    <th className="px-6 py-4 text-[10px] font-black text-slate-500 uppercase tracking-widest">Session</th>
                    <th className="px-6 py-4 text-[10px] font-black text-slate-500 uppercase tracking-widest">Timestamp</th>
                    <th className="px-6 py-4 text-[10px] font-black text-slate-500 uppercase tracking-widest">Export</th>
                  </tr>
                </thead>
                <tbody>
                  {traces.map((trace, idx) => {
                    const agentColor = getAgentColor(trace.agent_name, agentColorMap);
                    const isExpanded = expandedRow === idx;
                    return (
                      <Fragment key={trace.id || idx}>
                        <tr
                          className="border-b border-white/5 hover:bg-white/[0.02] cursor-pointer transition-colors"
                          onClick={() => setExpandedRow(isExpanded ? null : idx)}
                          role="row"
                        >
                          <td className="px-6 py-3">
                            {isExpanded ? <ChevronDown size={14} className="text-slate-500" /> : <ChevronRight size={14} className="text-slate-500" />}
                          </td>
                          <td className={`px-6 py-3 font-bold text-sm ${agentColor}`}>{trace.agent_name || '—'}</td>
                          <td className="px-6 py-3 text-white text-sm">{trace.action_type || '—'}</td>
                          <td className="px-6 py-3 text-slate-400 text-xs font-mono">{trace.session_id?.slice(0, 8) || '—'}</td>
                          <td className="px-6 py-3 text-slate-500 text-xs">{trace.timestamp ? new Date(trace.timestamp).toLocaleString() : '—'}</td>
                          <td className="px-6 py-3">
                            {trace.session_id && (
                              <button
                                onClick={(e) => { e.stopPropagation(); handleExport(trace.session_id); }}
                                className="text-slate-500 hover:text-purple-400 transition-colors"
                                aria-label={`Export trace for session ${trace.session_id}`}
                              >
                                <Download size={14} />
                              </button>
                            )}
                          </td>
                        </tr>
                        {isExpanded && (
                          <tr className="bg-white/[0.01]">
                            <td colSpan={6} className="px-6 py-4">
                              <pre className="text-xs text-slate-400 bg-white/[0.02] border border-white/5 rounded-xl p-4 overflow-x-auto max-h-[200px]">
                                {JSON.stringify(trace, null, 2)}
                              </pre>
                            </td>
                          </tr>
                        )}
                      </Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Pagination */}
        <div className="flex items-center justify-center gap-2">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page <= 1}
            className="px-4 py-2 bg-white/5 border border-white/10 rounded-xl text-slate-300 text-sm font-bold hover:bg-white/10 transition-all disabled:opacity-30"
          >
            Previous
          </button>
          <span className="text-slate-500 text-sm px-4">Page {page} of {totalPages}</span>
          <button
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
            className="px-4 py-2 bg-white/5 border border-white/10 rounded-xl text-slate-300 text-sm font-bold hover:bg-white/10 transition-all disabled:opacity-30"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
};

export default ObservabilityPanel;
