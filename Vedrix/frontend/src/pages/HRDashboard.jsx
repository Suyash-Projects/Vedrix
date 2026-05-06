import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Briefcase, Plus, Link as LinkIcon, Activity,
  ChevronRight, Copy, CheckCircle2, Clock, LayoutDashboard,
  LogOut, Settings, MoreVertical, X, Loader2, Mail, Send,
  ChevronDown, Radio, MessageSquareText
} from 'lucide-react';
import apiClient from '../services/api';
import useAuthStore from '../store/useAuthStore';
import SkillMatrixTab from '../components/SkillMatrixTab';

/* ── CREATE DRIVE MODAL ── */
const CreateDriveModal = ({ onClose, onCreated }) => {
  const [formData, setFormData] = useState({ title: '', job_role: '', description: '', skills_required: '' });
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await apiClient.post('/hr/drives', formData);
      onCreated();
      onClose();
    } catch {
      alert('Failed to create drive');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[200] flex items-center justify-center p-6">
      <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
        className="bg-[#0f172a] border border-white/10 rounded-[2rem] w-full max-w-xl overflow-hidden shadow-2xl">
        <div className="px-8 py-6 border-b border-white/5 flex justify-between items-center">
          <h2 className="text-xl font-bold text-white">New Recruitment Drive</h2>
          <button onClick={onClose} className="text-slate-500 hover:text-white transition-colors"><X size={20} /></button>
        </div>
        <form onSubmit={handleSubmit} className="p-8 space-y-5">
          {[
            { label: 'Drive Title', key: 'title', placeholder: 'e.g. Summer Internship 2026' },
            { label: 'Target Job Role', key: 'job_role', placeholder: 'e.g. Senior Backend Engineer' },
            { label: 'Required Skills (comma separated)', key: 'skills_required', placeholder: 'FastAPI, React, SQLModel' },
          ].map(({ label, key, placeholder }) => (
            <div key={key}>
              <label className="block text-xs font-black uppercase text-slate-400 tracking-widest mb-1.5 ml-1">{label}</label>
              <input required={key !== 'skills_required'}
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none transition-all"
                placeholder={placeholder}
                onChange={(e) => setFormData({ ...formData, [key]: e.target.value })}
              />
            </div>
          ))}
          <button type="submit" disabled={loading}
            className="w-full bg-purple-600 text-white py-4 rounded-2xl font-bold hover:bg-purple-500 shadow-xl shadow-purple-900/30 transition-all flex items-center justify-center">
            {loading ? <Loader2 className="animate-spin" size={20} /> : <span>Initialize Drive</span>}
          </button>
        </form>
      </motion.div>
    </div>
  );
};

/* ── BULK INVITE MODAL ── */
const BulkInviteModal = ({ drive, onClose }) => {
  const [emailInput, setEmailInput] = useState('');
  const [expiryHours, setExpiryHours] = useState(72);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const emails = emailInput.split(/[\n,]+/).map(e => e.trim()).filter(Boolean);
    if (!emails.length) return alert('Enter at least one email.');
    setLoading(true);
    try {
      const res = await apiClient.post(`/hr/drives/${drive.id}/bulk-invite`, {
        emails,
        expires_in_hours: expiryHours
      });
      setResult(res.data);
    } catch {
      alert('Failed to send invites');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[200] flex items-center justify-center p-6">
      <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
        className="bg-[#0f172a] border border-white/10 rounded-[2rem] w-full max-w-xl overflow-hidden shadow-2xl">
        <div className="px-8 py-6 border-b border-white/5 flex justify-between items-center">
          <div>
            <h2 className="text-xl font-bold text-white">Bulk Schedule Candidates</h2>
            <p className="text-xs text-slate-500 font-bold uppercase tracking-widest mt-0.5">{drive.title}</p>
          </div>
          <button onClick={onClose} className="text-slate-500 hover:text-white transition-colors"><X size={20} /></button>
        </div>

        {result ? (
          <div className="p-8 space-y-6">
            <div className="flex items-center space-x-3 text-emerald-400">
              <CheckCircle2 size={28} />
              <div>
                <p className="font-black text-lg text-white">{result.invited} Invites Generated</p>
                <p className="text-xs text-slate-500 uppercase tracking-widest font-bold">Invitation links are ready to share</p>
              </div>
            </div>
            <div className="space-y-3 max-h-64 overflow-y-auto pr-1">
              {result.links.map((l, i) => (
                <div key={i} className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 flex items-center justify-between gap-3">
                  <p className="text-xs text-slate-400 font-mono truncate flex-1">{l.link}</p>
                  <button onClick={() => navigator.clipboard.writeText(l.link)}
                    className="text-purple-400 hover:text-purple-300 shrink-0"><Copy size={14} /></button>
                </div>
              ))}
            </div>
            <button onClick={onClose}
              className="w-full bg-white/5 border border-white/10 text-white py-3 rounded-2xl font-bold hover:bg-white/10 transition-all">
              Done
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="p-8 space-y-5">
            <div>
              <label className="block text-xs font-black uppercase text-slate-400 tracking-widest mb-1.5 ml-1">
                Candidate Emails <span className="text-slate-600">(one per line or comma-separated)</span>
              </label>
              <textarea rows={5} value={emailInput} onChange={e => setEmailInput(e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none transition-all resize-none font-mono text-sm"
                placeholder={"alice@example.com\nbob@example.com\ncharlie@example.com"} />
            </div>
            <div>
              <label className="block text-xs font-black uppercase text-slate-400 tracking-widest mb-1.5 ml-1">
                Link Expiry
              </label>
              <div className="relative">
                <select value={expiryHours} onChange={e => setExpiryHours(Number(e.target.value))}
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white focus:ring-2 focus:ring-purple-500 outline-none appearance-none">
                  <option value={24} className="bg-slate-900">24 hours</option>
                  <option value={48} className="bg-slate-900">48 hours</option>
                  <option value={72} className="bg-slate-900">72 hours (default)</option>
                  <option value={168} className="bg-slate-900">7 days</option>
                </select>
                <ChevronDown size={16} className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none" />
              </div>
            </div>
            <button type="submit" disabled={loading}
              className="w-full bg-purple-600 text-white py-4 rounded-2xl font-bold hover:bg-purple-500 shadow-xl shadow-purple-900/30 transition-all flex items-center justify-center space-x-2">
              {loading ? <Loader2 className="animate-spin" size={20} /> : <><Send size={18} /><span>Send Invites</span></>}
            </button>
          </form>
        )}
      </motion.div>
    </div>
  );
};

/* ── TAKEOVER MODAL ── */
const TakeoverModal = ({ session, onClose }) => {
  const [instruction, setInstruction] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSend = async () => {
    if (!instruction.trim()) return;
    setLoading(true);
    try {
      await apiClient.post(`/interview/sessions/${session.id}/hr-instruction`, {
        text: instruction
      });
      setInstruction('');
      alert("Instruction sent to AI engine!");
      onClose();
    } catch {
      alert("Failed to send instruction.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[200] flex items-center justify-center p-6">
      <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
        className="bg-[#0f172a] border border-white/10 rounded-[2rem] w-full max-w-xl overflow-hidden shadow-2xl">
        <div className="px-8 py-6 border-b border-white/5 flex justify-between items-center">
          <div>
            <h2 className="text-xl font-bold text-white">Reviewer Guidance</h2>
            <p className="text-xs text-slate-500 font-bold uppercase tracking-widest mt-0.5">Session #{session.id}</p>
          </div>
          <button onClick={onClose} className="text-slate-500 hover:text-white transition-colors"><X size={20} /></button>
        </div>
        <div className="p-8 space-y-5">
          <p className="text-sm text-slate-400">
            Send a private note to guide the next follow-up question or steer the interview toward a topic you want reviewed.
          </p>
          <textarea rows={4} value={instruction} onChange={e => setInstruction(e.target.value)}
            className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none transition-all resize-none"
            placeholder="e.g. Ask the candidate to explain their experience with React Hooks in more depth." />
          <button onClick={handleSend} disabled={loading || !instruction.trim()}
            className="w-full bg-red-600 text-white py-4 rounded-2xl font-bold hover:bg-red-500 shadow-xl shadow-red-900/30 transition-all flex items-center justify-center space-x-2">
            {loading ? <Loader2 className="animate-spin" size={20} /> : <><MessageSquareText size={18} /><span>Send Guidance</span></>}
          </button>
        </div>
      </motion.div>
    </div>
  );
};

/* ── DRIVE SETTINGS TAB ── */
const DriveSettingsTab = () => {
  const [profile, setProfile] = useState({ company_name: '', department: '', position: '' });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    apiClient.get('/hr/profile')
      .then(r => setProfile({ company_name: r.data.company_name || '', department: r.data.department || '', position: r.data.position || '' }))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await apiClient.put('/hr/profile', profile);
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } catch { alert('Failed to save profile.'); }
    finally { setSaving(false); }
  };

  if (loading) return <div className="flex justify-center py-20"><Loader2 className="animate-spin text-purple-500" size={36} /></div>;

  return (
    <div className="max-w-xl">
      <h2 className="text-2xl font-black text-white mb-2">HR Profile Settings</h2>
      <p className="text-slate-500 mb-8 text-sm">Update your company and role information.</p>
      <form onSubmit={handleSave} className="space-y-5">
        {[
          { label: 'Company Name', key: 'company_name', placeholder: 'e.g. Acme Corp' },
          { label: 'Department', key: 'department', placeholder: 'e.g. Engineering' },
          { label: 'Your Position', key: 'position', placeholder: 'e.g. Senior Recruiter' },
        ].map(({ label, key, placeholder }) => (
          <div key={key}>
            <label className="block text-xs font-black uppercase text-slate-400 tracking-widest mb-1.5 ml-1">{label}</label>
            <input
              className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none transition-all"
              placeholder={placeholder}
              value={profile[key]}
              onChange={e => setProfile({ ...profile, [key]: e.target.value })}
            />
          </div>
        ))}
        <button type="submit" disabled={saving}
          className={`flex items-center space-x-2 px-8 py-4 rounded-2xl font-bold text-sm transition-all ${
            saved ? 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-400' : 'bg-purple-600 text-white hover:bg-purple-500 shadow-xl shadow-purple-900/30'
          } disabled:opacity-50`}>
          {saving ? <Loader2 className="animate-spin" size={16} /> : saved ? <CheckCircle2 size={16} /> : null}
          <span>{saving ? 'Saving...' : saved ? 'Saved!' : 'Save Changes'}</span>
        </button>
      </form>
    </div>
  );
};

/* ── MAIN HR DASHBOARD ── */
const HRDashboard = () => {
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();
  const [drives, setDrives] = useState([]);
  const [interviews, setInterviews] = useState([]);
  const [liveSessions, setLiveSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [profileCompletion, setProfileCompletion] = useState(0);
  const [activeTab, setActiveTab] = useState('Active Drives');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [bulkInviteDrive, setBulkInviteDrive] = useState(null);
  const [takeoverSession, setTakeoverSession] = useState(null);
  const [copiedId, setCopiedId] = useState(null);

  const handleViewReport = (sessionId) => {
    navigate(`/report/${sessionId}`);
  };

  const fetchData = async () => {
    setLoading(true);
    try {
      const [drivesRes, interviewsRes] = await Promise.all([
        apiClient.get('/hr/drives'),
        apiClient.get('/hr/interviews')
      ]);
      setDrives(drivesRes.data);
      setInterviews(interviewsRes.data.filter(i => i.status === 'completed'));
      setLiveSessions(interviewsRes.data.filter(i => i.status === 'in_progress'));
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // Preflight HR profile check
  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const res = await apiClient.get('/hr/profile-check');
        if (mounted) {
          setProfileCompletion(res.data?.completion ?? 0);
        }
      } catch {
        if (mounted) {
          setProfileCompletion(0);
        }
      }
    })();
    return () => { mounted = false };
  }, []);

  useEffect(() => { 
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchData(); 
    // Basic polling for live sessions could be added here
    const interval = setInterval(fetchData, 15000);
    return () => clearInterval(interval);
  }, []);

  const handleGenerateLink = async (driveId) => {
    try {
      const res = await apiClient.post(`/hr/drives/${driveId}/magic-link`, {});
      await navigator.clipboard.writeText(res.data.link);
      setCopiedId(driveId);
      setTimeout(() => setCopiedId(null), 2000);
    } catch {
      alert('Failed to generate link');
    }
  };

  const [sortConfig, setSortConfig] = useState({ key: 'overall_score', direction: 'desc' });

  const sortedInterviews = React.useMemo(() => {
    let sortableInterviews = [...interviews];
    sortableInterviews.sort((a, b) => {
      let aValue = a[sortConfig.key];
      let bValue = b[sortConfig.key];
      
      if (['technical_accuracy', 'communication_clarity', 'depth_of_knowledge'].includes(sortConfig.key)) {
        aValue = a.ai_feedback?.[sortConfig.key] || 0;
        bValue = b.ai_feedback?.[sortConfig.key] || 0;
      }
      
      if (aValue < bValue) return sortConfig.direction === 'asc' ? -1 : 1;
      if (aValue > bValue) return sortConfig.direction === 'asc' ? 1 : -1;
      return 0;
    });
    return sortableInterviews;
  }, [interviews, sortConfig]);

  const requestSort = (key) => {
    let direction = 'desc';
    if (sortConfig.key === key && sortConfig.direction === 'desc') {
      direction = 'asc';
    }
    setSortConfig({ key, direction });
  };

  return (
    <div className="min-h-screen bg-[#020617] flex font-sans">
      <AnimatePresence>
        {showCreateModal && <CreateDriveModal onClose={() => setShowCreateModal(false)} onCreated={fetchData} />}
        {bulkInviteDrive && <BulkInviteModal drive={bulkInviteDrive} onClose={() => setBulkInviteDrive(null)} />}
        {takeoverSession && <TakeoverModal session={takeoverSession} onClose={() => setTakeoverSession(null)} />}
      </AnimatePresence>

      {/* Sidebar */}
      <div className="w-72 bg-[#0a0f1e] border-r border-white/5 p-8 flex-col space-y-10 hidden lg:flex">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-gradient-to-tr from-purple-600 to-indigo-400 rounded-xl flex items-center justify-center text-white shadow-lg shadow-purple-900/30">
            <Briefcase size={20} />
          </div>
          <span className="text-xl font-bold tracking-tight text-white">Vedrix <span className="text-purple-400">HR</span></span>
        </div>

        <nav className="flex-1 space-y-2">
          {[
            { label: 'Active Drives', icon: LayoutDashboard },
            { label: 'Live Monitoring', icon: Radio },
            { label: 'Evaluation Reports', icon: Activity },
            { label: 'Skill Matrix', icon: Briefcase },
            { label: 'Drive Settings', icon: Settings },
          ].map(item => (
            <button key={item.label}
              onClick={() => setActiveTab(item.label)}
              className={`w-full flex items-center space-x-3 px-5 py-4 rounded-2xl transition-all text-sm font-bold ${
                activeTab === item.label ? 'bg-purple-600/10 text-purple-400 border border-purple-500/20' : 'text-slate-500 hover:text-white hover:bg-white/5'
              }`}>
              <item.icon size={18} />
              <span>{item.label}</span>
              {item.label === 'Live Monitoring' && liveSessions.length > 0 && (
                <span className="ml-auto bg-red-500 text-white text-[10px] font-black px-2 py-0.5 rounded-full animate-pulse">
                  {liveSessions.length}
                </span>
              )}
            </button>
          ))}
        </nav>

        <button onClick={logout}
          className="flex items-center space-x-3 px-5 py-4 rounded-2xl text-slate-500 hover:text-red-400 hover:bg-red-500/5 transition-all border border-transparent hover:border-red-500/10">
          <LogOut size={18} />
          <span className="text-sm font-bold uppercase tracking-wider">Logout</span>
        </button>
      </div>

      {/* Main Content */}
      <div className="flex-1 p-6 md:p-12 overflow-y-auto">
        {/* Ambient glow */}
        <div className="fixed top-0 right-0 w-[40%] h-[40%] bg-purple-600/5 blur-[150px] rounded-full pointer-events-none" />

        <header className="flex flex-col md:flex-row justify-between items-start md:items-center mb-12 gap-6 relative">
          <div>
            <h1 className="text-4xl font-extrabold text-white tracking-tight">
              {activeTab === 'Active Drives' ? 'Recruitment Orchestration' : 
               activeTab === 'Live Monitoring' ? 'Live Session Oversight' : 
               activeTab === 'Evaluation Reports' ? 'Assessment Insights' :
               activeTab === 'Skill Matrix' ? 'Skill Matrix Analytics' : 'HR Profile Settings'}
            </h1>
            <p className="text-slate-500 text-lg mt-1 font-medium italic">Welcome back, {user?.first_name}</p>
          </div>
          {activeTab === 'Active Drives' && (
            <div className="flex flex-col sm:flex-row sm:items-center sm:gap-3">
              <div className="rounded-3xl bg-white/5 border border-white/10 px-4 py-3 text-sm text-slate-300">
                <p className="uppercase tracking-[0.2em] text-[10px] text-slate-500 font-black">HR Profile Completion</p>
                <p className="text-lg font-black text-white">{profileCompletion}%</p>
              </div>
              <button onClick={() => setActiveTab('Drive Settings')}
                className="bg-white/5 border border-white/10 text-white px-6 py-3 rounded-2xl font-bold hover:bg-white/10 transition-all">
                Edit Profile
              </button>
              <button onClick={() => setShowCreateModal(true)}
                className={`bg-purple-600 text-white px-8 py-4 rounded-2xl font-bold hover:bg-purple-500 transition-all shadow-xl shadow-purple-900/30 flex items-center space-x-2 active:scale-95 ${profileCompletion < 50 ? 'opacity-50 cursor-not-allowed' : ''}`}
                disabled={profileCompletion < 50}>
                <Plus size={20} />
                <span>Launch Drive</span>
              </button>
            </div>
          )}
          {activeTab === 'Active Drives' && profileCompletion < 50 && (
            <div className="mt-4 text-sm text-slate-400">Complete at least 50% of your HR profile before launching a drive. Click <button onClick={() => setActiveTab('Drive Settings')} className="text-purple-400 underline">Edit Profile</button> to continue.</div>
          )}
        </header>

        {loading && !drives.length ? (
          <div className="flex justify-center items-center h-64">
            <Loader2 className="animate-spin text-purple-500" size={48} />
          </div>
        ) : activeTab === 'Active Drives' ? (
          drives.length === 0 ? (
            <div className="bg-white/2 border-2 border-dashed border-white/10 rounded-[2.5rem] p-20 text-center space-y-6">
              <div className="w-20 h-20 bg-white/5 rounded-full flex items-center justify-center mx-auto text-slate-600">
                <Briefcase size={40} />
              </div>
              <div>
                <h2 className="text-2xl font-bold text-white">No active drives detected</h2>
                <p className="text-slate-500 mt-2">Create your first hiring drive to start inviting candidates and collecting interview results.</p>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
              {drives.map(drive => (
                <motion.div layout key={drive.id}
                  className="bg-white/2 border border-white/5 p-10 rounded-[2.5rem] hover:border-purple-500/20 hover:bg-white/5 transition-all group relative overflow-hidden">
                  <div className="absolute top-0 right-0 w-32 h-32 bg-purple-600/5 blur-[60px] rounded-full group-hover:bg-purple-600/10 transition-all" />

                  <div className="flex justify-between items-start mb-8 relative">
                    <div>
                      <div className="flex items-center space-x-3 mb-2">
                        <span className="bg-purple-500/10 text-purple-400 text-[10px] font-black uppercase tracking-widest px-3 py-1 rounded-full border border-purple-500/20">Interview Workflow</span>
                        <span className="flex items-center text-[10px] font-bold text-slate-500 uppercase tracking-widest">
                          <Clock size={12} className="mr-1" /> {new Date(drive.created_at).toLocaleDateString()}
                        </span>
                      </div>
                      <h2 className="text-2xl font-bold text-white">{drive.title}</h2>
                      <p className="text-slate-400 font-medium">{drive.job_role}</p>
                    </div>
                    <button className="text-slate-600 hover:text-slate-400 transition-colors"><MoreVertical size={20} /></button>
                  </div>

                  <div className="grid grid-cols-2 gap-4 mb-8">
                    <div className="bg-white/5 p-5 rounded-2xl border border-white/5 text-center">
                      <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-1">Participants</p>
                      <p className="text-2xl font-black text-white">{drive.participant_count ?? 0}</p>
                    </div>
                    <div className="bg-white/5 p-5 rounded-2xl border border-white/5 text-center">
                      <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-1">Avg. Score</p>
                      <p className="text-2xl font-black text-white">{drive.avg_score ? drive.avg_score.toFixed(1) : '—'}</p>
                    </div>
                  </div>

                  <div className="flex items-center space-x-3">
                    <button onClick={() => handleGenerateLink(drive.id)}
                      className={`flex-1 flex items-center justify-center space-x-2 py-4 rounded-2xl font-bold transition-all text-sm ${
                        copiedId === drive.id ? 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-400' : 'bg-purple-600 text-white hover:bg-purple-500 shadow-lg shadow-purple-900/20'
                      }`}>
                      {copiedId === drive.id ? <CheckCircle2 size={18} /> : <LinkIcon size={18} />}
                      <span>{copiedId === drive.id ? 'Link Copied' : 'Copy Invite Link'}</span>
                    </button>

                    <button onClick={() => setBulkInviteDrive(drive)}
                      className="flex items-center space-x-2 bg-white/5 border border-white/10 text-slate-300 px-5 py-4 rounded-2xl font-bold hover:bg-white/10 hover:text-white transition-all text-sm">
                      <Mail size={16} />
                      <span>Bulk</span>
                    </button>

                    <button 
                      onClick={() => setActiveTab('Evaluation Reports')}
                      className="bg-white/5 border border-white/10 text-slate-400 px-4 py-4 rounded-2xl hover:bg-white/10 transition-all">
                      <ChevronRight size={18} />
                    </button>
                  </div>
                </motion.div>
              ))}
            </div>
          )
        ) : activeTab === 'Live Monitoring' ? (
          <div className="bg-white/2 border border-white/5 rounded-[2.5rem] overflow-hidden">
            <div className="px-10 py-6 border-b border-white/5 bg-white/2">
              <div className="grid grid-cols-12 gap-4 text-[10px] font-black uppercase tracking-[0.2em] text-slate-500">
                <div className="col-span-4">Candidate / Session</div>
                <div className="col-span-4">Role / Drive</div>
                <div className="col-span-2 text-center">Status</div>
                <div className="col-span-2 text-right">Actions</div>
              </div>
            </div>
            <div className="divide-y divide-white/5">
              {liveSessions.length === 0 ? (
                <div className="p-20 text-center">
                  <Radio size={48} className="mx-auto text-slate-700 mb-6" />
                  <p className="text-slate-500 font-medium">No live sessions currently in progress.</p>
                </div>
              ) : (
                liveSessions.map(session => (
                  <div key={session.id} className="px-10 py-8 grid grid-cols-12 gap-4 items-center hover:bg-white/5 transition-all group">
                    <div className="col-span-4 flex items-center space-x-4">
                      <div className="w-12 h-12 bg-red-500/10 border border-red-500/20 rounded-2xl flex items-center justify-center text-red-400 font-black relative">
                        <span className="absolute top-0 right-0 w-3 h-3 bg-red-500 rounded-full border-2 border-[#0a0f1e] -mt-1 -mr-1 animate-ping" />
                        <Radio size={20} />
                      </div>
                      <div>
                        <p className="text-white font-bold">Session #{session.id}</p>
                        <p className="text-xs text-slate-500 font-medium">{session.candidate_name || session.candidate_email || `Candidate #${session.candidate_id}`}</p>
                      </div>
                    </div>
                    <div className="col-span-4">
                      <p className="text-slate-300 font-bold text-sm">{session.job_role || 'Unknown Role'}</p>
                      <p className="text-[10px] text-slate-600 font-bold uppercase tracking-widest mt-0.5">{session.drive_title || 'Unknown Drive'}</p>
                    </div>
                    <div className="col-span-2 text-center">
                      <span className="text-red-400 text-xs font-black uppercase tracking-widest px-3 py-1 bg-red-500/10 rounded-full border border-red-500/20 inline-block">
                        Active Now
                      </span>
                    </div>
                    <div className="col-span-2 text-right flex justify-end">
                      <button 
                        onClick={() => setTakeoverSession(session)}
                        className="bg-red-600 hover:bg-red-500 text-white text-[10px] font-black uppercase tracking-widest px-4 py-2 rounded-xl transition-all shadow-lg shadow-red-900/30 flex items-center space-x-2">
                        <MessageSquareText size={14} />
                        <span>Guide</span>
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        ) : activeTab === 'Evaluation Reports' ? (
          <div className="bg-white/2 border border-white/5 rounded-[2.5rem] overflow-hidden">
            <div className="px-8 py-6 border-b border-white/5 bg-white/2">
              <div className="grid grid-cols-12 gap-4 text-[10px] font-black uppercase tracking-[0.2em] text-slate-500 items-center">
                <div className="col-span-3">Candidate</div>
                <div className="col-span-2">Role / Drive</div>
                <div className="col-span-2 text-center cursor-pointer hover:text-white transition-colors" onClick={() => requestSort('overall_score')}>Overall Score {sortConfig.key === 'overall_score' && (sortConfig.direction === 'asc' ? '↑' : '↓')}</div>
                <div className="col-span-2 text-center cursor-pointer hover:text-white transition-colors" onClick={() => requestSort('technical_accuracy')}>Technical {sortConfig.key === 'technical_accuracy' && (sortConfig.direction === 'asc' ? '↑' : '↓')}</div>
                <div className="col-span-2 text-center cursor-pointer hover:text-white transition-colors" onClick={() => requestSort('communication_clarity')}>Comm. {sortConfig.key === 'communication_clarity' && (sortConfig.direction === 'asc' ? '↑' : '↓')}</div>
                <div className="col-span-1"></div>
              </div>
            </div>
            <div className="divide-y divide-white/5">
              {sortedInterviews.length === 0 ? (
                <div className="p-20 text-center">
                  <p className="text-slate-500 font-medium">No evaluation reports generated yet.</p>
                </div>
              ) : (
                sortedInterviews.map(interview => (
                  <div key={interview.id} className="px-8 py-6 grid grid-cols-12 gap-4 items-center hover:bg-white/5 transition-all group">
                    <div className="col-span-3 flex items-center space-x-4">
                      <div className="w-10 h-10 bg-purple-600/10 border border-purple-500/20 rounded-2xl flex items-center justify-center text-purple-400 font-black text-sm shrink-0">
                        {(interview.candidate_name || interview.candidate_email || '#').charAt(0).toUpperCase()}
                      </div>
                      <div className="truncate">
                        <p className="text-white font-bold text-sm truncate">{interview.candidate_name || 'Guest Candidate'}</p>
                        <p className="text-[10px] text-slate-500 font-medium truncate">{interview.candidate_email || `ID #${interview.candidate_id}`}</p>
                      </div>
                    </div>
                    <div className="col-span-2 truncate">
                      <p className="text-slate-300 font-bold text-xs truncate">{interview.job_role || 'Unknown Role'}</p>
                      <p className="text-[9px] text-slate-600 font-bold uppercase tracking-widest mt-0.5 truncate">{interview.drive_title || 'Unknown Drive'}</p>
                    </div>
                    <div className="col-span-2 text-center">
                      <span className={`text-lg font-black ${
                        interview.overall_score >= 8 ? 'text-emerald-400' : 
                        interview.overall_score >= 5 ? 'text-purple-400' : 'text-amber-400'
                      }`}>
                        {interview.overall_score?.toFixed(1) || '—'}
                      </span>
                    </div>
                    <div className="col-span-2 text-center">
                      <span className="text-sm font-bold text-slate-300">
                        {interview.ai_feedback?.technical_accuracy?.toFixed(1) || '—'}
                      </span>
                    </div>
                    <div className="col-span-2 text-center">
                      <span className="text-sm font-bold text-slate-300">
                        {interview.ai_feedback?.communication_clarity?.toFixed(1) || '—'}
                      </span>
                    </div>
                    <div className="col-span-1 text-right">
                      <button 
                        onClick={() => handleViewReport(interview.id)}
                        className="p-2 bg-white/5 border border-white/10 rounded-xl text-slate-400 hover:text-white hover:bg-purple-600 transition-all group-hover:scale-110">
                        <ChevronRight size={16} />
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        ) : activeTab === 'Skill Matrix' ? (
          <SkillMatrixTab interviews={interviews} />
        ) : (
          activeTab === 'Drive Settings' ? (
            <DriveSettingsTab />
          ) : (
          <div className="p-20 text-center">
            <h2 className="text-2xl font-bold text-white">{activeTab}</h2>
            <p className="text-slate-500 mt-2">This module is coming soon in the next update.</p>
          </div>
          )
        )}
      </div>
    </div>
  );
};

export default HRDashboard;
