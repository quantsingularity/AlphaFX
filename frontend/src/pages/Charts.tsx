import { useState } from "react";
import { useQuery } from "react-query";
import { technicalApi } from "../services/api";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";

const PAIRS = [
  "EURUSD",
  "GBPUSD",
  "USDJPY",
  "AUDUSD",
  "USDCAD",
  "EURGBP",
  "EURJPY",
  "GBPJPY",
  "USDCHF",
  "NZDUSD",
];

export default function Charts() {
  const [pair, setPair] = useState("EURUSD");
  const { data, isLoading } = useQuery(
    ["technical", pair],
    () => technicalApi.analyze(pair, 252),
    { keepPreviousData: true },
  );
  const { data: corrData } = useQuery("correlation", () =>
    technicalApi.correlation("EURUSD,GBPUSD,USDJPY,AUDUSD,USDCAD", 60),
  );

  const ind = data?.indicators;
  const ohlcv = data?.ohlcv ?? [];

  const priceData = ohlcv.map((d: any) => ({
    ...d,
    ema20: null,
    bb_upper: null,
    bb_lower: null,
  }));

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-100">Charts</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Technical analysis and indicators
          </p>
        </div>
        <div className="flex gap-2 flex-wrap">
          {PAIRS.map((p) => (
            <button
              key={p}
              onClick={() => setPair(p)}
              className={
                pair === p
                  ? "btn-primary text-xs py-1 px-3"
                  : "btn-secondary text-xs py-1 px-3"
              }
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      {data && (
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
          {[
            [
              "Price",
              data.current_price?.toFixed(5),
              (data.change_pct >= 0 ? "+" : "") +
                data.change_pct?.toFixed(3) +
                "%",
              data.change_pct >= 0 ? "up" : "down",
            ],
            [
              "RSI 14",
              ind?.rsi_14?.toFixed(2),
              ind && ind.rsi_14 > 70
                ? "Overbought"
                : ind && ind.rsi_14 < 30
                  ? "Oversold"
                  : "Neutral",
              "neutral",
            ],
            [
              "MACD",
              ind?.macd?.toFixed(6),
              "Hist " + ind?.macd_hist?.toFixed(6),
              ind && ind.macd_hist > 0 ? "up" : "down",
            ],
            [
              "Vol %",
              data.annualized_volatility_pct?.toFixed(2) + "%",
              "Annualized",
              "neutral",
            ],
            [
              "Signal",
              data.signal,
              "Overall",
              data.signal === "BULLISH"
                ? "up"
                : data.signal === "BEARISH"
                  ? "down"
                  : "neutral",
            ],
          ].map(([label, value, sub, trend]) => (
            <div key={label as string} className="card-sm">
              <p className="stat-label">{label}</p>
              <p
                className={`text-lg font-mono font-semibold ${trend === "up" ? "text-emerald-400" : trend === "down" ? "text-red-400" : "text-slate-200"}`}
              >
                {value}
              </p>
              <p className="text-xs text-slate-500 mt-0.5">{sub}</p>
            </div>
          ))}
        </div>
      )}

      <div className="card">
        <p className="section-title">{pair} Price History</p>
        {isLoading ? (
          <div className="h-64 flex items-center justify-center text-slate-500 text-sm">
            Loading...
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={280}>
            <LineChart
              data={priceData}
              margin={{ top: 4, right: 16, bottom: 4, left: 0 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#161e35" />
              <XAxis
                dataKey="date"
                tick={{ fill: "#64748b", fontSize: 10 }}
                axisLine={{ stroke: "#1e2845" }}
                tickLine={false}
                tickFormatter={(v) => v.slice(5)}
                interval={Math.floor(priceData.length / 8)}
              />
              <YAxis
                tick={{ fill: "#64748b", fontSize: 10 }}
                axisLine={{ stroke: "#1e2845" }}
                tickLine={false}
                domain={["auto", "auto"]}
                tickFormatter={(v) => v.toFixed(4)}
              />
              <Tooltip
                contentStyle={{
                  background: "#0f1628",
                  border: "1px solid #1e2845",
                  borderRadius: 8,
                  fontSize: 11,
                }}
                formatter={(v: number) => [v.toFixed(5), "Close"]}
              />
              <Line
                type="monotone"
                dataKey="close"
                stroke="#22c55e"
                strokeWidth={1.5}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <p className="section-title">Indicators</p>
          {ind && (
            <div className="grid grid-cols-2 gap-x-8 gap-y-2">
              {[
                ["EMA 20", ind.ema_20?.toFixed(5)],
                ["EMA 50", ind.ema_50?.toFixed(5)],
                ["EMA 200", ind.ema_200?.toFixed(5)],
                ["BB Upper", ind.bb_upper?.toFixed(5)],
                ["BB Mid", ind.bb_mid?.toFixed(5)],
                ["BB Lower", ind.bb_lower?.toFixed(5)],
                ["ATR 14", ind.atr_14?.toFixed(6)],
                ["Stoch %K", ind.stoch_k?.toFixed(2)],
                ["Stoch %D", ind.stoch_d?.toFixed(2)],
                ["MACD Sig", ind.macd_signal?.toFixed(6)],
              ].map(([l, v]) => (
                <div
                  key={l as string}
                  className="flex justify-between border-b border-surface-700 py-1.5"
                >
                  <span className="text-xs text-slate-500">{l}</span>
                  <span className="text-xs font-mono text-slate-200">{v}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="card">
          <p className="section-title">Correlation Matrix (60D)</p>
          {corrData ? (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr>
                    <th className="pb-2 text-left text-slate-500"></th>
                    {corrData.pairs.map((p: string) => (
                      <th
                        key={p}
                        className="pb-2 text-center text-slate-500 font-medium"
                      >
                        {p.slice(0, 6)}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {corrData.matrix.map((row: number[], i: number) => (
                    <tr key={i}>
                      <td className="py-1.5 pr-2 text-slate-400 font-medium">
                        {corrData.pairs[i].slice(0, 6)}
                      </td>
                      {row.map((val: number, j: number) => (
                        <td
                          key={j}
                          className="py-1.5 text-center font-mono"
                          style={{
                            color:
                              val === 1
                                ? "#94a3b8"
                                : val > 0.5
                                  ? "#f87171"
                                  : val < -0.5
                                    ? "#4ade80"
                                    : "#94a3b8",
                          }}
                        >
                          {val.toFixed(2)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-slate-500 text-sm">Loading...</div>
          )}
        </div>
      </div>
    </div>
  );
}
