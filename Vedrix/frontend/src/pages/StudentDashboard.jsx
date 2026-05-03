import React, { useState, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import {
  Play, Upload, FileText, BarChart3, Clock, CheckCircle2,
  TrendingUp, Award, ChevronRight, Loader2, User, LogOut
} from 'lucide-react';
import apiClient from '../services/api';
import useAuthStore from '../store/useAuthStore';

const StudentDashboard = ({ onStartInterview, onViewReport }) => {
  const { user, logout } = useAuthStore();
  const [stats, setStats] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [resumeName, setResumeName] = useState(null);
  const fileRef = useRef();

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statsRes, sessionsRes] = await Promise.all([
          apiClient.get('/student/stats'),
          apiClient.get('/student/interviews'),
        ]);
        setStats(statsRes.data);
        setSessions(sessionsRes.data);
      } catch (err) {
        console.error('Dashboard fetch error:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const handleResumeUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.name.endsWith('.pdf')) return alert('Only PDF files are accepted.');
    setUploading(true);
    try {
      const form = new FormData();
      form.append('file', file);
      await apiClient.post('/profiles/student/resume', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setResumeName(file.name);
    } catch {
      alert('Resume upload failed. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  const scoreColor = (s) =>
    s >= 8 ? 'text-emerald-400' : s >= 5 ? 'text-purple-400' : 'text-amber-400';

  return (
    <div className="min-h-screen bg-[#020617] text-white font-sans">
      {/* Ambient */}
      <div className="fixed top-0 right-0 w-[40%] h-[40%] bg-purple-600/5 blur-[150px] rounded-full pointer-events-none" />

      {/* Top bar */}
      <div className="border-b border-white/5 bg-[#0a0f1e]/80 backdrop-blur-xl px-8 h-20 flex items-center justify-between sticky top-0 z-40">
        <div className="flex items-center space-x-3">
          <div className="w-9 h-9 bg-gradient-to-tr from-purple-600 to-indigo-400 rounded-xl flex items-center justify-center text-white font-black text-sm">
            {user?.first_name?.[0] || 'V'}
          </div>
          <div>
            <p className="text-white font-bold text-sm">{user?.first_name} {user?.last_name}</p>
            <p className="text-slate-500 text-[10px] font-black uppercase tracking-widest">Candidate</p>
          </div>
        </div>
        <button onClick={logout} className="text-slate-500 hover:text-red-400 transition-colors">
          <LogOut size={18} />
        </button>
      </div>

      <div className="max-w-6xl mx-auto px-8 py-12 space-y-10 relative z-10">

        {/* Welcome */}
        <div>
          <h1 className="text-4xl font-black text-white tracking-tight">
            Welcome back, <span className="text-purple-400">{user?.first_name}</span> 👋
          </h1>
          <p className="text-slate-500 mt-2">Ready for your next assessment?</p>
        </div>

        {/* Stats row */}
        {!loading && stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: 'Total Sessions', val: stats.total_interviews ?? 0, icon: BarChart3, color: 'text-purple-400' },
              { label: 'Completed', val: stats.completed_interviews ?? 0, icon: CheckCircle2, color: 'text-emerald-400' },
              { label: 'Avg Score', val: stats.avg_score ? `${stats.avg_score}/10` : '—', icon: TrendingUp, color: 'text-blue-400' },
              { label: 'Best Score', val: stats.best_score ? `${stats.best_score}/10` : '—', icon: Award, color: 'text-amber-400' },
            ].map(s => (
              <div key={s.label} className="bg-white/2 border border-white/5 rounded-3xl p-6 flex items-center space-x-4">
                <div className="w-10 h-10 bg-white/5 rounded-2xl flex items-center justify-center">
                  <s.icon size={20} className={s.color} />
                </div>
                <div>
                  <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest">{s.label}</p>
                  <p className={`text-xl font-black ${s.color}`}>{s.val}</p>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Action cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

          {/* Start Interview */}
          <motion.div
            whileHover={{ scale: 1.01 }}
            className="bg-gradient-to-br from-purple-600/20 to-indigo-600/10 border border-purple-500/20 rounded-[2rem] p-8 flex flex-col justify-between min-h-[200px] relative overflow-hidden cursor-pointer group"
            onClick={onStartInterview}
          >
            <div className="absolute top-0 right-0 w-32 h-32 bg-purple-600/10 blur-[60px] rounded-full group-hover:bg-purple-600/20 transition-all" />
            <div>
              <div className="w-12 h-12 bg-purple-600 rounded-2xl flex items-center justify-center mb-4 shadow-xl shadow-purple-900/40">
                <Play size={22} className="text-white" fill="white" />
              </div>
              <h2 className="text-2xl font-black text-white mb-1">Start AI Interview</h2>
              <p className="text-slate-400 text-sm">Adaptive, voice-based assessment powered by Vedrix AI</p>
            </div>
            <div className="flex items-center text-purple-400 font-black text-xs uppercase tracking-widest mt-6">
              <span>Join Room</span>
              <ChevronRight size={16} className="ml-1" />
            </div>
          </motion.div>

          {/* Resume Upload */}
          <div className="bg-white/2 border border-white/5 rounded-[2rem] p-8 flex flex-col justify-between min-h-[200px]">
            <div>
              <div className="w-12 h-12 bg-white/5 border border-white/10 rounded-2xl flex items-center justify-center mb-4">
                <FileText size={22} className="text-slate-400" />
              </div>
              <h2 className="text-2xl font-black text-white mb-1">Resume</h2>
              <p className="text-slate-400 text-sm">
                {resumeName
                  ? `Uploaded: ${resumeName}`
                  : 'Upload your resume so the AI can tailor questions to your experience.'}
              </p>
            </div>
            <button
              onClick={() => fileRef.current?.click()}
              disabled={uploading}
              className="mt-6 flex items-center space-x-2 bg-white/5 border border-white/10 hover:bg-white/10 text-white px-6 py-3 rounded-2xl font-bold text-sm transition-all disabled:opacity-50 active:scale-95"
            >
              {uploading ? <Loader2 size={16} className="animate-spin" /> : <Upload size={16} />}
              <span>{uploading ? 'Uploading...' : resumeName ? 'Replace Resume' : 'Upload PDF'}</span>
            </button>
            <input ref={fileRef} type="file" accept=".pdf" className="hidden" onChange={handleResumeUpload} />
          </div>
        </div>

        {/* Past Sessions */}
        <div>
          <h2 className="text-xl font-black text-white mb-4 uppercase tracking-widest text-sm">Past Sessions</h2>
          {loading ? (
            <div className="flex justify-center py-12">
              <Loader2 className="animate-spin text-purple-500" size={36} />
            </div>
          ) : sessions.length === 0 ? (
            <div className="bg-white/2 border-2 border-dashed border-white/10 rounded-[2rem] p-16 text-center">
              <Clock size={36} className="text-slate-600 mx-auto mb-4" />
              <p className="text-slate-500 font-medium">No sessions yet. Start your first interview above.</p>
            </div>
          ) : (
            <div className="bg-white/2 border border-white/5 rounded-[2rem] overflow-hidden">
              <div className="px-8 py-4 border-b border-white/5 grid grid-cols-12 gap-4 text-[10px] font-black uppercase tracking-[0.2em] text-slate-500">
                <div className="col-span-3">Type</div>
                <div className="col-span-3">Status</div>
                <div className="col-span-2 text-center">Score</div>
                <div className="col-span-3">Date</div>
                <div className="col-span-1" />
              </div>
              <div className="divide-y divide-white/5">
                {sessions.map(s => (
                  <div key={s.id} className="px-8 py-5 grid grid-cols-12 gap-4 items-center hover:bg-white/2 transition-all group">
                    <div className="col-span-3">
                      <span className={`text-[10px] font-black uppercase tracking-widest px-3 py-1 rounded-full border ${
                        s.session_type === 'actual'
                          ? 'bg-purple-500/10 text-purple-400 border-purple-500/20'
                          : 'bg-white/5 text-slate-400 border-white/10'
                      }`}>
                        {s.session_type}
                      </span>
                    </div>
                    <div className="col-span-3">
                      <span className={`text-[10px] font-black uppercase tracking-widest ${
                        s.status === 'completed' ? 'text-emerald-400' : 'text-amber-400'
                      }`}>
                        {s.status}
                      </span>
                    </div>
                    <div className="col-span-2 text-center">
                      <span className={`text-lg font-black ${s.overall_score ? scoreColor(s.overall_score) : 'text-slate-600'}`}>
                        {s.overall_score ? s.overall_score.toFixed(1) : '—'}
                      </span>
                    </div>
                    <div className="col-span-3 text-slate-500 text-xs font-bold">
                      {new Date(s.created_at).toLocaleDateString()}
                    </div>
                    <div className="col-span-1 text-right">
                      {s.status === 'completed' && (
                        <button
                          onClick={() => onViewReport(s.id)}
                          className="p-2 bg-white/5 border border-white/10 rounded-xl text-slate-400 hover:text-white hover:bg-purple-600 transition-all"
                        >
                          <ChevronRight size={16} />
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default StudentDashboard;
