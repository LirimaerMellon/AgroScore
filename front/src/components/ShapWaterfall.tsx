import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell, ReferenceLine, ResponsiveContainer } from "recharts";
import { Box } from "@mui/material";
import { featureDisplayName } from "../data/featureNames";

export interface ShapEntry {
  feature: string;
  display_name?: string;
  value?: number;
  shap_value?: number;
  score_points?: number;
  shap_points?: number;
  contribution_pct?: number;
  combo_label?: string;
  importance?: number;
  direction?: string;
}

export interface ShapWaterfallProps {
  factors: ShapEntry[];
  baseScore?: number;
  predictedScore?: number;
  /** Максимум именованных баров (остальные схлопнутся в «Остальные»). По умолчанию 5. */
  maxBars?: number;
  /** Показать все факторы без схлопывания (для модалки). */
  showAll?: boolean;
  /** Сумма SHAP-значений факторов за пределами top-N (из API rest.shap_points). */
  restShapPoints?: number;
  /** Количество факторов за пределами top-N (из API rest.count). */
  restCount?: number;
}

interface BarItem {
  name: string;
  shortName: string;
  value: number;
  color: string;
  display: string;
  isOthers?: boolean;
}

function buildBars(
  factors: ShapEntry[],
  maxBars: number,
  showAll: boolean,
  restShapPoints?: number,
  restCount?: number,
): BarItem[] {
  // Берём score_points / shap_points / shap_value, округляем до целых
  const sorted = [...factors]
    .map((f) => ({ ...f, pts: Math.round(f.shap_points ?? f.score_points ?? f.shap_value ?? 0) }))
    .filter((f) => f.pts !== 0)  // Убираем нулевые факторы
    .sort((a, b) => Math.abs(b.pts) - Math.abs(a.pts));

  const limit = showAll ? sorted.length : maxBars;
  const top = sorted.slice(0, limit);
  const internalRest = sorted.slice(limit);

  // Цвета: зелёный — повышает балл, красный — снижает
  const bars: BarItem[] = top.map((f) => {
    const label = featureDisplayName(f.display_name || f.feature);
    return {
      name: label,
      shortName: label,
      value: f.pts,
      color: f.pts > 0 ? "#22c55e" : "#ef4444",
      display: "",
    };
  });

  // Остальные: объединяем внутренние (из factors за пределами limit) и внешние (rest из API)
  const internalRestSum = internalRest.reduce((s, f) => s + f.pts, 0);
  const internalRestCount = internalRest.length;
  const externalRestSum = restShapPoints ?? 0;
  const externalRestCount = restCount ?? 0;

  const totalRestSum = internalRestSum + externalRestSum;
  const totalRestCount = internalRestCount + externalRestCount;

  if (totalRestCount > 0 && totalRestSum !== 0) {
    bars.push({
      name: `Остальные (${totalRestCount})`,
      shortName: `${totalRestCount} факторов`,
      value: totalRestSum,
      color: totalRestSum > 0 ? "#86efac" : "#fca5a5",
      display: `${totalRestCount} факторов суммарно`,
      isOthers: true,
    });
  }

  return bars;
}

export function ShapWaterfall({
  factors, baseScore, predictedScore, maxBars = 5, showAll = false,
  restShapPoints, restCount,
}: ShapWaterfallProps) {
  if (!factors || factors.length === 0) {
    return <Box sx={{ textAlign: "center", color: "#9ca3af", py: 4, fontSize: "0.875rem" }}>Нет данных SHAP</Box>;
  }

  const data = buildBars(factors, maxBars, showAll, restShapPoints, restCount);

  if (data.length === 0) {
    return <Box sx={{ textAlign: "center", color: "#9ca3af", py: 4, fontSize: "0.875rem" }}>Все факторы с нулевым вкладом</Box>;
  }

  const allVals = data.map((d) => d.value);
  const maxAbs = Math.max(Math.abs(Math.min(...allVals)), Math.abs(Math.max(...allVals)), 1);
  const pad = Math.max(1, Math.ceil(maxAbs * 0.25));
  const lo = Math.min(0, ...allVals) - pad;
  const hi = Math.max(0, ...allVals) + pad;

  const hasBreakdown = baseScore !== undefined && predictedScore !== undefined;

  // Сумма ВСЕХ баров (включая «Остальные») = полная сумма SHAP
  const totalShapSum = data.reduce((s, d) => s + d.value, 0);

  // Итог = base + сумма баров, ограничен [0, 100]
  const roundedBase = baseScore != null ? Math.round(baseScore) : 0;
  const computedTotal = Math.max(0, Math.min(100, roundedBase + totalShapSum));
  const isClamped = (roundedBase + totalShapSum) !== computedTotal;

  return (
    <Box>
      {hasBreakdown && (
        <Box sx={{
          display: "flex", gap: 1.5, mb: 2, p: 1.5, borderRadius: 2,
          bgcolor: "#f8fafc", flexWrap: "wrap",
          fontFamily: "'JetBrains Mono'", fontSize: "0.8125rem",
          alignItems: "center", justifyContent: "center",
        }}>
          <span>Типичный: <b>{roundedBase}</b></span>
          <span style={{ color: totalShapSum >= 0 ? "#22c55e" : "#ef4444" }}>
            {totalShapSum >= 0 ? "+" : ""}{totalShapSum}
          </span>
          <span>=</span>
          <span style={{ fontWeight: 700, fontSize: "0.9375rem" }}>
            Итого: {computedTotal} б.{isClamped && (computedTotal === 100 ? " (макс.)" : " (мин.)")}
          </span>
        </Box>
      )}

      <Box sx={{ minWidth: 0, width: "100%" }}>
        <ResponsiveContainer width="100%" height={Math.max(340, data.length * 64 + 70)}>
          <BarChart data={data} layout="vertical" margin={{ top: 4, right: 90, left: 4, bottom: 16 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" horizontal={false} />
            <XAxis
              type="number" domain={[lo, hi]}
              tick={{ fontSize: 11, fill: "#9ca3af", fontFamily: "'JetBrains Mono'" }}
              axisLine={{ stroke: "#e5e7eb" }} tickLine={false}
              tickFormatter={(v: number) => `${v > 0 ? "+" : ""}${v}`}
              label={{ value: "← снижает | повышает →", position: "insideBottom", offset: -6, fontSize: 10, fill: "#9ca3af" }}
            />
            <YAxis
              type="category" dataKey="name" width={200}
              tick={{ fontSize: 12, fill: "#374151", fontFamily: "Inter" }}
              axisLine={false} tickLine={false}
            />
            <Tooltip
              formatter={(value: number, _: string, props: { payload: BarItem }) => [
                `${value > 0 ? "+" : ""}${value} б.`,
                props.payload.isOthers ? "Остальные факторы" : `Вклад «${props.payload.shortName}»`,
              ]}
              contentStyle={{ fontFamily: "Inter", fontSize: 12, borderRadius: 8, border: "1px solid #e5e7eb", boxShadow: "0 4px 16px rgba(0,0,0,.08)" }}
              labelStyle={{ fontWeight: 600, color: "#111827" }}
            />
            <ReferenceLine x={0} stroke="#d1d5db" strokeWidth={1.5} />
            <Bar dataKey="value" radius={[0, 4, 4, 0]} barSize={32} label={{
              position: "right", fontSize: 13, fill: "#6b7280", fontFamily: "'JetBrains Mono'", fontWeight: 600,
              formatter: (v: number) => `${v > 0 ? "+" : ""}${v} б.`,
            }}>
              {data.map((entry, i) => (
                <Cell
                  key={i}
                  fill={entry.color}
                  fillOpacity={entry.isOthers ? 0.5 : 1}
                  strokeDasharray={entry.isOthers ? "4 2" : undefined}
                  stroke={entry.isOthers ? entry.color : undefined}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </Box>
    </Box>
  );
}
