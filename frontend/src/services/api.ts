/**
 * AlphaFX API Service
 * Typed Axios client covering all Django REST endpoints + WebSocket factory.
 */
import axios from "axios";

const BASE_URL =
  (import.meta as any).env?.VITE_API_URL || "http://localhost:8000";
const API_V1 = `${BASE_URL}/api/v1`;
const WS_BASE = BASE_URL.replace(/^http/, "ws");

export const api = axios.create({
  baseURL: API_V1,
  headers: { "Content-Type": "application/json" },
  timeout: 15_000,
});

export const ratesApi = {
  getMajorPairs: () => api.get("/rates/"),
  getAllPairs: () => api.get("/rates/all-pairs/"),
  getSpotRate: (pair: string) => api.get(`/rates/spot/${pair}/`),
  batchSpot: (pairs: string[]) => api.post("/rates/spot/", { pairs }),
  getForwardRate: (req: any) => api.post("/rates/forward/", req),
  getCrossRate: (req: any) => api.post("/rates/cross/", req),
  priceOption: (req: any) => api.post("/rates/option/", req),
  getVolSurface: (pair: string) =>
    api.get(`/rates/option/vol-surface/${pair}/`),
  getRiskReversal: (pair: string) =>
    api.get(`/rates/option/risk-reversal/${pair}/`),
  getCarry: (minBps = 0) => api.get(`/rates/carry/?min_carry_bps=${minBps}`),
  getInterestRates: () => api.get("/rates/interest-rates/"),
  getCalendar: () => api.get("/rates/calendar/"),
  getPipValue: (pair: string, notional = 100_000) =>
    api.get(`/rates/pip-value/${pair}/?notional=${notional}`),
};

export const technicalApi = {
  analyze: (pair: string, n = 252) => api.get(`/technical/${pair}/?n=${n}`),
  scan: (n = 100) => api.get(`/technical/?n=${n}`),
  correlation: (pairs: string[], n = 60) =>
    api.get(`/technical/correlation/?pairs=${pairs.join(",")}&n=${n}`),
  supportResistance: (pair: string, n = 100) =>
    api.get(`/technical/${pair}/support-resistance/?n=${n}`),
  fibonacci: (pair: string, n = 100) =>
    api.get(`/technical/${pair}/fibonacci/?n=${n}`),
  volatility: (pair: string) => api.get(`/technical/${pair}/volatility/`),
};

export const portfolioApi = {
  list: () => api.get("/portfolios/"),
  create: (data: any) => api.post("/portfolios/", data),
  get: (id: string) => api.get(`/portfolios/${id}/`),
  update: (id: string, data: any) => api.patch(`/portfolios/${id}/`, data),
  delete: (id: string) => api.delete(`/portfolios/${id}/`),
  listPositions: (id: string) => api.get(`/portfolios/${id}/positions/`),
  openPosition: (id: string, data: any) =>
    api.post(`/portfolios/${id}/positions/`, data),
  closePosition: (pid: string, posId: string, rate?: number) =>
    api.delete(`/portfolios/${pid}/positions/${posId}/`, {
      data: rate ? { close_rate: rate } : {},
    }),
  getRisk: (id: string, confidence = 0.99) =>
    api.get(`/portfolios/${id}/risk/?confidence=${confidence}`),
  getScenarios: (id: string) => api.post(`/portfolios/${id}/scenarios/`),
  getHistory: (id: string) => api.get(`/portfolios/${id}/history/`),
  getPerformance: (id: string) => api.get(`/portfolios/${id}/performance/`),
};

export const analyticsApi = {
  positionSize: (data: any) => api.post("/analytics/position-size/", data),
  riskReward: (data: any) => api.post("/analytics/risk-reward/", data),
  pipValue: (pair: string, notional: number) =>
    api.post("/analytics/pip-value/", { pair, notional }),
  swapRates: () => api.get("/analytics/swap-rates/"),
  ppp: () => api.get("/analytics/purchasing-power-parity/"),
  fixingRates: () => api.get("/analytics/fixing-rates/"),
  sabrSmile: (data: any) => api.post("/analytics/sabr-smile/", data),
  strategyBuilder: (data: any) =>
    api.post("/analytics/strategy-builder/", data),
};

export const alertsApi = {
  list: () => api.get("/portfolios/alerts/"),
  create: (d: any) => api.post("/portfolios/alerts/", d),
  check: (id: string) => api.get(`/portfolios/alerts/${id}/`),
  delete: (id: string) => api.delete(`/portfolios/alerts/${id}/`),
};

export function createRateStream(
  pair = "all",
  onTick: (data: any) => void,
  onError?: (e: Event) => void,
): WebSocket {
  const ws = new WebSocket(`${WS_BASE}/ws/rates/${pair.toUpperCase()}/`);
  ws.onmessage = (e) => {
    try {
      const d = JSON.parse(e.data);
      if (d.type === "tick") onTick(d);
    } catch {}
  };
  if (onError) ws.onerror = onError;
  return ws;
}
