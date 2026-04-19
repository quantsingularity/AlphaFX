import { useState, useEffect, useCallback } from "react";
import { alertsApi, ratesApi } from "../services/api";

interface Alert {
  id: string;
  pair: string;
  target_price: number;
  condition: "above" | "below";
  triggered: boolean;
  triggered_at: string | null;
  message: string | null;
  created_at: string;
}

const PAIRS = [
  "EURUSD",
  "GBPUSD",
  "USDJPY",
  "USDCHF",
  "AUDUSD",
  "NZDUSD",
  "USDCAD",
  "EURGBP",
  "EURJPY",
  "GBPJPY",
];

export default function Alerts() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({
    pair: "EURUSD",
    target_price: "",
    condition: "above" as "above" | "below",
    message: "",
  });
  const [liveRates, setLiveRates] = useState<Record<string, number>>({});

  const fetchAlerts = useCallback(async () => {
    try {
      const r = await alertsApi.list();
      setAlerts((r as any).alerts || []);
    } catch {
      /* ignore */
    }
    setLoading(false);
  }, []);

  const fetchRates = useCallback(async () => {
    try {
      const r = await ratesApi.getMajorPairs();
      const map: Record<string, number> = {};
      for (const q of (r as any).pairs) map[`${q.base}${q.quote}`] = q.mid;
      setLiveRates(map);
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    fetchAlerts();
    fetchRates();
    const t = setInterval(fetchRates, 10_000);
    return () => clearInterval(t);
  }, [fetchAlerts, fetchRates]);

  const createAlert = async () => {
    if (!form.target_price) return;
    try {
      await alertsApi.create({
        pair: form.pair,
        target_price: parseFloat(form.target_price),
        condition: form.condition,
        message: form.message || undefined,
      });
      setForm({
        pair: "EURUSD",
        target_price: "",
        condition: "above",
        message: "",
      });
      fetchAlerts();
    } catch {
      /* ignore */
    }
  };

  const deleteAlert = async (id: string) => {
    await alertsApi.delete(id);
    fetchAlerts();
  };

  const conditionColor = (a: Alert) => {
    if (a.triggered) return "text-green-400";
    const current = liveRates[a.pair] || 0;
    const dist = (Math.abs(current - a.target_price) / a.target_price) * 100;
    if (dist < 0.1) return "text-yellow-400 animate-pulse";
    return "text-gray-300";
  };

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold text-cyan-400">Price Alerts</h1>

      {/* Create Alert */}
      <div className="bg-gray-900 rounded-xl p-5 border border-gray-800">
        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">
          New Alert
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Pair</label>
            <select
              value={form.pair}
              onChange={(e) => setForm((f) => ({ ...f, pair: e.target.value }))}
              className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-gray-100"
            >
              {PAIRS.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">
              Condition
            </label>
            <select
              value={form.condition}
              onChange={(e) =>
                setForm((f) => ({ ...f, condition: e.target.value as any }))
              }
              className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-gray-100"
            >
              <option value="above">Price Above</option>
              <option value="below">Price Below</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">
              Target Price
              {liveRates[form.pair] && (
                <span className="ml-2 text-cyan-400">
                  (current: {liveRates[form.pair].toFixed(5)})
                </span>
              )}
            </label>
            <input
              type="number"
              step="0.00001"
              value={form.target_price}
              onChange={(e) =>
                setForm((f) => ({ ...f, target_price: e.target.value }))
              }
              placeholder="1.09000"
              className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-gray-100"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">
              Message (optional)
            </label>
            <input
              type="text"
              value={form.message}
              onChange={(e) =>
                setForm((f) => ({ ...f, message: e.target.value }))
              }
              placeholder="e.g. Breakout alert"
              className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-gray-100"
            />
          </div>
        </div>
        <button
          onClick={createAlert}
          className="mt-4 bg-cyan-600 hover:bg-cyan-700 text-white px-6 py-2 rounded-lg text-sm font-medium transition-colors"
        >
          Create Alert
        </button>
      </div>

      {/* Alert List */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-800 text-gray-400 text-xs uppercase">
            <tr>
              {[
                "Pair",
                "Condition",
                "Target",
                "Current",
                "Distance",
                "Status",
                "Created",
                "",
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
                <td colSpan={8} className="text-center py-12 text-gray-500">
                  Loading…
                </td>
              </tr>
            ) : alerts.length === 0 ? (
              <tr>
                <td colSpan={8} className="text-center py-12 text-gray-500">
                  No alerts set
                </td>
              </tr>
            ) : (
              alerts.map((a) => {
                const current = liveRates[a.pair];
                const dist = current
                  ? (
                      ((current - a.target_price) / a.target_price) *
                      100
                    ).toFixed(3)
                  : "–";
                return (
                  <tr
                    key={a.id}
                    className="border-t border-gray-800 hover:bg-gray-800/50"
                  >
                    <td className="px-4 py-3 font-mono font-bold text-white">
                      {a.pair}
                    </td>
                    <td className="px-4 py-3 text-gray-300 capitalize">
                      {a.condition}
                    </td>
                    <td className="px-4 py-3 font-mono text-yellow-400">
                      {a.target_price.toFixed(5)}
                    </td>
                    <td className="px-4 py-3 font-mono text-cyan-400">
                      {current ? current.toFixed(5) : "–"}
                    </td>
                    <td className={`px-4 py-3 font-mono ${conditionColor(a)}`}>
                      {dist}%
                    </td>
                    <td className="px-4 py-3">
                      {a.triggered ? (
                        <span className="px-2 py-1 bg-green-900/50 text-green-400 rounded text-xs">
                          Triggered{" "}
                          {a.triggered_at
                            ? new Date(a.triggered_at).toLocaleDateString()
                            : ""}
                        </span>
                      ) : (
                        <span className="px-2 py-1 bg-blue-900/50 text-blue-400 rounded text-xs">
                          Active
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-gray-500 text-xs">
                      {new Date(a.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => deleteAlert(a.id)}
                        className="text-red-500 hover:text-red-400 text-xs px-2 py-1 rounded hover:bg-red-900/20 transition-colors"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
