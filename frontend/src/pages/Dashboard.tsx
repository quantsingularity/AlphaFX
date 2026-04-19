import { useQuery } from "react-query";
import { ratesApi, technicalApi } from "../services/api";
import StatCard from "../components/StatCard";

function fmtRate(n: number, pair: string) {
  return pair.includes("JPY") ? n.toFixed(3) : n.toFixed(5);
}

export default function Dashboard() {
  const { data: majors } = useQuery("majors", ratesApi.getMajorPairs, {
    refetchInterval: 15000,
  });
  const { data: scan } = useQuery("scan", () => technicalApi.scan());
  const { data: calendar } = useQuery("calendar", ratesApi.getCalendar);

  const pairs: any[] = (majors as any)?.pairs ?? [];
  const signals: any[] = (scan as any)?.signals ?? [];

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-100">Dashboard</h1>
        <p className="text-sm text-slate-500 mt-0.5">
          Global FX market overview
        </p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {pairs.slice(0, 4).map((p: any) => (
          <StatCard
            key={p.base + p.quote}
            label={`${p.base}/${p.quote}`}
            value={fmtRate(p.mid, p.base + p.quote)}
            sub={`Spread ${p.spread_pips} pips`}
          />
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="card lg:col-span-2">
          <p className="section-title">Major Pairs</p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-surface-600">
                  {["Pair", "Bid", "Ask", "Mid", "Spread"].map((h) => (
                    <th
                      key={h}
                      className="pb-3 text-right first:text-left table-th"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-700">
                {pairs.map((p: any) => {
                  const pair = p.base + p.quote;
                  return (
                    <tr key={pair} className="hover:bg-surface-700/30">
                      <td className="py-2.5 text-slate-200 font-medium">
                        {p.base}/{p.quote}
                      </td>
                      <td className="py-2.5 table-td text-right text-red-400">
                        {fmtRate(p.bid, pair)}
                      </td>
                      <td className="py-2.5 table-td text-right text-emerald-400">
                        {fmtRate(p.ask, pair)}
                      </td>
                      <td className="py-2.5 table-td text-right">
                        {fmtRate(p.mid, pair)}
                      </td>
                      <td className="py-2.5 table-td text-right text-slate-500">
                        {p.spread_pips}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        <div className="card">
          <p className="section-title">Technical Signals</p>
          <div className="space-y-1">
            {signals.map((s: any) => (
              <div
                key={s.pair}
                className="flex justify-between items-center py-2 border-b border-surface-700 last:border-0"
              >
                <span className="text-sm text-slate-300 font-medium">
                  {s.pair}
                </span>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-slate-500 font-mono">
                    RSI {s.rsi?.toFixed(1)}
                  </span>
                  <span
                    className={
                      s.signal === "BULLISH"
                        ? "badge-buy"
                        : s.signal === "BEARISH"
                          ? "badge-sell"
                          : "badge-neutral"
                    }
                  >
                    {s.signal}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="card">
        <p className="section-title">Economic Calendar</p>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-surface-600">
                {[
                  "Date",
                  "Time",
                  "Currency",
                  "Event",
                  "Impact",
                  "Forecast",
                  "Previous",
                ].map((h) => (
                  <th key={h} className="pb-3 text-left table-th pr-4">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-700">
              {((calendar as any)?.events ?? []).map((ev: any, i: number) => (
                <tr key={i} className="hover:bg-surface-700/30">
                  <td className="py-2.5 text-slate-400 pr-4 text-sm">
                    {ev.date}
                  </td>
                  <td className="py-2.5 font-mono text-slate-300 pr-4 text-sm">
                    {ev.time}
                  </td>
                  <td className="py-2.5 pr-4">
                    <span className="badge-neutral">{ev.currency}</span>
                  </td>
                  <td className="py-2.5 text-slate-200 pr-4 text-sm">
                    {ev.event}
                  </td>
                  <td className="py-2.5 pr-4">
                    <span
                      className={
                        ev.impact === "high"
                          ? "badge-sell"
                          : ev.impact === "medium"
                            ? "text-yellow-400 text-xs"
                            : "badge-neutral"
                      }
                    >
                      {ev.impact}
                    </span>
                  </td>
                  <td className="py-2.5 font-mono text-slate-300 pr-4 text-xs">
                    {ev.forecast}
                  </td>
                  <td className="py-2.5 font-mono text-slate-500 text-xs">
                    {ev.previous}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
