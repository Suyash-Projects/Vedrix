import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  LineChart, Line, PieChart, Pie, Cell
} from 'recharts';
import {
  Users, TrendingUp, Award, Clock, Target, Download, ChevronLeft,
  Briefcase, Activity, Loader2
} from 'lucide-react';
import apiClient from '../services/api';

const TeamAnalytics = () => {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await apiClient.get('/admin/analytics/team');
        setData(res.data);
      } catch (err) {
        console.error('Failed to fetch team analytics:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const handleExportCSV = async () => {
    setExporting(true);
    try {
      const res = await apiClient.get('/admin/analytics/export/csv', { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'vedrix_platform_export.csv');
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      alert('Export failed.');
    } finally {
      setExporting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#020617] flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="w-16 h-16 border-4 border-purple-500 border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-purple-400 font-bold tracking-widest uppercase text-xs">Loading Analytics...</p>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="min-h-screen bg-[#020617] flex items-center justify-center">
        <div className="text-center space-y-4">
          <p className="text-red-400 font-bold tracking-widest uppercase text-xs">Failed to load analytics.</p>
          <button onClick={() => navigate(-1)} className="text-purple-400 underline text-sm">Go Back</button>
        </div>
      </div>
    );
  }

  const { summary, funnel, score_distribution, role_breakdown, daily_trend, pass_fail } = data;

  // Funnel data
  const funnelData = Object.entries(funnel).map(([stage, count]) => ({
    name: stage.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase()),
    value: count,
  }));

  // Score distribution data
  const scoreDistData = Object.entries(score_distribution).map(([range, count]) => ({
    name: range,
    count,
  }));

  // Pass/Fail pie data
  const passFailData = [
    { name: 'Passed', value: pass_fail.pass },
    { name: 'Failed', value: pass_fail.fail },
  ];

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
              <h1 className="text-xl font-bold text-white">Team Analytics</h1>
              <p className="text-xs text-slate-500 font-medium uppercase tracking-wider">Platform-wide insights</p>
            </div>
          </div>
          <button
            onClick={handleExportCSV}
            disabled={exporting}
            className="flex items-center space-x-2 bg-white/5 border border-white/10 text-slate-300 px-5 py-2.5 rounded-xl text-sm font-bold hover:bg-white/10 transition-all disabled:opacity-50"
          >
            {exporting ? <Loader2 className="animate-spin" size={16} /> : <Download size={16} />}
            <span>{exporting ? 'Exporting...' : 'Export CSV'}</span>
          </button>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 mt-10 space-y-8">

        {/* SUMMARY CARDS */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          {[
            { label: 'Total Sessions', value: summary.total_sessions, icon: Activity, color: 'purple' },
            { label: 'Completed', value: summary.completed_sessions, icon: Users, color: 'emerald' },
            { label: 'Avg Score', value: summary.avg_score.toFixed(1), icon: Award, color: 'amber' },
            { label: 'Pass Rate', value: `${summary.pass_rate}%`, icon: Target, color: 'blue' },
          ].map(({ label, value, icon: Icon, color }) => {
            const colorMap = {
              purple: 'bg-purple-600/10 border-purple-500/20 text-purple-400',
              emerald: 'bg-emerald-600/10 border-emerald-500/20 text-emerald-400',
              amber: 'bg-amber-600/10 border-amber-500/20 text-amber-400',
              blue: 'bg-blue-600/10 border-blue-500/20 text-blue-400',
            };
            return (
              <div key={label} className="bg-white/2 border border-white/5 rounded-[2rem] p-8">
                <div className="flex items-center justify-between mb-4">
                  <div className={`w-12 h-12 rounded-2xl flex items-center justify-center ${colorMap[color]}`}>
                    <Icon size={22} />
                  </div>
                </div>
                <p className="text-3xl font-black text-white">{value}</p>
                <p className="text-[10px] text-slate-500 uppercase font-bold tracking-widest mt-1">{label}</p>
              </div>
            );
          })}
        </div>

        {/* SECOND ROW */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          {[
            { label: 'Completion Rate', value: `${summary.completion_rate}%`, icon: TrendingUp, color: 'purple' },
            { label: 'Avg Duration', value: `${summary.avg_duration_minutes}m`, icon: Clock, color: 'emerald' },
            { label: 'In Progress', value: summary.in_progress, icon: Activity, color: 'amber' },
            { label: '30-Day Avg', value: summary.recent_30d_avg.toFixed(1), icon: Award, color: 'blue' },
          ].map(({ label, value, icon: Icon, color }) => {
            const colorMap = {
              purple: 'bg-purple-600/10 border-purple-500/20 text-purple-400',
              emerald: 'bg-emerald-600/10 border-emerald-500/20 text-emerald-400',
              amber: 'bg-amber-600/10 border-amber-500/20 text-amber-400',
              blue: 'bg-blue-600/10 border-blue-500/20 text-blue-400',
            };
            return (
              <div key={label} className="bg-white/2 border border-white/5 rounded-[2rem] p-8">
                <div className="flex items-center justify-between mb-4">
                  <div className={`w-12 h-12 rounded-2xl flex items-center justify-center ${colorMap[color]}`}>
                    <Icon size={22} />
                  </div>
                </div>
                <p className="text-3xl font-black text-white">{value}</p>
                <p className="text-[10px] text-slate-500 uppercase font-bold tracking-widest mt-1">{label}</p>
              </div>
            );
          })}
        </div>

        {/* CHARTS ROW */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">

          {/* Score Distribution */}
          <div className="bg-white/2 border border-white/5 rounded-[2.5rem] p-10">
            <h3 className="text-xs font-black text-slate-500 uppercase tracking-[0.2em] mb-8 flex items-center">
              <Award size={16} className="mr-2 text-purple-400" /> Score Distribution
            </h3>
            <div className="w-full h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={scoreDistData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis dataKey="name" tick={{ fill: '#64748B', fontSize: 11, fontWeight: 600 }} />
                  <YAxis tick={{ fill: '#64748B', fontSize: 10 }} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#1e293b', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px' }}
                  />
                  <Bar dataKey="count" fill="#8B5CF6" radius={[6, 6, 0, 0]} barSize={40} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Pass/Fail Pie */}
          <div className="bg-white/2 border border-white/5 rounded-[2.5rem] p-10">
            <h3 className="text-xs font-black text-slate-500 uppercase tracking-[0.2em] mb-8 flex items-center">
              <Target size={16} className="mr-2 text-emerald-400" /> Pass / Fail Ratio
            </h3>
            <div className="w-full h-64">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={passFailData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={90}
                    paddingAngle={5}
                    dataKey="value"
                    label={({ name, value }) => `${name}: ${value}`}
                  >
                    {passFailData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={index === 0 ? '#10b981' : '#ef4444'} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ backgroundColor: '#1e293b', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px' }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* DAILY TREND */}
        <div className="bg-white/2 border border-white/5 rounded-[2.5rem] p-10">
          <h3 className="text-xs font-black text-slate-500 uppercase tracking-[0.2em] mb-8 flex items-center">
            <TrendingUp size={16} className="mr-2 text-blue-400" /> Daily Trend (Last 14 Days)
          </h3>
          <div className="w-full h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={daily_trend}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="date" tick={{ fill: '#64748B', fontSize: 9 }} />
                <YAxis tick={{ fill: '#64748B', fontSize: 10 }} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#1e293b', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px' }}
                />
                <Legend />
                <Line type="monotone" dataKey="avg_score" stroke="#8B5CF6" strokeWidth={2} dot={{ fill: '#8B5CF6', r: 3 }} name="Avg Score" />
                <Line type="monotone" dataKey="count" stroke="#10b981" strokeWidth={2} dot={{ fill: '#10b981', r: 3 }} name="Completed" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* HIRING FUNNEL + ROLE BREAKDOWN */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">

          {/* Hiring Funnel */}
          <div className="bg-white/2 border border-white/5 rounded-[2.5rem] p-10">
            <h3 className="text-xs font-black text-slate-500 uppercase tracking-[0.2em] mb-8 flex items-center">
              <Users size={16} className="mr-2 text-amber-400" /> Hiring Funnel
            </h3>
            <div className="space-y-4">
              {funnelData.map((stage, idx) => {
                const prevCount = idx > 0 ? funnelData[idx - 1].value : stage.value;
                const conversionRate = prevCount > 0 ? Math.round((stage.value / prevCount) * 100) : 0;
                const barWidth = funnelData[0].value > 0 ? Math.round((stage.value / funnelData[0].value) * 100) : 0;

                return (
                  <div key={stage.name} className="space-y-2">
                    <div className="flex justify-between items-center">
                      <span className="text-sm font-bold text-white">{stage.name}</span>
                      <span className="text-sm font-bold text-purple-400">{stage.value}</span>
                    </div>
                    <div className="w-full bg-white/5 rounded-full h-3">
                      <div
                        className="bg-purple-600 h-3 rounded-full transition-all"
                        style={{ width: `${barWidth}%` }}
                      />
                    </div>
                    {idx > 0 && (
                      <p className="text-[10px] text-slate-500 font-bold text-right">{conversionRate}% conversion</p>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Role Breakdown */}
          <div className="bg-white/2 border border-white/5 rounded-[2.5rem] p-10">
            <h3 className="text-xs font-black text-slate-500 uppercase tracking-[0.2em] mb-8 flex items-center">
              <Briefcase size={16} className="mr-2 text-emerald-400" /> Role Breakdown
            </h3>
            {role_breakdown.length === 0 ? (
              <div className="text-center py-16 text-slate-500">No role data available yet.</div>
            ) : (
              <div className="w-full h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={role_breakdown}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                    <XAxis dataKey="job_role" tick={{ fill: '#64748B', fontSize: 9 }} interval={0} angle={-30} textAnchor="end" height={60} />
                    <YAxis tick={{ fill: '#64748B', fontSize: 10 }} />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#1e293b', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px' }}
                    />
                    <Legend />
                    <Bar dataKey="avg_score" fill="#8B5CF6" name="Avg Score" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="pass_rate" fill="#10b981" name="Pass Rate %" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
};

export default TeamAnalytics;
