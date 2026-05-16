import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, 
  ResponsiveContainer
} from 'recharts';
import { 
  ChevronLeft, Download, Share2, Award, AlertTriangle, 
  CheckCircle2, Target, MessageSquare, BookOpen, ShieldCheck, Loader2
} from 'lucide-react';
import apiClient from '../services/api';

const InterviewReport = () => {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);

  const handleBack = () => {
    navigate(-1); // Go back to previous page
  };

  const handleExportPDF = async () => {
    setExporting(true);
    try {
      // Use the correct HR endpoint for PDF
      const res = await apiClient.get(`/hr/interviews/${sessionId}/pdf`, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `Vedrix_Report_${sessionId}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      alert('Export failed. Ensure you have HR permissions to export this report.');
    } finally {
      setExporting(false);
    }
  };

  const handleShare = () => {
    navigator.clipboard.writeText(window.location.href);
    alert("Report link copied to clipboard!");
  };

  const handleDownloadCertificate = async () => {
    setExporting(true);
    try {
      const res = await apiClient.get(`/users/sessions/${sessionId}/certificate`, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `Vedrix_Certificate_${sessionId}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      alert('Failed to download certificate.');
    } finally {
      setExporting(false);
    }
  };

  useEffect(() => {
    if (!sessionId) return;
    const fetchReport = async () => {
      try {
        // Try HR endpoint first, fall back to student endpoint
        let data, aiFeedback, transcript;
        try {
          const res = await apiClient.get(`/hr/interviews/${sessionId}`);
          data = res.data;
          aiFeedback = typeof data.ai_feedback === 'string' ? JSON.parse(data.ai_feedback) : data.ai_feedback;
          transcript = typeof data.responses === 'string' ? JSON.parse(data.responses) : data.responses;
        } catch {
          // Student fallback
          const res = await apiClient.get(`/users/sessions/${sessionId}/report`);
          data = res.data;
          aiFeedback = data;
          transcript = data.transcript || [];
        }

        const skillMatrix = data.skill_matrix ? (typeof data.skill_matrix === 'string' ? JSON.parse(data.skill_matrix) : data.skill_matrix) : null;
        
        let radarMetrics = [
          { subject: 'Accuracy', A: (aiFeedback?.technical_accuracy ?? 0) * 10, fullMark: 100 },
          { subject: 'Clarity', A: (aiFeedback?.communication_clarity ?? 0) * 10, fullMark: 100 },
          { subject: 'Depth', A: (aiFeedback?.depth_of_knowledge ?? 0) * 10, fullMark: 100 },
          { subject: 'Overall', A: (data.overall_score ?? 0) * 10, fullMark: 100 },
        ];

        if (skillMatrix && Object.keys(skillMatrix).length > 0) {
          radarMetrics = Object.entries(skillMatrix).map(([topic, score]) => ({
            subject: topic.charAt(0).toUpperCase() + topic.slice(1),
            A: score * 10,
            fullMark: 100
          }));
        }

        setReport({
          overall_score: data.overall_score ?? 0,
          hire_recommendation: aiFeedback?.hire_recommendation || 'Unknown',
          technical_accuracy: aiFeedback?.technical_accuracy ?? 0,
          communication_clarity: aiFeedback?.communication_clarity ?? 0,
          depth_of_knowledge: aiFeedback?.depth_of_knowledge ?? 0,
          metrics: radarMetrics,
          strengths: aiFeedback?.strengths || [],
          weaknesses: aiFeedback?.weaknesses || [],
          summary: aiFeedback?.summary || 'No summary available.',
          transcript: transcript || [],
        });
      } catch (err) {
        console.error('Failed to fetch report:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchReport();
  }, [sessionId]);

  if (loading) {
    return (
      <div className="min-h-screen bg-[#020617] flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="w-16 h-16 border-4 border-purple-500 border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-purple-400 font-bold tracking-widest uppercase text-xs">Preparing Interview Report...</p>
        </div>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="min-h-screen bg-[#020617] flex items-center justify-center">
        <div className="text-center space-y-4">
          <p className="text-red-400 font-bold tracking-widest uppercase text-xs">Failed to load report.</p>
          <button onClick={handleBack} className="text-purple-400 underline text-sm">Go Back</button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#020617] font-sans pb-20">
      {/* HEADER */}
      <header className="bg-[#0a0f1e] border-b border-white/5 sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <button onClick={handleBack} className="p-2 hover:bg-white/5 rounded-xl transition-colors text-slate-500 hover:text-white">
              <ChevronLeft size={24} />
            </button>
            <div className="h-8 w-px bg-white/5" />
            <div>
              <h1 className="text-xl font-bold text-white">Candidate Evaluation Report</h1>
              <p className="text-xs text-slate-500 font-medium uppercase tracking-wider">Session ID: {sessionId}</p>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <button 
              onClick={handleExportPDF}
              disabled={exporting}
              className="flex items-center space-x-2 bg-white/5 border border-white/10 text-slate-300 px-4 py-2.5 rounded-xl text-sm font-bold hover:bg-white/10 transition-all disabled:opacity-50"
            >
              {exporting ? <Loader2 className="animate-spin" size={18} /> : <Download size={18} />}
              <span>{exporting ? 'Generating...' : 'Export PDF'}</span>
            </button>
            <button
              onClick={handleShare}
              className="flex items-center space-x-2 bg-purple-600 text-white px-6 py-2.5 rounded-xl text-sm font-bold hover:bg-purple-500 transition-all shadow-lg shadow-purple-900/30 active:scale-95"
            >
              <Share2 size={18} />
              <span>Share with Team</span>
            </button>
            {report?.overall_score >= 6 && (
              <button
                onClick={handleDownloadCertificate}
                disabled={exporting}
                className="flex items-center space-x-2 bg-gradient-to-r from-amber-500 to-orange-500 text-white px-6 py-2.5 rounded-xl text-sm font-bold hover:from-amber-400 hover:to-orange-400 transition-all shadow-lg shadow-orange-900/30 active:scale-95 disabled:opacity-50"
              >
                <Award size={18} />
                <span>Certificate</span>
              </button>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 mt-10">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">

          {/* LEFT COLUMN */}
          <div className="lg:col-span-8 space-y-8">

            {/* OVERVIEW CARD */}
            <div className="bg-white/2 border border-white/5 rounded-[2.5rem] p-10">
              <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-8 mb-10">
                <div className="flex items-center space-x-6">
                  <div className="w-24 h-24 bg-purple-500/10 rounded-3xl flex items-center justify-center text-purple-400 border border-purple-500/20">
                    <span className="text-4xl font-black">{report.overall_score}</span>
                  </div>
                  <div>
                    <div className="flex items-center space-x-2 mb-1">
                      <span className="bg-emerald-500/10 text-emerald-400 text-[10px] font-black uppercase tracking-widest px-3 py-1 rounded-full border border-emerald-500/20">
                        {report.hire_recommendation}
                      </span>
                    </div>
                    <h2 className="text-3xl font-extrabold text-white leading-tight">Interview Summary</h2>
                  </div>
                </div>
              </div>

              <div className="bg-white/5 rounded-3xl p-8 border border-white/5 mb-10">
                <h3 className="text-xs font-black text-slate-500 uppercase tracking-[0.2em] mb-4 flex items-center">
                  <MessageSquare size={14} className="mr-2 text-purple-400" /> Executive Summary
                </h3>
                <p className="text-lg text-slate-300 leading-relaxed italic font-medium">
                  "{report.summary}"
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div>
                  <h3 className="text-[10px] font-black text-emerald-400 uppercase tracking-widest mb-4 flex items-center">
                    <CheckCircle2 size={14} className="mr-2" /> Key Strengths
                  </h3>
                  <ul className="space-y-3">
                    {(report.strengths.length ? report.strengths : ['No strengths were captured for this session yet.']).map((s, i) => (
                      <li key={i} className="flex items-start text-sm text-slate-400 bg-emerald-500/5 p-3 rounded-xl border border-emerald-500/10">
                        <Award size={16} className="mr-3 text-emerald-400 shrink-0 mt-0.5" />{s}
                      </li>
                    ))}
                  </ul>
                </div>
                <div>
                  <h3 className="text-[10px] font-black text-amber-400 uppercase tracking-widest mb-4 flex items-center">
                    <AlertTriangle size={14} className="mr-2" /> Improvement Areas
                  </h3>
                  <ul className="space-y-3">
                    {(report.weaknesses.length ? report.weaknesses : ['No improvement areas were captured for this session yet.']).map((w, i) => (
                      <li key={i} className="flex items-start text-sm text-slate-400 bg-amber-500/5 p-3 rounded-xl border border-amber-500/10">
                        <Target size={16} className="mr-3 text-amber-400 shrink-0 mt-0.5" />{w}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>

            {/* TRANSCRIPT */}
            <div className="bg-white/2 border border-white/5 rounded-[2.5rem] overflow-hidden">
              <div className="px-10 py-6 border-b border-white/5 flex justify-between items-center">
                <h2 className="font-bold text-white flex items-center">
                  <BookOpen size={18} className="mr-3 text-purple-400" /> Full Session Transcript
                </h2>
              </div>
              <div className="p-10 space-y-6">
                {report.transcript.length === 0 ? (
                  <div className="bg-white/5 border border-white/5 rounded-3xl p-6 text-sm text-slate-400">
                    A transcript is not available for this session.
                  </div>
                ) : report.transcript.map((msg, i) => (
                  <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-[80%] p-6 rounded-3xl ${
                      msg.role === 'user'
                        ? 'bg-purple-600/20 border border-purple-500/20 text-white rounded-tr-none'
                        : 'bg-white/5 border border-white/5 text-slate-300 rounded-tl-none'
                    }`}>
                      <p className="text-[9px] font-black uppercase tracking-widest opacity-50 mb-2">
                        {msg.role === 'user' ? 'Candidate' : 'Interviewer'}
                      </p>
                      <p className="text-base leading-relaxed font-medium">{msg.content}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* RIGHT COLUMN */}
          <div className="lg:col-span-4 space-y-8">

            {/* RADAR CHART */}
            <div className="bg-white/2 border border-white/5 rounded-[2.5rem] p-10 flex flex-col items-center">
              <h3 className="text-xs font-black text-slate-500 uppercase tracking-[0.2em] mb-10 self-start">Competency Radar</h3>
              <div className="w-full h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart cx="50%" cy="50%" outerRadius="80%" data={report.metrics}>
                    <PolarGrid stroke="rgba(255,255,255,0.05)" />
                    <PolarAngleAxis dataKey="subject" tick={{ fill: '#64748B', fontSize: 10, fontWeight: 700 }} />
                    <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                    <Radar name="Candidate" dataKey="A" stroke="#8B5CF6" fill="#8B5CF6" fillOpacity={0.3} />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* PROCTORING — Coming Soon */}
            <div className="bg-white/2 border border-white/5 rounded-[2.5rem] p-10">
              <div className="flex items-center space-x-3 mb-4">
                <div className="w-10 h-10 bg-purple-600/10 border border-purple-500/20 rounded-2xl flex items-center justify-center">
                  <ShieldCheck size={20} className="text-purple-400" />
                </div>
                <div>
                  <h3 className="font-bold text-white text-lg tracking-tight">System Integrity</h3>
                  <span className="text-[9px] font-black text-amber-400 uppercase tracking-widest">Coming Soon</span>
                </div>
              </div>
              <p className="text-slate-500 text-xs leading-relaxed">
                Additional session integrity signals will appear here once they are implemented and validated.
              </p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default InterviewReport;
