import { useState, useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Columns3, RefreshCw, Clock, CheckSquare, ArrowRight, History } from 'lucide-react';
import apiClient from '../services/api';

const COLUMNS = [
  { id: 'invited', label: 'Invited', color: 'border-slate-500/30' },
  { id: 'scheduled', label: 'Scheduled', color: 'border-blue-500/30' },
  { id: 'in_progress', label: 'In Progress', color: 'border-purple-500/30' },
  { id: 'evaluated', label: 'Evaluated', color: 'border-indigo-500/30' },
  { id: 'shortlisted', label: 'Shortlisted', color: 'border-emerald-500/30' },
  { id: 'decided', label: 'Decided', color: 'border-amber-500/30' },
];

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: 'easeOut' } }
};

const CandidateCard = ({ candidate, selected, onSelect }) => {
  const [showHistory, setShowHistory] = useState(false);
  const timeInState = candidate.time_in_state || '—';

  return (
    <div
      draggable
      onDragStart={(e) => {
        e.dataTransfer.setData('candidateId', candidate.candidate_id);
        e.dataTransfer.setData('fromState', candidate.state);
      }}
      className={`bg-white/[0.03] border rounded-2xl p-4 cursor-grab active:cursor-grabbing hover:bg-white/[0.05] transition-all relative group ${
        selected ? 'border-purple-500/50 ring-1 ring-purple-500/30' : 'border-white/5'
      }`}
      role="listitem"
      aria-label={`${candidate.name}, score ${candidate.score ?? '—'}, ${timeInState} in state`}
    >
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={selected}
            onChange={() => onSelect(candidate.candidate_id)}
            className="w-4 h-4 rounded border-white/20 bg-white/5 text-purple-600 focus:ring-purple-500"
            aria-label={`Select ${candidate.name}`}
          />
          <p className="text-white font-bold text-sm truncate">{candidate.name}</p>
        </div>
        <button
          onClick={() => setShowHistory(!showHistory)}
          className="text-slate-500 hover:text-purple-400 transition-colors opacity-0 group-hover:opacity-100"
          aria-label="Show transition history"
        >
          <History size={14} />
        </button>
      </div>
      <div className="flex items-center justify-between">
        <span className="text-purple-400 font-black text-xs">{candidate.score ?? '—'}/100</span>
        <span className="text-slate-500 text-[10px] flex items-center gap-1">
          <Clock size={10} /> {timeInState}
        </span>
      </div>
      {showHistory && candidate.transition_history && (
        <div className="mt-3 pt-3 border-t border-white/5 space-y-1">
          {candidate.transition_history.map((t, i) => (
            <p key={i} className="text-[10px] text-slate-500">
              {t.from} → {t.to} <span className="text-slate-600">({t.timestamp})</span>
            </p>
          ))}
        </div>
      )}
    </div>
  );
};

const WorkflowKanban = () => {
  const { driveId } = useParams();
  const [candidates, setCandidates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selected, setSelected] = useState(new Set());
  const [bulkTarget, setBulkTarget] = useState('');
  const [transitioning, setTransitioning] = useState(false);

  const fetchPipeline = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.get(`/hr/drives/${driveId}/pipeline`);
      setCandidates(res.data?.candidates || res.data || []);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load pipeline');
    } finally {
      setLoading(false);
    }
  }, [driveId]);

  useEffect(() => { fetchPipeline(); }, [fetchPipeline]);

  const handleTransition = async (candidateId, toState) => {
    try {
      await apiClient.post(`/hr/drives/${driveId}/workflow/${candidateId}/transition`, {
        to_state: toState
      });
      setCandidates(prev => prev.map(c =>
        c.candidate_id === candidateId ? { ...c, state: toState } : c
      ));
    } catch (err) {
      console.error('Transition failed:', err);
    }
  };

  const handleDrop = useCallback((e, toState) => {
    e.preventDefault();
    const candidateId = e.dataTransfer.getData('candidateId');
    if (candidateId) handleTransition(candidateId, toState);
  }, [driveId]);

  const handleDragOver = (e) => e.preventDefault();

  const toggleSelect = (id) => {
    setSelected(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleBulkTransition = async () => {
    if (!bulkTarget || selected.size === 0) return;
    setTransitioning(true);
    try {
      await Promise.all(
        [...selected].map(id => handleTransition(id, bulkTarget))
      );
      setSelected(new Set());
      setBulkTarget('');
    } finally {
      setTransitioning(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#020617] text-white flex items-center justify-center">
        <div className="w-12 h-12 border-4 border-purple-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-[#020617] text-white flex items-center justify-center">
        <div className="text-center space-y-4">
          <p className="text-red-400 text-lg font-bold">{error}</p>
          <button onClick={fetchPipeline}
            className="inline-flex items-center gap-2 bg-purple-600 hover:bg-purple-500 text-white font-bold px-6 py-3 rounded-2xl transition-all"
            aria-label="Retry loading pipeline"
          >
            <RefreshCw size={16} /> Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#020617] text-white font-sans">
      <div className="fixed top-0 left-[-5%] w-[30%] h-[40%] bg-purple-900/10 blur-[150px] rounded-full pointer-events-none" />

      <div className="max-w-[1400px] mx-auto px-6 py-12 space-y-6 relative z-10">
        {/* Header */}
        <motion.div variants={fadeUp} initial="hidden" animate="visible">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 bg-gradient-to-tr from-purple-600 to-indigo-400 rounded-2xl flex items-center justify-center shadow-xl shadow-purple-900/30">
                <Columns3 size={24} className="text-white" />
              </div>
              <div>
                <h1 className="text-3xl font-black text-white tracking-tight">Pipeline</h1>
                <p className="text-slate-500 text-sm">Drag candidates between stages</p>
              </div>
            </div>

            {/* Bulk Actions */}
            {selected.size > 0 && (
              <div className="flex items-center gap-3 bg-white/[0.03] border border-white/10 rounded-2xl px-4 py-2">
                <span className="text-slate-400 text-sm font-bold">
                  <CheckSquare size={14} className="inline mr-1" />{selected.size} selected
                </span>
                <select
                  value={bulkTarget}
                  onChange={(e) => setBulkTarget(e.target.value)}
                  className="bg-white/5 border border-white/10 rounded-xl px-3 py-1.5 text-white text-sm outline-none focus:ring-2 focus:ring-purple-500"
                  aria-label="Select target state for bulk transition"
                >
                  <option value="">Move to...</option>
                  {COLUMNS.map(col => <option key={col.id} value={col.id}>{col.label}</option>)}
                </select>
                <button
                  onClick={handleBulkTransition}
                  disabled={!bulkTarget || transitioning}
                  className="flex items-center gap-1 bg-purple-600 hover:bg-purple-500 text-white font-bold px-4 py-1.5 rounded-xl text-sm transition-all disabled:opacity-50"
                >
                  <ArrowRight size={14} /> Move
                </button>
              </div>
            )}
          </div>
        </motion.div>

        {/* Kanban Board */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4 overflow-x-auto">
          {COLUMNS.map(col => {
            const colCandidates = candidates.filter(c => c.state === col.id);
            return (
              <div
                key={col.id}
                className={`bg-white/[0.02] border ${col.color} rounded-3xl p-4 min-h-[400px]`}
                onDrop={(e) => handleDrop(e, col.id)}
                onDragOver={handleDragOver}
                role="list"
                aria-label={`${col.label} column, ${colCandidates.length} candidates`}
              >
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-xs font-black uppercase text-slate-400 tracking-widest">{col.label}</h3>
                  <span className="text-[10px] font-black text-slate-600 bg-white/5 px-2 py-0.5 rounded-full">
                    {colCandidates.length}
                  </span>
                </div>
                <div className="space-y-3">
                  {colCandidates.map(c => (
                    <CandidateCard
                      key={c.candidate_id}
                      candidate={c}
                      selected={selected.has(c.candidate_id)}
                      onSelect={toggleSelect}
                    />
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default WorkflowKanban;
