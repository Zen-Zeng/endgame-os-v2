/**
 * Endgame OS - 主应用入口
 */
import { useEffect } from 'react';
import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { useAuthStore } from './stores/useAuthStore';
import { useOnboardingStore } from './stores/useOnboardingStore';

// 布局
import MainLayout from './components/layout/MainLayout';

// 页面
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import ChatPage from './pages/ChatPage';
import CalibrationPage from './pages/CalibrationPage';
import ArchivesPage from './pages/ArchivesPage';
import MemoryPage from './pages/MemoryPage';
import MorningWakePage from './pages/MorningWakePage';
import SettingsPage from './pages/SettingsPage';

// 引导页面
import PersonaSetupPage from './pages/onboarding/PersonaSetupPage';
import H3OnboardingPage from './pages/onboarding/H3OnboardingPage';

// 受保护路由组件
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { token, isLoading } = useAuthStore();
  const { isOnboardingComplete } = useOnboardingStore();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--color-bg-dark)]">
        <div className="text-center">
          <div className="w-12 h-12 rounded-xl bg-[var(--color-primary)] flex items-center justify-center mx-auto mb-4 animate-pulse">
            <span className="text-white font-bold text-xl">E</span>
          </div>
          <p className="text-[var(--color-text-secondary)]">加载中...</p>
        </div>
      </div>
    );
  }

  if (!token) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // 如果未完成引导，重定向到引导流程
  if (!isOnboardingComplete && !location.pathname.startsWith('/onboarding')) {
    return <Navigate to="/onboarding/persona" replace />;
  }

  return <>{children}</>;
}

// 引导路由组件（已登录但未完成引导）
function OnboardingRoute({ children }: { children: React.ReactNode }) {
  const { token, isLoading } = useAuthStore();
  const { isOnboardingComplete } = useOnboardingStore();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--color-bg-dark)]">
        <div className="text-center">
          <div className="w-12 h-12 rounded-xl bg-[var(--color-primary)] flex items-center justify-center mx-auto mb-4 animate-pulse">
            <span className="text-white font-bold text-xl">E</span>
          </div>
          <p className="text-[var(--color-text-secondary)]">加载中...</p>
        </div>
      </div>
    );
  }

  if (!token) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // 如果已完成引导，重定向到主页
  if (isOnboardingComplete) {
    return <Navigate to="/dashboard" replace />;
  }

  return <>{children}</>;
}

// 公开路由组件（已登录则跳转）
function PublicRoute({ children }: { children: React.ReactNode }) {
  const { token } = useAuthStore();
  const { isOnboardingComplete } = useOnboardingStore();
  const location = useLocation();

  if (token) {
    // 如果已登录但未完成引导，跳转到引导流程
    if (!isOnboardingComplete) {
      return <Navigate to="/onboarding/persona" replace />;
    }
    const from = (location.state as { from?: Location })?.from?.pathname || '/dashboard';
    return <Navigate to={from} replace />;
  }

  return <>{children}</>;
}

export default function App() {
  const { checkAuth } = useAuthStore();

  // 应用启动时检查认证状态
  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  return (
    <Routes>
      {/* 公开路由 */}
      <Route
        path="/login"
        element={
          <PublicRoute>
            <LoginPage />
          </PublicRoute>
        }
      />

      {/* 引导流程路由 */}
      <Route
        path="/onboarding/persona"
        element={
          <OnboardingRoute>
            <PersonaSetupPage />
          </OnboardingRoute>
        }
      />
      <Route
        path="/onboarding/h3"
        element={
          <OnboardingRoute>
            <H3OnboardingPage />
          </OnboardingRoute>
        }
      />

      {/* 受保护路由 */}
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <MainLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="morning" element={<MorningWakePage />} />
        <Route path="chat" element={<ChatPage />} />
        <Route path="calibration" element={<CalibrationPage />} />
        <Route path="archives" element={<ArchivesPage />} />
        <Route path="memory" element={<MemoryPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>

      {/* 404 重定向 */}
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

