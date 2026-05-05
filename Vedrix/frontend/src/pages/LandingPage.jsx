import { ShieldCheck, Cpu, Zap, ChevronRight, Activity } from 'lucide-react';
import { Link } from 'react-router-dom';
import LandingSections from '../components/LandingSections';

const LandingPage = () => (
  <div className="relative min-h-screen pt-40 pb-20 px-8 overflow-hidden font-sans">
    {/* Ambient Glows */}
    <div className="absolute top-[-20%] left-[-10%] w-[60%] h-[60%] bg-purple-900/20 blur-[150px] rounded-full" />
    <div className="absolute bottom-[-20%] right-[-10%] w-[60%] h-[60%] bg-indigo-900/20 blur-[150px] rounded-full" />

    {/* Hero — 2 columns */}
    <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-20 items-center relative z-10">

      {/* Left: copy */}
      <div className="space-y-10">
        <div className="inline-flex items-center space-x-3 bg-white/5 border border-white/10 px-5 py-2 rounded-full">
          <span className="w-2 h-2 bg-purple-500 rounded-full animate-pulse" />
          <span className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-300">Structured AI Interview Workflows</span>
        </div>

        <h1 className="text-7xl md:text-8xl font-black text-white leading-[0.9] tracking-tighter">
          Better Interviews. <br />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-indigo-300 italic">Clearer Hiring Decisions.</span>
        </h1>

        <p className="text-xl text-slate-400 max-w-lg leading-relaxed font-medium">
          Vedrix helps teams run consistent interviews, capture candidate responses, and review structured feedback in one place.
        </p>

        <div className="flex flex-col sm:flex-row gap-6">
          <Link to="/register" className="bg-purple-600 text-white px-12 py-5 rounded-2xl font-black uppercase tracking-widest text-sm hover:bg-purple-500 shadow-[0_0_50px_rgba(147,51,234,0.3)] transition-all flex items-center justify-center space-x-3 active:scale-95">
            <span>Get Started</span>
            <ChevronRight size={20} />
          </Link>
          <div className="flex items-center space-x-4 px-6 border-l border-white/10">
            <div className="w-11 h-11 rounded-2xl border border-white/10 bg-white/5 flex items-center justify-center">
              <ShieldCheck size={18} className="text-purple-400" />
            </div>
            <div className="text-left">
              <p className="text-white font-bold text-sm">Built for candidate and recruiter workflows</p>
              <p className="text-slate-500 text-xs">Focused on consistency, visibility, and review quality</p>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-8 pt-10 border-t border-white/5">
          {[
            { label: 'Interviews', val: 'Structured', icon: Zap },
            { label: 'Feedback', val: 'Actionable', icon: ShieldCheck },
            { label: 'Workflow', val: 'Unified', icon: Cpu },
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

      {/* Right: mockup */}
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
                <span className="text-[10px] font-black text-purple-400 uppercase tracking-widest">Interview analysis in progress</span>
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

    {/* Full-width sections below hero */}
    <LandingSections />
  </div>
);

export default LandingPage;
