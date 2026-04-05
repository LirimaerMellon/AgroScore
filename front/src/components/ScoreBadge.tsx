export function ScoreBadge({ score, size = "md", category }: {
  score: number; size?: "sm" | "md" | "lg"; category?: string;
}) {
  const color = category
    ? (category === "HIGH"
      ? { bg: "#dcfce7", text: "#16a34a", border: "#bbf7d0" }
      : category === "MEDIUM"
        ? { bg: "#fef9c3", text: "#b45309", border: "#fde68a" }
        : { bg: "#fee2e2", text: "#dc2626", border: "#fecaca" })
    : (score >= 71 ? { bg: "#dcfce7", text: "#16a34a", border: "#bbf7d0" } :
    score >= 31 ? { bg: "#fef9c3", text: "#b45309", border: "#fde68a" } :
    { bg: "#fee2e2", text: "#dc2626", border: "#fecaca" });

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

export function ScoreLabel({ score, category }: { score: number; category?: string }) {
  const label = category
    ? (category === "HIGH" ? "Высокий" : category === "MEDIUM" ? "Средний" : "Низкий")
    : (score >= 71 ? "Высокий" : score >= 31 ? "Средний" : "Низкий");
  const color = category
    ? (category === "HIGH" ? "#16a34a" : category === "MEDIUM" ? "#b45309" : "#dc2626")
    : (score >= 71 ? "#16a34a" : score >= 31 ? "#b45309" : "#dc2626");
  return <span style={{ color }} className="text-[12px] font-medium">{label}</span>;
}
