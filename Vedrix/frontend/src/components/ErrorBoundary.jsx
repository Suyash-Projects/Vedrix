import { Component } from 'react';
import { AlertTriangle, RefreshCw, Home, Bug } from 'lucide-react';

/**
 * ErrorBoundary — Catches JavaScript errors in child component tree.
 *
 * Renders a premium glassmorphic error fallback UI with:
 * - Error message and stack trace (collapsed)
 * - "Try Again" button to reset state
 * - "Go to Dashboard" link for navigation
 * - componentDidCatch logs full stack to console
 *
 * Platform Completion Task 10.1
 */
class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      showDetails: false,
    };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('[ErrorBoundary] Caught error:', error);
    console.error('[ErrorBoundary] Component stack:', errorInfo?.componentStack);
    this.setState({ errorInfo });
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null, errorInfo: null, showDetails: false });
  };

  handleDashboard = () => {
    window.location.href = '/dashboard';
  };

  render() {
    if (this.state.hasError) {
      const { error, errorInfo, showDetails } = this.state;
      const { fallbackTitle, fallbackMessage } = this.props;

      return (
        <div className="min-h-[60vh] flex items-center justify-center p-8">
          <div className="max-w-lg w-full">
            {/* Error Card */}
            <div className="bg-white/5 backdrop-blur-2xl border border-red-500/20 rounded-3xl p-10 shadow-2xl relative overflow-hidden">
              {/* Background glow */}
              <div className="absolute inset-0 pointer-events-none">
                <div className="absolute top-0 left-1/2 -translate-x-1/2 w-48 h-48 bg-red-500/10 blur-[80px] rounded-full" />
              </div>

              <div className="relative z-10">
                {/* Icon */}
                <div className="w-16 h-16 bg-red-500/10 border border-red-500/20 rounded-2xl flex items-center justify-center mb-6">
                  <AlertTriangle size={32} className="text-red-400" />
                </div>

                {/* Title */}
                <h2 className="text-2xl font-black text-white mb-3 tracking-tight">
                  {fallbackTitle || 'Something went wrong'}
                </h2>

                {/* Message */}
                <p className="text-slate-400 text-sm leading-relaxed mb-8">
                  {fallbackMessage ||
                    'An unexpected error occurred while rendering this page. You can try again or return to the dashboard.'}
                </p>

                {/* Error message preview */}
                {error?.message && (
                  <div className="bg-red-500/5 border border-red-500/10 rounded-2xl p-4 mb-6">
                    <div className="flex items-center space-x-2 mb-2">
                      <Bug size={14} className="text-red-400" />
                      <span className="text-[10px] font-black uppercase tracking-widest text-red-400">
                        Error Details
                      </span>
                    </div>
                    <p className="text-xs text-red-300/80 font-mono break-all">
                      {error.message}
                    </p>
                  </div>
                )}

                {/* Expandable stack trace */}
                {errorInfo?.componentStack && (
                  <div className="mb-6">
                    <button
                      onClick={() => this.setState({ showDetails: !showDetails })}
                      className="text-[10px] font-black uppercase tracking-widest text-slate-500 hover:text-slate-300 transition-colors"
                    >
                      {showDetails ? '▼ Hide' : '▶ Show'} Stack Trace
                    </button>
                    {showDetails && (
                      <pre className="mt-3 bg-slate-900/50 border border-white/5 rounded-xl p-4 text-[10px] text-slate-500 font-mono overflow-auto max-h-48 leading-relaxed">
                        {errorInfo.componentStack}
                      </pre>
                    )}
                  </div>
                )}

                {/* Action buttons */}
                <div className="flex space-x-3">
                  <button
                    onClick={this.handleRetry}
                    className="flex-1 flex items-center justify-center space-x-2 bg-purple-600 hover:bg-purple-500 text-white py-3.5 rounded-xl font-black uppercase tracking-widest text-xs transition-all shadow-lg shadow-purple-600/20"
                  >
                    <RefreshCw size={16} />
                    <span>Try Again</span>
                  </button>
                  <button
                    onClick={this.handleDashboard}
                    className="flex-1 flex items-center justify-center space-x-2 bg-white/5 hover:bg-white/10 border border-white/10 text-slate-300 py-3.5 rounded-xl font-black uppercase tracking-widest text-xs transition-all"
                  >
                    <Home size={16} />
                    <span>Dashboard</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
