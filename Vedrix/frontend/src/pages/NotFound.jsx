import { useNavigate, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Home, ArrowLeft, Cpu, Sparkles, Compass, Orbit } from 'lucide-react';
import AnimatedBackground from '../components/AnimatedBackground';

const sparkles = Array.from({ length: 12 }, (_, i) => ({
  id: i,
  x: `${10 + Math.random() * 80}%`,
  y: `${10 + Math.random() * 80}%`,
  yAnimate: [`${10 + Math.random() * 80}%`, `${5 + Math.random() * 80}%`],
  duration: 4 + Math.random() * 4,
  delay: Math.random() * 3,
  size: 10 + Math.random() * 10,
}));

const NotFound = () => {
  const navigate = useNavigate();

  return (
    <div className="relative min-h-[calc(100vh-5rem)] flex items-center justify-center overflow-hidden px-4 py-16">
      <AnimatedBackground variant="auth" />

      {/* Floating sparkles */}
      {sparkles.map((sparkle) => (
        <motion.div
          key={sparkle.id}
          className="absolute pointer-events-none text-purple-400/40"
          initial={{
            x: sparkle.x,
            y: sparkle.y,
            opacity: 0,
          }}
          animate={{
            y: sparkle.yAnimate,
            opacity: [0, 0.8, 0],
          }}
          transition={{
            duration: sparkle.duration,
            repeat: Infinity,
            delay: sparkle.delay,
          }}
          aria-hidden="true"
        >
          <Sparkles size={sparkle.size} />
        </motion.div>
      ))}

      <div className="relative z-10 text-center max-w-2xl mx-auto">
        {/* Animated illustration: orbiting icons */}
        <motion.div
          initial={{ scale: 0, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ type: 'spring', damping: 18, stiffness: 200 }}
          className="relative w-40 h-40 mx-auto mb-8"
          aria-hidden="true"
        >
          {/* Orbit ring */}
          <motion.div
            className="absolute inset-0 rounded-full border border-purple-500/20"
            animate={{ rotate: 360 }}
            transition={{ duration: 18, repeat: Infinity, ease: 'linear' }}
          >
            <div className="absolute -top-1.5 left-1/2 -translate-x-1/2 w-3 h-3 rounded-full bg-purple-500 shadow-[0_0_18px_rgba(124,58,237,0.8)]" />
          </motion.div>
          <motion.div
            className="absolute inset-2 rounded-full border border-indigo-500/15"
            animate={{ rotate: -360 }}
            transition={{ duration: 12, repeat: Infinity, ease: 'linear' }}
          >
            <div className="absolute top-1/2 -right-1.5 -translate-y-1/2 w-2.5 h-2.5 rounded-full bg-indigo-400 shadow-[0_0_14px_rgba(129,140,248,0.7)]" />
          </motion.div>
          <motion.div
            className="absolute inset-5 rounded-full border border-fuchsia-500/10"
            animate={{ rotate: 360 }}
            transition={{ duration: 9, repeat: Infinity, ease: 'linear' }}
          >
            <div className="absolute -bottom-1 left-1/2 -translate-x-1/2 w-2 h-2 rounded-full bg-fuchsia-400 shadow-[0_0_10px_rgba(232,121,249,0.7)]" />
          </motion.div>

          {/* Center logo */}
          <motion.div
            animate={{ scale: [1, 1.05, 1] }}
            transition={{ duration: 2.4, repeat: Infinity, ease: 'easeInOut' }}
            className="absolute inset-0 m-auto w-20 h-20 rounded-2xl bg-gradient-to-br from-purple-600 to-indigo-500 flex items-center justify-center shadow-2xl shadow-purple-900/50"
          >
            <Cpu className="text-white" size={32} />
          </motion.div>
        </motion.div>

        {/* 404 huge text */}
        <motion.h1
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.15 }}
          className="text-[120px] sm:text-[180px] font-black tracking-tighter leading-none gradient-text glitch-text select-none"
          aria-label="404"
        >
          404
        </motion.h1>

        <motion.div
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.25 }}
        >
          <p className="text-2xl sm:text-3xl font-black text-white tracking-tight mb-3">
            Lost in the matrix
          </p>
          <p className="text-slate-400 text-sm sm:text-base max-w-md mx-auto leading-relaxed">
            The page you're looking for slipped through a wormhole. Let's get you
            back on a known orbit.
          </p>
        </motion.div>

        <motion.div
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.35 }}
          className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-3"
        >
          <Link
            to="/home"
            className="inline-flex items-center gap-2 bg-purple-600 text-white font-black uppercase tracking-widest text-xs px-7 py-3.5 rounded-xl hover:bg-purple-500 shadow-[0_0_40px_rgba(147,51,234,0.3)] transition-all active:scale-95"
          >
            <Home size={16} />
            Go Home
          </Link>
          <button
            type="button"
            onClick={() => navigate(-1)}
            className="inline-flex items-center gap-2 bg-white/5 border border-white/10 text-white font-black uppercase tracking-widest text-xs px-7 py-3.5 rounded-xl hover:bg-white/10 transition-all active:scale-95"
          >
            <ArrowLeft size={16} />
            Go Back
          </button>
        </motion.div>

        {/* Tiny help footer */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.6 }}
          className="mt-12 inline-flex items-center gap-2 text-[11px] font-bold uppercase tracking-widest text-slate-500"
        >
          <Compass size={12} />
          Tip — Press
          <span className="kbd-key">⌘</span>
          <span className="kbd-key">K</span>
          to navigate anywhere
          <Orbit size={12} />
        </motion.div>
      </div>
    </div>
  );
};

export default NotFound;
