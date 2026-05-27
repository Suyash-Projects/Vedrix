import { useState, useEffect } from 'react';
import {
  Users, Plus, X, Edit2, Trash2,
  RefreshCcw, FileText, User, Lock, Settings, Briefcase,
  Database, Activity, BarChart3, Eye,
  Shield, Mail, Key,
  Brain, Server, Clock, Zap, ExternalLink, Check,
  PlayCircle, Network
} from 'lucide-react';
import { motion } from 'framer-motion';
import apiClient from '../services/api';
import { useNavigate, Link } from 'react-router-dom';

const AdminDashboard = () => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('overview');
  
  const [users, setUsers] = useState([]);
  const [drives, setDrives] = useState([]);
  const [interviews, setInterviews] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [hrUsers, setHrUsers] = useState([]);
  const [stats, setStats] = useState({ 
    total_users: 0, total_sessions: 0, active_users: 0, 
    students: 0, hr_managers: 0, admins: 0, 
    system_status: 'Checking...', version: '' 
  });
  const [loading, setLoading] = useState(false);

  // Create form state
  const [showCreate, setShowCreate] = useState(false);
  const [newUser, setNewUser] = useState({
    email: '',
    username: '',
    password: '',
    first_name: '',
    last_name: '',
    user_type: 'student',
    company_name: '',
  });

  // Edit form state
  const [editingId, setEditingId] = useState(null);
  const [editForm, setEditForm] = useState({
    email: '',
    username: '',
    first_name: '',
    last_name: '',
    user_type: 'student',
  });

  // Drive management state
  const [showDriveModal, setShowDriveModal] = useState(false);
  const [editingDriveId, setEditingDriveId] = useState(null);
  const [driveForm, setDriveForm] = useState({
    title: '',
    job_role: '',
    description: '',
    experience_required: '',
    skills_required: '',
    hr_id: '',
    is_active: true
  });

  // Template management state
  const [showTemplateModal, setShowTemplateModal] = useState(false);
  const [editingTemplateId, setEditingTemplateId] = useState(null);
  const [templateForm, setTemplateForm] = useState({
    title: '',
    type: 'behavioral',
    description: '',
    difficulty_level: 1,
    estimated_time: 30,
    scenarios: '[]' // JSON string for textarea
  });

  // Error / success message
  const [message, setMessage] = useState({ type: '', text: '' });

  const fetchData = async () => {
    try {
      setLoading(true);
      const [usersRes, statsRes, drivesRes, interviewsRes, templatesRes] = await Promise.all([
        apiClient.get('/admin/users'),
        apiClient.get('/admin/stats'),
        apiClient.get('/admin/drives'),
        apiClient.get('/admin/interviews'),
        apiClient.get('/admin/templates'),
      ]);
      setUsers(usersRes.data);
      setStats(statsRes.data);
      setDrives(drivesRes.data);
      setInterviews(Array.isArray(interviewsRes.data) ? interviewsRes.data : (interviewsRes.data?.interviews ?? []));
      setTemplates(templatesRes.data);
      
      // Extract HR users for drive assignment
      setHrUsers(usersRes.data.filter(u => u.user_type === 'hr'));
    } catch {
      setMessage({ type: 'error', text: 'Failed to fetch data' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchData();
  }, []);

  const showMsg = (type, text) => {
    setMessage({ type, text });
    setTimeout(() => setMessage({ type: '', text: '' }), 3000);
  };

  const handleCreateChange = (e) => {
    const { name, value } = e.target;
    setNewUser((prev) => ({ ...prev, [name]: value }));
  };

  const handleCreateUser = async (e) => {
    e.preventDefault();
    try {
      if (!newUser.email || !newUser.username || !newUser.password || !newUser.first_name || !newUser.last_name) {
        showMsg('error', 'All required fields must be filled');
        return;
      }
      const res = await apiClient.post('/admin/users', newUser);
      if (res.status === 201) {
        showMsg('success', `User "${res.data.username}" created`);
        setNewUser({ email: '', username: '', password: '', first_name: '', last_name: '', user_type: 'student', company_name: '' });
        setShowCreate(false);
        await fetchData();
      }
    } catch (err) {
      showMsg('error', err.response?.data?.detail || 'Failed to create user');
    }
  };

  const handleDeleteUser = async (userId, username) => {
    if (!window.confirm(`Delete "${username}"? This is permanent.`)) return;
    try {
      await apiClient.delete(`/admin/users/${userId}`);
      showMsg('success', 'User deleted');
      await fetchData();
    } catch (err) {
      showMsg('error', err.response?.data?.detail || 'Failed to delete');
    }
  };

  const handleDeactivate = async (userId, currentState) => {
    try {
      const endpoint = currentState ? '/deactivate' : '/activate';
      await apiClient.patch(`/admin/users/${userId}${endpoint}`);
      showMsg('success', currentState ? 'Disabled' : 'Activated');
      await fetchData();
    } catch (err) {
      showMsg('error', err.response?.data?.detail || 'Failed');
    }
  };

  const startEdit = (user) => {
    setEditingId(user.id);
    setEditForm({ email: user.email, username: user.username, first_name: user.first_name, last_name: user.last_name, user_type: user.user_type });
  };

  const handleUpdateUser = async (e) => {
    e.preventDefault();
    try {
      if (!editForm.first_name && !editForm.last_name && !editForm.email && !editForm.username) {
        showMsg('error', 'At least one field must be changed');
        return;
      }
      const res = await apiClient.patch(`/admin/users/${editingId}`, editForm);
      if (res.status === 200) {
        showMsg('success', `User ${res.data.username} updated`);
        setEditingId(null);
        await fetchData();
      }
    } catch (err) {
      showMsg('error', err.response?.data?.detail || 'Failed to update');
    }
  };

  const handleChangeRole = async (userId, newRole) => {
    try {
      await apiClient.patch(`/admin/users/${userId}/role`, { role: newRole });
      showMsg('success', `Role changed to ${newRole}`);
      await fetchData();
    } catch (err) {
      showMsg('error', err.response?.data?.detail || 'Failed to change role');
    }
  };

  const handleSendCredentials = async (userId, username) => {
    try {
      await apiClient.post(`/admin/users/${userId}/send-credentials`);
      showMsg('success', `Credentials sent to ${username}`);
    } catch (err) {
      showMsg('error', err.response?.data?.detail || 'Failed to send credentials');
    }
  };

  const handleResetPassword = async (userId, username) => {
    if (!window.confirm(`Reset password for "${username}"? A new password will be generated and sent to their email.`)) return;
    try {
      await apiClient.post(`/admin/users/${userId}/reset-password`);
      showMsg('success', `Password reset for ${username}. New credentials sent to email.`);
    } catch (err) {
      showMsg('error', err.response?.data?.detail || 'Failed to reset password');
    }
  };

  // ── Drive Actions ─────────────────────────────────────────────────────────

  const handleToggleDrive = async (driveId) => {
    try {
      await apiClient.patch(`/admin/drives/${driveId}/toggle`);
      showMsg('success', 'Drive status toggled');
      await fetchData();
    } catch {
      showMsg('error', 'Failed to toggle drive');
    }
  };

  const handleDeleteDrive = async (driveId, title) => {
    if (!window.confirm(`Delete drive "${title}" and all its interviews?`)) return;
    try {
      await apiClient.delete(`/admin/drives/${driveId}`);
      showMsg('success', 'Drive deleted');
      await fetchData();
    } catch {
      showMsg('error', 'Failed to delete drive');
    }
  };

  const openDriveEdit = (drive) => {
    setEditingDriveId(drive.id);
    setDriveForm({
      title: drive.title,
      job_role: drive.job_role,
      description: drive.description || '',
      experience_required: drive.experience_required || '',
      skills_required: drive.skills_required || '',
      hr_id: drive.hr_id,
      is_active: drive.is_active
    });
    setShowDriveModal(true);
  };

  const handleDriveSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingDriveId) {
        await apiClient.patch(`/admin/drives/${editingDriveId}`, driveForm);
        showMsg('success', 'Drive updated');
      } else {
        await apiClient.post(`/admin/drives?hr_id=${driveForm.hr_id}`, driveForm);
        showMsg('success', 'Drive created');
      }
      setShowDriveModal(false);
      setEditingDriveId(null);
      await fetchData();
    } catch (err) {
      showMsg('error', err.response?.data?.detail || 'Failed to save drive');
    }
  };

  // ── Template Actions ──────────────────────────────────────────────────────

  const handleDeleteTemplate = async (templateId, title) => {
    if (!window.confirm(`Delete template "${title}"?`)) return;
    try {
      await apiClient.delete(`/admin/templates/${templateId}`);
      showMsg('success', 'Template deleted');
      await fetchData();
    } catch {
      showMsg('error', 'Failed to delete template');
    }
  };

  const openTemplateEdit = (t) => {
    setEditingTemplateId(t.id);
    setTemplateForm({
      title: t.title,
      type: t.type,
      description: t.description || '',
      difficulty_level: t.difficulty_level,
      estimated_time: t.estimated_time,
      scenarios: JSON.stringify(t.scenarios || [], null, 2)
    });
    setShowTemplateModal(true);
  };

  const handleTemplateSubmit = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        ...templateForm,
        scenarios: JSON.parse(templateForm.scenarios)
      };
      if (editingTemplateId) {
        await apiClient.patch(`/admin/templates/${editingTemplateId}`, payload);
        showMsg('success', 'Template updated');
      } else {
        await apiClient.post('/admin/templates', payload);
        showMsg('success', 'Template created');
      }
      setShowTemplateModal(false);
      setEditingTemplateId(null);
      await fetchData();
    } catch (err) {
      showMsg('error', err.response?.data?.detail || 'Failed to save template. Check JSON syntax.');
    }
  };

  const roleColors = {
    admin: { bg: "bg-red-500/10", text: "text-red-400", border: "border-red-500/20" },
    hr: { bg: "bg-violet-500/10", text: "text-violet-400", border: "border-violet-500/20" },
    student: { bg: "bg-cyan-500/10", text: "text-cyan-400", border: "border-cyan-500/20" },
  };

  const scoreColor = (s) =>
    s >= 8 ? 'text-emerald-400' : s >= 5 ? 'text-purple-400' : 'text-amber-400';

  const statsCards = [
    { label: "Total Users", value: stats.total_users, icon: Users, color: "text-purple-400" },
    { label: "Active", value: stats.active_users, icon: Activity, color: "text-emerald-400" },
    { label: "Total Drives", value: drives.length, icon: Briefcase, color: "text-blue-400" },
    { label: "Total Interviews", value: stats.total_sessions, icon: FileText, color: "text-cyan-400" },
  ];

  const systemCards = [
    { label: "Database Health", value: stats.system_status, icon: Database, color: stats.system_status === "Healthy" ? "text-emerald-400" : "text-red-400" },
    { label: "Students", value: stats.students, icon: User, color: "text-cyan-400" },
    { label: "HR Managers", value: stats.hr_managers, icon: Settings, color: "text-violet-400" },
    { label: "Admins", value: stats.admins, icon: Lock, color: "text-red-400" },
  ];

  return (
    <div className="min-h-screen bg-[#020617] text-white">
      {/* Ambient glow */}
      <div className="fixed top-0 right-0 w-[40%] h-[40%] bg-purple-600/5 blur-[150px] rounded-full pointer-events-none" />
      <div className="fixed bottom-0 left-0 w-[30%] h-[30%] bg-indigo-600/3 blur-[150px] rounded-full pointer-events-none" />
      {/* Subtle grid pattern */}
      <div className="fixed inset-0 bg-grid-pattern pointer-events-none opacity-30" />

      <div className="max-w-7xl mx-auto px-8 py-10 relative z-10">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight">Admin Dashboard</h1>
            <p className="text-slate-500 mt-1">Platform governance, user management, and oversight</p>
          </div>
          <div className="flex items-center space-x-3">
            <button
              onClick={() => navigate('/analytics/team')}
              className="flex items-center space-x-2 bg-emerald-600/10 border border-emerald-500/20 text-emerald-400 px-4 py-2 rounded-xl text-sm font-bold hover:bg-emerald-600/20 transition-all"
            >
              <BarChart3 size={16} />
              <span>Team Analytics</span>
            </button>
            <button
              onClick={() => navigate('/admin/supervisor')}
              className="flex items-center space-x-2 bg-purple-600/10 border border-purple-500/20 text-purple-400 px-4 py-2 rounded-xl text-sm font-bold hover:bg-purple-600/20 transition-all"
            >
              <Brain size={16} />
              <span>AI Supervisor</span>
            </button>
            <button
              onClick={fetchData}
              disabled={loading}
              className="flex items-center space-x-2 bg-white/5 border border-white/10 text-slate-300 px-4 py-2 rounded-xl text-sm font-bold hover:bg-white/10 transition-all disabled:opacity-50"
            >
              <RefreshCcw size={16} className={loading ? 'animate-spin' : ''} />
              <span>Refresh Data</span>
            </button>
            {activeTab === 'users' && (
              <button
                onClick={() => setShowCreate(true)}
                className="flex items-center space-x-2 bg-purple-600 text-white px-4 py-2 rounded-xl text-sm font-bold hover:bg-purple-500 shadow-lg shadow-purple-900/30 transition-all active:scale-95"
              >
                <Plus size={16} />
                <span>New User</span>
              </button>
            )}
            {activeTab === 'drives' && (
              <button
                onClick={() => {
                  setEditingDriveId(null);
                  setDriveForm({ title: '', job_role: '', description: '', experience_required: '', skills_required: '', hr_id: hrUsers[0]?.id || '', is_active: true });
                  setShowDriveModal(true);
                }}
                className="flex items-center space-x-2 bg-purple-600 text-white px-4 py-2 rounded-xl text-sm font-bold hover:bg-purple-500 shadow-lg shadow-purple-900/30 transition-all active:scale-95"
              >
                <Plus size={16} />
                <span>New Drive</span>
              </button>
            )}
            {activeTab === 'templates' && (
              <button
                onClick={() => {
                  setEditingTemplateId(null);
                  setTemplateForm({ title: '', type: 'behavioral', description: '', difficulty_level: 1, estimated_time: 30, scenarios: '[]' });
                  setShowTemplateModal(true);
                }}
                className="flex items-center space-x-2 bg-purple-600 text-white px-4 py-2 rounded-xl text-sm font-bold hover:bg-purple-500 shadow-lg shadow-purple-900/30 transition-all active:scale-95"
              >
                <Plus size={16} />
                <span>New Template</span>
              </button>
            )}
          </div>
        </div>

        {/* Message */}
        {message.text && (
          <div className={`mb-6 p-4 rounded-xl text-sm font-bold border ${message.type === 'success' ? 'bg-green-500/10 border-green-500/20 text-green-400' : 'bg-red-500/10 border-red-500/20 text-red-400'}`}>
            {message.text}
          </div>
        )}

        {/* Navigation Tabs */}
        <div className="flex space-x-2 mb-8 border-b border-white/5 pb-2">
          {['overview', 'users', 'drives', 'interviews', 'templates'].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-5 py-2.5 rounded-t-xl text-sm font-bold uppercase tracking-wider transition-colors border-b-2 ${
                activeTab === tab 
                  ? 'text-purple-400 border-purple-500 bg-white/5' 
                  : 'text-slate-500 border-transparent hover:text-white hover:bg-white/5'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>

        {/* OVERVIEW TAB */}
        {activeTab === 'overview' && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className="space-y-8"
          >
            <div>
              <h2 className="text-xl font-bold mb-4 flex items-center"><BarChart3 className="mr-2 text-purple-400" size={20} /> Platform Statistics</h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {statsCards.map((s, i) => (
                  <motion.div
                    key={s.label}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.05 }}
                    className="glass-card p-6 rounded-2xl flex items-center space-x-4"
                  >
                    <div className="w-12 h-12 bg-white/5 rounded-xl flex items-center justify-center">
                      <s.icon className={s.color} size={24} />
                    </div>
                    <div>
                      <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest">{s.label}</p>
                      <p className="text-2xl font-bold text-white leading-tight">{s.value ?? 0}</p>
                    </div>
                  </motion.div>
                ))}
              </div>
            </div>

            {/* System Health Indicators */}
            <div>
              <h2 className="text-xl font-bold mb-4 flex items-center"><Server className="mr-2 text-purple-400" size={20} /> System Health & Demographics</h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {systemCards.map((s, i) => (
                  <motion.div
                    key={s.label}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.05 + 0.2 }}
                    className="glass-card p-6 rounded-2xl flex items-center space-x-4"
                  >
                    <div className="w-12 h-12 bg-white/5 rounded-xl flex items-center justify-center relative">
                      <s.icon className={s.color} size={24} />
                      {s.label === 'Database Health' && (
                        <span className={`absolute -top-1 -right-1 w-3 h-3 rounded-full border-2 border-[#020617] ${s.value === 'Healthy' ? 'bg-emerald-400 pulse-glow' : 'bg-red-400'}`} />
                      )}
                    </div>
                    <div>
                      <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest">{s.label}</p>
                      <p className={`text-xl font-bold ${s.label === 'Database Health' && s.value === 'Healthy' ? 'text-emerald-400' : 'text-white'} leading-tight`}>{s.value ?? 0}</p>
                    </div>
                  </motion.div>
                ))}
              </div>
            </div>

            {/* Agent Status Grid */}
            <div>
              <h2 className="text-xl font-bold mb-4 flex items-center"><Brain className="mr-2 text-purple-400" size={20} /> AI Agent Status</h2>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                {[
                  { name: 'Interviewer', status: 'active' },
                  { name: 'Evaluator', status: 'active' },
                  { name: 'Skeptic', status: 'active' },
                  { name: 'Pragmatist', status: 'active' },
                  { name: 'Bias Auditor', status: 'active' },
                  { name: 'Empathy', status: 'active' },
                  { name: 'Advisor', status: 'active' },
                  { name: 'Enrichment', status: 'idle' },
                  { name: 'Matching', status: 'idle' },
                  { name: 'Coaching', status: 'idle' },
                ].map((agent) => (
                  <div key={agent.name} className="glass-card rounded-xl p-3 flex items-center space-x-2">
                    <span className={`w-2 h-2 rounded-full shrink-0 ${agent.status === 'active' ? 'bg-emerald-400 pulse-glow' : agent.status === 'idle' ? 'bg-amber-400' : 'bg-red-400'}`} />
                    <span className="text-xs font-bold text-slate-300 truncate">{agent.name}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Quick Links Grid */}
            <div>
              <h2 className="text-xl font-bold mb-4 flex items-center"><Zap className="mr-2 text-purple-400" size={20} /> Quick Links</h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {[
                  { label: 'System Health', to: '/admin/health', icon: Activity, color: 'text-emerald-400' },
                  { label: 'Audit Logs', to: '/admin/audit-logs', icon: FileText, color: 'text-blue-400' },
                  { label: 'AI Supervisor', to: '/admin/supervisor', icon: Brain, color: 'text-purple-400' },
                  { label: 'QA Monitor', to: '/admin/qa-monitor', icon: Eye, color: 'text-amber-400' },
                  { label: 'Audit Trail', to: '/admin/audit-trail', icon: Shield, color: 'text-indigo-400' },
                  { label: 'Team Analytics', to: '/analytics/team', icon: BarChart3, color: 'text-cyan-400' },
                  { label: 'System Config', to: '/admin/config', icon: Settings, color: 'text-slate-400' },
                  { label: 'Manage Users', to: '#', icon: Users, color: 'text-violet-400', action: () => setActiveTab('users') },
                ].map(({ label, to, icon: Icon, color, action }) => (
                  action ? (
                    <button key={label} onClick={action} className="glass-card rounded-xl p-4 flex items-center space-x-3 hover:bg-white/[0.06] transition-all text-left">
                      <Icon size={18} className={color} />
                      <span className="text-sm font-bold text-slate-300">{label}</span>
                    </button>
                  ) : (
                    <Link key={label} to={to} className="glass-card rounded-xl p-4 flex items-center space-x-3 hover:bg-white/[0.06] transition-all">
                      <Icon size={18} className={color} />
                      <span className="text-sm font-bold text-slate-300">{label}</span>
                      <ExternalLink size={12} className="text-slate-600 ml-auto" />
                    </Link>
                  )
                ))}
              </div>
            </div>

            {/* Recent Interviews Preview */}
            {interviews.length > 0 && (
              <div>
                <h2 className="text-xl font-bold mb-4 flex items-center"><Clock className="mr-2 text-purple-400" size={20} /> Recent Interviews</h2>
                <div className="glass-card rounded-2xl overflow-hidden">
                  <table className="w-full text-left">
                    <thead>
                      <tr className="text-[10px] font-black text-slate-500 uppercase tracking-widest border-b border-white/5">
                        <th className="px-6 py-3">Candidate</th>
                        <th className="px-6 py-3">Role</th>
                        <th className="px-6 py-3 text-center">Score</th>
                        <th className="px-6 py-3">Status</th>
                        <th className="px-6 py-3">Date</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                      {interviews.slice(0, 5).map(interview => (
                        <tr key={interview.id} className="hover:bg-white/[0.03] transition-colors">
                          <td className="px-6 py-3 text-sm text-white font-medium">{interview.candidate_name || interview.candidate_email || `#${interview.id}`}</td>
                          <td className="px-6 py-3 text-sm text-slate-400">{interview.job_role || '—'}</td>
                          <td className="px-6 py-3 text-center">
                            <span className={`text-sm font-black ${scoreColor(interview.overall_score || 0)}`}>
                              {interview.overall_score ? interview.overall_score.toFixed(1) : '—'}
                            </span>
                          </td>
                          <td className="px-6 py-3">
                            <span className={`text-[9px] font-black uppercase px-2 py-0.5 rounded-full border ${
                              interview.status === 'completed' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                            }`}>{interview.status}</span>
                          </td>
                          <td className="px-6 py-3 text-xs text-slate-500">{new Date(interview.created_at).toLocaleDateString()}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </motion.div>
        )}

        {/* USERS TAB */}
        {activeTab === 'users' && (
          <div className="bg-white/2 border border-white/5 rounded-3xl overflow-hidden">
            <div className="px-8 py-6 border-b border-white/5 flex justify-between items-center">
              <h2 className="font-bold text-white flex items-center">
                <Users size={18} className="mr-2 text-purple-400" />
                Manage Identities ({users.length})
              </h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead>
                  <tr className="text-[10px] font-black text-slate-500 uppercase tracking-widest border-b border-white/5">
                    <th className="px-8 py-4">User</th>
                    <th className="px-8 py-4">Username</th>
                    <th className="px-8 py-4">Role</th>
                    <th className="px-8 py-4">Email</th>
                    <th className="px-8 py-4">Status</th>
                    <th className="px-8 py-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {users.map((user) => {
                    const rc = roleColors[user.user_type] || roleColors.student;
                    const isEditing = editingId === user.id;

                    return (
                      <tr key={user.id} className="hover:bg-white/[0.03] transition-colors">
                        <td className="px-8 py-5">
                          {isEditing ? (
                            <>
                              <input
                                value={editForm.first_name}
                                onChange={(e) => setEditForm((p) => ({ ...p, first_name: e.target.value }))}
                                className="block w-full bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-sm text-white placeholder-slate-500 focus:ring-1 focus:ring-purple-500 mb-1"
                                placeholder="First name"
                              />
                              <input
                                value={editForm.last_name}
                                onChange={(e) => setEditForm((p) => ({ ...p, last_name: e.target.value }))}
                                className="block w-full bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-sm text-white placeholder-slate-500 focus:ring-1 focus:ring-purple-500"
                                placeholder="Last name"
                              />
                            </>
                          ) : (
                            <div className="flex items-center space-x-3">
                              <div className="w-10 h-10 bg-white/5 rounded-full flex items-center justify-center text-slate-500">
                                <User size={16} />
                              </div>
                              <div>
                                <p className="font-bold text-white text-sm">{user.first_name} {user.last_name}</p>
                                <p className="text-[10px] text-slate-500 font-mono">@{user.username}</p>
                              </div>
                            </div>
                          )}
                        </td>

                        <td className="px-8 py-5">
                          <span className="text-sm font-mono text-slate-400">@{user.username}</span>
                        </td>

                        <td className="px-8 py-5">
                          {isEditing ? (
                            <select
                              value={editForm.user_type}
                              onChange={(e) => setEditForm((p) => ({ ...p, user_type: e.target.value }))}
                              className="bg-white/5 border border-white/10 rounded-lg px-2 py-1.5 text-xs font-bold text-white focus:ring-1 focus:ring-purple-500"
                            >
                              <option value="student">student</option>
                              <option value="hr">hr</option>
                              <option value="admin">admin</option>
                            </select>
                          ) : (
                            <span className={`px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest ${rc.bg} ${rc.text} ${rc.border}`}>
                              {user.user_type}
                            </span>
                          )}
                        </td>

                        <td className="px-8 py-5">
                          {isEditing ? (
                            <input
                              value={editForm.email}
                              type="email"
                              onChange={(e) => setEditForm((p) => ({ ...p, email: e.target.value }))}
                              className="block w-full bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-sm text-white placeholder-slate-500 focus:ring-1 focus:ring-purple-500"
                              placeholder="Email"
                            />
                          ) : (
                            <span className="text-sm font-medium text-slate-400">{user.email}</span>
                          )}
                        </td>

                        <td className="px-8 py-5">
                          {user.is_active ? (
                            <span className="px-2 py-1 rounded-full text-[9px] font-black uppercase bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                              Active
                            </span>
                          ) : (
                            <span className="px-2 py-1 rounded-full text-[9px] font-black uppercase bg-red-500/10 text-red-400 border border-red-500/20">
                              Disabled
                            </span>
                          )}
                        </td>

                        <td className="px-8 py-5 text-right">
                          {isEditing ? (
                            <div className="flex items-center justify-end space-x-2">
                              <button onClick={handleUpdateUser} className="text-emerald-400 hover:bg-emerald-500/10 p-1.5 rounded-lg transition-colors" title="Save"><Check size={16} /></button>
                              <button onClick={() => setEditingId(null)} className="text-slate-500 hover:bg-white/5 p-1.5 rounded-lg transition-colors" title="Cancel"><X size={16} /></button>
                            </div>
                          ) : (
                            <div className="flex items-center justify-end space-x-1">
                              <select
                                value={user.user_type}
                                onChange={(e) => handleChangeRole(user.id, e.target.value)}
                                className="bg-white/5 border border-white/10 rounded px-2 py-1 text-[10px] font-black text-slate-400 hover:text-white focus:ring-1 focus:ring-purple-500 cursor-pointer"
                                title="Change role"
                              >
                                <option value="student">student</option>
                                <option value="hr">hr</option>
                                <option value="admin">admin</option>
                              </select>
                              {!user.is_active ? (
                                <button onClick={() => handleDeactivate(user.id, false)} className="text-slate-500 hover:text-emerald-400 p-1.5 rounded-lg hover:bg-emerald-500/10 transition-colors" title="Activate"><Key size={14} /></button>
                              ) : (
                                <button onClick={() => handleDeactivate(user.id, true)} className="text-slate-500 hover:text-red-400 p-1.5 rounded-lg hover:bg-red-500/10 transition-colors" title="Deactivate"><X size={14} /></button>
                              )}
                              <button onClick={() => startEdit(user)} className="text-slate-500 hover:text-purple-400 p-1.5 rounded-lg hover:bg-purple-500/10 transition-colors" title="Edit"><Edit2 size={14} /></button>
                              {user.user_type !== 'admin' && (
                                <>
                                  <button onClick={() => handleSendCredentials(user.id, user.email)} className="text-slate-500 hover:text-emerald-400 p-1.5 rounded-lg hover:bg-emerald-500/10 transition-colors" title="Send login credentials via email">
                                    <Mail size={14} />
                                  </button>
                                  <button onClick={() => handleResetPassword(user.id, user.username)} className="text-slate-500 hover:text-amber-400 p-1.5 rounded-lg hover:bg-amber-500/10 transition-colors" title="Reset password and send new credentials">
                                    <RefreshCcw size={14} />
                                  </button>
                                  <button onClick={() => handleDeleteUser(user.id, `${user.first_name} ${user.last_name}`)} className="text-slate-600 hover:text-red-400 p-1.5 rounded-lg transition-colors" title="Delete permanently"><Trash2 size={16} /></button>
                                </>
                              )}
                            </div>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* DRIVES TAB */}
        {activeTab === 'drives' && (
          <div className="bg-white/2 border border-white/5 rounded-3xl overflow-hidden">
            <div className="px-8 py-6 border-b border-white/5 flex justify-between items-center">
              <h2 className="font-bold text-white flex items-center">
                <Briefcase size={18} className="mr-2 text-purple-400" />
                All Job Drives ({drives.length})
              </h2>
            </div>
            {drives.length === 0 ? (
              <div className="p-12 text-center text-slate-500">No job drives found in the system.</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left">
                  <thead>
                    <tr className="text-[10px] font-black text-slate-500 uppercase tracking-widest border-b border-white/5">
                      <th className="px-8 py-4">Title / Role</th>
                      <th className="px-8 py-4">HR Manager</th>
                      <th className="px-8 py-4">Status</th>
                      <th className="px-8 py-4 text-center">Sessions</th>
                      <th className="px-8 py-4 text-center">Avg Score</th>
                      <th className="px-8 py-4">Date</th>
                      <th className="px-8 py-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {drives.map((d) => (
                      <tr key={d.id} className="hover:bg-white/[0.03] transition-colors">
                        <td className="px-8 py-5">
                          <p className="font-bold text-white text-sm">{d.title}</p>
                          <p className="text-[10px] text-slate-400">{d.job_role}</p>
                        </td>
                        <td className="px-8 py-5">
                          <p className="font-bold text-white text-xs">{d.hr_name}</p>
                          <p className="text-[10px] text-slate-500">{d.hr_email}</p>
                        </td>
                        <td className="px-8 py-5">
                          {d.is_active ? (
                            <span className="px-2 py-1 rounded-full text-[9px] font-black uppercase bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Active</span>
                          ) : (
                            <span className="px-2 py-1 rounded-full text-[9px] font-black uppercase bg-amber-500/10 text-amber-400 border border-amber-500/20">Closed</span>
                          )}
                        </td>
                        <td className="px-8 py-5 text-center text-slate-300 text-sm font-bold">
                          {d.completed_sessions} / {d.total_sessions}
                        </td>
                        <td className="px-8 py-5 text-center">
                          <span className={`font-black ${d.avg_score ? scoreColor(d.avg_score) : 'text-slate-600'}`}>
                            {d.avg_score ? d.avg_score.toFixed(1) : '—'}
                          </span>
                        </td>
                        <td className="px-8 py-5 text-xs text-slate-400">
                          {new Date(d.created_at).toLocaleDateString()}
                        </td>
                        <td className="px-8 py-5 text-right">
                          <div className="flex items-center justify-end space-x-1">
                            <button
                              onClick={() => handleToggleDrive(d.id)}
                              className={`p-1.5 rounded-lg transition-colors ${d.is_active ? 'text-amber-400 hover:bg-amber-500/10' : 'text-emerald-400 hover:bg-emerald-500/10'}`}
                              title={d.is_active ? 'Close Drive' : 'Open Drive'}
                            >
                              <PlayCircle size={14} className={d.is_active ? 'rotate-90' : ''} />
                            </button>
                            <button
                              onClick={() => openDriveEdit(d)}
                              className="text-slate-500 hover:text-purple-400 p-1.5 rounded-lg hover:bg-purple-500/10 transition-colors"
                              title="Edit Drive"
                            >
                              <Edit2 size={14} />
                            </button>
                            <button
                              onClick={() => handleDeleteDrive(d.id, d.title)}
                              className="text-slate-600 hover:text-red-400 p-1.5 rounded-lg transition-colors"
                              title="Delete Drive"
                            >
                              <Trash2 size={14} />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* INTERVIEWS TAB */}
        {activeTab === 'interviews' && (
          <div className="bg-white/2 border border-white/5 rounded-3xl overflow-hidden">
            <div className="px-8 py-6 border-b border-white/5 flex justify-between items-center">
              <h2 className="font-bold text-white flex items-center">
                <FileText size={18} className="mr-2 text-purple-400" />
                All Interviews ({interviews.length})
              </h2>
            </div>
            {interviews.length === 0 ? (
              <div className="p-12 text-center text-slate-500">No interviews found.</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left">
                  <thead>
                    <tr className="text-[10px] font-black text-slate-500 uppercase tracking-widest border-b border-white/5">
                      <th className="px-8 py-4">ID</th>
                      <th className="px-8 py-4">Candidate ID</th>
                      <th className="px-8 py-4">Status</th>
                      <th className="px-8 py-4 text-center">Score</th>
                      <th className="px-8 py-4">Date</th>
                      <th className="px-8 py-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {interviews.map((session) => (
                      <tr key={session.id} className="hover:bg-white/[0.03] transition-colors">
                        <td className="px-8 py-5 text-sm text-slate-400 font-mono">#{session.id}</td>
                        <td className="px-8 py-5 text-sm text-white font-bold">{session.candidate_id}</td>
                        <td className="px-8 py-5">
                          <span className={`text-[10px] font-black uppercase tracking-widest ${
                            session.status === 'completed' ? 'text-emerald-400' : 'text-amber-400'
                          }`}>
                            {session.status}
                          </span>
                        </td>
                        <td className="px-8 py-5 text-center">
                          <span className={`font-black ${session.overall_score ? scoreColor(session.overall_score) : 'text-slate-600'}`}>
                            {session.overall_score ? session.overall_score.toFixed(1) : '—'}
                          </span>
                        </td>
                        <td className="px-8 py-5 text-xs text-slate-400">
                          {new Date(session.created_at).toLocaleDateString()}
                        </td>
                        <td className="px-8 py-5 text-right">
                          {session.status === 'completed' && (
                            <button
                              onClick={() => navigate(`/report/${session.id}`)}
                              className="text-purple-400 hover:text-purple-300 text-xs font-bold uppercase tracking-widest transition-colors"
                            >
                              View Report
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* TEMPLATES TAB */}
        {activeTab === 'templates' && (
          <div className="bg-white/2 border border-white/5 rounded-3xl overflow-hidden">
            <div className="px-8 py-6 border-b border-white/5 flex justify-between items-center">
              <h2 className="font-bold text-white flex items-center">
                <Network size={18} className="mr-2 text-purple-400" />
                Scenario Templates ({templates.length})
              </h2>
            </div>
            {templates.length === 0 ? (
              <div className="p-12 text-center text-slate-500">No scenario templates found.</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left">
                  <thead>
                    <tr className="text-[10px] font-black text-slate-500 uppercase tracking-widest border-b border-white/5">
                      <th className="px-8 py-4">Title / Type</th>
                      <th className="px-8 py-4">Difficulty</th>
                      <th className="px-8 py-4">Est. Time</th>
                      <th className="px-8 py-4">Scenarios</th>
                      <th className="px-8 py-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {templates.map((t) => (
                      <tr key={t.id} className="hover:bg-white/[0.03] transition-colors">
                        <td className="px-8 py-5">
                          <p className="font-bold text-white text-sm">{t.title}</p>
                          <p className="text-[10px] text-slate-400 uppercase font-black">{t.type}</p>
                        </td>
                        <td className="px-8 py-5">
                          <div className="flex items-center space-x-1">
                            {[1, 2, 3, 4, 5].map(lvl => (
                              <div key={lvl} className={`w-2 h-2 rounded-full ${lvl <= t.difficulty_level ? 'bg-purple-500' : 'bg-white/10'}`} />
                            ))}
                          </div>
                        </td>
                        <td className="px-8 py-5 text-sm text-slate-300 font-bold">{t.estimated_time}m</td>
                        <td className="px-8 py-5 text-xs text-slate-500 font-mono">
                          {t.scenarios?.length || 0} units
                        </td>
                        <td className="px-8 py-5 text-right">
                          <div className="flex items-center justify-end space-x-2">
                            <button
                              onClick={() => openTemplateEdit(t)}
                              className="text-slate-500 hover:text-purple-400 p-1.5 rounded-lg hover:bg-purple-500/10 transition-colors"
                              title="Edit Template"
                            >
                              <Edit2 size={14} />
                            </button>
                            <button
                              onClick={() => handleDeleteTemplate(t.id, t.title)}
                              className="text-slate-600 hover:text-red-400 p-1.5 rounded-lg transition-colors"
                              title="Delete Template"
                            >
                              <Trash2 size={14} />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Create User Modal */}
        {showCreate && (
          <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-[200]">
            <div className="bg-[#0f1420] border border-white/10 rounded-3xl p-8 w-full max-w-md mx-4 shadow-2xl shadow-black/50">
              <div className="flex justify-between items-center mb-6">
                <h3 className="text-xl font-bold text-white">Create New User</h3>
                <button onClick={() => setShowCreate(false)} className="text-slate-500 hover:text-white">
                  <X size={20} />
                </button>
              </div>

              <form onSubmit={handleCreateUser} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500 mb-1.5">
                      <Mail size={12} className="inline mr-1" /> Email
                    </label>
                    <input type="email" name="email" value={newUser.email} onChange={handleCreateChange} required
                      className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-slate-500 focus:ring-1 focus:ring-purple-500 outline-none" placeholder="user@example.com" />
                  </div>
                  <div>
                    <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500 mb-1.5">
                      <Key size={12} className="inline mr-1" /> Username
                    </label>
                    <input type="text" name="username" value={newUser.username} onChange={handleCreateChange} required
                      className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-slate-500 focus:ring-1 focus:ring-purple-500 outline-none" placeholder="johndoe" />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500 mb-1.5">First Name</label>
                    <input type="text" name="first_name" value={newUser.first_name} onChange={handleCreateChange} required
                      className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-slate-500 focus:ring-1 focus:ring-purple-500 outline-none" placeholder="John" />
                  </div>
                  <div>
                    <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500 mb-1.5">Last Name</label>
                    <input type="text" name="last_name" value={newUser.last_name} onChange={handleCreateChange} required
                      className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-slate-500 focus:ring-1 focus:ring-purple-500 outline-none" placeholder="Doe" />
                  </div>
                </div>

                <div>
                  <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500 mb-1.5">Password</label>
                  <input type="password" name="password" value={newUser.password} onChange={handleCreateChange} required
                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-slate-500 focus:ring-1 focus:ring-purple-500 outline-none" placeholder="••••••••" />
                </div>

                <div>
                  <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500 mb-1.5">Role</label>
                  <select name="user_type" value={newUser.user_type} onChange={(e) => {
                      setNewUser((p) => ({ ...p, user_type: e.target.value, company_name: e.target.value === 'hr' ? '' : p.company_name }));
                    }}
                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:ring-1 focus:ring-purple-500 outline-none"
                  >
                    <option value="student">Student</option>
                    <option value="hr">HR Manager</option>
                    <option value="admin">Admin</option>
                  </select>
                </div>

                {newUser.user_type === 'hr' && (
                  <div>
                    <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500 mb-1.5">Company Name</label>
                    <input type="text" name="company_name" value={newUser.company_name} onChange={handleCreateChange} placeholder="e.g. Google, Microsoft"
                      className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-slate-500 focus:ring-1 focus:ring-purple-500 outline-none" />
                  </div>
                )}

                <div className="flex justify-end space-x-3 pt-2">
                  <button type="button" onClick={() => setShowCreate(false)} className="px-6 py-3 bg-white/5 hover:bg-white/10 text-slate-400 rounded-xl text-sm font-bold transition-all">Cancel</button>
                  <button type="submit" className="px-6 py-3 bg-purple-600 hover:bg-purple-500 text-white rounded-xl text-sm font-bold shadow-lg shadow-purple-900/30 transition-all active:scale-95">Create Account</button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Drive Create/Edit Modal */}
        {showDriveModal && (
          <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-[200]">
            <div className="bg-[#0f1420] border border-white/10 rounded-3xl p-8 w-full max-w-lg mx-4 shadow-2xl overflow-y-auto max-h-[90vh]">
              <div className="flex justify-between items-center mb-6">
                <h3 className="text-xl font-bold text-white">{editingDriveId ? 'Edit Job Drive' : 'Create New Job Drive'}</h3>
                <button onClick={() => setShowDriveModal(false)} className="text-slate-500 hover:text-white"><X size={20} /></button>
              </div>

              <form onSubmit={handleDriveSubmit} className="space-y-4">
                <div>
                  <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500 mb-1.5">Drive Title</label>
                  <input type="text" value={driveForm.title} onChange={e => setDriveForm({...driveForm, title: e.target.value})} required
                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:ring-1 focus:ring-purple-500 outline-none" placeholder="e.g. Software Engineer - Python" />
                </div>
                <div>
                  <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500 mb-1.5">Job Role</label>
                  <input type="text" value={driveForm.job_role} onChange={e => setDriveForm({...driveForm, job_role: e.target.value})} required
                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:ring-1 focus:ring-purple-500 outline-none" placeholder="e.g. Senior Backend Developer" />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500 mb-1.5">Experience</label>
                    <input type="text" value={driveForm.experience_required} onChange={e => setDriveForm({...driveForm, experience_required: e.target.value})}
                      className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:ring-1 focus:ring-purple-500 outline-none" placeholder="e.g. 3+ years" />
                  </div>
                  <div>
                    <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500 mb-1.5">Assign to HR</label>
                    <select value={driveForm.hr_id} onChange={e => setDriveForm({...driveForm, hr_id: e.target.value})} required
                      className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:ring-1 focus:ring-purple-500 outline-none">
                      {hrUsers.map(hr => (
                        <option key={hr.id} value={hr.id}>{hr.first_name} {hr.last_name} (@{hr.username})</option>
                      ))}
                    </select>
                  </div>
                </div>
                <div>
                  <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500 mb-1.5">Skills Required (Comma separated)</label>
                  <input type="text" value={driveForm.skills_required} onChange={e => setDriveForm({...driveForm, skills_required: e.target.value})}
                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:ring-1 focus:ring-purple-500 outline-none" placeholder="Python, Django, PostgreSQL" />
                </div>
                <div>
                  <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500 mb-1.5">Description</label>
                  <textarea value={driveForm.description} onChange={e => setDriveForm({...driveForm, description: e.target.value})} rows={3}
                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:ring-1 focus:ring-purple-500 outline-none" placeholder="Job description..." />
                </div>
                <div className="flex justify-end space-x-3 pt-4">
                  <button type="button" onClick={() => setShowDriveModal(false)} className="px-6 py-3 bg-white/5 text-slate-400 rounded-xl text-sm font-bold transition-all">Cancel</button>
                  <button type="submit" className="px-6 py-3 bg-purple-600 text-white rounded-xl text-sm font-bold shadow-lg shadow-purple-900/30 transition-all active:scale-95">
                    {editingDriveId ? 'Update Drive' : 'Create Drive'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Template Create/Edit Modal */}
        {showTemplateModal && (
          <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-[200]">
            <div className="bg-[#0f1420] border border-white/10 rounded-3xl p-8 w-full max-w-2xl mx-4 shadow-2xl overflow-y-auto max-h-[90vh]">
              <div className="flex justify-between items-center mb-6">
                <h3 className="text-xl font-bold text-white">{editingTemplateId ? 'Edit Template' : 'Create New Template'}</h3>
                <button onClick={() => setShowTemplateModal(false)} className="text-slate-500 hover:text-white"><X size={20} /></button>
              </div>

              <form onSubmit={handleTemplateSubmit} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500 mb-1.5">Title</label>
                    <input type="text" value={templateForm.title} onChange={e => setTemplateForm({...templateForm, title: e.target.value})} required
                      className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:ring-1 focus:ring-purple-500 outline-none" placeholder="e.g. Python Core Concepts" />
                  </div>
                  <div>
                    <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500 mb-1.5">Type</label>
                    <select value={templateForm.type} onChange={e => setTemplateForm({...templateForm, type: e.target.value})} required
                      className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:ring-1 focus:ring-purple-500 outline-none">
                      <option value="coding">Coding</option>
                      <option value="behavioral">Behavioral</option>
                      <option value="system_design">System Design</option>
                    </select>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500 mb-1.5">Difficulty (1-5)</label>
                    <input type="number" min="1" max="5" value={templateForm.difficulty_level} onChange={e => setTemplateForm({...templateForm, difficulty_level: parseInt(e.target.value)})}
                      className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:ring-1 focus:ring-purple-500 outline-none" />
                  </div>
                  <div>
                    <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500 mb-1.5">Est. Time (min)</label>
                    <input type="number" value={templateForm.estimated_time} onChange={e => setTemplateForm({...templateForm, estimated_time: parseInt(e.target.value)})}
                      className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:ring-1 focus:ring-purple-500 outline-none" />
                  </div>
                </div>
                <div>
                  <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500 mb-1.5">Description</label>
                  <input type="text" value={templateForm.description} onChange={e => setTemplateForm({...templateForm, description: e.target.value})}
                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:ring-1 focus:ring-purple-500 outline-none" placeholder="Brief overview..." />
                </div>
                <div>
                  <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500 mb-1.5">Scenario Units (JSON Array)</label>
                  <p className="text-[9px] text-slate-500 mb-2 font-mono">Example: [{"{ \"topic\": \"decorators\", \"count\": 2 }"}]</p>
                  <textarea value={templateForm.scenarios} onChange={e => setTemplateForm({...templateForm, scenarios: e.target.value})} rows={5}
                    className="w-full bg-[#050810] border border-white/10 rounded-xl px-4 py-3 text-xs text-indigo-300 font-mono focus:ring-1 focus:ring-purple-500 outline-none" />
                </div>
                <div className="flex justify-end space-x-3 pt-4">
                  <button type="button" onClick={() => setShowTemplateModal(false)} className="px-6 py-3 bg-white/5 text-slate-400 rounded-xl text-sm font-bold transition-all">Cancel</button>
                  <button type="submit" className="px-6 py-3 bg-purple-600 text-white rounded-xl text-sm font-bold shadow-lg shadow-purple-900/30 transition-all active:scale-95">
                    {editingTemplateId ? 'Update Template' : 'Create Template'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AdminDashboard;
