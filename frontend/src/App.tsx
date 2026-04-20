import { Routes, Route, Navigate } from "react-router-dom";
import { lazy, Suspense } from "react";
import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";

// Public pages
const Home = lazy(() => import("./pages/Home"));
const Login = lazy(() => import("./pages/Login"));
const Register = lazy(() => import("./pages/Register"));

// Protected pages
const Dashboard = lazy(() => import("./pages/Dashboard"));
const Rates = lazy(() => import("./pages/Rates"));
const Charts = lazy(() => import("./pages/Charts"));
const Portfolio = lazy(() => import("./pages/Portfolio"));
const Options = lazy(() => import("./pages/Options"));
const Carry = lazy(() => import("./pages/Carry"));
const Calculator = lazy(() => import("./pages/Calculator"));
const Alerts = lazy(() => import("./pages/Alerts"));
const History = lazy(() => import("./pages/History"));
const Profile = lazy(() => import("./pages/Profile"));

function PageLoader() {
  return (
    <div className="flex items-center justify-center h-full min-h-[60vh]">
      <div className="flex flex-col items-center gap-3">
        <div className="w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
        <span className="text-sm text-slate-500 font-mono tracking-wider">
          LOADING
        </span>
      </div>
    </div>
  );
}

const S = (C: React.ComponentType) => (
  <Suspense fallback={<PageLoader />}>
    <C />
  </Suspense>
);

// NOTE: BrowserRouter + AuthProvider are in main.tsx — never nest them here.
export default function App() {
  return (
    <Routes>
      {/* ── Public routes ── */}
      <Route path="/" element={S(Home)} />
      <Route path="/login" element={S(Login)} />
      <Route path="/register" element={S(Register)} />

      {/* ── Protected routes (require login) ── */}
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route path="dashboard" element={S(Dashboard)} />
        <Route path="rates" element={S(Rates)} />
        <Route path="charts" element={S(Charts)} />
        <Route path="portfolio" element={S(Portfolio)} />
        <Route path="options" element={S(Options)} />
        <Route path="carry" element={S(Carry)} />
        <Route path="calculator" element={S(Calculator)} />
        <Route path="alerts" element={S(Alerts)} />
        <Route path="history" element={S(History)} />
        <Route path="profile" element={S(Profile)} />
      </Route>

      {/* ── Fallback ── */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
