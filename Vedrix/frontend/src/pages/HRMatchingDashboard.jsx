import { useState, useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Trophy, X, RefreshCw, ArrowUpDown, Star, ThumbsDown } from 'lucide-react';
import apiClient from '../services/api';

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  visible: (i) => ({ opacity: 1, y: 0, transition: { delay: i * 0.06, duration: 0.5, ease: 'easeOut' } })
};

const SkeletonRow = () => (
  <div className="bg-white/[0.03] border border-white/5 rounded-2xl p-4 animate-pulse flex items-center gap-4">
    <div className="w-10 h-10 bg-white/5 rounded-full" />
    <div className="flex-1 space-y-2">
      <div className="h-4 bg-white/5 rounded w-1/3" />
      <div className="h-3 bg-white/5 rounded w-1/2" />
    </div>
    <div className="h-8 w-16 bg-white/5 rounded-xl" />
  </div>
);

const ScoreBar = ({ score, label, color }) => (
  <div className="flex items-center gap-2">
    <span className="text-[10px] text-slate-500 w-20 shrink-0">{label}</span>
    <div className="flex-1 h-2 bg-white/5 rounded-full overflow-hidden">
      <div className={`h-full ${color} rounded-full`} style={{ width: `${score}%` }} />
    </div>
    <span className="text-[10px] text-slate-400 font-bold w-8 text-right">{score}</span>
  </div>
);

const ExplanationModal = ({ candidate, onClose }) => {
  if (!candidate) return null;
  const contributing = candidate.contributing_factors || [];
  const disqualifying = candidate.disqualifying_factors || [];

  return (
    <div className="fixed inset-0 z-[200] bg-black/70 flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-label="Match explanation">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="bg-[#0f172a] border border-white/10 rounded-3xl w-full max-w-lg p-8 space-y-6"
      >
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-black text-white">Match Explanation</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-white transition-colors" aria-label="Close modal">
            <X size={20} />
          </button>
        </div>
        <div className="space-y-4">
          <div>
            <h3 className="text-xs font-black uppercase text-emerald-400 tracking-widest mb-2 flex items-center gap-2">
              <Star size={14} /> Top Contributing Factors
            </h3>
            {contributing.slice(0, 3).map((f, i) => (
              <div key={i} className="bg-emerald-500/5 border border-emerald-500/10 rounded-xl p-3 mb-2">
                <p className="text-white text-sm font-bold">{f.factor}</p>
                <p className="text-slate-400 text-xs">{f.explanation}</p>
              </div>
            ))}
          </div>
          <div>
            <h3 className="text-xs font-black uppercase text-red-400 tracking-widest mb-2 flex items-center gap-2">
              <ThumbsDown size={14} /> Disqualifying Factors
            </h3>
            {disqualifying.slice(0, 2).map((f, i) => (
              <div key={i} className="bg-red-500/5 border border-red-500/10 rounded-xl p-3 mb-2">
                <p className="text-white text-sm font-bold">{f.factor}</p>
                <p className="text-slate-400 text-xs">{f.explanation}</p>
              </div>
            ))}
            {disqualifying.length === 0 && (
              <p className="text-slate-500 text-sm">No disqualifying factors found.</p>
            )}
          </div>
        </div>
      </motion.div>
    </div>
  );
};

const HRMatchingDashboard = () => {
  const { driveId } = useParams();
  const [rankings, setRankings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [sortAsc, setSortAsc] = useState(false);
  const [selectedCandidate, setSelectedCandidate] = useState(null);

  const fetchRankings = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.get(`/hr/drives/${driveId}/rankings`);
      setRankings(res.data?.candidates || res.data || []);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load rankings');
    } finally {
      setLoading(false);
    }
  }, [driveId]);

  useEffect(() => {
    Promise.resolve().then(() => {
      fetchRankings();
    });
  }, [fetchRankings]);

  const sorted = [...rankings].sort((a, b) =>
    sortAsc ? (a.match_score ?? 0) - (b.match_score ?? 0) : (b.match_score ?? 0) - (a.match_score ?? 0)
  );

  if (loading) {
    return (
      <div className="min-h-screen bg-[#020617] text-white">
        <div className="max-w-5xl mx-auto px-8 py-12 space-y-4">
          <div className="h-8 bg-white/5 rounded w-1/3 animate-pulse" />
          {[...Array(5)].map((_, i) => <SkeletonRow key={i} />)}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-[#020617] text-white flex items-center justify-center">
        <div className="text-center space-y-4">
          <p className="text-red-400 text-lg font-bold">{error}</p>
          <button onClick={fetchRankings}
            className="inline-flex items-center gap-2 bg-purple-600 hover:bg-purple-500 text-white font-bold px-6 py-3 rounded-2xl transition-all"
            aria-label="Retry loading rankings"
          >
            <RefreshCw size={16} /> Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#020617] text-white font-sans">
      <div className="fixed bottom-0 right-[-10%] w-[40%] h-[50%] bg-indigo-900/10 blur-[150px] rounded-full pointer-events-none" />

      <div className="max-w-5xl mx-auto px-8 py-12 space-y-8 relative z-10">
        <motion.div initial="hidden" animate="visible" custom={0} variants={fadeUp}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 bg-gradient-to-tr from-purple-600 to-indigo-400 rounded-2xl flex items-center justify-center shadow-xl shadow-purple-900/30">
                <Trophy size={24} className="text-white" />
              </div>
              <div>
                <h1 className="text-3xl font-black text-white tracking-tight">Candidate Rankings</h1>
                <p className="text-slate-500 text-sm">{sorted.length} candidates ranked by match score</p>
              </div>
            </div>
            <button
              onClick={() => setSortAsc(!sortAsc)}
              className="flex items-center gap-2 bg-white/5 border border-white/10 px-4 py-2.5 rounded-xl text-slate-300 hover:bg-white/10 transition-all text-sm font-bold"
              aria-label={`Sort ${sortAsc ? 'descending' : 'ascending'}`}
            >
              <ArrowUpDown size={14} /> {sortAsc ? 'Low → High' : 'High → Low'}
            </button>
          </div>
        </motion.div>

        {/* Rankings List */}
        <div className="space-y-3">
          {sorted.map((c, idx) => {
            const score = c.match_score ?? 0;
            const isTop = c.is_top_match;
            return (
              <motion.div
                key={c.candidate_id || idx}
                initial="hidden"
                animate="visible"
                custom={idx + 1}
                variants={fadeUp}
                className={`bg-white/[0.03] border rounded-2xl p-5 flex items-center gap-4 hover:bg-white/[0.05] transition-all cursor-pointer ${
                  isTop ? 'border-amber-500/30 shadow-[0_0_20px_rgba(245,158,11,0.1)]' : 'border-white/5'
                }`}
                onClick={() => setSelectedCandidate(c)}
                role="button"
                tabIndex={0}
                aria-label={`View match details for ${c.name || 'candidate'}`}
                onKeyDown={(e) => e.key === 'Enter' && setSelectedCandidate(c)}
              >
                {/* Rank */}
                <div className={`w-10 h-10 rounded-full flex items-center justify-center font-black text-sm ${
                  isTop ? 'bg-amber-500/20 text-amber-400' : 'bg-white/5 text-slate-400'
                }`}>
                  {idx + 1}
                </div>

                {/* Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="text-white font-black truncate">{c.name || `Candidate ${c.candidate_id}`}</p>
                    {isTop && (
                      <span className="px-2 py-0.5 bg-amber-500/10 border border-amber-500/20 rounded-full text-amber-400 text-[9px] font-black uppercase tracking-widest">
                        Top Match
                      </span>
                    )}
                  </div>
                  {/* Score breakdown bar */}
                  <div className="mt-2 space-y-1">
                    {c.score_breakdown && Object.entries(c.score_breakdown).slice(0, 3).map(([key, val]) => (
                      <ScoreBar key={key} label={key} score={val} color="bg-purple-500" />
                    ))}
                  </div>
                </div>

                {/* Score */}
                <div className={`text-2xl font-black ${score >= 80 ? 'text-emerald-400' : score >= 60 ? 'text-purple-400' : 'text-amber-400'}`}>
                  {score}
                </div>
              </motion.div>
            );
          })}
        </div>

        {sorted.length === 0 && (
          <div className="text-center py-16">
            <p className="text-slate-500 text-lg">No candidates ranked yet for this drive.</p>
          </div>
        )}
      </div>

      <AnimatePresence>
        {selectedCandidate && (
          <ExplanationModal candidate={selectedCandidate} onClose={() => setSelectedCandidate(null)} />
        )}
      </AnimatePresence>
    </div>
  );
};

export default HRMatchingDashboard;
