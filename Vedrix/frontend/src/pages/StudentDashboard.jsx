import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Play, Upload, FileText, BarChart3, Clock, CheckCircle2,
  TrendingUp, Award, ChevronRight, Loader2, Trash2,
  Flame, Calendar, Target, Zap, BookOpen
} from 'lucide-react';
import { RadarChart, PolarGrid, PolarAngleAxis, Radar, ResponsiveContainer } from 'recharts';
import apiClient from '../services/api';
import useAuthStore from '../store/useAuthStore';

/* ── Animated Counter ──────────────────────────────────────────────────────── */
const AnimatedNumber = ({ value, suffix = '' }) => {
  const [display, setDisplay] = useState(0);
  const started = useRef(false);

  useEffect(() => {
    if (started.current || value === null || value === undefined) return;
    started.current = true;
    const num = typeof value === 'string' ? parseFloat(value) : value;
    if (isNaN(num)) { setDisplay(value); return; }
    let start = 0;
    const duration = 1000;
    const startTime = performance.now();
    const animate = (now) => {
      const progress = Math.min((now - startTime) / duration, 1);
      setDisplay(Math.round(progress * num * 10) / 10);
      if (progress < 1) requestAnimationFrame(animate);
    };
    requestAnimationFrame(animate);
  }, [value]);

  return <>{typeof display === 'number' ? display : value}{suffix}</>;
};

/* ── Progress Ring SVG ─────────────────────────────────────────────────────── */
const ProgressRing = ({ percent, size = 80, strokeWidth = 6 }) => {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (percent / 100) * circumference;

  return (
    <svg width={size} height={size} className="transform -rotate-90">
      <circle cx={size/2} cy={size/2} r={radius} fill="none"
        stroke="rgba(255,255,255,0.05)" strokeWidth={strokeWidth} />
      <motion.circle
        cx={size/2} cy={size/2} r={radius} fill="none"
        stroke="url(#progressGradient)" strokeWidth={strokeWidth}
        strokeLinecap="round" strokeDasharray={circumference}
        initial={{ strokeDashoffset: circumference }}
        animate={{ strokeDashoffset: offset }}
        transition={{ duration: 1.5, ease: 'easeOut' }}
      />
      <defs>
        <linearGradient id="progressGradient" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#7c3aed" />
          <stop offset="100%" stopColor="#6366f1" />
        </linearGradient>
      </defs>
    </svg>
  );
};

const StudentDashboard = () => {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const [stats, setStats] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [profile, setProfile] = useState(null);
  const [editProfile, setEditProfile] = useState({
    university: '', degree: '', graduation_year: '', gpa: '', major: '', minor: '',
    skills: '', experience_level: '', work_experience: '', internships: '',
    projects: '', certifications: '', languages: '',
    linkedin_url: '', github_url: '', portfolio_url: '', hackathons: '',
    expected_salary: '', preferred_locations: '', availability: '', interests: ''
  });
  const [completion, setCompletion] = useState(0);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [resumeName, setResumeName] = useState(null);
  const [profileModalOpen, setProfileModalOpen] = useState(false);
  const [accountSettingsOpen, setAccountSettingsOpen] = useState(false);
  const [fabOpen, setFabOpen] = useState(false);

  // Username change state
  const [newUsername, setNewUsername] = useState('');
  const [usernameSaving, setUsernameSaving] = useState(false);
  const [usernameSuccess, setUsernameSuccess] = useState(false);
  const [usernameError, setUsernameError] = useState('');

  // Password change state
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [passwordSaving, setPasswordSaving] = useState(false);
  const [passwordSuccess, setPasswordSuccess] = useState(false);
  const [passwordError, setPasswordError] = useState('');

  const fileRef = useRef();

  const handleStartInterview = () => navigate('/interview');
  const handleViewReport = (sessionId) => navigate(`/report/${sessionId}`);
  const handleStartScheduledInterview = (sessionId) => navigate(`/interview?scheduled_session_id=${sessionId}`);

  useEffect(() => {
    const computeCompletion = (profileData) => {
      const required = [profileData?.university, profileData?.degree, profileData?.graduation_year, profileData?.skills];
      const filled = required.filter(field => field !== null && field !== undefined && String(field).trim() !== '').length;
      return Math.round((filled / required.length) * 100);
    };

    const fetchData = async () => {
      try {
        const [statsRes, sessionsRes, profileRes] = await Promise.all([
          apiClient.get('/student/stats'),
          apiClient.get('/student/interviews'),
          apiClient.get('/profiles/student'),
        ]);
        setStats(statsRes.data);
        setSessions(sessionsRes.data);
        setProfile(profileRes.data);
        setCompletion(computeCompletion(profileRes.data));
      } catch (err) {
        console.error('Dashboard fetch error:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const handleResumeUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.name.endsWith('.pdf')) return alert('Only PDF files are accepted.');
    setUploading(true);
    try {
      const form = new FormData();
      form.append('file', file);
      await apiClient.post('/profiles/student/resume', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setResumeName(file.name);
    } catch {
      alert('Resume upload failed. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  const scoreColor = (s) =>
    s >= 8 ? 'text-emerald-400' : s >= 5 ? 'text-purple-400' : 'text-amber-400';

  const handleProfileSave = async (updatedProfile) => {
    const payload = Object.entries(updatedProfile).reduce((acc, [key, value]) => {
      if (value !== null && value !== undefined && String(value).trim() !== '') {
        acc[key] = value;
      }
      return acc;
    }, {});

    try {
      await apiClient.post('/profiles/student', payload);
      setProfile({ ...profile, ...payload });
      setCompletion(Math.round(([
        payload.university, payload.degree, payload.graduation_year, payload.skills
      ].filter(field => field !== null && field !== undefined && String(field).trim() !== '').length / 4) * 100));
      setProfileModalOpen(false);
      alert('Profile saved successfully.');
    } catch (err) {
      console.error('Profile save error:', err.response?.data || err.message || err);
      alert(err.response?.data?.detail ? `Failed to save profile: ${err.response.data.detail}` : 'Failed to save profile.');
    }
  };

  const handleUsernameChange = async (e) => {
    e.preventDefault();
    setUsernameError('');
    if (!newUsername || newUsername.length < 3) { setUsernameError('Username must be at least 3 characters'); return; }
    setUsernameSaving(true);
    try {
      await apiClient.put('/users/username', { new_username: newUsername });
      setUsernameSuccess(true);
      setNewUsername('');
      setTimeout(() => setUsernameSuccess(false), 2500);
    } catch (err) {
      setUsernameError(err.response?.data?.detail || 'Failed to change username');
    } finally { setUsernameSaving(false); }
  };

  const handlePasswordChange = async (e) => {
    e.preventDefault();
    setPasswordError('');
    if (!currentPassword || !newPassword) { setPasswordError('Please fill in all password fields'); return; }
    if (newPassword.length < 4) { setPasswordError('New password must be at least 4 characters'); return; }
    if (newPassword !== confirmPassword) { setPasswordError('New passwords do not match'); return; }
    setPasswordSaving(true);
    try {
      await apiClient.post('/users/change-password', { current_password: currentPassword, new_password: newPassword });
      setPasswordSuccess(true);
      setCurrentPassword(''); setNewPassword(''); setConfirmPassword('');
      setTimeout(() => setPasswordSuccess(false), 2500);
    } catch (err) {
      setPasswordError(err.response?.data?.detail || 'Failed to change password');
    } finally { setPasswordSaving(false); }
  };

  const handleClearInterviewData = async () => {
    if (!window.confirm('Are you absolutely sure? This will permanently delete ALL your interview sessions and reports. This action cannot be undone.')) return;
    try {
      setLoading(true);
      await apiClient.delete('/users/clear-interviews');
      setSessions([]);
      setStats(prev => ({ ...prev, total_interviews: 0, completed_interviews: 0, avg_score: null, best_score: null }));
      alert('All interview data has been cleared.');
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to clear interview data. Please try again.');
    } finally { setLoading(false); }
  };

  // Skill radar data from profile
  const radarData = [
    { skill: 'Technical', value: stats?.avg_score ? Math.min(stats.avg_score * 10, 100) : 40 },
    { skill: 'Communication', value: 65 },
    { skill: 'Problem Solving', value: 70 },
    { skill: 'Adaptability', value: 55 },
    { skill: 'Leadership', value: 45 },
  ];

  // Streak calculation (mock based on sessions)
  const streak = sessions.filter(s => s.status === 'completed').length > 0 ? Math.min(sessions.filter(s => s.status === 'completed').length, 7) : 0;

  // Container animation variants
  const containerVariants = {
    hidden: { opacity: 0 },
    visible: { opacity: 1, transition: { staggerChildren: 0.08 } }
  };
  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.4, ease: 'easeOut' } }
  };

  return (
    <div className="min-h-screen bg-[#020617] text-white font-sans">
      {/* Ambient glow */}
      <div className="fixed top-0 right-0 w-[40%] h-[40%] bg-purple-600/5 blur-[150px] rounded-full pointer-events-none" />
      <div className="fixed bottom-0 left-0 w-[30%] h-[30%] bg-indigo-600/5 blur-[150px] rounded-full pointer-events-none" />

      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="max-w-6xl mx-auto px-8 py-12 space-y-10 relative z-10"
      >
        {/* Welcome + Streak */}
        <motion.div variants={itemVariants} className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-4xl font-black text-white tracking-tight">
              Welcome back, <span className="gradient-text">{user?.first_name}</span>
            </h1>
            <p className="text-slate-500 mt-2">Review your progress, update your resume, and start your next interview when you are ready.</p>
          </div>
          {streak > 0 && (
            <div className="flex items-center space-x-2 bg-amber-500/10 border border-amber-500/20 px-4 py-2 rounded-2xl">
              <Flame size={20} className="text-amber-400" />
              <span className="text-amber-400 font-black text-lg">{streak}</span>
              <span className="text-amber-400/70 text-xs font-bold uppercase tracking-widest">day streak</span>
            </div>
          )}
        </motion.div>

        {/* Stats row */}
        {!loading && stats && (
          <motion.div variants={itemVariants} className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: 'Total Sessions', val: stats.total_interviews ?? 0, icon: BarChart3, color: 'text-purple-400' },
              { label: 'Completed', val: stats.completed_interviews ?? 0, icon: CheckCircle2, color: 'text-emerald-400' },
              { label: 'Avg Score', val: stats.avg_score ? stats.avg_score : null, suffix: stats.avg_score ? '/10' : '', icon: TrendingUp, color: 'text-blue-400' },
              { label: 'Best Score', val: stats.best_score ? stats.best_score : null, suffix: stats.best_score ? '/10' : '', icon: Award, color: 'text-amber-400' },
            ].map(s => (
              <div key={s.label} className="glass-card rounded-3xl p-6 flex items-center space-x-4">
                <div className="w-10 h-10 bg-white/5 rounded-2xl flex items-center justify-center">
                  <s.icon size={20} className={s.color} />
                </div>
                <div>
                  <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest">{s.label}</p>
                  <p className={`text-xl font-black ${s.color}`}>
                    {s.val !== null ? <><AnimatedNumber value={s.val} />{s.suffix}</> : '—'}
                  </p>
                </div>
              </div>
            ))}
          </motion.div>
        )}

        {/* Loading skeleton */}
        {loading && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[1,2,3,4].map(i => (
              <div key={i} className="skeleton h-24 rounded-3xl" />
            ))}
          </div>
        )}

        {/* Action cards + Skill Radar */}
        <motion.div variants={itemVariants} className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Start Interview */}
          <motion.div
            whileHover={{ scale: 1.01 }}
            className={`bg-gradient-to-br from-purple-600/20 to-indigo-600/10 border border-purple-500/20 rounded-[2rem] p-8 flex flex-col justify-between min-h-[200px] relative overflow-hidden group cursor-pointer ${completion < 50 ? 'opacity-80 cursor-not-allowed' : ''}`}
            onClick={() => completion >= 50 && handleStartInterview()}
          >
            <div className="absolute top-0 right-0 w-32 h-32 bg-purple-600/10 blur-[60px] rounded-full group-hover:bg-purple-600/20 transition-all" />
            <div>
              <div className="w-12 h-12 bg-purple-600 rounded-2xl flex items-center justify-center mb-4 shadow-xl shadow-purple-900/40">
                <Play size={22} className="text-white" fill="white" />
              </div>
              <h2 className="text-2xl font-black text-white mb-1">Start AI Interview</h2>
              <p className="text-slate-400 text-sm">Begin a practice interview or launch your scheduled assessment.</p>
            </div>
            <div className="flex items-center text-purple-400 font-black text-xs uppercase tracking-widest mt-6">
              <span>{completion >= 50 ? 'Start Interview' : 'Complete Profile First'}</span>
              <ChevronRight size={16} className="ml-1" />
            </div>
          </motion.div>

          {/* Resume Upload */}
          <div className="glass-card rounded-[2rem] p-8 flex flex-col justify-between min-h-[200px]">
            <div>
              <div className="w-12 h-12 bg-white/5 border border-white/10 rounded-2xl flex items-center justify-center mb-4">
                <FileText size={22} className="text-slate-400" />
              </div>
              <h2 className="text-2xl font-black text-white mb-1">Resume</h2>
              <p className="text-slate-400 text-sm">
                {resumeName ? `Uploaded: ${resumeName}` : 'Upload your resume so the AI can tailor questions to your experience.'}
              </p>
            </div>
            <button
              onClick={() => fileRef.current?.click()}
              disabled={uploading}
              className="mt-6 flex items-center space-x-2 bg-white/5 border border-white/10 hover:bg-white/10 text-white px-6 py-3 rounded-2xl font-bold text-sm transition-all disabled:opacity-50 active:scale-95"
            >
              {uploading ? <Loader2 size={16} className="animate-spin" /> : <Upload size={16} />}
              <span>{uploading ? 'Uploading...' : resumeName ? 'Replace Resume' : 'Upload PDF'}</span>
            </button>
            <input ref={fileRef} type="file" accept=".pdf" className="hidden" onChange={handleResumeUpload} aria-label="Upload resume PDF" />
          </div>

          {/* Profile + Progress Ring */}
          <div className="glass-card rounded-[2rem] p-8 min-h-[200px] flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-2xl font-black text-white">Profile</h2>
                <div className="flex gap-2">
                  <button onClick={() => {
                    setEditProfile({
                      university: profile?.university ?? '', degree: profile?.degree ?? '',
                      graduation_year: profile?.graduation_year ?? '', gpa: profile?.gpa ?? '',
                      major: profile?.major ?? '', minor: profile?.minor ?? '',
                      skills: profile?.skills ?? '', experience_level: profile?.experience_level ?? '',
                      work_experience: profile?.work_experience ?? '', internships: profile?.internships ?? '',
                      projects: profile?.projects ?? '', certifications: profile?.certifications ?? '',
                      languages: profile?.languages ?? '', linkedin_url: profile?.linkedin_url ?? '',
                      github_url: profile?.github_url ?? '', portfolio_url: profile?.portfolio_url ?? '',
                      hackathons: profile?.hackathons ?? '', expected_salary: profile?.expected_salary ?? '',
                      preferred_locations: profile?.preferred_locations ?? '', availability: profile?.availability ?? '',
                      interests: profile?.interests ?? '',
                    });
                    setProfileModalOpen(true);
                  }} className="bg-purple-600 text-white px-4 py-2 rounded-2xl text-sm font-bold hover:bg-purple-500 transition-all">Edit</button>
                  <button onClick={() => setAccountSettingsOpen(true)} className="bg-white/5 border border-white/10 text-white px-4 py-2 rounded-2xl text-sm font-bold hover:bg-white/10 transition-all">Account</button>
                </div>
              </div>
              <div className="flex items-center space-x-4">
                <div className="relative">
                  <ProgressRing percent={completion} size={70} strokeWidth={5} />
                  <span className="absolute inset-0 flex items-center justify-center text-white font-black text-sm">{completion}%</span>
                </div>
                <div>
                  <p className="text-slate-400 text-xs">Profile Completion</p>
                  {completion < 50 ? (
                    <p className="text-amber-400 text-xs font-bold mt-1">Complete 50% to unlock interviews</p>
                  ) : (
                    <p className="text-emerald-400 text-xs font-bold mt-1">Ready to interview</p>
                  )}
                </div>
              </div>
            </div>
            <div className="mt-6 pt-4 border-t border-white/5">
              <button onClick={handleClearInterviewData}
                className="flex items-center space-x-2 text-slate-500 hover:text-red-400 transition-colors text-xs font-black uppercase tracking-widest">
                <Trash2 size={14} /><span>Clear Interview Data</span>
              </button>
            </div>
          </div>
        </motion.div>

        {/* Skill Radar + Recent Activity */}
        <motion.div variants={itemVariants} className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Skill Radar Chart */}
          <div className="glass-card rounded-3xl p-6">
            <h3 className="text-xs font-black uppercase text-slate-400 tracking-widest mb-4 flex items-center gap-2">
              <Target size={14} className="text-purple-400" /> Skill Overview
            </h3>
            {stats?.total_interviews > 0 ? (
              <ResponsiveContainer width="100%" height={200}>
                <RadarChart data={radarData} cx="50%" cy="50%" outerRadius="70%">
                  <PolarGrid stroke="rgba(255,255,255,0.05)" />
                  <PolarAngleAxis dataKey="skill" tick={{ fill: '#94a3b8', fontSize: 10, fontWeight: 700 }} />
                  <Radar dataKey="value" stroke="#7c3aed" fill="#7c3aed" fillOpacity={0.2} strokeWidth={2} />
                </RadarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[200px] flex flex-col items-center justify-center text-slate-600">
                <Target size={32} className="mb-2 opacity-40" />
                <p className="text-sm">Complete interviews to see your skill radar</p>
              </div>
            )}
          </div>

          {/* Recent Activity Timeline */}
          <div className="glass-card rounded-3xl p-6">
            <h3 className="text-xs font-black uppercase text-slate-400 tracking-widest mb-4 flex items-center gap-2">
              <Clock size={14} className="text-purple-400" /> Recent Activity
            </h3>
            {sessions.length > 0 ? (
              <div className="space-y-4">
                {sessions.slice(0, 5).map((s, i) => (
                  <div key={s.id} className="flex items-start space-x-3">
                    <div className="mt-1 w-2 h-2 rounded-full bg-purple-500 shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-white text-sm font-bold truncate">
                        {s.session_type === 'actual' ? 'Scheduled Interview' : 'Practice Session'}
                        {s.overall_score && <span className={`ml-2 ${scoreColor(s.overall_score)}`}>{s.overall_score.toFixed(1)}/10</span>}
                      </p>
                      <p className="text-slate-500 text-xs">{new Date(s.created_at).toLocaleDateString()} · {s.status}</p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="h-[200px] flex flex-col items-center justify-center text-slate-600">
                <BookOpen size={32} className="mb-2 opacity-40" />
                <p className="text-sm">No activity yet. Start your first interview!</p>
              </div>
            )}
          </div>
        </motion.div>

        {/* Past Sessions */}
        <motion.div variants={itemVariants}>
          <h2 className="text-xs font-black text-slate-400 uppercase tracking-widest mb-4">Past Sessions</h2>
          {loading ? (
            <div className="space-y-3">
              {[1,2,3].map(i => <div key={i} className="skeleton h-16 rounded-2xl" />)}
            </div>
          ) : sessions.length === 0 ? (
            <div className="glass-card border-2 border-dashed border-white/10 rounded-[2rem] p-16 text-center">
              <Clock size={36} className="text-slate-600 mx-auto mb-4" />
              <p className="text-slate-500 font-medium">No sessions yet. Start your first interview above.</p>
            </div>
          ) : (
            <div className="glass-card rounded-[2rem] overflow-hidden">
              <div className="px-8 py-4 border-b border-white/5 grid grid-cols-12 gap-4 text-[10px] font-black uppercase tracking-[0.2em] text-slate-500 hidden md:grid">
                <div className="col-span-3">Type</div>
                <div className="col-span-3">Status</div>
                <div className="col-span-2 text-center">Score</div>
                <div className="col-span-3">Date</div>
                <div className="col-span-1" />
              </div>
              <div className="divide-y divide-white/5">
                {sessions.map((s, i) => (
                  <motion.div
                    key={s.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.05 }}
                    className="px-8 py-5 grid grid-cols-12 gap-4 items-center hover:bg-white/[0.03] transition-all group"
                  >
                    <div className="col-span-6 md:col-span-3">
                      <span className={`text-[10px] font-black uppercase tracking-widest px-3 py-1 rounded-full border ${
                        s.session_type === 'actual' ? 'bg-purple-500/10 text-purple-400 border-purple-500/20' : 'bg-white/5 text-slate-400 border-white/10'
                      }`}>{s.session_type === 'actual' ? 'Scheduled' : 'Practice'}</span>
                    </div>
                    <div className="col-span-6 md:col-span-3">
                      <span className={`text-[10px] font-black uppercase tracking-widest ${s.status === 'completed' ? 'text-emerald-400' : 'text-amber-400'}`}>{s.status}</span>
                    </div>
                    <div className="col-span-6 md:col-span-2 text-center">
                      <span className={`text-lg font-black ${s.overall_score ? scoreColor(s.overall_score) : 'text-slate-600'}`}>
                        {s.overall_score ? s.overall_score.toFixed(1) : '—'}
                      </span>
                    </div>
                    <div className="col-span-4 md:col-span-3 text-slate-500 text-xs font-bold">
                      {new Date(s.created_at).toLocaleDateString()}
                    </div>
                    <div className="col-span-2 md:col-span-1 text-right">
                      {s.status === 'completed' ? (
                        <button onClick={() => handleViewReport(s.id)}
                          className="p-2 bg-white/5 border border-white/10 rounded-xl text-slate-400 hover:text-white hover:bg-purple-600 transition-all" aria-label="View report">
                          <ChevronRight size={16} />
                        </button>
                      ) : s.status === 'scheduled' ? (
                        <button onClick={() => handleStartScheduledInterview(s.id)}
                          className="p-2 bg-purple-600 border border-purple-500 rounded-xl text-white hover:bg-purple-500 transition-all" aria-label="Start interview">
                          <Play size={16} />
                        </button>
                      ) : null}
                    </div>
                  </motion.div>
                ))}
              </div>
            </div>
          )}
        </motion.div>

        {/* Profile Edit Modal */}
        {profileModalOpen && (
          <div className="fixed inset-0 z-[200] bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
            <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
              className="bg-[#0f172a] border border-white/10 rounded-[2rem] w-full max-w-2xl p-6 space-y-6 max-h-[90vh] overflow-y-auto">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-2xl font-black text-white">Edit Student Profile</h2>
                  <p className="text-slate-500 text-sm">Complete your profile to get personalized interview questions.</p>
                </div>
                <button onClick={() => setProfileModalOpen(false)} className="text-slate-400 hover:text-white p-2 rounded-xl hover:bg-white/5 transition-all" aria-label="Close">✕</button>
              </div>
              <div className="space-y-4">
                <h3 className="text-xs font-black uppercase text-purple-400 tracking-widest">Academic</h3>
                <div className="grid grid-cols-2 gap-4">
                  <input type="text" placeholder="University" value={editProfile.university} onChange={e => setEditProfile({...editProfile, university: e.target.value})} className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none" />
                  <input type="text" placeholder="Major" value={editProfile.major} onChange={e => setEditProfile({...editProfile, major: e.target.value})} className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none" />
                  <input type="text" placeholder="Degree" value={editProfile.degree} onChange={e => setEditProfile({...editProfile, degree: e.target.value})} className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none" />
                  <input type="text" placeholder="Minor" value={editProfile.minor} onChange={e => setEditProfile({...editProfile, minor: e.target.value})} className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none" />
                  <input type="number" placeholder="Graduation Year" value={editProfile.graduation_year} onChange={e => setEditProfile({...editProfile, graduation_year: e.target.value ? Number(e.target.value) : null})} className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none" />
                  <input type="number" step="0.01" placeholder="GPA" value={editProfile.gpa} onChange={e => setEditProfile({...editProfile, gpa: e.target.value ? Number(e.target.value) : null})} className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none" />
                </div>
              </div>
              <div className="space-y-4">
                <h3 className="text-xs font-black uppercase text-purple-400 tracking-widest">Skills & Experience</h3>
                <div className="grid grid-cols-2 gap-4">
                  <input type="text" placeholder="Technical Skills" value={editProfile.skills} onChange={e => setEditProfile({...editProfile, skills: e.target.value})} className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none col-span-2" />
                  <select value={editProfile.experience_level} onChange={e => setEditProfile({...editProfile, experience_level: e.target.value})} className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white focus:ring-2 focus:ring-purple-500 outline-none">
                    <option value="">Experience Level</option>
                    <option value="entry">Entry Level</option>
                    <option value="mid">Mid Level</option>
                    <option value="senior">Senior Level</option>
                  </select>
                  <input type="text" placeholder="Availability" value={editProfile.availability} onChange={e => setEditProfile({...editProfile, availability: e.target.value})} className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none" />
                  <input type="text" placeholder="Work Experience" value={editProfile.work_experience} onChange={e => setEditProfile({...editProfile, work_experience: e.target.value})} className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none col-span-2" />
                  <input type="text" placeholder="Internships" value={editProfile.internships} onChange={e => setEditProfile({...editProfile, internships: e.target.value})} className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none col-span-2" />
                </div>
              </div>
              <div className="space-y-4">
                <h3 className="text-xs font-black uppercase text-purple-400 tracking-widest">Projects & Links</h3>
                <div className="grid grid-cols-2 gap-4">
                  <input type="text" placeholder="Projects" value={editProfile.projects} onChange={e => setEditProfile({...editProfile, projects: e.target.value})} className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none col-span-2" />
                  <input type="text" placeholder="Certifications" value={editProfile.certifications} onChange={e => setEditProfile({...editProfile, certifications: e.target.value})} className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none" />
                  <input type="text" placeholder="Hackathons" value={editProfile.hackathons} onChange={e => setEditProfile({...editProfile, hackathons: e.target.value})} className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none" />
                  <input type="text" placeholder="LinkedIn URL" value={editProfile.linkedin_url} onChange={e => setEditProfile({...editProfile, linkedin_url: e.target.value})} className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none" />
                  <input type="text" placeholder="GitHub URL" value={editProfile.github_url} onChange={e => setEditProfile({...editProfile, github_url: e.target.value})} className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none" />
                  <input type="text" placeholder="Portfolio URL" value={editProfile.portfolio_url} onChange={e => setEditProfile({...editProfile, portfolio_url: e.target.value})} className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none col-span-2" />
                  <input type="text" placeholder="Languages" value={editProfile.languages} onChange={e => setEditProfile({...editProfile, languages: e.target.value})} className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none" />
                  <input type="text" placeholder="Interests" value={editProfile.interests} onChange={e => setEditProfile({...editProfile, interests: e.target.value})} className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none" />
                  <input type="text" placeholder="Expected Salary" value={editProfile.expected_salary} onChange={e => setEditProfile({...editProfile, expected_salary: e.target.value})} className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none" />
                  <input type="text" placeholder="Preferred Locations" value={editProfile.preferred_locations} onChange={e => setEditProfile({...editProfile, preferred_locations: e.target.value})} className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none" />
                </div>
              </div>
              <div className="flex justify-end gap-3 pt-2">
                <button onClick={() => setProfileModalOpen(false)} className="px-6 py-3 rounded-2xl border border-white/10 text-slate-300 hover:bg-white/5 transition-all">Cancel</button>
                <button onClick={() => handleProfileSave(editProfile)} className="px-6 py-3 rounded-2xl bg-purple-600 text-white font-bold hover:bg-purple-500 transition-all">Save Profile</button>
              </div>
            </motion.div>
          </div>
        )}

        {/* Account Settings Modal */}
        {accountSettingsOpen && (
          <div className="fixed inset-0 z-[200] bg-black/70 backdrop-blur-sm flex items-center justify-center p-6">
            <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
              className="bg-[#0f172a] border border-white/10 rounded-[2rem] w-full max-w-xl p-8 space-y-8 max-h-[90vh] overflow-y-auto">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-2xl font-black text-white">Account Settings</h2>
                  <p className="text-slate-500 text-sm">Manage your username and password.</p>
                </div>
                <button onClick={() => setAccountSettingsOpen(false)} className="text-slate-400 hover:text-white p-2 rounded-xl hover:bg-white/5 transition-all" aria-label="Close">✕</button>
              </div>
              <div className="border-t border-white/10 pt-6">
                <h3 className="text-lg font-bold text-white mb-2">Change Username</h3>
                <p className="text-slate-500 mb-4 text-sm">Current: <span className="text-purple-400 font-mono">@{user?.username}</span></p>
                {usernameSuccess ? (
                  <div className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 px-4 py-3 rounded-xl text-sm font-bold">Username changed successfully!</div>
                ) : (
                  <form onSubmit={handleUsernameChange} className="space-y-4">
                    {usernameError && <div className="bg-red-500/10 border border-red-500/20 text-red-400 px-4 py-2 rounded-xl text-sm">{usernameError}</div>}
                    <input className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none" placeholder="Enter new username" value={newUsername} onChange={e => setNewUsername(e.target.value)} />
                    <button type="submit" disabled={usernameSaving} className="flex items-center space-x-2 px-6 py-3 bg-white/10 hover:bg-white/20 border border-white/10 text-white rounded-xl font-bold text-sm transition-all disabled:opacity-50">
                      {usernameSaving && <Loader2 className="animate-spin" size={14} />}
                      <span>{usernameSaving ? 'Changing...' : 'Change Username'}</span>
                    </button>
                  </form>
                )}
              </div>
              <div className="border-t border-white/10 pt-6">
                <h3 className="text-lg font-bold text-white mb-2">Change Password</h3>
                {passwordSuccess ? (
                  <div className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 px-4 py-3 rounded-xl text-sm font-bold">Password changed successfully!</div>
                ) : (
                  <form onSubmit={handlePasswordChange} className="space-y-4">
                    {passwordError && <div className="bg-red-500/10 border border-red-500/20 text-red-400 px-4 py-2 rounded-xl text-sm">{passwordError}</div>}
                    <input type="password" className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none" placeholder="Current password" value={currentPassword} onChange={e => setCurrentPassword(e.target.value)} />
                    <input type="password" className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none" placeholder="New password" value={newPassword} onChange={e => setNewPassword(e.target.value)} />
                    <input type="password" className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none" placeholder="Confirm new password" value={confirmPassword} onChange={e => setConfirmPassword(e.target.value)} />
                    <button type="submit" disabled={passwordSaving} className="flex items-center space-x-2 px-6 py-3 bg-white/10 hover:bg-white/20 border border-white/10 text-white rounded-xl font-bold text-sm transition-all disabled:opacity-50">
                      {passwordSaving && <Loader2 className="animate-spin" size={14} />}
                      <span>{passwordSaving ? 'Changing...' : 'Change Password'}</span>
                    </button>
                  </form>
                )}
              </div>
            </motion.div>
          </div>
        )}

        {/* Quick Actions FAB */}
        <div className="fixed bottom-8 right-8 z-50">
          <AnimatePresence>
            {fabOpen && (
              <motion.div
                initial={{ opacity: 0, y: 20, scale: 0.8 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 20, scale: 0.8 }}
                className="absolute bottom-16 right-0 space-y-2 mb-2"
              >
                {[
                  { label: 'Start Interview', icon: Play, action: handleStartInterview, color: 'bg-purple-600' },
                  { label: 'Upload Resume', icon: Upload, action: () => fileRef.current?.click(), color: 'bg-indigo-600' },
                  { label: 'Edit Profile', icon: FileText, action: () => setProfileModalOpen(true), color: 'bg-violet-600' },
                ].map(({ label, icon: Icon, action, color }) => (
                  <button key={label} onClick={() => { action(); setFabOpen(false); }}
                    className={`flex items-center space-x-2 ${color} text-white px-4 py-2.5 rounded-2xl font-bold text-sm shadow-lg whitespace-nowrap hover:opacity-90 transition-all`}
                    aria-label={label}>
                    <Icon size={16} /><span>{label}</span>
                  </button>
                ))}
              </motion.div>
            )}
          </AnimatePresence>
          <button
            onClick={() => setFabOpen(!fabOpen)}
            className={`w-14 h-14 rounded-full bg-purple-600 text-white flex items-center justify-center shadow-xl shadow-purple-900/40 hover:bg-purple-500 transition-all ${fabOpen ? 'rotate-45' : ''}`}
            aria-label="Quick actions"
          >
            <Zap size={22} />
          </button>
        </div>

      </motion.div>
    </div>
  );
};

export default StudentDashboard;
