import { useState, useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Database, GitBranch, Globe, CheckCircle2, XCircle, Clock, RefreshCw, Code2 } from 'lucide-react';
import apiClient from '../services/api';

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  visible: (i) => ({ opacity: 1, y: 0, transition: { delay: i * 0.08, duration: 0.5, ease: 'easeOut' } })
};

const statusConfig = {
  success: { icon: CheckCircle2, color: 'text-emerald-400', bg: 'bg-emerald-500/10 border-emerald-500/20', label: 'Success' },
  failed: { icon: XCircle, color: 'text-red-400', bg: 'bg-red-500/10 border-red-500/20', label: 'Failed' },
  pending: { icon: Clock, color: 'text-amber-400', bg: 'bg-amber-500/10 border-amber-500/20', label: 'Pending' },
};

const sourceIcons = {
  github: GitBranch,
  linkedin: Globe,
};

const EnrichmentSummary = () => {
  const { candidateId } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.get(`/hr/candidates/${candidateId}/enrichment`);
      setData(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load enrichment data');
    } finally {
      setLoading(false);
    }
  }, [candidateId]);

  useEffect(() => { fetchData(); }, [fetchData]);

  if (loading) {
    return (
      <div className="min-h-screen bg-[#020617] text-white">
        <div className="max-w-5xl mx-auto px-8 py-12 space-y-6">
          <div className="h-8 bg-white/5 rounded w-1/3 animate-pulse" />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {[...Array(2)].map((_, i) => (
              <div key={i} className="bg-white/[0.03] border border-white/5 rounded-3xl p-6 h-48 animate-pulse" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-[#020617] text-white flex items-center justify-center">
        <div className="text-center space-y-4">
          <p className="text-red-400 text-lg font-bold">{error}</p>
          <button onClick={fetchData}
            className="inline-flex items-center gap-2 bg-purple-600 hover:bg-purple-500 text-white font-bold px-6 py-3 rounded-2xl transition-all"
            aria-label="Retry loading enrichment data"
          >
            <RefreshCw size={16} /> Retry
          </button>
        </div>
      </div>
    );
  }

  const sources = data?.sources || [];
  const skills = data?.skill_verifications || [];
  const githubRepos = data?.github_repos_indexed ?? 0;

  return (
    <div className="min-h-screen bg-[#020617] text-white font-sans">
      <div className="fixed bottom-0 right-[-5%] w-[30%] h-[40%] bg-indigo-900/10 blur-[150px] rounded-full pointer-events-none" />

      <div className="max-w-5xl mx-auto px-8 py-12 space-y-8 relative z-10">
        {/* Header */}
        <motion.div initial="hidden" animate="visible" custom={0} variants={fadeUp}>
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 bg-gradient-to-tr from-purple-600 to-indigo-400 rounded-2xl flex items-center justify-center shadow-xl shadow-purple-900/30">
              <Database size={24} className="text-white" />
            </div>
            <div>
              <h1 className="text-3xl font-black text-white tracking-tight">Enrichment Summary</h1>
              <p className="text-slate-500 text-sm">Candidate data enrichment from external sources</p>
            </div>
          </div>
        </motion.div>

        {/* GitHub Repos Count */}
        <motion.div initial="hidden" animate="visible" custom={1} variants={fadeUp}
          className="bg-white/[0.03] border border-white/5 rounded-3xl p-6 flex items-center gap-4"
        >
          <div className="w-12 h-12 bg-white/5 rounded-2xl flex items-center justify-center">
            <Code2 size={22} className="text-purple-400" />
          </div>
          <div>
            <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest">GitHub Repos Indexed</p>
            <p className="text-3xl font-black text-white">{githubRepos}</p>
          </div>
        </motion.div>

        {/* Data Sources */}
        <motion.div initial="hidden" animate="visible" custom={2} variants={fadeUp}>
          <h2 className="text-xs font-black uppercase text-slate-400 tracking-widest mb-4">Data Sources</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {sources.map((source, i) => {
              const status = statusConfig[source.status] || statusConfig.pending;
              const StatusIcon = status.icon;
              const SourceIcon = sourceIcons[source.name?.toLowerCase()] || Database;
              return (
                <motion.div
                  key={i}
                  initial="hidden"
                  animate="visible"
                  custom={i + 3}
                  variants={fadeUp}
                  className="bg-white/[0.03] border border-white/5 rounded-3xl p-6"
                >
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-white/5 rounded-xl flex items-center justify-center">
                        <SourceIcon size={20} className="text-slate-300" />
                      </div>
                      <div>
                        <p className="text-white font-black">{source.name}</p>
                        {source.enriched_at && (
                          <p className="text-slate-500 text-[10px]">
                            {new Date(source.enriched_at).toLocaleString()}
                          </p>
                        )}
                      </div>
                    </div>
                    <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full ${status.bg} border text-[10px] font-black uppercase tracking-widest ${status.color}`}>
                      <StatusIcon size={12} /> {status.label}
                    </span>
                  </div>
                  {source.details && (
                    <p className="text-slate-400 text-sm">{source.details}</p>
                  )}
                </motion.div>
              );
            })}
          </div>
          {sources.length === 0 && (
            <p className="text-slate-500 text-center py-8">No enrichment sources configured</p>
          )}
        </motion.div>

        {/* Skill Verification */}
        {skills.length > 0 && (
          <motion.div initial="hidden" animate="visible" custom={5} variants={fadeUp}
            className="bg-white/[0.03] border border-white/5 rounded-3xl p-6"
          >
            <h2 className="text-xs font-black uppercase text-purple-400 tracking-widest mb-6">Skill Verification Confidence</h2>
            <div className="space-y-4">
              {skills.map((skill, i) => {
                const confidence = skill.confidence ?? 0;
                const pct = Math.min(confidence * 100, 100);
                return (
                  <div key={i}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-white text-sm font-bold">{skill.name}</span>
                      <span className="text-slate-400 text-xs font-bold">{(confidence * 100).toFixed(0)}%</span>
                    </div>
                    <div className="h-2 bg-white/5 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-700 ${
                          confidence >= 0.8 ? 'bg-emerald-500' : confidence >= 0.5 ? 'bg-purple-500' : 'bg-amber-500'
                        }`}
                        style={{ width: `${pct}%` }}
                        role="progressbar"
                        aria-valuenow={pct}
                        aria-valuemin={0}
                        aria-valuemax={100}
                        aria-label={`${skill.name} confidence ${(confidence * 100).toFixed(0)}%`}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
};

export default EnrichmentSummary;
