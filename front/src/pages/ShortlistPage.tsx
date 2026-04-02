import { useState, useEffect } from "react";
import { useNavigate } from "react-router";
import {
  Box, Card, CardContent, Typography, Button, Grid, Stack,
  Table, TableHead, TableBody, TableRow, TableCell, TableContainer,
  CircularProgress, Slider, Chip, TextField, MenuItem,
} from "@mui/material";
import { Download, TuneRounded, Warning } from "@mui/icons-material";
import { fetchShortlist, downloadExport, type ShortlistResponse } from "../data/api";
import { ScoreBadge } from "../components/ScoreBadge";

/** Краткий формат (для таблицы) */
function fmt(n: number) {
  if (n >= 1e9) return `₸${(n / 1e9).toFixed(1)} млрд`;
  if (n >= 1e6) return `₸${(n / 1e6).toFixed(1)} млн`;
  if (n >= 1e3) return `₸${(n / 1e3).toFixed(0)} тыс`;
  return `₸${n.toLocaleString("ru")}`;
}

/** Точный формат (для итого) */
function fmtExact(n: number) {
  return `₸${n.toLocaleString("ru", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

const CATEGORY_CHIP: Record<string, { color: "success" | "warning" | "error"; label: string }> = {
  HIGH: { color: "success", label: "HIGH" },
  MEDIUM: { color: "warning", label: "MEDIUM" },
  LOW: { color: "error", label: "LOW" },
};

export function ShortlistPage() {
  const navigate = useNavigate();
  const [minScore, setMinScore] = useState<number>(0);
  const [budget, setBudget] = useState<number>(0);
  const [maxBudget, setMaxBudget] = useState<number>(0);
  const [direction, setDirection] = useState("");
  const [subsidyType, setSubsidyType] = useState("");
  const [region, setRegion] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ShortlistResponse | null>(null);
  const [regions, setRegions] = useState<string[]>([]);
  const [directions, setDirections] = useState<string[]>([]);
  const [subsidyTypes, setSubsidyTypes] = useState<string[]>([]);

  function budgetStep(max: number) {
    if (max > 1e9) return 10_000_000;
    if (max > 100e6) return 1_000_000;
    if (max > 1e6) return 100_000;
    return 10_000;
  }

  function ceilBudget(val: number) {
    const step = budgetStep(val);
    return Math.ceil(val / step) * step;
  }

  async function handleCalculate(
    ms: number = minScore,
    b: number = budget,
    dir = direction,
    sub = subsidyType,
    reg = region,
  ) {
    setLoading(true);
    try {
      const budgetParam = b > 0 ? b : undefined;
      const res = await fetchShortlist(
        budgetParam,
        undefined,
        reg || undefined,
        ms > 0 ? ms : undefined,
        "score",
        dir || undefined,
        sub || undefined,
      );
      setResult(res);
    } catch {
      /* silent */
    }
    setLoading(false);
  }


  // On mount: get totals, extract filter options
  useEffect(() => {
    (async () => {
      try {
        const full = await fetchShortlist(undefined, undefined, undefined, undefined, "score");
        if (full.total_cost > 0) {
          setMaxBudget(ceilBudget(full.total_cost));
        }
        const regionSet = new Set<string>();
        const directionSet = new Set<string>();
        const subsidySet = new Set<string>();
        for (const app of full.selected) {
          if (app.region && app.region.trim()) regionSet.add(app.region.trim());
          if (app.direction && app.direction.trim()) directionSet.add(app.direction.trim());
          if (app.subsidy_type && app.subsidy_type.trim()) subsidySet.add(app.subsidy_type.trim());
        }
        setRegions(Array.from(regionSet).sort());
        setDirections(Array.from(directionSet).sort());
        setSubsidyTypes(Array.from(subsidySet).sort());
      } catch { /* silent */ }
      handleCalculate(0, 0, "", "", "");
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const selected = result?.selected ?? [];
  const rows = selected.map((app: any, i: number) => ({ ...app, rank: i + 1 }));
  const notIncluded = (result?.total_in_db ?? 0) - (result?.selected_count ?? 0);

  return (
    <Box sx={{ p: { xs: 2.5, md: 4 } }}>
      <Box mb={3}>
        <Typography variant="h5">Формирование шорт-листа</Typography>
        <Typography variant="body2" color="text.secondary">
          Отбор заявок по ключевым параметрам и лимиту бюджета.
        </Typography>
      </Box>

      <Grid container spacing={3}>
        {/* ══════ LEFT PANEL ══════ */}
        <Grid size={{ xs: 12, md: 4, lg: 3.5 }}>
          <Stack spacing={2.5}>
            <Card>
              <CardContent sx={{ p: 3 }}>
                <Stack direction="row" spacing={1} alignItems="center" mb={3}>
                  <TuneRounded sx={{ fontSize: 18, color: "text.secondary" }} />
                  <Typography variant="subtitle2">Параметры отбора</Typography>
                </Stack>

                {/* Region */}
                <TextField
                  select fullWidth size="small" label="Область"
                  value={region}
                  onChange={(e) => {
                    setRegion(e.target.value);
                    handleCalculate(minScore, budget, direction, subsidyType, e.target.value);
                  }}
                  sx={{ mb: 2 }}
                >
                  <MenuItem value="">Все области</MenuItem>
                  {regions.map((r) => <MenuItem key={r} value={r}>{r}</MenuItem>)}
                </TextField>

                {/* Direction */}
                <TextField
                  select fullWidth size="small" label="Направление"
                  value={direction}
                  onChange={(e) => {
                    setDirection(e.target.value);
                    handleCalculate(minScore, budget, e.target.value, subsidyType, region);
                  }}
                  sx={{ mb: 2 }}
                >
                  <MenuItem value="">Все направления</MenuItem>
                  {directions.map((d) => <MenuItem key={d} value={d}>{d}</MenuItem>)}
                </TextField>

                {/* Subsidy type */}
                <TextField
                  select fullWidth size="small" label="Вид субсидии"
                  value={subsidyType}
                  onChange={(e) => {
                    setSubsidyType(e.target.value);
                    handleCalculate(minScore, budget, direction, e.target.value, region);
                  }}
                  sx={{ mb: 2.5 }}
                >
                  <MenuItem value="">Все виды</MenuItem>
                  {subsidyTypes.map((s) => <MenuItem key={s} value={s}>{s}</MenuItem>)}
                </TextField>

                {/* Min score — slider */}
                <Typography variant="caption" color="text.secondary" fontWeight={600}>
                  Мин. балл AI
                </Typography>
                <Slider
                  value={minScore}
                  onChange={(_, v) => setMinScore(v as number)}
                  onChangeCommitted={(_, v) => {
                    const ms = v as number;
                    setMinScore(ms);
                    handleCalculate(ms, budget, direction, subsidyType, region);
                  }}
                  min={0}
                  max={100}
                  step={1}
                  valueLabelDisplay="auto"
                  sx={{ mt: 1, mb: 0.5, color: "#8b5cf6" }}
                />
                <Typography variant="body2" fontWeight={700} mb={2.5}>
                  {minScore > 0 ? `≥ ${minScore} баллов` : "Без ограничений"}
                </Typography>

                {/* Budget slider */}
                <Typography variant="caption" color="text.secondary" fontWeight={600}>
                  Лимит бюджета
                </Typography>
                <Slider
                  value={budget}
                  onChange={(_, v) => setBudget(v as number)}
                  onChangeCommitted={(_, v) => {
                    const b = v as number;
                    setBudget(b);
                    handleCalculate(minScore, b, direction, subsidyType, region);
                  }}
                  min={0}
                  max={maxBudget || 1}
                  step={budgetStep(maxBudget)}
                  disabled={maxBudget === 0}
                  sx={{ mt: 1, mb: 0.5, color: "#3b82f6" }}
                />
                <Typography variant="body2" fontWeight={700} mb={0.5}>
                  {budget > 0 ? fmt(budget) : "Без ограничений"}
                </Typography>
              </CardContent>
            </Card>

            {/* Summary */}
            {result && (
              <Card>
                <CardContent sx={{ p: 3 }}>
                  <Typography variant="subtitle2" mb={2}>Итого</Typography>
                  <Stack spacing={1.5}>
                    <Stack direction="row" justifyContent="space-between">
                      <Typography variant="body2" color="text.secondary">В шорт-листе</Typography>
                      <Typography variant="body2" fontWeight={700} fontFamily="'JetBrains Mono'">
                        {result.selected_count}
                      </Typography>
                    </Stack>
                    <Stack direction="row" justifyContent="space-between" alignItems="baseline">
                      <Typography variant="body2" color="text.secondary">Общая сумма</Typography>
                      <Typography variant="body2" fontWeight={700} fontFamily="'JetBrains Mono'" color="#22c55e">
                        {fmtExact(result.total_cost)}
                      </Typography>
                    </Stack>
                    <Stack direction="row" justifyContent="space-between">
                      <Typography variant="body2" color="text.secondary">Требуют проверки</Typography>
                      <Typography variant="body2" fontWeight={700} fontFamily="'JetBrains Mono'" color="#f59e0b">
                        {result.review_required_count}
                      </Typography>
                    </Stack>
                    <Stack direction="row" justifyContent="space-between">
                      <Typography variant="body2" color="text.secondary">Не вошли</Typography>
                      <Typography variant="body2" fontWeight={700} fontFamily="'JetBrains Mono'" color="text.secondary">
                        {notIncluded}
                      </Typography>
                    </Stack>
                  </Stack>
                </CardContent>
              </Card>
            )}
          </Stack>
        </Grid>

        {/* ══════ RIGHT PANEL — TABLE ══════ */}
        <Grid size={{ xs: 12, md: 8, lg: 8.5 }}>
          <Card sx={{ height: "100%" }}>
            {/* Table header */}
            <Box sx={{ px: 3, py: 2, borderBottom: "1px solid #f0f0f0", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <Typography variant="subtitle2">
                {loading ? "Загрузка…" : `${selected.length} заявок включено`}
              </Typography>
              <Button size="small" startIcon={<Download />} onClick={() => downloadExport()} disabled={!result}>
                Excel
              </Button>
            </Box>

            {loading ? (
              <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", py: 12 }}>
                <CircularProgress />
              </Box>
            ) : (
              <TableContainer sx={{ maxHeight: "calc(100vh - 220px)" }}>
                <Table stickyHeader size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell width={50} sx={{ fontWeight: 700, textTransform: "uppercase", fontSize: "0.7rem", letterSpacing: 0.5 }}>Ранг</TableCell>
                      <TableCell width={60} sx={{ fontWeight: 700, textTransform: "uppercase", fontSize: "0.7rem", letterSpacing: 0.5 }}>Балл</TableCell>
                      <TableCell width={80} sx={{ fontWeight: 700, textTransform: "uppercase", fontSize: "0.7rem", letterSpacing: 0.5 }}>Категория</TableCell>
                      <TableCell sx={{ fontWeight: 700, textTransform: "uppercase", fontSize: "0.7rem", letterSpacing: 0.5 }}>Область</TableCell>
                      <TableCell sx={{ fontWeight: 700, textTransform: "uppercase", fontSize: "0.7rem", letterSpacing: 0.5 }}>Направление</TableCell>
                      <TableCell sx={{ fontWeight: 700, textTransform: "uppercase", fontSize: "0.7rem", letterSpacing: 0.5 }}>Вид субсидии</TableCell>
                      <TableCell align="right" sx={{ fontWeight: 700, textTransform: "uppercase", fontSize: "0.7rem", letterSpacing: 0.5 }}>Норматив</TableCell>
                      <TableCell align="right" sx={{ fontWeight: 700, textTransform: "uppercase", fontSize: "0.7rem", letterSpacing: 0.5 }}>Причитающая сумма</TableCell>
                      <TableCell width={50} sx={{ fontWeight: 700, textTransform: "uppercase", fontSize: "0.7rem", letterSpacing: 0.5 }}>Проверка</TableCell>
                      <TableCell width={85} sx={{ fontWeight: 700, textTransform: "uppercase", fontSize: "0.7rem", letterSpacing: 0.5 }}>Дата</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {rows.map((app: any) => {
                      const cat = CATEGORY_CHIP[app.category] ?? { color: "default" as const, label: app.category };
                      const date = app.created_at ? new Date(app.created_at).toLocaleDateString("ru", { day: "2-digit", month: "2-digit", year: "2-digit" }) : "—";
                      const reviewRequired = app.review_required;
                      return (
                        <TableRow
                          key={app.id ?? app.rank}
                          hover
                          sx={{ cursor: app.id ? "pointer" : "default", "&:hover": { bgcolor: "#f0fdf4" } }}
                          onClick={() => app.id && navigate(`/app/${app.id}`)}
                        >
                          <TableCell sx={{ fontFamily: "'JetBrains Mono'", color: "text.secondary", fontWeight: 500 }}>{app.rank}</TableCell>
                          <TableCell><ScoreBadge score={Math.round(app.score)} size="sm" /></TableCell>
                          <TableCell><Chip label={cat.label} color={cat.color} size="small" variant="outlined" /></TableCell>
                          <TableCell sx={{ fontWeight: 500 }}>{app.region || "—"}</TableCell>
                          <TableCell sx={{ color: "text.secondary" }}>{app.direction || "—"}</TableCell>
                          <TableCell sx={{ color: "text.secondary", maxWidth: 200 }}>
                            <Typography variant="body2" noWrap title={app.subsidy_type}>{app.subsidy_type || "—"}</Typography>
                          </TableCell>
                          <TableCell align="right" sx={{ fontFamily: "'JetBrains Mono'", fontWeight: 600 }}>
                            {(app.normative ?? 0).toLocaleString("ru", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                          </TableCell>
                          <TableCell align="right" sx={{ fontFamily: "'JetBrains Mono'", fontWeight: 600 }}>
                            {(app.amount ?? 0).toLocaleString("ru", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                          </TableCell>
                          <TableCell>
                            {reviewRequired && <Warning sx={{ fontSize: 16, color: "#f59e0b" }} titleAccess="Рекомендуется доп. проверка" />}
                          </TableCell>
                          <TableCell sx={{ fontFamily: "'JetBrains Mono'", color: "text.secondary" }}>{date}</TableCell>
                        </TableRow>
                      );
                    })}
                    {rows.length === 0 && (
                      <TableRow>
                        <TableCell colSpan={10} sx={{ textAlign: "center", py: 8 }}>
                          <Typography variant="body2" color="text.secondary">
                            Нет заявок, подходящих под заданные параметры
                          </Typography>
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}

