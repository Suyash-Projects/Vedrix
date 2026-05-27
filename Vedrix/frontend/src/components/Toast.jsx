import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle2, AlertCircle, AlertTriangle, Info, X } from 'lucide-react';
import useToastStore from '../store/useToastStore';

const TOAST_CONFIG = {
  success: {
    icon: CheckCircle2,
    iconColor: 'text-emerald-400',
    bgGradient: 'from-emerald-500/10 to-emerald-500/5',
    borderColor: 'border-emerald-500/30',
    progressColor: 'bg-emerald-400',
    iconRingColor: 'bg-emerald-500/15',
  },
  error: {
    icon: AlertCircle,
    iconColor: 'text-red-400',
    bgGradient: 'from-red-500/10 to-red-500/5',
    borderColor: 'border-red-500/30',
    progressColor: 'bg-red-400',
    iconRingColor: 'bg-red-500/15',
  },
  warning: {
    icon: AlertTriangle,
    iconColor: 'text-amber-400',
    bgGradient: 'from-amber-500/10 to-amber-500/5',
    borderColor: 'border-amber-500/30',
    progressColor: 'bg-amber-400',
    iconRingColor: 'bg-amber-500/15',
  },
  info: {
    icon: Info,
    iconColor: 'text-purple-400',
    bgGradient: 'from-purple-500/10 to-purple-500/5',
    borderColor: 'border-purple-500/30',
    progressColor: 'bg-purple-400',
    iconRingColor: 'bg-purple-500/15',
  },
};

const ToastItem = ({ toast, onClose }) => {
  const cfg = TOAST_CONFIG[toast.type] || TOAST_CONFIG.info;
  const Icon = cfg.icon;

  return (
    <motion.div
      layout
      initial={{ opacity: 0, x: 60, scale: 0.92 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      exit={{ opacity: 0, x: 60, scale: 0.92, transition: { duration: 0.18 } }}
      transition={{ type: 'spring', damping: 22, stiffness: 280 }}
      className={`pointer-events-auto relative w-[360px] max-w-[calc(100vw-2rem)] overflow-hidden
        rounded-2xl border ${cfg.borderColor}
        bg-gradient-to-br ${cfg.bgGradient}
        backdrop-blur-xl shadow-2xl shadow-black/40`}
      role="status"
      aria-live="polite"
    >
      <div className="absolute inset-0 bg-[#0a0f1e]/80 -z-10" />

      <div className="flex items-start gap-3 p-4">
        <div className={`shrink-0 w-9 h-9 rounded-xl ${cfg.iconRingColor} flex items-center justify-center`}>
          <Icon className={cfg.iconColor} size={18} />
        </div>

        <div className="flex-1 min-w-0 pt-0.5">
          {toast.title && (
            <p className="text-sm font-bold text-white leading-tight">{toast.title}</p>
          )}
          {toast.message && (
            <p className={`text-xs text-slate-400 leading-relaxed ${toast.title ? 'mt-1' : ''}`}>
              {toast.message}
            </p>
          )}
        </div>

        <button
          onClick={onClose}
          aria-label="Dismiss notification"
          className="shrink-0 w-7 h-7 rounded-lg flex items-center justify-center text-slate-500 hover:text-white hover:bg-white/5 transition-all active:scale-95"
        >
          <X size={14} />
        </button>
      </div>

      {toast.duration > 0 && (
        <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-white/5">
          <div
            className={`h-full ${cfg.progressColor} toast-progress`}
            style={{ animationDuration: `${toast.duration}ms` }}
          />
        </div>
      )}
    </motion.div>
  );
};

const Toast = () => {
  const toasts = useToastStore((s) => s.toasts);
  const removeToast = useToastStore((s) => s.removeToast);

  return (
    <div
      className="fixed bottom-[calc(var(--floating-panel-bottom)+4.5rem)] right-[var(--floating-panel-right)] z-[9999] flex flex-col-reverse gap-3 pointer-events-none"
      aria-label="Notifications"
    >
      <AnimatePresence initial={false}>
        {toasts.map((t) => (
          <ToastItem key={t.id} toast={t} onClose={() => removeToast(t.id)} />
        ))}
      </AnimatePresence>
    </div>
  );
};

export default Toast;
