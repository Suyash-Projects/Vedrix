import { create } from 'zustand';
import apiClient from '../services/api';

/**
 * Read a cookie by name from document.cookie.
 * Returns undefined if not found.
 */
function getCookie(name) {
  if (typeof document === 'undefined') return undefined;
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
  return undefined;
}

const useAuthStore = create((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: true, // Start loading — checkAuth will resolve
  error: null,

  clearError: () => set({ error: null }),

  login: async (username, password) => {
    set({ isLoading: true, error: null });
    try {
      const params = new URLSearchParams();
      params.append('username', username);
      params.append('password', password);

      // Login sets httpOnly cookies (access_token, refresh_token, csrf_token)
      // automatically on the browser. No token to store in JS.
      await apiClient.post('/auth/login', params, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      });

      // Fetch user profile
      const userResponse = await apiClient.get('/users/me');

      set({
        user: userResponse.data,
        isAuthenticated: true,
        isLoading: false,
      });
      return true;
    } catch (err) {
      set({
        error: err.response?.data?.detail || 'Login failed',
        isLoading: false,
      });
      return false;
    }
  },

  register: async (userData) => {
    set({ isLoading: true, error: null });
    try {
      await apiClient.post('/auth/register', userData);
      set({ isLoading: false });
      return true;
    } catch (err) {
      set({
        error: err.response?.data?.detail || 'Registration failed',
        isLoading: false,
      });
      return false;
    }
  },

  logout: async () => {
    try {
      await apiClient.post('/auth/logout');
    } catch {
      // Ignore errors — clear local state anyway
    }
    set({ user: null, isAuthenticated: false, error: null });
  },

  checkAuth: async () => {
    // Check if CSRF cookie exists as a hint that we might be authenticated
    const csrfToken = getCookie('csrf_token');
    if (!csrfToken) {
      set({ isLoading: false });
      return;
    }

    set({ isLoading: true });
    try {
      const response = await apiClient.get('/users/me');
      set({ user: response.data, isAuthenticated: true, isLoading: false });
    } catch {
      set({ user: null, isAuthenticated: false, isLoading: false });
    }
  },

  /**
   * Refresh the access token using the refresh token cookie.
   * Called automatically by the API interceptor on 401.
   */
  refreshToken: async () => {
    try {
      const response = await apiClient.post('/auth/refresh');
      return response.data;
    } catch (err) {
      // Refresh failed — user needs to re-login
      set({ user: null, isAuthenticated: false });
      throw err;
    }
  },
}));

export default useAuthStore;
