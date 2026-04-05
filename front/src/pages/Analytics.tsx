import { useState, useEffect } from "react";
import {
  Box, Card, CardContent, Typography, Tabs, Tab, Grid, Stack, CircularProgress,
  Tooltip as MuiTooltip,
} from "@mui/material";
import { BarChart as BarChartIcon, Insights } from "@mui/icons-material";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from "recharts";
import {
  fetchFeatureImportance,
  type FeatureImportanceItem, type ModelInfo,
} from "../data/api";
import { FEATURE_DISPLAY } from "../data/featureNames";
import { METRIC_TOOLTIPS } from "../data/metricTooltips";
import { useModel } from "../data/ModelContext";

/* ── Наборы метрик по типу отображения ── */
const PERCENT_METRICS = new Set([
  "auc_mean", "f1_mean", "precision_mean", "recall_mean", "accuracy_mean", "gini_mean",
  "auc_std", "f1_std", "precision_std", "recall_std", "accuracy_std", "gini_std",
  "positive_rate", "avg_precision_mean", "avg_precision_std",
]);
const INTEGER_METRICS = new Set([
  "total_tp", "total_fp", "total_tn", "total_fn", "train_size", "n_features",
]);
const LOG_LOSS_METRICS = new Set(["log_loss_mean", "log_loss_std"]);


/** Форматирование значения метрики в зависимости от типа */
function fmtMetricValue(key: string, val: number): string {
  if (INTEGER_METRICS.has(key)) return val.toLocaleString("ru");
  if (LOG_LOSS_METRICS.has(key)) return val.toFixed(3);
  if (PERCENT_METRICS.has(key)) return (val > 1 ? val : val * 100).toFixed(1) + "%";
  // fallback
  return val > 1 ? val.toFixed(0) : (val * 100).toFixed(1) + "%";
}

const TOOLTIP_SX = {
  bgcolor: "rgba(30,30,30,0.95)",
  color: "#fff",
  maxWidth: 280,
  borderRadius: 1.5,
  fontSize: "0.78rem",
  lineHeight: 1.45,
  px: 1.5,
  py: 1,
};

function MetricTile({ label, value, metricKey }: { label: string; value: string; metricKey?: string }) {
  const tooltip = metricKey ? METRIC_TOOLTIPS[metricKey] : undefined;
  const tile = (
    <Card>
      <CardContent sx={{ p: 3, textAlign: "center" }}>
        <Typography variant="caption" fontWeight={600} sx={{ cursor: tooltip ? "help" : undefined }}>{label}</Typography>
        <Typography variant="h4" fontFamily="'JetBrains Mono'" mt={0.5}>
          {value}
        </Typography>
      </CardContent>
    </Card>
  );
  if (!tooltip) return tile;
  return (
    <MuiTooltip title={tooltip} arrow enterDelay={300} slotProps={{ tooltip: { sx: TOOLTIP_SX }, arrow: { sx: { color: "rgba(30,30,30,0.95)" } } }}>
      {tile}
    </MuiTooltip>
  );
}

export function Analytics() {
  const { modelVersion, models } = useModel();
  const [tab, setTab] = useState(0);
  const [features, setFeatures] = useState<FeatureImportanceItem[]>([]);
  const [featureVersion, setFeatureVersion] = useState("");
  const [loading, setLoading] = useState(true);

  const activeModel = models.find((m) => m.version === modelVersion) ?? null;

  useEffect(() => {
    setLoading(true);
    fetchFeatureImportance(modelVersion || undefined)
      .then((fi) => {
        setFeatures(fi.features);
        setFeatureVersion(fi.model_version);
      })
      .catch(() => {
        setFeatures([]);
        setFeatureVersion("");
      })
      .finally(() => setLoading(false));
  }, [modelVersion]);


  if (loading) return (
    <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", height: "60vh" }}>
      <CircularProgress />
    </Box>
  );

  const metrics = activeModel?.metrics ?? {};
  const metricLabels: Record<string, string> = {
    auc_mean: "AUC", f1_mean: "F1", precision_mean: "Precision",
    recall_mean: "Recall", accuracy_mean: "Accuracy", gini_mean: "Gini",
    auc_std: "AUC (std)", f1_std: "F1 (std)", precision_std: "Precision (std)",
    recall_std: "Recall (std)", accuracy_std: "Accuracy (std)", gini_std: "Gini (std)",
    total_tp: "True Positives (TP)", total_fp: "False Positives (FP)",
    total_tn: "True Negatives (TN)", total_fn: "False Negatives (FN)",
    train_size: "Train Size", n_features: "Features Count",
    positive_rate: "Positive Rate",
    log_loss_mean: "Log Loss (mean)", log_loss_std: "Log Loss (std)",
    avg_precision_mean: "Avg Precision (mean)", avg_precision_std: "Avg Precision (std)",
  };
  const keyMetrics = ["auc_mean", "f1_mean", "precision_mean", "recall_mean", "accuracy_mean", "gini_mean"];

  return (
    <Box sx={{ p: { xs: 2.5, md: 4 } }}>
      <Stack spacing={3}>
        <Box>
          <Typography variant="h5">Исследование модели</Typography>
          <Typography variant="caption">Метрики качества, важность факторов и параметры AI-модели</Typography>
        </Box>

        <Tabs value={tab} onChange={(_, v) => setTab(v)} variant="scrollable" scrollButtons="auto"
          sx={{ bgcolor: "background.paper", borderRadius: 2, border: "1px solid #f0f0f0", minHeight: 42, "& .MuiTab-root": { minHeight: 42, textTransform: "none", fontWeight: 600, fontSize: "0.8125rem" } }}>
          <Tab icon={<BarChartIcon sx={{ fontSize: 16 }} />} iconPosition="start" label="Важность факторов" />
          <Tab icon={<Insights sx={{ fontSize: 16 }} />} iconPosition="start" label="Метрики модели" />
        </Tabs>

        {tab === 0 && (
          <Card>
            <CardContent sx={{ p: 3 }}>
              <Typography variant="subtitle2" mb={0.5}>Важность факторов модели{featureVersion ? ` (${featureVersion})` : ""}</Typography>
              <Typography variant="caption" display="block" mb={3}>Feature Importance — вклад каждого фактора в итоговое решение</Typography>
              {features.length > 0 ? (
                <ResponsiveContainer width="100%" height={Math.max(340, features.length * 32)}>
                  <BarChart data={features.map((f) => ({ ...f, displayName: FEATURE_DISPLAY[f.feature] || f.feature }))} layout="vertical" margin={{ top: 4, right: 48, left: 4, bottom: 4 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" horizontal={false} />
                    <XAxis type="number" tick={{ fontSize: 11, fill: "#9ca3af" }} axisLine={false} tickLine={false} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} />
                    <YAxis type="category" dataKey="displayName" width={200} tick={{ fontSize: 12, fill: "#374151" }} axisLine={false} tickLine={false} />
                    <Tooltip formatter={(v: number) => [`${(v * 100).toFixed(1)}%`, "Важность"]} contentStyle={{ fontSize: 12, borderRadius: 8, border: "1px solid #e5e7eb" }} />
                    <Bar dataKey="importance" radius={[0, 6, 6, 0]} barSize={24}
                      label={{ position: "right", fontSize: 11, fill: "#6b7280", formatter: (v: number) => `${(v * 100).toFixed(0)}%` }}>
                      {features.map((_, i) => <Cell key={i} fill={i === 0 ? "#22c55e" : i < 3 ? "#3b82f6" : "#94a3b8"} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <Typography variant="body2" color="text.secondary" textAlign="center" py={6}>Нет обученной модели</Typography>
              )}
            </CardContent>
          </Card>
        )}

        {tab === 1 && (
          <Stack spacing={3}>
            {Object.keys(metrics).length > 0 ? (
              <>
                <Typography variant="subtitle2">Ключевые метрики</Typography>
                <Grid container spacing={2}>
                  {keyMetrics.filter((k) => metrics[k] != null).map((key) => (
                    <Grid size={{ xs: 6, md: 2 }} key={key}>
                      <MetricTile
                        label={metricLabels[key] || key}
                        value={typeof metrics[key] === "number" ? fmtMetricValue(key, metrics[key]) : String(metrics[key])}
                        metricKey={key}
                      />
                    </Grid>
                  ))}
                </Grid>
                {Object.keys(metrics).filter((k) => !keyMetrics.includes(k)).length > 0 && (
                  <>
                    <Typography variant="subtitle2">Дополнительные метрики</Typography>
                    <Grid container spacing={2}>
                      {Object.entries(metrics)
                        .filter(([k]) => !keyMetrics.includes(k))
                        .map(([key, val]) => (
                          <Grid size={{ xs: 6, md: 2.4 }} key={key}>
                            <MetricTile
                              label={metricLabels[key] || key}
                              value={typeof val === "number" ? fmtMetricValue(key, val) : String(val)}
                              metricKey={key}
                            />
                          </Grid>
                        ))}
                    </Grid>
                  </>
                )}
              </>
            ) : (
              <Card>
                <CardContent sx={{ p: 6, textAlign: "center" }}>
                  <Typography variant="body2" color="text.secondary">Нет данных о метриках модели. Обучите модель для получения метрик.</Typography>
                </CardContent>
              </Card>
            )}
            {activeModel && (
              <Card>
                <CardContent sx={{ p: 3 }}>
                  <Typography variant="subtitle2" mb={2}>Информация об активной модели</Typography>
                  <Stack spacing={1}>
                    <Box sx={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid #f5f5f5", py: 1 }}>
                      <Typography variant="body2" color="text.secondary">Версия</Typography>
                      <Typography variant="body2" fontWeight={600}>{activeModel.version}</Typography>
                    </Box>
                    <Box sx={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid #f5f5f5", py: 1 }}>
                      <Typography variant="body2" color="text.secondary">Обучающая выборка</Typography>
                      <Typography variant="body2" fontWeight={600}>{activeModel.train_size.toLocaleString("ru")} записей</Typography>
                    </Box>
                    <Box sx={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid #f5f5f5", py: 1 }}>
                      <Typography variant="body2" color="text.secondary">Кол-во признаков</Typography>
                      <Typography variant="body2" fontWeight={600}>{activeModel.n_features}</Typography>
                    </Box>
                    <Box sx={{ display: "flex", justifyContent: "space-between", py: 1 }}>
                      <Typography variant="body2" color="text.secondary">Доля одобренных</Typography>
                      <Typography variant="body2" fontWeight={600}>{(activeModel.positive_rate * 100).toFixed(1)}%</Typography>
                    </Box>
                  </Stack>
                </CardContent>
              </Card>
            )}
          </Stack>
        )}
      </Stack>
    </Box>
  );
}
