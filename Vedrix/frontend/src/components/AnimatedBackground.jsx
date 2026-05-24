import { useEffect, useRef } from 'react';
import { motion } from 'framer-motion';

/**
 * Reusable animated background.
 * Features:
 *  - Grid pattern with mouse-tracking glow
 *  - Floating orbs that drift slowly
 *
 * Props:
 *  - variant: 'auth' | 'subtle' | 'hero'  (default 'subtle')
 *  - showGrid: boolean (default true)
 *  - showOrbs: boolean (default true)
 */
const AnimatedBackground = ({
  variant = 'subtle',
  showGrid = true,
  showOrbs = true,
  className = '',
}) => {
  const containerRef = useRef(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const handleMove = (e) => {
      const rect = el.getBoundingClientRect();
      const x = ((e.clientX - rect.left) / rect.width) * 100;
      const y = ((e.clientY - rect.top) / rect.height) * 100;
      el.style.setProperty('--mx', `${x}%`);
      el.style.setProperty('--my', `${y}%`);
    };
    el.addEventListener('mousemove', handleMove);
    return () => el.removeEventListener('mousemove', handleMove);
  }, []);

  const orbConfigs = {
    auth: [
      { class: 'orb orb-purple', size: 480, top: '-10%', left: '-10%', delay: 0 },
      { class: 'orb orb-indigo', size: 360, top: '60%', left: '70%', delay: 1.5 },
      { class: 'orb orb-pink', size: 280, top: '20%', left: '80%', delay: 3 },
      { class: 'orb orb-cyan', size: 320, top: '70%', left: '-5%', delay: 2 },
    ],
    subtle: [
      { class: 'orb orb-purple', size: 360, top: '-15%', left: '60%', delay: 0 },
      { class: 'orb orb-indigo', size: 280, top: '70%', left: '-5%', delay: 2 },
    ],
    hero: [
      { class: 'orb orb-purple', size: 520, top: '-20%', left: '-5%', delay: 0 },
      { class: 'orb orb-indigo', size: 420, top: '40%', left: '75%', delay: 1.5 },
      { class: 'orb orb-pink', size: 320, top: '70%', left: '30%', delay: 3 },
    ],
  };
  const orbs = orbConfigs[variant] || orbConfigs.subtle;

  return (
    <div
      ref={containerRef}
      className={`absolute inset-0 overflow-hidden pointer-events-none glow-cursor ${className}`}
      aria-hidden="true"
    >
      {/* Grid pattern with mouse-tracking glow (the ::before pseudo on .glow-cursor) */}
      {showGrid && (
        <div className="absolute inset-0 bg-grid-pattern opacity-60" />
      )}

      {/* Floating orbs */}
      {showOrbs &&
        orbs.map((orb, i) => (
          <motion.div
            key={i}
            className={orb.class}
            style={{
              width: `${orb.size}px`,
              height: `${orb.size}px`,
              top: orb.top,
              left: orb.left,
            }}
            animate={{
              x: [0, 40, -30, 0],
              y: [0, -30, 20, 0],
              scale: [1, 1.1, 0.95, 1],
            }}
            transition={{
              duration: 14 + i * 2,
              repeat: Infinity,
              ease: 'easeInOut',
              delay: orb.delay,
            }}
          />
        ))}

      {/* Vignette to blend into base */}
      <div className="absolute inset-0 bg-gradient-to-t from-[#020617] via-transparent to-transparent" />
    </div>
  );
};

export default AnimatedBackground;
