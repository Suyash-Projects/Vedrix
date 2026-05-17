/**
 * Notification utilities for adding and managing in-app notifications.
 */

/**
 * Add a new notification to the notification store.
 * @param {Object} notification - The notification object
 * @param {string} notification.title - Notification title
 * @param {string} notification.message - Notification message
 * @param {string} notification.type - Notification type (interview_completed, new_candidate, etc.)
 * @returns {Object} The created notification
 */
export const addNotification = (notification) => {
  const stored = localStorage.getItem('vedrix_notifications');
  const notifications = stored ? JSON.parse(stored) : [];

  const newNotification = {
    id: Date.now().toString(),
    timestamp: new Date().toISOString(),
    read: false,
    ...notification,
  };

  // Keep only last 50 notifications
  const updated = [newNotification, ...notifications].slice(0, 50);
  localStorage.setItem('vedrix_notifications', JSON.stringify(updated));

  return newNotification;
};
