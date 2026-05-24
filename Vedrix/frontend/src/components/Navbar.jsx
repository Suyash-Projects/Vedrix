import { useState } from 'react';
import { Cpu, LogOut, Menu, X, ChevronDown } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import useAuthStore from '../store/useAuthStore';

const Navbar = () => {
  const { isAuthenticated, user, logout } = useAuthStore();
  const [isOpen, setIsOpen] = useState(false);
  const [dropdownOpen, setDropdownOpen] = useState(null);
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

              {/* Student-specific nav */}
              {user?.user_type === 'student' && (
                <div className="relative" onMouseLeave={() => setDropdownOpen(null)}>
                  <button
                    onMouseEnter={() => setDropdownOpen('student')}
                    className="flex items-center gap-1 text-slate-400 hover:text-white font-bold text-sm uppercase tracking-widest transition-colors"
                    aria-expanded={dropdownOpen === 'student'}
                    aria-haspopup="true"
                  >
                    Growth <ChevronDown size={12} />
                  </button>
                  {dropdownOpen === 'student' && (
                    <div className="absolute top-full left-0 mt-2 bg-[#0f172a] border border-white/10 rounded-xl p-2 min-w-[180px] shadow-xl z-50">
                      <Link to="/dashboard/profile" className="block px-4 py-2 text-slate-300 hover:text-white hover:bg-white/5 rounded-lg text-sm font-bold transition-all">Skill Profile</Link>
                      <Link to="/dashboard/coaching/latest" className="block px-4 py-2 text-slate-300 hover:text-white hover:bg-white/5 rounded-lg text-sm font-bold transition-all">Coaching Plan</Link>
                    </div>
                  )}
                </div>
              )}

              {/* HR-specific nav */}
              {(user?.user_type === 'hr' || user?.user_type === 'admin') && (
                <div className="relative" onMouseLeave={() => setDropdownOpen(null)}>
                  <button
                    onMouseEnter={() => setDropdownOpen('hr')}
                    className="flex items-center gap-1 text-slate-400 hover:text-white font-bold text-sm uppercase tracking-widest transition-colors"
                    aria-expanded={dropdownOpen === 'hr'}
                    aria-haspopup="true"
                  >
                    HR Tools <ChevronDown size={12} />
                  </button>
                  {dropdownOpen === 'hr' && (
                    <div className="absolute top-full left-0 mt-2 bg-[#0f172a] border border-white/10 rounded-xl p-2 min-w-[180px] shadow-xl z-50">
                      <Link to="/hr/pipeline" className="block px-4 py-2 text-slate-300 hover:text-white hover:bg-white/5 rounded-lg text-sm font-bold transition-all">Pipeline</Link>
                      <Link to="/hr/schedule" className="block px-4 py-2 text-slate-300 hover:text-white hover:bg-white/5 rounded-lg text-sm font-bold transition-all">Schedule</Link>
                    </div>
                  )}
                </div>
              )}

              {/* Admin-specific nav */}
              {user?.user_type === 'admin' && (
                <div className="relative" onMouseLeave={() => setDropdownOpen(null)}>
                  <button
                    onMouseEnter={() => setDropdownOpen('admin')}
                    className="flex items-center gap-1 text-amber-400 hover:text-amber-300 font-bold text-sm uppercase tracking-widest transition-colors"
                    aria-expanded={dropdownOpen === 'admin'}
                    aria-haspopup="true"
                  >
                    Admin <ChevronDown size={12} />
                  </button>
                  {dropdownOpen === 'admin' && (
                    <div className="absolute top-full left-0 mt-2 bg-[#0f172a] border border-white/10 rounded-xl p-2 min-w-[180px] shadow-xl z-50">
                      <Link to="/admin" className="block px-4 py-2 text-slate-300 hover:text-white hover:bg-white/5 rounded-lg text-sm font-bold transition-all">Overview</Link>
                      <Link to="/admin/audit-trail" className="block px-4 py-2 text-slate-300 hover:text-white hover:bg-white/5 rounded-lg text-sm font-bold transition-all">Audit Trail</Link>
                      <Link to="/admin/qa-monitor" className="block px-4 py-2 text-slate-300 hover:text-white hover:bg-white/5 rounded-lg text-sm font-bold transition-all">QA Monitor</Link>
                      <Link to="/admin/health" className="block px-4 py-2 text-slate-300 hover:text-white hover:bg-white/5 rounded-lg text-sm font-bold transition-all">System Health</Link>
                      <Link to="/admin/supervisor" className="block px-4 py-2 text-slate-300 hover:text-white hover:bg-white/5 rounded-lg text-sm font-bold transition-all">AI Supervisor</Link>
                    </div>
                  )}
                </div>
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
              <>
                <Link onClick={() => setIsOpen(false)} to={getDashboardPath()}
                  className="block text-slate-400 hover:text-white font-bold text-sm uppercase tracking-widest transition-colors">Dashboard</Link>
                {user?.user_type === 'student' && (
                  <>
                    <Link onClick={() => setIsOpen(false)} to="/dashboard/profile"
                      className="block text-slate-400 hover:text-white font-bold text-sm uppercase tracking-widest transition-colors pl-4">Skill Profile</Link>
                    <Link onClick={() => setIsOpen(false)} to="/dashboard/coaching/latest"
                      className="block text-slate-400 hover:text-white font-bold text-sm uppercase tracking-widest transition-colors pl-4">Coaching</Link>
                  </>
                )}
                {(user?.user_type === 'hr' || user?.user_type === 'admin') && (
                  <>
                    <Link onClick={() => setIsOpen(false)} to="/hr/pipeline"
                      className="block text-slate-400 hover:text-white font-bold text-sm uppercase tracking-widest transition-colors pl-4">Pipeline</Link>
                    <Link onClick={() => setIsOpen(false)} to="/hr/schedule"
                      className="block text-slate-400 hover:text-white font-bold text-sm uppercase tracking-widest transition-colors pl-4">Schedule</Link>
                  </>
                )}
                {user?.user_type === 'admin' && (
                  <>
                    <Link onClick={() => setIsOpen(false)} to="/admin/audit-trail"
                      className="block text-amber-400 hover:text-amber-300 font-bold text-sm uppercase tracking-widest transition-colors pl-4">Audit Trail</Link>
                    <Link onClick={() => setIsOpen(false)} to="/admin/qa-monitor"
                      className="block text-amber-400 hover:text-amber-300 font-bold text-sm uppercase tracking-widest transition-colors pl-4">QA Monitor</Link>
                  </>
                )}
              </>
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
