import { useState, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ChevronLeft,
  ChevronRight,
  Brain,
  Calendar,
  Heart,
  ShieldCheck,
  Eye,
  Sparkles,
  Users,
  Workflow,
  Search,
  Activity,
} from 'lucide-react';

const AGENTS = [
  { id: 'memory', name: 'Memory', icon: Brain, action: 'Indexed transcript' },
  { id: 'planner', name: 'Planner', icon: Calendar, action: 'Computed next question' },
  { id: 'sentiment', name: 'Sentiment', icon: Heart, action: 'Scored last response' },
  { id: 'qa', name: 'QA', icon: ShieldCheck, action: 'Validated answer rubric' },
  { id: 'proctor', name: 'Proctor', icon: Eye, action: 'Watching session' },
  { id: 'coaching', name: 'Coaching', icon: Sparkles, action: 'Drafting plan' },
  { id: 'matching', name: 'Matching', icon: Users, action: 'Re-ranking candidates' },
  { id: 'orchestrator', name: 'Orchestrator', icon: Workflow, action: 'Routing tasks' },
  { id: 'research', name: 'Research', icon: Search, action: 'Enriched profile' },
  { id: 'observability', name: 'Observability', icon: Activity, action: 'Tracing spans' },
];

const STATUS_COLORS = {
  active: { dot: 'bg-emerald-400', glow: 'pulse-glow', label: 'text-emerald-400' },
  idle: { dot: 'bg-amber-400', glow: '', label: 'text-amber-400' },
  error: { dot: 'bg-red-400', glow: '', label: 'text-red-400' },
};

const formatRelative = (ms) => {
  if (ms < 5_000) return 'just now';
  if (ms < 60_000) return `${Math.floor(ms / 1000)}s ago`;
  if (ms < 3_600_000) return `${Math.floor(ms / 60_000)}m ago`;
  return `${Math.floor(ms / 3_600_000)}h ago`;
};

const seedAgents = () =>
  AGENTS.map((a, i) => ({
    ...a,
    status: i % 4 === 3 ? 'idle' : 'active',
    lastActionAt: Date.now() - (5_000 + Math.random() * 90_000),
  }));

/**
 * Real-time agent activity indicator panel.
 * Shows on admin/HR pages, fixed to right edge below the navbar.
 *
 * Note: This is a UI scaffold — the agent state mutates on a small
 * client-side timer to give a "live" feel until the backend events
 * stream is wired up.
 */
const AgentActivityPanel = () => {
  const [collapsed, setCollapsed] = useState(false);
  const [agents, setAgents] = useState(seedAgents);
  const [tick, setTick] = useState(0);

  // Force a re-render every few seconds so relative times update
  useEffect(() => {
    const id = setInterval(() => setTick((t) => t + 1), 5000);
    return () => clearInterval(id);
  }, []);

  // Occasionally bump an agent's activity to simulate "live"
  useEffect(() => {
    const id = setInterval(() => {
      setAgents((prev) => {
        const next = [...prev];
        const idx = Math.floor(Math.random() * next.length);
        const r = Math.random();
        next[idx] = {
          ...next[idx],
          lastActionAt: Date.now(),
          status: r > 0.85 ? 'idle' : r > 0.97 ? 'error' : 'active',
        };
        return next;
      });
    }, 3500);
    return () => clearInterval(id);
  }, []);

  const activeCount = useMemo(
    () => agents.filter((a) => a.status === 'active').length,
    [agents]
  );

  return (
    <motion.aside
      initial={false}
      animate={{ width: collapsed ? 56 : 280 }}
      transition={{ type: 'spring', damping: 26, stiffness: 240 }}
      className="fixed top-24 right-4 z-40 bg-[#0a0f1e]/85 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl shadow-black/40 overflow-hidden hidden lg:block"
      aria-label="Agent activity panel"
    >
      {/* Header */}
      <button
        type="button"
        onClick={() => setCollapsed((c) => !c)}
        className="w-full flex items-center justify-between px-3 py-3 hover:bg-white/5 transition-all border-b border-white/5"
        aria-expanded={!collapsed}
        aria-label={collapsed ? 'Expand agent panel' : 'Collapse agent panel'}
      >
        <div className="flex items-center gap-2 min-w-0">
          <div className="relative w-8 h-8 shrink-0 rounded-lg bg-gradient-to-br from-purple-600 to-indigo-500 flex items-center justify-center text-white">
            <Activity size={14} />
            <span className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-emerald-400 pulse-glow border-2 border-[#0a0f1e]" />
          </div>
          {!collapsed && (
            <div className="text-left min-w-0">
              <p className="text-white font-bold text-xs leading-tight truncate">Agents</p>
              <p className="text-[10px] font-bold uppercase tracking-widest text-emerald-400">
                {activeCount} active
              </p>
            </div>
          )}
        </div>
        {!collapsed ? (
          <ChevronRight size={14} className="text-slate-500 shrink-0" />
        ) : (
          <ChevronLeft size={14} className="text-slate-500 shrink-0" />
        )}
      </button>

      <AnimatePresence initial={false}>
        {!collapsed && (
          <motion.div
            key="content"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.22 }}
            className="overflow-hidden"
          >
            <ul className="max-h-[calc(100vh-12rem)] overflow-y-auto py-1.5">
              {agents.map((agent) => {
                const Icon = agent.icon;
                const cfg = STATUS_COLORS[agent.status] || STATUS_COLORS.idle;
                const elapsed = Date.now() - agent.lastActionAt;
                return (
                  <li key={agent.id}>
                    <div className="flex items-center gap-2.5 px-3 py-2 hover:bg-white/[0.03] transition-colors">
                      <div
                        className={`shrink-0 w-7 h-7 rounded-lg bg-white/5 border border-white/5 flex items-center justify-center text-slate-300 ${
                          agent.status === 'active' ? 'text-purple-300' : ''
                        }`}
                      >
                        <Icon size={13} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-1.5">
                          <span className="text-white text-xs font-bold truncate">
                            {agent.name}
                          </span>
                          <span
                            className={`shrink-0 w-1.5 h-1.5 rounded-full ${cfg.dot} ${cfg.glow}`}
                            aria-label={`Status: ${agent.status}`}
                          />
                        </div>
                        <p className="text-[10px] text-slate-500 truncate">
                          {agent.action} · <span className={cfg.label}>{formatRelative(elapsed)}</span>
                          {/* tick subscribers for re-render */}
                          <span className="hidden">{tick}</span>
                        </p>
                      </div>
                    </div>
                  </li>
                );
              })}
            </ul>

            <div className="px-3 py-2 border-t border-white/5 text-[10px] font-bold uppercase tracking-widest text-slate-500 flex items-center justify-between">
              <span>Live</span>
              <span className="flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 pulse-glow" />
                Streaming
              </span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.aside>
  );
};

export default AgentActivityPanel;
