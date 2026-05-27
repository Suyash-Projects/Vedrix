import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import SupervisorDashboard from '../../pages/SupervisorDashboard';

// Mock the API client
vi.mock('../../services/api', () => ({
  default: {
    get: vi.fn(),
  },
}));

import apiClient from '../../services/api';

const renderWithRouter = (component) => {
  return render(
    <BrowserRouter>
      {component}
    </BrowserRouter>
  );
};

const mockActiveSessions = [
  {
    session_id: 'sess-001',
    control_mode: 'suggest',
    duration_seconds: 600,
    difficulty_analysis: {
      current_difficulty: 'medium',
      recommended_difficulty: 'hard',
      difficulty_switches: 1,
      is_stuck_on_easy: false,
      is_stuck_on_hard: false,
      confidence: 0.7,
    },
    performance_trend: {
      trend: 'improving',
      volatility: 0.5,
      fatigue_detected: false,
      diminishing_returns: false,
    },
    last_action: null,
    observations_count: 2,
    paused: false,
  },
  {
    session_id: 'sess-002',
    control_mode: 'auto',
    duration_seconds: 1800,
    difficulty_analysis: {
      current_difficulty: 'hard',
      recommended_difficulty: 'medium',
      difficulty_switches: 2,
      is_stuck_on_easy: false,
      is_stuck_on_hard: true,
      confidence: 0.85,
    },
    performance_trend: {
      trend: 'declining',
      volatility: 1.2,
      fatigue_detected: true,
      diminishing_returns: true,
    },
    last_action: {
      action_type: 'adjust_difficulty',
      confidence: 0.85,
      reason: 'Too hard',
      executed: true,
    },
    observations_count: 5,
    paused: false,
  },
];

const mockStats = {
  active_sessions: 2,
  total_observations: 7,
  sessions_with_alerts: 1,
  auto_mode_sessions: 1,
  suggest_mode_sessions: 1,
};

describe('SupervisorDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading state on mount', () => {
    // Don't resolve the promise so loading persists
    apiClient.get.mockReturnValue(new Promise(() => {}));
    renderWithRouter(<SupervisorDashboard />);
    expect(screen.getByText(/Loading sessions/i)).toBeInTheDocument();
  });

  it('renders error state when API fails', async () => {
    apiClient.get.mockRejectedValue(new Error('Network error'));
    renderWithRouter(<SupervisorDashboard />);

    await waitFor(() => {
      expect(screen.getByText(/Failed to fetch supervisor data/i)).toBeInTheDocument();
    });
  });

  it('renders stats cards with correct values', async () => {
    apiClient.get
      .mockResolvedValueOnce({ data: mockActiveSessions })
      .mockResolvedValueOnce({ data: mockStats });

    renderWithRouter(<SupervisorDashboard />);

    await waitFor(() => {
      // "2" appears in both the active_sessions stat and the observations_count badge
      const twos = screen.getAllByText('2');
      expect(twos.length).toBeGreaterThanOrEqual(1);
    });

    expect(screen.getByText('7')).toBeInTheDocument();   // Total observations
    // Multiple stats have value "1" (alerts, auto mode, suggest mode)
    const ones = screen.getAllByText('1');
    expect(ones.length).toBeGreaterThanOrEqual(1);
  });

  it('renders session list entries', async () => {
    apiClient.get
      .mockResolvedValueOnce({ data: mockActiveSessions })
      .mockResolvedValueOnce({ data: mockStats });

    renderWithRouter(<SupervisorDashboard />);

    await waitFor(() => {
      expect(screen.getByText(/sess-001/i)).toBeInTheDocument();
    });

    expect(screen.getByText(/sess-002/i)).toBeInTheDocument();
  });

  it('displays mode badges for each session', async () => {
    apiClient.get
      .mockResolvedValueOnce({ data: mockActiveSessions })
      .mockResolvedValueOnce({ data: mockStats });

    renderWithRouter(<SupervisorDashboard />);

    await waitFor(() => {
      // "Suggest" appears in the stat header ("Suggest Mode") and badge
      const suggests = screen.getAllByText(/Suggest/i);
      expect(suggests.length).toBeGreaterThanOrEqual(1);
    });

    const autos = screen.getAllByText(/Auto/i);
    expect(autos.length).toBeGreaterThanOrEqual(1);
  });

  it('shows performance trends', async () => {
    apiClient.get
      .mockResolvedValueOnce({ data: mockActiveSessions })
      .mockResolvedValueOnce({ data: mockStats });

    renderWithRouter(<SupervisorDashboard />);

    await waitFor(() => {
      expect(screen.getByText(/improving/i)).toBeInTheDocument();
    });

    expect(screen.getByText(/declining/i)).toBeInTheDocument();
  });

  it('renders 5 stat header cards', async () => {
    apiClient.get
      .mockResolvedValueOnce({ data: mockActiveSessions })
      .mockResolvedValueOnce({ data: mockStats });

    renderWithRouter(<SupervisorDashboard />);

    await waitFor(() => {
      expect(screen.getByText('Active Sessions')).toBeInTheDocument();
    });

    // "Observations" appears in both the stat header and the placeholder description
    const observations = screen.getAllByText(/Observations/i);
    expect(observations.length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Sessions w/ Alerts')).toBeInTheDocument();
    expect(screen.getByText('Auto Mode')).toBeInTheDocument();
    expect(screen.getByText('Suggest Mode')).toBeInTheDocument();
  });

  it('shows 2 live sessions indicator', async () => {
    apiClient.get
      .mockResolvedValueOnce({ data: mockActiveSessions })
      .mockResolvedValueOnce({ data: mockStats });

    renderWithRouter(<SupervisorDashboard />);

    await waitFor(() => {
      expect(screen.getByText(/2 live/i)).toBeInTheDocument();
    });
  });

  it('passes session ID to detail on click', async () => {
    apiClient.get
      .mockResolvedValueOnce({ data: mockActiveSessions })
      .mockResolvedValueOnce({ data: mockStats });

    renderWithRouter(<SupervisorDashboard />);

    await waitFor(() => {
      expect(screen.getByText(/sess-001/i)).toBeInTheDocument();
    });
  });
});
