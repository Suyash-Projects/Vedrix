import { useEffect } from 'react';
import { Routes, Route, Navigate, useLocation } from 'react-router-dom';

import Login from './pages/Login';
import LandingSections from './components/LandingSections';
import Register from './pages/Register';
import InterviewRoom from './pages/InterviewRoom';
import AdminDashboard from './pages/AdminDashboard';
import HRDashboard from './pages/HRDashboard';
import StudentDashboard from './pages/StudentDashboard';
import InterviewReport from './pages/InterviewReport';
import LandingPage from './pages/LandingPage';
import Navbar from './components/Navbar';
import ProtectedRoute from './components/ProtectedRoute';
import useAuthStore from './store/useAuthStore';

function App() {
  const { checkAuth, isAuthenticated, user } = useAuthStore();
  const location = useLocation();

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  // Determine if we should show the navbar/footer
  const isInterviewRoom = location.pathname === '/interview';
  const isReport = location.pathname.startsWith('/report');

  return (
    <div className="min-h-screen bg-[#020617] text-white pt-20">
      {!isInterviewRoom && !isReport && <Navbar />}

      <main className="pt-0">
        <Routes>
          {/* Public Routes */}
          <Route path="/" element={
            isAuthenticated ? (
              user?.user_type === 'hr' ? <Navigate to="/hr" replace /> :
              user?.user_type === 'admin' ? <Navigate to="/admin" replace /> :
              <Navigate to="/dashboard" replace />
            ) : <LandingPage />
          } />
          
          <Route path="/login" element={<Login onToggleMode={() => {}} onSuccess={() => {}} />} />
          <Route path="/register" element={<Register onToggleMode={() => {}} onSuccess={() => {}} />} />
          
          {/* Interview Room (Public-ish/Self-protected) */}
          <Route path="/interview" element={<InterviewRoom />} />

          {/* Protected Student Routes */}
          <Route path="/dashboard" element={
            <ProtectedRoute allowedRoles={['student']}>
              <StudentDashboard />
            </ProtectedRoute>
          } />

          {/* Protected HR Routes */}
          <Route path="/hr" element={
            <ProtectedRoute allowedRoles={['hr', 'admin']}>
              <HRDashboard />
            </ProtectedRoute>
          } />

          {/* Protected Admin Routes */}
          <Route path="/admin" element={
            <ProtectedRoute allowedRoles={['admin']}>
              <AdminDashboard />
            </ProtectedRoute>
          } />

          {/* Protected Report Route */}
          <Route path="/report/:sessionId" element={
            <ProtectedRoute>
              <InterviewReport />
            </ProtectedRoute>
          } />

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>

      {!isInterviewRoom && !isReport && (
        <footer className="py-12 border-t border-white/5 text-center bg-[#0a0f1e]">
          <div className="text-2xl font-black text-white mb-4 tracking-tighter">Vedrix</div>
          <p className="text-slate-500 font-bold uppercase tracking-widest text-[10px]">© 2026 Vedrix. Interview operations and evaluation workflows.</p>
        </footer>
      )}
    </div>
  );
}

export default App;
