import { useState, useEffect, useCallback } from 'react';
import {
  Save,
  RefreshCcw,
  Zap,
  Shield,
  Mail,
  AlertTriangle,
  CheckCircle,
  Sliders,
  History,
  User
} from 'lucide-react';
import apiClient from '../services/api';
import { useNavigate } from 'react-router-dom';

const AVAILABLE_MODELS = [
  { value: 'groq', label: 'Groq (Default)' },
  { value: 'deepseek', label: 'DeepSeek (Default)' },
  { value: 'nvidia', label: 'NVIDIA (Default)' },
  { value: 'openrouter', label: 'OpenRouter (Default)' },
  { value: 'llama3-70b-8192', label: 'Llama 3.1 70B (Groq)' },
  { value: 'llama3-8b-8192', label: 'Llama 3.1 8B (Groq)' },
  { value: 'llama-3.1-70b-versatile', label: 'Llama 3.1 70B (Groq/OpenRouter)' },
  { value: 'llama-3.1-8b-instant', label: 'Llama 3.1 8B (Groq/OpenRouter)' },
  { value: 'deepseek-chat', label: 'DeepSeek Chat V3' },
  { value: 'deepseek-coder', label: 'DeepSeek Coder V2' },
  { value: 'deepseek-reasoner', label: 'DeepSeek R1 (Reasoner)' },
  { value: 'gpt-4o-mini', label: 'GPT-4o Mini (OpenAI)' },
  { value: 'gpt-4o', label: 'GPT-4o (OpenAI)' },
  { value: 'claude-3-5-sonnet', label: 'Claude 3.5 Sonnet' },
  { value: 'nvidia/nemotron-4-340b', label: 'NVIDIA Nemotron 4 340B' },
];

const DEFAULT_CONFIGS = {
  ai_provider: 'groq',
  rate_limit_per_minute: 60,
  session_timeout_minutes: 30,
  max_interview_duration_minutes: 90,
  enable_email_notifications: true,
  enable_audit_logging: true,
  passing_score_threshold: 6.0,
  max_questions_per_drive: 10,
  proctor_tab_switch_threshold: 3,
  proctor_paste_threshold: 100,
  ai_model_interview: 'llama3-70b-8192',
  ai_model_evaluation: 'deepseek-chat',
  ai_model_coaching: 'gpt-4o-mini',
};

const loadSystemConfigData = () =>
  Promise.allSettled([
    apiClient.get('/admin/ai-health'),
    apiClient.get('/admin/config'),
    apiClient.get('/admin/config/history'),
  ]);

const SystemConfig = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [config, setConfig] = useState(DEFAULT_CONFIGS);
  const [history, setHistory] = useState([]);
  const [aiHealth, setAiHealth] = useState(null);

  const fetchConfig = useCallback(async ({ showLoading = true, clearError = true } = {}) => {
    try {
      if (showLoading) {
        setLoading(true);
      }
      if (clearError) {
        setError('');
      }

      // Fetch AI health and configuration concurrently
      const [aiRes, configRes, historyRes] = await loadSystemConfigData();

      if (aiRes.status === 'fulfilled') {
        setAiHealth(aiRes.value.data);
      }

      if (configRes.status === 'fulfilled') {
        setConfig(configRes.value.data);
      } else {
        setError('Failed to fetch system configuration from the database.');
      }

      if (historyRes.status === 'fulfilled') {
        setHistory(historyRes.value.data);
      }
    } catch {
      setError('Failed to fetch system configuration');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let isActive = true;

    loadSystemConfigData()
      .then(([aiRes, configRes, historyRes]) => {
        if (!isActive) {
          return;
        }

        if (aiRes.status === 'fulfilled') {
          setAiHealth(aiRes.value.data);
        }

        if (configRes.status === 'fulfilled') {
          setConfig(configRes.value.data);
        } else {
          setError('Failed to fetch system configuration from the database.');
        }

        if (historyRes.status === 'fulfilled') {
          setHistory(historyRes.value.data);
        }
      })
      .catch(() => {
        if (isActive) {
          setError('Failed to fetch system configuration');
        }
      })
      .finally(() => {
        if (isActive) {
          setLoading(false);
        }
      });

    return () => {
      isActive = false;
    };
  }, []);

  const handleSave = async () => {
    try {
      setSaving(true);
      setError('');
      setSuccess('');

      // Save each configuration key to the database
      const savePromises = Object.entries(config).map(([key, value]) =>
        apiClient.put(`/admin/config/${key}`, { value })
      );
      await Promise.all(savePromises);

      setSuccess('Configuration saved and applied successfully');
      // Refresh configurations and logs
      const historyRes = await apiClient.get('/admin/config/history');
      setHistory(historyRes.data);
      
      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to save configuration. Please check the values.');
    } finally {
      setSaving(false);
    }
  };

  const handleReset = async () => {
    try {
      setSaving(true);
      setError('');
      setSuccess('');

      // Save all defaults to DB
      const savePromises = Object.entries(DEFAULT_CONFIGS).map(([key, value]) =>
        apiClient.put(`/admin/config/${key}`, { value })
      );
      await Promise.all(savePromises);

      setConfig(DEFAULT_CONFIGS);
      setSuccess('Configuration reset to defaults successfully');

      const historyRes = await apiClient.get('/admin/config/history');
      setHistory(historyRes.data);

      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to reset configuration.');
    } finally {
      setSaving(false);
    }
  };

  const handleChange = (key, value) => {
    setConfig(prev => ({ ...prev, [key]: value }));
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#020617] flex items-center justify-center">
        <div className="text-center">
          <RefreshCcw size={32} className="animate-spin text-purple-400 mx-auto mb-4" />
          <p className="text-slate-400">Loading system configuration...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#020617] text-white">
      <div className="max-w-5xl mx-auto px-8 py-10">
        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-8 gap-4">
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight">System Configuration</h1>
            <p className="text-slate-500 mt-1">Manage global AI services, limits, proctoring thresholds, and security</p>
          </div>
          <div className="flex items-center space-x-3">
            <button
              onClick={() => navigate('/admin')}
              className="flex items-center space-x-2 bg-white/5 border border-white/10 text-slate-300 px-4 py-2 rounded-xl text-sm font-bold hover:bg-white/10 transition-all cursor-pointer"
            >
              <span>Back to Admin</span>
            </button>
            <button
              onClick={fetchConfig}
              className="flex items-center space-x-2 bg-white/5 border border-white/10 text-slate-300 px-4 py-2 rounded-xl text-sm font-bold hover:bg-white/10 transition-all cursor-pointer"
            >
              <RefreshCcw size={16} />
              <span>Refresh</span>
            </button>
          </div>
        </div>

        {error && (
          <div className="mb-6 p-4 rounded-xl text-sm font-bold border bg-red-500/10 border-red-500/20 text-red-400 flex items-center">
            <AlertTriangle size={16} className="mr-2" />
            {error}
          </div>
        )}

        {success && (
          <div className="mb-6 p-4 rounded-xl text-sm font-bold border bg-emerald-500/10 border-emerald-500/20 text-emerald-400 flex items-center">
            <CheckCircle size={16} className="mr-2" />
            {success}
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {/* Left Column: AI Provider & Task Routing */}
          <div className="space-y-8">
            <div className="bg-white/2 border border-white/5 rounded-3xl overflow-hidden shadow-xl backdrop-blur-md">
              <div className="px-8 py-6 border-b border-white/5 bg-white/1">
                <h2 className="font-bold text-white flex items-center">
                  <Zap className="mr-2 text-amber-400" size={20} />
                  AI Settings & Model Routing
                </h2>
              </div>
              <div className="p-8 space-y-6">
                <div>
                  <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500 mb-1.5">
                    Primary AI Gateway Provider
                  </label>
                  <select
                    value={config.ai_provider}
                    onChange={(e) => handleChange('ai_provider', e.target.value)}
                    className="w-full bg-slate-900 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:ring-1 focus:ring-purple-500 outline-none"
                  >
                    <option value="groq">Groq</option>
                    <option value="deepseek">DeepSeek</option>
                    <option value="nvidia">NVIDIA</option>
                    <option value="openrouter">OpenRouter</option>
                  </select>
                </div>

                <div>
                  <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500 mb-1.5">
                    Interview Loop Model (Groq / Nemotron)
                  </label>
                  <select
                    value={config.ai_model_interview}
                    onChange={(e) => handleChange('ai_model_interview', e.target.value)}
                    className="w-full bg-slate-900 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:ring-1 focus:ring-purple-500 outline-none"
                  >
                    {AVAILABLE_MODELS.map(m => (
                      <option key={m.value} value={m.value}>{m.label}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500 mb-1.5">
                    Evaluation Model (Deep Analysis)
                  </label>
                  <select
                    value={config.ai_model_evaluation}
                    onChange={(e) => handleChange('ai_model_evaluation', e.target.value)}
                    className="w-full bg-slate-900 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:ring-1 focus:ring-purple-500 outline-none"
                  >
                    {AVAILABLE_MODELS.map(m => (
                      <option key={m.value} value={m.value}>{m.label}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500 mb-1.5">
                    Coaching & Report Model
                  </label>
                  <select
                    value={config.ai_model_coaching}
                    onChange={(e) => handleChange('ai_model_coaching', e.target.value)}
                    className="w-full bg-slate-900 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:ring-1 focus:ring-purple-500 outline-none"
                  >
                    {AVAILABLE_MODELS.map(m => (
                      <option key={m.value} value={m.value}>{m.label}</option>
                    ))}
                  </select>
                </div>

                {aiHealth && (
                  <div className="bg-white/2 border border-white/5 rounded-xl p-4">
                    <p className="text-xs font-bold text-slate-400 mb-2">Service Circuit Breakers:</p>
                    <div className="flex flex-wrap gap-2">
                      {aiHealth.circuit_breakers && Object.entries(aiHealth.circuit_breakers).map(([name, cb]) => (
                        <span
                          key={name}
                          className={`px-3 py-1 rounded-full text-[10px] font-black uppercase border ${
                            cb.state === 'CLOSED'
                              ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                              : 'bg-red-500/10 text-red-400 border-red-500/20'
                          }`}
                        >
                          {name}: {cb.state}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Right Column: Limits, Proctoring, & Alerts */}
          <div className="space-y-8">
            <div className="bg-white/2 border border-white/5 rounded-3xl overflow-hidden shadow-xl backdrop-blur-md">
              <div className="px-8 py-6 border-b border-white/5 bg-white/1">
                <h2 className="font-bold text-white flex items-center">
                  <Shield className="mr-2 text-emerald-400" size={20} />
                  Limits & Security Settings
                </h2>
              </div>
              <div className="p-8 space-y-6">
                <div>
                  <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500 mb-1.5">
                    API Rate Limit (requests/min)
                  </label>
                  <input
                    type="number"
                    value={config.rate_limit_per_minute}
                    onChange={(e) => handleChange('rate_limit_per_minute', parseInt(e.target.value))}
                    className="w-full bg-slate-900 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:ring-1 focus:ring-purple-500 outline-none"
                    min="10"
                    max="500"
                  />
                </div>

                <div>
                  <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500 mb-1.5">
                    Session Inactivity Timeout (minutes)
                  </label>
                  <input
                    type="number"
                    value={config.session_timeout_minutes}
                    onChange={(e) => handleChange('session_timeout_minutes', parseInt(e.target.value))}
                    className="w-full bg-slate-900 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:ring-1 focus:ring-purple-500 outline-none"
                    min="5"
                    max="180"
                  />
                </div>

                <div>
                  <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500 mb-1.5">
                    Max Interview Duration (minutes)
                  </label>
                  <input
                    type="number"
                    value={config.max_interview_duration_minutes}
                    onChange={(e) => handleChange('max_interview_duration_minutes', parseInt(e.target.value))}
                    className="w-full bg-slate-900 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:ring-1 focus:ring-purple-500 outline-none"
                    min="15"
                    max="300"
                  />
                </div>
              </div>
            </div>

            <div className="bg-white/2 border border-white/5 rounded-3xl overflow-hidden shadow-xl backdrop-blur-md">
              <div className="px-8 py-6 border-b border-white/5 bg-white/1">
                <h2 className="font-bold text-white flex items-center">
                  <Sliders className="mr-2 text-purple-400" size={20} />
                  Evaluation & Proctoring Thresholds
                </h2>
              </div>
              <div className="p-8 space-y-6">
                <div>
                  <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500 mb-1.5">
                    Passing Score Threshold (0.0 - 10.0)
                  </label>
                  <input
                    type="number"
                    value={config.passing_score_threshold}
                    onChange={(e) => handleChange('passing_score_threshold', parseFloat(e.target.value))}
                    className="w-full bg-slate-900 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:ring-1 focus:ring-purple-500 outline-none"
                    step="0.1"
                    min="0"
                    max="10"
                  />
                </div>

                <div>
                  <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500 mb-1.5">
                    Max Questions per Interview Drive
                  </label>
                  <input
                    type="number"
                    value={config.max_questions_per_drive}
                    onChange={(e) => handleChange('max_questions_per_drive', parseInt(e.target.value))}
                    className="w-full bg-slate-900 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:ring-1 focus:ring-purple-500 outline-none"
                    min="1"
                  />
                </div>

                <div>
                  <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500 mb-1.5">
                    Proctor Tab Switch Warning Limit (Count)
                  </label>
                  <input
                    type="number"
                    value={config.proctor_tab_switch_threshold}
                    onChange={(e) => handleChange('proctor_tab_switch_threshold', parseInt(e.target.value))}
                    className="w-full bg-slate-900 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:ring-1 focus:ring-purple-500 outline-none"
                    min="1"
                  />
                </div>

                <div>
                  <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500 mb-1.5">
                    Proctor Paste Detection Length (Chars)
                  </label>
                  <input
                    type="number"
                    value={config.proctor_paste_threshold}
                    onChange={(e) => handleChange('proctor_paste_threshold', parseInt(e.target.value))}
                    className="w-full bg-slate-900 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:ring-1 focus:ring-purple-500 outline-none"
                    min="1"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Notifications & Logging Toggle Cards */}
        <div className="mt-8 bg-white/2 border border-white/5 rounded-3xl overflow-hidden shadow-xl">
          <div className="px-8 py-6 border-b border-white/5 bg-white/1">
            <h2 className="font-bold text-white flex items-center">
              <Mail className="mr-2 text-violet-400" size={20} />
              Notifications & Logging
            </h2>
          </div>
          <div className="p-8 space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-bold text-white">Email Notifications</p>
                <p className="text-xs text-slate-500 mt-1">
                  Send email notifications for interview booking, reminders, and evaluation reports.
                </p>
              </div>
              <button
                onClick={() => handleChange('enable_email_notifications', !config.enable_email_notifications)}
                className={`relative w-12 h-6 rounded-full transition-colors cursor-pointer ${
                  config.enable_email_notifications ? 'bg-purple-600' : 'bg-slate-700'
                }`}
              >
                <span
                  className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full transition-transform ${
                    config.enable_email_notifications ? 'translate-x-6' : 'translate-x-0'
                  }`}
                />
              </button>
            </div>

            <div className="flex items-center justify-between border-t border-white/5 pt-6">
              <div>
                <p className="text-sm font-bold text-white">Audit Logging</p>
                <p className="text-xs text-slate-500 mt-1">
                  Enable secure, persistent audit trails for all configuration edits and administrative actions.
                </p>
              </div>
              <button
                onClick={() => handleChange('enable_audit_logging', !config.enable_audit_logging)}
                className={`relative w-12 h-6 rounded-full transition-colors cursor-pointer ${
                  config.enable_audit_logging ? 'bg-purple-600' : 'bg-slate-700'
                }`}
              >
                <span
                  className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full transition-transform ${
                    config.enable_audit_logging ? 'translate-x-6' : 'translate-x-0'
                  }`}
                />
              </button>
            </div>
          </div>
        </div>

        {/* Change History Section */}
        <div className="mt-8 bg-white/2 border border-white/5 rounded-3xl overflow-hidden shadow-xl">
          <div className="px-8 py-6 border-b border-white/5 bg-white/1">
            <h2 className="font-bold text-white flex items-center">
              <History className="mr-2 text-sky-400" size={20} />
              Configuration Edit Logs (Database History)
            </h2>
          </div>
          <div className="p-8">
            {history.length === 0 ? (
              <div className="text-center text-slate-500 py-8 text-sm">
                No configurations have been modified yet. Showing active defaults.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm border-collapse">
                  <thead>
                    <tr className="border-b border-white/10 text-slate-400 text-xs uppercase tracking-wider">
                      <th className="pb-3 font-semibold">Config Key</th>
                      <th className="pb-3 font-semibold">Old Value</th>
                      <th className="pb-3 font-semibold">New Value</th>
                      <th className="pb-3 font-semibold">Edited By</th>
                      <th className="pb-3 font-semibold">Timestamp</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {history.map((log) => (
                      <tr key={log.id} className="hover:bg-white/1 transition-colors">
                        <td className="py-4 font-mono text-xs text-purple-300">{log.key}</td>
                        <td className="py-4 font-mono text-xs text-slate-500 truncate max-w-[120px]" title={JSON.stringify(log.old_value)}>
                          {log.old_value !== null ? String(log.old_value) : <span className="text-slate-600 font-sans italic">None (Default)</span>}
                        </td>
                        <td className="py-4 font-mono text-xs text-emerald-400 truncate max-w-[120px]" title={JSON.stringify(log.new_value)}>
                          {String(log.new_value)}
                        </td>
                        <td className="py-4 text-xs text-slate-400 flex items-center">
                          <User size={12} className="mr-1 text-slate-500" />
                          User #{log.changed_by_user_id}
                        </td>
                        <td className="py-4 text-xs text-slate-400">
                          {new Date(log.changed_at).toLocaleString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        {/* Action Buttons */}
        <div className="mt-8 flex flex-col-reverse sm:flex-row justify-end gap-3">
          <button
            onClick={handleReset}
            disabled={saving}
            className="px-6 py-3 bg-white/5 hover:bg-white/10 text-slate-400 rounded-xl text-sm font-bold transition-all cursor-pointer disabled:opacity-50"
          >
            Reset to System Defaults
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center space-x-2 px-6 py-3 bg-purple-600 hover:bg-purple-500 text-white rounded-xl text-sm font-bold shadow-lg shadow-purple-900/30 transition-all active:scale-95 disabled:opacity-50 cursor-pointer"
          >
            {saving ? (
              <>
                <RefreshCcw size={16} className="animate-spin" />
                <span>Saving...</span>
              </>
            ) : (
              <>
                <Save size={16} />
                <span>Save & Apply Settings</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default SystemConfig;
