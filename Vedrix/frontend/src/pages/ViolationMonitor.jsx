import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Shield, AlertTriangle, Eye, Clipboard, Keyboard, RefreshCw, Clock, UserCheck, UserMinus, EyeOff } from 'lucide-react';
import apiClient from '../services/api';

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: 'easeOut' } }
};

const violationConfig = {
  tab_switch: { icon: Eye, color: 'text-amber-400', dot: 'bg-amber-400', bg: 'bg-amber-500/10 border-amber-500/20', label: 'Tab Switch' },
  paste_detected: { icon: Clipboard, color: 'text-red-400', dot: 'bg-red-400', bg: 'bg-red-500/10 border-red-500/20', label: 'Paste Detected' },
  anomalous_typing: { icon: Keyboard, color: 'text-purple-400', dot: 'bg-purple-400', bg: 'bg-purple-500/10 border-purple-500/20', label: 'Anomalous Typing' },
  multiple_faces: { icon: UserCheck, color: 'text-red-500', dot: 'bg-red-500', bg: 'bg-red-500/10 border-red-500/20', label: 'Multiple Faces' },
  no_face: { icon: UserMinus, color: 'text-rose-400', dot: 'bg-rose-400', bg: 'bg-rose-500/10 border-rose-500/20', label: 'No Face Detected' },
  gaze_deviation: { icon: EyeOff, color: 'text-orange-400', dot: 'bg-orange-400', bg: 'bg-orange-500/10 border-orange-500/20', label: 'Gaze Deviation' },
};

const ViolationMonitor = () => {
  const { sessionId } = useParams();
  const [violations, setViolations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const feedRef = useRef(null);

  const fetchViolations = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.get(`/hr/interviews/${sessionId}/violations`);
      setViolations(res.data?.violations || res.data || []);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load violations');
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    Promise.resolve().then(() => {
      fetchViolations();
    });
  }, [fetchViolations]);

  // Auto-scroll feed
  useEffect(() => {
    if (feedRef.current) {
      feedRef.current.scrollTop = feedRef.current.scrollHeight;
    }
  }, [violations]);

  const counts = violations.reduce((acc, v) => {
    acc[v.type] = (acc[v.type] || 0) + 1;
    return acc;
  }, {});

  const tabSwitchCount = counts['tab_switch'] || 0;
  const thresholdExceeded = tabSwitchCount >= 3;

  // Build timeline data
  const timelineStart = violations.length > 0 ? new Date(violations[0].timestamp).getTime() : 0;
  const timelineEnd = violations.length > 0 ? new Date(violations[violations.length - 1].timestamp).getTime() : 0;
  const timelineDuration = timelineEnd - timelineStart || 1;

  if (loading) {
    return (
      <div className="min-h-screen bg-[#020617] text-white flex items-center justify-center">
        <div className="w-12 h-12 border-4 border-purple-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-[#020617] text-white flex items-center justify-center">
        <div className="text-center space-y-4">
          <p className="text-red-400 text-lg font-bold">{error}</p>
          <button onClick={fetchViolations}
            className="inline-flex items-center gap-2 bg-purple-600 hover:bg-purple-500 text-white font-bold px-6 py-3 rounded-2xl transition-all"
            aria-label="Retry loading violations"
          >
            <RefreshCw size={16} /> Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#020617] text-white font-sans">
      <div className="fixed top-0 right-0 w-[30%] h-[40%] bg-red-900/5 blur-[150px] rounded-full pointer-events-none" />

      <div className="max-w-6xl mx-auto px-8 py-12 space-y-8 relative z-10">
        {/* Header */}
        <motion.div variants={fadeUp} initial="hidden" animate="visible">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 bg-gradient-to-tr from-red-600 to-amber-500 rounded-2xl flex items-center justify-center shadow-xl shadow-red-900/30">
              <Shield size={24} className="text-white" />
            </div>
            <div>
              <h1 className="text-3xl font-black text-white tracking-tight">Proctor Monitor</h1>
              <p className="text-slate-500 text-sm">Session: {sessionId}</p>
            </div>
          </div>
        </motion.div>

        {/* Alert Banner */}
        {thresholdExceeded && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-red-500/10 border border-red-500/30 rounded-2xl p-4 flex items-center gap-3 animate-pulse"
            role="alert"
          >
            <AlertTriangle size={20} className="text-red-400 shrink-0" />
            <div>
              <p className="text-red-400 font-black text-sm">Tab Switch Threshold Exceeded</p>
              <p className="text-red-300/70 text-xs">{tabSwitchCount} tab switches detected — possible integrity concern</p>
            </div>
          </motion.div>
        )}

        {/* Violation Counts */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {Object.entries(violationConfig).map(([type, config]) => {
            const Icon = config.icon;
            const count = counts[type] || 0;
            return (
              <div key={type} className={`${config.bg} border rounded-2xl p-5 flex items-center gap-4`}>
                <div className="w-10 h-10 bg-white/5 rounded-xl flex items-center justify-center">
                  <Icon size={20} className={config.color} />
                </div>
                <div>
                  <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest">{config.label}</p>
                  <p className={`text-2xl font-black ${config.color}`}>{count}</p>
                </div>
              </div>
            );
          })}
        </div>

        {/* Timeline */}
        {violations.length > 0 && (
          <div className="bg-white/[0.03] border border-white/5 rounded-3xl p-6">
            <h2 className="text-xs font-black uppercase text-slate-400 tracking-widest mb-4">Violation Timeline</h2>
            <div className="relative h-12 bg-white/[0.02] rounded-xl overflow-hidden" role="img" aria-label="Violation timeline visualization">
              {violations.map((v, i) => {
                const pos = ((new Date(v.timestamp).getTime() - timelineStart) / timelineDuration) * 100;
                const cfg = violationConfig[v.type] || violationConfig.tab_switch;
                return (
                  <div
                    key={i}
                    className={`absolute top-1/2 -translate-y-1/2 w-3 h-3 rounded-full ${cfg.dot} opacity-80`}
                    style={{ left: `${Math.min(pos, 97)}%` }}
                    title={`${cfg.label} at ${new Date(v.timestamp).toLocaleTimeString()}`}
                  />
                );
              })}
            </div>
            <div className="flex justify-between mt-2">
              <span className="text-[10px] text-slate-600">Start</span>
              <span className="text-[10px] text-slate-600">End</span>
            </div>
          </div>
        )}

        {/* Violation Feed */}
        <div className="bg-white/[0.03] border border-white/5 rounded-3xl p-6">
          <h2 className="text-xs font-black uppercase text-slate-400 tracking-widest mb-4">Live Feed</h2>
          <div ref={feedRef} className="max-h-[400px] overflow-y-auto space-y-2 pr-2" role="log" aria-live="polite">
            {violations.map((v, i) => {
              const cfg = violationConfig[v.type] || violationConfig.tab_switch;
              const Icon = cfg.icon;
              return (
                <div key={i} className="flex items-center gap-3 bg-white/[0.02] border border-white/5 rounded-xl p-3">
                  <div className={`w-8 h-8 ${cfg.bg} border rounded-lg flex items-center justify-center shrink-0`}>
                    <Icon size={14} className={cfg.color} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-white text-sm font-bold">{cfg.label}</p>
                    {v.details && <p className="text-slate-500 text-xs truncate">{v.details}</p>}
                  </div>
                  <span className="text-slate-600 text-[10px] flex items-center gap-1 shrink-0">
                    <Clock size={10} /> {new Date(v.timestamp).toLocaleTimeString()}
                  </span>
                </div>
              );
            })}
            {violations.length === 0 && (
              <p className="text-slate-500 text-center py-8">No violations detected</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ViolationMonitor;
