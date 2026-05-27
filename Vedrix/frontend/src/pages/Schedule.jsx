import { useState, useEffect, useCallback } from 'react';
import {
  Calendar,
  Clock,
  User,
  Briefcase,
  ChevronLeft,
  ChevronRight,
  Plus,
  X,
  Check,
  AlertCircle
} from 'lucide-react';
import apiClient from '../services/api';
import { useNavigate } from 'react-router-dom';

const Schedule = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [drives, setDrives] = useState([]);
  const [interviews, setInterviews] = useState([]);
  const [currentDate, setCurrentDate] = useState(new Date());
  const [showModal, setShowModal] = useState(false);
  const [selectedDate, setSelectedDate] = useState(null);
  const [formData, setFormData] = useState({
    drive_id: '',
    candidate_email: '',
    scheduled_time: '',
    notes: '',
  });
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState('');

  const fetchDrives = useCallback(async () => {
    try {
      const res = await apiClient.get('/hr/drives');
      setDrives(res.data);
    } catch {
      setError('Failed to fetch drives');
    }
  }, []);

  const fetchInterviews = useCallback(async () => {
    try {
      const res = await apiClient.get('/hr/interviews');
      const allInterviews = Array.isArray(res.data) ? res.data : (res.data?.interviews ?? []);
      setInterviews(allInterviews);
    } catch {
      setError('Failed to fetch interviews');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchDrives();
    fetchInterviews();
  }, [fetchDrives, fetchInterviews]);

  const getDaysInMonth = (date) => {
    const year = date.getFullYear();
    const month = date.getMonth();
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const daysInMonth = lastDay.getDate();
    const startDayOfWeek = firstDay.getDay();

    const days = [];
    // Add empty cells for days before the first day of the month
    for (let i = 0; i < startDayOfWeek; i++) {
      days.push(null);
    }
    // Add days of the month
    for (let i = 1; i <= daysInMonth; i++) {
      days.push(new Date(year, month, i));
    }
    return days;
  };

  const getLocalDateString = (d) => {
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  };

  const getInterviewsForDate = (date) => {
    if (!date) return [];
    const dateStr = getLocalDateString(date);
    return interviews.filter(interview => {
      if (!interview.scheduled_time) return false;
      const interviewDate = getLocalDateString(new Date(interview.scheduled_time));
      return interviewDate === dateStr;
    });
  };

  const handlePrevMonth = () => {
    setCurrentDate(prev => new Date(prev.getFullYear(), prev.getMonth() - 1, 1));
  };

  const handleNextMonth = () => {
    setCurrentDate(prev => new Date(prev.getFullYear(), prev.getMonth() + 1, 1));
  };

  const handleDateClick = (date) => {
    if (date) {
      setSelectedDate(date);
      setFormData(prev => ({
        ...prev,
        scheduled_time: getLocalDateString(date) + 'T10:00',
      }));
      setShowModal(true);
    }
  };

  const handleScheduleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.drive_id || !formData.candidate_email || !formData.scheduled_time) {
      setError('All fields are required');
      return;
    }

    try {
      setSubmitting(true);
      setError('');
      setSuccess('');

      await apiClient.post('/hr/interviews/schedule', {
        drive_id: parseInt(formData.drive_id),
        candidate_email: formData.candidate_email,
        scheduled_time: formData.scheduled_time,
        notes: formData.notes,
      });

      setSuccess('Interview scheduled successfully');
      setShowModal(false);
      setFormData({ drive_id: '', candidate_email: '', scheduled_time: '', notes: '' });
      fetchInterviews();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to schedule interview');
    } finally {
      setSubmitting(false);
    }
  };

  const monthNames = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
  ];
  const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

  const days = getDaysInMonth(currentDate);
  const today = new Date();

  if (loading) {
    return (
      <div className="min-h-screen bg-[#020617] flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin text-purple-400 mx-auto mb-4">
            <Calendar size={32} />
          </div>
          <p className="text-slate-400">Loading calendar...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#020617] text-white">
      <div className="max-w-7xl mx-auto px-8 py-10">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight">Interview Schedule</h1>
            <p className="text-slate-500 mt-1">Manage and schedule upcoming interviews</p>
          </div>
          <div className="flex items-center space-x-3">
            <button
              onClick={() => navigate('/hr')}
              className="flex items-center space-x-2 bg-white/5 border border-white/10 text-slate-300 px-4 py-2 rounded-xl text-sm font-bold hover:bg-white/10 transition-all"
            >
              <span>Back to HR</span>
            </button>
          </div>
        </div>

        {error && (
          <div className="mb-6 p-4 rounded-xl text-sm font-bold border bg-red-500/10 border-red-500/20 text-red-400 flex items-center">
            <AlertCircle size={16} className="mr-2" />
            {error}
          </div>
        )}

        {success && (
          <div className="mb-6 p-4 rounded-xl text-sm font-bold border bg-emerald-500/10 border-emerald-500/20 text-emerald-400 flex items-center">
            <Check size={16} className="mr-2" />
            {success}
          </div>
        )}

        {/* Calendar Navigation */}
        <div className="bg-white/2 border border-white/5 rounded-3xl overflow-hidden">
          <div className="px-8 py-6 border-b border-white/5 flex justify-between items-center">
            <button
              onClick={handlePrevMonth}
              className="p-2 rounded-lg hover:bg-white/5 transition-colors"
            >
              <ChevronLeft size={20} />
            </button>
            <h2 className="text-xl font-bold">
              {monthNames[currentDate.getMonth()]} {currentDate.getFullYear()}
            </h2>
            <button
              onClick={handleNextMonth}
              className="p-2 rounded-lg hover:bg-white/5 transition-colors"
            >
              <ChevronRight size={20} />
            </button>
          </div>

          {/* Day Names Header */}
          <div className="grid grid-cols-7 border-b border-white/5">
            {dayNames.map(day => (
              <div key={day} className="py-3 text-center text-[10px] font-black text-slate-500 uppercase tracking-widest">
                {day}
              </div>
            ))}
          </div>

          {/* Calendar Grid */}
          <div className="grid grid-cols-7">
            {days.map((date, idx) => {
              if (!date) {
                return <div key={`empty-${idx}`} className="min-h-24 border-b border-r border-white/5" />;
              }

              const isToday = date.toDateString() === today.toDateString();
              const dayInterviews = getInterviewsForDate(date);
              const hasInterviews = dayInterviews.length > 0;

              return (
                <div
                  key={date.toISOString()}
                  onClick={() => handleDateClick(date)}
                  className={`min-h-24 border-b border-r border-white/5 p-2 cursor-pointer transition-colors hover:bg-white/5 ${
                    isToday ? 'bg-purple-500/10' : ''
                  }`}
                >
                  <div className="flex justify-between items-start">
                    <span className={`text-sm font-bold ${
                      isToday ? 'text-purple-400' : 'text-slate-400'
                    }`}>
                      {date.getDate()}
                    </span>
                    {hasInterviews && (
                      <span className="w-2 h-2 bg-emerald-400 rounded-full" />
                    )}
                  </div>
                  {hasInterviews && (
                    <div className="mt-1 space-y-1">
                      {dayInterviews.slice(0, 2).map((interview, i) => (
                        <div
                          key={i}
                          className="text-[10px] bg-emerald-500/20 text-emerald-400 px-1.5 py-0.5 rounded truncate"
                          title={`${interview.candidate_name} - ${interview.job_role}`}
                        >
                          {interview.candidate_name?.split(' ')[0] || 'Candidate'}
                        </div>
                      ))}
                      {dayInterviews.length > 2 && (
                        <div className="text-[10px] text-slate-500">+{dayInterviews.length - 2} more</div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Upcoming Interviews */}
        <div className="mt-8 bg-white/2 border border-white/5 rounded-3xl overflow-hidden">
          <div className="px-8 py-6 border-b border-white/5">
            <h2 className="font-bold text-white flex items-center">
              <Clock className="mr-2 text-amber-400" size={20} />
              Upcoming Interviews
            </h2>
          </div>
          {interviews.filter(i => i.scheduled_time && new Date(i.scheduled_time) >= today).length === 0 ? (
            <div className="p-12 text-center text-slate-500">No upcoming interviews scheduled.</div>
          ) : (
            <div className="divide-y divide-white/5">
              {interviews
                .filter(i => i.scheduled_time && new Date(i.scheduled_time) >= today)
                .sort((a, b) => new Date(a.scheduled_time) - new Date(b.scheduled_time))
                .slice(0, 10)
                .map((interview) => (
                  <div key={interview.id} className="px-8 py-4 flex items-center justify-between hover:bg-white/5 transition-colors">
                    <div className="flex items-center space-x-4">
                      <div className="w-10 h-10 bg-white/5 rounded-full flex items-center justify-center">
                        <User size={16} className="text-slate-400" />
                      </div>
                      <div>
                        <p className="font-bold text-white text-sm">{interview.candidate_name}</p>
                        <p className="text-xs text-slate-500">{interview.candidate_email}</p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-4">
                      <div className="text-right">
                        <p className="text-xs text-slate-400 flex items-center">
                          <Briefcase size={12} className="mr-1" />
                          {interview.job_role}
                        </p>
                        <p className="text-xs text-slate-500 flex items-center">
                          <Calendar size={12} className="mr-1" />
                          {new Date(interview.scheduled_time).toLocaleDateString()} at{' '}
                          {new Date(interview.scheduled_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </p>
                      </div>
                      <button
                        onClick={() => navigate(`/hr/feedback/${interview.id}`)}
                        className="text-slate-500 hover:text-purple-400 p-1.5 rounded-lg hover:bg-purple-500/10 transition-colors"
                        title="View feedback"
                      >
                        <ChevronRight size={16} />
                      </button>
                    </div>
                  </div>
                ))}
            </div>
          )}
        </div>

        {/* Schedule Modal */}
        {showModal && selectedDate && (
          <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-[200]">
            <div className="bg-[#0f1420] border border-white/10 rounded-3xl p-8 w-full max-w-md mx-4 shadow-2xl">
              <div className="flex justify-between items-center mb-6">
                <h3 className="text-xl font-bold text-white">
                  Schedule Interview - {selectedDate.toLocaleDateString()}
                </h3>
                <button onClick={() => setShowModal(false)} className="text-slate-500 hover:text-white">
                  <X size={20} />
                </button>
              </div>

              <form onSubmit={handleScheduleSubmit} className="space-y-4">
                <div>
                  <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500 mb-1.5">
                    Job Drive
                  </label>
                  <select
                    value={formData.drive_id}
                    onChange={(e) => setFormData(prev => ({ ...prev, drive_id: e.target.value }))}
                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:ring-1 focus:ring-purple-500 outline-none"
                    required
                  >
                    <option value="">Select a drive...</option>
                    {drives.map(drive => (
                      <option key={drive.id} value={drive.id}>{drive.title}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500 mb-1.5">
                    Candidate Email
                  </label>
                  <input
                    type="email"
                    value={formData.candidate_email}
                    onChange={(e) => setFormData(prev => ({ ...prev, candidate_email: e.target.value }))}
                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-slate-500 focus:ring-1 focus:ring-purple-500 outline-none"
                    placeholder="candidate@example.com"
                    required
                  />
                </div>

                <div>
                  <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500 mb-1.5">
                    Scheduled Time
                  </label>
                  <input
                    type="datetime-local"
                    value={formData.scheduled_time}
                    onChange={(e) => setFormData(prev => ({ ...prev, scheduled_time: e.target.value }))}
                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:ring-1 focus:ring-purple-500 outline-none"
                    required
                  />
                </div>

                <div>
                  <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500 mb-1.5">
                    Notes (Optional)
                  </label>
                  <textarea
                    value={formData.notes}
                    onChange={(e) => setFormData(prev => ({ ...prev, notes: e.target.value }))}
                    rows={3}
                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-slate-500 focus:ring-1 focus:ring-purple-500 outline-none resize-none"
                    placeholder="Additional notes..."
                  />
                </div>

                <div className="flex justify-end space-x-3 pt-2">
                  <button
                    type="button"
                    onClick={() => setShowModal(false)}
                    className="px-6 py-3 bg-white/5 hover:bg-white/10 text-slate-400 rounded-xl text-sm font-bold transition-all"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={submitting}
                    className="flex items-center space-x-2 px-6 py-3 bg-purple-600 hover:bg-purple-500 text-white rounded-xl text-sm font-bold shadow-lg shadow-purple-900/30 transition-all active:scale-95 disabled:opacity-50"
                  >
                    <Plus size={16} />
                    <span>{submitting ? 'Scheduling...' : 'Schedule Interview'}</span>
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

export default Schedule;
