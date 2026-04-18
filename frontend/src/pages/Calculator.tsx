import { useState } from "react";
import { analyticsApi, ratesApi } from "../services/api";

function fmt(n?: number, dp = 2) {
  return n !== undefined && n !== null ? n.toFixed(dp) : "—";
}

export default function Calculator() {
  const [psForm, setPsForm] = useState({
    account_balance: 10000,
    risk_pct: 1,
    stop_loss_pips: 20,
    pair: "EURUSD",
    leverage: 50,
  });
  const [psResult, setPsResult] = useState<any>(null);

  const [rrForm, setRrForm] = useState({
    pair: "EURUSD",
    side: "buy",
    entry: 1.0842,
    stop_loss: 1.08,
    take_profit: 1.095,
  });
  const [rrResult, setRrResult] = useState<any>(null);

  const [pvForm, setPvForm] = useState({ pair: "EURUSD", notional: 100000 });
  const [pvResult, setPvResult] = useState<any>(null);

  const handlePS = async () => {
    setPsResult(await analyticsApi.positionSize(psForm));
  };
  const handleRR = async () => {
    setRrResult(await analyticsApi.riskReward(rrForm));
  };
  const handlePV = async () => {
    setPvResult(await ratesApi.pipValue(pvForm.pair, pvForm.notional));
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-100">Calculator</h1>
        <p className="text-sm text-slate-500 mt-0.5">
          Position sizing, risk/reward, pip value
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="card space-y-4">
          <p className="section-title">Position Sizer</p>
          <div className="space-y-3">
            {[
              ["account_balance", "Account Balance ($)", "number"],
              ["risk_pct", "Risk % per Trade", "number"],
              ["stop_loss_pips", "Stop Loss (pips)", "number"],
              ["pair", "Currency Pair", "text"],
              ["leverage", "Leverage", "number"],
            ].map(([k, label, type]) => (
              <div key={k as string}>
                <label className="label">{label}</label>
                <input
                  type={type as string}
                  className="input"
                  value={(psForm as any)[k as string]}
                  onChange={(e) =>
                    setPsForm((f) => ({
                      ...f,
                      [k as string]:
                        type === "text"
                          ? e.target.value.toUpperCase()
                          : parseFloat(e.target.value),
                    }))
                  }
                />
              </div>
            ))}
          </div>
          <button className="btn-primary w-full" onClick={handlePS}>
            Calculate
          </button>
          {psResult && (
            <div className="space-y-2 pt-3 border-t border-surface-600">
              {[
                ["Risk Amount", "$" + fmt(psResult.risk_amount_usd)],
                ["Units", String(psResult.recommended_units?.toLocaleString())],
                ["Lots", fmt(psResult.recommended_lots)],
                ["Notional", "$" + fmt(psResult.notional)],
                ["Pip Value/Unit", fmt(psResult.pip_value_per_unit, 6)],
              ].map(([l, v]) => (
                <div key={l as string} className="flex justify-between">
                  <span className="text-xs text-slate-500">{l}</span>
                  <span className="text-xs font-mono text-brand-400">{v}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="card space-y-4">
          <p className="section-title">Risk / Reward</p>
          <div className="space-y-3">
            {[
              ["pair", "Pair", "text", "EURUSD"],
              ["entry", "Entry Rate", "number", "1.0842"],
              ["stop_loss", "Stop Loss", "number", "1.0800"],
              ["take_profit", "Take Profit", "number", "1.0950"],
            ].map(([k, label, type, ph]) => (
              <div key={k as string}>
                <label className="label">{label}</label>
                <input
                  type={type as string}
                  step="0.0001"
                  className="input"
                  placeholder={ph as string}
                  value={(rrForm as any)[k as string]}
                  onChange={(e) =>
                    setRrForm((f) => ({
                      ...f,
                      [k as string]:
                        type === "text"
                          ? e.target.value.toUpperCase()
                          : parseFloat(e.target.value),
                    }))
                  }
                />
              </div>
            ))}
            <div>
              <label className="label">Side</label>
              <select
                className="input"
                value={rrForm.side}
                onChange={(e) =>
                  setRrForm((f) => ({ ...f, side: e.target.value }))
                }
              >
                <option value="buy">Buy</option>
                <option value="sell">Sell</option>
              </select>
            </div>
          </div>
          <button className="btn-primary w-full" onClick={handleRR}>
            Calculate
          </button>
          {rrResult && (
            <div className="space-y-2 pt-3 border-t border-surface-600">
              {[
                ["Risk (pips)", fmt(rrResult.risk_pips, 1)],
                ["Reward (pips)", fmt(rrResult.reward_pips, 1)],
                ["R:R Ratio", "1 : " + fmt(rrResult.risk_reward_ratio)],
                [
                  "Breakeven Win %",
                  fmt(rrResult.breakeven_win_rate_pct, 1) + "%",
                ],
              ].map(([l, v]) => (
                <div key={l as string} className="flex justify-between">
                  <span className="text-xs text-slate-500">{l}</span>
                  <span
                    className={`text-xs font-mono ${l === "R:R Ratio" ? "text-brand-400 font-semibold" : "text-slate-200"}`}
                  >
                    {v}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="card space-y-4">
          <p className="section-title">Pip Value</p>
          <div className="space-y-3">
            <div>
              <label className="label">Currency Pair</label>
              <input
                className="input"
                value={pvForm.pair}
                onChange={(e) =>
                  setPvForm((f) => ({
                    ...f,
                    pair: e.target.value.toUpperCase(),
                  }))
                }
              />
            </div>
            <div>
              <label className="label">Notional (units)</label>
              <input
                type="number"
                className="input"
                value={pvForm.notional}
                onChange={(e) =>
                  setPvForm((f) => ({
                    ...f,
                    notional: parseFloat(e.target.value),
                  }))
                }
              />
            </div>
          </div>
          <button className="btn-primary w-full" onClick={handlePV}>
            Calculate
          </button>
          {pvResult && (
            <div className="space-y-2 pt-3 border-t border-surface-600">
              {[
                ["Pair", pvResult.pair],
                ["Spot Rate", pvResult.spot?.toFixed(5)],
                ["Notional", pvResult.notional?.toLocaleString()],
                ["Pip Value (USD)", "$" + fmt(pvResult.pip_value_usd, 4)],
              ].map(([l, v]) => (
                <div key={l as string} className="flex justify-between">
                  <span className="text-xs text-slate-500">{l}</span>
                  <span className="text-xs font-mono text-slate-200">{v}</span>
                </div>
              ))}
              <div className="bg-surface-700 rounded-lg p-3 text-center mt-2">
                <p className="text-xs text-slate-500 mb-1">10 pip move P&L</p>
                <p className="text-lg font-mono font-semibold text-brand-400">
                  ${fmt(pvResult.pip_value_usd * 10, 2)}
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
