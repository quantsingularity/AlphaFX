# AlphaFX Frontend Guide

The frontend is a React 18 single-page application built with Vite,
TypeScript, and Tailwind CSS. It consumes the Django REST API and
opens WebSocket connections for live rate streaming.

---

## Technology Stack

| Technology   | Version | Purpose                                  |
| ------------ | ------- | ---------------------------------------- |
| React        | 18      | Component framework                      |
| TypeScript   | 5       | Type safety                              |
| Vite         | 5       | Build tool and dev server                |
| Tailwind CSS | 3       | Utility-first styling                    |
| React Router | 6       | Client-side routing                      |
| Recharts     | 2       | Charts (OHLCV, correlation heatmap, bar) |
| Axios        | 1       | HTTP client                              |

---

## Page Inventory

| Page        | Route       | Description                                            |
| ----------- | ----------- | ------------------------------------------------------ |
| Dashboard   | /dashboard  | Live major pair quotes, signal scan, economic calendar |
| Live Rates  | /rates      | Spot table, forward calculator, cross-rate calculator  |
| Charts      | /charts     | OHLCV line chart, indicator panel, correlation matrix  |
| Portfolio   | /portfolio  | Position management, live P&L, VaR, scenarios          |
| FX Options  | /options    | GK pricer, full Greeks, vol surface, risk reversal     |
| Carry Trade | /carry      | Carry screener, swap rates, PPP analysis               |
| Calculator  | /calculator | Position sizer, risk/reward, pip value                 |
| Alerts      | /alerts     | Price alert CRUD, live distance from target            |
| History     | /history    | Closed trade log, performance summary                  |

---

## Component Structure

```
src/
  App.tsx                  Route definitions
  main.tsx                 React DOM render entry
  index.css                Tailwind base styles
  components/
    Layout.tsx             Sidebar navigation, collapsible
    StatCard.tsx           Metric display card (label, value, color)
  pages/
    Dashboard.tsx          Live quotes, scan table, calendar
    Rates.tsx              Quote table, forward and cross calculators
    Charts.tsx             OHLCV chart, indicator panel, heatmap
    Portfolio.tsx          Portfolio selector, position table, risk
    Options.tsx            Option pricer form, Greeks table, vol surface
    Carry.tsx              Carry bar chart, screener table, PPP
    Calculator.tsx         Three calculator panels
    Alerts.tsx             Alert creation form, alert table
    History.tsx            Trade history table, performance cards
  services/
    api.ts                 Typed Axios client + WebSocket factory
```

---

## API Service Reference

The api.ts file exports five namespaced clients and a WebSocket factory.

| Export           | Purpose                                        |
| ---------------- | ---------------------------------------------- |
| ratesApi         | Spot, forward, cross, options, carry, calendar |
| technicalApi     | Analysis, scan, correlation, S/R, Fibonacci    |
| portfolioApi     | Portfolio and position CRUD, risk, scenarios   |
| analyticsApi     | Position sizing, R:R, SABR, strategy builder   |
| alertsApi        | Price alert CRUD                               |
| createRateStream | WebSocket factory for live tick streaming      |

### WebSocket usage

```typescript
import { createRateStream } from "./services/api";

const ws = createRateStream("EURUSD", ({ ticks }) => {
  const tick = ticks[0];
  console.log(tick.pair, tick.bid, tick.ask, tick.mid);
});

// Change subscription
ws.send(JSON.stringify({ action: "subscribe", pair: "GBPUSD" }));

// Cleanup on unmount
ws.close();
```

---

## Environment Variables

| Variable     | Default               | Description             |
| ------------ | --------------------- | ----------------------- |
| VITE_API_URL | http://localhost:8000 | Django backend base URL |

Set in frontend/.env or frontend/.env.production.

---

## Build and Serve

```bash
cd code/frontend

# Development (Vite hot-reload, port 5173)
npm run dev

# Production build (outputs to dist/)
npm run build

# Preview production build locally
npm run preview
```

The Nginx SPA config (`nginx-spa.conf`) serves the dist/ directory with
a fallback to index.html for all routes, enabling React Router client-side navigation.

---

## Colour Conventions

| Colour     | Meaning                               |
| ---------- | ------------------------------------- |
| cyan-400   | Brand accent, active nav items        |
| green-400  | Positive values, BUY signals, wins    |
| red-400    | Negative values, SELL signals, losses |
| yellow-400 | Targets, warnings, neutral highlights |
| gray-900   | Card backgrounds                      |
| gray-800   | Table headers, input backgrounds      |
| gray-950   | Page background                       |

---

## Adding a New Page

1. Create the component in src/pages/NewPage.tsx
2. Add the route to App.tsx

```tsx
<Route path="new-page" element={<NewPage />} />
```

3. Add the nav item to the NAV array in Layout.tsx

```tsx
{ to: "/new-page", label: "New Page", icon: "X" },
```

4. Add any new API calls to src/services/api.ts
