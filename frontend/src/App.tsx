import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import Rates from "./pages/Rates";
import Charts from "./pages/Charts";
import Portfolio from "./pages/Portfolio";
import Options from "./pages/Options";
import Carry from "./pages/Carry";
import Calculator from "./pages/Calculator";
import Alerts from "./pages/Alerts";
import History from "./pages/History";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="rates" element={<Rates />} />
          <Route path="charts" element={<Charts />} />
          <Route path="portfolio" element={<Portfolio />} />
          <Route path="options" element={<Options />} />
          <Route path="carry" element={<Carry />} />
          <Route path="calculator" element={<Calculator />} />
          <Route path="alerts" element={<Alerts />} />
          <Route path="history" element={<History />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
