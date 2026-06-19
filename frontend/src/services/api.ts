/**
 * AlphaFX API Service
 * Typed Axios client covering all Django REST endpoints + WebSocket factory.
 * All methods resolve to the response payload (response.data) directly.
 *
 * Dev:  set VITE_API_URL="" (or leave unset) so requests go through the Vite
 *       proxy which forwards /api/* and /ws/* to http://localhost:8000.
 * Prod: set VITE_API_URL="" so nginx routes /api/* to the backend container.
 *       Set VITE_API_URL="https://api.myhost.com" only when the API lives on
 *       a different origin.
 */
import axios from "axios";

// Empty string means same-origin: Vite proxy in dev, nginx in prod Docker.
const BASE_URL: string = (import.meta as any).env?.VITE_API_URL ?? "";
const API_V1 = `${BASE_URL}/api/v1`;
// WebSocket base: replace http(s) with ws(s), fall back to same host.
const WS_BASE = BASE_URL
  ? BASE_URL.replace(/^https?/, (p) => (p === "https" ? "wss" : "ws"))
  : "";

export const api = axios.create({
  baseURL: API_V1,
  headers: { "Content-Type": "application/json" },
  timeout: 15_000,
});

const d = <T>(p: Promise<{ data: T }>) => p.then((r) => r.data);

export interface FXOptionResult {
  option_type: string;
  price: number;
  price_pct: number;
  intrinsic_value: number;
  time_value: number;
  breakeven: number;
  volatility_pct: number;
  delta: number;
  gamma: number;
  vega: number;
  theta: number;
  rho: number;
}

export const ratesApi = {
  getMajorPairs: () => d(api.get("/rates/")),
  getAllPairs: () => d(api.get("/rates/all-pairs/")),
  getSpotRate: (pair: string) => d(api.get(`/rates/spot/${pair}/`)),
  batchSpot: (pairs: string[]) => d(api.post("/rates/spot/", { pairs })),
  getForwardRate: (req: any) => d(api.post("/rates/forward/", req)),
  getCrossRate: (req: any) => d(api.post("/rates/cross/", req)),
  priceOption: (req: any) => d<FXOptionResult>(api.post("/rates/option/", req)),
  getVolSurface: (pair: string) =>
    d(api.get(`/rates/option/vol-surface/${pair}/`)),
  getRiskReversal: (pair: string) =>
    d(api.get(`/rates/option/risk-reversal/${pair}/`)),
  getCarry: (minBps = 0) => d(api.get(`/rates/carry/?min_carry_bps=${minBps}`)),
  getInterestRates: () => d(api.get("/rates/interest-rates/")),
  getCalendar: () => d(api.get("/rates/calendar/")),
  getPipValue: (pair: string, notional = 100_000) =>
    d(api.get(`/rates/pip-value/${pair}/?notional=${notional}`)),
};

export const technicalApi = {
  analyze: (pair: string, n = 252) => d(api.get(`/technical/${pair}/?n=${n}`)),
  scan: (n = 100) => d(api.get(`/technical/?n=${n}`)),
  correlation: (pairs: string[], n = 60) =>
    d(api.get(`/technical/correlation/?pairs=${pairs.join(",")}&n=${n}`)),
  supportResistance: (pair: string, n = 100) =>
    d(api.get(`/technical/${pair}/support-resistance/?n=${n}`)),
  fibonacci: (pair: string, n = 100) =>
    d(api.get(`/technical/${pair}/fibonacci/?n=${n}`)),
  volatility: (pair: string) => d(api.get(`/technical/${pair}/volatility/`)),
};

export const portfolioApi = {
  list: () => d(api.get("/portfolios/")),
  create: (data: any) => d(api.post("/portfolios/", data)),
  get: (id: string) => d(api.get(`/portfolios/${id}/`)),
  update: (id: string, data: any) => d(api.patch(`/portfolios/${id}/`, data)),
  delete: (id: string) => d(api.delete(`/portfolios/${id}/`)),
  listPositions: (id: string) => d(api.get(`/portfolios/${id}/positions/`)),
  openPosition: (id: string, data: any) =>
    d(api.post(`/portfolios/${id}/positions/`, data)),
  closePosition: (pid: string, posId: string, rate?: number) =>
    d(
      api.delete(`/portfolios/${pid}/positions/${posId}/`, {
        data: rate ? { close_rate: rate } : {},
      }),
    ),
  getRisk: (id: string, confidence = 0.99) =>
    d(api.get(`/portfolios/${id}/risk/?confidence=${confidence}`)),
  getScenarios: (id: string) => d(api.post(`/portfolios/${id}/scenarios/`)),
  getHistory: (id: string) => d(api.get(`/portfolios/${id}/history/`)),
  getPerformance: (id: string) => d(api.get(`/portfolios/${id}/performance/`)),
};

export const analyticsApi = {
  positionSize: (data: any) => d(api.post("/analytics/position-size/", data)),
  riskReward: (data: any) => d(api.post("/analytics/risk-reward/", data)),
  pipValue: (pair: string, notional: number) =>
    d(api.post("/analytics/pip-value/", { pair, notional })),
  swapRates: () => d(api.get("/analytics/swap-rates/")),
  ppp: () => d(api.get("/analytics/purchasing-power-parity/")),
  fixingRates: () => d(api.get("/analytics/fixing-rates/")),
  sabrSmile: (data: any) => d(api.post("/analytics/sabr-smile/", data)),
  strategyBuilder: (data: any) =>
    d(api.post("/analytics/strategy-builder/", data)),
};

export const alertsApi = {
  list: () => d(api.get("/portfolios/alerts/")),
  create: (data: any) => d(api.post("/portfolios/alerts/", data)),
  check: (id: string) => d(api.get(`/portfolios/alerts/${id}/`)),
  delete: (id: string) => d(api.delete(`/portfolios/alerts/${id}/`)),
};

export function createRateStream(
  pair = "all",
  onTick: (data: any) => void,
  onError?: (e: Event) => void,
): WebSocket {
  // When WS_BASE is empty (same-origin), derive the WS URL from window.location.
  const wsOrigin =
    WS_BASE ||
    `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}`;
  const ws = new WebSocket(`${wsOrigin}/ws/rates/${pair.toUpperCase()}/`);
  ws.onmessage = (e) => {
    try {
      const d = JSON.parse(e.data);
      if (d.type === "tick") onTick(d);
    } catch {}
  };
  if (onError) ws.onerror = onError;
  return ws;
}
