import { create } from 'zustand';

/**
 * Premium toast notification store.
 *
 * Usage:
 *   import useToastStore from './store/useToastStore';
 *   const addToast = useToastStore(s => s.addToast);
 *   addToast({ type: 'success', title: 'Saved', message: 'Profile updated.' });
 *
 * Toast types: 'success' | 'error' | 'warning' | 'info'
 * Default duration: 4000ms (set duration: 0 to disable auto-dismiss)
 */
const useToastStore = create((set, get) => ({
  toasts: [],

  addToast: ({ type = 'info', title = '', message = '', duration = 4000 } = {}) => {
    const id = `toast-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    const toast = { id, type, title, message, duration, createdAt: Date.now() };

    set((state) => ({ toasts: [...state.toasts, toast] }));

    if (duration > 0) {
      setTimeout(() => {
        get().removeToast(id);
      }, duration);
    }
    return id;
  },

  removeToast: (id) => {
    set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) }));
  },

  clearToasts: () => set({ toasts: [] }),

  // Convenience helpers
  success: (title, message, duration) =>
    get().addToast({ type: 'success', title, message, duration }),
  error: (title, message, duration) =>
    get().addToast({ type: 'error', title, message, duration: duration ?? 6000 }),
  warning: (title, message, duration) =>
    get().addToast({ type: 'warning', title, message, duration }),
  info: (title, message, duration) =>
    get().addToast({ type: 'info', title, message, duration }),
}));

export default useToastStore;
