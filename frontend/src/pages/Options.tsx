import { useState } from "react";
import { ratesApi } from "../services/api";
import type { FXOptionResult } from "../services/api";

function fmt(n?: number, dp = 4) {
  return n !== undefined ? n.toFixed(dp) : "—";
}

const DEFAULT = {
  base: "EUR",
  quote: "USD",
  spot: 1.0842,
  strike: 1.09,
  tenor_days: 30,
  volatility: 0.065,
  base_rate: 0.0425,
  quote_rate: 0.0533,
  option_type: "call",
  notional: 1000000,
};

export default function Options() {
  const [form, setForm] = useState(DEFAULT);
  const [result, setResult] = useState<FXOptionResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [volPair, setVolPair] = useState("EURUSD");
  const [surface, setSurface] = useState<any>(null);

  const handlePrice = async () => {
    setLoading(true);
    try {
      setResult(await ratesApi.option(form));
    } finally {
      setLoading(false);
    }
  };

  const handleSurface = async () => {
    const s = await ratesApi.volSurface(volPair);
    setSurface(s);
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-100">FX Options</h1>
        <p className="text-sm text-slate-500 mt-0.5">
          Garman-Kohlhagen pricing, Greeks, implied volatility surface
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card space-y-4">
          <p className="section-title">Option Pricer</p>
          <div className="grid grid-cols-2 gap-3">
            {[
              ["base", "Base CCY", "text", "EUR"],
              ["quote", "Quote CCY", "text", "USD"],
              ["spot", "Spot Rate", "number", "1.0842"],
              ["strike", "Strike", "number", "1.09"],
              ["tenor_days", "Tenor (days)", "number", "30"],
              ["volatility", "Vol (decimal)", "number", "0.065"],
              ["base_rate", "Base Rate", "number", "0.0425"],
              ["quote_rate", "Quote Rate", "number", "0.0533"],
              ["notional", "Notional", "number", "1000000"],
            ].map(([key, label, type, ph]) => (
              <div key={key as string}>
                <label className="label">{label}</label>
                <input
                  type={type as string}
                  step="0.0001"
                  className="input"
                  placeholder={ph as string}
                  value={(form as any)[key as string]}
                  onChange={(e) =>
                    setForm((f) => ({
                      ...f,
                      [key as string]:
                        type === "text"
                          ? e.target.value.toUpperCase()
                          : parseFloat(e.target.value),
                    }))
                  }
                />
              </div>
            ))}
            <div>
              <label className="label">Option Type</label>
              <select
                className="input"
                value={form.option_type}
                onChange={(e) =>
                  setForm((f) => ({ ...f, option_type: e.target.value }))
                }
              >
                <option value="call">Call</option>
                <option value="put">Put</option>
              </select>
            </div>
          </div>
          <button
            className="btn-primary w-full"
            onClick={handlePrice}
            disabled={loading}
          >
            {loading ? "Pricing..." : "Price Option"}
          </button>
        </div>

        {result ? (
          <div className="card space-y-4">
            <p className="section-title">
              {result.option_type.toUpperCase()} Option Results
            </p>
            <div className="grid grid-cols-2 gap-3">
              {[
                ["Price", fmt(result.price, 6)],
                ["Price %", fmt(result.price_pct, 4) + "%"],
                ["Intrinsic", fmt(result.intrinsic_value, 6)],
                ["Time Value", fmt(result.time_value, 6)],
                ["Breakeven", fmt(result.breakeven, 5)],
                ["Volatility", result.volatility_pct?.toFixed(2) + "%"],
              ].map(([l, v]) => (
                <div
                  key={l as string}
                  className="bg-surface-700 rounded-lg p-3"
                >
                  <p className="text-xs text-slate-500">{l}</p>
                  <p className="text-base font-mono font-semibold text-slate-100 mt-0.5">
                    {v}
                  </p>
                </div>
              ))}
            </div>

            <div className="border-t border-surface-600 pt-4">
              <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-3">
                Greeks
              </p>
              <div className="grid grid-cols-2 gap-2">
                {[
                  ["Delta", fmt(result.delta, 6), "Direction sensitivity"],
                  ["Gamma", fmt(result.gamma, 6), "Delta rate of change"],
                  ["Vega", fmt(result.vega, 6), "Vol sensitivity (per 1%)"],
                  ["Theta", fmt(result.theta, 6), "Time decay (per day)"],
                  ["Rho", fmt(result.rho, 6), "Rate sensitivity"],
                ].map(([name, value, desc]) => (
                  <div
                    key={name as string}
                    className="flex justify-between items-center border-b border-surface-700 py-1.5"
                  >
                    <div>
                      <span className="text-xs font-medium text-slate-300">
                        {name}
                      </span>
                      <p className="text-xs text-slate-600">{desc}</p>
                    </div>
                    <span className="text-xs font-mono text-brand-400">
                      {value}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="card flex items-center justify-center text-slate-600 text-sm">
            Price an option to see Greeks and analytics
          </div>
        )}
      </div>

      <div className="card space-y-4">
        <div className="flex items-center gap-4">
          <p className="section-title mb-0">Implied Volatility Surface</p>
          <input
            className="input w-32"
            value={volPair}
            onChange={(e) => setVolPair(e.target.value.toUpperCase())}
            placeholder="EURUSD"
          />
          <button className="btn-secondary text-sm" onClick={handleSurface}>
            Load Surface
          </button>
        </div>

        {surface && (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-surface-600">
                  <th className="pb-2 text-left table-th pr-4">Tenor</th>
                  {surface.deltas.map((d: number) => (
                    <th key={d} className="pb-2 text-center table-th px-3">
                      {d}D
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-700">
                {surface.tenors.map((t: number) => {
                  const row = surface.surface[`${t}D`];
                  return (
                    <tr key={t} className="hover:bg-surface-700/30">
                      <td className="py-2 text-slate-400 pr-4 font-medium">
                        {t}D
                      </td>
                      {surface.deltas.map((d: number) => (
                        <td
                          key={d}
                          className="py-2 text-center font-mono text-brand-400 px-3"
                        >
                          {(row[String(d)] * 100).toFixed(2)}%
                        </td>
                      ))}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
