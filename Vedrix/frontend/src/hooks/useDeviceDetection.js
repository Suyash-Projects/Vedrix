import { useState, useEffect } from 'react';

/**
 * Hook to detect if the current device is mobile/tablet.
 * Uses screen width and user agent detection.
 * 
 * @param {number} breakpoint - Width in px below which to consider mobile (default: 1024)
 * @returns {boolean} - True if device is mobile/tablet
 */
export function useIsMobile(breakpoint = 1024) {
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const check = () => {
      const width = window.innerWidth;
      // Check screen width
      const widthCheck = width < breakpoint;
      // Also check user agent for common mobile/tablet patterns
      const uaCheck = /Android|iPhone|iPad|iPod|webOS|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
      
      setIsMobile(widthCheck || uaCheck);
    };

    check();
    window.addEventListener('resize', check);
    return () => window.removeEventListener('resize', check);
  }, [breakpoint]);

  return isMobile;
}

/**
 * Hook to detect if the current device is a tablet specifically.
 * 
 * @returns {boolean} - True if device is tablet
 */
export function useIsTablet() {
  const [isTablet, setIsTablet] = useState(false);

  useEffect(() => {
    const check = () => {
      const width = window.innerWidth;
      const ua = navigator.userAgent;
      // Tablets typically have width between 768 and 1024
      const isTabletWidth = width >= 768 && width < 1024;
      const isTabletUA = /iPad|Android(?!.*Mobile)/i.test(ua);
      
      setIsTablet(isTabletWidth || isTabletUA);
    };

    check();
    window.addEventListener('resize', check);
    return () => window.removeEventListener('resize', check);
  }, []);

  return isTablet;
}
