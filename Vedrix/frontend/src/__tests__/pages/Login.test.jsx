import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import Login from '../../pages/Login';
import useAuthStore from '../../store/useAuthStore';

vi.mock('../../store/useAuthStore', () => ({
  default: vi.fn(() => ({
    login: vi.fn(),
    isLoading: false,
    error: null,
  })),
}));

const renderWithRouter = (component) => {
  return render(
    <BrowserRouter>
      {component}
    </BrowserRouter>
  );
};

describe('Login Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders login form with welcome message', () => {
    renderWithRouter(<Login />);
    expect(screen.getByText(/welcome back/i)).toBeInTheDocument();
  });

  it('shows sign in button', () => {
    renderWithRouter(<Login />);
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });

  it('has username input', () => {
    renderWithRouter(<Login />);
    expect(screen.getByPlaceholderText(/your username/i)).toBeInTheDocument();
  });

  it('has password input', () => {
    renderWithRouter(<Login />);
    expect(screen.getByPlaceholderText(/••/i)).toBeInTheDocument();
  });

  it('shows register link', () => {
    renderWithRouter(<Login />);
    expect(screen.getByText(/don't have an account/i)).toBeInTheDocument();
  });
});