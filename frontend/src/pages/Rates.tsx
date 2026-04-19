import { useState } from "react";
import { useQuery } from "react-query";
import { ratesApi } from "../services/api";

function fmtRate(n: number, pair: string) {
  return pair.includes("JPY") ? n.toFixed(3) : n.toFixed(5);
}

export default function Rates() {
  const { data: majors, isLoading } = useQuery(
    "majors",
    ratesApi.getMajorPairs,
    {
      refetchInterval: 10000,
    },
  );
  const { data: irData } = useQuery(
    "interest-rates",
    ratesApi.getInterestRates,
  );
  const [fwdForm, setFwdForm] = useState({
    base: "EUR",
    quote: "USD",
    tenor_days: 30,
  });
  const [fwdResult, setFwdResult] = useState<any>(null);
  const [crossForm, setCrossForm] = useState({ base: "GBP", quote: "JPY" });
  const [crossResult, setCrossResult] = useState<any>(null);

  const handleForward = async () => {
    const r = await ratesApi.getForwardRate(fwdForm);
    setFwdResult(r);
  };

  const handleCross = async () => {
    const r = await ratesApi.getCrossRate(crossForm);
    setCrossResult(r);
  };

  const pairs: any[] = (majors as any)?.pairs ?? [];
  const rates: Record<string, number> = (irData as any)?.rates ?? {};

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-100">Live Rates</h1>
        <p className="text-sm text-slate-500 mt-0.5">
          Spot quotes, forwards, cross-rates
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="card lg:col-span-2 p-0 overflow-hidden">
          <div className="px-5 py-4 border-b border-surface-600">
            <p className="section-title mb-0">Spot Quotes</p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-surface-700/40">
                <tr>
                  {["Pair", "Bid", "Ask", "Mid", "Spread (pips)", "Source"].map(
                    (h) => (
                      <th key={h} className="px-4 py-3 text-left table-th">
                        {h}
                      </th>
                    ),
                  )}
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-700">
                {isLoading ? (
                  <tr>
                    <td
                      colSpan={6}
                      className="px-4 py-8 text-center text-slate-500"
                    >
                      Loading rates...
                    </td>
                  </tr>
                ) : (
                  pairs.map((p: any) => {
                    const pair = p.base + p.quote;
                    return (
                      <tr key={pair} className="hover:bg-surface-700/30">
                        <td className="px-4 py-3 font-medium text-slate-200">
                          {p.base}/{p.quote}
                        </td>
                        <td className="px-4 py-3 font-mono text-red-400">
                          {fmtRate(p.bid, pair)}
                        </td>
                        <td className="px-4 py-3 font-mono text-emerald-400">
                          {fmtRate(p.ask, pair)}
                        </td>
                        <td className="px-4 py-3 font-mono text-slate-200">
                          {fmtRate(p.mid, pair)}
                        </td>
                        <td className="px-4 py-3 font-mono text-slate-400">
                          {p.spread_pips}
                        </td>
                        <td className="px-4 py-3 text-xs text-slate-600">
                          {p.source}
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="space-y-4">
          <div className="card space-y-4">
            <p className="section-title">Forward Rate</p>
            <div className="grid grid-cols-2 gap-3">
              {[
                ["base", "Base", "EUR"],
                ["quote", "Quote", "USD"],
              ].map(([k, label, ph]) => (
                <div key={k}>
                  <label className="label">{label}</label>
                  <input
                    className="input"
                    value={(fwdForm as any)[k]}
                    placeholder={ph}
                    onChange={(e) =>
                      setFwdForm((f) => ({
                        ...f,
                        [k]: e.target.value.toUpperCase(),
                      }))
                    }
                  />
                </div>
              ))}
              <div className="col-span-2">
                <label className="label">Tenor (days)</label>
                <input
                  type="number"
                  className="input"
                  value={fwdForm.tenor_days}
                  onChange={(e) =>
                    setFwdForm((f) => ({
                      ...f,
                      tenor_days: parseInt(e.target.value),
                    }))
                  }
                />
              </div>
            </div>
            <button className="btn-primary w-full" onClick={handleForward}>
              Calculate
            </button>
            {fwdResult && (
              <div className="space-y-1.5 pt-2 border-t border-surface-600">
                {[
                  ["Spot", fwdResult.spot?.toFixed(5)],
                  ["Forward Rate", fwdResult.forward_rate?.toFixed(5)],
                  ["Fwd Points", fwdResult.forward_points?.toFixed(4)],
                  [
                    "Carry (bps)",
                    fwdResult.annualized_swap_cost_bps?.toFixed(1),
                  ],
                ].map(([l, v]) => (
                  <div key={l as string} className="flex justify-between">
                    <span className="text-xs text-slate-500">{l}</span>
                    <span className="text-xs font-mono text-slate-200">
                      {v}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="card space-y-4">
            <p className="section-title">Cross Rate</p>
            <div className="grid grid-cols-2 gap-3">
              {[
                ["base", "Base", "GBP"],
                ["quote", "Quote", "JPY"],
              ].map(([k, label, ph]) => (
                <div key={k}>
                  <label className="label">{label}</label>
                  <input
                    className="input"
                    value={(crossForm as any)[k]}
                    placeholder={ph}
                    onChange={(e) =>
                      setCrossForm((f) => ({
                        ...f,
                        [k]: e.target.value.toUpperCase(),
                      }))
                    }
                  />
                </div>
              ))}
            </div>
            <button className="btn-primary w-full" onClick={handleCross}>
              Calculate
            </button>
            {crossResult && (
              <div className="pt-2 border-t border-surface-600 text-center">
                <p className="text-2xl font-mono font-semibold text-brand-400">
                  {crossResult.rate?.toFixed(5)}
                </p>
                <p className="text-xs text-slate-500 mt-1">
                  {crossResult.base}/{crossResult.quote}
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="card">
        <p className="section-title">Central Bank Interest Rates</p>
        <div className="grid grid-cols-3 lg:grid-cols-5 gap-3">
          {Object.entries(rates).map(([ccy, rate]) => (
            <div
              key={ccy}
              className="bg-surface-700 rounded-lg p-3 text-center"
            >
              <p className="text-sm font-semibold text-slate-200">{ccy}</p>
              <p className="text-lg font-mono text-brand-400 mt-1">
                {((rate as number) * 100).toFixed(2)}%
              </p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
