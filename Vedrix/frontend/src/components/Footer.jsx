import { Link } from 'react-router-dom';

const Footer = () => {
  return (
    <footer className="py-12 border-t border-white/5 text-center bg-[#0a0f1e]">
      <div className="text-2xl font-black text-white mb-4 tracking-tighter">Vedrix</div>
      <p className="text-slate-500 font-bold uppercase tracking-widest text-[10px] mb-6">
        © 2026 Vedrix. Interview operations and evaluation workflows.
      </p>
      <div className="flex justify-center space-x-6 text-xs text-slate-500">
        <Link to="/privacy" className="hover:text-purple-400 transition-colors">
          Privacy Policy
        </Link>
        <Link to="/terms" className="hover:text-purple-400 transition-colors">
          Terms of Service
        </Link>
        <Link to="/dpa" className="hover:text-purple-400 transition-colors">
          Data Processing
        </Link>
        <Link to="/accessibility" className="hover:text-purple-400 transition-colors">
          Accessibility
        </Link>
      </div>
    </footer>
  );
};

export default Footer;
