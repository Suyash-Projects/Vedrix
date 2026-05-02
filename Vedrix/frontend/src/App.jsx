import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  ShieldCheck, Cpu, UserCheck, Zap, ChevronRight, Menu, X, LogOut,
  LayoutDashboard, BookOpen, Briefcase, Play, Award, Activity
} from 'lucide-react';

import Login from './pages/Login';
import Register from './pages/Register';
import InterviewRoom from './pages/InterviewRoom';
import AdminDashboard from './pages/AdminDashboard';
import HRDashboard from './pages/HRDashboard';
import StudentDashboard from './pages/StudentDashboard';
import InterviewReport from './pages/InterviewReport';
import useAuthStore from './store/useAuthStore';

/* ─────────────────────────────────────────────
   NAVBAR (RE-STYLED FOR DARK THEME)
───────────────────────────────────────────── */
const Navbar = ({ onShowLogin, onShowRegister, onShowDashboard, onShowAdmin, onHome }) => {
  const { isAuthenticated, user, logout } = useAuthStore();
  const [isOpen, setIsOpen] = useState(false);

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-[#020617]/80 backdrop-blur-xl border-b border-white/5">
      <div className="max-w-7xl mx-auto px-8 h-20 flex items-center justify-between">
        <div 
          onClick={onHome}
          className="flex items-center space-x-3 cursor-pointer group"
        >
          <div className="w-10 h-10 bg-gradient-to-tr from-purple-600 to-indigo-400 rounded-xl flex items-center justify-center text-white shadow-lg shadow-purple-900/20 group-hover:scale-110 transition-all">
            <Cpu size={22} />
          </div>
          <span className="text-2xl font-black tracking-tighter text-white">Vedrix <span className="text-purple-400 text-sm align-top ml-1">AI</span></span>
        </div>

        {/* Desktop Nav */}
        <div className="hidden md:flex items-center space-x-10">
          <button onClick={onHome} className="text-slate-400 hover:text-white font-bold text-sm uppercase tracking-widest transition-colors">Home</button>
          {isAuthenticated && (
            <>
              <button onClick={onShowDashboard} className="text-slate-400 hover:text-white font-bold text-sm uppercase tracking-widest transition-colors">Dashboard</button>
              {user?.user_type === 'admin' && (
                <button onClick={onShowAdmin} className="text-amber-400 hover:text-amber-300 font-bold text-sm uppercase tracking-widest transition-colors">Admin</button>
              )}
            </>
          )}
        </div>

        <div className="hidden md:flex items-center space-x-4">
          {!isAuthenticated ? (
            <>
              <button onClick={onShowLogin} className="text-white font-bold px-6 py-2.5 rounded-xl hover:bg-white/5 transition-all">Sign In</button>
              <button onClick={onShowRegister} className="bg-purple-600 text-white font-bold px-8 py-2.5 rounded-xl hover:bg-purple-500 shadow-xl shadow-purple-900/30 transition-all active:scale-95">Register</button>
            </>
          ) : (
            <div className="flex items-center space-x-6">
              <div className="flex flex-col text-right">
                <span className="text-white font-bold text-sm">{user?.first_name}</span>
                <span className="text-slate-500 text-[10px] font-black uppercase tracking-widest">{user?.user_type}</span>
              </div>
              <button 
                onClick={() => { logout(); onHome(); }}
                className="w-10 h-10 bg-white/5 border border-white/10 rounded-xl flex items-center justify-center text-slate-400 hover:text-red-400 hover:bg-red-500/5 transition-all"
              >
                <LogOut size={18} />
              </button>
            </div>
          )}
        </div>

        {/* Mobile toggle */}
        <button className="md:hidden text-white" onClick={() => setIsOpen(!isOpen)}>
          {isOpen ? <X /> : <Menu />}
        </button>
      </div>
    </nav>
  );
};

/* ─────────────────────────────────────────────
   LANDING PAGE (IMPRESSIVE HERO)
───────────────────────────────────────────── */
const LandingPage = ({ onRegister }) => (
  <div className="relative min-h-screen pt-40 pb-20 px-8 overflow-hidden font-sans">
    {/* Ambient Glows */}
    <div className="absolute top-[-20%] left-[-10%] w-[60%] h-[60%] bg-purple-900/20 blur-[150px] rounded-full" />
    <div className="absolute bottom-[-20%] right-[-10%] w-[60%] h-[60%] bg-indigo-900/20 blur-[150px] rounded-full" />

    <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-20 items-center relative z-10">
      <div className="space-y-10">
        <div className="inline-flex items-center space-x-3 bg-white/5 border border-white/10 px-5 py-2 rounded-full">
          <span className="w-2 h-2 bg-purple-500 rounded-full animate-pulse" />
          <span className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-300">Next-Gen Hiring Engine Live</span>
        </div>
        
        <h1 className="text-7xl md:text-8xl font-black text-white leading-[0.9] tracking-tighter">
          Synchronize <br />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-indigo-300 italic">Talent & Scale.</span>
        </h1>
        
        <p className="text-xl text-slate-400 max-w-lg leading-relaxed font-medium">
          Vedrix is the industry's first autonomous interview orchestration platform. Scale your recruitment with agentic intelligence.
        </p>

        <div className="flex flex-col sm:flex-row gap-6">
          <button onClick={onRegister} className="bg-purple-600 text-white px-12 py-5 rounded-2xl font-black uppercase tracking-widest text-sm hover:bg-purple-500 shadow-[0_0_50px_rgba(147,51,234,0.3)] transition-all flex items-center justify-center space-x-3 active:scale-95">
            <span>Start Evaluaton</span>
            <ChevronRight size={20} />
          </button>
          <div className="flex items-center space-x-4 px-6 border-l border-white/10">
            <div className="flex -space-x-3">
              {[1, 2, 3].map(i => (
                <div key={i} className="w-10 h-10 rounded-full border-2 border-[#020617] overflow-hidden">
                  <img src={`https://i.pravatar.cc/100?img=${i+10}`} alt="user" />
                </div>
              ))}
            </div>
            <div className="text-left">
              <p className="text-white font-bold text-sm">Join 2,000+ Teams</p>
              <p className="text-slate-500 text-xs">Scaling with AI evaluation</p>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-8 pt-10 border-t border-white/5">
           {[
             { label: 'Latency', val: '< 200ms', icon: Zap },
             { label: 'Accuracy', val: '99.4%', icon: ShieldCheck },
             { label: 'Autonomy', val: 'Agentic', icon: Cpu },
           ].map(stat => (
             <div key={stat.label} className="space-y-1">
                <p className="text-slate-500 text-[10px] font-black uppercase tracking-widest flex items-center">
                  <stat.icon size={12} className="mr-2 text-purple-500" /> {stat.label}
                </p>
                <p className="text-white font-black text-xl tracking-tight">{stat.val}</p>
             </div>
           ))}
        </div>
      </div>

      <div className="relative group lg:block hidden">
        <div className="absolute inset-0 bg-purple-600/20 blur-[100px] rounded-full group-hover:bg-purple-600/30 transition-all duration-700" />
        <div className="relative bg-white/5 backdrop-blur-2xl border border-white/10 rounded-[3rem] p-10 shadow-2xl overflow-hidden">
          <div className="flex items-center justify-between mb-8">
            <div className="flex space-x-2">
              <div className="w-3 h-3 rounded-full bg-red-500/50" />
              <div className="w-3 h-3 rounded-full bg-amber-500/50" />
              <div className="w-3 h-3 rounded-full bg-emerald-500/50" />
            </div>
            <div className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Assessment Console</div>
          </div>
          <div className="space-y-6">
            <div className="h-4 bg-white/5 rounded-full w-3/4" />
            <div className="h-4 bg-white/5 rounded-full w-1/2" />
            <div className="h-32 bg-purple-500/10 border border-purple-500/20 rounded-3xl flex items-center justify-center">
               <div className="flex flex-col items-center text-center">
                  <div className="w-12 h-12 bg-purple-600 rounded-full flex items-center justify-center text-white mb-3 animate-bounce">
                    <Activity size={24} />
                  </div>
                  <span className="text-[10px] font-black text-purple-400 uppercase tracking-widest">AI Agent Evaluating...</span>
               </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="h-12 bg-white/5 rounded-2xl" />
              <div className="h-12 bg-white/5 rounded-2xl" />
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
);

/* ─────────────────────────────────────────────
   MAIN APP ROUTER
───────────────────────────────────────────── */
function App() {
  const { user, isAuthenticated, checkAuth } = useAuthStore();
  const [view, setView] = useState('landing');
  const [selectedSession, setSelectedSession] = useState(null);

  useEffect(() => {
    checkAuth();
  }, []);

  useEffect(() => {
    if (isAuthenticated) {
      if (user?.user_type === 'hr') setView('hr_dashboard');
      else if (user?.user_type === 'admin') setView('admin');
      else setView('dashboard');
    } else {
      // Allow magic links (guest sessions) to bypass landing if URL has tokens
      const params = new URLSearchParams(window.location.search);
      if (params.get('token') && params.get('drive_id')) {
        setView('interview');
      }
    }
  }, [isAuthenticated, user]);

  const switchView = (v) => {
    window.scrollTo(0, 0);
    setView(v);
  };

  return (
    <div className="min-h-screen bg-[#020617] text-white">
      {view !== 'interview' && view !== 'admin' && view !== 'hr_dashboard' && view !== 'report' && (
        <Navbar
          onShowLogin={() => switchView('login')}
          onShowRegister={() => switchView('register')}
          onShowDashboard={() => {
            if (user?.user_type === 'hr') switchView('hr_dashboard');
            else if (user?.user_type === 'admin') switchView('admin');
            else switchView('dashboard');
          }}
          onShowAdmin={() => switchView('admin')}
          onHome={() => switchView('landing')}
        />
      )}

      <main>
        {view === 'admin' ? <AdminDashboard /> :
         view === 'hr_dashboard' ? (
           <HRDashboard onViewReport={(id) => { 
             setSelectedSession(id); 
             switchView('report'); 
           }} />
         ) :
         view === 'report' ? (
           <InterviewReport sessionId={selectedSession} onBack={() => {
             if (user?.user_type === 'hr') switchView('hr_dashboard');
             else switchView('dashboard');
           }} />
         ) :
         view === 'interview' ? (
           <InterviewRoom onComplete={(sessionId) => { 
             if (sessionId) setSelectedSession(sessionId); 
             switchView('report'); 
           }} />
         ) :
         view === 'dashboard' ? (
           <StudentDashboard 
             onStartInterview={() => switchView('interview')} 
             onViewReport={(id) => {
               setSelectedSession(id);
               switchView('report');
             }} 
           />
         ) :
         view === 'landing' ? <LandingPage onRegister={() => switchView('register')} /> : (
          <div className="max-w-7xl mx-auto pt-40 pb-32 flex justify-center">
            <div className="w-full max-w-md">
              {view === 'login' ? (
                <Login 
                  onToggleMode={() => switchView('register')} 
                  onSuccess={(u) => {
                    const target = u?.user_type === 'hr' ? 'hr_dashboard' : 'dashboard';
                    setView(target);
                  }} 
                />
              ) : (
                <Register 
                  onToggleMode={() => switchView('login')} 
                  onSuccess={() => switchView('login')} 
                />
              )}
            </div>
          </div>
        )}
      </main>

      {view !== 'interview' && view !== 'report' && (
        <footer className="py-12 border-t border-white/5 text-center bg-[#0a0f1e]">
          <div className="text-2xl font-black text-white mb-4 tracking-tighter">Vedrix</div>
          <p className="text-slate-500 font-bold uppercase tracking-widest text-[10px]">© 2026 Vedrix AI System. Building the future of hiring.</p>
        </footer>
      )}
    </div>
  );
}

export default App;
