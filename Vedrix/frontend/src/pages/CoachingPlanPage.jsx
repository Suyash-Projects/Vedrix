import { useState, useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { BookOpen, Video, GraduationCap, FileText, ExternalLink, RefreshCw, Target, TrendingUp } from 'lucide-react';
import apiClient from '../services/api';

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  visible: (i) => ({ opacity: 1, y: 0, transition: { delay: i * 0.08, duration: 0.5, ease: 'easeOut' } })
};

const resourceIcons = {
  book: BookOpen,
  course: GraduationCap,
  video: Video,
  documentation: FileText,
};

const resourceColors = {
  book: 'bg-amber-500/10 border-amber-500/20 text-amber-400',
  course: 'bg-purple-500/10 border-purple-500/20 text-purple-400',
  video: 'bg-red-500/10 border-red-500/20 text-red-400',
  documentation: 'bg-blue-500/10 border-blue-500/20 text-blue-400',
};

const SkeletonCard = () => (
  <div className="bg-white/[0.03] border border-white/5 rounded-3xl p-6 animate-pulse">
    <div className="h-4 bg-white/5 rounded w-1/3 mb-4" />
    <div className="h-3 bg-white/5 rounded w-full mb-2" />
    <div className="h-3 bg-white/5 rounded w-2/3" />
  </div>
);

const CoachingPlanPage = () => {
  const { planId } = useParams();
  const [plan, setPlan] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchPlan = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.get(`/student/coaching-plans/${planId}`);
      setPlan(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load coaching plan');
    } finally {
      setLoading(false);
    }
  }, [planId]);

  useEffect(() => {
    Promise.resolve().then(() => {
      fetchPlan();
    });
  }, [fetchPlan]);

  if (loading) {
    return (
      <div className="min-h-screen bg-[#020617] text-white">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12 space-y-6">
          <div className="h-8 bg-white/5 rounded w-1/3 animate-pulse" />
          {[...Array(3)].map((_, i) => <SkeletonCard key={i} />)}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-[#020617] text-white flex items-center justify-center">
        <div className="text-center space-y-4">
          <p className="text-red-400 text-lg font-bold">{error}</p>
          <button
            onClick={fetchPlan}
            className="inline-flex items-center gap-2 bg-purple-600 hover:bg-purple-500 text-white font-bold px-6 py-3 rounded-2xl transition-all"
            aria-label="Retry loading coaching plan"
          >
            <RefreshCw size={16} /> Retry
          </button>
        </div>
      </div>
    );
  }

  const gaps = (plan?.skill_gaps || []).sort((a, b) => (b.gap_magnitude ?? 0) - (a.gap_magnitude ?? 0));
  const effectiveness = plan?.effectiveness_metrics || [];

  return (
    <div className="min-h-screen bg-[#020617] text-white font-sans">
      <div className="fixed top-0 left-[-10%] w-[40%] h-[50%] bg-purple-900/10 blur-[150px] rounded-full pointer-events-none" />

      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12 space-y-8 sm:space-y-10 relative z-10">
        {/* Header */}
        <motion.div initial="hidden" animate="visible" custom={0} variants={fadeUp}>
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 bg-gradient-to-tr from-purple-600 to-indigo-400 rounded-2xl flex items-center justify-center shadow-xl shadow-purple-900/30">
              <Target size={24} className="text-white" />
            </div>
            <div>
              <h1 className="text-3xl font-black text-white tracking-tight">{plan?.title || 'Coaching Plan'}</h1>
              <p className="text-slate-500 text-sm">{plan?.description || 'Personalized learning path based on your skill gaps'}</p>
            </div>
          </div>
        </motion.div>

        {/* Effectiveness Metrics */}
        {effectiveness.length > 0 && (
          <motion.div initial="hidden" animate="visible" custom={1} variants={fadeUp}
            className="bg-white/[0.03] border border-white/5 rounded-3xl p-6"
          >
            <h2 className="text-xs font-black uppercase text-purple-400 tracking-widest mb-4">Coaching Effectiveness</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {effectiveness.map((m, i) => (
                <div key={i} className="bg-white/[0.03] border border-white/5 rounded-2xl p-4 text-center">
                  <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-1">{m.session_label || `Session ${i + 1}`}</p>
                  <p className={`text-2xl font-black ${m.delta_score > 0 ? 'text-emerald-400' : m.delta_score < 0 ? 'text-red-400' : 'text-slate-300'}`}>
                    {m.delta_score > 0 ? '+' : ''}{(m.delta_score ?? 0).toFixed(1)}
                  </p>
                  <p className="text-slate-500 text-[10px] mt-1">Score Delta</p>
                </div>
              ))}
            </div>
          </motion.div>
        )}

        {/* Skill Gaps */}
        <div className="space-y-6">
          <h2 className="text-xs font-black uppercase text-slate-400 tracking-widest">Prioritized Skill Gaps</h2>
          {gaps.map((gap, idx) => {
            const magnitude = gap.gap_magnitude ?? 0;
            const pct = Math.min(magnitude * 10, 100);
            return (
              <motion.div
                key={gap.skill_name || idx}
                initial="hidden"
                animate="visible"
                custom={idx + 2}
                variants={fadeUp}
                className="bg-white/[0.03] border border-white/5 rounded-3xl p-6"
              >
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-white font-black text-lg">{gap.skill_name}</h3>
                  <span className="text-purple-400 font-black text-sm">Gap: {magnitude.toFixed(1)}</span>
                </div>

                {/* Gap Progress Bar */}
                <div className="mb-4">
                  <div className="h-2 bg-white/5 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-purple-600 to-indigo-400 rounded-full transition-all duration-700"
                      style={{ width: `${pct}%` }}
                      role="progressbar"
                      aria-valuenow={pct}
                      aria-valuemin={0}
                      aria-valuemax={100}
                      aria-label={`${gap.skill_name} gap magnitude ${magnitude.toFixed(1)}`}
                    />
                  </div>
                  <div className="flex justify-between mt-1">
                    <span className="text-[10px] text-slate-500">Current: {(gap.current_score ?? 0).toFixed(1)}</span>
                    <span className="text-[10px] text-slate-500">Target: {(gap.target_score ?? 10).toFixed(1)}</span>
                  </div>
                </div>

                {/* Resources */}
                {gap.resources && gap.resources.length > 0 && (
                  <div className="space-y-2">
                    <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Learning Resources</p>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {gap.resources.map((r, ri) => {
                        const Icon = resourceIcons[r.type] || FileText;
                        const colorClass = resourceColors[r.type] || resourceColors.documentation;
                        return (
                          <a
                            key={ri}
                            href={r.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center gap-3 bg-white/[0.02] border border-white/5 rounded-xl p-3 hover:bg-white/[0.05] hover:border-white/10 transition-all group"
                            aria-label={`${r.title} - ${r.type}`}
                          >
                            <div className={`w-8 h-8 ${colorClass} border rounded-lg flex items-center justify-center shrink-0`}>
                              <Icon size={14} />
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="text-white text-sm font-bold truncate">{r.title}</p>
                              <span className={`text-[10px] font-black uppercase tracking-widest ${colorClass.split(' ').pop()}`}>{r.type}</span>
                            </div>
                            <ExternalLink size={14} className="text-slate-500 group-hover:text-purple-400 transition-colors shrink-0" />
                          </a>
                        );
                      })}
                    </div>
                  </div>
                )}
              </motion.div>
            );
          })}
        </div>

        {gaps.length === 0 && (
          <div className="text-center py-16">
            <TrendingUp size={48} className="text-emerald-400 mx-auto mb-4" />
            <p className="text-slate-400 text-lg font-bold">No skill gaps identified</p>
            <p className="text-slate-500 text-sm">Great job! Your skills are well-aligned with the target.</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default CoachingPlanPage;
