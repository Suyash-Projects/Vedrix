import { useState } from 'react';
import {
  Star,
  ThumbsUp,
  ThumbsDown,
  Clock,
  Send,
  CheckCircle,
  AlertCircle
} from 'lucide-react';
import apiClient from '../services/api';
import { useNavigate, useSearchParams } from 'react-router-dom';

const FeedbackSurvey = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const sessionId = searchParams.get('session_id');
  const candidateId = searchParams.get('candidate_id');

  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState('');
  const [formData, setFormData] = useState({
    rating: 0,
    questions_relevant: '',
    interview_length: '',
    would_recommend: '',
    additional_feedback: '',
  });

  const handleRatingChange = (rating) => {
    setFormData(prev => ({ ...prev, rating }));
  };

  const handleChange = (key, value) => {
    setFormData(prev => ({ ...prev, [key]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (formData.rating === 0) {
      setError('Please select a rating');
      return;
    }

    try {
      setLoading(true);
      setError('');

      await apiClient.post('/hr/feedback/candidate', {
        session_id: parseInt(sessionId),
        candidate_id: parseInt(candidateId),
        ...formData,
      });

      setSubmitted(true);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to submit feedback');
    } finally {
      setLoading(false);
    }
  };

  if (submitted) {
    return (
      <div className="min-h-screen bg-[#020617] flex items-center justify-center px-4">
        <div className="bg-white/2 border border-white/5 rounded-3xl p-12 max-w-md w-full text-center">
          <CheckCircle size={48} className="text-emerald-400 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-white mb-2">Thank You!</h2>
          <p className="text-slate-400 mb-6">
            Your feedback helps us improve the interview experience for future candidates.
          </p>
          <button
            onClick={() => navigate('/dashboard')}
            className="px-6 py-3 bg-purple-600 hover:bg-purple-500 text-white rounded-xl text-sm font-bold shadow-lg shadow-purple-900/30 transition-all active:scale-95"
          >
            Go to Dashboard
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#020617] flex items-center justify-center px-4 py-16">
      <div className="bg-white/2 border border-white/5 rounded-3xl p-8 max-w-2xl w-full">
        <div className="mb-8">
          <h1 className="text-3xl font-extrabold tracking-tight text-white">Interview Feedback</h1>
          <p className="text-slate-500 mt-2">Help us improve by sharing your experience</p>
        </div>

        {error && (
          <div className="mb-6 p-4 rounded-xl text-sm font-bold border bg-red-500/10 border-red-500/20 text-red-400 flex items-center">
            <AlertCircle size={16} className="mr-2" />
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-8">
          {/* Rating */}
          <div>
            <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500 mb-3">
              How would you rate your interview experience?
            </label>
            <div className="flex space-x-2">
              {[1, 2, 3, 4, 5].map((star) => (
                <button
                  key={star}
                  type="button"
                  onClick={() => handleRatingChange(star)}
                  className={`p-2 rounded-xl transition-all ${
                    formData.rating >= star
                      ? 'text-amber-400 bg-amber-500/10'
                      : 'text-slate-600 hover:text-slate-400'
                  }`}
                >
                  <Star size={32} fill={formData.rating >= star ? 'currentColor' : 'none'} />
                </button>
              ))}
            </div>
          </div>

          {/* Questions Relevant */}
          <div>
            <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500 mb-3">
              Were the questions relevant to the role?
            </label>
            <div className="flex space-x-3">
              {['Yes', 'No', 'Somewhat'].map((option) => (
                <button
                  key={option}
                  type="button"
                  onClick={() => handleChange('questions_relevant', option)}
                  className={`flex-1 py-3 rounded-xl text-sm font-bold transition-all ${
                    formData.questions_relevant === option
                      ? 'bg-purple-600 text-white'
                      : 'bg-white/5 text-slate-400 hover:bg-white/10'
                  }`}
                >
                  {option}
                </button>
              ))}
            </div>
          </div>

          {/* Interview Length */}
          <div>
            <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500 mb-3">
              Was the interview length appropriate?
            </label>
            <div className="flex space-x-3">
              {[
                { value: 'Too short', icon: Clock },
                { value: 'Just right', icon: CheckCircle },
                { value: 'Too long', icon: AlertCircle },
              ].map((option) => (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => handleChange('interview_length', option.value)}
                  className={`flex-1 py-3 rounded-xl text-sm font-bold transition-all flex items-center justify-center space-x-2 ${
                    formData.interview_length === option.value
                      ? 'bg-purple-600 text-white'
                      : 'bg-white/5 text-slate-400 hover:bg-white/10'
                  }`}
                >
                  <option.icon size={16} />
                  <span>{option.value}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Would Recommend */}
          <div>
            <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500 mb-3">
              Would you recommend this interview process?
            </label>
            <div className="flex space-x-3">
              <button
                type="button"
                onClick={() => handleChange('would_recommend', true)}
                className={`flex-1 py-3 rounded-xl text-sm font-bold transition-all flex items-center justify-center space-x-2 ${
                  formData.would_recommend === true
                    ? 'bg-emerald-600 text-white'
                    : 'bg-white/5 text-slate-400 hover:bg-white/10'
                }`}
              >
                <ThumbsUp size={16} />
                <span>Yes</span>
              </button>
              <button
                type="button"
                onClick={() => handleChange('would_recommend', false)}
                className={`flex-1 py-3 rounded-xl text-sm font-bold transition-all flex items-center justify-center space-x-2 ${
                  formData.would_recommend === false
                    ? 'bg-red-600 text-white'
                    : 'bg-white/5 text-slate-400 hover:bg-white/10'
                }`}
              >
                <ThumbsDown size={16} />
                <span>No</span>
              </button>
            </div>
          </div>

          {/* Additional Feedback */}
          <div>
            <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500 mb-1.5">
              Any additional feedback?
            </label>
            <textarea
              value={formData.additional_feedback}
              onChange={(e) => handleChange('additional_feedback', e.target.value)}
              rows={4}
              className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-slate-500 focus:ring-1 focus:ring-purple-500 outline-none resize-none"
              placeholder="Share your thoughts..."
            />
          </div>

          {/* Submit */}
          <div className="flex justify-end">
            <button
              type="submit"
              disabled={loading}
              className="flex items-center space-x-2 px-6 py-3 bg-purple-600 hover:bg-purple-500 text-white rounded-xl text-sm font-bold shadow-lg shadow-purple-900/30 transition-all active:scale-95 disabled:opacity-50"
            >
              <Send size={16} />
              <span>{loading ? 'Submitting...' : 'Submit Feedback'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default FeedbackSurvey;
