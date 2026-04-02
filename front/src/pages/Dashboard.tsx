import { useNavigate } from "react-router";
import { useState, useEffect } from "react";
import { Box, Card, CardContent, Typography, Grid, Button, Stack, Avatar, CircularProgress } from "@mui/material";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell,
} from "recharts";
import { CheckCircle, Cancel, AccessTime, ListAlt, Insights, TrendingUp, CloudUpload, School, PlayArrow } from "@mui/icons-material";
import { TextField, MenuItem } from "@mui/material";
import {
  fetchSummary, fetchDistribution, fetchModels,
  fetchByMonth, fetchAvgScoreByRegion, fetchAvgScoreByDirection,
  fetchAvailableYears,
  type AnalyticsSummary, type DistributionBin, type ModelsResponse,
  type MonthStat, type RegionScoreStat, type DirectionScoreStat,
} from "../data/api";

function fmt(n: number) {
  if (n >= 1e9) return `₸${(n / 1e9).toFixed(1)} млрд`;
  if (n >= 1e6) return `₸${(n / 1e6).toFixed(0)} млн`;
  return `₸${n.toLocaleString("ru")}`;
}

function KpiCard({ label, value, sub, color }: { label: string; value: string; sub?: string; color?: string }) {
  return (
    <Card>
      <CardContent sx={{ p: 3 }}>
        <Typography variant="caption" fontWeight={600} textTransform="uppercase" letterSpacing={0.5}>{label}</Typography>
        <Typography variant="h4" fontFamily="'JetBrains Mono', monospace" mt={0.5} color={color || "text.primary"}>{value}</Typography>
        {sub && <Typography variant="caption" mt={0.5} display="block">{sub}</Typography>}
      </CardContent>
    </Card>
  );
}

function ChartCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Card>
      <CardContent sx={{ p: 3 }}>
        <Typography variant="subtitle2" mb={2}>{title}</Typography>
        {children}
      </CardContent>
    </Card>
  );
}

export function Dashboard() {
  const navigate = useNavigate();
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [dist, setDist] = useState<DistributionBin[]>([]);
  const [models, setModels] = useState<ModelsResponse | null>(null);
  const [monthData, setMonthData] = useState<MonthStat[]>([]);
  const [regionData, setRegionData] = useState<RegionScoreStat[]>([]);
  const [directionData, setDirectionData] = useState<DirectionScoreStat[]>([]);
  const [loading, setLoading] = useState(true);
  const [availableYears, setAvailableYears] = useState<number[]>([]);
  const [selectedYear, setSelectedYear] = useState<number | "">("");

  useEffect(() => {
    Promise.allSettled([
      fetchSummary(),
      fetchDistribution(10),
      fetchModels(),
      fetchByMonth(),
      fetchAvgScoreByRegion(),
      fetchAvgScoreByDirection(),
      fetchAvailableYears(),
    ]).then(([s, d, m, bm, rg, dr, yrs]) => {
      if (s.status === "fulfilled") setSummary(s.value);
      if (d.status === "fulfilled") setDist(d.value.bins);
      if (m.status === "fulfilled") setModels(m.value);
      if (bm.status === "fulfilled") setMonthData(bm.value.months);
      if (rg.status === "fulfilled") setRegionData(rg.value.regions);
      if (dr.status === "fulfilled") setDirectionData(dr.value.directions);
      if (yrs.status === "fulfilled") setAvailableYears(yrs.value.years);
      setLoading(false);
    });
  }, []);

  function handleYearChange(year: number | "") {
    setSelectedYear(year);
    const y = year || undefined;
    fetchByMonth(y).then((res) => setMonthData(res.months)).catch(() => {});
  }

  if (loading) return (
    <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", height: "60vh" }}>
      <CircularProgress color="primary" />
    </Box>
  );

  const total = summary?.total ?? 0;
  const high = summary?.high ?? 0;
  const medium = summary?.medium ?? 0;
  const low = summary?.low ?? 0;
  const meanScore = summary?.mean_score ?? 0;
  const activeModel = models?.models?.find((m) => m.is_active);
  const hasModel = !!activeModel;
  const hasData = total > 0;

  const statuses = [
    { icon: <CheckCircle />, label: "Высокий (HIGH)", count: high, color: "#22c55e", bg: "#f0fdf4" },
    { icon: <AccessTime />, label: "Средний (MEDIUM)", count: medium, color: "#f59e0b", bg: "#fffbeb" },
    { icon: <Cancel />, label: "Низкий (LOW)", count: low, color: "#ef4444", bg: "#fef2f2" },
  ];

  const monthNames = ["Янв", "Фев", "Мар", "Апр", "Май", "Июн", "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек"];
  const monthChartData = monthData.map((m) => {
    const [y, mo] = m.month.split("-");
    return { name: monthNames[parseInt(mo, 10) - 1] + " " + y, count: m.count };
  });

  const regionChartData = regionData.map((r) => ({
    name: r.region.length > 20 ? r.region.slice(0, 20) + "…" : r.region,
    fullName: r.region,
    avgScore: r.avg_score,
    count: r.count,
  })).slice(0, 15);

  const directionChartData = directionData.map((d) => ({
    name: d.direction.length > 25 ? d.direction.slice(0, 25) + "…" : d.direction,
    fullName: d.direction,
    avgScore: d.avg_score,
    count: d.count,
  }));

  return (
    <Box sx={{ p: { xs: 2.5, md: 4 } }}>
      <Stack spacing={3}>
        {/* Getting started banner */}
        {(!hasModel || !hasData) && (
          <Card sx={{ bgcolor: "#fffbeb", borderColor: "#fde68a" }}>
            <CardContent sx={{ p: 3 }}>
              <Typography variant="subtitle2" mb={1.5}>
                {!hasModel ? "Начало работы" : "Система готова к скорингу"}
              </Typography>
              <Stack spacing={1.5}>
                {!hasModel && (
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
                    <Avatar sx={{ bgcolor: "#fef3c7", color: "#f59e0b", width: 32, height: 32 }}>
                      <School sx={{ fontSize: 18 }} />
                    </Avatar>
                    <Box sx={{ flex: 1 }}>
                      <Typography variant="body2" fontWeight={600}>Шаг 1: Обучите модель</Typography>
                      <Typography variant="caption">Загрузите исторические данные (Excel/CSV) с решёнными заявками для обучения AI-модели</Typography>
                    </Box>
                    <Button variant="outlined" size="small" onClick={() => navigate("/models")}>
                      Обучить модель
                    </Button>
                  </Box>
                )}
                {hasModel && !hasData && (
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
                    <Avatar sx={{ bgcolor: "#dcfce7", color: "#22c55e", width: 32, height: 32 }}>
                      <PlayArrow sx={{ fontSize: 18 }} />
                    </Avatar>
                    <Box sx={{ flex: 1 }}>
                      <Typography variant="body2" fontWeight={600}>Загрузите заявки для оценки</Typography>
                      <Typography variant="caption">Модель <b>{activeModel?.version}</b> готова — загрузите файл с заявками для скоринга</Typography>
                    </Box>
                    <Button variant="outlined" size="small" onClick={() => navigate("/scoring")}>
                      Скоринг
                    </Button>
                  </Box>
                )}
              </Stack>
            </CardContent>
          </Card>
        )}

        {/* KPIs */}
        <Grid container spacing={2}>
          {[
            { label: "Всего оценено", value: total.toLocaleString("ru"), sub: "заявок в системе" },
            { label: "Средний балл AI", value: meanScore ? meanScore.toFixed(1) : "—", sub: "по всем заявкам", color: "#f59e0b" },
            { label: "Мин / Макс балл", value: `${summary?.min_score ?? "—"} / ${summary?.max_score ?? "—"}`, sub: "диапазон оценок" },
            { label: "Моделей обучено", value: String(models?.total ?? 0), sub: activeModel ? `Активная: ${activeModel.version}` : "нет активной", color: "#22c55e" },
          ].map((kpi) => (
            <Grid size={{ xs: 6, md: 3 }} key={kpi.label}>
              <KpiCard {...kpi} />
            </Grid>
          ))}
        </Grid>

        {/* Status row */}
        <Grid container spacing={2}>
          {statuses.map(({ icon, label, count, color, bg }) => (
            <Grid size={{ xs: 12, md: 4 }} key={label}>
              <Card>
                <CardContent sx={{ p: 2.5, display: "flex", alignItems: "center", gap: 2 }}>
                  <Avatar sx={{ bgcolor: bg, color, width: 40, height: 40 }}>{icon}</Avatar>
                  <Box>
                    <Typography variant="h6" fontFamily="'JetBrains Mono', monospace" color={color}>{count.toLocaleString("ru")}</Typography>
                    <Typography variant="caption">{label}</Typography>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>

        {/* Applications by month */}
        {monthChartData.length > 0 && (
          <ChartCard title="">
            <Stack direction="row" justifyContent="space-between" alignItems="center" mb={2} mt={-1}>
              <Typography variant="subtitle2">Заявки по месяцам</Typography>
              <TextField
                select size="small" label="Год"
                value={selectedYear}
                onChange={(e) => handleYearChange(e.target.value === "" ? "" : Number(e.target.value))}
                sx={{ minWidth: 120 }}
              >
                <MenuItem value="">Все годы</MenuItem>
                {availableYears.map((y) => <MenuItem key={y} value={y}>{y}</MenuItem>)}
              </TextField>
            </Stack>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={monthChartData} margin={{ top: 4, right: 12, left: -12, bottom: 4 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                <XAxis dataKey="name" tick={{ fontSize: 11, fill: "#9ca3af" }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 10, fill: "#9ca3af" }} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, border: "1px solid #e5e7eb" }} formatter={(v: number) => [v.toLocaleString("ru"), "Заявок"]} />
                <Bar dataKey="count" name="Заявок" radius={[4, 4, 0, 0]} barSize={28} fill="#3b82f6" />
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>
        )}

        {/* Avg score by region + Avg score by direction */}
        <Grid container spacing={2.5}>
          <Grid size={{ xs: 12, md: 6 }}>
            <ChartCard title="Средний балл по регионам">
              {regionChartData.length > 0 ? (
                <ResponsiveContainer width="100%" height={Math.max(280, regionChartData.length * 30)}>
                  <BarChart data={regionChartData} layout="vertical" margin={{ top: 4, right: 60, left: 4, bottom: 4 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" horizontal={false} />
                    <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 10, fill: "#9ca3af" }} axisLine={false} tickLine={false} />
                    <YAxis type="category" dataKey="name" width={150} tick={{ fontSize: 11, fill: "#374151" }} axisLine={false} tickLine={false} />
                    <Tooltip
                      formatter={(v: number, name: string) => [name === "Ср. балл" ? v : v.toLocaleString("ru"), name]}
                      labelFormatter={(_: string, payload: any[]) => payload?.[0]?.payload?.fullName || _}
                      contentStyle={{ fontSize: 12, borderRadius: 8, border: "1px solid #e5e7eb" }}
                    />
                    <Bar dataKey="avgScore" name="Ср. балл" radius={[0, 6, 6, 0]} barSize={18}
                      label={{ position: "right", fontSize: 11, fill: "#6b7280", formatter: (v: number) => v.toFixed(1) }}>
                      {regionChartData.map((r, i) => (
                        <Cell key={i} fill={r.avgScore >= 70 ? "#22c55e" : r.avgScore >= 40 ? "#f59e0b" : "#ef4444"} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <Typography variant="body2" color="text.secondary" textAlign="center" py={6}>Нет данных</Typography>
              )}
            </ChartCard>
          </Grid>
          <Grid size={{ xs: 12, md: 6 }}>
            <ChartCard title="Средний балл по направлениям">
              {directionChartData.length > 0 ? (
                <ResponsiveContainer width="100%" height={Math.max(280, directionChartData.length * 32)}>
                  <BarChart data={directionChartData} layout="vertical" margin={{ top: 4, right: 60, left: 4, bottom: 4 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" horizontal={false} />
                    <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 10, fill: "#9ca3af" }} axisLine={false} tickLine={false} />
                    <YAxis type="category" dataKey="name" width={170} tick={{ fontSize: 11, fill: "#374151" }} axisLine={false} tickLine={false} />
                    <Tooltip
                      formatter={(v: number, name: string) => [name === "Ср. балл" ? v : v.toLocaleString("ru"), name]}
                      labelFormatter={(_: string, payload: any[]) => payload?.[0]?.payload?.fullName || _}
                      contentStyle={{ fontSize: 12, borderRadius: 8, border: "1px solid #e5e7eb" }}
                    />
                    <Bar dataKey="avgScore" name="Ср. балл" radius={[0, 6, 6, 0]} barSize={18} fill="#3b82f6"
                      label={{ position: "right", fontSize: 11, fill: "#6b7280", formatter: (v: number) => v.toFixed(1) }}>
                      {directionChartData.map((d, i) => (
                        <Cell key={i} fill={d.avgScore >= 70 ? "#22c55e" : d.avgScore >= 40 ? "#f59e0b" : "#ef4444"} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <Typography variant="body2" color="text.secondary" textAlign="center" py={6}>Нет данных</Typography>
              )}
            </ChartCard>
          </Grid>
        </Grid>

        {/* Score distribution chart */}
        <Grid container spacing={2.5}>
          <Grid size={{ xs: 12, md: 8 }}>
            <ChartCard title="Распределение AI-баллов">
              {dist.length > 0 ? (
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={dist} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                    <XAxis dataKey="range" tick={{ fontSize: 10, fill: "#9ca3af" }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fontSize: 10, fill: "#9ca3af" }} axisLine={false} tickLine={false} />
                    <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, border: "1px solid #e5e7eb" }} formatter={(v: number) => [v.toLocaleString("ru"), "Заявок"]} />
                    <Bar dataKey="count" radius={[4, 4, 0, 0]} barSize={28}>
                      {dist.map((e, i) => {
                        const lo = parseFloat(e.range);
                        const c = lo >= 70 ? "#22c55e" : lo >= 40 ? "#f59e0b" : "#ef4444";
                        return <Cell key={i} fill={c} />;
                      })}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <Typography variant="body2" color="text.secondary" textAlign="center" py={6}>Нет данных для отображения</Typography>
              )}
            </ChartCard>
          </Grid>
          <Grid size={{ xs: 12, md: 4 }}>
            <Card>
              <CardContent sx={{ p: 3 }}>
                <Typography variant="subtitle2" mb={2}>Распределение по категориям</Typography>
                <Stack spacing={1.5}>
                  {[
                    { label: "HIGH (70–100)", count: high, color: "#22c55e" },
                    { label: "MEDIUM (40–69)", count: medium, color: "#f59e0b" },
                    { label: "LOW (0–39)", count: low, color: "#ef4444" },
                  ].map(({ label, count, color }) => (
                    <Box key={label} sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
                      <Box sx={{ width: 8, height: 8, borderRadius: "50%", bgcolor: color, flexShrink: 0 }} />
                      <Typography variant="body2" flex={1}>{label}</Typography>
                      <Typography variant="body2" fontFamily="'JetBrains Mono'" fontWeight={700} color={color}>{count}</Typography>
                    </Box>
                  ))}
                </Stack>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        {/* Quick actions */}
        <Card sx={{ bgcolor: "#f0fdf4", borderColor: "#dcfce7" }}>
          <CardContent sx={{ p: 3 }}>
            <Typography variant="subtitle2" mb={2}>Быстрые действия</Typography>
            <Grid container spacing={1.5}>
              {[
                { icon: <ListAlt />, label: "Реестр заявок", sub: "Все оценённые заявки", to: "/registry", color: "#3b82f6" },
                { icon: <CloudUpload />, label: "Скоринг / Шаблон", sub: "Загрузить файл для оценки", to: "/scoring", color: "#22c55e" },
                { icon: <Insights />, label: "Исследование модели", sub: "Метрики и факторы", to: "/analytics", color: "#f59e0b" },
              ].map(({ icon, label, sub, to, color }) => (
                <Grid size={{ xs: 12, sm: 4 }} key={to}>
                  <Button
                    fullWidth variant="outlined" onClick={() => navigate(to)}
                    sx={{ justifyContent: "flex-start", gap: 1.5, py: 1.5, px: 2, borderRadius: 3, textTransform: "none", color: "text.primary", borderColor: "#e0e0e0", bgcolor: "white", "&:hover": { borderColor: "#22c55e", bgcolor: "white" } }}
                  >
                    <Avatar sx={{ bgcolor: `${color}18`, color, width: 36, height: 36 }}>{icon}</Avatar>
                    <Box textAlign="left">
                      <Typography variant="body2" fontWeight={600}>{label}</Typography>
                      <Typography variant="caption">{sub}</Typography>
                    </Box>
                  </Button>
                </Grid>
              ))}
            </Grid>
            <Box sx={{ mt: 2, p: 2, bgcolor: "rgba(255,255,255,0.7)", borderRadius: 2, border: "1px solid #dcfce7", display: "flex", gap: 1, alignItems: "flex-start" }}>
              <TrendingUp sx={{ fontSize: 14, color: "primary.main", mt: 0.3 }} />
              <Typography variant="caption" color="text.secondary">
                AI-модель оценила <b>{total.toLocaleString("ru")} заявок</b>.
                Итоговое решение остаётся за комиссией — модель только ранжирует и объясняет.
              </Typography>
            </Box>
          </CardContent>
        </Card>
      </Stack>
    </Box>
  );
}
