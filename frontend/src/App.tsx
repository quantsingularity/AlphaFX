import { Routes, Route, Navigate } from "react-router-dom";
import { lazy, Suspense } from "react";
import Layout from "./components/Layout";

// Lazy-load every page so each becomes its own JS chunk
const Dashboard = lazy(() => import("./pages/Dashboard"));
const Rates = lazy(() => import("./pages/Rates"));
const Charts = lazy(() => import("./pages/Charts"));
const Portfolio = lazy(() => import("./pages/Portfolio"));
const Options = lazy(() => import("./pages/Options"));
const Carry = lazy(() => import("./pages/Carry"));
const Calculator = lazy(() => import("./pages/Calculator"));
const Alerts = lazy(() => import("./pages/Alerts"));
const History = lazy(() => import("./pages/History"));

function PageLoader() {
  return (
    <div className="flex items-center justify-center h-full min-h-[60vh]">
      <div className="flex flex-col items-center gap-3">
        <div className="w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
        <span className="text-sm text-slate-500">Loading…</span>
      </div>
    </div>
  );
}

// NOTE: BrowserRouter is provided in main.tsx — do NOT add another one here.
// A nested BrowserRouter creates an isolated routing context that breaks all
// route matching, which was the root cause of the blank-page bug.
export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route
          path="dashboard"
          element={
            <Suspense fallback={<PageLoader />}>
              <Dashboard />
            </Suspense>
          }
        />
        <Route
          path="rates"
          element={
            <Suspense fallback={<PageLoader />}>
              <Rates />
            </Suspense>
          }
        />
        <Route
          path="charts"
          element={
            <Suspense fallback={<PageLoader />}>
              <Charts />
            </Suspense>
          }
        />
        <Route
          path="portfolio"
          element={
            <Suspense fallback={<PageLoader />}>
              <Portfolio />
            </Suspense>
          }
        />
        <Route
          path="options"
          element={
            <Suspense fallback={<PageLoader />}>
              <Options />
            </Suspense>
          }
        />
        <Route
          path="carry"
          element={
            <Suspense fallback={<PageLoader />}>
              <Carry />
            </Suspense>
          }
        />
        <Route
          path="calculator"
          element={
            <Suspense fallback={<PageLoader />}>
              <Calculator />
            </Suspense>
          }
        />
        <Route
          path="alerts"
          element={
            <Suspense fallback={<PageLoader />}>
              <Alerts />
            </Suspense>
          }
        />
        <Route
          path="history"
          element={
            <Suspense fallback={<PageLoader />}>
              <History />
            </Suspense>
          }
        />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Route>
    </Routes>
  );
}
