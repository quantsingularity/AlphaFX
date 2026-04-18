import { useState, useEffect, useCallback } from "react";
import { portfolioApi } from "../services/api";

interface Trade {
  id: string;
  pair: string;
  side: string;
  notional: number;
  entry_rate: number;
  close_rate: number;
  realized_pnl: number;
  pnl_pct: number;
  leverage: number;
  opened_at: string;
  closed_at: string;
  duration_hours: number | null;
}

interface Performance {
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate_pct: number;
  total_realized_pnl: number;
  avg_pnl_per_trade: number;
  best_trade_pnl: number;
  worst_trade_pnl: number;
  profit_factor: number | null;
  avg_win: number;
  avg_loss: number;
}

export default function History() {
  const [portfolios, setPortfolios] = useState<any[]>([]);
  const [selectedId, setSelectedId] = useState<string>("");
  const [trades, setTrades] = useState<Trade[]>([]);
  const [perf, setPerf] = useState<Performance | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    portfolioApi
      .list()
      .then((r) => {
        setPortfolios(r.data);
        if (r.data.length > 0) setSelectedId(r.data[0].id);
      })
      .catch(() => {});
  }, []);

  const loadHistory = useCallback(async (id: string) => {
    if (!id) return;
    setLoading(true);
    try {
      const [h, p] = await Promise.all([
        portfolioApi.getHistory(id),
        portfolioApi.getPerformance(id),
      ]);
      setTrades(h.data.trades || []);
      setPerf(p.data);
    } catch {
      /* ignore */
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    if (selectedId) loadHistory(selectedId);
  }, [selectedId, loadHistory]);

  const pnlColor = (v: number) => (v >= 0 ? "text-green-400" : "text-red-400");

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-cyan-400">Trade History</h1>
        <select
          value={selectedId}
          onChange={(e) => setSelectedId(e.target.value)}
          className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-gray-100"
        >
          {portfolios.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
      </div>

      {/* Performance Summary */}
      {perf && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: "Total Trades", value: perf.total_trades, unit: "" },
            {
              label: "Win Rate",
              value: `${perf.win_rate_pct.toFixed(1)}%`,
              unit: "",
              colored: perf.win_rate_pct >= 50,
            },
            {
              label: "Total P&L",
              value: `$${perf.total_realized_pnl.toFixed(2)}`,
              colored: true,
              raw: perf.total_realized_pnl,
            },
            {
              label: "Profit Factor",
              value: perf.profit_factor ? perf.profit_factor.toFixed(2) : "–",
              unit: "",
            },
            {
              label: "Avg Trade P&L",
              value: `$${perf.avg_pnl_per_trade.toFixed(2)}`,
              colored: true,
              raw: perf.avg_pnl_per_trade,
            },
            {
              label: "Best Trade",
              value: `$${perf.best_trade_pnl.toFixed(2)}`,
              unit: "",
              className: "text-green-400",
            },
            {
              label: "Worst Trade",
              value: `$${perf.worst_trade_pnl.toFixed(2)}`,
              unit: "",
              className: "text-red-400",
            },
            {
              label: "W / L",
              value: `${perf.winning_trades} / ${perf.losing_trades}`,
              unit: "",
            },
          ].map((s, i) => (
            <div
              key={i}
              className="bg-gray-900 rounded-xl p-4 border border-gray-800"
            >
              <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">
                {s.label}
              </p>
              <p
                className={`text-lg font-bold ${
                  s.className
                    ? s.className
                    : "raw" in s
                      ? pnlColor(s.raw as number)
                      : "text-white"
                }`}
              >
                {s.value}
              </p>
            </div>
          ))}
        </div>
      )}

      {/* Trade Table */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-800 text-gray-400 text-xs uppercase">
            <tr>
              {[
                "Pair",
                "Side",
                "Notional",
                "Entry",
                "Close",
                "P&L",
                "P&L %",
                "Leverage",
                "Duration",
                "Closed",
              ].map((h) => (
                <th key={h} className="px-4 py-3 text-left">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={10} className="text-center py-12 text-gray-500">
                  Loading…
                </td>
              </tr>
            ) : trades.length === 0 ? (
              <tr>
                <td colSpan={10} className="text-center py-12 text-gray-500">
                  No closed trades yet
                </td>
              </tr>
            ) : (
              trades.map((t) => (
                <tr
                  key={t.id}
                  className="border-t border-gray-800 hover:bg-gray-800/50"
                >
                  <td className="px-4 py-3 font-mono font-bold text-white">
                    {t.pair}
                  </td>
                  <td
                    className={`px-4 py-3 font-semibold ${t.side === "buy" ? "text-green-400" : "text-red-400"}`}
                  >
                    {t.side.toUpperCase()}
                  </td>
                  <td className="px-4 py-3 text-gray-300">
                    {t.notional.toLocaleString()}
                  </td>
                  <td className="px-4 py-3 font-mono text-gray-300">
                    {t.entry_rate.toFixed(5)}
                  </td>
                  <td className="px-4 py-3 font-mono text-gray-300">
                    {t.close_rate.toFixed(5)}
                  </td>
                  <td
                    className={`px-4 py-3 font-mono font-semibold ${pnlColor(t.realized_pnl)}`}
                  >
                    {t.realized_pnl >= 0 ? "+" : ""}${t.realized_pnl.toFixed(2)}
                  </td>
                  <td className={`px-4 py-3 font-mono ${pnlColor(t.pnl_pct)}`}>
                    {t.pnl_pct >= 0 ? "+" : ""}
                    {t.pnl_pct.toFixed(3)}%
                  </td>
                  <td className="px-4 py-3 text-gray-400">{t.leverage}x</td>
                  <td className="px-4 py-3 text-gray-400 text-xs">
                    {t.duration_hours ? `${t.duration_hours.toFixed(1)}h` : "–"}
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs">
                    {new Date(t.closed_at).toLocaleDateString()}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
