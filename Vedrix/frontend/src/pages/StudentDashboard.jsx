import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Play, Upload, FileText, BarChart3, Clock, CheckCircle2,
  TrendingUp, Award, ChevronRight, Loader2, Trash2
} from 'lucide-react';
import apiClient from '../services/api';
import useAuthStore from '../store/useAuthStore';

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

  const handleStartInterview = () => {
    navigate('/interview');
  };

  const handleViewReport = (sessionId) => {
    navigate(`/report/${sessionId}`);
  };

  const handleStartScheduledInterview = (sessionId) => {
    navigate(`/interview?scheduled_session_id=${sessionId}`);
  };

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
      setProfile({
        ...profile,
        ...payload,
      });
      setCompletion(Math.round(([
        payload.university,
        payload.degree,
        payload.graduation_year,
        payload.skills
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
    if (!newUsername || newUsername.length < 3) {
      setUsernameError('Username must be at least 3 characters');
      return;
    }
    setUsernameSaving(true);
    try {
      await apiClient.put('/users/username', { new_username: newUsername });
      setUsernameSuccess(true);
      setNewUsername('');
      setTimeout(() => setUsernameSuccess(false), 2500);
    } catch (err) {
      setUsernameError(err.response?.data?.detail || 'Failed to change username');
    } finally {
      setUsernameSaving(false);
    }
  };

  const handlePasswordChange = async (e) => {
    e.preventDefault();
    setPasswordError('');
    if (!currentPassword || !newPassword) {
      setPasswordError('Please fill in all password fields');
      return;
    }
    if (newPassword.length < 4) {
      setPasswordError('New password must be at least 4 characters');
      return;
    }
    if (newPassword !== confirmPassword) {
      setPasswordError('New passwords do not match');
      return;
    }
    setPasswordSaving(true);
    try {
      await apiClient.post('/users/change-password', {
        current_password: currentPassword,
        new_password: newPassword
      });
      setPasswordSuccess(true);
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setTimeout(() => setPasswordSuccess(false), 2500);
    } catch (err) {
      setPasswordError(err.response?.data?.detail || 'Failed to change password');
    } finally {
      setPasswordSaving(false);
    }
  };

  const handleClearInterviewData = async () => {
    if (!window.confirm('Are you absolutely sure? This will permanently delete ALL your interview sessions and reports. This action cannot be undone.')) {
      return;
    }

    try {
      setLoading(true);
      await apiClient.delete('/users/clear-interviews');
      setSessions([]);
      setStats(prev => ({
        ...prev,
        total_interviews: 0,
        completed_interviews: 0,
        avg_score: null,
        best_score: null
      }));
      alert('All interview data has been cleared.');
    } catch (err) {
      console.error('Clear data error:', err);
      const msg = err.response?.data?.detail || 'Failed to clear interview data. Please try again.';
      alert(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#020617] text-white font-sans">
      <div className="fixed top-0 right-0 w-[40%] h-[40%] bg-purple-600/5 blur-[150px] rounded-full pointer-events-none" />

      <div className="max-w-6xl mx-auto px-8 py-12 space-y-10 relative z-10">

        {/* Welcome */}
        <div>
          <h1 className="text-4xl font-black text-white tracking-tight">
            Welcome back, <span className="text-purple-400">{user?.first_name}</span>
          </h1>
          <p className="text-slate-500 mt-2">Review your progress, update your resume, and start your next interview when you are ready.</p>
        </div>

        {/* Stats row */}
        {!loading && stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: 'Total Sessions', val: stats.total_interviews ?? 0, icon: BarChart3, color: 'text-purple-400' },
              { label: 'Completed', val: stats.completed_interviews ?? 0, icon: CheckCircle2, color: 'text-emerald-400' },
              { label: 'Avg Score', val: stats.avg_score ? `${stats.avg_score}/10` : '—', icon: TrendingUp, color: 'text-blue-400' },
              { label: 'Best Score', val: stats.best_score ? `${stats.best_score}/10` : '—', icon: Award, color: 'text-amber-400' },
            ].map(s => (
              <div key={s.label} className="bg-white/2 border border-white/5 rounded-3xl p-6 flex items-center space-x-4">
                <div className="w-10 h-10 bg-white/5 rounded-2xl flex items-center justify-center">
                  <s.icon size={20} className={s.color} />
                </div>
                <div>
                  <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest">{s.label}</p>
                  <p className={`text-xl font-black ${s.color}`}>{s.val}</p>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Action cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">

          <motion.div
            whileHover={{ scale: 1.01 }}
            className={`bg-gradient-to-br from-purple-600/20 to-indigo-600/10 border rounded-[2rem] p-8 flex flex-col justify-between min-h-[200px] relative overflow-hidden group ${completion < 50 ? 'opacity-80 cursor-not-allowed' : ''}`}
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

          <div className="bg-white/2 border border-white/5 rounded-[2rem] p-8 flex flex-col justify-between min-h-[200px]">
            <div>
              <div className="w-12 h-12 bg-white/5 border border-white/10 rounded-2xl flex items-center justify-center mb-4">
                <FileText size={22} className="text-slate-400" />
              </div>
              <h2 className="text-2xl font-black text-white mb-1">Resume</h2>
              <p className="text-slate-400 text-sm">
                {resumeName
                  ? `Uploaded: ${resumeName}`
                  : 'Upload your resume so the AI can tailor questions to your experience.'}
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
            <input ref={fileRef} type="file" accept=".pdf" className="hidden" onChange={handleResumeUpload} />
          </div>

          <div className="bg-white/2 border border-white/5 rounded-[2rem] p-8 min-h-[200px] flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="text-2xl font-black text-white">Profile</h2>
                  <p className="text-slate-500 text-sm">Complete at least 50% to unlock interviews.</p>
                </div>
                <div className="flex gap-2">
                  <button onClick={() => {
                    setEditProfile({
                      // Academic
                      university: profile?.university ?? '',
                      degree: profile?.degree ?? '',
                      graduation_year: profile?.graduation_year ?? '',
                      gpa: profile?.gpa ?? '',
                      major: profile?.major ?? '',
                      minor: profile?.minor ?? '',
                      // Skills & Experience
                      skills: profile?.skills ?? '',
                      experience_level: profile?.experience_level ?? '',
                      work_experience: profile?.work_experience ?? '',
                      internships: profile?.internships ?? '',
                      // Additional
                      projects: profile?.projects ?? '',
                      certifications: profile?.certifications ?? '',
                      languages: profile?.languages ?? '',
                      linkedin_url: profile?.linkedin_url ?? '',
                      github_url: profile?.github_url ?? '',
                      portfolio_url: profile?.portfolio_url ?? '',
                      hackathons: profile?.hackathons ?? '',
                      // Preferences
                      expected_salary: profile?.expected_salary ?? '',
                      preferred_locations: profile?.preferred_locations ?? '',
                      availability: profile?.availability ?? '',
                      interests: profile?.interests ?? '',
                    });
                    setProfileModalOpen(true);
                  }}
                    className="bg-purple-600 text-white px-4 py-2 rounded-2xl text-sm font-bold hover:bg-purple-500 transition-all">
                    Edit
                  </button>
                  <button onClick={() => setAccountSettingsOpen(true)}
                    className="bg-white/5 border border-white/10 text-white px-4 py-2 rounded-2xl text-sm font-bold hover:bg-white/10 transition-all">
                    Account
                  </button>
                </div>
              </div>
              <div className="space-y-3">
                <div className="text-slate-400 text-sm">Completion</div>
                <div className="text-3xl font-black text-white">{completion}%</div>
              </div>
            </div>
            {completion < 50 ? (
              <p className="text-slate-400 text-sm mt-4">Add more profile details before starting interviews.</p>
            ) : (
              <p className="text-emerald-400 text-sm mt-4">Profile is complete enough to use the platform.</p>
            )}
            
            {/* Clear Data Action */}
            <div className="mt-8 pt-6 border-t border-white/5">
              <button 
                onClick={handleClearInterviewData}
                className="flex items-center space-x-2 text-slate-500 hover:text-red-400 transition-colors text-xs font-black uppercase tracking-widest"
              >
                <Trash2 size={14} />
                <span>Clear Interview Data</span>
              </button>
            </div>
          </div>
        </div>

        {profileModalOpen && (
          <div className="fixed inset-0 z-[200] bg-black/70 flex items-center justify-center p-4">
            <div className="bg-[#0f172a] border border-white/10 rounded-[2rem] w-full max-w-2xl p-6 space-y-6 max-h-[90vh] overflow-y-auto">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-2xl font-black text-white">Edit Student Profile</h2>
                  <p className="text-slate-500 text-sm">Complete your profile to get personalized interview questions.</p>
                </div>
                <button onClick={() => setProfileModalOpen(false)} className="text-slate-400 hover:text-white">Close</button>
              </div>

              {/* Academic Section */}
              <div className="space-y-4">
                <h3 className="text-xs font-black uppercase text-purple-400 tracking-widest">Academic</h3>
                <div className="grid grid-cols-2 gap-4">
                  <input type="text" placeholder="University" value={editProfile.university} onChange={e => setEditProfile({...editProfile, university: e.target.value})} className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none" />
                  <input type="text" placeholder="Major (e.g. CS)" value={editProfile.major} onChange={e => setEditProfile({...editProfile, major: e.target.value})} className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none" />
                  <input type="text" placeholder="Degree (e.g. B.Sc. CS)" value={editProfile.degree} onChange={e => setEditProfile({...editProfile, degree: e.target.value})} className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none" />
                  <input type="text" placeholder="Minor" value={editProfile.minor} onChange={e => setEditProfile({...editProfile, minor: e.target.value})} className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none" />
                  <input type="number" placeholder="Graduation Year" value={editProfile.graduation_year} onChange={e => setEditProfile({...editProfile, graduation_year: e.target.value ? Number(e.target.value) : null})} className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none" />
                  <input type="number" step="0.01" placeholder="GPA (e.g. 3.8)" value={editProfile.gpa} onChange={e => setEditProfile({...editProfile, gpa: e.target.value ? Number(e.target.value) : null})} className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none" />
                </div>
              </div>

              {/* Skills & Experience Section */}
              <div className="space-y-4">
                <h3 className="text-xs font-black uppercase text-purple-400 tracking-widest">Skills & Experience</h3>
                <div className="grid grid-cols-2 gap-4">
                  <input type="text" placeholder="Technical Skills (Python, React, SQL)" value={editProfile.skills} onChange={e => setEditProfile({...editProfile, skills: e.target.value})} className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none col-span-2" />
                  <select value={editProfile.experience_level} onChange={e => setEditProfile({...editProfile, experience_level: e.target.value})} className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none">
                    <option value="">Experience Level</option>
                    <option value="entry">Entry Level</option>
                    <option value="mid">Mid Level</option>
                    <option value="senior">Senior Level</option>
                  </select>
                  <input type="text" placeholder="Availability (e.g. Immediately)" value={editProfile.availability} onChange={e => setEditProfile({...editProfile, availability: e.target.value})} className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none" />
                  <input type="text" placeholder="Work Experience (Company, Role, Years)" value={editProfile.work_experience} onChange={e => setEditProfile({...editProfile, work_experience: e.target.value})} className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none col-span-2" />
                  <input type="text" placeholder="Internships" value={editProfile.internships} onChange={e => setEditProfile({...editProfile, internships: e.target.value})} className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none col-span-2" />
                </div>
              </div>

              {/* Projects & Certifications Section */}
              <div className="space-y-4">
                <h3 className="text-xs font-black uppercase text-purple-400 tracking-widest">Projects & Certifications</h3>
                <div className="space-y-4">
                  <input type="text" placeholder="Projects (e.g. E-commerce site - React, Node)" value={editProfile.projects} onChange={e => setEditProfile({...editProfile, projects: e.target.value})} className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none" />
                  <input type="text" placeholder="Certifications (e.g. AWS Certified, Google Analytics)" value={editProfile.certifications} onChange={e => setEditProfile({...editProfile, certifications: e.target.value})} className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none" />
                  <input type="text" placeholder="Hackathons (e.g. HackMIT 2024, NASA Space Apps)" value={editProfile.hackathons} onChange={e => setEditProfile({...editProfile, hackathons: e.target.value})} className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none" />
                </div>
              </div>

              {/* Links Section */}
              <div className="space-y-4">
                <h3 className="text-xs font-black uppercase text-purple-400 tracking-widest">Links</h3>
                <div className="grid grid-cols-2 gap-4">
                  <input type="text" placeholder="LinkedIn URL" value={editProfile.linkedin_url} onChange={e => setEditProfile({...editProfile, linkedin_url: e.target.value})} className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none" />
                  <input type="text" placeholder="GitHub URL" value={editProfile.github_url} onChange={e => setEditProfile({...editProfile, github_url: e.target.value})} className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none" />
                  <input type="text" placeholder="Portfolio URL" value={editProfile.portfolio_url} onChange={e => setEditProfile({...editProfile, portfolio_url: e.target.value})} className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none col-span-2" />
                </div>
              </div>

              {/* Languages & Interests Section */}
              <div className="space-y-4">
                <h3 className="text-xs font-black uppercase text-purple-400 tracking-widest">Languages & Preferences</h3>
                <div className="grid grid-cols-2 gap-4">
                  <input type="text" placeholder="Languages (e.g. English-Native, Spanish-Intermediate)" value={editProfile.languages} onChange={e => setEditProfile({...editProfile, languages: e.target.value})} className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none" />
                  <input type="text" placeholder="Expected Salary" value={editProfile.expected_salary} onChange={e => setEditProfile({...editProfile, expected_salary: e.target.value})} className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none" />
                  <input type="text" placeholder="Preferred Locations (Remote, NYC, SF)" value={editProfile.preferred_locations} onChange={e => setEditProfile({...editProfile, preferred_locations: e.target.value})} className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none col-span-2" />
                  <input type="text" placeholder="Interests (e.g. AI, Web Dev, Systems)" value={editProfile.interests} onChange={e => setEditProfile({...editProfile, interests: e.target.value})} className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none col-span-2" />
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button onClick={() => setProfileModalOpen(false)} className="px-6 py-3 rounded-2xl border border-white/10 text-slate-300 hover:bg-white/5 transition-all">Cancel</button>
                <button onClick={() => handleProfileSave(editProfile)} className="px-6 py-3 rounded-2xl bg-purple-600 text-white font-bold hover:bg-purple-500 transition-all">Save Profile</button>
              </div>
            </div>
          </div>
        )}

        {/* Account Settings Modal */}
        {accountSettingsOpen && (
          <div className="fixed inset-0 z-[200] bg-black/70 flex items-center justify-center p-6">
            <div className="bg-[#0f172a] border border-white/10 rounded-[2rem] w-full max-w-xl p-8 space-y-8 max-h-[90vh] overflow-y-auto">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-2xl font-black text-white">Account Settings</h2>
                  <p className="text-slate-500 text-sm">Manage your username and password.</p>
                </div>
                <button onClick={() => setAccountSettingsOpen(false)} className="text-slate-400 hover:text-white">Close</button>
              </div>

              {/* Username Change */}
              <div className="border-t border-white/10 pt-6">
                <h3 className="text-lg font-bold text-white mb-2">Change Username</h3>
                <p className="text-slate-500 mb-4 text-sm">Current: <span className="text-purple-400 font-mono">@{user?.username}</span></p>
                {usernameSuccess ? (
                  <div className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 px-4 py-3 rounded-xl text-sm font-bold">
                    Username changed successfully!
                  </div>
                ) : (
                  <form onSubmit={handleUsernameChange} className="space-y-4">
                    {usernameError && (
                      <div className="bg-red-500/10 border border-red-500/20 text-red-400 px-4 py-2 rounded-xl text-sm">{usernameError}</div>
                    )}
                    <div>
                      <label className="block text-xs font-black uppercase text-slate-400 tracking-widest mb-1.5 ml-1">New Username</label>
                      <input
                        className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none transition-all"
                        placeholder="Enter new username"
                        value={newUsername}
                        onChange={e => setNewUsername(e.target.value)}
                      />
                    </div>
                    <button type="submit" disabled={usernameSaving}
                      className="flex items-center space-x-2 px-6 py-3 bg-white/10 hover:bg-white/20 border border-white/10 text-white rounded-xl font-bold text-sm transition-all disabled:opacity-50">
                      {usernameSaving && <Loader2 className="animate-spin" size={14} />}
                      <span>{usernameSaving ? 'Changing...' : 'Change Username'}</span>
                    </button>
                  </form>
                )}
              </div>

              {/* Password Change */}
              <div className="border-t border-white/10 pt-6">
                <h3 className="text-lg font-bold text-white mb-2">Change Password</h3>
                <p className="text-slate-500 mb-4 text-sm">Update your account password.</p>
                {passwordSuccess ? (
                  <div className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 px-4 py-3 rounded-xl text-sm font-bold">
                    Password changed successfully!
                  </div>
                ) : (
                  <form onSubmit={handlePasswordChange} className="space-y-4">
                    {passwordError && (
                      <div className="bg-red-500/10 border border-red-500/20 text-red-400 px-4 py-2 rounded-xl text-sm">{passwordError}</div>
                    )}
                    <div>
                      <label className="block text-xs font-black uppercase text-slate-400 tracking-widest mb-1.5 ml-1">Current Password</label>
                      <input
                        type="password"
                        className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none transition-all"
                        placeholder="Enter current password"
                        value={currentPassword}
                        onChange={e => setCurrentPassword(e.target.value)}
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-black uppercase text-slate-400 tracking-widest mb-1.5 ml-1">New Password</label>
                      <input
                        type="password"
                        className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none transition-all"
                        placeholder="Enter new password"
                        value={newPassword}
                        onChange={e => setNewPassword(e.target.value)}
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-black uppercase text-slate-400 tracking-widest mb-1.5 ml-1">Confirm New Password</label>
                      <input
                        type="password"
                        className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none transition-all"
                        placeholder="Confirm new password"
                        value={confirmPassword}
                        onChange={e => setConfirmPassword(e.target.value)}
                      />
                    </div>
                    <button type="submit" disabled={passwordSaving}
                      className="flex items-center space-x-2 px-6 py-3 bg-white/10 hover:bg-white/20 border border-white/10 text-white rounded-xl font-bold text-sm transition-all disabled:opacity-50">
                      {passwordSaving && <Loader2 className="animate-spin" size={14} />}
                      <span>{passwordSaving ? 'Changing...' : 'Change Password'}</span>
                    </button>
                  </form>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Past Sessions */}
        <div>
          <h2 className="text-xl font-black text-white mb-4 uppercase tracking-widest text-sm">Past Sessions</h2>
          {loading ? (
            <div className="flex justify-center py-12">
              <Loader2 className="animate-spin text-purple-500" size={36} />
            </div>
          ) : sessions.length === 0 ? (
            <div className="bg-white/2 border-2 border-dashed border-white/10 rounded-[2rem] p-16 text-center">
              <Clock size={36} className="text-slate-600 mx-auto mb-4" />
              <p className="text-slate-500 font-medium">No sessions yet. Start your first interview above.</p>
            </div>
          ) : (
            <div className="bg-white/2 border border-white/5 rounded-[2rem] overflow-hidden">
              <div className="px-8 py-4 border-b border-white/5 grid grid-cols-12 gap-4 text-[10px] font-black uppercase tracking-[0.2em] text-slate-500">
                <div className="col-span-3">Type</div>
                <div className="col-span-3">Status</div>
                <div className="col-span-2 text-center">Score</div>
                <div className="col-span-3">Date</div>
                <div className="col-span-1" />
              </div>
              <div className="divide-y divide-white/5">
                {sessions.map(s => (
                  <div key={s.id} className="px-8 py-5 grid grid-cols-12 gap-4 items-center hover:bg-white/2 transition-all group">
                    <div className="col-span-3">
                      <span className={`text-[10px] font-black uppercase tracking-widest px-3 py-1 rounded-full border ${
                        s.session_type === 'actual'
                          ? 'bg-purple-500/10 text-purple-400 border-purple-500/20'
                          : 'bg-white/5 text-slate-400 border-white/10'
                      }`}>
                        {s.session_type === 'actual' ? 'Scheduled' : 'Practice'}
                      </span>
                    </div>
                    <div className="col-span-3">
                      <span className={`text-[10px] font-black uppercase tracking-widest ${
                        s.status === 'completed' ? 'text-emerald-400' : 'text-amber-400'
                      }`}>
                        {s.status}
                      </span>
                    </div>
                    <div className="col-span-2 text-center">
                      <span className={`text-lg font-black ${s.overall_score ? scoreColor(s.overall_score) : 'text-slate-600'}`}>
                        {s.overall_score ? s.overall_score.toFixed(1) : '—'}
                      </span>
                    </div>
                    <div className="col-span-3 text-slate-500 text-xs font-bold">
                      {new Date(s.created_at).toLocaleDateString()}
                    </div>
                    <div className="col-span-1 text-right">
                      {s.status === 'completed' ? (
                        <button
                          onClick={() => handleViewReport(s.id)}
                          className="p-2 bg-white/5 border border-white/10 rounded-xl text-slate-400 hover:text-white hover:bg-purple-600 transition-all"
                        >
                          <ChevronRight size={16} />
                        </button>
                      ) : s.status === 'scheduled' ? (
                        <button
                          onClick={() => handleStartScheduledInterview(s.id)}
                          className="p-2 bg-purple-600 border border-purple-500 rounded-xl text-white hover:bg-purple-500 transition-all"
                        >
                          <Play size={16} />
                        </button>
                      ) : null}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default StudentDashboard;
