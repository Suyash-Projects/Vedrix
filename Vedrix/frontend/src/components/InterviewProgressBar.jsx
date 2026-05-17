import { motion } from 'framer-motion';
import { Clock, Target, Award } from 'lucide-react';

/**
 * InterviewProgressBar — Shows real-time interview progress.
 * 
 * Displays:
 * - Current question number / total questions
 * - Skills covered percentage
 * - Time elapsed
 * - Visual progress bar
 */
const InterviewProgressBar = ({
  currentQuestion = 1,
  totalQuestions = 15,
  skillsCovered = 0,
  totalSkills = 8,
  timeElapsed = 0,
  advisorReady = false,
  advisorConfidence = 0,
}) => {
  // Format time as MM:SS
  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const questionProgress = (currentQuestion / totalQuestions) * 100;
  const skillProgress = totalSkills > 0 ? (skillsCovered / totalSkills) * 100 : 0;

  return (
    <div className="bg-slate-900/80 backdrop-blur-xl border border-white/5 rounded-2xl p-4">
      {/* Top row: Question progress */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Target className="w-4 h-4 text-purple-400" />
          <span className="text-sm font-bold text-white">
            Question {currentQuestion} of {totalQuestions}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4 text-slate-400" />
          <span className="text-sm font-mono text-slate-300">
            {formatTime(timeElapsed)}
          </span>
        </div>
      </div>

      {/* Question progress bar */}
      <div className="w-full bg-white/5 rounded-full h-2 mb-4 overflow-hidden">
        <motion.div
          className="h-full bg-gradient-to-r from-purple-500 to-indigo-500 rounded-full"
          initial={{ width: 0 }}
          animate={{ width: `${questionProgress}%` }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
        />
      </div>

      {/* Bottom row: Skills + Advisor */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Award className="w-4 h-4 text-emerald-400" />
          <span className="text-xs font-bold text-slate-400">
            Skills: {skillsCovered}/{totalSkills} ({Math.round(skillProgress)}%)
          </span>
        </div>

        {/* Phase 1A: Advisor status indicator */}
        {advisorReady && (
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse" />
            <span className="text-xs font-bold text-emerald-400">
              Ready to close ({Math.round(advisorConfidence * 100)}%)
            </span>
          </div>
        )}
      </div>
    </div>
  );
};

export default InterviewProgressBar;
