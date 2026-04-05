import { useState, useEffect, useRef, useMemo } from "react";
import { useNavigate } from "react-router";
import {
  Box, Card, CardContent, Typography, Button, Grid, Stack,
  Table, TableHead, TableBody, TableRow, TableCell, TableContainer,
  CircularProgress, Slider, Chip, TextField, InputAdornment,
  ToggleButtonGroup, ToggleButton, Autocomplete, Alert,
} from "@mui/material";
import { Download, TuneRounded, Groups, AccountBalance, Warning } from "@mui/icons-material";
import { fetchShortlist, downloadExport, type ShortlistResponse } from "../data/api";
import { ScoreBadge } from "../components/ScoreBadge";
import { useModel } from "../data/ModelContext";

/* ── Форматирование ── */

function fmt(n: number) {
  if (n >= 1e9) return `₸${(n / 1e9).toFixed(1)} млрд`;
  if (n >= 1e6) return `₸${(n / 1e6).toFixed(1)} млн`;
  if (n >= 1e3) return `₸${(n / 1e3).toFixed(0)} тыс`;
  return `₸${n.toLocaleString("ru")}`;
}

function fmtExact(n: number) {
  return `₸${Math.round(n).toLocaleString("ru")}`;
}

const CATEGORY_CHIP: Record<string, { color: "success" | "warning" | "error"; label: string }> = {
  HIGH: { color: "success", label: "HIGH" },
  MEDIUM: { color: "warning", label: "MEDIUM" },
  LOW: { color: "error", label: "LOW" },
};

/* ── Бюджет: форматирование ── */

function formatBudgetDisplay(raw: string): string {
  // Убираем всё кроме цифр, запятой и точки
  let cleaned = raw.replace(/[^\d.,]/g, "");
  // Точку заменяем на запятую
  cleaned = cleaned.replace(/\./g, ",");
  // Берём только первую запятую
  const parts = cleaned.split(",");
  let intPart = parts[0] || "";
  const hasDecimal = parts.length > 1;
  let decPart = hasDecimal ? parts.slice(1).join("") : null;

  // Убираем ведущие нули (но оставляем одинокий «0»)
  intPart = intPart.replace(/^0+(\d)/, "$1");

  // Ограничиваем дробную часть 2 знаками
  if (decPart !== null) {
    decPart = decPart.replace(/\D/g, "").slice(0, 2);
  }

  // Разделяем тысячи пробелами
  intPart = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, " ");

  return decPart !== null ? `${intPart},${decPart}` : intPart;
}

function parseBudgetNumber(display: string): number {
  if (!display.trim()) return 0;
  const cleaned = display.replace(/\s/g, "").replace(",", ".");
  const num = parseFloat(cleaned);
  return isNaN(num) ? 0 : num;
}

/* ── Стратегия ── */
type Strategy = "more_applications" | "more_budget";

/* ══════════════════════════════════════════════════════ */

export function ShortlistPage() {
  const navigate = useNavigate();
  const { modelVersion } = useModel();

  /* Фильтры */
  const [minScore, setMinScore] = useState(0);
  const [budget, setBudget] = useState(0);
  const [budgetText, setBudgetText] = useState("");
  const [direction, setDirection] = useState<string | null>(null);
  const [subsidyType, setSubsidyType] = useState<string | null>(null);
  const [region, setRegion] = useState<string | null>(null);
  const [district, setDistrict] = useState<string | null>(null);
  const [strategy, setStrategy] = useState<Strategy>("more_applications");

  /* Данные */
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ShortlistResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [regions, setRegions] = useState<string[]>([]);
  const [directions, setDirections] = useState<string[]>([]);
  const [subsidyTypes, setSubsidyTypes] = useState<string[]>([]);
  const [districts, setDistricts] = useState<string[]>([]);

  const budgetTimerRef = useRef<ReturnType<typeof setTimeout>>();
  const abortRef = useRef<AbortController | null>(null);

  const budgetActive = budget > 0;

  /* ── Бюджетный ввод ── */
  function handleBudgetInput(raw: string) {
    const formatted = formatBudgetDisplay(raw);
    setBudgetText(formatted);
    const numVal = parseBudgetNumber(formatted);
    setBudget(numVal);

    // Если бюджет стал 0 — сбросить стратегию на дефолт
    const effectiveStrategy = numVal > 0 ? strategy : "more_applications";
    if (numVal <= 0 && strategy !== "more_applications") {
      setStrategy("more_applications");
    }

    if (budgetTimerRef.current) clearTimeout(budgetTimerRef.current);
    budgetTimerRef.current = setTimeout(() => {
      doFetch(minScore, numVal, direction, subsidyType, region, district, effectiveStrategy);
    }, 400);
  }

  /* ── Запрос к API ── */
  async function doFetch(
    ms = minScore, _b = budget,
    dir = direction, sub = subsidyType,
    reg = region, dist = district,
    strat: Strategy = strategy,
    signal?: AbortSignal,
  ) {
    if (!modelVersion) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetchShortlist(
        undefined,
        undefined,
        reg || undefined,
        ms > 0 ? ms : undefined,
        strat,
        dir || undefined,
        sub || undefined,
        dist || undefined,
        modelVersion,
        signal,
      );
      setResult(res);
    } catch (e: any) {
      if (e?.name === "AbortError") return;
      console.error("Shortlist fetch error:", e);
      setError(e?.message || "Ошибка загрузки шорт-листа");
    }
    setLoading(false);
  }

  /* ── Init + model change ── */
  useEffect(() => {
    // Не запрашиваем, пока модель не определена
    if (!modelVersion) {
      setResult(null);
      setLoading(false);
      return;
    }

    // Отменяем предыдущие запросы
    if (abortRef.current) abortRef.current.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    // Сброс фильтров при смене модели
    setMinScore(0);
    setDirection(null);
    setSubsidyType(null);
    setRegion(null);
    setDistrict(null);

    (async () => {
      setLoading(true);
      setError(null);
      try {
        // Один запрос — используем и для фильтров, и для таблицы
        const full = await fetchShortlist(
          undefined, undefined, undefined, undefined, strategy,
          undefined, undefined, undefined, modelVersion,
          controller.signal,
        );
        if (controller.signal.aborted) return;
        // Заполняем варианты фильтров из результата
        const rSet = new Set<string>(), dSet = new Set<string>();
        const sSet = new Set<string>(), dtSet = new Set<string>();
        for (const app of full.selected) {
          if (app.region?.trim()) rSet.add(app.region.trim());
          if (app.direction?.trim()) dSet.add(app.direction.trim());
          if (app.subsidy_type?.trim()) sSet.add(app.subsidy_type.trim());
          if (app.district?.trim()) dtSet.add(app.district.trim());
        }
        setRegions(Array.from(rSet).sort());
        setDirections(Array.from(dSet).sort());
        setSubsidyTypes(Array.from(sSet).sort());
        setDistricts(Array.from(dtSet).sort());
        setResult(full);
      } catch (e: any) {
        if (e?.name === "AbortError") return;
        console.error("Shortlist init error:", e);
        setError(e?.message || "Ошибка загрузки шорт-листа");
      }
      setLoading(false);
    })();
    return () => {
      controller.abort();
      if (budgetTimerRef.current) clearTimeout(budgetTimerRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [modelVersion]);

  /* ── Клиентский knapsack-отбор по бюджету ── */
  const { selected, totalCost, selectedCount, notIncluded, remaining } = useMemo(() => {
    const all = result?.selected ?? [];
    if (budget <= 0) {
      const cost = all.reduce((s, a) => s + (a.amount ?? 0), 0);
      return {
        selected: all.map((a, i) => ({ ...a, rank: i + 1 })),
        totalCost: cost,
        selectedCount: all.length,
        notIncluded: (result?.total_in_db ?? 0) - all.length,
        remaining: 0,
      };
    }

    let cumulative = 0;
    const picked: any[] = [];
    for (const app of all) {
      const cost = app.amount ?? 0;
      if (cumulative + cost <= budget) {
        cumulative += cost;
        picked.push({ ...app, rank: picked.length + 1 });
      }
    }
    return {
      selected: picked,
      totalCost: cumulative,
      selectedCount: picked.length,
      notIncluded: (result?.total_in_db ?? 0) - picked.length,
      remaining: budget - cumulative,
    };
  }, [result, budget]);

  const reviewCount = selected.filter((a: any) => a.review_required).length;

  /* ── Хелпер для пересчёта ── */
  function recalc(
    ms?: number, b?: number,
    dir?: string | null, sub?: string | null,
    reg?: string | null, dist?: string | null,
    strat?: Strategy,
  ) {
    doFetch(
      ms ?? minScore, b ?? budget,
      dir !== undefined ? dir : direction,
      sub !== undefined ? sub : subsidyType,
      reg !== undefined ? reg : region,
      dist !== undefined ? dist : district,
      strat ?? strategy,
    );
  }

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
                <Autocomplete
                  size="small"
                  options={regions}
                  value={region}
                  onChange={(_, v) => { setRegion(v); recalc(undefined, undefined, undefined, undefined, v); }}
                  renderInput={(params) => <TextField {...params} label="Область" placeholder="Поиск..." />}
                  noOptionsText="Не найдено"
                  clearOnBlur
                  sx={{ mb: 2 }}
                />

                {/* Direction */}
                <Autocomplete
                  size="small"
                  options={directions}
                  value={direction}
                  onChange={(_, v) => { setDirection(v); recalc(undefined, undefined, v); }}
                  renderInput={(params) => <TextField {...params} label="Направление" placeholder="Поиск..." />}
                  noOptionsText="Не найдено"
                  clearOnBlur
                  sx={{ mb: 2 }}
                />

                {/* Subsidy type */}
                <Autocomplete
                  size="small"
                  options={subsidyTypes}
                  value={subsidyType}
                  onChange={(_, v) => { setSubsidyType(v); recalc(undefined, undefined, undefined, v); }}
                  renderInput={(params) => <TextField {...params} label="Вид субсидии" placeholder="Поиск..." />}
                  noOptionsText="Не найдено"
                  clearOnBlur
                  slotProps={{ paper: { sx: { maxWidth: 420 } } }}
                  sx={{ mb: 2 }}
                />

                {/* District */}
                <Autocomplete
                  size="small"
                  options={districts}
                  value={district}
                  onChange={(_, v) => { setDistrict(v); recalc(undefined, undefined, undefined, undefined, undefined, v); }}
                  renderInput={(params) => <TextField {...params} label="Район" placeholder="Поиск..." />}
                  noOptionsText="Не найдено"
                  clearOnBlur
                  sx={{ mb: 2.5 }}
                />

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
                    recalc(ms);
                  }}
                  min={0} max={100} step={1}
                  valueLabelDisplay="auto"
                  sx={{ mt: 1, mb: 0.5, color: "#8b5cf6" }}
                />
                <Typography variant="body2" fontWeight={700} mb={2.5}>
                  {minScore > 0 ? `≥ ${minScore} баллов` : "Без ограничений"}
                </Typography>

                {/* Budget input */}
                <Typography variant="caption" color="text.secondary" fontWeight={600}>
                  Лимит бюджета
                </Typography>
                <TextField
                  fullWidth size="small"
                  placeholder="Без ограничений"
                  value={budgetText}
                  onChange={(e) => handleBudgetInput(e.target.value)}
                  slotProps={{
                    input: {
                      endAdornment: (
                        <InputAdornment position="end">
                          <Typography variant="body2" color="text.secondary" fontWeight={600}>₸</Typography>
                        </InputAdornment>
                      ),
                    },
                  }}
                  sx={{ mt: 1, mb: 2.5, "& .MuiOutlinedInput-root": { fontFamily: "'JetBrains Mono'" } }}
                />

                {/* Strategy toggle */}
                <Typography variant="caption" color="text.secondary" fontWeight={600}>
                  Стратегия
                </Typography>
                <ToggleButtonGroup
                  value={strategy}
                  exclusive
                  disabled={!budgetActive}
                  onChange={(_, v) => {
                    if (v) {
                      setStrategy(v);
                      recalc(undefined, undefined, undefined, undefined, undefined, undefined, v);
                    }
                  }}
                  size="small"
                  fullWidth
                  sx={{ mt: 1 }}
                >
                  <ToggleButton value="more_applications" sx={{ textTransform: "none", fontSize: "0.75rem", py: 0.8 }}>
                    <Groups sx={{ fontSize: 16, mr: 0.5 }} />
                    Больше заявок
                  </ToggleButton>
                  <ToggleButton value="more_budget" sx={{ textTransform: "none", fontSize: "0.75rem", py: 0.8 }}>
                    <AccountBalance sx={{ fontSize: 16, mr: 0.5 }} />
                    Больше освоение
                  </ToggleButton>
                </ToggleButtonGroup>
                <Typography variant="caption" display="block" mt={0.5} color="text.secondary">
                  {!budgetActive
                    ? "Введите лимит бюджета для выбора стратегии."
                    : strategy === "more_applications"
                      ? "При равном балле предпочтение заявкам с меньшей суммой. В бюджет войдёт больше заявок."
                      : "При равном балле предпочтение заявкам с большей суммой. Бюджет будет освоен плотнее."}
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
                        {selectedCount}
                      </Typography>
                    </Stack>
                    <Stack direction="row" justifyContent="space-between" alignItems="baseline">
                      <Typography variant="body2" color="text.secondary">Общая сумма</Typography>
                      <Typography variant="body2" fontWeight={700} fontFamily="'JetBrains Mono'" color="#22c55e">
                        {fmtExact(totalCost)}
                      </Typography>
                    </Stack>
                    {budget > 0 && (
                      <Stack direction="row" justifyContent="space-between" alignItems="baseline">
                        <Typography variant="body2" color="text.secondary">Остаток</Typography>
                        <Typography variant="body2" fontWeight={700} fontFamily="'JetBrains Mono'" color={remaining > 0 ? "#3b82f6" : "text.secondary"}>
                          {fmtExact(remaining)}
                        </Typography>
                      </Stack>
                    )}
                    <Stack direction="row" justifyContent="space-between">
                      <Typography variant="body2" color="text.secondary">Требуют проверки</Typography>
                      <Typography variant="body2" fontWeight={700} fontFamily="'JetBrains Mono'" color="#f59e0b">
                        {reviewCount}
                      </Typography>
                    </Stack>
                    <Stack direction="row" justifyContent="space-between">
                      <Typography variant="body2" color="text.secondary">Не вошли в выборку</Typography>
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
              <Button size="small" startIcon={<Download />} onClick={() => downloadExport(modelVersion || undefined)} disabled={!result}>
                Excel
              </Button>
            </Box>

            {!modelVersion ? (
              <Box sx={{ display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center", py: 12, gap: 2 }}>
                <Warning sx={{ fontSize: 40, color: "text.disabled" }} />
                <Typography variant="body2" color="text.secondary">
                  Модель не выбрана. Выберите модель в переключателе вверху страницы.
                </Typography>
              </Box>
            ) : error ? (
              <Box sx={{ p: 3 }}>
                <Alert severity="error" sx={{ borderRadius: 2 }}>
                  <Typography variant="body2" fontWeight={600}>Ошибка загрузки шорт-листа</Typography>
                  <Typography variant="caption">{error}</Typography>
                </Alert>
              </Box>
            ) : loading ? (
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
                      <TableCell align="right" sx={{ fontWeight: 700, textTransform: "uppercase", fontSize: "0.7rem", letterSpacing: 0.5 }}>Причитающая сумма</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {selected.map((app: any) => {
                      const cat = CATEGORY_CHIP[app.category] ?? { color: "default" as const, label: app.category };
                      return (
                        <TableRow
                          key={app.id ?? app.rank}
                          hover
                          sx={{ cursor: app.id ? "pointer" : "default", "&:hover": { bgcolor: "#f0fdf4" } }}
                          onClick={() => app.id && navigate(`/app/${app.id}`)}
                        >
                          <TableCell sx={{ fontFamily: "'JetBrains Mono'", color: "text.secondary", fontWeight: 500 }}>{app.rank}</TableCell>
                          <TableCell><ScoreBadge score={Math.round(app.score)} size="sm" category={app.category} /></TableCell>
                          <TableCell><Chip label={cat.label} color={cat.color} size="small" variant="outlined" /></TableCell>
                          <TableCell sx={{ fontWeight: 500 }}>{app.region || "—"}</TableCell>
                          <TableCell sx={{ color: "text.secondary" }}>{app.direction || "—"}</TableCell>
                          <TableCell align="right" sx={{ fontFamily: "'JetBrains Mono'", fontWeight: 600 }}>
                            {fmt(app.amount ?? 0)}
                          </TableCell>
                        </TableRow>
                      );
                    })}
                    {selected.length === 0 && (
                      <TableRow>
                        <TableCell colSpan={6} sx={{ textAlign: "center", py: 8 }}>
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

      <Typography
        variant="caption" display="block" mt={3} color="text.secondary" textAlign="center"
        sx={{ fontStyle: "italic" }}
      >
        Носит рекомендательный характер. Решение принимает комиссия.
      </Typography>
    </Box>
  );
}

