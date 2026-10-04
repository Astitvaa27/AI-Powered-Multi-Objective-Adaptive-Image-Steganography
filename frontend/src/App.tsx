import type { ReactNode } from "react";
import { Navigate, Route, Routes, useParams } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { AnalysisReportPage } from "@/pages/AnalysisReport";
import { AnalyzePage } from "@/pages/Analyze";
import { DashboardPage } from "@/pages/Dashboard";
import { ExtractPage } from "@/pages/Extract";
import { ForgotPasswordPage } from "@/pages/ForgotPassword";
import { HidePage } from "@/pages/Hide";
import { HideRunDetailPage } from "@/pages/HideRunDetail";
import { HistoryPage } from "@/pages/History";
import { LoginPage } from "@/pages/Login";
import { ResetPasswordPage } from "@/pages/ResetPassword";
import { SettingsPage } from "@/pages/Settings";
import { SignupPage } from "@/pages/Signup";
import { VerifyOtpPage } from "@/pages/VerifyOtp";

function RequireAuth({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useAuth();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

/** Keeps old /reports/:sessionId links working. */
function LegacyReportRedirect() {
  const { sessionId } = useParams<{ sessionId: string }>();
  return <Navigate to={`/history/analyses/${sessionId ?? ""}`} replace />;
}

const PROTECTED: { path: string; element: ReactNode }[] = [
  { path: "/", element: <DashboardPage /> },
  { path: "/hide", element: <HidePage /> },
  { path: "/extract", element: <ExtractPage /> },
  { path: "/analyze", element: <AnalyzePage /> },
  { path: "/history", element: <HistoryPage /> },
  { path: "/history/analyses/:sessionId", element: <AnalysisReportPage /> },
  { path: "/history/hides/:runId", element: <HideRunDetailPage /> },
  { path: "/settings", element: <SettingsPage /> },
];

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/signup" element={<SignupPage />} />
      <Route path="/verify-otp" element={<VerifyOtpPage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      {/* Path used by the password reset email; keep in sync with the backend. */}
      <Route path="/reset-password" element={<ResetPasswordPage />} />

      {PROTECTED.map(({ path, element }) => (
        <Route key={path} path={path} element={<RequireAuth>{element}</RequireAuth>} />
      ))}

      {/* Previous URLs */}
      <Route path="/steganography" element={<Navigate to="/hide" replace />} />
      <Route path="/steganalysis" element={<Navigate to="/analyze" replace />} />
      <Route path="/reports" element={<Navigate to="/history?tab=analyses" replace />} />
      <Route path="/reports/:sessionId" element={<LegacyReportRedirect />} />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
