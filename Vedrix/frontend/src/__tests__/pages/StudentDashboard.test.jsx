import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import StudentDashboard from '../../pages/StudentDashboard';

vi.mock('../../services/api', () => ({
  default: {
    get: vi.fn().mockImplementation((url) => {
      if (url.includes('stats')) {
        return Promise.resolve({ data: { total_interviews: 0, completed_interviews: 0, avg_score: null, best_score: null } });
      }
      if (url.includes('interviews')) {
        return Promise.resolve({ data: [] });
      }
      if (url.includes('profile')) {
        return Promise.resolve({ data: {} });
      }
      return Promise.resolve({ data: {} });
    }),
    post: vi.fn().mockResolvedValue({ data: {} }),
    delete: vi.fn().mockResolvedValue({ data: {} }),
  },
}));

vi.mock('../../store/useAuthStore', () => ({
  default: vi.fn(() => ({
    user: { id: 1, first_name: 'Test', user_type: 'student' },
    isAuthenticated: true,
  })),
}));

const renderWithRouter = (component) => {
  return render(
    <BrowserRouter>
      {component}
    </BrowserRouter>
  );
};

describe('StudentDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders welcome message', async () => {
    renderWithRouter(<StudentDashboard />);
    await waitFor(() => {
      expect(screen.getByText(/welcome back/i)).toBeInTheDocument();
    });
  });

  it('shows stats cards', async () => {
    renderWithRouter(<StudentDashboard />);
    await waitFor(() => {
      expect(screen.getByText(/total sessions/i)).toBeInTheDocument();
      expect(screen.getByText(/completed/i)).toBeInTheDocument();
    });
  });

  it('shows interview button', async () => {
    renderWithRouter(<StudentDashboard />);
    await waitFor(() => {
      expect(screen.getByText(/start ai interview/i)).toBeInTheDocument();
    });
  });

  it('shows profile heading', async () => {
    renderWithRouter(<StudentDashboard />);
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /profile/i })).toBeInTheDocument();
    });
  });

  it('shows past sessions section', async () => {
    renderWithRouter(<StudentDashboard />);
    await waitFor(() => {
      expect(screen.getByText(/past sessions/i)).toBeInTheDocument();
    });
  });
});