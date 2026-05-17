import { useState, useEffect, useCallback } from 'react';
import {
  Bell,
  Check,
  X,
  Mail,
  Calendar,
  User,
  AlertCircle,
  CheckCircle,
  Star
} from 'lucide-react';

const Notifications = () => {
  const [notifications, setNotifications] = useState(() => {
    const stored = localStorage.getItem('vedrix_notifications');
    return stored ? JSON.parse(stored) : [];
  });
  const [showDropdown, setShowDropdown] = useState(false);

  const unreadCount = notifications.filter(n => !n.read).length;

  // Save notifications to localStorage when they change
  useEffect(() => {
    if (notifications.length > 0) {
      localStorage.setItem('vedrix_notifications', JSON.stringify(notifications));
    }
  }, [notifications]);

  const markAsRead = useCallback((id) => {
    setNotifications(prev =>
      prev.map(n => n.id === id ? { ...n, read: true } : n)
    );
  }, []);

  const markAllAsRead = useCallback(() => {
    setNotifications(prev =>
      prev.map(n => ({ ...n, read: true }))
    );
  }, []);

  const clearAll = useCallback(() => {
    setNotifications([]);
    localStorage.removeItem('vedrix_notifications');
  }, []);

  const deleteNotification = useCallback((id) => {
    setNotifications(prev => prev.filter(n => n.id !== id));
  }, []);

  const getIcon = (type) => {
    switch (type) {
      case 'interview_completed':
        return <CheckCircle className="text-emerald-400" size={18} />;
      case 'new_candidate':
        return <User className="text-blue-400" size={18} />;
      case 'feedback_submitted':
        return <Star className="text-amber-400" size={18} />;
      case 'interview_scheduled':
        return <Calendar className="text-purple-400" size={18} />;
      case 'email_sent':
        return <Mail className="text-violet-400" size={18} />;
      case 'alert':
        return <AlertCircle className="text-red-400" size={18} />;
      default:
        return <Bell className="text-slate-400" size={18} />;
    }
  };

  const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return 'Just now';
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    return `${days}d ago`;
  };

  return (
    <div className="relative">
      {/* Bell Icon */}
      <button
        onClick={() => setShowDropdown(!showDropdown)}
        className="relative p-2 rounded-xl hover:bg-white/5 transition-colors"
      >
        <Bell size={20} className="text-slate-400" />
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 rounded-full text-[10px] font-bold text-white flex items-center justify-center">
            {unreadCount}
          </span>
        )}
      </button>

      {/* Dropdown */}
      {showDropdown && (
        <div className="absolute right-0 top-full mt-2 w-80 bg-[#0f1420] border border-white/10 rounded-2xl shadow-2xl shadow-black/50 z-[300]">
          {/* Header */}
          <div className="px-4 py-3 border-b border-white/5 flex justify-between items-center">
            <h3 className="font-bold text-white text-sm">Notifications</h3>
            <div className="flex items-center space-x-2">
              {unreadCount > 0 && (
                <button
                  onClick={markAllAsRead}
                  className="text-xs text-purple-400 hover:text-purple-300 font-bold"
                >
                  Mark all read
                </button>
              )}
              {notifications.length > 0 && (
                <button
                  onClick={clearAll}
                  className="text-xs text-slate-500 hover:text-slate-400 font-bold"
                >
                  Clear all
                </button>
              )}
            </div>
          </div>

          {/* Notifications List */}
          <div className="max-h-96 overflow-y-auto">
            {notifications.length === 0 ? (
              <div className="p-8 text-center text-slate-500 text-sm">
                No notifications
              </div>
            ) : (
              notifications.map((notification) => (
                <div
                  key={notification.id}
                  className={`px-4 py-3 border-b border-white/5 hover:bg-white/5 transition-colors ${
                    !notification.read ? 'bg-white/2' : ''
                  }`}
                >
                  <div className="flex items-start space-x-3">
                    <div className="mt-0.5">
                      {getIcon(notification.type)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-white font-medium truncate">
                        {notification.title}
                      </p>
                      <p className="text-xs text-slate-500 mt-0.5">
                        {notification.message}
                      </p>
                      <p className="text-[10px] text-slate-600 mt-1">
                        {formatTime(notification.timestamp)}
                      </p>
                    </div>
                    <div className="flex items-center space-x-1">
                      {!notification.read && (
                        <button
                          onClick={() => markAsRead(notification.id)}
                          className="p-1 rounded hover:bg-white/10 text-slate-500 hover:text-emerald-400 transition-colors"
                          title="Mark as read"
                        >
                          <Check size={14} />
                        </button>
                      )}
                      <button
                        onClick={() => deleteNotification(notification.id)}
                        className="p-1 rounded hover:bg-white/10 text-slate-500 hover:text-red-400 transition-colors"
                        title="Delete"
                      >
                        <X size={14} />
                      </button>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default Notifications;
