import { useState, useEffect, useCallback, useMemo } from 'react';
import { motion } from 'framer-motion';
import {
  User, Mail, Shield, Building2, GraduationCap, Briefcase, Award,
  Link2, GitBranch, Globe, MapPin, Calendar, Edit3, Save, X,
  CheckCircle2, AlertCircle, Loader2, Sparkles, BookOpen, Code2,
} from 'lucide-react';
import apiClient from '../services/api';
import useAuthStore from '../store/useAuthStore';

const fadeUp = {
  hidden: { opacity: 0, y: 18 },
  visible: (i = 0) => ({ opacity: 1, y: 0, transition: { delay: i * 0.06, duration: 0.45, ease: 'easeOut' } }),
};

/* ── Reusable field display ── */
const Field = ({ icon: Icon, label, value, href }) => {
  const isEmpty = value === null || value === undefined || String(value).trim() === '';
  const content = isEmpty ? <span className="text-slate-600 italic">Not provided</span> : value;
  return (
    <div className="flex items-start gap-3 py-3 border-b border-white/5 last:border-0">
      {Icon && (
        <div className="w-9 h-9 shrink-0 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center text-purple-400">
          <Icon size={16} />
        </div>
      )}
      <div className="min-w-0 flex-1">
        <p className="text-[10px] font-black uppercase tracking-widest text-slate-500">{label}</p>
        {href && !isEmpty ? (
          <a href={href} target="_blank" rel="noopener noreferrer"
            className="text-sm font-bold text-purple-300 hover:text-purple-200 break-words transition-colors">
            {content}
          </a>
        ) : (
          <p className="text-sm font-bold text-white break-words">{content}</p>
        )}
      </div>
    </div>
  );
};

/* ── Editable input ── */
const EditField = ({ label, name, value, onChange, type = 'text', placeholder, textarea }) => (
  <div>
    <label className="block text-[10px] font-black uppercase tracking-widest text-slate-400 mb-1.5">{label}</label>
    {textarea ? (
      <textarea
        name={name} value={value ?? ''} onChange={onChange} rows={3} placeholder={placeholder}
        className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none transition-all resize-none"
      />
    ) : (
      <input
        type={type} name={name} value={value ?? ''} onChange={onChange} placeholder={placeholder}
        className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none transition-all"
      />
    )}
  </div>
);

const SectionCard = ({ title, icon: Icon, children, custom }) => (
  <motion.section
    variants={fadeUp} initial="hidden" animate="visible" custom={custom}
    className="glass-card rounded-3xl p-6 sm:p-8"
  >
    <h2 className="text-xs font-black uppercase tracking-widest text-purple-400 mb-5 flex items-center gap-2">
      {Icon && <Icon size={15} />} {title}
    </h2>
    {children}
  </motion.section>
);

const SkeletonBlock = () => (
  <div className="space-y-6">
    <div className="glass-card rounded-3xl p-8 animate-pulse">
      <div className="flex items-center gap-5">
        <div className="w-20 h-20 rounded-2xl bg-white/5" />
        <div className="flex-1 space-y-3">
          <div className="h-5 bg-white/5 rounded w-1/3" />
          <div className="h-3 bg-white/5 rounded w-1/2" />
        </div>
      </div>
    </div>
    {[...Array(2)].map((_, i) => (
      <div key={i} className="glass-card rounded-3xl p-8 h-48 animate-pulse" />
    ))}
  </div>
);

const STUDENT_FIELDS = [
  'university', 'degree', 'graduation_year', 'gpa', 'major', 'minor',
  'skills', 'experience_level', 'work_experience', 'internships',
  'projects', 'certifications', 'languages', 'linkedin_url', 'github_url',
  'portfolio_url', 'hackathons', 'expected_salary', 'preferred_locations',
  'availability', 'interests',
];

const ProfilePage = () => {
  const { user } = useAuthStore();
  const role = user?.user_type;

  const [profile, setProfile] = useState(null);
  const [form, setForm] = useState({});
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [toast, setToast] = useState(null);

  const profileEndpoint = role === 'hr' ? '/hr/profile' : role === 'student' ? '/profiles/student' : null;

  const fetchProfile = useCallback(async () => {
    if (!profileEndpoint) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.get(profileEndpoint);
      setProfile(res.data || {});
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load profile data');
    } finally {
      setLoading(false);
    }
  }, [profileEndpoint]);

  useEffect(() => {
    Promise.resolve().then(() => fetchProfile());
  }, [fetchProfile]);

  const showToast = (type, message) => {
    setToast({ type, message });
    setTimeout(() => setToast(null), 3000);
  };

  const startEdit = () => {
    setForm({ ...(profile || {}) });
    setEditing(true);
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      if (role === 'student') {
        const payload = Object.entries(form).reduce((acc, [k, v]) => {
          if (STUDENT_FIELDS.includes(k) && v !== null && v !== undefined && String(v).trim() !== '') acc[k] = v;
          return acc;
        }, {});
        await apiClient.post('/profiles/student', payload);
      } else if (role === 'hr') {
        await apiClient.put('/hr/profile', form);
      }
      setProfile((prev) => ({ ...prev, ...form }));
      setEditing(false);
      showToast('success', 'Profile updated successfully');
    } catch (err) {
      showToast('error', err.response?.data?.detail || 'Failed to save profile');
    } finally {
      setSaving(false);
    }
  };

  const completion = useMemo(() => {
    if (role !== 'student' || !profile) return null;
    const required = [profile.university, profile.degree, profile.graduation_year, profile.skills];
    const filled = required.filter((f) => f !== null && f !== undefined && String(f).trim() !== '').length;
    return Math.round((filled / required.length) * 100);
  }, [profile, role]);

  const initials = `${user?.first_name?.[0] ?? ''}${user?.last_name?.[0] ?? ''}`.toUpperCase() || 'U';
  const roleLabel = role === 'hr' ? 'Recruiter' : role === 'admin' ? 'Administrator' : 'Candidate';

  return (
    <div className="min-h-screen bg-[#020617] text-white font-sans">
      {/* Ambient glow */}
      <div className="fixed top-0 right-0 w-[40%] h-[40%] bg-purple-600/5 blur-[150px] rounded-full pointer-events-none" />
      <div className="fixed bottom-0 left-0 w-[30%] h-[30%] bg-indigo-600/5 blur-[150px] rounded-full pointer-events-none" />

      {/* Toast */}
      {toast && (
        <motion.div
          initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }}
          className={`fixed top-24 left-1/2 -translate-x-1/2 z-[150] flex items-center gap-2 px-5 py-3 rounded-2xl border backdrop-blur-xl shadow-2xl ${
            toast.type === 'success'
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
              : 'bg-red-500/10 border-red-500/30 text-red-300'
          }`}
          role="status"
        >
          {toast.type === 'success' ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}
          <span className="text-sm font-bold">{toast.message}</span>
        </motion.div>
      )}

      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12 space-y-6 relative z-10">
        {loading ? (
          <SkeletonBlock />
        ) : error ? (
          <div className="glass-card rounded-3xl p-12 text-center space-y-4">
            <AlertCircle size={36} className="text-red-400 mx-auto" />
            <p className="text-red-400 text-lg font-bold">{error}</p>
            <button onClick={fetchProfile}
              className="inline-flex items-center gap-2 bg-purple-600 hover:bg-purple-500 text-white font-bold px-6 py-3 rounded-2xl transition-all">
              Retry
            </button>
          </div>
        ) : (
          <>
            {/* ── Header / Identity Card ── */}
            <motion.div
              variants={fadeUp} initial="hidden" animate="visible" custom={0}
              className="glass-card rounded-3xl p-6 sm:p-8"
            >
              <div className="flex flex-col sm:flex-row items-center sm:items-start gap-6">
                <div className="relative shrink-0">
                  <div className="w-24 h-24 rounded-3xl bg-gradient-to-tr from-purple-600 via-indigo-500 to-cyan-400 flex items-center justify-center text-white text-3xl font-black shadow-xl shadow-purple-900/30">
                    {initials}
                  </div>
                  {role === 'student' && completion !== null && (
                    <span className="absolute -bottom-2 -right-2 bg-[#0f172a] border border-white/10 rounded-full px-2.5 py-1 text-[10px] font-black text-purple-300">
                      {completion}%
                    </span>
                  )}
                </div>

                <div className="flex-1 min-w-0 text-center sm:text-left">
                  <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-3 justify-center sm:justify-start">
                    <h1 className="text-2xl sm:text-3xl font-black text-white tracking-tight truncate">
                      {user?.first_name} {user?.last_name}
                    </h1>
                    <span className="inline-flex items-center gap-1 self-center sm:self-auto px-3 py-1 rounded-full bg-purple-500/10 border border-purple-500/20 text-purple-300 text-[10px] font-black uppercase tracking-widest">
                      <Shield size={11} /> {roleLabel}
                    </span>
                  </div>
                  <div className="mt-3 flex flex-col sm:flex-row items-center sm:items-start gap-x-6 gap-y-1.5 text-sm text-slate-400">
                    <span className="inline-flex items-center gap-2"><Mail size={14} className="text-slate-500" /> {user?.email}</span>
                    <span className="inline-flex items-center gap-2"><User size={14} className="text-slate-500" /> @{user?.username}</span>
                  </div>
                </div>

                {profileEndpoint && (
                  <div className="shrink-0">
                    {editing ? (
                      <div className="flex gap-2">
                        <button onClick={() => setEditing(false)} disabled={saving}
                          className="inline-flex items-center gap-2 bg-white/5 border border-white/10 text-slate-300 font-bold px-4 py-2.5 rounded-2xl hover:bg-white/10 transition-all disabled:opacity-50">
                          <X size={16} /> Cancel
                        </button>
                        <button onClick={handleSave} disabled={saving}
                          className="inline-flex items-center gap-2 bg-purple-600 hover:bg-purple-500 text-white font-bold px-5 py-2.5 rounded-2xl shadow-lg shadow-purple-900/30 transition-all disabled:opacity-50">
                          {saving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />} Save
                        </button>
                      </div>
                    ) : (
                      <button onClick={startEdit}
                        className="inline-flex items-center gap-2 bg-purple-600 hover:bg-purple-500 text-white font-bold px-5 py-2.5 rounded-2xl shadow-lg shadow-purple-900/30 transition-all">
                        <Edit3 size={16} /> Edit Profile
                      </button>
                    )}
                  </div>
                )}
              </div>

              {role === 'student' && completion !== null && !editing && (
                <div className="mt-6 pt-6 border-t border-white/5">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[10px] font-black uppercase tracking-widest text-slate-500">Profile Completion</span>
                    <span className={`text-xs font-black ${completion >= 50 ? 'text-emerald-400' : 'text-amber-400'}`}>
                      {completion >= 50 ? 'Ready to interview' : 'Complete 50% to unlock interviews'}
                    </span>
                  </div>
                  <div className="h-2 bg-white/5 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-700 ${completion >= 50 ? 'bg-emerald-500' : 'bg-amber-500'}`}
                      style={{ width: `${completion}%` }}
                      role="progressbar" aria-valuenow={completion} aria-valuemin={0} aria-valuemax={100}
                    />
                  </div>
                </div>
              )}
            </motion.div>

            {/* ── Admin (no extended profile) ── */}
            {role === 'admin' && (
              <SectionCard title="Account" icon={Shield} custom={1}>
                <Field icon={User} label="Full Name" value={`${user?.first_name} ${user?.last_name}`} />
                <Field icon={Mail} label="Email" value={user?.email} />
                <Field icon={Shield} label="Role" value={roleLabel} />
                <p className="mt-4 text-xs text-slate-500">Administrator accounts manage the platform and don't have an extended public profile.</p>
              </SectionCard>
            )}

            {/* ── HR Profile ── */}
            {role === 'hr' && (
              editing ? (
                <SectionCard title="Recruiter Details" icon={Building2} custom={1}>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <EditField label="Company Name" name="company_name" value={form.company_name} onChange={handleChange} placeholder="Acme Corp" />
                    <EditField label="Position" name="position" value={form.position} onChange={handleChange} placeholder="Talent Lead" />
                    <EditField label="Department" name="department" value={form.department} onChange={handleChange} placeholder="People Ops" />
                  </div>
                </SectionCard>
              ) : (
                <SectionCard title="Recruiter Details" icon={Building2} custom={1}>
                  <Field icon={Building2} label="Company" value={profile?.company_name} />
                  <Field icon={Briefcase} label="Position" value={profile?.position} />
                  <Field icon={User} label="Department" value={profile?.department} />
                  {profile?.hr_code && <Field icon={Shield} label="HR Code" value={profile?.hr_code} />}
                </SectionCard>
              )
            )}

            {/* ── Student Profile ── */}
            {role === 'student' && (
              editing ? (
                <>
                  <SectionCard title="Academic Background" icon={GraduationCap} custom={1}>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <EditField label="University" name="university" value={form.university} onChange={handleChange} placeholder="MIT" />
                      <EditField label="Degree" name="degree" value={form.degree} onChange={handleChange} placeholder="B.Sc. Computer Science" />
                      <EditField label="Graduation Year" name="graduation_year" value={form.graduation_year} onChange={handleChange} placeholder="2026" />
                      <EditField label="GPA" name="gpa" value={form.gpa} onChange={handleChange} placeholder="3.8" />
                      <EditField label="Major" name="major" value={form.major} onChange={handleChange} placeholder="Software Engineering" />
                      <EditField label="Minor" name="minor" value={form.minor} onChange={handleChange} placeholder="Mathematics" />
                    </div>
                  </SectionCard>

                  <SectionCard title="Skills & Experience" icon={Code2} custom={2}>
                    <div className="grid grid-cols-1 gap-4">
                      <EditField label="Skills (comma separated)" name="skills" value={form.skills} onChange={handleChange} placeholder="React, Python, SQL" textarea />
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <EditField label="Experience Level" name="experience_level" value={form.experience_level} onChange={handleChange} placeholder="Entry / Mid / Senior" />
                        <EditField label="Languages" name="languages" value={form.languages} onChange={handleChange} placeholder="English, Spanish" />
                      </div>
                      <EditField label="Work Experience" name="work_experience" value={form.work_experience} onChange={handleChange} textarea />
                      <EditField label="Internships" name="internships" value={form.internships} onChange={handleChange} textarea />
                      <EditField label="Projects" name="projects" value={form.projects} onChange={handleChange} textarea />
                    </div>
                  </SectionCard>

                  <SectionCard title="Achievements & Links" icon={Award} custom={3}>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <EditField label="Certifications" name="certifications" value={form.certifications} onChange={handleChange} />
                      <EditField label="Hackathons" name="hackathons" value={form.hackathons} onChange={handleChange} />
                      <EditField label="LinkedIn URL" name="linkedin_url" value={form.linkedin_url} onChange={handleChange} placeholder="https://linkedin.com/in/..." />
                      <EditField label="GitHub URL" name="github_url" value={form.github_url} onChange={handleChange} placeholder="https://github.com/..." />
                      <EditField label="Portfolio URL" name="portfolio_url" value={form.portfolio_url} onChange={handleChange} placeholder="https://..." />
                      <EditField label="Interests" name="interests" value={form.interests} onChange={handleChange} />
                    </div>
                  </SectionCard>

                  <SectionCard title="Preferences" icon={Sparkles} custom={4}>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <EditField label="Expected Salary" name="expected_salary" value={form.expected_salary} onChange={handleChange} placeholder="$80,000" />
                      <EditField label="Availability" name="availability" value={form.availability} onChange={handleChange} placeholder="Immediate / 2 weeks" />
                      <EditField label="Preferred Locations" name="preferred_locations" value={form.preferred_locations} onChange={handleChange} placeholder="Remote, NYC" />
                    </div>
                  </SectionCard>
                </>
              ) : (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <SectionCard title="Academic Background" icon={GraduationCap} custom={1}>
                    <Field icon={BookOpen} label="University" value={profile?.university} />
                    <Field icon={GraduationCap} label="Degree" value={profile?.degree} />
                    <Field icon={Calendar} label="Graduation Year" value={profile?.graduation_year} />
                    <Field icon={Award} label="GPA" value={profile?.gpa} />
                    <Field icon={BookOpen} label="Major" value={profile?.major} />
                    <Field icon={BookOpen} label="Minor" value={profile?.minor} />
                  </SectionCard>

                  <SectionCard title="Skills & Experience" icon={Code2} custom={2}>
                    <Field icon={Code2} label="Skills" value={profile?.skills} />
                    <Field icon={Briefcase} label="Experience Level" value={profile?.experience_level} />
                    <Field icon={Globe} label="Languages" value={profile?.languages} />
                    <Field icon={Briefcase} label="Work Experience" value={profile?.work_experience} />
                    <Field icon={Briefcase} label="Internships" value={profile?.internships} />
                    <Field icon={Code2} label="Projects" value={profile?.projects} />
                  </SectionCard>

                  <SectionCard title="Achievements & Links" icon={Award} custom={3}>
                    <Field icon={Award} label="Certifications" value={profile?.certifications} />
                    <Field icon={Award} label="Hackathons" value={profile?.hackathons} />
                    <Field icon={Globe} label="LinkedIn" value={profile?.linkedin_url} href={profile?.linkedin_url} />
                    <Field icon={GitBranch} label="GitHub" value={profile?.github_url} href={profile?.github_url} />
                    <Field icon={Link2} label="Portfolio" value={profile?.portfolio_url} href={profile?.portfolio_url} />
                    <Field icon={Sparkles} label="Interests" value={profile?.interests} />
                  </SectionCard>

                  <SectionCard title="Preferences" icon={Sparkles} custom={4}>
                    <Field icon={Award} label="Expected Salary" value={profile?.expected_salary} />
                    <Field icon={Calendar} label="Availability" value={profile?.availability} />
                    <Field icon={MapPin} label="Preferred Locations" value={profile?.preferred_locations} />
                  </SectionCard>
                </div>
              )
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default ProfilePage;
