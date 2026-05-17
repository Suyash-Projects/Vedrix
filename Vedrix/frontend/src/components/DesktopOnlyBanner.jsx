import { useState } from 'react';
import { Monitor, X } from 'lucide-react';

/**
 * DesktopOnlyBanner — Shown when user tries to access interview on mobile/tablet.
 * Interviews require desktop for proper functionality (code editor, webcam, etc.).
 */
const DesktopOnlyBanner = ({ onDismiss }) => {
  const dismissed = typeof localStorage !== 'undefined' && localStorage.getItem('desktop-banner-dismissed');
  const [visible, setVisible] = useState(!dismissed);

  const handleDismiss = () => {
    localStorage.setItem('desktop-banner-dismissed', 'true');
    setVisible(false);
    onDismiss?.();
  };

  if (!visible) return null;

  return (
    <div className="fixed inset-0 z-[9999] bg-slate-950/95 backdrop-blur-xl flex items-center justify-center p-6">
      <div className="max-w-lg w-full">
        <div className="bg-slate-900 border border-amber-500/20 rounded-3xl p-8 shadow-2xl shadow-amber-500/5 relative">
          {/* Close button */}
          <button
            onClick={handleDismiss}
            className="absolute top-4 right-4 text-slate-500 hover:text-white transition-colors p-2 rounded-xl hover:bg-white/5"
            title="Dismiss"
          >
            <X className="w-5 h-5" />
          </button>

          {/* Icon */}
          <div className="w-16 h-16 bg-amber-500/10 rounded-2xl flex items-center justify-center mx-auto mb-6">
            <Monitor className="w-8 h-8 text-amber-400" />
          </div>

          {/* Content */}
          <h2 className="text-2xl font-bold text-white text-center mb-3">
            Desktop Required
          </h2>
          <p className="text-slate-400 text-center text-sm leading-relaxed mb-6">
            Interviews require a desktop computer for the best experience. Features like the code editor, webcam, and screen sharing are not available on mobile devices.
          </p>

          {/* What works on mobile */}
          <div className="bg-white/5 rounded-2xl p-5 mb-6">
            <h3 className="text-xs font-bold uppercase tracking-widest text-slate-500 mb-3">
              Available on Mobile
            </h3>
            <ul className="space-y-2 text-sm text-slate-300">
              <li className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full" />
                View dashboard and analytics
              </li>
              <li className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full" />
                Check interview reports
              </li>
              <li className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full" />
                Manage recruitment drives
              </li>
              <li className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full" />
                Update profile settings
              </li>
            </ul>
          </div>

          {/* What requires desktop */}
          <div className="bg-white/5 rounded-2xl p-5 mb-6">
            <h3 className="text-xs font-bold uppercase tracking-widest text-slate-500 mb-3">
              Requires Desktop
            </h3>
            <ul className="space-y-2 text-sm text-slate-300">
              <li className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 bg-amber-400 rounded-full" />
                Conduct interviews
              </li>
              <li className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 bg-amber-400 rounded-full" />
                Code editor & execution
              </li>
              <li className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 bg-amber-400 rounded-full" />
                Webcam & voice recording
              </li>
            </ul>
          </div>

          {/* Action */}
          <p className="text-xs text-slate-500 text-center">
            Please switch to a desktop or laptop computer to continue.
          </p>
        </div>
      </div>
    </div>
  );
};

export default DesktopOnlyBanner;
