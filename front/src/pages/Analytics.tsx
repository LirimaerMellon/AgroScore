import { useState, useEffect } from "react";
import {
  Box, Card, CardContent, Typography, Tabs, Tab, Grid, Stack, CircularProgress,
} from "@mui/material";
import { BarChart as BarChartIcon, Insights } from "@mui/icons-material";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from "recharts";
import {
  fetchFeatureImportance, fetchModels,
  type FeatureImportanceItem, type ModelInfo,
} from "../data/api";

function MetricTile({ label, value, unit }: { label: string; value: number | string; unit?: string }) {
  return (
    <Card>
      <CardContent sx={{ p: 3, textAlign: "center" }}>
        <Typography variant="caption" fontWeight={600}>{label}</Typography>
        <Typography variant="h4" fontFamily="'JetBrains Mono'" mt={0.5}>
          {typeof value === "number" ? value.toFixed(1) : value}
          {unit && <Typography component="span" variant="h6" color="text.secondary">{unit}</Typography>}
        </Typography>
      </CardContent>
    </Card>
  );
}

export function Analytics() {
  const [tab, setTab] = useState(0);
  const [features, setFeatures] = useState<FeatureImportanceItem[]>([]);
  const [featureVersion, setFeatureVersion] = useState("");
  const [activeModel, setActiveModel] = useState<ModelInfo | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.allSettled([
      fetchFeatureImportance(),
      fetchModels(),
    ]).then(([fi, m]) => {
      if (fi.status === "fulfilled") {
        setFeatures(fi.value.features);
        setFeatureVersion(fi.value.model_version);
      }
      if (m.status === "fulfilled") {
        const active = m.value.models?.find((mod) => mod.is_active);
        if (active) setActiveModel(active);
      }
      setLoading(false);
    });
  }, []);


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
                  <BarChart data={features} layout="vertical" margin={{ top: 4, right: 48, left: 4, bottom: 4 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" horizontal={false} />
                    <XAxis type="number" tick={{ fontSize: 11, fill: "#9ca3af" }} axisLine={false} tickLine={false} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} />
                    <YAxis type="category" dataKey="feature" width={160} tick={{ fontSize: 12, fill: "#374151" }} axisLine={false} tickLine={false} />
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
                        value={typeof metrics[key] === "number" ? (metrics[key] > 1 ? metrics[key] : metrics[key] * 100) : String(metrics[key])}
                        unit={typeof metrics[key] === "number" ? "%" : undefined}
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
                              value={typeof val === "number" ? (val > 1 ? val : val * 100) : String(val)}
                              unit={typeof val === "number" ? "%" : undefined}
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
                      <Typography variant="body2" fontWeight={600}>{activeModel.train_size} записей</Typography>
                    </Box>
                    <Box sx={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid #f5f5f5", py: 1 }}>
                      <Typography variant="body2" color="text.secondary">Кол-во признаков</Typography>
                      <Typography variant="body2" fontWeight={600}>{activeModel.n_features}</Typography>
                    </Box>
                    <Box sx={{ display: "flex", justifyContent: "space-between", py: 1 }}>
                      <Typography variant="body2" color="text.secondary">Positive rate</Typography>
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
