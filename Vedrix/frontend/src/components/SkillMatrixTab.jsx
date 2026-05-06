import React, { useState, useMemo } from 'react';
import { motion } from 'framer-motion';
import {
  TrendingUp, Target, Award, BarChart3, PieChart,
  ChevronDown, Filter, Download, RefreshCw
} from 'lucide-react';

/* ── SKILL MATRIX RADAR CHART COMPONENT ── */
const SkillRadarChart = ({ skills, candidateName }) => {
  const maxScore = 10;
  const size = 200;
  const center = size / 2;

  // Calculate points for radar chart
  const points = useMemo(() => {
    const skillKeys = Object.keys(skills);
    const angleStep = (Math.PI * 2) / skillKeys.length;

    return skillKeys.map((skill, index) => {
      const angle = index * angleStep - Math.PI / 2; // Start from top
      const score = skills[skill] || 0;
      const radius = (score / maxScore) * (size * 0.35);
      const x = center + radius * Math.cos(angle);
      const y = center + radius * Math.sin(angle);
      return { x, y, skill, score };
    });
  }, [skills]);

  const pathData = points.map(p => `${p.x},${p.y}`).join(' ');

  return (
    <div className="bg-white/5 border border-white/10 rounded-2xl p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-bold text-white">{candidateName}</h3>
        <div className="text-sm text-slate-400">
          Avg: {(Object.values(skills).reduce((a, b) => a + b, 0) / Object.keys(skills).length).toFixed(1)}
        </div>
      </div>

      <div className="relative" style={{ width: size, height: size, margin: '0 auto' }}>
        <svg width={size} height={size} className="overflow-visible">
          {/* Background circles */}
          {[2, 4, 6, 8, 10].map(score => {
            const radius = (score / maxScore) * (size * 0.35);
            return (
              <circle
                key={score}
                cx={center}
                cy={center}
                r={radius}
                fill="none"
                stroke="rgba(255,255,255,0.1)"
                strokeWidth="1"
                strokeDasharray={score < 10 ? "2,2" : "none"}
              />
            );
          })}

          {/* Axis lines */}
          {points.map((point, index) => {
            const angle = (index * (Math.PI * 2)) / points.length - Math.PI / 2;
            const x = center + (size * 0.35) * Math.cos(angle);
            const y = center + (size * 0.35) * Math.sin(angle);
            return (
              <line
                key={`axis-${index}`}
                x1={center}
                y1={center}
                x2={x}
                y2={y}
                stroke="rgba(255,255,255,0.1)"
                strokeWidth="1"
              />
            );
          })}

          {/* Skill radar area */}
          <polygon
            points={pathData}
            fill="rgba(168, 85, 247, 0.2)"
            stroke="#a855f7"
            strokeWidth="2"
            className="drop-shadow-lg"
          />

          {/* Data points */}
          {points.map((point, index) => (
            <circle
              key={`point-${index}`}
              cx={point.x}
              cy={point.y}
              r="4"
              fill="#a855f7"
              className="drop-shadow-md"
            />
          ))}
        </svg>

        {/* Skill labels */}
        {points.map((point, index) => {
          const angle = (index * (Math.PI * 2)) / points.length - Math.PI / 2;
          const labelRadius = size * 0.45;
          const x = center + labelRadius * Math.cos(angle);
          const y = center + labelRadius * Math.sin(angle);

          return (
            <div
              key={`label-${index}`}
              className="absolute text-xs text-slate-400 font-medium transform -translate-x-1/2 -translate-y-1/2"
              style={{
                left: x,
                top: y,
                textAlign: angle > 0 && angle < Math.PI ? 'left' : 'right'
              }}
            >
              {point.skill}
            </div>
          );
        })}
      </div>
    </div>
  );
};

/* ── SKILL MATRIX TAB ── */
const SkillMatrixTab = ({ interviews }) => {
  const [selectedDrive, setSelectedDrive] = useState('all');
  const [viewMode, setViewMode] = useState('radar'); // 'radar' or 'table'
  const [sortBy, setSortBy] = useState('overall');

  // Extract unique drives
  const drives = useMemo(() => {
    const driveSet = new Set(interviews.map(i => i.drive_title).filter(Boolean));
    return ['all', ...Array.from(driveSet)];
  }, [interviews]);

  // Process skill data from interviews
  const skillData = useMemo(() => {
    const filtered = selectedDrive === 'all'
      ? interviews
      : interviews.filter(i => i.drive_title === selectedDrive);

    return filtered.map(interview => {
      // Extract skills from the interview data
      // This assumes the backend provides skill_matrix data
      const skills = interview.skill_matrix || {};

      // If no skill matrix, try to derive from AI feedback
      if (Object.keys(skills).length === 0 && interview.ai_feedback) {
        const feedback = interview.ai_feedback;
        skills.technical = feedback.technical_accuracy || 0;
        skills.communication = feedback.communication_clarity || 0;
        skills.problem_solving = feedback.problem_solving || 0;
        skills.code_quality = feedback.code_quality || 0;
      }

      return {
        id: interview.id,
        candidate_name: interview.candidate_name || 'Anonymous',
        candidate_email: interview.candidate_email,
        drive_title: interview.drive_title,
        skills,
        overall_score: interview.overall_score || 0,
        completed_at: interview.completed_at
      };
    }).filter(item => Object.keys(item.skills).length > 0);
  }, [interviews, selectedDrive]);

  // Sort skill data
  const sortedSkillData = useMemo(() => {
    return [...skillData].sort((a, b) => {
      if (sortBy === 'overall') return b.overall_score - a.overall_score;
      if (sortBy === 'name') return a.candidate_name.localeCompare(b.candidate_name);

      // Sort by specific skill
      const aSkill = a.skills[sortBy] || 0;
      const bSkill = b.skills[sortBy] || 0;
      return bSkill - aSkill;
    });
  }, [skillData, sortBy]);

  // Calculate aggregate statistics
  const aggregateStats = useMemo(() => {
    if (skillData.length === 0) return {};

    const allSkills = {};
    skillData.forEach(item => {
      Object.entries(item.skills).forEach(([skill, score]) => {
        if (!allSkills[skill]) allSkills[skill] = [];
        allSkills[skill].push(score);
      });
    });

    const stats = {};
    Object.entries(allSkills).forEach(([skill, scores]) => {
      stats[skill] = {
        average: scores.reduce((a, b) => a + b, 0) / scores.length,
        max: Math.max(...scores),
        min: Math.min(...scores),
        count: scores.length
      };
    });

    return stats;
  }, [skillData]);

  if (skillData.length === 0) {
    return (
      <div className="p-20 text-center">
        <BarChart3 size={48} className="mx-auto text-slate-700 mb-6" />
        <h2 className="text-2xl font-bold text-white mb-2">No Skill Data Available</h2>
        <p className="text-slate-500">Complete interviews to see skill matrix analytics.</p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Controls */}
      <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="relative">
            <select
              value={selectedDrive}
              onChange={e => setSelectedDrive(e.target.value)}
              className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white focus:ring-2 focus:ring-purple-500 outline-none appearance-none pr-10"
            >
              {drives.map(drive => (
                <option key={drive} value={drive} className="bg-slate-900">
                  {drive === 'all' ? 'All Drives' : drive}
                </option>
              ))}
            </select>
            <ChevronDown size={16} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none" />
          </div>

          <div className="flex bg-white/5 border border-white/10 rounded-xl p-1">
            {[
              { key: 'radar', label: 'Radar View', icon: Target },
              { key: 'table', label: 'Table View', icon: BarChart3 }
            ].map(mode => (
              <button
                key={mode.key}
                onClick={() => setViewMode(mode.key)}
                className={`flex items-center space-x-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  viewMode === mode.key
                    ? 'bg-purple-600 text-white'
                    : 'text-slate-400 hover:text-white hover:bg-white/5'
                }`}
              >
                <mode.icon size={16} />
                <span>{mode.label}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="flex gap-2">
          <button className="flex items-center space-x-2 bg-white/5 border border-white/10 text-slate-300 px-4 py-3 rounded-xl hover:bg-white/10 transition-all">
            <Download size={16} />
            <span className="text-sm font-medium">Export</span>
          </button>
          <button className="flex items-center space-x-2 bg-purple-600 text-white px-4 py-3 rounded-xl hover:bg-purple-500 transition-all">
            <RefreshCw size={16} />
            <span className="text-sm font-medium">Refresh</span>
          </button>
        </div>
      </div>

      {/* Aggregate Statistics */}
      {Object.keys(aggregateStats).length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {Object.entries(aggregateStats).slice(0, 4).map(([skill, stats]) => (
            <motion.div
              key={skill}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-white/5 border border-white/10 rounded-2xl p-4"
            >
              <div className="flex items-center justify-between mb-2">
                <h4 className="text-sm font-bold text-slate-300 capitalize">{skill.replace('_', ' ')}</h4>
                <Award size={16} className="text-purple-400" />
              </div>
              <div className="text-2xl font-black text-white">{stats.average.toFixed(1)}</div>
              <div className="text-xs text-slate-500 mt-1">
                Range: {stats.min.toFixed(1)} - {stats.max.toFixed(1)}
              </div>
            </motion.div>
          ))}
        </div>
      )}

      {/* Main Content */}
      {viewMode === 'radar' ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {sortedSkillData.map((candidate, index) => (
            <motion.div
              key={candidate.id}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: index * 0.1 }}
            >
              <SkillRadarChart
                skills={candidate.skills}
                candidateName={candidate.candidate_name}
              />
            </motion.div>
          ))}
        </div>
      ) : (
        <div className="bg-white/2 border border-white/5 rounded-[2.5rem] overflow-hidden">
          <div className="px-8 py-6 border-b border-white/5 bg-white/2">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-bold text-white">Skill Matrix Table</h3>
              <div className="flex items-center space-x-2">
                <span className="text-sm text-slate-500">Sort by:</span>
                <select
                  value={sortBy}
                  onChange={e => setSortBy(e.target.value)}
                  className="bg-white/5 border border-white/10 rounded-lg px-3 py-1 text-sm text-white focus:ring-2 focus:ring-purple-500 outline-none"
                >
                  <option value="overall">Overall Score</option>
                  <option value="name">Candidate Name</option>
                  {Object.keys(aggregateStats).map(skill => (
                    <option key={skill} value={skill}>{skill.replace('_', ' ')}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-white/2">
                <tr className="text-left">
                  <th className="px-8 py-4 text-xs font-black uppercase tracking-widest text-slate-500">Candidate</th>
                  <th className="px-4 py-4 text-xs font-black uppercase tracking-widest text-slate-500">Overall</th>
                  {Object.keys(aggregateStats).map(skill => (
                    <th key={skill} className="px-4 py-4 text-xs font-black uppercase tracking-widest text-slate-500 capitalize">
                      {skill.replace('_', ' ')}
                    </th>
                  ))}
                  <th className="px-8 py-4 text-xs font-black uppercase tracking-widest text-slate-500">Drive</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {sortedSkillData.map(candidate => (
                  <tr key={candidate.id} className="hover:bg-white/5 transition-all">
                    <td className="px-8 py-6">
                      <div>
                        <div className="font-bold text-white">{candidate.candidate_name}</div>
                        <div className="text-xs text-slate-500">{candidate.candidate_email}</div>
                      </div>
                    </td>
                    <td className="px-4 py-6">
                      <span className={`text-lg font-black ${
                        candidate.overall_score >= 8 ? 'text-emerald-400' :
                        candidate.overall_score >= 6 ? 'text-purple-400' : 'text-amber-400'
                      }`}>
                        {candidate.overall_score.toFixed(1)}
                      </span>
                    </td>
                    {Object.keys(aggregateStats).map(skill => (
                      <td key={skill} className="px-4 py-6">
                        <span className="text-sm font-bold text-slate-300">
                          {candidate.skills[skill]?.toFixed(1) || '—'}
                        </span>
                      </td>
                    ))}
                    <td className="px-8 py-6 text-sm text-slate-400">{candidate.drive_title}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default SkillMatrixTab;