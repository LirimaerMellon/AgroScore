export function ScoreBadge({ score, size = "md" }: { score: number; size?: "sm" | "md" | "lg" }) {
  const color =
    score >= 70 ? { bg: "#dcfce7", text: "#16a34a", border: "#bbf7d0" } :
    score >= 40 ? { bg: "#fef9c3", text: "#b45309", border: "#fde68a" } :
    score >= 20 ? { bg: "#ffedd5", text: "#c2410c", border: "#fed7aa" } :
    { bg: "#fee2e2", text: "#dc2626", border: "#fecaca" };

  const sizeClass = size === "lg" ? "text-[14px] px-3 py-1" : size === "sm" ? "text-[11px] px-2 py-0.5" : "text-[12px] px-2.5 py-0.5";

  return (
    <span
      className={`inline-flex items-center justify-center rounded-md font-mono font-semibold border ${sizeClass}`}
      style={{ backgroundColor: color.bg, color: color.text, borderColor: color.border }}
    >
      {score}
    </span>
  );
}

export function ScoreLabel({ score }: { score: number }) {
  const label = score >= 70 ? "Высокий" : score >= 40 ? "Средний" : score >= 20 ? "Низкий" : "Критический";
  const color = score >= 70 ? "#16a34a" : score >= 40 ? "#b45309" : score >= 20 ? "#c2410c" : "#dc2626";
  return <span style={{ color }} className="text-[12px] font-medium">{label}</span>;
}
