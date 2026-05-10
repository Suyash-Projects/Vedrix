import { useState } from 'react';
import { Cpu, LogOut, Menu, X } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import useAuthStore from '../store/useAuthStore';

const Navbar = () => {
  const { isAuthenticated, user, logout } = useAuthStore();
  const [isOpen, setIsOpen] = useState(false);
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const getDashboardPath = () => {
    if (user?.user_type === 'hr') return '/hr';
    if (user?.user_type === 'admin') return '/admin';
    return '/dashboard';
  };

  return (
    <nav className="fixed top-0 left-0 right-0 z-[100] bg-[#020617]/80 backdrop-blur-xl border-b border-white/5">
      <div className="max-w-7xl mx-auto px-8 h-20 flex items-center justify-between">
        <Link
          to="/home"
          className="flex items-center space-x-3 cursor-pointer group"
        >
          <div className="w-10 h-10 bg-gradient-to-tr from-purple-600 to-indigo-400 rounded-xl flex items-center justify-center text-white shadow-lg shadow-purple-900/20 group-hover:scale-110 transition-all">
            <Cpu size={22} />
          </div>
          <span className="text-2xl font-black tracking-tighter text-white">Vedrix <span className="text-purple-400 text-sm align-top ml-1">AI</span></span>
        </Link>

        {/* Desktop Nav */}
        <div className="hidden md:flex items-center space-x-10">
          <Link to="/home" className="text-slate-400 hover:text-white font-bold text-sm uppercase tracking-widest transition-colors">Home</Link>
          {isAuthenticated && (
            <>
              <Link to={getDashboardPath()} className="text-slate-400 hover:text-white font-bold text-sm uppercase tracking-widest transition-colors">Dashboard</Link>
              {user?.user_type === 'admin' && (
                <Link to="/admin" className="text-amber-400 hover:text-amber-300 font-bold text-sm uppercase tracking-widest transition-colors">Admin</Link>
              )}
            </>
          )}
        </div>

        <div className="hidden md:flex items-center space-x-4">
          {!isAuthenticated ? (
            <>
              <Link to="/login" className="text-white font-bold px-6 py-2.5 rounded-xl hover:bg-white/5 transition-all">Sign In</Link>
              <Link to="/register" className="bg-purple-600 text-white font-bold px-8 py-2.5 rounded-xl hover:bg-purple-500 shadow-xl shadow-purple-900/30 transition-all active:scale-95">Register</Link>
            </>
          ) : (
            <div className="flex items-center space-x-6">
              <div className="flex flex-col text-right">
                <span className="text-white font-bold text-sm">{user?.first_name}</span>
                <span className="text-slate-500 text-[10px] font-black uppercase tracking-widest">{user?.user_type}</span>
              </div>
              <button 
                onClick={handleLogout}
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

      {isOpen && (
        <div className="md:hidden bg-[#020617]/95 border-t border-white/10 backdrop-blur-xl">
          <div className="px-6 py-4 space-y-3">
            <Link onClick={() => setIsOpen(false)} to={isAuthenticated ? getDashboardPath() : '/'}
              className="block text-slate-400 hover:text-white font-bold text-sm uppercase tracking-widest transition-colors">Home</Link>
            {isAuthenticated && (
              <Link onClick={() => setIsOpen(false)} to={getDashboardPath()}
                className="block text-slate-400 hover:text-white font-bold text-sm uppercase tracking-widest transition-colors">Dashboard</Link>
            )}
            {!isAuthenticated ? (
              <>
                <Link onClick={() => setIsOpen(false)} to="/login" className="block text-white font-bold px-4 py-3 rounded-xl hover:bg-white/5 transition-all">Sign In</Link>
                <Link onClick={() => setIsOpen(false)} to="/register" className="block bg-purple-600 text-white font-bold px-4 py-3 rounded-xl hover:bg-purple-500 transition-all">Register</Link>
              </>
            ) : (
              <button onClick={() => { setIsOpen(false); handleLogout(); }}
                className="w-full text-left text-slate-400 hover:text-red-400 font-bold px-4 py-3 rounded-xl hover:bg-red-500/10 transition-all">Logout</button>
            )}
          </div>
        </div>
      )}
    </nav>
  );
};

export default Navbar;
