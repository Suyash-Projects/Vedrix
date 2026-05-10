import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import Register from '../../pages/Register';

vi.mock('../../services/api', () => ({
  default: {
    post: vi.fn().mockResolvedValue({ data: {} }),
  },
}));

const renderWithRouter = (component) => {
  return render(
    <BrowserRouter>
      {component}
    </BrowserRouter>
  );
};

describe('Register Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders registration form with create account title', () => {
    renderWithRouter(<Register />);
    expect(screen.getByText(/create account/i)).toBeInTheDocument();
  });

  it('has first name input', () => {
    renderWithRouter(<Register />);
    expect(screen.getByPlaceholderText('John')).toBeInTheDocument();
  });

  it('has last name input', () => {
    renderWithRouter(<Register />);
    expect(screen.getByPlaceholderText('Doe')).toBeInTheDocument();
  });

  it('has email input', () => {
    renderWithRouter(<Register />);
    expect(screen.getByPlaceholderText('john@example.com')).toBeInTheDocument();
  });

  it('has username input', () => {
    renderWithRouter(<Register />);
    expect(screen.getByPlaceholderText('johndoe')).toBeInTheDocument();
  });

  it('has password input', () => {
    renderWithRouter(<Register />);
    expect(screen.getByPlaceholderText('••••••••')).toBeInTheDocument();
  });

  it('shows user type selector', () => {
    renderWithRouter(<Register />);
    expect(screen.getByText(/i am a/i)).toBeInTheDocument();
  });

  it('has sign in link', () => {
    renderWithRouter(<Register />);
    expect(screen.getByText(/already have an account/i)).toBeInTheDocument();
  });
});