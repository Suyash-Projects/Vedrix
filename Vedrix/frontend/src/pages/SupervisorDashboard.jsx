import { useState, useEffect, useCallback } from 'react';
import {
  Activity, Eye, Zap, Clock, AlertTriangle,
  XCircle, RefreshCcw, Radio,
  TrendingUp, TrendingDown, Minus,
  Sliders, Shield, PauseCircle, PlayCircle,
  Target, Brain
} from 'lucide-react';
import apiClient from '../services/api';
import { useNavigate } from 'react-router-dom';

const MODE_COLORS = {
  monitor: { bg: 'bg-blue-500/10', text: 'text-blue-400', border: 'border-blue-500/20', label: 'Monitor' },
  suggest: { bg: 'bg-amber-500/10', text: 'text-amber-400', border: 'border-amber-500/20', label: 'Suggest' },
  auto: { bg: 'bg-emerald-500/10', text: 'text-emerald-400', border: 'border-emerald-500/20', label: 'Auto' },
};

const SEVERITY_COLORS = {
  info: { bg: 'bg-blue-500/10', text: 'text-blue-400', dot: 'bg-blue-400' },
  warning: { bg: 'bg-amber-500/10', text: 'text-amber-400', dot: 'bg-amber-400' },
  critical: { bg: 'bg-red-500/10', text: 'text-red-400', dot: 'bg-red-400' },
};

const SupervisorDashboard = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [activeSessions, setActiveSessions] = useState([]);
  const [stats, setStats] = useState(null);
  const [selectedSession, setSelectedSession] = useState(null);
  const [sessionDetail, setSessionDetail] = useState(null);
  const [timeline, setTimeline] = useState(null);
  const [error, setError] = useState('');
  const [lastRefresh, setLastRefresh] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const fetchActiveSessions = useCallback(async () => {
    try {
      setError('');
      const [sessionsRes, statsRes] = await Promise.allSettled([
        apiClient.get('/admin/supervisor/active-sessions'),
        apiClient.get('/admin/supervisor/stats'),
      ]);

      if (sessionsRes.status === 'fulfilled') {
        setActiveSessions(sessionsRes.value.data);
      }
      if (statsRes.status === 'fulfilled') {
        setStats(statsRes.value.data);
      }

      if (sessionsRes.status === 'rejected' && statsRes.status === 'rejected') {
        setError('Failed to fetch supervisor data');
      }

      setLastRefresh(new Date());
    } catch {
      setError('Failed to fetch supervisor data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchActiveSessions();
    const interval = setInterval(fetchActiveSessions, 15000);
    return () => clearInterval(interval);
  }, [fetchActiveSessions]);

  const fetchSessionDetail = async (sessionId) => {
    setDetailLoading(true);
    setSelectedSession(sessionId);
    try {
      const [detailRes, timelineRes] = await Promise.allSettled([
        apiClient.get(`/admin/supervisor/sessions/${sessionId}`),
        apiClient.get(`/admin/supervisor/sessions/${sessionId}/timeline?limit=30`),
      ]);
      if (detailRes.status === 'fulfilled') {
        setSessionDetail(detailRes.value.data);
      }
      if (timelineRes.status === 'fulfilled') {
        setTimeline(timelineRes.value.data);
      }
    } catch {
      setError('Failed to fetch session details');
    } finally {
      setDetailLoading(false);
    }
  };

  const handleOverride = async (sessionId, action, payload = {}) => {
    try {
      await apiClient.post(`/admin/supervisor/sessions/${sessionId}/override`, {
        action,
        ...payload,
        reason: payload.reason || `Admin ${action}`,
      });
      fetchActiveSessions();
      if (selectedSession === sessionId) {
        fetchSessionDetail(sessionId);
      }
    } catch (err) {
      setError(`Override failed: ${err.response?.data?.detail || err.message}`);
    }
  };

  const formatDuration = (seconds) => {
    if (!seconds) return '0m';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
  };

  const getTrendIcon = (trend) => {
    if (trend === 'improving') return <TrendingUp size={16} className="text-emerald-400" />;
    if (trend === 'declining') return <TrendingDown size={16} className="text-red-400" />;
    return <Minus size={16} className="text-slate-400" />;
  };

  const getDifficultyBadge = (diff) => {
    const colors = {
      easy: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
      medium: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
      hard: 'bg-red-500/10 text-red-400 border-red-500/20',
    };
    return (
      <span className={`px-2 py-0.5 rounded-md text-xs font-bold border ${colors[diff] || colors.medium}`}>
        {diff}
      </span>
    );
  };

  return (
    <div className="min-h-screen bg-[#020617] text-white">
      <div className="max-w-7xl mx-auto px-8 py-10">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <div className="flex items-center gap-3">
              <div className="p-2 bg-purple-500/10 rounded-xl border border-purple-500/20">
                <Brain size={28} className="text-purple-400" />
              </div>
              <div>
                <h1 className="text-3xl font-extrabold tracking-tight">AI Supervisor</h1>
                <p className="text-slate-500 mt-1">Real-time monitoring and control of active interview sessions</p>
              </div>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <button
              onClick={() => navigate('/admin')}
              className="flex items-center space-x-2 bg-white/5 border border-white/10 text-slate-300 px-4 py-2 rounded-xl text-sm font-bold hover:bg-white/10 transition-all"
            >
              <Activity size={16} />
              <span>Admin Panel</span>
            </button>
            <button
              onClick={fetchActiveSessions}
              disabled={loading}
              className="flex items-center space-x-2 bg-white/5 border border-white/10 text-slate-300 px-4 py-2 rounded-xl text-sm font-bold hover:bg-white/10 transition-all disabled:opacity-50"
            >
              <RefreshCcw size={16} className={loading ? 'animate-spin' : ''} />
              <span>Refresh</span>
            </button>
          </div>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 text-sm">
            {error}
          </div>
        )}

        {/* Stats Cards */}
        {stats && (
          <div className="grid grid-cols-5 gap-4 mb-8">
            <div className="p-4 bg-white/[0.03] border border-white/10 rounded-xl">
              <div className="flex items-center gap-2 text-slate-400 text-xs font-bold uppercase tracking-wider mb-2">
                <Radio size={14} /> Active Sessions
              </div>
              <div className="text-3xl font-extrabold text-white">{stats.active_sessions}</div>
            </div>
            <div className="p-4 bg-white/[0.03] border border-white/10 rounded-xl">
              <div className="flex items-center gap-2 text-slate-400 text-xs font-bold uppercase tracking-wider mb-2">
                <Eye size={14} /> Observations
              </div>
              <div className="text-3xl font-extrabold text-white">{stats.total_observations}</div>
            </div>
            <div className="p-4 bg-white/[0.03] border border-white/10 rounded-xl">
              <div className="flex items-center gap-2 text-slate-400 text-xs font-bold uppercase tracking-wider mb-2">
                <AlertTriangle size={14} /> Sessions w/ Alerts
              </div>
              <div className="text-3xl font-extrabold text-amber-400">{stats.sessions_with_alerts}</div>
            </div>
            <div className="p-4 bg-white/[0.03] border border-white/10 rounded-xl">
              <div className="flex items-center gap-2 text-slate-400 text-xs font-bold uppercase tracking-wider mb-2">
                <Zap size={14} /> Auto Mode
              </div>
              <div className="text-3xl font-extrabold text-emerald-400">{stats.auto_mode_sessions}</div>
            </div>
            <div className="p-4 bg-white/[0.03] border border-white/10 rounded-xl">
              <div className="flex items-center gap-2 text-slate-400 text-xs font-bold uppercase tracking-wider mb-2">
                <Sliders size={14} /> Suggest Mode
              </div>
              <div className="text-3xl font-extrabold text-amber-400">{stats.suggest_mode_sessions}</div>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Active Sessions List */}
          <div className="lg:col-span-1">
            <div className="p-4 bg-white/[0.03] border border-white/10 rounded-xl">
              <h2 className="text-lg font-bold mb-4 flex items-center gap-2">
                <Radio size={18} className="text-purple-400" />
                Active Sessions
                <span className="ml-auto text-xs text-slate-500 font-normal">{activeSessions.length} live</span>
              </h2>

              {loading && activeSessions.length === 0 ? (
                <div className="text-center py-12 text-slate-500">
                  <div className="animate-spin w-8 h-8 border-2 border-purple-500 border-t-transparent rounded-full mx-auto mb-3" />
                  <p className="text-sm">Loading sessions...</p>
                </div>
              ) : activeSessions.length === 0 ? (
                <div className="text-center py-12 text-slate-500">
                  <Radio size={32} className="mx-auto mb-3 opacity-30" />
                  <p className="text-sm font-medium">No active interviews</p>
                  <p className="text-xs mt-1">Sessions will appear here when candidates start interviews</p>
                </div>
              ) : (
                <div className="space-y-2 max-h-[600px] overflow-y-auto pr-1">
                  {activeSessions.map((session) => {
                    const modeStyle = MODE_COLORS[session.control_mode] || MODE_COLORS.suggest;
                    const hasAlerts = session.observations_count > 0;
                    const isSelected = selectedSession === session.session_id;
                    return (
                      <button
                        key={session.session_id}
                        onClick={() => fetchSessionDetail(session.session_id)}
                        className={`w-full text-left p-3 rounded-xl border transition-all ${
                          isSelected
                            ? 'bg-purple-500/10 border-purple-500/30'
                            : 'bg-white/[0.02] border-white/5 hover:bg-white/[0.05] hover:border-white/10'
                        }`}
                      >
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-xs font-mono text-slate-400 truncate max-w-[120px]">
                            {session.session_id.slice(0, 12)}...
                          </span>
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${modeStyle.bg} ${modeStyle.text} ${modeStyle.border} border`}>
                            {modeStyle.label}
                          </span>
                        </div>
                        <div className="flex items-center gap-3 text-xs text-slate-400">
                          <span className="flex items-center gap-1">
                            <Clock size={11} />
                            {formatDuration(session.duration_seconds)}
                          </span>
                          {session.difficulty_analysis && (
                            <span>{getDifficultyBadge(session.difficulty_analysis.current_difficulty)}</span>
                          )}
                          {session.performance_trend && (
                            <span className="flex items-center gap-1">
                              {getTrendIcon(session.performance_trend.trend)}
                              <span className="capitalize text-[10px] text-slate-500">{session.performance_trend.trend}</span>
                            </span>
                          )}
                          {hasAlerts && (
                            <span className="ml-auto flex items-center gap-1 text-amber-400">
                              <AlertTriangle size={11} />
                              {session.observations_count}
                            </span>
                          )}
                        </div>
                      </button>
                    );
                  })}
                </div>
              )}

              {lastRefresh && (
                <p className="text-[10px] text-slate-600 mt-3 text-center">
                  Last updated: {lastRefresh.toLocaleTimeString()}
                </p>
              )}
            </div>
          </div>

          {/* Session Details Panel */}
          <div className="lg:col-span-2">
            {!selectedSession ? (
              <div className="p-12 bg-white/[0.03] border border-white/10 rounded-xl flex flex-col items-center justify-center text-slate-500">
                <Brain size={48} className="mb-4 opacity-20" />
                <p className="text-lg font-medium">Select a session to inspect</p>
                <p className="text-sm mt-2">
                  Click on any active session to view real-time supervisor analysis, observations, and controls
                </p>
                <div className="grid grid-cols-3 gap-4 mt-8 text-center text-xs">
                  <div className="p-3 bg-white/[0.02] rounded-lg border border-white/5">
                    <Clock size={20} className="mx-auto mb-2 text-blue-400" />
                    Duration Monitoring
                  </div>
                  <div className="p-3 bg-white/[0.02] rounded-lg border border-white/5">
                    <Target size={20} className="mx-auto mb-2 text-amber-400" />
                    Difficulty Tracking
                  </div>
                  <div className="p-3 bg-white/[0.02] rounded-lg border border-white/5">
                    <Shield size={20} className="mx-auto mb-2 text-emerald-400" />
                    Auto Control
                  </div>
                </div>
              </div>
            ) : detailLoading ? (
              <div className="p-12 bg-white/[0.03] border border-white/10 rounded-xl flex flex-col items-center justify-center text-slate-500">
                <div className="animate-spin w-8 h-8 border-2 border-purple-500 border-t-transparent rounded-full mx-auto mb-3" />
                <p className="text-sm">Loading session details...</p>
              </div>
            ) : sessionDetail ? (
              <div className="space-y-4">
                {/* Session Header */}
                <div className="p-4 bg-white/[0.03] border border-white/10 rounded-xl">
                  <div className="flex items-center justify-between mb-3">
                    <div>
                      <h2 className="text-lg font-bold">Session Analysis</h2>
                      <p className="text-xs font-mono text-slate-500 mt-1">{sessionDetail.session_id}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <select
                        value={sessionDetail.control_mode}
                        onChange={(e) => handleOverride(sessionDetail.session_id, 'set_control_mode', { mode: e.target.value })}
                        className="bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-xs font-bold text-white cursor-pointer"
                      >
                        <option value="monitor">🔍 Monitor</option>
                        <option value="suggest">💡 Suggest</option>
                        <option value="auto">⚡ Auto</option>
                      </select>
                      {sessionDetail.paused ? (
                        <button
                          onClick={() => handleOverride(sessionDetail.session_id, 'resume')}
                          className="flex items-center gap-1.5 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 px-3 py-1.5 rounded-lg text-xs font-bold hover:bg-emerald-500/20 transition-all"
                        >
                          <PlayCircle size={14} /> Resume
                        </button>
                      ) : (
                        <button
                          onClick={() => handleOverride(sessionDetail.session_id, 'pause')}
                          className="flex items-center gap-1.5 bg-amber-500/10 border border-amber-500/20 text-amber-400 px-3 py-1.5 rounded-lg text-xs font-bold hover:bg-amber-500/20 transition-all"
                        >
                          <PauseCircle size={14} /> Pause
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Quick Stats */}
                  <div className="grid grid-cols-4 gap-3">
                    <div className="p-3 bg-white/[0.02] rounded-lg border border-white/5">
                      <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">Duration</div>
                      <div className="text-lg font-bold">
                        {formatDuration(sessionDetail.duration_analysis?.total_elapsed_seconds)}
                      </div>
                      {sessionDetail.duration_analysis?.is_running_overtime && (
                        <div className="flex items-center gap-1 text-[10px] text-red-400 mt-1">
                          <AlertTriangle size={10} /> Overtime
                        </div>
                      )}
                    </div>
                    <div className="p-3 bg-white/[0.02] rounded-lg border border-white/5">
                      <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">Difficulty</div>
                      <div className="text-lg font-bold">
                        {getDifficultyBadge(sessionDetail.difficulty_analysis?.current_difficulty || 'medium')}
                      </div>
                      <div className="text-[10px] text-slate-500 mt-1">
                        Switches: {sessionDetail.difficulty_analysis?.difficulty_switches || 0}
                      </div>
                    </div>
                    <div className="p-3 bg-white/[0.02] rounded-lg border border-white/5">
                      <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">Performance</div>
                      <div className="flex items-center gap-2">
                        <span className="text-lg font-bold capitalize">
                          {sessionDetail.performance_trend?.trend || 'stable'}
                        </span>
                        {getTrendIcon(sessionDetail.performance_trend?.trend)}
                      </div>
                      {sessionDetail.performance_trend?.fatigue_detected && (
                        <div className="flex items-center gap-1 text-[10px] text-amber-400 mt-1">
                          <AlertTriangle size={10} /> Fatigue
                        </div>
                      )}
                    </div>
                    <div className="p-3 bg-white/[0.02] rounded-lg border border-white/5">
                      <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">Observations</div>
                      <div className="text-lg font-bold">{sessionDetail.observations?.length || 0}</div>
                      {sessionDetail.last_action && (
                        <div className="text-[10px] text-purple-400 mt-1 truncate">
                          Last: {sessionDetail.last_action.action_type}
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                {/* Control Actions */}
                <div className="p-4 bg-white/[0.03] border border-white/10 rounded-xl">
                  <h3 className="text-sm font-bold mb-3 flex items-center gap-2">
                    <Shield size={16} className="text-purple-400" />
                    Control Actions
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    <button
                      onClick={() => handleOverride(sessionDetail.session_id, 'override_difficulty', { difficulty: 'easy' })}
                      className="flex items-center gap-1.5 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 px-3 py-1.5 rounded-lg text-xs font-bold hover:bg-emerald-500/20 transition-all"
                    >
                      <Sliders size={12} /> Easy
                    </button>
                    <button
                      onClick={() => handleOverride(sessionDetail.session_id, 'override_difficulty', { difficulty: 'medium' })}
                      className="flex items-center gap-1.5 bg-amber-500/10 border border-amber-500/20 text-amber-400 px-3 py-1.5 rounded-lg text-xs font-bold hover:bg-amber-500/20 transition-all"
                    >
                      <Sliders size={12} /> Medium
                    </button>
                    <button
                      onClick={() => handleOverride(sessionDetail.session_id, 'override_difficulty', { difficulty: 'hard' })}
                      className="flex items-center gap-1.5 bg-red-500/10 border border-red-500/20 text-red-400 px-3 py-1.5 rounded-lg text-xs font-bold hover:bg-red-500/20 transition-all"
                    >
                      <Sliders size={12} /> Hard
                    </button>
                    <span className="w-px bg-white/10 mx-1" />
                    <button
                      onClick={() => handleOverride(sessionDetail.session_id, 'force_close')}
                      className="flex items-center gap-1.5 bg-red-500/10 border border-red-500/20 text-red-400 px-3 py-1.5 rounded-lg text-xs font-bold hover:bg-red-500/20 transition-all"
                    >
                      <XCircle size={12} /> Force Close
                    </button>
                  </div>
                </div>

                {/* Observation Timeline */}
                {timeline && timeline.length > 0 && (
                  <div className="p-4 bg-white/[0.03] border border-white/10 rounded-xl">
                    <h3 className="text-sm font-bold mb-3 flex items-center gap-2">
                      <Activity size={16} className="text-purple-400" />
                      Observation Timeline
                      <span className="ml-auto text-[10px] text-slate-500 font-normal">Last {timeline.length}</span>
                    </h3>
                    <div className="space-y-1 max-h-[300px] overflow-y-auto pr-1">
                      {timeline.slice().reverse().map((obs, i) => {
                        const sevStyle = SEVERITY_COLORS[obs.severity] || SEVERITY_COLORS.info;
                        return (
                          <div key={i} className="flex items-start gap-3 p-2 rounded-lg hover:bg-white/[0.02] transition-colors">
                            <div className={`w-2 h-2 rounded-full mt-1.5 flex-shrink-0 ${sevStyle.dot}`} />
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2">
                                <span className={`text-[10px] font-bold uppercase ${sevStyle.text}`}>
                                  {obs.type.replace(/_/g, ' ')}
                                </span>
                                <span className="text-[10px] text-slate-600">
                                  {new Date(obs.timestamp).toLocaleTimeString()}
                                </span>
                              </div>
                              <p className="text-xs text-slate-300 mt-0.5">{obs.message}</p>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {(!timeline || timeline.length === 0) && (
                  <div className="p-6 bg-white/[0.03] border border-white/10 rounded-xl text-center text-slate-500">
                    <Activity size={24} className="mx-auto mb-2 opacity-30" />
                    <p className="text-sm">No observations recorded yet</p>
                    <p className="text-xs mt-1">Observations will appear as the interview progresses</p>
                  </div>
                )}
              </div>
            ) : (
              <div className="p-12 bg-white/[0.03] border border-white/10 rounded-xl text-center text-slate-500">
                <XCircle size={32} className="mx-auto mb-3 opacity-30" />
                <p className="text-sm font-medium">Session not found</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default SupervisorDashboard;
