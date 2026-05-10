import { Mic, BarChart3, ShieldCheck, ChevronRight, BrainCircuit, User, LogOut } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import useAuthStore from '../store/useAuthStore';

const LandingPage = () => {
  const { isAuthenticated, user, logout } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/home');
  };

  const getDashboardPath = () => {
    if (user?.user_type === 'hr') return '/hr';
    if (user?.user_type === 'admin') return '/admin';
    return '/dashboard';
  };

  return (
  <div className="bg-[#020617] overflow-hidden">

    {/* ── HERO ─────────────────────────────────────────────────────────── */}
    <section className="relative min-h-[calc(100vh-80px)] flex items-center px-6 md:px-12">
      {/* Ambient glows */}
      <div className="absolute top-0 left-[-10%] w-[50%] h-[70%] bg-purple-900/20 blur-[120px] rounded-full pointer-events-none" />
      <div className="absolute bottom-0 right-[-10%] w-[50%] h-[60%] bg-indigo-900/15 blur-[120px] rounded-full pointer-events-none" />

      <div className="max-w-7xl mx-auto w-full grid grid-cols-1 lg:grid-cols-2 gap-16 items-center relative z-10 py-16">

        {/* Left */}
        <div className="space-y-8">
          <div className="inline-flex items-center space-x-2 bg-purple-500/10 border border-purple-500/20 px-4 py-2 rounded-full">
            <span className="w-2 h-2 bg-purple-400 rounded-full animate-pulse" />
            <span className="text-xs font-bold uppercase tracking-widest text-purple-300">AI-Powered Interview Platform</span>
          </div>

          <h1 className="text-5xl md:text-6xl lg:text-7xl font-black text-white leading-[1.0] tracking-tight">
            Smarter Interviews.<br />
            <span className="bg-gradient-to-r from-purple-400 via-violet-400 to-indigo-400 bg-clip-text text-transparent">
              Better Hires.
            </span>
          </h1>

          <p className="text-lg text-slate-400 max-w-xl leading-relaxed">
            Vedrix conducts adaptive AI interviews, evaluates candidates in real-time, and delivers structured reports — so your team can focus on the right people.
          </p>

          <div className="flex flex-wrap gap-4">
            {isAuthenticated ? (
              <>
                <div className="inline-flex items-center space-x-3 bg-white/5 border border-white/10 px-6 py-3 rounded-2xl">
                  <div className="w-10 h-10 bg-purple-600 rounded-full flex items-center justify-center">
                    <User size={18} className="text-white" />
                  </div>
                  <div className="text-left">
                    <p className="text-white font-bold text-sm">{user?.first_name} {user?.last_name}</p>
                    <p className="text-slate-400 text-xs capitalize">{user?.user_type}</p>
                  </div>
                </div>
                <Link to={getDashboardPath()}
                  className="inline-flex items-center space-x-2 bg-purple-600 hover:bg-purple-500 text-white font-bold px-8 py-4 rounded-2xl transition-all shadow-[0_0_40px_rgba(124,58,237,0.35)] active:scale-95">
                  <span>Go to Dashboard</span>
                  <ChevronRight size={18} />
                </Link>
                <button onClick={handleLogout}
                  className="inline-flex items-center space-x-2 bg-white/5 hover:bg-white/10 border border-white/10 text-white font-bold px-8 py-4 rounded-2xl transition-all">
                  <span>Logout</span>
                  <LogOut size={18} />
                </button>
              </>
            ) : (
              <>
                <Link to="/register"
                  className="inline-flex items-center space-x-2 bg-purple-600 hover:bg-purple-500 text-white font-bold px-8 py-4 rounded-2xl transition-all shadow-[0_0_40px_rgba(124,58,237,0.35)] active:scale-95">
                  <span>Get Started Free</span>
                  <ChevronRight size={18} />
                </Link>
                <Link to="/login"
                  className="inline-flex items-center space-x-2 bg-white/5 hover:bg-white/10 border border-white/10 text-white font-bold px-8 py-4 rounded-2xl transition-all">
                  <span>Sign In</span>
                </Link>
              </>
            )}
          </div>

          <div className="flex items-center space-x-8 pt-4 border-t border-white/5">
            {[
              { val: 'Adaptive', label: 'AI Questions' },
              { val: 'Real-time', label: 'Evaluation' },
              { val: 'Instant', label: 'Reports' },
            ].map(s => (
              <div key={s.label}>
                <p className="text-white font-black text-lg">{s.val}</p>
                <p className="text-slate-500 text-xs font-bold uppercase tracking-widest">{s.label}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Right — mockup card */}
        <div className="relative hidden lg:block">
          <div className="absolute inset-0 bg-purple-600/15 blur-[80px] rounded-full" />
          <div className="relative bg-white/[0.03] border border-white/10 rounded-[2rem] p-8 shadow-2xl backdrop-blur-sm">
            {/* Fake browser chrome */}
            <div className="flex items-center space-x-2 mb-6">
              <div className="w-3 h-3 rounded-full bg-red-500/60" />
              <div className="w-3 h-3 rounded-full bg-amber-500/60" />
              <div className="w-3 h-3 rounded-full bg-emerald-500/60" />
              <div className="ml-4 flex-1 h-6 bg-white/5 rounded-lg" />
            </div>

            {/* AI interviewer card */}
            <div className="bg-white/5 border border-white/10 rounded-2xl p-6 mb-4">
              <div className="flex items-center space-x-3 mb-4">
                <div className="w-10 h-10 bg-gradient-to-tr from-purple-600 to-indigo-400 rounded-xl flex items-center justify-center">
                  <BrainCircuit size={20} className="text-white" />
                </div>
                <div>
                  <p className="text-white font-bold text-sm">Vedrix AI Interviewer</p>
                  <div className="flex items-center space-x-1">
                    <div className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-pulse" />
                    <p className="text-emerald-400 text-[10px] font-bold uppercase tracking-widest">Live</p>
                  </div>
                </div>
              </div>
              <div className="bg-white/5 rounded-xl p-4 text-sm text-slate-300 italic leading-relaxed">
                "Can you walk me through how you'd design a scalable REST API for a high-traffic application?"
              </div>
            </div>

            {/* Score bars */}
            <div className="space-y-3">
              {[
                { label: 'Technical Accuracy', pct: 88, color: 'bg-purple-500' },
                { label: 'Communication', pct: 74, color: 'bg-indigo-400' },
                { label: 'Depth of Knowledge', pct: 91, color: 'bg-violet-500' },
              ].map(b => (
                <div key={b.label}>
                  <div className="flex justify-between mb-1">
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">{b.label}</span>
                    <span className="text-[10px] font-black text-white">{b.pct}%</span>
                  </div>
                  <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
                    <div className={`h-full ${b.color} rounded-full`} style={{ width: `${b.pct}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>

    {/* ── FEATURES ─────────────────────────────────────────────────────── */}
    <section className="py-24 px-6 md:px-12 border-t border-white/5">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-16">
          <p className="text-purple-400 text-xs font-black uppercase tracking-[0.3em] mb-3">What Vedrix Does</p>
          <h2 className="text-4xl md:text-5xl font-black text-white tracking-tight">
            Everything you need to hire better
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[
            {
              icon: BrainCircuit,
              title: 'Adaptive AI',
              desc: 'Questions evolve based on every answer. No two interviews are the same.',
              color: 'text-purple-400',
              bg: 'bg-purple-500/10 border-purple-500/20',
            },
            {
              icon: Mic,
              title: 'Voice-First',
              desc: 'Candidates speak naturally. Groq Whisper transcribes in under 300ms.',
              color: 'text-indigo-400',
              bg: 'bg-indigo-500/10 border-indigo-500/20',
            },
            {
              icon: BarChart3,
              title: 'Live Scoring',
              desc: 'Real-time evaluation across accuracy, clarity, depth, and communication.',
              color: 'text-violet-400',
              bg: 'bg-violet-500/10 border-violet-500/20',
            },
            {
              icon: ShieldCheck,
              title: 'Fair & Unbiased',
              desc: 'Every candidate gets the same structured, objective assessment.',
              color: 'text-emerald-400',
              bg: 'bg-emerald-500/10 border-emerald-500/20',
            },
          ].map(f => (
            <div key={f.title} className="bg-white/[0.03] border border-white/8 rounded-3xl p-8 hover:bg-white/[0.06] hover:border-white/15 transition-all group">
              <div className={`w-12 h-12 ${f.bg} border rounded-2xl flex items-center justify-center mb-6`}>
                <f.icon size={22} className={f.color} />
              </div>
              <h3 className="text-white font-black text-lg mb-2">{f.title}</h3>
              <p className="text-slate-400 text-sm leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>

    {/* ── HOW IT WORKS ─────────────────────────────────────────────────── */}
    <section className="py-24 px-6 md:px-12 border-t border-white/5">
      <div className="max-w-4xl mx-auto">
        <div className="text-center mb-16">
          <p className="text-purple-400 text-xs font-black uppercase tracking-[0.3em] mb-3">Simple Process</p>
          <h2 className="text-4xl md:text-5xl font-black text-white tracking-tight">How it works</h2>
        </div>

        <div className="space-y-4">
          {[
            { n: '01', title: 'HR creates a drive', desc: 'Set the job role, required skills, and generate invite links for candidates.' },
            { n: '02', title: 'Candidate joins the room', desc: 'Opens the link, passes hardware check, and the AI interviewer begins immediately.' },
            { n: '03', title: 'AI conducts the interview', desc: 'Adaptive questions across warmup, technical, stress, and behavioral phases.' },
            { n: '04', title: 'Instant report delivered', desc: 'Scores, strengths, weaknesses, and full transcript sent to HR and candidate by email.' },
          ].map((step) => (
            <div key={step.n} className="flex items-start space-x-6 bg-white/[0.03] border border-white/8 rounded-2xl p-6 hover:border-purple-500/20 transition-all">
              <span className="text-3xl font-black text-purple-500/40 shrink-0 w-12">{step.n}</span>
              <div>
                <h3 className="text-white font-black text-lg mb-1">{step.title}</h3>
                <p className="text-slate-400 text-sm leading-relaxed">{step.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>

    {/* ── CTA ──────────────────────────────────────────────────────────── */}
    <section className="py-24 px-6 md:px-12 border-t border-white/5">
      <div className="max-w-3xl mx-auto text-center">
        <h2 className="text-4xl md:text-5xl font-black text-white tracking-tight mb-6">
          Ready to transform your hiring?
        </h2>
        <p className="text-slate-400 text-lg mb-10">
          Join teams using Vedrix to run faster, fairer, and more insightful interviews.
        </p>
        <div className="flex flex-wrap justify-center gap-4">
          {isAuthenticated ? (
            <>
              <div className="inline-flex items-center space-x-3 bg-white/5 border border-white/10 px-6 py-3 rounded-2xl">
                <div className="w-10 h-10 bg-purple-600 rounded-full flex items-center justify-center">
                  <User size={18} className="text-white" />
                </div>
                <div className="text-left">
                  <p className="text-white font-bold text-sm">{user?.first_name} {user?.last_name}</p>
                  <p className="text-slate-400 text-xs capitalize">{user?.user_type}</p>
                </div>
              </div>
              <Link to={getDashboardPath()}
                className="inline-flex items-center space-x-2 bg-purple-600 hover:bg-purple-500 text-white font-black px-10 py-5 rounded-2xl transition-all shadow-[0_0_50px_rgba(124,58,237,0.4)] active:scale-95 text-sm uppercase tracking-widest">
                <span>Go to Dashboard</span>
                <ChevronRight size={18} />
              </Link>
              <button onClick={handleLogout}
                className="inline-flex items-center space-x-2 bg-white/5 hover:bg-white/10 border border-white/10 text-white font-bold px-10 py-5 rounded-2xl transition-all text-sm">
                <span>Logout</span>
                <LogOut size={18} />
              </button>
            </>
          ) : (
            <>
              <Link to="/register"
                className="inline-flex items-center space-x-2 bg-purple-600 hover:bg-purple-500 text-white font-black px-10 py-5 rounded-2xl transition-all shadow-[0_0_50px_rgba(124,58,237,0.4)] active:scale-95 text-sm uppercase tracking-widest">
                <span>Start for Free</span>
                <ChevronRight size={18} />
              </Link>
              <Link to="/login"
                className="inline-flex items-center space-x-2 bg-white/5 hover:bg-white/10 border border-white/10 text-white font-bold px-10 py-5 rounded-2xl transition-all text-sm">
                <span>Sign In</span>
              </Link>
            </>
          )}
        </div>
      </div>
    </section>

  </div>
);
};

export default LandingPage;
