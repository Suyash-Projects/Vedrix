import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import useAuthStore from '../store/useAuthStore';
import { Mail, Lock, User, Briefcase, Loader2, ArrowRight } from 'lucide-react';

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

      <div className="mt-8 text-center text-sm text-slate-500">
        Already have an account?{' '}
        <Link to="/login" className="text-purple-400 font-bold hover:text-purple-300">Sign In</Link>
      </div>
    </div>
  );
};

export default Register;
