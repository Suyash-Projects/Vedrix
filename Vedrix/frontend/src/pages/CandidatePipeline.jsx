import { useState, useEffect, useCallback } from 'react';
import {
  Users,
  Mail,
  Calendar,
  CheckCircle,
  Clock,
  Star,
  Download,
  Upload,
  RefreshCcw,
  Eye,
  Search
} from 'lucide-react';
import apiClient from '../services/api';
import { useNavigate } from 'react-router-dom';

const CandidatePipeline = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [drives, setDrives] = useState([]);
  const [selectedDrive, setSelectedDrive] = useState(null);
  const [candidates, setCandidates] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [showImport, setShowImport] = useState(false);
  const [csvContent, setCsvContent] = useState('');
  const [importResult, setImportResult] = useState(null);
  const [importing, setImporting] = useState(false);

  const stages = [
    { key: 'invited', label: 'Invited', color: 'bg-blue-500/10 text-blue-400 border-blue-500/20', icon: Mail },
    { key: 'scheduled', label: 'Scheduled', color: 'bg-amber-500/10 text-amber-400 border-amber-500/20', icon: Calendar },
    { key: 'in_progress', label: 'In Progress', color: 'bg-purple-500/10 text-purple-400 border-purple-500/20', icon: Clock },
    { key: 'completed', label: 'Completed', color: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20', icon: CheckCircle },
    { key: 'reviewed', label: 'Reviewed', color: 'bg-violet-500/10 text-violet-400 border-violet-500/20', icon: Star },
  ];

  const fetchDrives = useCallback(async () => {
    try {
      setLoading(true);
      const res = await apiClient.get('/hr/drives');
      setDrives(res.data);
      if (res.data.length > 0 && !selectedDrive) {
        setSelectedDrive(res.data[0]);
      }
    } catch {
      setError('Failed to fetch drives');
    } finally {
      setLoading(false);
    }
  }, [selectedDrive]);

  const fetchCandidates = useCallback(async (driveId) => {
    try {
      const res = await apiClient.get(`/hr/drives/${driveId}/candidates`);
      setCandidates(res.data.candidates || []);
    } catch {
      setError('Failed to fetch candidates');
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchDrives();
  }, [fetchDrives]);

  useEffect(() => {
    if (selectedDrive) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      fetchCandidates(selectedDrive.id);
    }
  }, [selectedDrive, fetchCandidates]);

  const getCandidatesByStage = (stage) => {
    return candidates.filter(c => {
      if (stage === 'invited') return !c.is_used && !c.session_status;
      if (stage === 'scheduled') return c.session_status === 'scheduled';
      if (stage === 'in_progress') return c.session_status === 'in_progress';
      if (stage === 'completed') return c.session_status === 'completed';
      if (stage === 'reviewed') return c.session_status === 'completed' && c.overall_score;
      return false;
    });
  };

  const handleDriveSelect = (drive) => {
    setSelectedDrive(drive);
  };

  const handleSearch = (e) => {
    setSearchTerm(e.target.value);
  };

  const filteredCandidates = candidates.filter(c =>
    c.candidate_email?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    c.candidate_name?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleImportChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (event) => {
        setCsvContent(event.target.result);
      };
      reader.readAsText(file);
    }
  };

  const handleValidateImport = async () => {
    try {
      setImporting(true);
      const res = await apiClient.post('/hr/import/validate', { csv_content: csvContent });
      setImportResult(res.data);
    } catch {
      setError('Failed to validate import');
    } finally {
      setImporting(false);
    }
  };

  const handleExecuteImport = async () => {
    try {
      setImporting(true);
      const res = await apiClient.post('/hr/import/execute', { csv_content: csvContent });
      setImportResult(res.data);
      setCsvContent('');
      setShowImport(false);
      fetchCandidates(selectedDrive.id);
    } catch {
      setError('Failed to execute import');
    } finally {
      setImporting(false);
    }
  };

  const handleDownloadTemplate = async () => {
    try {
      const res = await apiClient.get('/hr/import/template', { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'candidate_import_template.csv');
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch {
      setError('Failed to download template');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#020617] flex items-center justify-center">
        <div className="text-center">
          <RefreshCcw size={32} className="animate-spin text-purple-400 mx-auto mb-4" />
          <p className="text-slate-400">Loading candidate pipeline...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#020617] text-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-10">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight">Candidate Pipeline</h1>
            <p className="text-slate-500 mt-1">Track candidates through the hiring process</p>
          </div>
          <div className="flex items-center space-x-3">
            <button
              onClick={handleDownloadTemplate}
              className="flex items-center space-x-2 bg-white/5 border border-white/10 text-slate-300 px-4 py-2 rounded-xl text-sm font-bold hover:bg-white/10 transition-all"
            >
              <Download size={16} />
              <span>Template</span>
            </button>
            <button
              onClick={() => setShowImport(!showImport)}
              className="flex items-center space-x-2 bg-purple-600/10 border border-purple-500/20 text-purple-400 px-4 py-2 rounded-xl text-sm font-bold hover:bg-purple-600/20 transition-all"
            >
              <Upload size={16} />
              <span>Import CSV</span>
            </button>
          </div>
        </div>

        {error && (
          <div className="mb-6 p-4 rounded-xl text-sm font-bold border bg-red-500/10 border-red-500/20 text-red-400">
            {error}
          </div>
        )}

        {/* Drive Selector */}
        <div className="mb-6">
          <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500 mb-1.5">
            Select Job Drive
          </label>
          <select
            value={selectedDrive?.id || ''}
            onChange={(e) => {
              const drive = drives.find(d => d.id === parseInt(e.target.value));
              handleDriveSelect(drive);
            }}
            className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:ring-1 focus:ring-purple-500 outline-none"
          >
            {drives.map(drive => (
              <option key={drive.id} value={drive.id}>{drive.title} ({drive.job_role})</option>
            ))}
          </select>
        </div>

        {/* Pipeline Stages */}
        {selectedDrive && (
          <div className="mb-8">
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              {stages.map((stage) => {
                const count = getCandidatesByStage(stage.key).length;
                const Icon = stage.icon;
                return (
                  <div key={stage.key} className="bg-white/2 border border-white/5 p-6 rounded-2xl">
                    <div className="flex items-center justify-between mb-4">
                      <div className="w-10 h-10 bg-white/5 rounded-xl flex items-center justify-center">
                        <Icon className={stage.color.split(' ')[1]} size={20} />
                      </div>
                      <span className={`px-3 py-1 rounded-full text-xs font-bold ${stage.color}`}>
                        {count}
                      </span>
                    </div>
                    <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest">{stage.label}</p>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Search */}
        <div className="mb-6">
          <div className="relative">
            <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 text-slate-500" size={18} />
            <input
              type="text"
              value={searchTerm}
              onChange={handleSearch}
              className="w-full bg-white/5 border border-white/10 rounded-xl pl-12 pr-4 py-3 text-sm text-white placeholder-slate-500 focus:ring-1 focus:ring-purple-500 outline-none"
              placeholder="Search candidates by email or name..."
            />
          </div>
        </div>

        {/* Candidates Table */}
        <div className="bg-white/2 border border-white/5 rounded-3xl overflow-hidden">
          <div className="px-8 py-6 border-b border-white/5">
            <h2 className="font-bold text-white flex items-center">
              <Users size={18} className="mr-2 text-purple-400" />
              Candidates ({filteredCandidates.length})
            </h2>
          </div>

          {filteredCandidates.length === 0 ? (
            <div className="p-12 text-center text-slate-500">No candidates found.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead>
                  <tr className="text-[10px] font-black text-slate-500 uppercase tracking-widest border-b border-white/5">
                    <th className="px-8 py-4">Candidate</th>
                    <th className="px-8 py-4">Stage</th>
                    <th className="px-8 py-4">Score</th>
                    <th className="px-8 py-4">Date</th>
                    <th className="px-8 py-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {filteredCandidates.map((candidate, idx) => {
                    const stage = stages.find(s => {
                      if (s.key === 'invited') return !candidate.is_used && !candidate.session_status;
                      if (s.key === 'scheduled') return candidate.session_status === 'scheduled';
                      if (s.key === 'in_progress') return candidate.session_status === 'in_progress';
                      if (s.key === 'completed') return candidate.session_status === 'completed';
                      if (s.key === 'reviewed') return candidate.session_status === 'completed' && candidate.overall_score;
                      return false;
                    }) || stages[0];

                    return (
                      <tr key={idx} className="hover:bg-white/[0.03] transition-colors">
                        <td className="px-8 py-5">
                          <div>
                            <p className="font-bold text-white text-sm">{candidate.candidate_name || 'N/A'}</p>
                            <p className="text-xs text-slate-500">{candidate.candidate_email}</p>
                          </div>
                        </td>
                        <td className="px-8 py-5">
                          <span className={`px-3 py-1 rounded-full text-[9px] font-black uppercase border ${stage.color}`}>
                            {stage.label}
                          </span>
                        </td>
                        <td className="px-8 py-5">
                          {candidate.overall_score ? (
                            <span className={`font-black ${
                              candidate.overall_score >= 8 ? 'text-emerald-400' :
                              candidate.overall_score >= 5 ? 'text-amber-400' : 'text-red-400'
                            }`}>
                              {candidate.overall_score.toFixed(1)}
                            </span>
                          ) : (
                            <span className="text-slate-500">—</span>
                          )}
                        </td>
                        <td className="px-8 py-5 text-sm text-slate-400">
                          {candidate.created_at ? new Date(candidate.created_at).toLocaleDateString() : '—'}
                        </td>
                        <td className="px-8 py-5 text-right">
                          {candidate.session_id && (
                            <button
                              onClick={() => navigate(`/replay/${candidate.session_id}`)}
                              className="text-slate-500 hover:text-purple-400 p-1.5 rounded-lg hover:bg-purple-500/10 transition-colors"
                              title="View interview replay"
                            >
                              <Eye size={14} />
                            </button>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Import Modal */}
        {showImport && (
          <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-[200]">
            <div className="bg-[#0f1420] border border-white/10 rounded-3xl p-8 w-full max-w-lg mx-4 shadow-2xl">
              <div className="flex justify-between items-center mb-6">
                <h3 className="text-xl font-bold text-white">Import Candidates from CSV</h3>
                <button onClick={() => setShowImport(false)} className="text-slate-500 hover:text-white">
                  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                </button>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-[10px] font-black uppercase tracking-widest text-slate-500 mb-1.5">
                    Upload CSV File
                  </label>
                  <input
                    type="file"
                    accept=".csv"
                    onChange={handleImportChange}
                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white"
                  />
                </div>

                {csvContent && (
                  <div className="bg-white/2 border border-white/5 rounded-xl p-4">
                    <p className="text-xs text-slate-400 mb-2">Preview:</p>
                    <pre className="text-xs text-slate-300 font-mono overflow-auto max-h-32">
                      {csvContent.split('\n').slice(0, 5).join('\n')}
                    </pre>
                  </div>
                )}

                {importResult && (
                  <div className="bg-white/2 border border-white/5 rounded-xl p-4">
                    <p className="text-sm font-bold text-white mb-2">Validation Results:</p>
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <p className="text-slate-400">Total Rows: <span className="text-white font-bold">{importResult.total_rows}</span></p>
                      <p className="text-slate-400">Valid: <span className="text-emerald-400 font-bold">{importResult.valid_rows}</span></p>
                      <p className="text-slate-400">Invalid: <span className="text-red-400 font-bold">{importResult.invalid_rows}</span></p>
                      <p className="text-slate-400">Duplicates: <span className="text-amber-400 font-bold">{importResult.duplicate_rows}</span></p>
                    </div>
                    {importResult.errors.length > 0 && (
                      <div className="mt-2">
                        <p className="text-xs text-red-400 font-bold mb-1">Errors:</p>
                        {importResult.errors.slice(0, 3).map((err, idx) => (
                          <p key={idx} className="text-xs text-slate-400">Row {err.row}: {err.errors.join(', ')}</p>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                <div className="flex justify-end space-x-3 pt-2">
                  <button
                    onClick={() => setShowImport(false)}
                    className="px-6 py-3 bg-white/5 hover:bg-white/10 text-slate-400 rounded-xl text-sm font-bold transition-all"
                  >
                    Cancel
                  </button>
                  {csvContent && !importResult && (
                    <button
                      onClick={handleValidateImport}
                      disabled={importing}
                      className="px-6 py-3 bg-amber-600 hover:bg-amber-500 text-white rounded-xl text-sm font-bold transition-all disabled:opacity-50"
                    >
                      {importing ? 'Validating...' : 'Validate'}
                    </button>
                  )}
                  {importResult && importResult.valid_rows > 0 && (
                    <button
                      onClick={handleExecuteImport}
                      disabled={importing}
                      className="px-6 py-3 bg-purple-600 hover:bg-purple-500 text-white rounded-xl text-sm font-bold shadow-lg shadow-purple-900/30 transition-all active:scale-95 disabled:opacity-50"
                    >
                      {importing ? 'Importing...' : `Import ${importResult.valid_rows} Candidates`}
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default CandidatePipeline;
