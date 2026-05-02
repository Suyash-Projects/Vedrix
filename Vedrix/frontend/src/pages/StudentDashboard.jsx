import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  LayoutDashboard, Activity, BookOpen, Settings, LogOut,
  ChevronRight, Play, Star, Clock, Trophy, Target,
  TrendingUp, Calendar, Loader2, Award, Zap
} from 'lucide-react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, AreaChart, Area
} from 'recharts';
import apiClient from '../services/api';
import useAuthStore from '../store/useAuthStore';

const StudentDashboard = ({ onStartInterview, onViewReport }) => {
  const { user, logout } = useAuthStore();
  const [stats, setStats] = useState(null);
  const [interviews, setInterviews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('Overview');

  const fetchData = async () => {
    setLoading(true);
    try {
      const [statsRes, interviewsRes] = await Promise.all([
        apiClient.get('/student/stats'),
        apiClient.get('/student/interviews')
      ]);
      setStats(statsRes.data);
      setInterviews(interviewsRes.data);
    } catch (err) {
      console.error("Failed to fetch student data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-[#020617] flex items-center justify-center">
        <Loader2 className="animate-spin text-purple-500" size={48} />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#020617] flex font-sans text-white">
      {/* Sidebar */}
      <div className="w-72 bg-[#0a0f1e] border-r border-white/5 p-8 flex flex-col space-y-10 hidden lg:flex">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-gradient-to-tr from-purple-600 to-indigo-400 rounded-xl flex items-center justify-center text-white shadow-lg shadow-purple-900/30">
            <Zap size={20} />
          </div>
          <span className="text-xl font-bold tracking-tight text-white">Vedrix <span className="text-purple-400">AI</span></span>
        </div>

        <nav className="flex-1 space-y-2">
          {[
            { label: 'Overview', icon: LayoutDashboard },
            { label: 'Interview History', icon: Clock },
            { label: 'Skill Analysis', icon: Activity },
            { label: 'Settings', icon: Settings },
          ].map(item => (
            <button key={item.label}
              onClick={() => setActiveTab(item.label)}
              className={`w-full flex items-center space-x-3 px-5 py-4 rounded-2xl transition-all text-sm font-bold ${
                activeTab === item.label ? 'bg-purple-600/10 text-purple-400 border border-purple-500/20' : 'text-slate-500 hover:text-white hover:bg-white/5'
              }`}>
              <item.icon size={18} />
              <span>{item.label}</span>
            </button>
          ))}
        </nav>

        <button onClick={logout}
          className="flex items-center space-x-3 px-5 py-4 rounded-2xl text-slate-500 hover:text-red-400 hover:bg-red-500/5 transition-all border border-transparent hover:border-red-500/10">
          <LogOut size={18} />
          <span className="text-sm font-bold uppercase tracking-wider">Logout</span>
        </button>
      </div>

      {/* Main Content */}
      <div className="flex-1 p-6 md:p-12 overflow-y-auto relative">
        {/* Ambient glow */}
        <div className="fixed top-0 right-0 w-[40%] h-[40%] bg-purple-600/5 blur-[150px] rounded-full pointer-events-none" />

        <header className="flex flex-col md:flex-row justify-between items-start md:items-center mb-12 gap-6 relative">
          <div>
            <h1 className="text-4xl font-extrabold text-white tracking-tight">Performance Command Center</h1>
            <p className="text-slate-500 text-lg mt-1 font-medium italic">Welcome back, {user?.first_name} 👋</p>
          </div>
          <button onClick={onStartInterview}
            className="bg-purple-600 text-white px-8 py-4 rounded-2xl font-bold hover:bg-purple-500 transition-all shadow-xl shadow-purple-900/30 flex items-center space-x-2 active:scale-95">
            <Play size={20} fill="currentColor" />
            <span>Start Practice Round</span>
          </button>
        </header>

        {activeTab === 'Overview' ? (
          <div className="space-y-10">
            {/* Quick Stats */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {[
                { label: 'Total Sessions', value: stats?.total_sessions || 0, icon: BookOpen, color: 'text-blue-400', bg: 'bg-blue-400/10' },
                { label: 'Average Score', value: stats?.avg_score || '0.0', icon: Target, color: 'text-purple-400', bg: 'bg-purple-400/10' },
                { label: 'Best Performance', value: stats?.best_score || '0.0', icon: Trophy, color: 'text-emerald-400', bg: 'bg-emerald-400/10' },
                { label: 'Global Rank', value: 'Top 12%', icon: Award, color: 'text-amber-400', bg: 'bg-amber-400/10' },
              ].map((stat, i) => (
                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.1 }}
                  key={i} className="bg-white/2 border border-white/5 p-6 rounded-3xl flex items-center space-x-4">
                  <div className={`w-12 h-12 ${stat.bg} ${stat.color} rounded-2xl flex items-center justify-center`}>
                    <stat.icon size={24} />
                  </div>
                  <div>
                    <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest">{stat.label}</p>
                    <p className="text-2xl font-black text-white">{stat.value}</p>
                  </div>
                </motion.div>
              ))}
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
              {/* Score Trend Chart */}
              <div className="lg:col-span-8 bg-white/2 border border-white/5 p-8 rounded-[2.5rem] relative overflow-hidden">
                <div className="flex justify-between items-center mb-8">
                  <h3 className="font-bold text-xl flex items-center">
                    <TrendingUp size={20} className="mr-3 text-purple-400" /> Improvement Curve
                  </h3>
                  <div className="flex space-x-2">
                    {['7D', '30D', 'ALL'].map(p => (
                      <button key={p} className="text-[10px] font-black px-3 py-1 rounded-full bg-white/5 border border-white/5 text-slate-500 hover:text-white transition-all">
                        {p}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="h-72 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={stats?.chart_data || []}>
                      <defs>
                        <linearGradient id="colorScore" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#8B5CF6" stopOpacity={0.3}/>
                          <stop offset="95%" stopColor="#8B5CF6" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                      <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{fill: '#64748B', fontSize: 10}} dy={10} />
                      <YAxis domain={[0, 10]} axisLine={false} tickLine={false} tick={{fill: '#64748B', fontSize: 10}} dx={-10} />
                      <Tooltip 
                        contentStyle={{backgroundColor: '#0f172a', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px'}}
                        itemStyle={{color: '#8B5CF6', fontWeight: 'bold'}}
                      />
                      <Area type="monotone" dataKey="score" stroke="#8B5CF6" strokeWidth={3} fillOpacity={1} fill="url(#colorScore)" />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Recent Activity */}
              <div className="lg:col-span-4 bg-white/2 border border-white/5 p-8 rounded-[2.5rem]">
                <h3 className="font-bold text-xl mb-6 flex items-center">
                  <Clock size={20} className="mr-3 text-purple-400" /> Recent Rounds
                </h3>
                <div className="space-y-4">
                  {interviews.slice(0, 5).map((interview, i) => (
                    <div key={i} className="bg-white/5 p-4 rounded-2xl border border-white/5 flex items-center justify-between group hover:border-purple-500/20 transition-all cursor-pointer"
                      onClick={() => interview.status === 'completed' && onViewReport(interview.id)}>
                      <div className="flex items-center space-x-3">
                        <div className={`w-10 h-10 ${interview.status === 'completed' ? 'bg-emerald-400/10 text-emerald-400' : 'bg-amber-400/10 text-amber-400'} rounded-xl flex items-center justify-center`}>
                          {interview.status === 'completed' ? <Award size={18} /> : <Activity size={18} />}
                        </div>
                        <div>
                          <p className="text-sm font-bold text-white capitalize">{interview.session_type} Session</p>
                          <p className="text-[10px] text-slate-500 font-bold uppercase tracking-widest">{new Date(interview.created_at).toLocaleDateString()}</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-black text-white">{interview.overall_score ? interview.overall_score.toFixed(1) : '—'}</p>
                        <ChevronRight size={14} className="text-slate-600 group-hover:text-purple-400 ml-auto" />
                      </div>
                    </div>
                  ))}
                  {interviews.length === 0 && (
                    <div className="text-center py-10">
                      <p className="text-slate-500 text-sm font-medium">No sessions found.</p>
                      <button onClick={onStartInterview} className="text-purple-400 text-xs font-bold mt-2 hover:underline">Start your first round</button>
                    </div>
                  )}
                </div>
                {interviews.length > 5 && (
                   <button onClick={() => setActiveTab('Interview History')} className="w-full text-center py-4 text-xs font-black uppercase tracking-widest text-slate-500 hover:text-white transition-all mt-4">
                     View All Rounds
                   </button>
                )}
              </div>
            </div>
          </div>
        ) : activeTab === 'Interview History' ? (
          <div className="bg-white/2 border border-white/5 rounded-[2.5rem] overflow-hidden">
             <div className="px-10 py-6 border-b border-white/5 bg-white/2">
               <div className="grid grid-cols-12 gap-4 text-[10px] font-black uppercase tracking-[0.2em] text-slate-500">
                 <div className="col-span-4">Session Type</div>
                 <div className="col-span-3">Status</div>
                 <div className="col-span-2 text-center">Score</div>
                 <div className="col-span-2 text-center">Date</div>
                 <div className="col-span-1"></div>
               </div>
             </div>
             <div className="divide-y divide-white/5">
                {interviews.map(interview => (
                  <div key={interview.id} className="px-10 py-8 grid grid-cols-12 gap-4 items-center hover:bg-white/5 transition-all group">
                     <div className="col-span-4 flex items-center space-x-4">
                        <div className="w-12 h-12 bg-purple-600/10 border border-purple-500/20 rounded-2xl flex items-center justify-center text-purple-400 font-black">
                           <Zap size={20} />
                        </div>
                        <div>
                           <p className="text-white font-bold capitalize">{interview.session_type} Round</p>
                           <p className="text-xs text-slate-500 font-medium">AI-Guided Assessment</p>
                        </div>
                     </div>
                     <div className="col-span-3">
                        <span className={`px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest border ${
                          interview.status === 'completed' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                        }`}>
                          {interview.status}
                        </span>
                     </div>
                     <div className="col-span-2 text-center">
                        <span className="text-xl font-black text-white">{interview.overall_score?.toFixed(1) || '—'}</span>
                     </div>
                     <div className="col-span-2 text-center text-slate-500 text-xs font-bold uppercase tracking-widest">
                        {new Date(interview.created_at).toLocaleDateString()}
                     </div>
                     <div className="col-span-1 text-right">
                        <button 
                          onClick={() => interview.status === 'completed' && onViewReport(interview.id)}
                          disabled={interview.status !== 'completed'}
                          className="p-3 bg-white/5 border border-white/10 rounded-xl text-slate-400 hover:text-white hover:bg-purple-600 transition-all disabled:opacity-30 disabled:hover:bg-white/5">
                           <ChevronRight size={18} />
                        </button>
                     </div>
                  </div>
                ))}
             </div>
          </div>
        ) : (
          <div className="p-20 text-center bg-white/2 border border-white/5 rounded-[2.5rem]">
             <h2 className="text-2xl font-bold text-white">{activeTab} Section</h2>
             <p className="text-slate-500 mt-2 italic font-medium">This module is currently being optimized for your profile.</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default StudentDashboard;
