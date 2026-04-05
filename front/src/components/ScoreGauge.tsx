export function ScoreGauge({ score, size = 160, category }: {
  score: number; size?: number; category?: string;
}) {
  const r = (size - 24) / 2;
  const cx = size / 2;
  const cy = size / 2;
  const circ = 2 * Math.PI * r;
  const filled = (score / 100) * circ;
  const offset = circ - filled;

  const color = category
    ? (category === "HIGH" ? "#22c55e" : category === "MEDIUM" ? "#f59e0b" : "#ef4444")
    : (score >= 71 ? "#22c55e" : score >= 31 ? "#f59e0b" : "#ef4444");

  const label = category
    ? (category === "HIGH" ? "Высокий приоритет" : category === "MEDIUM" ? "Средний приоритет" : "Низкий приоритет")
    : (score >= 71 ? "Высокий приоритет" : score >= 31 ? "Средний приоритет" : "Низкий приоритет");

  return (
    <div className="flex flex-col items-center gap-3">
      <svg width={size} height={size}>
        <circle cx={cx} cy={cy} r={r} fill="none" stroke="#f1f5f9" strokeWidth="12" />
        <circle
          cx={cx} cy={cy} r={r} fill="none"
          stroke={color} strokeWidth="12" strokeLinecap="round"
          strokeDasharray={circ} strokeDashoffset={offset}
          transform={`rotate(-90 ${cx} ${cy})`}
          style={{ transition: "stroke-dashoffset 1s ease" }}
        />
        <text x={cx} y={cy - 8} textAnchor="middle" dominantBaseline="middle"
          style={{ fontFamily: "JetBrains Mono, monospace", fontSize: size * 0.22, fontWeight: 700, fill: "#111827" }}>
          {score}
        </text>
        <text x={cx} y={cy + size * 0.16} textAnchor="middle" dominantBaseline="middle"
          style={{ fontFamily: "Inter, sans-serif", fontSize: size * 0.09, fill: "#9ca3af" }}>
          из 100
        </text>
      </svg>
      <span className="text-[13px] font-semibold px-3 py-1 rounded-full"
        style={{ backgroundColor: `${color}18`, color }}>
        {label}
      </span>
    </div>
  );
}
