import { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import {
  AreaChart, Area, ResponsiveContainer, Tooltip, XAxis, YAxis
} from 'recharts';
import { AlertTriangle, CheckCircle2, Flag, RefreshCw, Gauge } from 'lucide-react';
import apiClient from '../services/api';

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  visible: (i) => ({ opacity: 1, y: 0, transition: { delay: i * 0.08, duration: 0.5, ease: 'easeOut' } })
};

const GaugeChart = ({ score, label }) => {
  const pct = Math.min(Math.max(score * 100, 0), 100);
  const isLow = score < 0.7;
  const color = isLow ? '#ef4444' : score < 0.85 ? '#f59e0b' : '#10b981';
  const circumference = 2 * Math.PI * 40;
  const dashOffset = circumference - (pct / 100) * circumference * 0.75; // 270 degree arc

  return (
    <div className="flex flex-col items-center">
      <svg width="100" height="80" viewBox="0 0 100 80" role="img" aria-label={`${label} quality score: ${(score * 100).toFixed(0)}%`}>
        <circle cx="50" cy="60" r="40" fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="8"
          strokeDasharray={`${circumference * 0.75} ${circumference * 0.25}`}
          strokeLinecap="round" transform="rotate(-225 50 60)" />
        <circle cx="50" cy="60" r="40" fill="none" stroke={color} strokeWidth="8"
          strokeDasharray={`${circumference * 0.75} ${circumference * 0.25}`}
          strokeDashoffset={dashOffset}
          strokeLinecap="round" transform="rotate(-225 50 60)"
          className="transition-all duration-700" />
        <text x="50" y="55" textAnchor="middle" fill="white" fontSize="16" fontWeight="900">
          {(score * 100).toFixed(0)}%
        </text>
        <text x="50" y="72" textAnchor="middle" fill="#64748b" fontSize="8" fontWeight="700">
          {label}
        </text>
      </svg>
    </div>
  );
};

const QAQualityWidget = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.get('/admin/qa-monitor');
      setData(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load QA data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  if (loading) {
    return (
      <div className="min-h-screen bg-[#020617] text-white">
        <div className="max-w-6xl mx-auto px-8 py-12 space-y-6">
          <div className="h-8 bg-white/5 rounded w-1/3 animate-pulse" />
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="bg-white/[0.03] border border-white/5 rounded-3xl p-6 h-40 animate-pulse" />
            ))}
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
          <button onClick={fetchData}
            className="inline-flex items-center gap-2 bg-purple-600 hover:bg-purple-500 text-white font-bold px-6 py-3 rounded-2xl transition-all"
            aria-label="Retry loading QA data"
          >
            <RefreshCw size={16} /> Retry
          </button>
        </div>
      </div>
    );
  }

  const sessions = data?.sessions || [];
  const flags = data?.flags || [];
  const trendData = data?.quality_trend || [];
  const hasLowScore = sessions.some(s => (s.quality_score ?? 1) < 0.7);

  return (
    <div className="min-h-screen bg-[#020617] text-white font-sans">
      <div className="fixed top-0 right-[-5%] w-[30%] h-[40%] bg-purple-900/10 blur-[150px] rounded-full pointer-events-none" />

      <div className="max-w-6xl mx-auto px-8 py-12 space-y-8 relative z-10">
        {/* Header */}
        <motion.div initial="hidden" animate="visible" custom={0} variants={fadeUp}>
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 bg-gradient-to-tr from-purple-600 to-indigo-400 rounded-2xl flex items-center justify-center shadow-xl shadow-purple-900/30">
              <Gauge size={24} className="text-white" />
            </div>
            <div>
              <h1 className="text-3xl font-black text-white tracking-tight">QA Monitor</h1>
              <p className="text-slate-500 text-sm">Interview quality assurance metrics</p>
            </div>
          </div>
        </motion.div>

        {/* Low Quality Alert */}
        {hasLowScore && (
          <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
            className="bg-red-500/10 border border-red-500/30 rounded-2xl p-4 flex items-center gap-3"
            role="alert"
          >
            <AlertTriangle size={20} className="text-red-400 shrink-0" />
            <div>
              <p className="text-red-400 font-black text-sm">Quality Below Threshold</p>
              <p className="text-red-300/70 text-xs">One or more sessions have quality scores below 0.7</p>
            </div>
          </motion.div>
        )}

        {/* Session Gauges */}
        <motion.div initial="hidden" animate="visible" custom={1} variants={fadeUp}
          className="bg-white/[0.03] border border-white/5 rounded-3xl p-8"
        >
          <h2 className="text-xs font-black uppercase text-purple-400 tracking-widest mb-6">Per-Session Quality</h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-6">
            {sessions.map((s, i) => (
              <GaugeChart key={i} score={s.quality_score ?? 0} label={s.session_label || `S${i + 1}`} />
            ))}
          </div>
          {sessions.length === 0 && (
            <p className="text-slate-500 text-center py-4">No session data available</p>
          )}
        </motion.div>

        {/* Quality Trend */}
        {trendData.length > 0 && (
          <motion.div initial="hidden" animate="visible" custom={2} variants={fadeUp}
            className="bg-white/[0.03] border border-white/5 rounded-3xl p-8"
          >
            <h2 className="text-xs font-black uppercase text-purple-400 tracking-widest mb-6">Quality Trend</h2>
            <div className="h-[200px]" role="img" aria-label="Quality trend area chart">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={trendData}>
                  <defs>
                    <linearGradient id="qualityGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#7C3AED" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#7C3AED" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 10 }} axisLine={false} tickLine={false} />
                  <YAxis domain={[0, 1]} tick={{ fill: '#64748b', fontSize: 10 }} axisLine={false} tickLine={false} width={30} />
                  <Tooltip
                    contentStyle={{ background: '#0f172a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px', color: '#fff' }}
                    labelStyle={{ color: '#a78bfa', fontWeight: 700 }}
                    formatter={(val) => [(val * 100).toFixed(1) + '%', 'Quality']}
                  />
                  <Area type="monotone" dataKey="score" stroke="#7C3AED" strokeWidth={2} fill="url(#qualityGradient)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </motion.div>
        )}

        {/* Flag History */}
        <motion.div initial="hidden" animate="visible" custom={3} variants={fadeUp}
          className="bg-white/[0.03] border border-white/5 rounded-3xl p-8"
        >
          <h2 className="text-xs font-black uppercase text-slate-400 tracking-widest mb-4">Flag History</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-left" role="table">
              <thead>
                <tr className="border-b border-white/5">
                  <th className="px-4 py-3 text-[10px] font-black text-slate-500 uppercase tracking-widest">Type</th>
                  <th className="px-4 py-3 text-[10px] font-black text-slate-500 uppercase tracking-widest">Session</th>
                  <th className="px-4 py-3 text-[10px] font-black text-slate-500 uppercase tracking-widest">Details</th>
                  <th className="px-4 py-3 text-[10px] font-black text-slate-500 uppercase tracking-widest">Timestamp</th>
                </tr>
              </thead>
              <tbody>
                {flags.map((f, i) => (
                  <tr key={i} className="border-b border-white/5 hover:bg-white/[0.02] transition-colors">
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-black uppercase tracking-widest ${
                        f.flag_type === 'bias' ? 'bg-red-500/10 border border-red-500/20 text-red-400' : 'bg-amber-500/10 border border-amber-500/20 text-amber-400'
                      }`}>
                        <Flag size={10} /> {f.flag_type}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-400 text-xs font-mono">{f.session_id?.slice(0, 8) || '—'}</td>
                    <td className="px-4 py-3 text-white text-sm">{f.details || '—'}</td>
                    <td className="px-4 py-3 text-slate-500 text-xs">{f.timestamp ? new Date(f.timestamp).toLocaleString() : '—'}</td>
                  </tr>
                ))}
                {flags.length === 0 && (
                  <tr>
                    <td colSpan={4} className="px-4 py-8 text-center text-slate-500">
                      <CheckCircle2 size={20} className="inline mr-2 text-emerald-400" />
                      No flags raised — all sessions passed QA checks
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </motion.div>
      </div>
    </div>
  );
};

export default QAQualityWidget;
