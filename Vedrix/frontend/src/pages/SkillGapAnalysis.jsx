import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  ResponsiveContainer, BarChart, Bar, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend
} from 'recharts';
import {
  ChevronLeft, Target, AlertTriangle, CheckCircle2,
  TrendingUp, Award
} from 'lucide-react';
import apiClient from '../services/api';

const SkillGapAnalysis = () => {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!sessionId) return;
    const fetchData = async () => {
      try {
        // Try HR endpoint first, fall back to student endpoint
        let res;
        try {
          res = await apiClient.get(`/hr/interviews/${sessionId}/skill-gap`);
        } catch {
          res = await apiClient.get(`/users/sessions/${sessionId}/skill-gap`);
        }
        setData(res.data);
      } catch (err) {
        console.error('Failed to fetch skill gap:', err);
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
          <p className="text-purple-400 font-bold tracking-widest uppercase text-xs">Analyzing Skill Gaps...</p>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="min-h-screen bg-[#020617] flex items-center justify-center">
        <div className="text-center space-y-4">
          <p className="text-red-400 font-bold tracking-widest uppercase text-xs">Failed to load skill gap analysis.</p>
          <button onClick={() => navigate(-1)} className="text-purple-400 underline text-sm">Go Back</button>
        </div>
      </div>
    );
  }

  const { candidate_skills, required_skills, gaps, recommendations, job_role, overall_match_score } = data;

  // Build radar chart data
  const allSkillKeys = [...new Set([...Object.keys(candidate_skills), ...Object.keys(required_skills)])];
  const radarData = allSkillKeys.map(skill => ({
    subject: skill.charAt(0).toUpperCase() + skill.slice(1),
    candidate: (candidate_skills[skill] || 0) * 10,
    required: (required_skills[skill] || 0) * 10,
    fullMark: 100,
  }));

  // Build bar chart for gaps
  const gapChartData = Object.entries(gaps)
    .sort((a, b) => a[1] - b[1])
    .map(([skill, gap]) => ({
      name: skill.charAt(0).toUpperCase() + skill.slice(1),
      gap: gap,
      fill: gap >= 0 ? '#10b981' : '#ef4444',
    }));

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
              <h1 className="text-xl font-bold text-white">Skill Gap Analysis</h1>
              <p className="text-xs text-slate-500 font-medium uppercase tracking-wider">{job_role}</p>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <div className="rounded-2xl bg-white/5 border border-white/10 px-5 py-3 text-center">
              <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Match Score</p>
              <p className="text-2xl font-black text-purple-400">{overall_match_score}%</p>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 mt-10">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">

          {/* LEFT COLUMN */}
          <div className="lg:col-span-8 space-y-8">

            {/* RADAR CHART */}
            <div className="bg-white/2 border border-white/5 rounded-[2.5rem] p-10">
              <h3 className="text-xs font-black text-slate-500 uppercase tracking-[0.2em] mb-8 flex items-center">
                <Target size={16} className="mr-2 text-purple-400" /> Candidate vs Role Requirements
              </h3>
              {radarData.length > 0 ? (
                <div className="w-full h-80">
                  <ResponsiveContainer width="100%" height="100%">
                    <RadarChart cx="50%" cy="50%" outerRadius="80%" data={radarData}>
                      <PolarGrid stroke="rgba(255,255,255,0.05)" />
                      <PolarAngleAxis dataKey="subject" tick={{ fill: '#64748B', fontSize: 11, fontWeight: 700 }} />
                      <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                      <Radar name="Candidate" dataKey="candidate" stroke="#8B5CF6" fill="#8B5CF6" fillOpacity={0.3} />
                      <Radar name="Required" dataKey="required" stroke="#10b981" fill="#10b981" fillOpacity={0.1} />
                      <Legend />
                    </RadarChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="text-center py-16 text-slate-500">No skill data available for comparison.</div>
              )}
            </div>

            {/* GAP BAR CHART */}
            <div className="bg-white/2 border border-white/5 rounded-[2.5rem] p-10">
              <h3 className="text-xs font-black text-slate-500 uppercase tracking-[0.2em] mb-8 flex items-center">
                <TrendingUp size={16} className="mr-2 text-purple-400" /> Skill Gaps (Positive = Exceeds Requirement)
              </h3>
              {gapChartData.length > 0 ? (
                <div className="w-full h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={gapChartData} layout="vertical" margin={{ left: 20 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                      <XAxis type="number" domain={[-10, 10]} tick={{ fill: '#64748B', fontSize: 10 }} />
                      <YAxis dataKey="name" type="category" tick={{ fill: '#94a3b8', fontSize: 11, fontWeight: 600 }} width={120} />
                      <Tooltip
                        contentStyle={{ backgroundColor: '#1e293b', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px' }}
                        labelStyle={{ color: '#e2e8f0', fontWeight: 700 }}
                      />
                      <Bar dataKey="gap" radius={[0, 6, 6, 0]} barSize={24}>
                        {gapChartData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.fill} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="text-center py-16 text-slate-500">No gap data available.</div>
              )}
            </div>

            {/* SKILL DETAIL TABLE */}
            <div className="bg-white/2 border border-white/5 rounded-[2.5rem] overflow-hidden">
              <div className="px-10 py-6 border-b border-white/5">
                <h3 className="text-xs font-black text-slate-500 uppercase tracking-[0.2em]">Detailed Skill Breakdown</h3>
              </div>
              <div className="divide-y divide-white/5">
                {allSkillKeys.map(skill => {
                  const candidateScore = candidate_skills[skill] || 0;
                  const requiredScore = required_skills[skill] || 0;
                  const gap = gaps[skill] || 0;
                  const statusColor = gap >= 0 ? 'text-emerald-400' : 'text-red-400';
                  const statusIcon = gap >= 0 ? <CheckCircle2 size={14} /> : <AlertTriangle size={14} />;

                  return (
                    <div key={skill} className="px-10 py-5 flex items-center justify-between">
                      <div>
                        <p className="text-white font-bold capitalize">{skill}</p>
                        <p className="text-xs text-slate-500">
                          Required: {requiredScore.toFixed(1)}/10
                        </p>
                      </div>
                      <div className="flex items-center space-x-6">
                        <div className="text-right">
                          <p className="text-sm font-bold text-purple-400">{candidateScore.toFixed(1)}</p>
                          <p className="text-[10px] text-slate-500 uppercase">Score</p>
                        </div>
                        <div className={`text-right flex items-center space-x-1 ${statusColor}`}>
                          {statusIcon}
                          <span className="text-sm font-bold">{gap >= 0 ? '+' : ''}{gap.toFixed(1)}</span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* RIGHT COLUMN */}
          <div className="lg:col-span-4 space-y-8">

            {/* RECOMMENDATIONS */}
            <div className="bg-white/2 border border-white/5 rounded-[2.5rem] p-10">
              <h3 className="text-xs font-black text-slate-500 uppercase tracking-[0.2em] mb-6 flex items-center">
                <Award size={16} className="mr-2 text-amber-400" /> Recommendations
              </h3>
              <div className="space-y-4">
                {recommendations.map((rec, i) => (
                  <div key={i} className="bg-white/5 border border-white/5 rounded-xl p-4 text-sm text-slate-300 leading-relaxed">
                    {rec}
                  </div>
                ))}
              </div>
            </div>

            {/* QUICK SUMMARY */}
            <div className="bg-white/2 border border-white/5 rounded-[2.5rem] p-10">
              <h3 className="text-xs font-black text-slate-500 uppercase tracking-[0.2em] mb-6">Quick Summary</h3>
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-slate-400">Skills Assessed</span>
                  <span className="text-lg font-black text-white">{allSkillKeys.length}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-slate-400">Skills Meeting Req.</span>
                  <span className="text-lg font-black text-emerald-400">
                    {allSkillKeys.filter(s => (gaps[s] || 0) >= 0).length}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-slate-400">Skills Below Req.</span>
                  <span className="text-lg font-black text-red-400">
                    {allSkillKeys.filter(s => (gaps[s] || 0) < 0).length}
                  </span>
                </div>
                <div className="border-t border-white/5 pt-4 mt-4">
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-bold text-white">Overall Match</span>
                    <span className="text-2xl font-black text-purple-400">{overall_match_score}%</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default SkillGapAnalysis;
