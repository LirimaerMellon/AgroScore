import { useState, useEffect, useCallback } from "react";
import {
  Box, Card, CardContent, Typography, Button, Stack, Alert, Chip, Slider,
  Dialog, DialogTitle, DialogContent, DialogActions, Checkbox, FormControlLabel,
  TextField, Divider, Grid,
} from "@mui/material";
import { DeleteForever, Warning, TuneRounded, SaveAlt, Refresh, AccountBalance } from "@mui/icons-material";
import {
  fetchThresholds, updateThresholds, resetThresholds, previewThresholds,
  fetchRoundBudget, updateRoundBudget,
  type ThresholdItem,
} from "../data/api";
import { useModel } from "../data/ModelContext";

export function Settings() {
  const { modelVersion, refreshModels } = useModel();
  const [actionMsg, setActionMsg] = useState("");
  const [actionError, setActionError] = useState("");
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [resetApps, setResetApps] = useState(true);
  const [resetModels, setResetModels] = useState(true);
  const [resetErrors, setResetErrors] = useState(true);
  const [resetting, setResetting] = useState(false);

  // Thresholds
  const [lowMax, setLowMax] = useState(40);
  const [highMin, setHighMin] = useState(71);
  const [preview, setPreview] = useState<Record<string, number>>({});
  const [thresholdsSaving, setThresholdsSaving] = useState(false);
  const [thresholdsLoaded, setThresholdsLoaded] = useState(false);

  // Round budget
  const [roundBudget, setRoundBudget] = useState(0);
  const [budgetInput, setBudgetInput] = useState("");
  const [budgetSaving, setBudgetSaving] = useState(false);

  const buildThresholds = useCallback((lm: number, hm: number): ThresholdItem[] => [
    { category: "LOW", min_score: 0, max_score: lm },
    { category: "MEDIUM", min_score: lm + 1, max_score: hm - 1 },
    { category: "HIGH", min_score: hm, max_score: 100 },
  ], []);

  // Load thresholds + budget on mount and when model changes
  useEffect(() => {
    (async () => {
      try {
        const res = await fetchThresholds(modelVersion || undefined);
        const sorted = [...res.thresholds].sort((a, b) => a.min_score - b.min_score);
        if (sorted.length === 3) {
          setLowMax(sorted[0].max_score);
          setHighMin(sorted[2].min_score);
        }
        setThresholdsLoaded(true);
      } catch { /* ignore */ }
      try {
        const bRes = await fetchRoundBudget();
        setRoundBudget(bRes.budget);
        setBudgetInput(bRes.budget > 0 ? String(bRes.budget) : "");
      } catch { /* ignore */ }
    })();
  }, [modelVersion]);

  // Preview when sliders change
  useEffect(() => {
    if (!thresholdsLoaded) return;
    const t = buildThresholds(lowMax, highMin);
    previewThresholds(t).then((r) => setPreview(r.counts)).catch(() => {});
  }, [lowMax, highMin, thresholdsLoaded, buildThresholds]);

  async function handleSaveThresholds() {
    setThresholdsSaving(true);
    setActionMsg(""); setActionError("");
    try {
      const t = buildThresholds(lowMax, highMin);
      await updateThresholds(t, "admin", modelVersion || "_default");
      setActionMsg("Пороги категорий сохранены");
    } catch (e: any) {
      setActionError(e.message || "Ошибка сохранения порогов");
    }
    setThresholdsSaving(false);
  }

  async function handleResetThresholds() {
    setThresholdsSaving(true);
    try {
      const res = await resetThresholds(modelVersion || "_default");
      const sorted = [...res.thresholds].sort((a, b) => a.min_score - b.min_score);
      if (sorted.length === 3) {
        setLowMax(sorted[0].max_score);
        setHighMin(sorted[2].min_score);
      }
      setActionMsg("Пороги сброшены к дефолтным (0–40, 41–70, 71–100)");
    } catch (e: any) {
      setActionError(e.message || "Ошибка сброса порогов");
    }
    setThresholdsSaving(false);
  }

  async function handleSaveBudget() {
    setBudgetSaving(true);
    setActionMsg(""); setActionError("");
    try {
      const val = parseFloat(budgetInput) || 0;
      await updateRoundBudget(val);
      setRoundBudget(val);
      setActionMsg(`Бюджет раунда обновлён: ₸${val.toLocaleString("ru")}`);
    } catch (e: any) {
      setActionError(e.message || "Ошибка сохранения бюджета");
    }
    setBudgetSaving(false);
  }

  async function handleReset() {
    setResetting(true);
    setActionMsg(""); setActionError("");
    try {
      const q = new URLSearchParams();
      q.set("applications", String(resetApps));
      q.set("models", String(resetModels));
      q.set("errors", String(resetErrors));
      const res = await fetch(`/api/admin/reset?${q.toString()}`, { method: "DELETE" });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || "Ошибка сброса");
      }
      const data = await res.json();
      setActionMsg(`Система очищена. Удалено: ${JSON.stringify(data.deleted)}`);
      await refreshModels();
    } catch (e: any) {
      setActionError(e.message || "Ошибка сброса");
    }
    setResetting(false);
    setConfirmOpen(false);
  }

  const medMin = lowMax + 1;
  const medMax = highMin - 1;

  return (
    <Box sx={{ p: { xs: 2.5, md: 4 } }}>
      <Stack spacing={3}>
        <Box>
          <Typography variant="h5">Настройки</Typography>
          <Typography variant="caption">Администрирование системы</Typography>
        </Box>

        {actionMsg && <Alert severity="success" sx={{ borderRadius: 2 }} onClose={() => setActionMsg("")}>{actionMsg}</Alert>}
        {actionError && <Alert severity="error" sx={{ borderRadius: 2 }} onClose={() => setActionError("")}>{actionError}</Alert>}

        {/* ═══ Threshold Management ═══ */}
        <Card>
          <CardContent sx={{ p: 3 }}>
            <Stack direction="row" spacing={1.5} alignItems="center" mb={2}>
              <TuneRounded sx={{ color: "#8b5cf6" }} />
              <Typography variant="subtitle2">Пороги категорий</Typography>
            </Stack>
            <Typography variant="caption" display="block" mb={3} color="text.secondary">
              Настройте границы категорий LOW / MEDIUM / HIGH. Категории — визуальная подсказка для комиссии.
            </Typography>

            <Grid container spacing={3}>
              <Grid size={{ xs: 12, md: 7 }}>
                {/* LOW slider */}
                <Box sx={{ mb: 3 }}>
                  <Stack direction="row" justifyContent="space-between" alignItems="center" mb={0.5}>
                    <Chip label="LOW" size="small" color="error" variant="outlined" />
                    <Typography variant="body2" fontWeight={700} fontFamily="'JetBrains Mono'">0 — {lowMax}</Typography>
                  </Stack>
                  <Slider
                    value={lowMax}
                    onChange={(_, v) => {
                      const val = v as number;
                      if (val < highMin - 1) setLowMax(val);
                    }}
                    min={10} max={90} step={1}
                    valueLabelDisplay="auto"
                    sx={{ color: "#ef4444" }}
                  />
                </Box>

                {/* MEDIUM (display only) */}
                <Box sx={{ mb: 3 }}>
                  <Stack direction="row" justifyContent="space-between" alignItems="center" mb={0.5}>
                    <Chip label="MEDIUM" size="small" color="warning" variant="outlined" />
                    <Typography variant="body2" fontWeight={700} fontFamily="'JetBrains Mono'">{medMin} — {medMax}</Typography>
                  </Stack>
                  <Box sx={{ height: 8, borderRadius: 4, bgcolor: "#fef3c7", mx: 1.5 }} />
                </Box>

                {/* HIGH slider */}
                <Box sx={{ mb: 2 }}>
                  <Stack direction="row" justifyContent="space-between" alignItems="center" mb={0.5}>
                    <Chip label="HIGH" size="small" color="success" variant="outlined" />
                    <Typography variant="body2" fontWeight={700} fontFamily="'JetBrains Mono'">{highMin} — 100</Typography>
                  </Stack>
                  <Slider
                    value={highMin}
                    onChange={(_, v) => {
                      const val = v as number;
                      if (val > lowMax + 1) setHighMin(val);
                    }}
                    min={10} max={99} step={1}
                    valueLabelDisplay="auto"
                    sx={{ color: "#22c55e" }}
                  />
                </Box>
              </Grid>

              {/* Preview */}
              <Grid size={{ xs: 12, md: 5 }}>
                <Card variant="outlined" sx={{ p: 2, bgcolor: "#fafafa" }}>
                  <Typography variant="caption" fontWeight={600} mb={1.5} display="block">
                    Предпросмотр (заявки в каждой категории)
                  </Typography>
                  <Stack spacing={1.5}>
                    <Stack direction="row" justifyContent="space-between">
                      <Chip label="LOW" size="small" color="error" variant="outlined" />
                      <Typography variant="body2" fontWeight={700} fontFamily="'JetBrains Mono'">{preview.LOW ?? "—"}</Typography>
                    </Stack>
                    <Stack direction="row" justifyContent="space-between">
                      <Chip label="MEDIUM" size="small" color="warning" variant="outlined" />
                      <Typography variant="body2" fontWeight={700} fontFamily="'JetBrains Mono'">{preview.MEDIUM ?? "—"}</Typography>
                    </Stack>
                    <Stack direction="row" justifyContent="space-between">
                      <Chip label="HIGH" size="small" color="success" variant="outlined" />
                      <Typography variant="body2" fontWeight={700} fontFamily="'JetBrains Mono'">{preview.HIGH ?? "—"}</Typography>
                    </Stack>
                  </Stack>
                </Card>
              </Grid>
            </Grid>

            <Divider sx={{ my: 2 }} />
            <Stack direction="row" spacing={1.5}>
              <Button
                variant="contained" size="small"
                startIcon={<SaveAlt />}
                onClick={handleSaveThresholds}
                disabled={thresholdsSaving}
              >
                {thresholdsSaving ? "Сохранение…" : "Сохранить пороги"}
              </Button>
              <Button
                variant="outlined" size="small"
                startIcon={<Refresh />}
                onClick={handleResetThresholds}
                disabled={thresholdsSaving}
              >
                Сбросить
              </Button>
            </Stack>
          </CardContent>
        </Card>

        {/* ═══ Round Budget ═══ */}
        <Card>
          <CardContent sx={{ p: 3 }}>
            <Stack direction="row" spacing={1.5} alignItems="center" mb={2}>
              <AccountBalance sx={{ color: "#3b82f6" }} />
              <Typography variant="subtitle2">Бюджет раунда</Typography>
            </Stack>
            <Typography variant="caption" display="block" mb={2} color="text.secondary">
              Лимит бюджета для текущего раунда субсидирования.
              Используется для расчёта флага «укладывается в бюджет» на карточке заявки и в шорт-листе.
            </Typography>
            <Stack direction="row" spacing={2} alignItems="center">
              <TextField
                size="small" label="Бюджет (₸)" type="number"
                value={budgetInput}
                onChange={(e) => setBudgetInput(e.target.value)}
                sx={{ width: 260 }}
                slotProps={{ htmlInput: { min: 0 } }}
              />
              <Button
                variant="contained" size="small"
                startIcon={<SaveAlt />}
                onClick={handleSaveBudget}
                disabled={budgetSaving}
              >
                {budgetSaving ? "…" : "Сохранить"}
              </Button>
            </Stack>
            {roundBudget > 0 && (
              <Typography variant="caption" display="block" mt={1} color="text.secondary">
                Текущий бюджет: <b>₸{roundBudget.toLocaleString("ru")}</b>
              </Typography>
            )}
          </CardContent>
        </Card>

        {/* ═══ Reset section ═══ */}
        <Card sx={{ border: "1px solid #fecaca" }}>
          <CardContent sx={{ p: 3 }}>
            <Stack direction="row" spacing={1.5} alignItems="center" mb={1}>
              <Warning color="error" />
              <Typography variant="subtitle2" color="error.main">Сброс системы</Typography>
            </Stack>
            <Typography variant="caption" display="block" mb={2} color="text.secondary">
              Полная очистка базы данных. Удалённые данные невозможно восстановить.
              После сброса моделей потребуется заново обучить модель на странице «Модели».
            </Typography>
            <Button
              variant="outlined" color="error"
              startIcon={<DeleteForever />}
              onClick={() => setConfirmOpen(true)}
            >
              Сбросить систему
            </Button>
          </CardContent>
        </Card>

        <Alert severity="info" sx={{ borderRadius: 3 }}>
          <Typography variant="caption">
            <strong>Обучение и управление моделями</strong> перенесены на отдельную страницу «Модели» в боковом меню.
            Там можно обучить новую модель и выбрать активную.
          </Typography>
        </Alert>

        {/* Confirm dialog */}
        <Dialog open={confirmOpen} onClose={() => setConfirmOpen(false)} maxWidth="xs" fullWidth>
          <DialogTitle>Подтверждение сброса</DialogTitle>
          <DialogContent>
            <Typography variant="body2" mb={2}>Выберите, что нужно удалить:</Typography>
            <Stack spacing={0.5}>
              <FormControlLabel
                control={<Checkbox checked={resetApps} onChange={(e) => setResetApps(e.target.checked)} />}
                label="Оценённые заявки"
              />
              <FormControlLabel
                control={<Checkbox checked={resetModels} onChange={(e) => setResetModels(e.target.checked)} />}
                label="Модели (БД + файлы .pkl)"
              />
              <FormControlLabel
                control={<Checkbox checked={resetErrors} onChange={(e) => setResetErrors(e.target.checked)} />}
                label="Лог ошибок"
              />
            </Stack>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setConfirmOpen(false)}>Отмена</Button>
            <Button
              variant="contained" color="error"
              onClick={handleReset}
              disabled={resetting || (!resetApps && !resetModels && !resetErrors)}
            >
              {resetting ? "Удаление…" : "Подтвердить сброс"}
            </Button>
          </DialogActions>
        </Dialog>
      </Stack>
    </Box>
  );
}
