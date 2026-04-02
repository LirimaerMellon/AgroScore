import { useState, useEffect, useRef } from "react";
import {
  Box, Card, CardContent, Typography, Button, Stack, Alert, Chip, LinearProgress,
  Table, TableHead, TableBody, TableRow, TableCell, TableContainer, CircularProgress,
  Grid, MenuItem, TextField, Collapse, Tooltip, IconButton,
} from "@mui/material";
import {
  CloudUpload, CheckCircle, Refresh, PlayArrow, ExpandMore, ExpandLess,
  School, ModelTraining, Info,
} from "@mui/icons-material";
import {
  fetchModels, activateModel, trainFromFile, type ModelInfo,
} from "../data/api";

function MetricChip({ label, value }: { label: string; value: string }) {
  return (
    <Chip
      size="small"
      variant="outlined"
      label={<><b>{label}:</b> {value}</>}
      sx={{ fontFamily: "'JetBrains Mono'", fontSize: "0.7rem" }}
    />
  );
}

export function ModelManager() {
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionMsg, setActionMsg] = useState("");
  const [actionError, setActionError] = useState("");
  const [training, setTraining] = useState(false);
  const [trainResult, setTrainResult] = useState<any>(null);
  const [baseModel, setBaseModel] = useState<string>("");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [expandedModel, setExpandedModel] = useState<number | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  async function loadModels() {
    setLoading(true);
    try {
      const res = await fetchModels();
      setModels(res.models);
    } catch { /* graceful */ }
    setLoading(false);
  }

  useEffect(() => { loadModels(); }, []);

  const activeModel = models.find((m) => m.is_active);

  async function handleActivate(version: string) {
    setActionMsg(""); setActionError("");
    try {
      await activateModel(version);
      setActionMsg(`Модель ${version} активирована`);
      await loadModels();
    } catch (e: any) {
      setActionError(e.message || "Ошибка активации");
    }
  }

  async function handleTrain(file: File) {
    setTraining(true); setTrainResult(null); setActionError(""); setActionMsg("");
    try {
      const res = await trainFromFile(file, baseModel || undefined);
      setTrainResult(res);
      setActionMsg(`Модель ${res.model_version} обучена успешно`);
      await loadModels();
    } catch (e: any) {
      setActionError(e.message || "Ошибка обучения");
    }
    setTraining(false);
  }

  const fmtMetric = (v: any) => {
    if (typeof v !== "number") return String(v);
    return v > 1 ? v.toFixed(0) : (v * 100).toFixed(1) + "%";
  };

  const keyMetrics = ["auc_mean", "f1_mean", "precision_mean", "recall_mean", "accuracy_mean", "gini_mean"];
  const metricLabels: Record<string, string> = {
    auc_mean: "AUC", f1_mean: "F1", precision_mean: "Precision",
    recall_mean: "Recall", accuracy_mean: "Accuracy", gini_mean: "Gini",
  };

  return (
    <Box sx={{ p: { xs: 2.5, md: 4 } }}>
      <Stack spacing={3}>
        <Box>
          <Typography variant="h5">Модели</Typography>
          <Typography variant="caption">Обучение, выбор и управление AI-моделями скоринга</Typography>
        </Box>

        {actionMsg && <Alert severity="success" sx={{ borderRadius: 2 }} onClose={() => setActionMsg("")}>{actionMsg}</Alert>}
        {actionError && <Alert severity="error" sx={{ borderRadius: 2 }} onClose={() => setActionError("")}>{actionError}</Alert>}

        {/* Active model banner */}
        {activeModel ? (
          <Card sx={{ bgcolor: "#f0fdf4", border: "1px solid #dcfce7" }}>
            <CardContent sx={{ p: 3 }}>
              <Stack direction="row" spacing={2} alignItems="center" flexWrap="wrap">
                <CheckCircle color="success" />
                <Box sx={{ flex: 1 }}>
                  <Typography variant="subtitle2">
                    Активная модель: <b>{activeModel.version}</b>
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Обучена {new Date(activeModel.created_at).toLocaleString("ru")} · {activeModel.train_size} записей · {activeModel.n_features} признаков
                  </Typography>
                </Box>
              </Stack>
              <Stack direction="row" spacing={1} mt={1.5} flexWrap="wrap" useFlexGap>
                {keyMetrics.map((key) =>
                  activeModel.metrics[key] != null && (
                    <MetricChip key={key} label={metricLabels[key] || key} value={fmtMetric(activeModel.metrics[key])} />
                  )
                )}
              </Stack>
            </CardContent>
          </Card>
        ) : (
          <Alert severity="warning" icon={<School />} sx={{ borderRadius: 2 }}>
            <Typography variant="body2" fontWeight={600}>Модель не обучена</Typography>
            <Typography variant="caption">
              Загрузите файл с историческими данными (Excel/CSV со статусами заявок) для обучения первой модели.
            </Typography>
          </Alert>
        )}

        {/* Training section */}
        <Card>
          <CardContent sx={{ p: 3 }}>
            <Stack direction="row" spacing={1.5} alignItems="center" mb={1}>
              <ModelTraining color="primary" />
              <Typography variant="subtitle2">Обучение модели</Typography>
            </Stack>
            <Typography variant="caption" display="block" mb={2} color="text.secondary">
              Загрузите Excel/CSV файл с историческими данными (со статусами заявок: «исполнена», «одобрена», «отклонена»).
              Модель обучится автоматически и станет активной.
            </Typography>

            {/* Advanced: fine-tuning */}
            <Button
              size="small" variant="text"
              startIcon={showAdvanced ? <ExpandLess /> : <ExpandMore />}
              onClick={() => setShowAdvanced(!showAdvanced)}
              sx={{ mb: 1, textTransform: "none", color: "text.secondary" }}
            >
              Дополнительные параметры
            </Button>

            <Collapse in={showAdvanced}>
              <Box sx={{ mb: 2, p: 2, bgcolor: "#fafafa", borderRadius: 2, border: "1px solid #f0f0f0" }}>
                <TextField
                  select fullWidth size="small"
                  label="Базовая модель для дообучения (fine-tuning)"
                  value={baseModel}
                  onChange={(e) => setBaseModel(e.target.value)}
                  helperText="Оставьте пустым для обучения с нуля, или выберите модель для дообучения на новых данных"
                >
                  <MenuItem value="">Обучение с нуля</MenuItem>
                  {models.map((m) => (
                    <MenuItem key={m.version} value={m.version}>
                      {m.version} {m.is_active ? " (активная)" : ""} — {m.train_size} записей
                    </MenuItem>
                  ))}
                </TextField>
              </Box>
            </Collapse>

            <Stack direction="row" spacing={2} alignItems="center">
              <input ref={fileRef} type="file" accept=".xlsx,.xls,.csv" hidden
                onChange={(e) => { if (e.target.files?.[0]) handleTrain(e.target.files[0]); e.target.value = ""; }} />
              <Button variant="contained" startIcon={<CloudUpload />} disabled={training}
                onClick={() => fileRef.current?.click()}>
                {training ? "Обучение…" : "Загрузить данные для обучения"}
              </Button>
              {baseModel && (
                <Chip
                  size="small" variant="outlined" color="info"
                  label={`Fine-tuning от: ${baseModel}`}
                  onDelete={() => setBaseModel("")}
                />
              )}
            </Stack>
            {training && <LinearProgress sx={{ mt: 2, borderRadius: 2 }} />}

            {/* Training result */}
            {trainResult && (
              <Card variant="outlined" sx={{ mt: 2, bgcolor: "#f0fdf4" }}>
                <CardContent sx={{ p: 2 }}>
                  <Stack spacing={0.5}>
                    <Stack direction="row" spacing={1} alignItems="center">
                      <CheckCircle color="success" sx={{ fontSize: 18 }} />
                      <Typography variant="body2" fontWeight={600}>Обучение завершено</Typography>
                    </Stack>
                    <Typography variant="body2"><b>Версия:</b> {trainResult.model_version}</Typography>
                    <Typography variant="body2">
                      <b>Данные:</b> {trainResult.total_raw_records} исходных → {trainResult.cleaned_records} очищенных
                    </Typography>
                    {trainResult.metrics && (
                      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap mt={0.5}>
                        {keyMetrics.map((key) =>
                          trainResult.metrics[key] != null && (
                            <MetricChip key={key} label={metricLabels[key] || key} value={fmtMetric(trainResult.metrics[key])} />
                          )
                        )}
                      </Stack>
                    )}
                  </Stack>
                </CardContent>
              </Card>
            )}
          </CardContent>
        </Card>

        {/* Models list */}
        <Card>
          <Box sx={{ px: 3, py: 2, borderBottom: "1px solid #f0f0f0", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <Typography variant="subtitle2">Все модели ({models.length})</Typography>
            <Button size="small" startIcon={<Refresh />} onClick={loadModels}>Обновить</Button>
          </Box>
          {loading ? (
            <Box sx={{ display: "flex", justifyContent: "center", py: 6 }}><CircularProgress size={28} /></Box>
          ) : models.length === 0 ? (
            <CardContent sx={{ textAlign: "center", py: 6 }}>
              <School sx={{ fontSize: 48, color: "#d1d5db", mb: 1 }} />
              <Typography variant="body2" color="text.secondary">Нет обученных моделей</Typography>
              <Typography variant="caption" color="text.secondary">Загрузите данные выше для обучения первой модели</Typography>
            </CardContent>
          ) : (
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Версия</TableCell>
                    <TableCell>Дата создания</TableCell>
                    <TableCell align="right">Выборка</TableCell>
                    <TableCell align="right">Признаков</TableCell>
                    <TableCell align="right">Positive rate</TableCell>
                    <TableCell>Статус</TableCell>
                    <TableCell width={140} />
                  </TableRow>
                </TableHead>
                <TableBody>
                  {models.map((m) => (
                    <>
                      <TableRow
                        key={m.id}
                        hover
                        sx={{ cursor: "pointer", bgcolor: m.is_active ? "#f0fdf4" : undefined }}
                        onClick={() => setExpandedModel(expandedModel === m.id ? null : m.id)}
                      >
                        <TableCell sx={{ fontWeight: 600 }}>{m.version}</TableCell>
                        <TableCell sx={{ fontFamily: "'JetBrains Mono'", fontSize: "0.75rem" }}>
                          {new Date(m.created_at).toLocaleString("ru")}
                        </TableCell>
                        <TableCell align="right" sx={{ fontFamily: "'JetBrains Mono'" }}>{m.train_size.toLocaleString("ru")}</TableCell>
                        <TableCell align="right" sx={{ fontFamily: "'JetBrains Mono'" }}>{m.n_features}</TableCell>
                        <TableCell align="right" sx={{ fontFamily: "'JetBrains Mono'" }}>{(m.positive_rate * 100).toFixed(1)}%</TableCell>
                        <TableCell>
                          {m.is_active ? (
                            <Chip label="Активная" size="small" color="success" icon={<CheckCircle />} />
                          ) : (
                            <Chip label="Неактивная" size="small" variant="outlined" />
                          )}
                        </TableCell>
                        <TableCell onClick={(e) => e.stopPropagation()}>
                          {!m.is_active && (
                            <Button size="small" variant="outlined" startIcon={<PlayArrow />}
                              onClick={() => handleActivate(m.version)}>
                              Активировать
                            </Button>
                          )}
                        </TableCell>
                      </TableRow>
                      {expandedModel === m.id && Object.keys(m.metrics).length > 0 && (
                        <TableRow key={`${m.id}-metrics`}>
                          <TableCell colSpan={7} sx={{ bgcolor: "#fafafa", py: 2 }}>
                            <Typography variant="caption" fontWeight={600} display="block" mb={1}>Метрики модели</Typography>
                            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                              {Object.entries(m.metrics).map(([key, val]) => (
                                <MetricChip key={key} label={metricLabels[key] || key} value={fmtMetric(val)} />
                              ))}
                            </Stack>
                          </TableCell>
                        </TableRow>
                      )}
                    </>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </Card>

        <Alert severity="info" icon={<Info />} sx={{ borderRadius: 3 }}>
          <Typography variant="caption">
            <strong>Как это работает:</strong> Загрузите Excel-файл с историческими данными (обязательно со столбцом «Статус заявки»).
            Модель обучится на одобренных и отклонённых заявках. После обучения она станет активной и будет использоваться
            для скоринга новых заявок. Вы можете обучить несколько моделей и переключаться между ними.
          </Typography>
        </Alert>
      </Stack>
    </Box>
  );
}

