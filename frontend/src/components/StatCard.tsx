interface Props {
  label: string;
  value: string | number;
  sub?: string;
  trend?: "up" | "down" | "neutral";
}

export default function StatCard({ label, value, sub, trend }: Props) {
  const subClass =
    trend === "up" ? "up" : trend === "down" ? "down" : "neutral";
  return (
    <div className="card-sm flex flex-col gap-1.5">
      <span className="stat-label">{label}</span>
      <span className="stat-value">{value}</span>
      {sub && <span className={`text-xs ${subClass}`}>{sub}</span>}
    </div>
  );
}
