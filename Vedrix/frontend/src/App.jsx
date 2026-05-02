import React, { useState, useEffect } from 'react';
import { 
  ShieldCheck, 
  Cpu, 
  UserCheck, 
  Zap, 
  ChevronRight, 
  Menu, 
  X,
  LogOut
} from 'lucide-react';
import Login from './pages/Login';
import Register from './pages/Register';
import useAuthStore from './store/useAuthStore';

const Navbar = ({ onShowLogin, onShowRegister }) => {
  const [isOpen, setIsOpen] = useState(false);
  const { isAuthenticated, user, logout } = useAuthStore();

  return (
    <nav className="bg-white/80 backdrop-blur-md sticky top-0 z-50 border-b border-gray-100">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16 items-center">
          <div className="flex items-center">
            <div className="text-2xl font-bold bg-gradient-to-r from-purple-600 to-indigo-600 bg-clip-text text-transparent cursor-pointer" onClick={() => window.location.reload()}>
              Vedrix
            </div>
          </div>
          
          <div className="hidden md:block">
            <div className="ml-10 flex items-baseline space-x-8 text-sm font-medium text-gray-600">
              <a href="#" className="hover:text-purple-600 transition-colors">How it Works</a>
              <a href="#" className="hover:text-purple-600 transition-colors">Features</a>
              <a href="#" className="hover:text-purple-600 transition-colors">Pricing</a>
            </div>
          </div>

          <div className="hidden md:flex items-center space-x-4">
            {isAuthenticated ? (
              <div className="flex items-center space-x-4">
                <span className="text-sm font-medium text-gray-700 italic">Hi, {user?.first_name || 'User'}</span>
                <button 
                  onClick={logout}
                  className="flex items-center space-x-1 text-sm font-medium text-red-500 hover:text-red-700 px-3 py-2"
                >
                  <LogOut size={16} />
                  <span>Logout</span>
                </button>
              </div>
            ) : (
              <>
                <button 
                  onClick={onShowLogin}
                  className="text-sm font-medium text-gray-700 hover:text-purple-600 transition-colors px-4 py-2"
                >
                  Login
                </button>
                <button 
                  onClick={onShowRegister}
                  className="bg-purple-600 text-white text-sm font-medium px-5 py-2.5 rounded-full hover:bg-purple-700 transition-all shadow-md hover:shadow-lg active:scale-95"
                >
                  Sign Up Free
                </button>
              </>
            )}
          </div>

          <div className="md:hidden">
            <button onClick={() => setIsOpen(!isOpen)} className="text-gray-500 hover:text-purple-600">
              {isOpen ? <X size={24} /> : <Menu size={24} />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile menu */}
      {isOpen && (
        <div className="md:hidden bg-white border-b border-gray-100 p-4 space-y-4 shadow-xl">
          <a href="#" className="block text-base font-medium text-gray-700">How it Works</a>
          <a href="#" className="block text-base font-medium text-gray-700">Features</a>
          {isAuthenticated ? (
            <button onClick={logout} className="w-full text-left py-2 text-red-500 font-medium">Logout</button>
          ) : (
            <>
              <button onClick={onShowLogin} className="w-full text-center py-2 text-gray-700 border border-gray-200 rounded-lg">Login</button>
              <button onClick={onShowRegister} className="w-full text-center py-2 bg-purple-600 text-white rounded-lg">Sign Up Free</button>
            </>
          )}
        </div>
      )}
    </nav>
  );
};

const FeatureCard = ({ icon: Icon, title, description }) => (
  <div className="p-8 bg-white rounded-2xl border border-gray-100 shadow-sm hover:shadow-xl transition-all group hover:-translate-y-1">
    <div className="w-12 h-12 bg-purple-50 rounded-xl flex items-center justify-center text-purple-600 mb-6 group-hover:bg-purple-600 group-hover:text-white transition-colors">
      <Icon size={24} />
    </div>
    <h3 className="text-xl font-bold text-gray-900 mb-3">{title}</h3>
    <p className="text-gray-600 leading-relaxed">{description}</p>
  </div>
);

function App() {
  const [view, setView] = useState('landing'); // 'landing', 'login', 'register'
  const { checkAuth, isAuthenticated } = useAuthStore();

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  // If authenticated and was on login/register, go to landing (or later dashboard)
  useEffect(() => {
    if (isAuthenticated && (view === 'login' || view === 'register')) {
      setView('landing');
    }
  }, [isAuthenticated, view]);

  return (
    <div className="min-h-screen bg-white text-gray-900">
      <Navbar 
        onShowLogin={() => setView('login')} 
        onShowRegister={() => setView('register')} 
      />
      
      <main className="max-w-7xl mx-auto">
        {view === 'landing' ? (
          <>
            {/* Hero Section */}
            <section className="relative pt-20 pb-32 overflow-hidden">
              <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-7xl h-full -z-10">
                <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-purple-200/20 blur-[120px] rounded-full" />
                <div className="absolute bottom-0 left-0 w-[500px] h-[500px] bg-indigo-200/20 blur-[120px] rounded-full" />
              </div>

              <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
                <div className="inline-flex items-center space-x-2 bg-purple-50 text-purple-700 px-4 py-2 rounded-full text-sm font-semibold mb-8 border border-purple-100">
                  <Zap size={16} />
                  <span>Next-Gen Adaptive AI Interviewing</span>
                </div>
                
                <h1 className="text-6xl md:text-7xl font-extrabold tracking-tight text-gray-900 mb-6 leading-tight">
                  Master Your Next Job with <br />
                  <span className="bg-gradient-to-r from-purple-600 via-indigo-600 to-purple-600 bg-[length:200%_auto] animate-gradient bg-clip-text text-transparent">
                    Vedrix Intelligence
                  </span>
                </h1>
                
                <p className="max-w-2xl mx-auto text-xl text-gray-600 mb-10 leading-relaxed">
                  The only adaptive interview platform that thinks like a senior engineer. 
                  Personalized technical rounds powered by Groq & NVIDIA's 405B models.
                </p>

                <div className="flex flex-col sm:flex-row items-center justify-center space-y-4 sm:space-y-0 sm:space-x-6">
                  <button 
                    onClick={() => setView('register')}
                    className="w-full sm:w-auto bg-purple-600 text-white px-8 py-4 rounded-full font-bold text-lg hover:bg-purple-700 shadow-xl shadow-purple-500/20 flex items-center justify-center group transition-all"
                  >
                    Start Free Interview
                    <ChevronRight className="ml-2 group-hover:translate-x-1 transition-transform" />
                  </button>
                  <button className="w-full sm:w-auto bg-white text-gray-900 border-2 border-gray-100 px-8 py-4 rounded-full font-bold text-lg hover:bg-gray-50 transition-all">
                    Request HR Demo
                  </button>
                </div>

                <div className="mt-20 pt-10 border-t border-gray-100">
                  <p className="text-sm font-semibold text-gray-400 uppercase tracking-widest mb-8">Trusted by candidates from</p>
                  <div className="flex flex-wrap justify-center gap-12 opacity-40 grayscale pointer-events-none">
                     <span className="text-2xl font-bold">Google</span>
                     <span className="text-2xl font-bold">Meta</span>
                     <span className="text-2xl font-bold">Amazon</span>
                     <span className="text-2xl font-bold">Netflix</span>
                  </div>
                </div>
              </div>
            </section>

            {/* Features Section */}
            <section className="py-24 bg-gray-50/50 border-y border-gray-100">
              <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="text-center max-w-3xl mx-auto mb-20">
                  <h2 className="text-4xl font-bold mb-6">Built for Scaling Talent</h2>
                  <p className="text-lg text-gray-600">
                    We've combined the latest in Large Language Models with a stateful adaptive engine 
                    to provide an interview experience that is indistinguishable from a human expert.
                  </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                  <FeatureCard 
                    icon={Cpu}
                    title="Stateful Adaptive Graph"
                    description="Powered by LangGraph, our engine remembers your strengths and pivots difficulty in real-time based on your depth of answer."
                  />
                  <FeatureCard 
                    icon={ShieldCheck}
                    title="Bias-Free Screening"
                    description="Eliminate human bias in the first round. Our AI evaluates technical accuracy and behavioral logic with clinical precision."
                  />
                  <FeatureCard 
                    icon={UserCheck}
                    title="Expert Feedback"
                    description="Get detailed radar charts and improvement plans. Know exactly where you stand against industry benchmarks."
                  />
                </div>
              </div>
            </section>
          </>
        ) : (
          <div className="pt-20 pb-32">
            {view === 'login' ? (
              <Login 
                onToggleMode={() => setView('register')} 
                onSuccess={() => setView('landing')} 
              />
            ) : (
              <Register 
                onToggleMode={() => setView('login')} 
                onSuccess={() => setView('login')} 
              />
            )}
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="bg-white py-12 border-t border-gray-100 text-center">
        <div className="text-2xl font-bold text-purple-600 mb-4">Vedrix</div>
        <p className="text-gray-500 text-sm">© 2026 Vedrix AI System. All rights reserved.</p>
      </footer>
    </div>
  );
}

export default App;
