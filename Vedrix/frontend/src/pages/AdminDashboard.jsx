import { useState, useEffect } from 'react';
import { 
  Users, 
  Settings, 
  Trash2, 
  Database, 
  Server, 
  RefreshCcw,
  Activity,
  History,
  Lock,
  User
} from 'lucide-react';
import apiClient from '../services/api';

const AdminDashboard = () => {
  const [users, setUsers] = useState([]);
  const [stats, setStats] = useState({ total_users: 0, total_sessions: 0, system_status: 'Checking...' });

  const fetchData = async () => {
    try {
      const [usersRes, statsRes] = await Promise.all([
        apiClient.get('/admin/users'),
        apiClient.get('/admin/stats')
      ]);
      setUsers(usersRes.data);
      setStats(statsRes.data);
    } catch {
      console.error("Admin fetch error");
    }
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchData();
  }, []);

  const handleDeleteUser = async (userId) => {
    if (!window.confirm("Are you sure you want to delete this user? This action is permanent.")) return;
    try {
      await apiClient.delete(`/admin/users/${userId}`);
      setUsers(users.filter(u => u.id !== userId));
    } catch {
      alert("Failed to delete user");
    }
  };

  return (
    <div className="min-h-screen bg-[#020617] flex">
      {/* Sidebar */}
      <div className="w-64 bg-[#0a0f1e] border-r border-white/5 p-8 space-y-10 hidden md:block">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 bg-gradient-to-tr from-purple-600 to-indigo-400 rounded-lg flex items-center justify-center">
            <Lock size={16} className="text-white" />
          </div>
          <span className="text-lg font-bold tracking-tight text-white">Vedrix <span className="text-purple-400">Admin</span></span>
        </div>

        <nav className="space-y-2">
          {[
            { label: 'Overview', icon: Activity, active: true },
            { label: 'User Management', icon: Users },
            { label: 'Session Logs', icon: History },
            { label: 'Infrastructure', icon: Server },
            { label: 'System Settings', icon: Settings },
          ].map(item => (
            <button 
              key={item.label}
              className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl transition-all text-sm font-bold ${
                item.active ? 'bg-purple-600/10 text-purple-400 border border-purple-500/20' : 'text-slate-500 hover:text-white hover:bg-white/5'
              }`}
            >
              <item.icon size={18} />
              <span>{item.label}</span>
            </button>
          ))}
        </nav>
      </div>

      {/* Main Content */}
      <div className="flex-1 p-10 overflow-y-auto">
        <header className="flex justify-between items-center mb-10">
          <div>
            <h1 className="text-3xl font-extrabold text-white tracking-tight">Command Center</h1>
            <p className="text-slate-500 mt-1">System-wide governance and resource management</p>
          </div>
          <button 
            onClick={fetchData}
            className="flex items-center space-x-2 bg-white/5 border border-white/10 text-slate-300 px-4 py-2 rounded-xl text-sm font-bold hover:bg-white/10 transition-all"
          >
            <RefreshCcw size={16} />
            <span>Sync Data</span>
          </button>
        </header>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
          {[
            { label: 'Global Users', value: stats.total_users, icon: Users, color: 'text-purple-400' },
            { label: 'Interview Load', value: stats.total_sessions, icon: Database, color: 'text-blue-400' },
            { label: 'Server Status', value: stats.system_status, icon: Activity, color: 'text-emerald-400' },
          ].map(s => (
            <div key={s.label} className="bg-white/2 border border-white/5 p-6 rounded-3xl flex items-center space-x-4">
              <div className="w-12 h-12 bg-white/5 rounded-2xl flex items-center justify-center">
                <s.icon className={s.color} size={24} />
              </div>
              <div>
                <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest">{s.label}</p>
                <p className="text-2xl font-bold text-white leading-tight">{s.value}</p>
              </div>
            </div>
          ))}
        </div>

        {/* User Table */}
        <div className="bg-white/2 border border-white/5 rounded-3xl overflow-hidden">
          <div className="px-8 py-6 border-b border-white/5 flex justify-between items-center">
            <h2 className="font-bold text-white flex items-center">
              <Users size={18} className="mr-2 text-purple-400" />
              Registered Identities
            </h2>
            <span className="text-[10px] font-black text-slate-500 uppercase">{users.length} Total</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="text-[10px] font-black text-slate-500 uppercase tracking-widest border-b border-white/5">
                  <th className="px-8 py-4">User</th>
                  <th className="px-8 py-4">Role</th>
                  <th className="px-8 py-4">Email</th>
                  <th className="px-8 py-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {users.map(user => (
                  <tr key={user.id} className="hover:bg-white/2 transition-colors group">
                    <td className="px-8 py-5">
                      <div className="flex items-center space-x-3">
                        <div className="w-10 h-10 bg-white/5 rounded-full flex items-center justify-center text-slate-500">
                          <User size={18} />
                        </div>
                        <div>
                          <p className="font-bold text-white text-sm">{user.first_name} {user.last_name}</p>
                          <p className="text-xs text-slate-500 font-mono italic">@{user.username}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-8 py-5">
                      <span className={`px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest ${
                        user.user_type === 'admin' ? 'bg-red-500/10 text-red-400 border border-red-500/20' : 
                        user.user_type === 'hr' ? 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20' : 
                        'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                      }`}>
                        {user.user_type}
                      </span>
                    </td>
                    <td className="px-8 py-5 text-sm font-medium text-slate-400">{user.email}</td>
                    <td className="px-8 py-5 text-right">
                      <button 
                        onClick={() => handleDeleteUser(user.id)}
                        disabled={user.user_type === 'admin'}
                        className="text-slate-600 hover:text-red-400 transition-colors disabled:opacity-0"
                      >
                        <Trash2 size={18} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminDashboard;
