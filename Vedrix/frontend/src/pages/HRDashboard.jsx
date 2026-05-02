import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Briefcase, Plus, Link as LinkIcon, Users, Activity,
  ChevronRight, Copy, CheckCircle2, Clock, LayoutDashboard,
  LogOut, Settings, MoreVertical, X, Loader2, Mail, Send,
  Calendar, ChevronDown
} from 'lucide-react';
import apiClient from '../services/api';
import useAuthStore from '../store/useAuthStore';

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
                <p className="text-xs text-slate-500 uppercase tracking-widest font-bold">Links are ready to share</p>
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

/* ── MAIN HR DASHBOARD ── */
const HRDashboard = ({ onViewReport }) => {
  const { user, logout } = useAuthStore();
  const [drives, setDrives] = useState([]);
  const [driveMap, setDriveMap] = useState({});
  const [interviews, setInterviews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('Active Drives');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [bulkInviteDrive, setBulkInviteDrive] = useState(null);
  const [copiedId, setCopiedId] = useState(null);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [drivesRes, interviewsRes] = await Promise.all([
        apiClient.get('/hr/drives'),
        apiClient.get('/hr/interviews')
      ]);
      setDrives(drivesRes.data);
      // Build a drive lookup map for the reports table
      const driveMap = {};
      drivesRes.data.forEach(d => { driveMap[d.id] = d; });
      setDriveMap(driveMap);
      setInterviews(interviewsRes.data.filter(i => i.status === 'completed'));
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);

  const handleGenerateLink = async (driveId) => {
    try {
      const res = await apiClient.post(`/hr/drives/${driveId}/magic-link`);
      await navigator.clipboard.writeText(res.data.link);
      setCopiedId(driveId);
      setTimeout(() => setCopiedId(null), 2000);
    } catch {
      alert('Failed to generate link');
    }
  };

  return (
    <div className="min-h-screen bg-[#020617] flex font-sans">
      <AnimatePresence>
        {showCreateModal && <CreateDriveModal onClose={() => setShowCreateModal(false)} onCreated={fetchData} />}
        {bulkInviteDrive && <BulkInviteModal drive={bulkInviteDrive} onClose={() => setBulkInviteDrive(null)} />}
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
            { label: 'Evaluation Reports', icon: Activity },
            { label: 'Drive Settings', icon: Settings },
          ].map(item => (
            <button key={item.label}
              onClick={() => setActiveTab(item.label)}
              className={`w-full flex items-center space-x-3 px-5 py-4 rounded-2xl transition-all text-sm font-bold ${
                activeTab === item.label ? 'bg-purple-600/10 text-purple-400 border border-purple-500/20' : 'text-slate-500 hover:text-white hover:bg-white/5'
              }`}>
              <item.icon size={18} />
              <span>{item.label}</span>
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
              {activeTab === 'Active Drives' ? 'Recruitment Orchestration' : 'Assessment Insights'}
            </h1>
            <p className="text-slate-500 text-lg mt-1 font-medium italic">Welcome back, {user?.first_name}</p>
          </div>
          {activeTab === 'Active Drives' && (
            <button onClick={() => setShowCreateModal(true)}
              className="bg-purple-600 text-white px-8 py-4 rounded-2xl font-bold hover:bg-purple-500 transition-all shadow-xl shadow-purple-900/30 flex items-center space-x-2 active:scale-95">
              <Plus size={20} />
              <span>Launch Drive</span>
            </button>
          )}
        </header>

        {loading ? (
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
                <p className="text-slate-500 mt-2">Initialize your first job drive to start inviting candidates for agentic evaluation.</p>
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
                        <span className="bg-purple-500/10 text-purple-400 text-[10px] font-black uppercase tracking-widest px-3 py-1 rounded-full border border-purple-500/20">AI Enabled</span>
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
                    {/* Single magic link */}
                    <button onClick={() => handleGenerateLink(drive.id)}
                      className={`flex-1 flex items-center justify-center space-x-2 py-4 rounded-2xl font-bold transition-all text-sm ${
                        copiedId === drive.id ? 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-400' : 'bg-purple-600 text-white hover:bg-purple-500 shadow-lg shadow-purple-900/20'
                      }`}>
                      {copiedId === drive.id ? <CheckCircle2 size={18} /> : <LinkIcon size={18} />}
                      <span>{copiedId === drive.id ? 'Link Copied' : 'Invite Candidate'}</span>
                    </button>

                    {/* Bulk invite */}
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
        ) : activeTab === 'Evaluation Reports' ? (
          <div className="bg-white/2 border border-white/5 rounded-[2.5rem] overflow-hidden">
            <div className="px-10 py-6 border-b border-white/5 bg-white/2">
              <div className="grid grid-cols-12 gap-4 text-[10px] font-black uppercase tracking-[0.2em] text-slate-500">
                <div className="col-span-4">Candidate</div>
                <div className="col-span-3">Role / Drive</div>
                <div className="col-span-2 text-center">Overall Score</div>
                <div className="col-span-2 text-center">Date</div>
                <div className="col-span-1"></div>
              </div>
            </div>
            <div className="divide-y divide-white/5">
              {interviews.length === 0 ? (
                <div className="p-20 text-center">
                  <p className="text-slate-500 font-medium">No evaluation reports generated yet.</p>
                </div>
              ) : (
                interviews.map(interview => (
                  <div key={interview.id} className="px-10 py-8 grid grid-cols-12 gap-4 items-center hover:bg-white/5 transition-all group">
                    <div className="col-span-4 flex items-center space-x-4">
                      <div className="w-12 h-12 bg-purple-600/10 border border-purple-500/20 rounded-2xl flex items-center justify-center text-purple-400 font-black">
                        {interview.candidate_id}
                      </div>
                      <div>
                        <p className="text-white font-bold">Candidate #{interview.candidate_id}</p>
                        <p className="text-xs text-slate-500 font-medium">Actual Assessment</p>
                      </div>
                    </div>
                    <div className="col-span-3">
                      <p className="text-slate-300 font-bold text-sm">{driveMap[interview.job_drive_id]?.job_role || 'Unknown Role'}</p>
                      <p className="text-[10px] text-slate-600 font-bold uppercase tracking-widest mt-0.5">{driveMap[interview.job_drive_id]?.title || 'Unknown Drive'}</p>
                    </div>
                    <div className="col-span-2 text-center">
                      <span className={`text-xl font-black ${
                        interview.overall_score >= 8 ? 'text-emerald-400' : 
                        interview.overall_score >= 5 ? 'text-purple-400' : 'text-amber-400'
                      }`}>
                        {interview.overall_score?.toFixed(1) || '—'}
                      </span>
                    </div>
                    <div className="col-span-2 text-center text-slate-500 text-xs font-bold uppercase tracking-widest">
                      {new Date(interview.created_at).toLocaleDateString()}
                    </div>
                    <div className="col-span-1 text-right">
                      <button 
                        onClick={() => onViewReport(interview.id)}
                        className="p-3 bg-white/5 border border-white/10 rounded-xl text-slate-400 hover:text-white hover:bg-purple-600 transition-all group-hover:scale-110">
                        <ChevronRight size={18} />
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        ) : (
          <div className="p-20 text-center">
            <h2 className="text-2xl font-bold text-white">{activeTab}</h2>
            <p className="text-slate-500 mt-2">This module is coming soon in the next update.</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default HRDashboard;
