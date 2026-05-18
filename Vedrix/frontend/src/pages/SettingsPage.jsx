import { useState, useEffect, useCallback } from 'react';
import {
  User,
  Shield,
  Cookie,
  Check,
  AlertCircle,
  Download,
  Trash2,
} from 'lucide-react';
import apiClient from '../services/api';
import useAuthStore from '../store/useAuthStore';

const SettingsPage = () => {
  const { user } = useAuthStore();
  const [activeTab, setActiveTab] = useState('profile');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [consents, setConsents] = useState([]);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  const fetchConsents = useCallback(async () => {
    try {
      const res = await apiClient.get('/users/consent');
      setConsents(res.data.consents || []);
    } catch {
      // Silently fail - consent may not be set up yet
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchConsents();
  }, [fetchConsents]);

  const handleConsentToggle = async (purpose, granted) => {
    try {
      setError('');
      setSuccess('');
      await apiClient.post('/users/consent', { purpose, granted });
      setSuccess('Consent preferences updated');
      fetchConsents();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to update consent');
    }
  };

  const handleExportData = async () => {
    try {
      setLoading(true);
      setError('');
      const res = await apiClient.get('/users/export-data');
      const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `vedrix_data_export_${new Date().toISOString().split('T')[0]}.json`;
      a.click();
      URL.revokeObjectURL(url);
      setSuccess('Data export downloaded successfully');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to export data');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteAccount = async () => {
    try {
      setLoading(true);
      setError('');
      await apiClient.post('/users/delete-account');
      setSuccess('Account deletion requested. Your data will be deleted in 30 days.');
      setShowDeleteConfirm(false);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to request account deletion');
    } finally {
      setLoading(false);
    }
  };

  const tabs = [
    { key: 'profile', label: 'Profile', icon: User },
    { key: 'privacy', label: 'Privacy & Consent', icon: Shield },
    { key: 'data', label: 'Data Management', icon: Download },
  ];

  return (
    <div className="min-h-screen bg-[#020617] text-white">
      <div className="max-w-4xl mx-auto px-8 py-10">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-extrabold tracking-tight">Settings</h1>
          <p className="text-slate-500 mt-1">Manage your account preferences and privacy settings</p>
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

        {/* Tabs */}
        <div className="flex space-x-2 mb-8 border-b border-white/5 pb-2">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`flex items-center space-x-2 px-5 py-2.5 rounded-t-xl text-sm font-bold uppercase tracking-wider transition-colors border-b-2 ${
                  activeTab === tab.key
                    ? 'text-purple-400 border-purple-500 bg-white/5'
                    : 'text-slate-500 border-transparent hover:text-white hover:bg-white/5'
                }`}
              >
                <Icon size={16} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        {/* Profile Tab */}
        {activeTab === 'profile' && (
          <div className="bg-white/2 border border-white/5 rounded-3xl p-8">
            <h2 className="text-xl font-bold mb-6 flex items-center">
              <User className="mr-2 text-purple-400" size={20} />
              Profile Information
            </h2>
            <div className="grid grid-cols-2 gap-6">
              <div>
                <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Email</p>
                <p className="text-white font-bold">{user?.email}</p>
              </div>
              <div>
                <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Username</p>
                <p className="text-white font-bold">@{user?.username}</p>
              </div>
              <div>
                <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Name</p>
                <p className="text-white font-bold">{user?.first_name} {user?.last_name}</p>
              </div>
              <div>
                <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Role</p>
                <p className="text-white font-bold capitalize">{user?.user_type}</p>
              </div>
            </div>
          </div>
        )}

        {/* Privacy Tab */}
        {activeTab === 'privacy' && (
          <div className="space-y-6">
            <div className="bg-white/2 border border-white/5 rounded-3xl p-8">
              <h2 className="text-xl font-bold mb-6 flex items-center">
                <Shield className="mr-2 text-emerald-400" size={20} />
                Data Processing Consent
              </h2>
              <div className="space-y-4">
                {consents.map((consent) => (
                  <div key={consent.purpose} className="flex items-center justify-between p-4 bg-white/5 rounded-xl">
                    <div>
                      <p className="text-white font-bold text-sm capitalize">
                        {consent.purpose.replace('_', ' ')}
                      </p>
                      <p className="text-slate-500 text-xs">
                        {consent.granted ? 'Consent granted' : 'Consent not granted'}
                      </p>
                    </div>
                    <button
                      onClick={() => handleConsentToggle(consent.purpose, !consent.granted)}
                      disabled={consent.purpose === 'cookies_essential'}
                      className={`w-12 h-6 rounded-full transition-colors ${
                        consent.granted ? 'bg-emerald-500' : 'bg-slate-600'
                      } ${consent.purpose === 'cookies_essential' ? 'opacity-50 cursor-not-allowed' : ''}`}
                    >
                      <span
                        className={`block w-5 h-5 bg-white rounded-full transition-transform ${
                          consent.granted ? 'translate-x-6' : 'translate-x-0.5'
                        }`}
                      />
                    </button>
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-white/2 border border-white/5 rounded-3xl p-8">
              <h2 className="text-xl font-bold mb-6 flex items-center">
                <Cookie className="mr-2 text-amber-400" size={20} />
                Cookie Preferences
              </h2>
              <p className="text-slate-400 text-sm mb-4">
                Manage your cookie preferences. Essential cookies cannot be disabled as they are
                required for the website to function.
              </p>
              <button
                onClick={() => {
                  localStorage.removeItem('vedrix_cookie_consent');
                  window.location.reload();
                }}
                className="px-4 py-2 bg-white/5 border border-white/10 text-slate-300 rounded-xl text-sm font-bold hover:bg-white/10 transition-all"
              >
                Reset Cookie Preferences
              </button>
            </div>
          </div>
        )}

        {/* Data Management Tab */}
        {activeTab === 'data' && (
          <div className="space-y-6">
            <div className="bg-white/2 border border-white/5 rounded-3xl p-8">
              <h2 className="text-xl font-bold mb-6 flex items-center">
                <Download className="mr-2 text-blue-400" size={20} />
                Export Your Data
              </h2>
              <p className="text-slate-400 text-sm mb-6">
                Download all your personal data including profile information, interview history,
                feedback, and consent records in JSON format.
              </p>
              <button
                onClick={handleExportData}
                disabled={loading}
                className="flex items-center space-x-2 px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-sm font-bold shadow-lg shadow-blue-900/30 transition-all active:scale-95 disabled:opacity-50"
              >
                <Download size={16} />
                <span>{loading ? 'Exporting...' : 'Export My Data'}</span>
              </button>
            </div>

            <div className="bg-white/2 border border-white/5 rounded-3xl p-8">
              <h2 className="text-xl font-bold mb-6 flex items-center">
                <Trash2 className="mr-2 text-red-400" size={20} />
                Delete Your Account
              </h2>
              <p className="text-slate-400 text-sm mb-6">
                Request deletion of your account and all associated personal data.
                This action cannot be undone. Your data will be permanently deleted after a 30-day grace period.
              </p>
              {!showDeleteConfirm ? (
                <button
                  onClick={() => setShowDeleteConfirm(true)}
                  className="flex items-center space-x-2 px-6 py-3 bg-red-600/10 border border-red-500/20 text-red-400 rounded-xl text-sm font-bold hover:bg-red-600/20 transition-all"
                >
                  <Trash2 size={16} />
                  <span>Request Account Deletion</span>
                </button>
              ) : (
                <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-6">
                  <p className="text-red-400 font-bold mb-4">
                    Are you sure? This action cannot be undone.
                  </p>
                  <div className="flex space-x-3">
                    <button
                      onClick={handleDeleteAccount}
                      disabled={loading}
                      className="px-6 py-3 bg-red-600 hover:bg-red-500 text-white rounded-xl text-sm font-bold transition-all disabled:opacity-50"
                    >
                      {loading ? 'Processing...' : 'Yes, Delete My Account'}
                    </button>
                    <button
                      onClick={() => setShowDeleteConfirm(false)}
                      className="px-6 py-3 bg-white/5 hover:bg-white/10 text-slate-400 rounded-xl text-sm font-bold transition-all"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default SettingsPage;
