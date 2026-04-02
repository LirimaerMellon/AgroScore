import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Cell, ReferenceLine, ResponsiveContainer } from "recharts";

interface ShapEntry {
  feature: string;
  display_name?: string;
  value: number;
  shap_value?: number;
  importance?: number;
  direction?: string;
}

interface Props { factors: ShapEntry[]; }

export function ShapWaterfall({ factors }: Props) {
  if (!factors || factors.length === 0) {
    return <div className="text-center text-gray-400 py-8 text-sm">Нет данных SHAP</div>;
  }

  const data = factors.map((f) => {
    const sv = f.shap_value ?? (f.direction === "negative" ? -(f.importance ?? 0) : (f.importance ?? 0));
    const color = sv >= 0 ? "#22c55e" : "#ef4444";
    const name = f.display_name || f.feature;
    return { name, value: Number(sv.toFixed(3)), color, display: `значение: ${f.value}` };
  });

  const allVals = data.map((d) => d.value);
  const lo = Math.min(0, ...allVals) - 0.05;
  const hi = Math.max(0, ...allVals) + 0.05;

  return (
    <ResponsiveContainer width="100%" height={Math.max(260, data.length * 40 + 40)}>
      <BarChart data={data} layout="vertical" margin={{ top: 4, right: 52, left: 4, bottom: 4 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" horizontal={false} />
        <XAxis
          type="number" domain={[lo, hi]}
          tick={{ fontSize: 11, fill: "#9ca3af", fontFamily: "Inter" }}
          axisLine={{ stroke: "#e5e7eb" }} tickLine={false}
        />
        <YAxis
          type="category" dataKey="name" width={200}
          tick={{ fontSize: 12, fill: "#374151", fontFamily: "Inter" }}
          axisLine={false} tickLine={false}
        />
        <Tooltip
          formatter={(value: number, _: string, props: { payload: { display: string } }) => [
            `${value > 0 ? "+" : ""}${value}  —  ${props.payload.display}`,
            "SHAP вклад",
          ]}
          contentStyle={{ fontFamily: "Inter", fontSize: 12, borderRadius: 8, border: "1px solid #e5e7eb", boxShadow: "0 4px 16px rgba(0,0,0,.08)" }}
          labelStyle={{ fontWeight: 600, color: "#111827" }}
        />
        <ReferenceLine x={0} stroke="#d1d5db" strokeWidth={1.5} />
        <Bar dataKey="value" radius={[0, 4, 4, 0]} barSize={22} label={{ position: "right", fontSize: 11, fill: "#6b7280", formatter: (v: number) => `${v > 0 ? "+" : ""}${v}` }}>
          {data.map((entry, i) => <Cell key={i} fill={entry.color} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
