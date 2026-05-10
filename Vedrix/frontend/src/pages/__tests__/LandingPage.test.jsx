import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { BrowserRouter } from 'react-router-dom';
import LandingPage from '../LandingPage';

describe('LandingPage', () => {
  it('renders the main heading', () => {
    render(
      <BrowserRouter>
        <LandingPage />
      </BrowserRouter>
    );

    expect(screen.getByText(/Smarter Interviews/i)).toBeInTheDocument();
    expect(screen.getByText(/Better Hires/i)).toBeInTheDocument();
  });

  it('contains the AI-Powered badge', () => {
    render(
      <BrowserRouter>
        <LandingPage />
      </BrowserRouter>
    );

    expect(screen.getByText(/AI-Powered Interview Platform/i)).toBeInTheDocument();
  });

  it('shows Get Started button', () => {
    render(
      <BrowserRouter>
        <LandingPage />
      </BrowserRouter>
    );

    expect(screen.getByText(/Get Started Free/i)).toBeInTheDocument();
  });

  it('shows Sign In link', () => {
    render(
      <BrowserRouter>
        <LandingPage />
      </BrowserRouter>
    );

    expect(screen.getAllByText(/Sign In/i).length).toBeGreaterThan(0);
  });
});