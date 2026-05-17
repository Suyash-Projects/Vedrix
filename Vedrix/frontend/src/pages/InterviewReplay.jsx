import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ChevronLeft, Play, Pause, SkipForward, SkipBack, FastForward,
  User, Bot, Award, Clock
} from 'lucide-react';
import apiClient from '../services/api';

/* ── Replay Content (re-mounts when sessionId changes via key) ── */
const ReplayContent = ({ data }) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);
  const playIntervalRef = useRef(null);

  // Auto-play functionality
  const startPlayback = useCallback(() => {
    setIsPlaying(true);
    const interval = setInterval(() => {
      setCurrentStep(prev => {
        if (!data || prev >= data.steps.length - 1) {
          clearInterval(interval);
          setIsPlaying(false);
          return prev;
        }
        return prev + 1;
      });
    }, 2000 / playbackSpeed);
    playIntervalRef.current = interval;
  }, [data, playbackSpeed]);

  const stopPlayback = useCallback(() => {
    setIsPlaying(false);
    if (playIntervalRef.current) {
      clearInterval(playIntervalRef.current);
      playIntervalRef.current = null;
    }
  }, []);

  const togglePlayback = () => {
    if (isPlaying) {
      stopPlayback();
    } else {
      startPlayback();
    }
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (playIntervalRef.current) {
        clearInterval(playIntervalRef.current);
      }
    };
  }, []);

  const handleNext = () => {
    if (data && currentStep < data.steps.length - 1) {
      setCurrentStep(prev => prev + 1);
    }
  };

  const handlePrev = () => {
    if (currentStep > 0) {
      setCurrentStep(prev => prev - 1);
    }
  };

  const handleSpeedUp = () => {
    const speeds = [0.5, 1, 1.5, 2];
    const idx = speeds.indexOf(playbackSpeed);
    if (idx < speeds.length - 1) {
      setPlaybackSpeed(speeds[idx + 1]);
    } else {
      setPlaybackSpeed(speeds[0]);
    }
    if (isPlaying) {
      stopPlayback();
      setTimeout(() => startPlayback(), 50);
    }
  };

  const { steps, ai_feedback } = data;
  const current = steps[currentStep];
  const progress = ((currentStep + 1) / steps.length) * 100;

  return (
    <main className="max-w-7xl mx-auto px-6 mt-8">
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">

        {/* LEFT: TIMELINE */}
        <div className="lg:col-span-4">
          <div className="bg-white/2 border border-white/5 rounded-[2.5rem] overflow-hidden">
            <div className="px-8 py-5 border-b border-white/5">
              <h3 className="text-xs font-black text-slate-500 uppercase tracking-[0.2em]">Timeline</h3>
            </div>
            <div className="max-h-[60vh] overflow-y-auto divide-y divide-white/5">
              {steps.map((step, idx) => {
                const isActive = idx === currentStep;
                const isQuestion = step.type === 'question';

                return (
                  <button
                    key={idx}
                    onClick={() => {
                      setCurrentStep(idx);
                      if (isPlaying) stopPlayback();
                    }}
                    className={`w-full text-left px-6 py-4 transition-all ${
                      isActive ? 'bg-purple-600/10 border-l-2 border-purple-500' : 'hover:bg-white/5'
                    }`}
                  >
                    <div className="flex items-center space-x-3">
                      <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-xs font-black ${
                        isQuestion ? 'bg-purple-600/20 text-purple-400' : 'bg-emerald-600/20 text-emerald-400'
                      }`}>
                        {isQuestion ? 'Q' : 'A'}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className={`text-sm font-bold truncate ${isActive ? 'text-white' : 'text-slate-400'}`}>
                          {isQuestion ? (step.skill_tested ? step.skill_tested.charAt(0).toUpperCase() + step.skill_tested.slice(1) : `Question ${step.question_index + 1}`) : `Answer ${step.question_index + 1}`}
                        </p>
                        {step.difficulty && (
                          <p className="text-[10px] text-slate-600 uppercase font-bold">{step.difficulty}</p>
                        )}
                      </div>
                      {isActive && <div className="w-2 h-2 bg-purple-500 rounded-full animate-pulse" />}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* RIGHT: TRANSCRIPT */}
        <div className="lg:col-span-8 space-y-6">
          <div className={`bg-white/2 border rounded-[2.5rem] p-10 ${
            current.type === 'question' ? 'border-purple-500/20' : 'border-emerald-500/20'
          }`}>
            <div className="flex items-center space-x-3 mb-6">
              {current.type === 'question' ? (
                <div className="w-10 h-10 bg-purple-600/20 rounded-xl flex items-center justify-center">
                  <Bot size={20} className="text-purple-400" />
                </div>
              ) : (
                <div className="w-10 h-10 bg-emerald-600/20 rounded-xl flex items-center justify-center">
                  <User size={20} className="text-emerald-400" />
                </div>
              )}
              <div>
                <p className="text-sm font-bold text-white">{current.speaker}</p>
                <p className="text-[10px] text-slate-500 uppercase font-bold tracking-widest">
                  {current.type === 'question' ? 'AI Interviewer' : 'Candidate Response'}
                  {current.category && ` — ${current.category}`}
                </p>
              </div>
            </div>
            <div className="bg-white/5 rounded-2xl p-6 border border-white/5">
              <p className="text-base text-slate-300 leading-relaxed font-medium whitespace-pre-wrap">
                {current.content}
              </p>
            </div>

            {current.type === 'answer' && ai_feedback && (
              <div className="mt-6 bg-amber-500/5 border border-amber-500/10 rounded-2xl p-6">
                <h4 className="text-[10px] font-black text-amber-400 uppercase tracking-widest mb-3 flex items-center">
                  <Award size={14} className="mr-2" /> AI Evaluation Summary
                </h4>
                <div className="grid grid-cols-3 gap-4">
                  {ai_feedback.technical_accuracy && (
                    <div className="text-center">
                      <p className="text-xl font-black text-purple-400">{ai_feedback.technical_accuracy}</p>
                      <p className="text-[10px] text-slate-500 uppercase">Technical</p>
                    </div>
                  )}
                  {ai_feedback.communication_clarity && (
                    <div className="text-center">
                      <p className="text-xl font-black text-purple-400">{ai_feedback.communication_clarity}</p>
                      <p className="text-[10px] text-slate-500 uppercase">Communication</p>
                    </div>
                  )}
                  {ai_feedback.depth_of_knowledge && (
                    <div className="text-center">
                      <p className="text-xl font-black text-purple-400">{ai_feedback.depth_of_knowledge}</p>
                      <p className="text-[10px] text-slate-500 uppercase">Depth</p>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Playback Controls */}
          <div className="bg-white/2 border border-white/5 rounded-[2.5rem] p-8">
            <div className="mb-6">
              <div className="w-full bg-white/5 rounded-full h-2">
                <div className="bg-purple-600 h-2 rounded-full transition-all duration-300" style={{ width: `${progress}%` }} />
              </div>
              <div className="flex justify-between mt-2">
                <span className="text-[10px] text-slate-500 font-bold">Step {currentStep + 1} of {steps.length}</span>
                <span className="text-[10px] text-slate-500 font-bold">{Math.round(progress)}%</span>
              </div>
            </div>
            <div className="flex items-center justify-center space-x-4">
              <button onClick={handlePrev} disabled={currentStep === 0}
                className="p-3 bg-white/5 border border-white/10 rounded-xl text-slate-400 hover:text-white hover:bg-white/10 transition-all disabled:opacity-30 disabled:cursor-not-allowed">
                <SkipBack size={20} />
              </button>
              <button onClick={togglePlayback}
                className="p-4 bg-purple-600 rounded-2xl text-white hover:bg-purple-500 transition-all shadow-lg shadow-purple-900/30 active:scale-95">
                {isPlaying ? <Pause size={24} /> : <Play size={24} />}
              </button>
              <button onClick={handleNext} disabled={currentStep >= steps.length - 1}
                className="p-3 bg-white/5 border border-white/10 rounded-xl text-slate-400 hover:text-white hover:bg-white/10 transition-all disabled:opacity-30 disabled:cursor-not-allowed">
                <SkipForward size={20} />
              </button>
              <button onClick={handleSpeedUp}
                className="px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-slate-400 hover:text-white hover:bg-white/10 transition-all text-sm font-bold">
                <FastForward size={16} className="inline mr-1" />{playbackSpeed}x
              </button>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
};


const InterviewReplay = () => {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!sessionId) return;
    const fetchData = async () => {
      try {
        let res;
        try {
          res = await apiClient.get(`/hr/interviews/${sessionId}/replay`);
        } catch {
          res = await apiClient.get(`/users/sessions/${sessionId}/replay`);
        }
        setData(res.data);
      } catch (err) {
        console.error('Failed to fetch replay:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [sessionId]);

  if (loading) {
    return (
      <div className="min-h-screen bg-[#020617] flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="w-16 h-16 border-4 border-purple-500 border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-purple-400 font-bold tracking-widest uppercase text-xs">Loading Interview Replay...</p>
        </div>
      </div>
    );
  }

  if (!data || !data.steps || data.steps.length === 0) {
    return (
      <div className="min-h-screen bg-[#020617] flex items-center justify-center">
        <div className="text-center space-y-4">
          <p className="text-red-400 font-bold tracking-widest uppercase text-xs">No replay data available.</p>
          <button onClick={() => navigate(-1)} className="text-purple-400 underline text-sm">Go Back</button>
        </div>
      </div>
    );
  }

  const { candidate_name, job_role, overall_score, duration_seconds } = data;

  const formatDuration = (secs) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  return (
    <div className="min-h-screen bg-[#020617] font-sans pb-20">
      {/* HEADER */}
      <header className="bg-[#0a0f1e] border-b border-white/5 sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <button onClick={() => navigate(-1)} className="p-2 hover:bg-white/5 rounded-xl transition-colors text-slate-500 hover:text-white">
              <ChevronLeft size={24} />
            </button>
            <div className="h-8 w-px bg-white/5" />
            <div>
              <h1 className="text-xl font-bold text-white">Interview Replay</h1>
              <p className="text-xs text-slate-500 font-medium">{candidate_name} — {job_role}</p>
            </div>
          </div>
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2 text-slate-400">
              <Clock size={14} />
              <span className="text-sm font-mono">{formatDuration(duration_seconds)}</span>
            </div>
            {overall_score !== null && (
              <div className="flex items-center space-x-2 bg-purple-600/10 border border-purple-500/20 px-4 py-2 rounded-xl">
                <Award size={14} className="text-purple-400" />
                <span className="text-sm font-bold text-purple-400">Score: {overall_score}/10</span>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Key forces re-mount when sessionId changes, resetting all internal state */}
      <ReplayContent key={sessionId} data={data} />
    </div>
  );
};

export default InterviewReplay;
