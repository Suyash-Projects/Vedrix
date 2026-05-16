import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,  // Send cookies with every request
});

// Add interceptor to attach CSRF token to state-changing requests
apiClient.interceptors.request.use((config) => {
  // For POST, PUT, DELETE, PATCH — attach CSRF token from cookie
  if (['post', 'put', 'delete', 'patch'].includes(config.method?.toLowerCase())) {
    const csrfToken = getCookie('csrf_token');
    if (csrfToken) {
      config.headers['X-CSRF-Token'] = csrfToken;
    }
  }
  return config;
}, (error) => {
  return Promise.reject(error);
});

// Auto-redirect on 401 — expired or invalid session
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Clear local state
      if (typeof window !== 'undefined') {
        // Avoid redirect loop if already on login page
        if (!window.location.pathname.startsWith('/login')) {
          window.location.href = '/login';
        }
      }
    }
    return Promise.reject(error);
  }
);

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

export default apiClient;
