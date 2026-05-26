import { useEffect } from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import ProtectedRoute from '../components/ProtectedRoute.tsx';
import ScrollToTop from '../components/ScrollToTop.tsx';
import { useAppDispatch } from '../app/hooks.ts';
import { restoreSession } from '../features/auth/auth.thunks.ts';

import AuthPage from '../pages/AuthPage.tsx';
import HomePage from '../pages/HomePage';
import AnalysisPage from '../pages/analysis/AnalysisPage.tsx';
import AnalysisDetailPage from '../pages/analysis-detail/AnalysisPageDetail.tsx';
import AnalysisPlotsPage from '../pages/plots/PlotsPage.tsx';
import AnalysisReportsPage from '../pages/ReportsPage.tsx';
import SettingsPage from '../pages/SettingsPage.tsx';

function AppRouterContent() {
  const dispatch = useAppDispatch();

  useEffect(() => {
    void dispatch(restoreSession());
  }, [dispatch]);

  return (
    <Routes>
      <Route path="/auth" element={<AuthPage />} />

      <Route
        path="/"
        element={
          <ProtectedRoute>
            <HomePage />
          </ProtectedRoute>
        }
      />

      <Route
        path="/analysis"
        element={
          <ProtectedRoute>
            <AnalysisPage />
          </ProtectedRoute>
        }
      />

      <Route
        path="/analysis/:analysisId"
        element={
          <ProtectedRoute>
            <AnalysisDetailPage />
          </ProtectedRoute>
        }
      />

      <Route
        path="/analysis/:analysisId/plots"
        element={
          <ProtectedRoute>
            <AnalysisPlotsPage />
          </ProtectedRoute>
        }
      />

      <Route
        path="/analysis/:analysisId/reports"
        element={
          <ProtectedRoute>
            <AnalysisReportsPage />
          </ProtectedRoute>
        }
      />

      <Route
        path="/settings"
        element={
          <ProtectedRoute>
            <SettingsPage />
          </ProtectedRoute>
        }
      />

      <Route
        path="/optimization-progress"
        element={<Navigate to="/analysis" replace />}
      />
      <Route
        path="/optimization-progress/:analysisId"
        element={<Navigate to="/analysis" replace />}
      />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function AppRouter() {
  return (
    <BrowserRouter>
      <ScrollToTop />
      <AppRouterContent />
    </BrowserRouter>
  );
}
