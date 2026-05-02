import React, { useState } from 'react';
import useAuthStore from '../store/useAuthStore';
import { Mail, Lock, Loader2, ArrowRight } from 'lucide-react';

const Login = ({ onToggleMode, onSuccess }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const { login, isLoading, error } = useAuthStore();

  const handleSubmit = async (e) => {
    e.preventDefault();
    const success = await login(username, password);
    if (success) {
      onSuccess?.();
    }
  };

  return (
    <div className="w-full max-w-md mx-auto p-8 bg-white/5 backdrop-blur-xl rounded-3xl shadow-2xl border border-white/10">
      <div className="text-center mb-8">
        <h2 className="text-3xl font-bold text-white mb-2">Welcome Back</h2>
        <p className="text-slate-400">Enter your credentials to access your interview dashboard</p>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-red-500/10 border border-red-500/20 text-red-400 text-sm rounded-xl">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <label className="block text-xs font-black uppercase text-slate-400 tracking-widest mb-1.5 ml-1">Username</label>
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
              <Mail size={18} />
            </div>
            <input
              type="text"
              required
              className="block w-full pl-10 pr-3 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none"
              placeholder="Your username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
          </div>
        </div>

        <div>
          <label className="block text-xs font-black uppercase text-slate-400 tracking-widest mb-1.5 ml-1">Password</label>
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
              <Lock size={18} />
            </div>
            <input
              type="password"
              required
              className="block w-full pl-10 pr-3 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
        </div>

        <div className="flex items-center justify-between text-sm">
          <label className="flex items-center text-slate-500 text-xs font-bold uppercase tracking-widest">
            <input type="checkbox" className="rounded border-white/10 bg-white/5 text-purple-600 focus:ring-purple-500 mr-2" />
            Remember me
          </label>
          <a href="#" className="text-purple-400 text-xs font-bold uppercase tracking-widest hover:text-purple-300">Forgot password?</a>
        </div>

        <button
          type="submit"
          disabled={isLoading}
          className="w-full bg-purple-600 text-white py-4 px-4 rounded-xl font-black uppercase tracking-widest text-sm hover:bg-purple-500 shadow-[0_0_40px_rgba(147,51,234,0.3)] transition-all flex items-center justify-center space-x-2 active:scale-95 disabled:opacity-70"
        >
          {isLoading ? (
            <Loader2 className="animate-spin" size={20} />
          ) : (
            <>
              <span>Sign In</span>
              <ArrowRight size={20} />
            </>
          )}
        </button>
      </form>

      <div className="mt-8 text-center text-sm text-slate-500">
        Don't have an account?{' '}
        <button onClick={onToggleMode} className="text-purple-400 font-bold hover:text-purple-300">
          Create account
        </button>
      </div>
    </div>
  );
};

export default Login;
