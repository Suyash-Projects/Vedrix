import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Briefcase, 
  Plus, 
  Link as LinkIcon, 
  Users, 
  Activity, 
  ChevronRight, 
  Copy, 
  CheckCircle2, 
  Clock,
  LayoutDashboard,
  LogOut,
  Settings,
  MoreVertical,
  X
} from 'lucide-react';
import apiClient from '../services/api';
import useAuthStore from '../store/useAuthStore';

/* ─────────────────────────────────────────────────────────────
   SUB-COMPONENT: CREATE DRIVE MODAL
────────────────────────────────────────────────────────────── */
const CreateDriveModal = ({ onClose, onCreated }) => {
  const [formData, setFormData] = useState({
    title: '',
    job_role: '',
    description: '',
    skills_required: ''
  });
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await apiClient.post('/hr/drives', formData);
      onCreated();
      onClose();
    } catch (err) {
      alert("Failed to create drive");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-slate-950/60 backdrop-blur-sm z-[200] flex items-center justify-center p-6">
      <motion.div 
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="bg-white rounded-[2rem] w-full max-w-xl overflow-hidden shadow-2xl"
      >
        <div className="px-8 py-6 bg-slate-50 border-b border-slate-100 flex justify-between items-center">
          <h2 className="text-xl font-bold text-slate-900">New Recruitment Drive</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600"><X size={20} /></button>
        </div>
        
        <form onSubmit={handleSubmit} className="p-8 space-y-6">
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-black uppercase text-slate-400 tracking-widest mb-1.5 ml-1">Drive Title</label>
              <input 
                required
                className="w-full bg-slate-50 border border-slate-100 rounded-xl px-4 py-3 text-slate-900 focus:ring-2 focus:ring-purple-500 outline-none transition-all"
                placeholder="e.g. Summer Internship 2026"
                onChange={(e) => setFormData({...formData, title: e.target.value})}
              />
            </div>
            <div>
              <label className="block text-xs font-black uppercase text-slate-400 tracking-widest mb-1.5 ml-1">Target Job Role</label>
              <input 
                required
                className="w-full bg-slate-50 border border-slate-100 rounded-xl px-4 py-3 text-slate-900 focus:ring-2 focus:ring-purple-500 outline-none transition-all"
                placeholder="e.g. Senior Backend Engineer"
                onChange={(e) => setFormData({...formData, job_role: e.target.value})}
              />
            </div>
            <div>
              <label className="block text-xs font-black uppercase text-slate-400 tracking-widest mb-1.5 ml-1">Required Skills (Comma separated)</label>
              <input 
                className="w-full bg-slate-50 border border-slate-100 rounded-xl px-4 py-3 text-slate-900 focus:ring-2 focus:ring-purple-500 outline-none transition-all"
                placeholder="FastAPI, React, SQLModel"
                onChange={(e) => setFormData({...formData, skills_required: e.target.value})}
              />
            </div>
          </div>

          <button 
            type="submit"
            disabled={loading}
            className="w-full bg-purple-600 text-white py-4 rounded-2xl font-bold text-lg hover:bg-purple-700 shadow-xl shadow-purple-500/30 transition-all flex items-center justify-center"
          >
            {loading ? <Loader2 className="animate-spin" /> : <span>Initialize Drive</span>}
          </button>
        </form>
      </motion.div>
    </div>
  );
};

/* ─────────────────────────────────────────────────────────────
   MAIN HR DASHBOARD
────────────────────────────────────────────────────────────── */
const HRDashboard = () => {
  const { user, logout } = useAuthStore();
  const [drives, setDrives] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [copiedId, setCopiedId] = useState(null);

  const fetchDrives = async () => {
    try {
      const res = await apiClient.get('/hr/drives');
      setDrives(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDrives();
  }, []);

  const handleGenerateLink = async (driveId) => {
    try {
      const res = await apiClient.post(`/hr/drives/${driveId}/magic-link`);
      await navigator.clipboard.writeText(res.data.link);
      setCopiedId(driveId);
      setTimeout(() => setCopiedId(null), 2000);
    } catch (err) {
      alert("Failed to generate link");
    }
  };

  return (
    <div className="min-h-screen bg-[#F8FAFC] flex font-sans">
      <AnimatePresence>
        {showModal && <CreateDriveModal onClose={() => setShowModal(false)} onCreated={fetchDrives} />}
      </AnimatePresence>

      {/* Sidebar */}
      <div className="w-72 bg-white border-r border-slate-200 p-8 flex flex-col space-y-10 hidden lg:flex shadow-sm">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-purple-600 rounded-xl flex items-center justify-center text-white shadow-lg shadow-purple-200">
            <Briefcase size={22} />
          </div>
          <span className="text-xl font-bold tracking-tight text-slate-900">Vedrix <span className="text-purple-600">HR</span></span>
        </div>

        <nav className="flex-1 space-y-2">
          {[
            { label: 'Active Drives', icon: LayoutDashboard, active: true },
            { label: 'Live Candidates', icon: Users },
            { label: 'Evaluation Reports', icon: Activity },
            { label: 'Drive Settings', icon: Settings },
          ].map(item => (
            <button 
              key={item.label}
              className={`w-full flex items-center space-x-3 px-5 py-4 rounded-2xl transition-all ${item.active ? 'bg-purple-50 text-purple-700 font-bold' : 'text-slate-500 hover:text-slate-900 hover:bg-slate-50'}`}
            >
              <item.icon size={20} />
              <span className="text-sm">{item.label}</span>
            </button>
          ))}
        </nav>

        <button 
          onClick={logout}
          className="flex items-center space-x-3 px-5 py-4 rounded-2xl text-slate-400 hover:text-red-500 hover:bg-red-50 transition-all border border-transparent hover:border-red-100"
        >
          <LogOut size={20} />
          <span className="text-sm font-bold uppercase tracking-wider">Logout</span>
        </button>
      </div>

      {/* Main Content */}
      <div className="flex-1 p-6 md:p-12 overflow-y-auto">
        <header className="flex flex-col md:flex-row justify-between items-start md:items-center mb-12 gap-6">
          <div>
            <h1 className="text-4xl font-extrabold text-slate-900 tracking-tight">Recruitment Orchestration</h1>
            <p className="text-slate-500 text-lg mt-1 font-medium italic">Welcome back, {user?.first_name}</p>
          </div>
          <button 
            onClick={() => setShowModal(true)}
            className="bg-slate-900 text-white px-8 py-4 rounded-2xl font-bold text-lg hover:bg-slate-800 transition-all shadow-xl shadow-slate-200 flex items-center space-x-2 active:scale-95"
          >
            <Plus size={22} />
            <span>Launch Drive</span>
          </button>
        </header>

        {/* Drives Grid */}
        {loading ? (
          <div className="flex justify-center items-center h-64"><Loader2 className="animate-spin text-purple-600" size={48} /></div>
        ) : drives.length === 0 ? (
          <div className="bg-white border-2 border-dashed border-slate-200 rounded-[2.5rem] p-20 text-center space-y-6">
            <div className="w-20 h-20 bg-slate-50 rounded-full flex items-center justify-center mx-auto text-slate-300"><Briefcase size={40} /></div>
            <div>
              <h2 className="text-2xl font-bold text-slate-900">No active drives detected</h2>
              <p className="text-slate-400 mt-2">Initialize your first job drive to start inviting candidates for agentic evaluation.</p>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
            {drives.map(drive => (
              <motion.div 
                layout
                key={drive.id}
                className="bg-white border border-slate-100 p-10 rounded-[2.5rem] shadow-sm hover:shadow-2xl hover:border-purple-100 transition-all group"
              >
                <div className="flex justify-between items-start mb-8">
                  <div>
                    <div className="flex items-center space-x-3 mb-2">
                       <span className="bg-purple-50 text-purple-600 text-[10px] font-black uppercase tracking-widest px-3 py-1 rounded-full border border-purple-100">AI Enabled</span>
                       <span className="flex items-center text-[10px] font-bold text-slate-400 uppercase tracking-widest"><Clock size={12} className="mr-1" /> {new Date(drive.created_at).toLocaleDateString()}</span>
                    </div>
                    <h2 className="text-2xl font-bold text-slate-900">{drive.title}</h2>
                    <p className="text-slate-500 font-medium">{drive.job_role}</p>
                  </div>
                  <button className="text-slate-300 hover:text-slate-600"><MoreVertical size={20}/></button>
                </div>

                <div className="grid grid-cols-2 gap-4 mb-8">
                  <div className="bg-slate-50 p-5 rounded-2xl border border-slate-100 text-center">
                    <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Participants</p>
                    <p className="text-2xl font-black text-slate-900">0</p>
                  </div>
                  <div className="bg-slate-50 p-5 rounded-2xl border border-slate-100 text-center">
                    <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Avg. Score</p>
                    <p className="text-2xl font-black text-slate-900">—</p>
                  </div>
                </div>

                <div className="flex items-center space-x-4">
                  <button 
                    onClick={() => handleGenerateLink(drive.id)}
                    className={`flex-1 flex items-center justify-center space-x-2 py-4 rounded-2xl font-bold transition-all ${
                      copiedId === drive.id ? 'bg-emerald-500 text-white' : 'bg-purple-600 text-white hover:bg-purple-700 shadow-lg shadow-purple-100'
                    }`}
                  >
                    {copiedId === drive.id ? <CheckCircle2 size={20} /> : <LinkIcon size={20} />}
                    <span>{copiedId === drive.id ? 'Magic Link Copied' : 'Invite Candidate'}</span>
                  </button>
                  <button className="bg-white border-2 border-slate-100 text-slate-900 px-6 py-4 rounded-2xl font-bold hover:bg-slate-50 transition-all flex items-center group-hover:border-purple-200">
                    <ChevronRight size={20} />
                  </button>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default HRDashboard;
