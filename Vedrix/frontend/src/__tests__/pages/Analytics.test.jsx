import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import InterviewReplay from '../../pages/InterviewReplay';
import SkillGapAnalysis from '../../pages/SkillGapAnalysis';
import TeamAnalytics from '../../pages/TeamAnalytics';

vi.mock('../../services/api', () => ({
  default: {
    get: vi.fn(() => Promise.resolve({ data: {} })),
  },
}));

const renderWithRouter = (component, path = '/') => {
  window.history.pushState({}, 'Test page', path);
  return render(
    <BrowserRouter>
      {component}
    </BrowserRouter>
  );
};

describe('InterviewReplay Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading state initially', () => {
    renderWithRouter(<InterviewReplay />, '/replay/1');
    expect(screen.getByText(/loading interview replay/i)).toBeInTheDocument();
  });
});

describe('SkillGapAnalysis Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading state initially', () => {
    renderWithRouter(<SkillGapAnalysis />, '/skill-gap/1');
    expect(screen.getByText(/analyzing skill gaps/i)).toBeInTheDocument();
  });
});

describe('TeamAnalytics Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading state initially', () => {
    renderWithRouter(<TeamAnalytics />, '/analytics/team');
    expect(screen.getByText(/loading analytics/i)).toBeInTheDocument();
  });
});
