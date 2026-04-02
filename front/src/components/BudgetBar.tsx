function fmt(n: number) {
  if (n >= 1e9) return `₸${(n / 1e9).toFixed(1)} млрд`;
  if (n >= 1e6) return `₸${(n / 1e6).toFixed(0)} млн`;
  return `₸${n.toLocaleString("ru")}`;
}

export function BudgetBar({ used, total }: { used: number; total: number }) {
  const pct = Math.min((used / total) * 100, 100);
  const color = pct > 90 ? "#ef4444" : pct > 70 ? "#f59e0b" : "#22c55e";

  return (
    <div className="flex flex-col gap-2">
      <div className="flex justify-between text-[12px] text-gray-500">
        <span>Использовано</span>
        <span className="font-semibold" style={{ color }}>{pct.toFixed(1)}%</span>
      </div>
      <div className="h-2.5 rounded-full bg-gray-100 overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
      <div className="flex justify-between text-[12px] font-medium">
        <span style={{ color }}>{fmt(used)}</span>
        <span className="text-gray-400">{fmt(total)}</span>
      </div>
    </div>
  );
}
