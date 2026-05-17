import { useState, useEffect, useCallback } from 'react';
import {
  Star,
  ThumbsUp,
  ThumbsDown,
  MessageSquare,
  Send,
  CheckCircle,
  AlertCircle,
  User,
  RefreshCcw,
  ChevronLeft
} from 'lucide-react';
import apiClient from '../services/api';
import { useNavigate, useParams } from 'react-router-dom';

const HRFeedback = () => {
  const navigate = useNavigate();
  const { sessionId } = useParams();

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [session, setSession] = useState(null);
  const [existingFeedback, setExistingFeedback] = useState(null);
  const [formData, setFormData] = useState({
    strengths: '',
    weaknesses: '',
    hire_recommendation: '',
    notes: '',
    rating: 0,
  });

  const hireOptions = [
    { value: 'Strong Yes', color: 'bg-emerald-600', icon: ThumbsUp },
    { value: 'Yes', color: 'bg-emerald-500', icon: ThumbsUp },
    { value: 'No', color: 'bg-red-500', icon: ThumbsDown },
    { value: 'Strong No', color: 'bg-red-600', icon: ThumbsDown },
  ];

  const fetchSession = useCallback(async () => {
    try {
      setLoading(true);
      const res = await apiClient.get(`/hr/interviews/${sessionId}`);
      setSession(res.data);
    } catch {
      setError('Failed to fetch interview details');
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  const fetchExistingFeedback = useCallback(async () => {
    try {
      const res = await apiClient.get(`/hr/feedback/hr/${sessionId}`);
      setExistingFeedback(res.data);
      setFormData({
        strengths: res.data.strengths || '',
        weaknesses: res.data.weaknesses || '',
        hire_recommendation: res.data.hire_recommendation || '',
        notes: res.data.notes || '',
        rating: res.data.rating || 0,
      });
    } catch {
      // No existing feedback, that's fine
    }
  }, [sessionId]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchSession();
    fetchExistingFeedback();
  }, [fetchSession, fetchExistingFeedback]);

  const handleChange = (key, value) => {
    setFormData(prev => ({ ...prev, [key]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (formData.hire_recommendation === '') {
      setError('Please select a hire recommendation');
      return;
    }

    try {
      setSubmitting(true);
      setError('');
      setSuccess('');

      await apiClient.post('/hr/feedback/hr', {
        session_id: parseInt(sessionId),
        candidate_id: session?.candidate_id,
        ...formData,
      });

      setSuccess(existingFeedback ? 'Feedback updated successfully' : 'Feedback submitted successfully');
      fetchExistingFeedback();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to submit feedback');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#020617] flex items-center justify-center">
        <div className="text-center">
          <RefreshCcw size={32} className="animate-spin text-purple-400 mx-auto mb-4" />
          <p className="text-slate-400">Loading interview details...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#020617] text-white">
      <div className="max-w-4xl mx-auto px-8 py-10">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div className="flex items-center space-x-4">
            <button
              onClick={() => navigate(-1)}
              className="flex items-center space-x-2 bg-white/5 border border-white/10 text-slate-300 px-4 py-2 rounded-xl text-sm font-bold hover:bg-white/10 transition-all"
            >
              <ChevronLeft size={16} />
              <span>Back</span>
            </button>
            <div>
              <h1 className="text-3xl font-extrabold tracking-tight">HR Feedback</h1>
              <p className="text-slate-500 mt-1">
                {session?.candidate_name || 'Candidate'} - {session?.job_role || 'Interview'}
              </p>
            </div>
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
            <CheckCircle size={16} className="mr-2" />
            {success}
          </div>
        )}

        {/* Candidate Info */}
        {session && (
          <div className="mb-8 bg-white/2 border border-white/5 rounded-3xl p-6">
            <h2 className="font-bold text-white mb-4 flex items-center">
              <User className="mr-2 text-purple-400" size={20} />
              Candidate Information
            </h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Name</p>
                <p className="text-sm font-bold text-white">{session.candidate_name}</p>
              </div>
              <div>
                <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Email</p>
                <p className="text-sm font-bold text-white">{session.candidate_email}</p>
              </div>
              <div>
                <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Score</p>
                <p className={`text-sm font-bold ${
                  session.overall_score >= 8 ? 'text-emerald-400' :
                  session.overall_score >= 5 ? 'text-amber-400' : 'text-red-400'
                }`}>
                  {session.overall_score ? session.overall_score.toFixed(1) : 'N/A'}
                </p>
              </div>
              <div>
                <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Status</p>
                <p className="text-sm font-bold text-white capitalize">{session.status}</p>
              </div>
            </div>
          </div>
        )}

        {/* Feedback Form */}
        <form onSubmit={handleSubmit} className="space-y-8">
          {/* Rating */}
          <div className="bg-white/2 border border-white/5 rounded-3xl p-6">
            <h2 className="font-bold text-white mb-4 flex items-center">
              <Star className="mr-2 text-amber-400" size={20} />
              Your Rating
            </h2>
            <div className="flex space-x-2">
              {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((star) => (
                <button
                  key={star}
                  type="button"
                  onClick={() => handleChange('rating', star)}
                  className={`w-10 h-10 rounded-xl text-sm font-bold transition-all ${
                    formData.rating >= star
                      ? 'bg-amber-500 text-white'
                      : 'bg-white/5 text-slate-500 hover:bg-white/10'
                  }`}
                >
                  {star}
                </button>
              ))}
            </div>
          </div>

          {/* Hire Recommendation */}
          <div className="bg-white/2 border border-white/5 rounded-3xl p-6">
            <h2 className="font-bold text-white mb-4 flex items-center">
              <ThumbsUp className="mr-2 text-emerald-400" size={20} />
              Hire Recommendation
            </h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {hireOptions.map((option) => (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => handleChange('hire_recommendation', option.value)}
                  className={`py-3 rounded-xl text-sm font-bold transition-all flex items-center justify-center space-x-2 ${
                    formData.hire_recommendation === option.value
                      ? `${option.color} text-white`
                      : 'bg-white/5 text-slate-400 hover:bg-white/10'
                  }`}
                >
                  <option.icon size={16} />
                  <span>{option.value}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Strengths */}
          <div className="bg-white/2 border border-white/5 rounded-3xl p-6">
            <h2 className="font-bold text-white mb-4 flex items-center">
              <ThumbsUp className="mr-2 text-emerald-400" size={20} />
              Strengths
            </h2>
            <textarea
              value={formData.strengths}
              onChange={(e) => handleChange('strengths', e.target.value)}
              rows={3}
              className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-slate-500 focus:ring-1 focus:ring-purple-500 outline-none resize-none"
              placeholder="What were the candidate's key strengths?"
            />
          </div>

          {/* Weaknesses */}
          <div className="bg-white/2 border border-white/5 rounded-3xl p-6">
            <h2 className="font-bold text-white mb-4 flex items-center">
              <ThumbsDown className="mr-2 text-red-400" size={20} />
              Areas for Improvement
            </h2>
            <textarea
              value={formData.weaknesses}
              onChange={(e) => handleChange('weaknesses', e.target.value)}
              rows={3}
              className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-slate-500 focus:ring-1 focus:ring-purple-500 outline-none resize-none"
              placeholder="What areas could the candidate improve?"
            />
          </div>

          {/* Notes */}
          <div className="bg-white/2 border border-white/5 rounded-3xl p-6">
            <h2 className="font-bold text-white mb-4 flex items-center">
              <MessageSquare className="mr-2 text-violet-400" size={20} />
              Additional Notes
            </h2>
            <textarea
              value={formData.notes}
              onChange={(e) => handleChange('notes', e.target.value)}
              rows={4}
              className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-slate-500 focus:ring-1 focus:ring-purple-500 outline-none resize-none"
              placeholder="Any additional observations or notes..."
            />
          </div>

          {/* Submit */}
          <div className="flex justify-end space-x-3">
            <button
              type="button"
              onClick={() => navigate(-1)}
              className="px-6 py-3 bg-white/5 hover:bg-white/10 text-slate-400 rounded-xl text-sm font-bold transition-all"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="flex items-center space-x-2 px-6 py-3 bg-purple-600 hover:bg-purple-500 text-white rounded-xl text-sm font-bold shadow-lg shadow-purple-900/30 transition-all active:scale-95 disabled:opacity-50"
            >
              <Send size={16} />
              <span>{submitting ? 'Submitting...' : existingFeedback ? 'Update Feedback' : 'Submit Feedback'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default HRFeedback;
