import { useState, useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  LineChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis,
  ReferenceArea
} from 'recharts';
import { Heart, RefreshCw } from 'lucide-react';
import apiClient from '../services/api';

const fadeUp = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: 'easeOut' } }
};

const METRICS = [
  { key: 'sentiment_score', label: 'Sentiment', color: '#7C3AED' },
  { key: 'stress_level', label: 'Stress', color: '#ef4444' },
  { key: 'hesitation_rating', label: 'Hesitation', color: '#f59e0b' },
  { key: 'confidence_level', label: 'Confidence', color: '#10b981' },
];

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload || !payload.length) return null;
  return (
    <div className="bg-[#0f172a] border border-white/10 rounded-xl p-3 shadow-xl">
      <p className="text-slate-400 text-xs font-bold mb-2">{label}</p>
      {payload.map((entry, i) => (
        <div key={i} className="flex items-center gap-2 text-xs">
          <div className="w-2 h-2 rounded-full" style={{ backgroundColor: entry.color }} />
          <span className="text-slate-300">{entry.name}:</span>
          <span className="text-white font-bold">{entry.value?.toFixed(2)}</span>
        </div>
      ))}
    </div>
  );
};

const SentimentTimeline = () => {
  const { sessionId } = useParams();
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [visibleMetrics, setVisibleMetrics] = useState(
    METRICS.reduce((acc, m) => ({ ...acc, [m.key]: true }), {})
  );

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.get(`/hr/interviews/${sessionId}/sentiment`);
      setData(res.data?.snapshots || res.data || []);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load sentiment data');
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    Promise.resolve().then(() => {
      fetchData();
    });
  }, [fetchData]);

  // Find high-stress zones (stress_level > 0.7)
  const highStressZones = [];
  let zoneStart = null;
  data.forEach((point, i) => {
    if ((point.stress_level ?? 0) > 0.7) {
      if (zoneStart === null) zoneStart = i;
    } else {
      if (zoneStart !== null) {
        highStressZones.push({ start: zoneStart, end: i - 1 });
        zoneStart = null;
      }
    }
  });
  if (zoneStart !== null) highStressZones.push({ start: zoneStart, end: data.length - 1 });

  const toggleMetric = (key) => {
    setVisibleMetrics(prev => ({ ...prev, [key]: !prev[key] }));
  };

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
          <button onClick={fetchData}
            className="inline-flex items-center gap-2 bg-purple-600 hover:bg-purple-500 text-white font-bold px-6 py-3 rounded-2xl transition-all"
            aria-label="Retry loading sentiment data"
          >
            <RefreshCw size={16} /> Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#020617] text-white font-sans">
      <div className="fixed top-0 left-[-5%] w-[30%] h-[40%] bg-purple-900/10 blur-[150px] rounded-full pointer-events-none" />

      <div className="max-w-6xl mx-auto px-8 py-12 space-y-8 relative z-10">
        {/* Header */}
        <motion.div variants={fadeUp} initial="hidden" animate="visible">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 bg-gradient-to-tr from-purple-600 to-pink-500 rounded-2xl flex items-center justify-center shadow-xl shadow-purple-900/30">
              <Heart size={24} className="text-white" />
            </div>
            <div>
              <h1 className="text-3xl font-black text-white tracking-tight">Sentiment Timeline</h1>
              <p className="text-slate-500 text-sm">Session: {sessionId}</p>
            </div>
          </div>
        </motion.div>

        {/* Legend / Toggle */}
        <div className="flex flex-wrap gap-3">
          {METRICS.map(m => (
            <button
              key={m.key}
              onClick={() => toggleMetric(m.key)}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-xl border text-xs font-bold transition-all ${
                visibleMetrics[m.key]
                  ? 'bg-white/5 border-white/10 text-white'
                  : 'bg-transparent border-white/5 text-slate-600'
              }`}
              aria-label={`Toggle ${m.label} visibility`}
              aria-pressed={visibleMetrics[m.key]}
            >
              <div className="w-3 h-3 rounded-full" style={{ backgroundColor: visibleMetrics[m.key] ? m.color : '#334155' }} />
              {m.label}
            </button>
          ))}
        </div>

        {/* Chart */}
        <motion.div variants={fadeUp} initial="hidden" animate="visible"
          className="bg-white/[0.03] border border-white/5 rounded-3xl p-8"
        >
          {data.length > 0 ? (
            <div className="h-[350px]" role="img" aria-label="Sentiment metrics timeline chart">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                  <XAxis
                    dataKey="timestamp"
                    tick={{ fill: '#64748b', fontSize: 10 }}
                    axisLine={false}
                    tickLine={false}
                    tickFormatter={(val) => {
                      if (!val) return '';
                      const d = new Date(val);
                      if (isNaN(d.getTime())) return val;
                      return `${d.getMinutes()}:${d.getSeconds().toString().padStart(2, '0')}`;
                    }}
                  />
                  <YAxis domain={[0, 1]} tick={{ fill: '#64748b', fontSize: 10 }} axisLine={false} tickLine={false} width={30} />
                  <Tooltip content={<CustomTooltip />} />

                  {/* High stress zones */}
                  {highStressZones.map((zone, i) => (
                    <ReferenceArea
                      key={i}
                      x1={data[zone.start]?.timestamp}
                      x2={data[zone.end]?.timestamp}
                      fill="rgba(239,68,68,0.08)"
                      strokeOpacity={0}
                    />
                  ))}

                  {METRICS.map(m => visibleMetrics[m.key] && (
                    <Line
                      key={m.key}
                      type="monotone"
                      dataKey={m.key}
                      name={m.label}
                      stroke={m.color}
                      strokeWidth={2}
                      dot={false}
                      activeDot={{ r: 4, fill: m.color }}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="text-slate-500 text-center py-16">No sentiment data available for this session</p>
          )}
        </motion.div>

        {/* High Stress Zones Info */}
        {highStressZones.length > 0 && (
          <div className="bg-red-500/5 border border-red-500/10 rounded-2xl p-4">
            <p className="text-red-400 text-xs font-black uppercase tracking-widest mb-2">High Stress Zones Detected</p>
            <p className="text-slate-400 text-sm">
              {highStressZones.length} period{highStressZones.length > 1 ? 's' : ''} of elevated stress (highlighted in red on chart)
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default SentimentTimeline;
