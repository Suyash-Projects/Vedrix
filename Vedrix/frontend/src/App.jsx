import { useEffect } from 'react';
import { Routes, Route, Navigate, useLocation } from 'react-router-dom';

import Login from './pages/Login';
import Register from './pages/Register';
import InterviewRoom from './pages/InterviewRoom';
import AdminDashboard from './pages/AdminDashboard';
import HRDashboard from './pages/HRDashboard';
import StudentDashboard from './pages/StudentDashboard';
import InterviewReport from './pages/InterviewReport';
import InterviewReplay from './pages/InterviewReplay';
import SkillGapAnalysis from './pages/SkillGapAnalysis';
import TeamAnalytics from './pages/TeamAnalytics';
import CertificateVerification from './pages/CertificateVerification';
import SystemHealth from './pages/SystemHealth';
import AuditLogs from './pages/AuditLogs';
import SystemConfig from './pages/SystemConfig';
import CandidatePipeline from './pages/CandidatePipeline';
import FeedbackSurvey from './pages/FeedbackSurvey';
import HRFeedback from './pages/HRFeedback';
import Schedule from './pages/Schedule';
import PrivacyPolicy from './pages/PrivacyPolicy';
import TermsOfService from './pages/TermsOfService';
import DataProcessingAgreement from './pages/DataProcessingAgreement';
import AccessibilityStatement from './pages/AccessibilityStatement';
import SettingsPage from './pages/SettingsPage';
import LandingPage from './pages/LandingPage';
import SupervisorDashboard from './pages/SupervisorDashboard';
import Navbar from './components/Navbar';
import Footer from './components/Footer';
import CookieConsent from './components/CookieConsent';
import ProtectedRoute from './components/ProtectedRoute';
import useAuthStore from './store/useAuthStore';

function App() {
  const { checkAuth, isAuthenticated, user } = useAuthStore();
  const location = useLocation();

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  // Helper to get dashboard path based on user type
  const getDashboardPath = (user) => {
    if (user?.user_type === 'admin') return '/admin';
    if (user?.user_type === 'hr') return '/hr';
    return '/dashboard'; // student default
  };

  // Determine if we should show the navbar/footer
  const isInterviewRoom = location.pathname === '/interview';
  const isReport = location.pathname.startsWith('/report');
  const isVerify = location.pathname.startsWith('/verify');
  const isReplay = location.pathname.startsWith('/replay');
  const isSkillGap = location.pathname.startsWith('/skill-gap');
  const isTeamAnalytics = location.pathname.startsWith('/analytics/team');
  const isLegalPage = ['/privacy', '/terms', '/dpa', '/accessibility'].includes(location.pathname);
  const showNavbar = !isInterviewRoom && !isReport && !isVerify && !isReplay && !isSkillGap && !isTeamAnalytics && !isLegalPage;
  const showFooter = !isInterviewRoom && !isReport && !isVerify;

  return (
    <div className="min-h-screen bg-[#020617] text-white">
      {/* Skip to main content link for accessibility */}
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>

      {showNavbar && <Navbar />}

      <main id="main-content" className={showNavbar ? 'pt-20' : 'pt-0'}>
        <Routes>
          {/* Public Routes */}
          <Route path="/home" element={<LandingPage />} />
          <Route path="/" element={
            isAuthenticated ? <Navigate to={getDashboardPath(user)} replace /> : <LandingPage />
          } />
          
          <Route path="/login" element={
            <div className="min-h-screen flex items-center justify-center px-4 py-16">
              <Login />
            </div>
          } />
          <Route path="/register" element={
            <div className="min-h-screen flex items-center justify-center px-4 py-16">
              <Register />
            </div>
          } />
          
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

          {/* Protected Replay Route */}
          <Route path="/replay/:sessionId" element={
            <ProtectedRoute>
              <InterviewReplay />
            </ProtectedRoute>
          } />

          {/* Protected Skill Gap Analysis Route */}
          <Route path="/skill-gap/:sessionId" element={
            <ProtectedRoute>
              <SkillGapAnalysis />
            </ProtectedRoute>
          } />

          {/* Protected Team Analytics Route (Admin only) */}
          <Route path="/analytics/team" element={
            <ProtectedRoute allowedRoles={['admin']}>
              <TeamAnalytics />
            </ProtectedRoute>
          } />

          {/* Public Certificate Verification Route */}
          <Route path="/verify/:token" element={<CertificateVerification />} />

          {/* Protected System Health Route (Admin only) */}
          <Route path="/admin/health" element={
            <ProtectedRoute allowedRoles={['admin']}>
              <SystemHealth />
            </ProtectedRoute>
          } />

          {/* Protected Audit Logs Route (Admin only) */}
          <Route path="/admin/audit-logs" element={
            <ProtectedRoute allowedRoles={['admin']}>
              <AuditLogs />
            </ProtectedRoute>
          } />

          {/* Protected System Config Route (Admin only) */}
          <Route path="/admin/config" element={
            <ProtectedRoute allowedRoles={['admin']}>
              <SystemConfig />
            </ProtectedRoute>
          } />

          {/* Protected AI Supervisor Route (Admin only) */}
          <Route path="/admin/supervisor" element={
            <ProtectedRoute allowedRoles={['admin']}>
              <SupervisorDashboard />
            </ProtectedRoute>
          } />

          {/* Protected Candidate Pipeline Route (HR/Admin) */}
          <Route path="/hr/pipeline" element={
            <ProtectedRoute allowedRoles={['hr', 'admin']}>
              <CandidatePipeline />
            </ProtectedRoute>
          } />

          {/* Public Feedback Survey Route */}
          <Route path="/feedback/survey" element={<FeedbackSurvey />} />

          {/* Protected HR Feedback Route */}
          <Route path="/hr/feedback/:sessionId" element={
            <ProtectedRoute allowedRoles={['hr', 'admin']}>
              <HRFeedback />
            </ProtectedRoute>
          } />

          {/* Protected Schedule Route (HR/Admin) */}
          <Route path="/hr/schedule" element={
            <ProtectedRoute allowedRoles={['hr', 'admin']}>
              <Schedule />
            </ProtectedRoute>
          } />

          {/* Protected Settings Route */}
          <Route path="/settings" element={
            <ProtectedRoute>
              <SettingsPage />
            </ProtectedRoute>
          } />

          {/* Public Legal Pages */}
          <Route path="/privacy" element={<PrivacyPolicy />} />
          <Route path="/terms" element={<TermsOfService />} />
          <Route path="/dpa" element={<DataProcessingAgreement />} />
          <Route path="/accessibility" element={<AccessibilityStatement />} />

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>

      {showFooter && <Footer />}
      <CookieConsent />
    </div>
  );
}

export default App;
