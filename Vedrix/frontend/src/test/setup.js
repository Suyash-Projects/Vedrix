/* eslint-disable no-unused-vars, no-undef */
import React from 'react';
import '@testing-library/jest-dom';
import { expect, afterEach, vi } from 'vitest';
import { cleanup } from '@testing-library/react';
import * as matchers from '@testing-library/jest-dom/matchers';

expect.extend(matchers);

afterEach(() => {
  cleanup();
});

// Mock IntersectionObserver for Framer Motion / JSDOM compatibility
class MockIntersectionObserver {
  constructor(callback, options) {
    this.callback = callback;
    this.options = options;
  }
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
}

Object.defineProperty(window, 'IntersectionObserver', {
  writable: true,
  configurable: true,
  value: MockIntersectionObserver,
});

Object.defineProperty(global, 'IntersectionObserver', {
  writable: true,
  configurable: true,
  value: MockIntersectionObserver,
});

// Mock framer-motion globally to render immediately without animations/delays
vi.mock('framer-motion', async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    motion: new Proxy(
      {},
      {
        get: (target, key) => {
          return React.forwardRef(({ children, whileHover, whileTap, animate, initial, exit, transition, ...props }, ref) => {
            return React.createElement(key, { ...props, ref }, children);
          });
        },
      }
    ),
    AnimatePresence: ({ children }) => children,
  };
});
