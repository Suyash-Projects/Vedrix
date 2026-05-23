import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import useAuthStore from '../store/useAuthStore';
import { Mail, Lock, User, Briefcase, Loader2, ArrowRight, Github, Linkedin } from 'lucide-react';

const Register = () => {
  const [formData, setFormData] = useState({
    email: '',
    username: '',
    password: '',
    first_name: '',
    last_name: '',
    user_type: 'student',
    company_name: '',
  });
  
  const { register, isLoading, error } = useAuthStore();
  const navigate = useNavigate();

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const success = await register(formData);
    if (success) {
      navigate('/login');
    }
  };

  const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

  return (
    <div className="w-full max-w-lg mx-auto p-8 bg-white/5 backdrop-blur-xl rounded-3xl shadow-2xl border border-white/10">
      <div className="text-center mb-8">
        <h2 className="text-3xl font-bold text-white mb-2">Create Account</h2>
        <p className="text-slate-400">Join Vedrix and master your interview skills</p>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-red-500/10 border border-red-500/20 text-red-400 text-sm rounded-xl">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-black uppercase text-slate-400 tracking-widest mb-1.5 ml-1">First Name</label>
            <input name="first_name" type="text" required
              className="block w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none transition-all"
              placeholder="John" onChange={handleChange} />
          </div>
          <div>
            <label className="block text-xs font-black uppercase text-slate-400 tracking-widest mb-1.5 ml-1">Last Name</label>
            <input name="last_name" type="text" required
              className="block w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none transition-all"
              placeholder="Doe" onChange={handleChange} />
          </div>
        </div>

        <div>
          <label className="block text-xs font-black uppercase text-slate-400 tracking-widest mb-1.5 ml-1">Email Address</label>
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500"><Mail size={18} /></div>
            <input name="email" type="email" required
              className="block w-full pl-10 pr-3 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none transition-all"
              placeholder="john@example.com" onChange={handleChange} />
          </div>
        </div>

        <div>
          <label className="block text-xs font-black uppercase text-slate-400 tracking-widest mb-1.5 ml-1">Username</label>
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500"><User size={18} /></div>
            <input name="username" type="text" required
              className="block w-full pl-10 pr-3 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none transition-all"
              placeholder="johndoe" onChange={handleChange} />
          </div>
        </div>

        <div>
          <label className="block text-xs font-black uppercase text-slate-400 tracking-widest mb-1.5 ml-1">Password</label>
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500"><Lock size={18} /></div>
            <input name="password" type="password" required
              className="block w-full pl-10 pr-3 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none transition-all"
              placeholder="••••••••" onChange={handleChange} />
          </div>
        </div>

        <div>
          <label className="block text-xs font-black uppercase text-slate-400 tracking-widest mb-1.5 ml-1">I am a...</label>
          <div className="grid grid-cols-2 gap-4 mt-2">
            <button type="button" onClick={() => setFormData({...formData, user_type: 'student'})}
              className={`py-3 px-4 rounded-xl border-2 transition-all flex items-center justify-center space-x-2 font-bold text-sm ${
                formData.user_type === 'student' ? 'border-purple-500 bg-purple-500/10 text-purple-400' : 'border-white/10 bg-white/5 text-slate-500 hover:border-white/20'
              }`}>
              <User size={18} /><span>Student</span>
            </button>
            <button type="button" onClick={() => setFormData({...formData, user_type: 'hr'})}
              className={`py-3 px-4 rounded-xl border-2 transition-all flex items-center justify-center space-x-2 font-bold text-sm ${
                formData.user_type === 'hr' ? 'border-indigo-500 bg-indigo-500/10 text-indigo-400' : 'border-white/10 bg-white/5 text-slate-500 hover:border-white/20'
              }`}>
              <Briefcase size={18} /><span>HR Expert</span>
            </button>
          </div>
        </div>

        {formData.user_type === 'hr' && (
          <div>
            <label className="block text-xs font-black uppercase text-slate-400 tracking-widest mb-1.5 ml-1">Company Name</label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500"><Briefcase size={18} /></div>
              <input name="company_name" type="text" required
                className="block w-full pl-10 pr-3 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-slate-600 focus:ring-2 focus:ring-indigo-500 outline-none transition-all"
                placeholder="e.g. Acme Corp" onChange={handleChange} />
            </div>
          </div>
        )}

        <button type="submit" disabled={isLoading}
          className="w-full bg-purple-600 text-white py-4 px-4 rounded-xl font-black uppercase tracking-widest text-sm hover:bg-purple-500 shadow-[0_0_40px_rgba(147,51,234,0.3)] transition-all flex items-center justify-center space-x-2 active:scale-95 disabled:opacity-70 mt-6"
        >
          {isLoading ? <Loader2 className="animate-spin" size={20} /> : <><span>Get Started</span><ArrowRight size={20} /></>}
        </button>
      </form>

      <div className="mt-8 flex items-center space-x-3">
        <div className="flex-1 h-px bg-white/10"></div>
        <span className="text-[10px] font-black uppercase text-slate-500 tracking-[0.2em]">or continue with</span>
        <div className="flex-1 h-px bg-white/10"></div>
      </div>

      <div className="mt-6 grid grid-cols-3 gap-3">
        <a
          href={`${API_BASE_URL}/auth/google/login`}
          className="flex items-center justify-center py-3 bg-white/5 border border-white/10 rounded-xl hover:bg-white/10 transition-all active:scale-95"
          title="Continue with Google"
        >
          <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
            <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-3.22 3.28-7.42 3.28-12.09z" fill="#4285F4" />
            <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
            <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.16H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.84l3.66-2.75z" fill="#FBBC05" />
            <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.16l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
          </svg>
        </a>
        <a
          href={`${API_BASE_URL}/auth/github/login`}
          className="flex items-center justify-center py-3 bg-white/5 border border-white/10 rounded-xl hover:bg-white/10 transition-all active:scale-95 text-slate-300"
          title="Continue with GitHub"
        >
          <Github size={20} />
        </a>
        <a
          href={`${API_BASE_URL}/auth/linkedin/login`}
          className="flex items-center justify-center py-3 bg-white/5 border border-white/10 rounded-xl hover:bg-white/10 transition-all active:scale-95 text-[#0A66C2]"
          title="Continue with LinkedIn"
        >
          <Linkedin size={20} />
        </a>
      </div>

      <div className="mt-8 text-center text-sm text-slate-500">
        Already have an account?{' '}
        <Link to="/login" className="text-purple-400 font-bold hover:text-purple-300">Sign In</Link>
      </div>
    </div>
  );
};

export default Register;
