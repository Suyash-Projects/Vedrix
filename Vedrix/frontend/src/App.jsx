import React, { useState, useEffect } from 'react';
import { 
  ShieldCheck, 
  Cpu, 
  UserCheck, 
  Zap, 
  ChevronRight, 
  Menu, 
  X,
  LogOut,
  LayoutDashboard,
  BookOpen,
  Briefcase,
  Play,
  Star,
  Settings as SettingsIcon,
  Users
} from 'lucide-react';
import Login from './pages/Login';
import Register from './pages/Register';
import InterviewRoom from './pages/InterviewRoom';
import AdminDashboard from './pages/AdminDashboard';
import HRDashboard from './pages/HRDashboard';
import useAuthStore from './store/useAuthStore';

/* ─────────────────────────────────────────────
   NAVBAR
───────────────────────────────────────────── */
const Navbar = ({ onShowLogin, onShowRegister, onShowDashboard, onShowAdmin, onHome }) => {
  const [isOpen, setIsOpen] = useState(false);
  const { isAuthenticated, user, logout } = useAuthStore();
  const isAdmin = user?.user_type === 'admin';
  const isHR = user?.user_type === 'hr';

  return (
    <nav className="bg-white/80 backdrop-blur-md sticky top-0 z-50 border-b border-gray-100">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16 items-center">
          <div className="flex items-center">
            <div
              className="text-2xl font-bold bg-gradient-to-r from-purple-600 to-indigo-600 bg-clip-text text-transparent cursor-pointer"
              onClick={onHome}
            >
              Vedrix
            </div>
          </div>

          <div className="hidden md:block">
            <div className="ml-10 flex items-baseline space-x-8 text-sm font-medium text-gray-600">
              <a href="#how-it-works" className="hover:text-purple-600 transition-colors">How it Works</a>
              <a href="#features" className="hover:text-purple-600 transition-colors">Features</a>
              {isAdmin && (
                <button onClick={onShowAdmin} className="text-red-500 font-bold hover:text-red-700 transition-colors">
                  System Admin
                </button>
              )}
            </div>
          </div>

          <div className="hidden md:flex items-center space-x-4">
            {isAuthenticated ? (
              <div className="flex items-center space-x-4">
                <button
                  onClick={onShowDashboard}
                  className="flex items-center space-x-1 text-sm font-medium text-purple-600 hover:text-purple-800 px-3 py-2"
                >
                  <LayoutDashboard size={16} />
                  <span>{isHR ? 'HR Panel' : 'Dashboard'}</span>
                </button>
                <span className="text-sm font-medium text-gray-500">|</span>
                <span className="text-sm font-medium text-gray-700 italic text-xs uppercase tracking-tighter font-bold">
                  {user?.user_type}: {user?.first_name}
                </span>
                <button
                  onClick={logout}
                  className="flex items-center space-x-1 text-sm font-medium text-red-500 hover:text-red-700 px-3 py-2"
                >
                  <LogOut size={16} />
                  <span>Logout</span>
                </button>
              </div>
            ) : (
              <>
                <button
                  onClick={onShowLogin}
                  className="text-sm font-medium text-gray-700 hover:text-purple-600 transition-colors px-4 py-2"
                >
                  Login
                </button>
                <button
                  onClick={onShowRegister}
                  className="bg-purple-600 text-white text-sm font-medium px-5 py-2.5 rounded-full hover:bg-purple-700 transition-all shadow-md hover:shadow-lg active:scale-95"
                >
                  Sign Up Free
                </button>
              </>
            )}
          </div>

          <div className="md:hidden">
            <button onClick={() => setIsOpen(!isOpen)} className="text-gray-500 hover:text-purple-600">
              {isOpen ? <X size={24} /> : <Menu size={24} />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile menu */}
      {isOpen && (
        <div className="md:hidden bg-white border-b border-gray-100 p-4 space-y-4 shadow-xl">
          <a href="#how-it-works" className="block text-base font-medium text-gray-700">How it Works</a>
          <a href="#features" className="block text-base font-medium text-gray-700">Features</a>
          {isAdmin && <button onClick={onShowAdmin} className="w-full text-left py-2 text-red-500 font-bold">System Admin</button>}
          {isAuthenticated ? (
            <>
              <button onClick={onShowDashboard} className="w-full text-left py-2 text-purple-600 font-medium">{isHR ? 'HR Panel' : 'Dashboard'}</button>
              <button onClick={logout} className="w-full text-left py-2 text-red-500 font-medium">Logout</button>
            </>
          ) : (
            <>
              <button onClick={onShowLogin} className="w-full text-center py-2 text-gray-700 border border-gray-200 rounded-lg">Login</button>
              <button onClick={onShowRegister} className="w-full text-center py-2 bg-purple-600 text-white rounded-lg">Sign Up Free</button>
            </>
          )}
        </div>
      )}
    </nav>
  );
};

/* ─────────────────────────────────────────────
   FEATURE CARD
───────────────────────────────────────────── */
const FeatureCard = ({ icon: Icon, title, description }) => (
  <div className="p-8 bg-white rounded-2xl border border-gray-100 shadow-sm hover:shadow-xl transition-all group hover:-translate-y-1">
    <div className="w-12 h-12 bg-purple-50 rounded-xl flex items-center justify-center text-purple-600 mb-6 group-hover:bg-purple-600 group-hover:text-white transition-colors">
      <Icon size={24} />
    </div>
    <h3 className="text-xl font-bold text-gray-900 mb-3">{title}</h3>
    <p className="text-gray-600 leading-relaxed">{description}</p>
  </div>
);

/* ─────────────────────────────────────────────
   DASHBOARD (STUDENT ONLY)
───────────────────────────────────────────── */
const Dashboard = ({ onStartInterview, onShowAdmin }) => {
  const { user } = useAuthStore();
  const isAdmin = user?.user_type === 'admin';

  return (
    <div className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-5xl mx-auto">
        <div className="mb-10 flex justify-between items-start">
          <div>
            <h1 className="text-4xl font-extrabold text-gray-900">
              Welcome back, <span className="text-purple-600">{user?.first_name || 'User'}</span> 👋
            </h1>
            <p className="mt-2 text-gray-500 text-lg">
              {isAdmin ? "Global system oversight and user governance." : "Your next AI-led technical round is ready."}
            </p>
          </div>
          {isAdmin && (
            <button 
              onClick={onShowAdmin}
              className="flex items-center space-x-2 bg-slate-900 text-white px-6 py-3 rounded-2xl font-bold hover:bg-slate-800 transition-all shadow-xl active:scale-95"
            >
              <ShieldAlert size={18} />
              <span>Admin Panel</span>
            </button>
          )}
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 mb-10">
          {[
            { label: 'Interviews', value: '0', icon: BookOpen },
            { label: 'Avg. Score', value: '—', icon: Star },
            { label: 'Profile Status', value: '80%', icon: UserCheck },
          ].map(({ label, value, icon: Icon }) => (
            <div key={label} className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6 flex items-center space-x-4">
              <div className="w-12 h-12 bg-purple-50 rounded-xl flex items-center justify-center text-purple-600">
                <Icon size={22} />
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900">{value}</p>
                <p className="text-sm text-gray-500">{label}</p>
              </div>
            </div>
          ))}
        </div>

        <div className="bg-gradient-to-br from-purple-600 to-indigo-600 rounded-3xl p-10 text-white flex flex-col sm:flex-row items-center justify-between gap-6">
          <div className="max-w-xl">
            <h2 className="text-2xl font-bold mb-2">Start Agentic AI Interview</h2>
            <p className="text-purple-100">
              Join a high-fidelity, adaptive interview. The AI will evaluate your technical depth, accuracy, and communication in real-time.
            </p>
          </div>
          <button
            onClick={onStartInterview}
            className="flex items-center space-x-2 bg-white text-purple-700 font-bold px-8 py-4 rounded-2xl hover:bg-purple-50 transition-all shadow-xl active:scale-95 whitespace-nowrap"
          >
            <Play size={18} />
            <span>Join Room</span>
          </button>
        </div>
      </div>
    </div>
  );
};

/* ─────────────────────────────────────────────
   LANDING PAGE
───────────────────────────────────────────── */
const LandingPage = ({ onRegister }) => (
  <>
    <section id="how-it-works" className="relative pt-20 pb-32 overflow-hidden">
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-7xl h-full -z-10">
        <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-purple-200/20 blur-[120px] rounded-full" />
        <div className="absolute bottom-0 left-0 w-[500px] h-[500px] bg-indigo-200/20 blur-[120px] rounded-full" />
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        <div className="inline-flex items-center space-x-2 bg-purple-50 text-purple-700 px-4 py-2 rounded-full text-sm font-semibold mb-8 border border-purple-100">
          <Zap size={16} />
          <span>Agentic & Adaptive Interviewing</span>
        </div>

        <h1 className="text-6xl md:text-7xl font-extrabold tracking-tight text-gray-900 mb-6 leading-tight">
          Building the Future of <br />
          <span className="bg-gradient-to-r from-purple-600 via-indigo-600 to-purple-600 bg-[length:200%_auto] animate-gradient bg-clip-text text-transparent">
            Agentic Evaluation
          </span>
        </h1>

        <p className="max-w-2xl mx-auto text-xl text-gray-600 mb-10 leading-relaxed">
          The only platform where AI interviewer agents conduct deep technical rounds, supervised in real-time by HR experts.
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center space-y-4 sm:space-y-0 sm:space-x-6">
          <button
            onClick={onRegister}
            className="w-full sm:w-auto bg-purple-600 text-white px-8 py-4 rounded-full font-bold text-lg hover:bg-purple-700 shadow-xl shadow-purple-500/20 flex items-center justify-center group transition-all"
          >
            Start Free Assessment
            <ChevronRight className="ml-2 group-hover:translate-x-1 transition-transform" />
          </button>
          <button className="w-full sm:w-auto bg-white text-gray-900 border-2 border-gray-100 px-8 py-4 rounded-full font-bold text-lg hover:bg-gray-50 transition-all">
            HR Dashboard Demo
          </button>
        </div>
      </div>
    </section>

    <section id="features" className="py-24 bg-gray-50/50 border-y border-gray-100">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <FeatureCard
            icon={Cpu}
            title="Agentic Reasoning"
            description="Four specialized AI agents manage dialogue, evaluation, and adaptive state transitions during the interview."
          />
          <FeatureCard
            icon={Users}
            title="HR Live Takeover"
            description="Observe interviews in real-time. Pause AI execution or take direct control of the conversation at any moment."
          />
          <FeatureCard
            icon={ShieldCheck}
            title="Secure Magic Links"
            description="One-time candidate access with built-in tab-switch detection and fullscreen proctoring requirements."
          />
        </div>
      </div>
    </section>
  </>
);

/* ─────────────────────────────────────────────
   ROOT APP
───────────────────────────────────────────── */
function App() {
  // Views: 'landing' | 'login' | 'register' | 'dashboard' | 'interview' | 'admin' | 'hr_dashboard'
  const [view, setView] = useState('landing');
  const { checkAuth, isAuthenticated, user, clearError } = useAuthStore();

  // Check for Magic Link on mount
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const driveId = urlParams.get('drive_id');
    const token = urlParams.get('token');
    if (driveId && token) {
      setView('interview');
    }
  }, []);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  useEffect(() => {
    if (isAuthenticated && (view === 'login' || view === 'register')) {
      if (user?.user_type === 'hr') setView('hr_dashboard');
      else if (user?.user_type === 'admin') setView('admin');
      else setView('dashboard');
    }
  }, [isAuthenticated, user, view]);

  const switchView = (newView) => {
    clearError();
    setView(newView);
    if (newView === 'landing') {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  const renderDashboard = () => {
    if (user?.user_type === 'hr') return <HRDashboard />;
    if (user?.user_type === 'admin') return <AdminDashboard />;
    return <Dashboard 
      onStartInterview={() => switchView('interview')} 
      onShowAdmin={() => switchView('admin')}
    />;
  };

  return (
    <div className="min-h-screen bg-white text-gray-900">
      {/* Hide navbar during interview for maximum realism/focus */}
      {view !== 'interview' && view !== 'admin' && view !== 'hr_dashboard' && (
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
        {view === 'admin' ? (
          <AdminDashboard />
        ) : view === 'hr_dashboard' ? (
          <HRDashboard />
        ) : view === 'interview' ? (
          <InterviewRoom onComplete={() => {
            if (isAuthenticated) {
               if (user?.user_type === 'hr') switchView('hr_dashboard');
               else switchView('dashboard');
            } else {
               switchView('landing');
            }
          }} />
        ) : view === 'dashboard' ? (
          <Dashboard 
            onStartInterview={() => switchView('interview')} 
            onShowAdmin={() => switchView('admin')}
          />
        ) : view === 'landing' ? (
          <div className="max-w-7xl mx-auto">
            <LandingPage onRegister={() => switchView('register')} />
          </div>
        ) : (
          <div className="max-w-7xl mx-auto pt-20 pb-32">
            {view === 'login' ? (
              <Login
                onToggleMode={() => switchView('register')}
                onSuccess={() => {
                   if (user?.user_type === 'hr') switchView('hr_dashboard');
                   else switchView('dashboard');
                }}
              />
            ) : (
              <Register
                onToggleMode={() => switchView('login')}
                onSuccess={() => switchView('login')}
              />
            )}
          </div>
        )}
      </main>

      {(view === 'landing' || view === 'login' || view === 'register') && (
        <footer className="bg-white py-12 border-t border-gray-100 text-center">
          <div className="text-2xl font-bold text-purple-600 mb-4">Vedrix</div>
          <p className="text-gray-500 text-sm">© 2026 Vedrix AI System. All rights reserved.</p>
        </footer>
      )}
    </div>
  );
}
