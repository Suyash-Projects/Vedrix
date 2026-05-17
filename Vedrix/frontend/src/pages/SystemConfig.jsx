import { useState, useEffect, useCallback } from 'react';
import {
  Save,
  RefreshCcw,
  Zap,
  Shield,
  Mail,
  AlertTriangle,
  CheckCircle,
  Info
} from 'lucide-react';
import apiClient from '../services/api';
import { useNavigate } from 'react-router-dom';

const SystemConfig = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [config, setConfig] = useState({
    ai_provider: 'groq',
    rate_limit_per_minute: 60,
    session_timeout_minutes: 30,
    max_interview_duration_minutes: 90,
    enable_email_notifications: true,
    enable_audit_logging: true,
  });
  const [aiHealth, setAiHealth] = useState(null);

  const fetchConfig = useCallback(async () => {
    try {
      setLoading(true);
      setError('');

      // Fetch AI health to show available providers
      const [aiRes] = await Promise.allSettled([
        apiClient.get('/admin/ai-health'),
      ]);

      if (aiRes.status === 'fulfilled') {
        setAiHealth(aiRes.value.data);
      }

      // Load current config from localStorage or use defaults
      const savedConfig = localStorage.getItem('vedrix_system_config');
      if (savedConfig) {
        setConfig(JSON.parse(savedConfig));
      }
    } catch {
      setError('Failed to fetch system configuration');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchConfig();
  }, [fetchConfig]);

  const handleSave = async () => {
    try {
      setSaving(true);
      setError('');
      setSuccess('');

      // Save to localStorage (in production, this would be a backend endpoint)
      localStorage.setItem('vedrix_system_config', JSON.stringify(config));

      setSuccess('Configuration saved successfully');
      setTimeout(() => setSuccess(''), 3000);
    } catch {
      setError('Failed to save configuration');
    } finally {
      setSaving(false);
    }
  };

  const handleReset = () => {
    setConfig({
      ai_provider: 'groq',
      rate_limit_per_minute: 60,
      session_timeout_minutes: 30,
      max_interview_duration_minutes: 90,
      enable_email_notifications: true,
      enable_audit_logging: true,
    });
    localStorage.removeItem('vedrix_system_config');
    setSuccess('Configuration reset to defaults');
    setTimeout(() => setSuccess(''), 3000);
  };

  const handleChange = (key, value) => {
    setConfig(prev => ({ ...prev, [key]: value }));
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#020617] flex items-center justify-center">
        <div className="text-center">
          <RefreshCcw size={32} className="animate-spin text-purple-400 mx-auto mb-4" />
          <p className="text-slate-400">Loading configuration...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#020617] text-white">
      <div className="max-w-4xl mx-auto px-8 py-10">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight">System Configuration</h1>
            <p className="text-slate-500 mt-1">Manage AI providers, rate limits, and system settings</p>
          </div>
          <div className="flex items-center space-x-3">
            <button
              onClick={() => navigate('/admin')}
              className="flex items-center space-x-2 bg-white/5 border border-white/10 text-slate-300 px-4 py-2 rounded-xl text-sm font-bold hover:bg-white/10 transition-all"
            >
              <span>Back to Admin</span>
            </button>
            <button
              onClick={fetchConfig}
              className="flex items-center space-x-2 bg-white/5 border border-white/10 text-slate-300 px-4 py-2 rounded-xl text-sm font-bold hover:bg-white/10 transition-all"
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

        {/* AI Provider Configuration */}
        <div className="mb-8 bg-white/2 border border-white/5 rounded-3xl overflow-hidden">
          <div className="px-8 py-6 border-b border-white/5">
            <h2 className="font-bold text-white flex items-center">
              <Zap className="mr-2 text-amber-400" size={20} />
              AI Provider Settings
            </h2>
          </div>
          <div className="p-8 space-y-6">
            <div>
              <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500 mb-1.5">
                Primary AI Provider
              </label>
              <select
                value={config.ai_provider}
                onChange={(e) => handleChange('ai_provider', e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:ring-1 focus:ring-purple-500 outline-none"
              >
                <option value="groq">Groq (Llama 3.1 70B)</option>
                <option value="deepseek">DeepSeek</option>
                <option value="nvidia">NVIDIA</option>
                <option value="openrouter">OpenRouter</option>
              </select>
              <p className="text-xs text-slate-500 mt-2">
                Select the primary AI provider for interview questions and analysis.
              </p>
            </div>

            {aiHealth && (
              <div className="bg-white/2 border border-white/5 rounded-xl p-4">
                <p className="text-xs font-bold text-slate-400 mb-2">Available Providers:</p>
                <div className="flex flex-wrap gap-2">
                  {aiHealth.circuit_breakers && Object.entries(aiHealth.circuit_breakers).map(([name, cb]) => (
                    <span
                      key={name}
                      className={`px-3 py-1 rounded-full text-[10px] font-black uppercase border ${
                        cb.state === 'CLOSED'
                          ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                          : cb.state === 'OPEN'
                          ? 'bg-red-500/10 text-red-400 border-red-500/20'
                          : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
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

        {/* Rate Limiting & Session Settings */}
        <div className="mb-8 bg-white/2 border border-white/5 rounded-3xl overflow-hidden">
          <div className="px-8 py-6 border-b border-white/5">
            <h2 className="font-bold text-white flex items-center">
              <Shield className="mr-2 text-emerald-400" size={20} />
              Rate Limiting & Session Settings
            </h2>
          </div>
          <div className="p-8 space-y-6">
            <div>
              <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500 mb-1.5">
                Rate Limit (requests per minute)
              </label>
              <input
                type="number"
                value={config.rate_limit_per_minute}
                onChange={(e) => handleChange('rate_limit_per_minute', parseInt(e.target.value))}
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:ring-1 focus:ring-purple-500 outline-none"
                min="10"
                max="200"
              />
              <p className="text-xs text-slate-500 mt-2">
                Maximum number of API requests allowed per minute per user.
              </p>
            </div>

            <div>
              <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500 mb-1.5">
                Session Timeout (minutes)
              </label>
              <input
                type="number"
                value={config.session_timeout_minutes}
                onChange={(e) => handleChange('session_timeout_minutes', parseInt(e.target.value))}
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:ring-1 focus:ring-purple-500 outline-none"
                min="5"
                max="120"
              />
              <p className="text-xs text-slate-500 mt-2">
                Time of inactivity before a user session expires.
              </p>
            </div>

            <div>
              <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500 mb-1.5">
                Max Interview Duration (minutes)
              </label>
              <input
                type="number"
                value={config.max_interview_duration_minutes}
                onChange={(e) => handleChange('max_interview_duration_minutes', parseInt(e.target.value))}
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:ring-1 focus:ring-purple-500 outline-none"
                min="15"
                max="180"
              />
              <p className="text-xs text-slate-500 mt-2">
                Maximum allowed duration for a single interview session.
              </p>
            </div>
          </div>
        </div>

        {/* Notifications & Logging */}
        <div className="mb-8 bg-white/2 border border-white/5 rounded-3xl overflow-hidden">
          <div className="px-8 py-6 border-b border-white/5">
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
                  Send email notifications for interview invites and credentials.
                </p>
              </div>
              <button
                onClick={() => handleChange('enable_email_notifications', !config.enable_email_notifications)}
                className={`relative w-12 h-6 rounded-full transition-colors ${
                  config.enable_email_notifications ? 'bg-emerald-500' : 'bg-slate-600'
                }`}
              >
                <span
                  className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full transition-transform ${
                    config.enable_email_notifications ? 'translate-x-6' : 'translate-x-0'
                  }`}
                />
              </button>
            </div>

            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-bold text-white">Audit Logging</p>
                <p className="text-xs text-slate-500 mt-1">
                  Log all system actions for security and compliance.
                </p>
              </div>
              <button
                onClick={() => handleChange('enable_audit_logging', !config.enable_audit_logging)}
                className={`relative w-12 h-6 rounded-full transition-colors ${
                  config.enable_audit_logging ? 'bg-emerald-500' : 'bg-slate-600'
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

        {/* Info Box */}
        <div className="mb-8 bg-blue-500/10 border border-blue-500/20 rounded-2xl p-6">
          <div className="flex items-start">
            <Info className="text-blue-400 mr-3 mt-0.5" size={20} />
            <div>
              <p className="text-sm font-bold text-blue-400 mb-1">Configuration Note</p>
              <p className="text-xs text-slate-300">
                These settings are stored locally in your browser. In production, they would be saved to the database
                and applied across all instances. Changes to AI providers and rate limits take effect immediately.
              </p>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex justify-end space-x-3">
          <button
            onClick={handleReset}
            className="px-6 py-3 bg-white/5 hover:bg-white/10 text-slate-400 rounded-xl text-sm font-bold transition-all"
          >
            Reset to Defaults
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center space-x-2 px-6 py-3 bg-purple-600 hover:bg-purple-500 text-white rounded-xl text-sm font-bold shadow-lg shadow-purple-900/30 transition-all active:scale-95 disabled:opacity-50"
          >
            <Save size={16} />
            <span>{saving ? 'Saving...' : 'Save Configuration'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default SystemConfig;
