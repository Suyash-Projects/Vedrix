import { motion, AnimatePresence } from 'framer-motion';
import { Wifi, WifiOff, Loader2, Save } from 'lucide-react';

/**
 * ConnectionStatus — Shows WebSocket connection state with visual indicators.
 *
 * States:
 * - connected: Green indicator, no banner
 * - reconnecting: Yellow banner with timer
 * - offline: Red banner with queued count
 * - syncing: Blue banner showing sync progress
 */
const ConnectionStatus = ({
  status = 'connected', // 'connected' | 'reconnecting' | 'offline' | 'syncing'
  reconnectAttempts = 0,
  queuedCount = 0,
  syncProgress = null, // { synced, total } or null
  onSaveDraft = null,
}) => {
  const isDisconnected = status !== 'connected';

  if (!isDisconnected && queuedCount === 0) {
    return (
      <div className="flex items-center space-x-2 px-3 py-1.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
        <Wifi size={14} className="text-emerald-500" />
        <span className="text-[10px] font-black uppercase tracking-widest text-emerald-400">
          Connected
        </span>
      </div>
    );
  }

  return (
    <div className="relative">
      {/* Inline status indicator */}
      <div className={`flex items-center space-x-2 px-3 py-1.5 rounded-xl border ${
        status === 'reconnecting'
          ? 'bg-amber-500/10 border-amber-500/20'
          : status === 'offline'
          ? 'bg-red-500/10 border-red-500/20'
          : status === 'syncing'
          ? 'bg-blue-500/10 border-blue-500/20'
          : 'bg-emerald-500/10 border-emerald-500/20'
      }`}>
        {status === 'reconnecting' && (
          <Loader2 size={14} className="text-amber-500 animate-spin" />
        )}
        {status === 'offline' && (
          <WifiOff size={14} className="text-red-500" />
        )}
        {status === 'syncing' && (
          <Loader2 size={14} className="text-blue-500 animate-spin" />
        )}
        {status === 'connected' && (
          <Wifi size={14} className="text-emerald-500" />
        )}
        <span className={`text-[10px] font-black uppercase tracking-widest ${
          status === 'reconnecting'
            ? 'text-amber-400'
            : status === 'offline'
            ? 'text-red-400'
            : status === 'syncing'
            ? 'text-blue-400'
            : 'text-emerald-400'
        }`}>
          {status === 'reconnecting' && `Reconnecting (${reconnectAttempts})`}
          {status === 'offline' && `Offline (${queuedCount} queued)`}
          {status === 'syncing' && `Syncing (${syncProgress?.synced}/${syncProgress?.total})`}
          {status === 'connected' && 'Connected'}
        </span>
      </div>

      {/* Full-width banner for disconnected states */}
      <AnimatePresence>
        {status !== 'connected' && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className={`absolute top-full left-0 right-0 mt-2 px-6 py-4 rounded-2xl border backdrop-blur-xl z-50 ${
              status === 'reconnecting'
                ? 'bg-amber-500/10 border-amber-500/20'
                : status === 'offline'
                ? 'bg-red-500/10 border-red-500/20'
                : 'bg-blue-500/10 border-blue-500/20'
            }`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                {status === 'reconnecting' && (
                  <>
                    <Loader2 size={18} className="text-amber-400 animate-spin" />
                    <div>
                      <p className="text-sm font-bold text-amber-300">Reconnecting...</p>
                      <p className="text-xs text-amber-400/70">
                        Attempt {reconnectAttempts} — Your session is being restored
                      </p>
                    </div>
                  </>
                )}
                {status === 'offline' && (
                  <>
                    <WifiOff size={18} className="text-red-400" />
                    <div>
                      <p className="text-sm font-bold text-red-300">Connection Lost</p>
                      <p className="text-xs text-red-400/70">
                        {queuedCount > 0
                          ? `${queuedCount} answer(s) saved locally — will sync when reconnected`
                          : 'Answers will be saved locally until connection is restored'}
                      </p>
                    </div>
                  </>
                )}
                {status === 'syncing' && (
                  <>
                    <Loader2 size={18} className="text-blue-400 animate-spin" />
                    <div>
                      <p className="text-sm font-bold text-blue-300">Syncing Answers...</p>
                      <p className="text-xs text-blue-400/70">
                        Restoring {syncProgress?.total} queued answer(s)
                      </p>
                    </div>
                  </>
                )}
              </div>

              {/* Save Draft button — only show when offline */}
              {status === 'offline' && onSaveDraft && (
                <button
                  onClick={onSaveDraft}
                  className="flex items-center space-x-2 px-4 py-2 rounded-xl bg-white/10 border border-white/10 text-white text-xs font-bold hover:bg-white/20 transition-all"
                >
                  <Save size={14} />
                  <span>Save Draft</span>
                </button>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default ConnectionStatus;
