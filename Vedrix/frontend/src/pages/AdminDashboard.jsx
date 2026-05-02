import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { 
  Users, 
  Settings, 
  Trash2, 
  ShieldAlert, 
  Database, 
  Server, 
  RefreshCcw,
  Activity,
  History,
  Lock
} from 'lucide-react';
import apiClient from '../services/api';
import useAuthStore from '../store/useAuthStore';

const AdminDashboard = () => {
  const [users, setUsers] = useState([]);
  const [stats, setStats] = useState({ total_users: 0, total_sessions: 0, system_status: 'Checking...' });
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    try {
      const [usersRes, statsRes] = await Promise.all([
        apiClient.get('/admin/users'),
        apiClient.get('/admin/stats')
      ]);
      setUsers(usersRes.data);
      setStats(statsRes.data);
    } catch (err) {
      console.error("Admin fetch error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleDeleteUser = async (userId) => {
    if (!window.confirm("Are you sure you want to delete this user? This action is permanent.")) return;
    try {
      await apiClient.delete(`/admin/users/${userId}`);
      setUsers(users.filter(u => u.id !== userId));
    } catch (err) {
      alert("Failed to delete user");
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex">
      {/* Sidebar */}
      <div className="w-64 bg-slate-900 text-white p-8 space-y-10 hidden md:block">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 bg-purple-500 rounded-lg flex items-center justify-center">
            <Lock size={18} />
          </div>
          <span className="text-lg font-bold tracking-tight">Vedrix <span className="text-purple-400">Admin</span></span>
        </div>

        <nav className="space-y-4">
          {[
            { label: 'Overview', icon: Activity, active: true },
            { label: 'User Management', icon: Users },
            { label: 'Session Logs', icon: History },
            { label: 'Infrastructure', icon: Server },
            { label: 'System Settings', icon: Settings },
          ].map(item => (
            <button 
              key={item.label}
              className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl transition-all ${item.active ? 'bg-purple-600 text-white shadow-lg shadow-purple-900/20' : 'text-slate-400 hover:text-white hover:bg-white/5'}`}
            >
              <item.icon size={18} />
              <span className="text-sm font-semibold">{item.label}</span>
            </button>
          ))}
        </nav>
      </div>

      {/* Main Content */}
      <div className="flex-1 p-10 overflow-y-auto">
        <header className="flex justify-between items-center mb-10">
          <div>
            <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">Command Center</h1>
            <p className="text-slate-500 mt-1">System-wide governance and resource management</p>
          </div>
          <button 
            onClick={fetchData}
            className="flex items-center space-x-2 bg-white border border-slate-200 text-slate-700 px-4 py-2 rounded-xl text-sm font-bold hover:bg-slate-100 transition-all shadow-sm"
          >
            <RefreshCcw size={16} />
            <span>Sync Data</span>
          </button>
        </header>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
          {[
            { label: 'Global Users', value: stats.total_users, icon: Users, color: 'text-purple-600' },
            { label: 'Interview Load', value: stats.total_sessions, icon: Database, color: 'text-blue-600' },
            { label: 'Server Status', value: stats.system_status, icon: Activity, color: 'text-green-600' },
          ].map(s => (
            <div key={s.label} className="bg-white p-6 rounded-3xl border border-slate-100 shadow-sm flex items-center space-x-4">
              <div className="w-12 h-12 bg-slate-50 rounded-2xl flex items-center justify-center">
                <s.icon className={s.color} size={24} />
              </div>
              <div>
                <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">{s.label}</p>
                <p className="text-2xl font-bold text-slate-900 leading-tight">{s.value}</p>
              </div>
            </div>
          ))}
        </div>

        {/* User Table */}
        <div className="bg-white rounded-3xl border border-slate-100 shadow-xl overflow-hidden">
          <div className="px-8 py-6 border-b border-slate-50 flex justify-between items-center bg-slate-50/50">
            <h2 className="font-bold text-slate-800 flex items-center">
              <Users size={18} className="mr-2 text-purple-600" />
              Registered Identities
            </h2>
            <span className="text-[10px] font-black text-slate-400 uppercase">{users.length} Total</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="text-[10px] font-black text-slate-400 uppercase tracking-widest border-b border-slate-50">
                  <th className="px-8 py-4">User</th>
                  <th className="px-8 py-4">Role</th>
                  <th className="px-8 py-4">Email</th>
                  <th className="px-8 py-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {users.map(user => (
                  <tr key={user.id} className="hover:bg-slate-50/80 transition-colors group">
                    <td className="px-8 py-5">
                      <div className="flex items-center space-x-3">
                        <div className="w-10 h-10 bg-slate-100 rounded-full flex items-center justify-center text-slate-400">
                          <User size={20} />
                        </div>
                        <div>
                          <p className="font-bold text-slate-900 text-sm">{user.first_name} {user.last_name}</p>
                          <p className="text-xs text-slate-500 font-mono italic">@{user.username}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-8 py-5 text-sm">
                      <span className={`px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest ${
                        user.user_type === 'admin' ? 'bg-red-50 text-red-600' : 
                        user.user_type === 'hr' ? 'bg-indigo-50 text-indigo-600' : 'bg-green-50 text-green-600'
                      }`}>
                        {user.user_type}
                      </span>
                    </td>
                    <td className="px-8 py-5 text-sm font-medium text-slate-600">{user.email}</td>
                    <td className="px-8 py-5 text-right">
                      <button 
                        onClick={() => handleDeleteUser(user.id)}
                        disabled={user.user_type === 'admin'}
                        className="text-slate-300 hover:text-red-600 transition-colors disabled:opacity-0"
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
