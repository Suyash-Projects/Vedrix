import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle2, X, Clock, AlertCircle } from 'lucide-react';

/**
 * AdvisorBadge — Green notification that appears when AI advisor
 * suggests the interview is ready to close.
 *
 * Design Philosophy:
 * - AI never ends the interview — only suggests
 * - HR always in control — can dismiss or act
 * - Clear, professional, non-intrusive
 */
const AdvisorBadge = ({ suggestion, onCloseInterview, onDismiss }) => {
  const [dismissed, setDismissed] = useState(false);

  if (!suggestion?.ready_to_close || dismissed) return null;

  const categoryIcons = {
    strong_performance: CheckCircle2,
    skill_coverage_complete: CheckCircle2,
    diminishing_returns: Clock,
    time_efficient: Clock,
    insufficient_data: AlertCircle,
    needs_more_time: AlertCircle,
  };

  const Icon = categoryIcons[suggestion.reason_category] || CheckCircle2;

  const confidenceColor =
    suggestion.confidence >= 0.8
      ? 'text-emerald-400'
      : suggestion.confidence >= 0.6
        ? 'text-yellow-400'
        : 'text-orange-400';

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: 20, scale: 0.95 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 20, scale: 0.95 }}
        transition={{ duration: 0.3, ease: 'easeOut' }}
        className="fixed bottom-6 right-6 z-50 max-w-sm"
      >
        <div className="bg-slate-900/95 backdrop-blur-xl border border-emerald-500/30 rounded-2xl p-5 shadow-2xl shadow-emerald-500/10">
          {/* Header */}
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-start gap-3 flex-1">
              <div className="w-9 h-9 bg-emerald-500/15 rounded-xl flex items-center justify-center flex-shrink-0 mt-0.5">
                <Icon className="w-5 h-5 text-emerald-400" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <h4 className="text-sm font-bold text-emerald-300">
                    Ready to Close
                  </h4>
                  <span
                    className={`text-xs font-bold ${confidenceColor} bg-white/5 px-2 py-0.5 rounded-full`}
                  >
                    {Math.round(suggestion.confidence * 100)}%
                  </span>
                </div>
                <p className="text-xs text-slate-400 mt-1.5 leading-relaxed">
                  {suggestion.reason}
                </p>
              </div>
            </div>
            <button
              onClick={() => setDismissed(true)}
              className="text-slate-500 hover:text-white transition-colors p-1 rounded-lg hover:bg-white/5"
              title="Dismiss suggestion"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Actions */}
          <div className="flex gap-2 mt-4 pt-4 border-t border-white/5">
            <button
              onClick={() => {
                onCloseInterview?.();
                setDismissed(true);
              }}
              className="flex-1 px-4 py-2.5 bg-emerald-500 text-white text-xs font-bold rounded-xl hover:bg-emerald-400 transition-all active:scale-95 shadow-lg shadow-emerald-500/20"
            >
              Close Interview
            </button>
            <button
              onClick={() => {
                onDismiss?.();
                setDismissed(true);
              }}
              className="px-4 py-2.5 bg-white/5 text-slate-300 text-xs font-bold rounded-xl hover:bg-white/10 transition-all active:scale-95"
            >
              Continue
            </button>
          </div>
        </div>
      </motion.div>
    </AnimatePresence>
  );
};

export default AdvisorBadge;
