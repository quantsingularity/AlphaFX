import { useState } from "react";
import { useQuery } from "react-query";
import { ratesApi, analyticsApi } from "../services/api";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Cell,
} from "recharts";

export default function Carry() {
  const [minCarry, setMinCarry] = useState(0);
  const { data: carryData } = useQuery(["carry", minCarry], () =>
    ratesApi.getCarry(minCarry),
  );
  const { data: swapData } = useQuery("swaps", analyticsApi.swapRates);
  const { data: pppData } = useQuery("ppp", analyticsApi.ppp);

  const opps = (carryData as any)?.opportunities ?? [];
  const swaps = (swapData as any)?.swap_rates ?? [];
  const ppps = (pppData as any)?.ppp_analysis ?? [];

  const chartData = opps.slice(0, 10).map((o: any) => ({
    pair: o.pair,
    carry: parseFloat(o.carry_rate_bps.toFixed(1)),
  }));

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-100">Carry Trade</h1>
        <p className="text-sm text-slate-500 mt-0.5">
          Interest rate differential screening, swap rates, PPP analysis
        </p>
      </div>

      <div className="flex items-center gap-4">
        <label className="label mb-0">Min Carry (bps)</label>
        <input
          type="number"
          className="input w-32"
          value={minCarry}
          onChange={(e) => setMinCarry(parseFloat(e.target.value) || 0)}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <p className="section-title">Top Carry Opportunities</p>
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart
                data={chartData}
                margin={{ top: 4, right: 8, bottom: 30, left: 0 }}
              >
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="#161e35"
                  vertical={false}
                />
                <XAxis
                  dataKey="pair"
                  tick={{ fill: "#64748b", fontSize: 10 }}
                  axisLine={{ stroke: "#1e2845" }}
                  tickLine={false}
                  angle={-35}
                  textAnchor="end"
                />
                <YAxis
                  tick={{ fill: "#64748b", fontSize: 10 }}
                  axisLine={{ stroke: "#1e2845" }}
                  tickLine={false}
                />
                <Tooltip
                  contentStyle={{
                    background: "#0f1628",
                    border: "1px solid #1e2845",
                    borderRadius: 8,
                    fontSize: 11,
                  }}
                  formatter={(v: number) => [v + " bps", "Carry"]}
                />
                <Bar dataKey="carry" radius={[3, 3, 0, 0]}>
                  {chartData.map((_: any, i: number) => (
                    <Cell
                      key={i}
                      fill={i < 3 ? "#22c55e" : i < 6 ? "#86efac" : "#4ade80"}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-64 flex items-center justify-center text-slate-500 text-sm">
              No opportunities at this threshold
            </div>
          )}
        </div>

        <div className="card overflow-y-auto max-h-96">
          <p className="section-title">Carry Screening Table</p>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-surface-600">
                {["Pair", "Long", "Short", "Carry (bps)", "Annual %"].map(
                  (h) => (
                    <th
                      key={h}
                      className="pb-2 text-right first:text-left table-th"
                    >
                      {h}
                    </th>
                  ),
                )}
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-700">
              {opps.map((o: any) => (
                <tr key={o.pair} className="hover:bg-surface-700/30">
                  <td className="py-2 font-medium text-slate-200">{o.pair}</td>
                  <td className="py-2 text-right">
                    <span className="badge-buy text-xs">{o.long_currency}</span>
                  </td>
                  <td className="py-2 text-right">
                    <span className="badge-sell text-xs">
                      {o.short_currency}
                    </span>
                  </td>
                  <td className="py-2 table-td text-right text-brand-400">
                    {o.carry_rate_bps.toFixed(1)}
                  </td>
                  <td className="py-2 table-td text-right">
                    {o.annualized_carry_pct.toFixed(2)}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <p className="section-title">Forward Swap Rates</p>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-surface-600">
                  {["Pair", "Carry (bps)", "Fwd Pts 1W", "Fwd Pts 1M"].map(
                    (h) => (
                      <th
                        key={h}
                        className="pb-2 text-right first:text-left table-th"
                      >
                        {h}
                      </th>
                    ),
                  )}
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-700">
                {swaps.slice(0, 12).map((s: any) => (
                  <tr key={s.pair} className="hover:bg-surface-700/30">
                    <td className="py-2 text-slate-300 font-medium">
                      {s.pair}
                    </td>
                    <td
                      className={`py-2 font-mono text-right ${s.carry_bps > 0 ? "text-emerald-400" : "text-red-400"}`}
                    >
                      {s.carry_bps.toFixed(1)}
                    </td>
                    <td className="py-2 table-td text-right">
                      {s.forward_points_1w.toFixed(4)}
                    </td>
                    <td className="py-2 table-td text-right">
                      {s.forward_points_1m.toFixed(4)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="card">
          <p className="section-title">Purchasing Power Parity</p>
          <div className="space-y-2">
            {ppps.map((p: any) => (
              <div
                key={p.pair}
                className="flex items-center justify-between border-b border-surface-700 py-2"
              >
                <div>
                  <p className="text-sm font-medium text-slate-200">{p.pair}</p>
                  <p className="text-xs text-slate-500">
                    PPP: {p.ppp_rate?.toFixed(4)} | Spot: {p.spot?.toFixed(4)}
                  </p>
                </div>
                <div className="text-right">
                  <p
                    className={`text-sm font-mono font-semibold ${p.deviation_pct > 0 ? "text-red-400" : "text-emerald-400"}`}
                  >
                    {p.deviation_pct > 0 ? "+" : ""}
                    {p.deviation_pct.toFixed(2)}%
                  </p>
                  <p className="text-xs text-slate-500">
                    {p.overvalued ? "Overvalued" : "Undervalued"}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
