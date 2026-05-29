import { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import {
  LineChart, Line, RadarChart, Radar, PolarGrid, PolarAngleAxis,
  PolarRadiusAxis, ResponsiveContainer, Tooltip, XAxis, YAxis
} from 'recharts';
import { TrendingUp, TrendingDown, Minus, User, RefreshCw } from 'lucide-react';
import apiClient from '../services/api';
import useAuthStore from '../store/useAuthStore';

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  visible: (i) => ({ opacity: 1, y: 0, transition: { delay: i * 0.08, duration: 0.5, ease: 'easeOut' } })
};

const TrendBadge = ({ direction }) => {
  if (direction === 'improving') return (
    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-[10px] font-black uppercase tracking-widest">
      <TrendingUp size={12} /> Improving
    </span>
  );
  if (direction === 'declining') return (
    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-red-500/10 border border-red-500/20 text-red-400 text-[10px] font-black uppercase tracking-widest">
      <TrendingDown size={12} /> Declining
    </span>
  );
  return (
    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-[10px] font-black uppercase tracking-widest">
      <Minus size={12} /> Stable
    </span>
  );
};

const SkeletonCard = () => (
  <div className="bg-white/[0.03] border border-white/5 rounded-3xl p-6 animate-pulse">
    <div className="h-4 bg-white/5 rounded w-1/3 mb-4" />
    <div className="h-32 bg-white/5 rounded-2xl" />
  </div>
);

const CandidateProfilePage = () => {
  const { user } = useAuthStore();
  const candidateId = user?.id;
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchProfile = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.get(`/memory/profiles/${candidateId}`);
      setProfile(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load profile data');
    } finally {
      setLoading(false);
    }
  }, [candidateId]);

  useEffect(() => {
    if (candidateId) {
      Promise.resolve().then(() => {
        fetchProfile();
      });
    }
  }, [candidateId, fetchProfile]);

  const computeTrend = (history) => {
    if (!history || history.length < 2) return 'stable';
    const recent = history.slice(-3);
    const first = recent[0]?.score ?? 0;
    const last = recent[recent.length - 1]?.score ?? 0;
    const diff = last - first;
    if (diff > 0.5) return 'improving';
    if (diff < -0.5) return 'declining';
    return 'stable';
  };

  const skills = profile?.skills || [];
  const radarData = skills.map(s => ({
    skill: s.name,
    score: s.average_score ?? 0,
    fullMark: 10
  }));

  if (loading) {
    return (
      <div className="min-h-screen bg-[#020617] text-white">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12 space-y-6">
          <div className="h-8 bg-white/5 rounded w-1/4 animate-pulse" />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {[...Array(4)].map((_, i) => <SkeletonCard key={i} />)}
          </div>
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
            onClick={fetchProfile}
            className="inline-flex items-center gap-2 bg-purple-600 hover:bg-purple-500 text-white font-bold px-6 py-3 rounded-2xl transition-all"
            aria-label="Retry loading profile"
          >
            <RefreshCw size={16} /> Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#020617] text-white font-sans">
      <div className="fixed top-0 right-0 w-[40%] h-[40%] bg-purple-600/5 blur-[150px] rounded-full pointer-events-none" />

      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12 space-y-8 sm:space-y-10 relative z-10">
        {/* Header */}
        <motion.div initial="hidden" animate="visible" custom={0} variants={fadeUp}>
          <div className="flex items-center gap-4 mb-2">
            <div className="w-14 h-14 bg-gradient-to-tr from-purple-600 to-indigo-400 rounded-2xl flex items-center justify-center shadow-xl shadow-purple-900/30">
              <User size={24} className="text-white" />
            </div>
            <div>
              <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight">Skill Profile</h1>
              <p className="text-slate-500 text-sm">Track your skill progression over time</p>
            </div>
          </div>
        </motion.div>

        {/* Radar Chart */}
        {radarData.length > 0 && (
          <motion.div initial="hidden" animate="visible" custom={1} variants={fadeUp}
            className="bg-white/[0.03] border border-white/5 rounded-3xl p-5 sm:p-8"
          >
            <h2 className="text-xs font-black uppercase text-purple-400 tracking-widest mb-6">Skill Overview</h2>
            <div className="h-[300px]" role="img" aria-label="Radar chart showing skill averages">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={radarData}>
                  <PolarGrid stroke="rgba(255,255,255,0.05)" />
                  <PolarAngleAxis dataKey="skill" tick={{ fill: '#94a3b8', fontSize: 11, fontWeight: 700 }} />
                  <PolarRadiusAxis angle={30} domain={[0, 10]} tick={{ fill: '#64748b', fontSize: 10 }} />
                  <Radar name="Score" dataKey="score" stroke="#7C3AED" fill="#7C3AED" fillOpacity={0.2} strokeWidth={2} />
                  <Tooltip
                    contentStyle={{ background: '#0f172a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px', color: '#fff' }}
                    labelStyle={{ color: '#a78bfa', fontWeight: 700 }}
                  />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </motion.div>
        )}

        {/* Per-Skill Trend Charts */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {skills.map((skill, idx) => {
            const trend = computeTrend(skill.history);
            return (
              <motion.div
                key={skill.name}
                initial="hidden"
                animate="visible"
                custom={idx + 2}
                variants={fadeUp}
                className="bg-white/[0.03] border border-white/5 rounded-3xl p-6"
              >
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h3 className="text-white font-black text-lg">{skill.name}</h3>
                    <p className="text-slate-500 text-xs">Avg: <span className="text-purple-400 font-bold">{(skill.average_score ?? 0).toFixed(1)}/10</span></p>
                  </div>
                  <TrendBadge direction={trend} />
                </div>
                <div className="h-[120px]" role="img" aria-label={`Line chart showing ${skill.name} score history`}>
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={skill.history || []}>
                      <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 10 }} axisLine={false} tickLine={false} />
                      <YAxis domain={[0, 10]} tick={{ fill: '#64748b', fontSize: 10 }} axisLine={false} tickLine={false} width={25} />
                      <Tooltip
                        contentStyle={{ background: '#0f172a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px', color: '#fff' }}
                        labelStyle={{ color: '#a78bfa', fontWeight: 700 }}
                      />
                      <Line type="monotone" dataKey="score" stroke="#7C3AED" strokeWidth={2} dot={{ fill: '#7C3AED', r: 3 }} activeDot={{ r: 5, fill: '#a78bfa' }} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </motion.div>
            );
          })}
        </div>

        {skills.length === 0 && (
          <div className="text-center py-16">
            <p className="text-slate-500 text-lg">No skill data available yet. Complete interviews to build your profile.</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default CandidateProfilePage;
