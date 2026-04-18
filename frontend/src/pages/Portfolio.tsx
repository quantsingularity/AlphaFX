import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "react-query";
import { portfoliosApi } from "../services/api";

function fmt(n?: number, dp = 2) {
  return n !== undefined ? n.toFixed(dp) : "—";
}

export default function Portfolio() {
  const qc = useQueryClient();
  const { data: portfolios = [] } = useQuery("portfolios", portfoliosApi.list);
  const [selected, setSelected] = useState<string | null>(null);
  const [showNewPort, setShowNewPort] = useState(false);
  const [showNewPos, setShowNewPos] = useState(false);
  const [portForm, setPortForm] = useState({
    name: "",
    base_currency: "USD",
    initial_balance: 100000,
  });
  const [posForm, setPosForm] = useState({
    pair: "EURUSD",
    side: "buy",
    notional: 100000,
    entry_rate: 1.0842,
    leverage: 50,
  });

  const { data: portDetail } = useQuery(
    ["port-detail", selected],
    () => portfoliosApi.get(selected!),
    { enabled: !!selected },
  );
  const { data: positions } = useQuery(
    ["positions", selected],
    () => portfoliosApi.positions(selected!),
    { enabled: !!selected },
  );
  const { data: riskData } = useQuery(
    ["risk", selected],
    () => portfoliosApi.risk(selected!),
    { enabled: !!selected },
  );
  const { data: scenarioData } = useQuery(
    ["scenarios", selected],
    () => portfoliosApi.scenarios(selected!),
    { enabled: !!selected },
  );

  const createPort = useMutation(portfoliosApi.create, {
    onSuccess: () => {
      qc.invalidateQueries("portfolios");
      setShowNewPort(false);
    },
  });
  const openPos = useMutation(
    (data: any) => portfoliosApi.openPos(selected!, data),
    {
      onSuccess: () => {
        qc.invalidateQueries(["positions", selected]);
        qc.invalidateQueries(["port-detail", selected]);
        setShowNewPos(false);
      },
    },
  );
  const closePos = useMutation(
    ({ posId }: { posId: string }) => portfoliosApi.closePos(selected!, posId),
    {
      onSuccess: () => {
        qc.invalidateQueries(["positions", selected]);
        qc.invalidateQueries(["port-detail", selected]);
      },
    },
  );
  const deletePort = useMutation(portfoliosApi.delete, {
    onSuccess: () => {
      qc.invalidateQueries("portfolios");
      setSelected(null);
    },
  });

  const posList = positions?.positions ?? [];

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-100">Portfolio</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            FX position management and risk
          </p>
        </div>
        <button className="btn-primary" onClick={() => setShowNewPort(true)}>
          + New Portfolio
        </button>
      </div>

      {showNewPort && (
        <div className="card space-y-4">
          <p className="section-title">New Portfolio</p>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="label">Name</label>
              <input
                className="input"
                value={portForm.name}
                onChange={(e) =>
                  setPortForm((f) => ({ ...f, name: e.target.value }))
                }
              />
            </div>
            <div>
              <label className="label">Base Currency</label>
              <input
                className="input"
                value={portForm.base_currency}
                onChange={(e) =>
                  setPortForm((f) => ({
                    ...f,
                    base_currency: e.target.value.toUpperCase(),
                  }))
                }
              />
            </div>
            <div>
              <label className="label">Initial Balance</label>
              <input
                type="number"
                className="input"
                value={portForm.initial_balance}
                onChange={(e) =>
                  setPortForm((f) => ({
                    ...f,
                    initial_balance: parseFloat(e.target.value),
                  }))
                }
              />
            </div>
          </div>
          <div className="flex gap-3">
            <button
              className="btn-primary"
              onClick={() => createPort.mutate(portForm as any)}
            >
              Create
            </button>
            <button
              className="btn-secondary"
              onClick={() => setShowNewPort(false)}
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="space-y-2">
          {portfolios.map((p) => (
            <div
              key={p.id}
              onClick={() => setSelected(p.id)}
              className={`card-sm cursor-pointer hover:border-brand-700 transition-colors ${selected === p.id ? "border-brand-600" : ""}`}
            >
              <div className="flex justify-between">
                <p className="text-sm font-medium text-slate-200">{p.name}</p>
                <button
                  className="text-xs text-slate-600 hover:text-red-400"
                  onClick={(e) => {
                    e.stopPropagation();
                    deletePort.mutate(p.id);
                  }}
                >
                  x
                </button>
              </div>
              <p className="text-xs text-slate-500 mt-1">
                {p.open_positions} positions
              </p>
              {p.total_pnl !== undefined && (
                <p
                  className={`text-xs font-mono mt-0.5 ${p.total_pnl >= 0 ? "text-emerald-400" : "text-red-400"}`}
                >
                  P&L ${fmt(p.total_pnl)}
                </p>
              )}
            </div>
          ))}
          {portfolios.length === 0 && (
            <p className="text-slate-600 text-sm">No portfolios yet.</p>
          )}
        </div>

        <div className="lg:col-span-3 space-y-5">
          {portDetail && (
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              {[
                ["Equity", "$" + fmt(portDetail.equity)],
                ["Free Margin", "$" + fmt(portDetail.free_margin)],
                ["Used Margin", "$" + fmt(portDetail.used_margin)],
                ["Total P&L", "$" + fmt(portDetail.total_pnl)],
              ].map(([l, v]) => (
                <div key={l as string} className="card-sm">
                  <p className="stat-label">{l}</p>
                  <p className="stat-value text-base">{v}</p>
                </div>
              ))}
            </div>
          )}

          {selected && (
            <div className="card space-y-4">
              <div className="flex justify-between items-center">
                <p className="section-title mb-0">Open Positions</p>
                <button
                  className="btn-primary text-xs py-1"
                  onClick={() => setShowNewPos(true)}
                >
                  + Open Position
                </button>
              </div>

              {showNewPos && (
                <div className="grid grid-cols-3 gap-3 p-4 bg-surface-700 rounded-lg">
                  {[
                    ["pair", "Pair", "EURUSD"],
                    ["entry_rate", "Entry Rate", "1.0842"],
                    ["notional", "Notional", "100000"],
                    ["leverage", "Leverage", "50"],
                  ].map(([k, l, ph]) => (
                    <div key={k}>
                      <label className="label">{l}</label>
                      <input
                        className="input"
                        value={(posForm as any)[k]}
                        placeholder={ph}
                        onChange={(e) =>
                          setPosForm((f) => ({
                            ...f,
                            [k]: isNaN(parseFloat(e.target.value))
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
                      value={posForm.side}
                      onChange={(e) =>
                        setPosForm((f) => ({ ...f, side: e.target.value }))
                      }
                    >
                      <option value="buy">Buy</option>
                      <option value="sell">Sell</option>
                    </select>
                  </div>
                  <div className="flex items-end gap-2">
                    <button
                      className="btn-primary text-sm"
                      onClick={() => openPos.mutate(posForm)}
                    >
                      Open
                    </button>
                    <button
                      className="btn-secondary text-sm"
                      onClick={() => setShowNewPos(false)}
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}

              {posList.length === 0 ? (
                <p className="text-sm text-slate-500">No open positions.</p>
              ) : (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-surface-600">
                      {[
                        "Pair",
                        "Side",
                        "Notional",
                        "Entry",
                        "Current",
                        "P&L",
                        "P&L %",
                        "Action",
                      ].map((h) => (
                        <th
                          key={h}
                          className="pb-2 text-right first:text-left table-th"
                        >
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-surface-700">
                    {posList.map((pos: any) => (
                      <tr key={pos.id}>
                        <td className="py-2.5 font-medium text-slate-200">
                          {pos.pair}
                        </td>
                        <td className="py-2.5 text-right">
                          <span
                            className={
                              pos.side === "buy" ? "badge-buy" : "badge-sell"
                            }
                          >
                            {pos.side}
                          </span>
                        </td>
                        <td className="py-2.5 table-td text-right">
                          ${fmt(pos.notional)}
                        </td>
                        <td className="py-2.5 table-td text-right">
                          {pos.entry_rate?.toFixed(5)}
                        </td>
                        <td className="py-2.5 table-td text-right">
                          {pos.current_rate?.toFixed(5)}
                        </td>
                        <td
                          className={`py-2.5 table-td text-right ${pos.unrealized_pnl >= 0 ? "text-emerald-400" : "text-red-400"}`}
                        >
                          ${fmt(pos.unrealized_pnl)}
                        </td>
                        <td
                          className={`py-2.5 table-td text-right ${pos.unrealized_pnl_pct >= 0 ? "text-emerald-400" : "text-red-400"}`}
                        >
                          {fmt(pos.unrealized_pnl_pct, 3)}%
                        </td>
                        <td className="py-2.5 text-right">
                          <button
                            className="text-xs text-red-400 hover:text-red-300"
                            onClick={() => closePos.mutate({ posId: pos.id })}
                          >
                            Close
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}

          {riskData && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
              <div className="card">
                <p className="section-title">Risk Metrics</p>
                <div className="space-y-2">
                  {[
                    ["VaR 1D (99%)", "$" + fmt(riskData.var_1d)],
                    ["VaR 10D (99%)", "$" + fmt(riskData.var_10d)],
                    ["Exp. Shortfall", "$" + fmt(riskData.expected_shortfall)],
                    ["Total Notional", "$" + fmt(riskData.total_notional)],
                    ["Largest Pos %", fmt(riskData.largest_position_pct) + "%"],
                    ["HHI Conc.", fmt(riskData.concentration_hhi, 4)],
                  ].map(([l, v]) => (
                    <div
                      key={l as string}
                      className="flex justify-between border-b border-surface-700 pb-1.5"
                    >
                      <span className="text-xs text-slate-500">{l}</span>
                      <span className="text-xs font-mono text-slate-200">
                        {v}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="card">
                <p className="section-title">Net Currency Exposure</p>
                <div className="space-y-2">
                  {Object.entries(riskData.net_exposure_by_currency ?? {}).map(
                    ([ccy, exp]) => (
                      <div
                        key={ccy}
                        className="flex justify-between border-b border-surface-700 pb-1.5"
                      >
                        <span className="text-xs text-slate-400 font-medium">
                          {ccy}
                        </span>
                        <span
                          className={`text-xs font-mono ${(exp as number) >= 0 ? "text-emerald-400" : "text-red-400"}`}
                        >
                          ${fmt(exp as number)}
                        </span>
                      </div>
                    ),
                  )}
                </div>
              </div>
            </div>
          )}

          {scenarioData && (
            <div className="card">
              <p className="section-title">Scenario Analysis</p>
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-surface-600">
                    {["Scenario", "P&L", "P&L %", "New Equity"].map((h) => (
                      <th
                        key={h}
                        className="pb-2 text-right first:text-left table-th"
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-700">
                  {scenarioData.scenarios?.map((s: any) => (
                    <tr key={s.scenario_name}>
                      <td className="py-2 text-slate-300">{s.scenario_name}</td>
                      <td
                        className={`py-2 table-td text-right ${s.pnl >= 0 ? "text-emerald-400" : "text-red-400"}`}
                      >
                        ${fmt(s.pnl)}
                      </td>
                      <td
                        className={`py-2 table-td text-right ${s.pnl_pct >= 0 ? "text-emerald-400" : "text-red-400"}`}
                      >
                        {(s.pnl_pct * 100).toFixed(3)}%
                      </td>
                      <td className="py-2 table-td text-right">
                        ${fmt(s.new_equity)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {!selected && (
            <div className="card flex items-center justify-center h-40 text-slate-600 text-sm">
              Select a portfolio to view details
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
