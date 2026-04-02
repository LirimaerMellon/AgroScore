import { useParams, useNavigate } from "react-router";
import { useState, useEffect } from "react";
import {
  Box, Card, CardContent, Typography, Button, Chip, Grid, Stack,
  Breadcrumbs, Link as MuiLink, CircularProgress, Alert, Tooltip,
  Table, TableHead, TableBody, TableRow, TableCell, TableContainer,
} from "@mui/material";
import {
  ArrowBack, Warning, CheckCircle, TrendingUp, TrendingDown,
  CompareArrows, Security, Info,
} from "@mui/icons-material";
import {
  fetchApplication, fetchApplicationAnalysis,
  type ApplicationItem, type ApplicationAnalysis, type RiskItem,
} from "../data/api";
import { ScoreGauge } from "../components/ScoreGauge";
import { ShapWaterfall } from "../components/ShapWaterfall";
import { ScoreBadge } from "../components/ScoreBadge";

function InfoRow({ label, value }: { label: string; value: string | number }) {
  return (
    <Box sx={{ py: 1.5, borderBottom: "1px solid #f5f5f5", "&:last-child": { borderBottom: 0 } }}>
      <Typography variant="caption" fontWeight={600} textTransform="uppercase" letterSpacing={0.5}>{label}</Typography>
      <Typography variant="body2" fontWeight={500} mt={0.3}>{value}</Typography>
    </Box>
  );
}

function PeerComparisonBar({
  label, score, maxScore = 100, color = "#64748b",
}: { label: string; score: number; maxScore?: number; color?: string }) {
  return (
    <Box sx={{ mb: 1.5 }}>
      <Box sx={{ display: "flex", justifyContent: "space-between", mb: 0.5 }}>
        <Typography variant="body2" color="text.secondary">{label}</Typography>
        <Typography variant="body2" fontWeight={700} fontFamily="'JetBrains Mono'" color={color}>{Math.round(score)}</Typography>
      </Box>
      <Box sx={{ height: 10, bgcolor: "#f1f5f9", borderRadius: 5, overflow: "hidden" }}>
        <Box sx={{
          height: "100%", borderRadius: 5,
          width: `${Math.min((score / maxScore) * 100, 100)}%`,
          bgcolor: color,
          transition: "width 0.5s ease",
        }} />
      </Box>
    </Box>
  );
}

function RiskCard({ risk }: { risk: RiskItem }) {
  const sevColor = risk.severity === "high" ? "#ef4444" : risk.severity === "medium" ? "#f59e0b" : "#9ca3af";
  const sevLabel = risk.severity === "high" ? "Высокий" : risk.severity === "medium" ? "Средний" : "Низкий";
  return (
    <Box sx={{
      p: 1.5, borderRadius: 2, border: `1px solid ${sevColor}30`,
      bgcolor: `${sevColor}08`,
    }}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
        <Warning sx={{ color: sevColor, fontSize: 20 }} />
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Typography variant="body2" fontWeight={600}>{risk.display_name || risk.feature}</Typography>
          <Typography variant="caption" color="text.secondary">
            Влияние: <b style={{ fontFamily: "'JetBrains Mono'" }}>{risk.impact.toFixed(4)}</b>
          </Typography>
        </Box>
        <Chip label={sevLabel} size="small" sx={{ bgcolor: `${sevColor}18`, color: sevColor, fontWeight: 600, fontSize: "0.65rem" }} />
      </Box>
      {(risk as any).description && (
        <Typography variant="caption" display="block" mt={1} ml={4.5} color="text.secondary">
          {(risk as any).description}
        </Typography>
      )}
    </Box>
  );
}

export function AppDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [app, setApp] = useState<ApplicationItem | null>(null);
  const [analysis, setAnalysis] = useState<ApplicationAnalysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    Promise.allSettled([
      fetchApplication(Number(id)),
      fetchApplicationAnalysis(Number(id)),
    ]).then(([appRes, analysisRes]) => {
      if (appRes.status === "fulfilled") setApp(appRes.value.application);
      else setError(appRes.reason?.message || "Не удалось загрузить заявку");
      if (analysisRes.status === "fulfilled") setAnalysis(analysisRes.value);
    }).finally(() => setLoading(false));
  }, [id]);

  if (loading) return (
    <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", height: "60vh" }}>
      <CircularProgress />
    </Box>
  );

  if (error || !app) return (
    <Box sx={{ p: 6, textAlign: "center" }}>
      <Typography color="text.secondary">{error || "Заявка не найдена"}</Typography>
      <Button onClick={() => navigate("/registry")} sx={{ mt: 2 }}>← Вернуться</Button>
    </Box>
  );

  const date = app.created_at
    ? new Date(app.created_at).toLocaleDateString("ru", { day: "2-digit", month: "long", year: "numeric", hour: "2-digit", minute: "2-digit" })
    : "—";

  const catColor = app.category === "HIGH" ? "success" : app.category === "MEDIUM" ? "warning" : "error";
  const score = Math.round(app.score);

  const shapFactors = app.shap_explanation?.top_factors ?? [];
  const allFactors = app.shap_explanation?.all_factors ?? [];
  const riskFactors = app.shap_explanation?.risk_factors ?? [];
  const positiveFactors = app.shap_explanation?.positive_factors ?? [];

  const peers = analysis?.peers;
  const risks = analysis?.risks ?? [];

  return (
    <Box sx={{ p: { xs: 2.5, md: 4 } }}>
      <Stack spacing={3}>
        {/* Breadcrumbs */}
        <Breadcrumbs sx={{ "& .MuiBreadcrumbs-separator": { mx: 0.5 } }}>
          <MuiLink underline="hover" color="text.secondary" sx={{ cursor: "pointer", fontSize: "0.8125rem", display: "flex", alignItems: "center", gap: 0.5 }}
            onClick={() => navigate("/registry")}>
            <ArrowBack sx={{ fontSize: 14 }} /> Реестр заявок
          </MuiLink>
          <Typography variant="body2" fontWeight={600}>Заявка #{app.id}</Typography>
        </Breadcrumbs>

        {/* Header */}
        <Box sx={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 2 }}>
          <Box>
            <Typography variant="h5">Заявка #{app.id}</Typography>
            <Typography variant="caption">{date} · Модель {app.model_version}</Typography>
          </Box>
          <Stack direction="row" spacing={1} alignItems="center">
            <Chip label={app.category} color={catColor as any} size="small" />
            <Typography variant="caption">Вероятность: {(app.probability * 100).toFixed(1)}%</Typography>
            {(app as any).review_required && (
              <Chip label="Рекомендуется проверка" size="small" color="warning" variant="outlined"
                icon={<Warning sx={{ fontSize: 14 }} />}
              />
            )}
          </Stack>
        </Box>

        {/* Score interpretation */}
        {analysis?.score_interpretation && (
          <Alert
            severity={app.category === "HIGH" ? "success" : app.category === "MEDIUM" ? "warning" : "error"}
            icon={<Info />}
            sx={{ borderRadius: 2 }}
          >
            <Typography variant="body2">{analysis.score_interpretation}</Typography>
          </Alert>
        )}

        {/* Data quality warnings */}
        {(app as any).data_warnings && (app as any).data_warnings.length > 0 && (
          <Alert
            severity={(app as any).review_required ? "info" : "warning"}
            icon={<Warning />}
            sx={{ borderRadius: 2 }}
          >
            <Typography variant="body2" fontWeight={600} mb={0.5}>
              {(app as any).review_required
                ? "ℹ Рекомендуется ручная проверка комиссией"
                : "ℹ Информация о качестве данных"
              }
            </Typography>
            <Typography variant="caption" display="block" mb={1}>
              Некоторые значения в заявке не встречались в обучающих данных модели.
              Оценка скорректирована с учётом неопределённости. Итоговое решение остаётся за комиссией.
            </Typography>
            {(app as any).data_warnings.filter((w: any) => w.field !== "_review").map((w: any, i: number) => (
              <Typography key={i} variant="caption" display="block" sx={{ ml: 1, color: "text.secondary" }}>
                • <b>{w.display_name || w.field}</b>: «{w.value}» — не встречалось в обучении
              </Typography>
            ))}
          </Alert>
        )}

        {/* Info + Score */}
        <Grid container spacing={3} sx={{ alignItems: "stretch" }}>
          <Grid size={{ xs: 12, lg: 8 }}>
            <Card sx={{ height: "100%" }}>
              <CardContent sx={{ p: 3 }}>
                <Typography variant="subtitle2" mb={2}>Информация о заявке</Typography>
                <Grid container spacing={3}>
                  <Grid size={{ xs: 12, sm: 6 }}>
                    <InfoRow label="Область" value={app.region || "—"} />
                    <InfoRow label="Направление" value={app.direction || "—"} />
                    <InfoRow label="Район" value={app.district || "—"} />
                  </Grid>
                  <Grid size={{ xs: 12, sm: 6 }}>
                    <InfoRow label="Акимат" value={app.akimat || "—"} />
                    <InfoRow label="Норматив" value={`₸${(app.normative ?? 0).toLocaleString("ru")}`} />
                    <InfoRow label="Причитающаяся сумма" value={`₸${(app.amount ?? 0).toLocaleString("ru")}`} />
                  </Grid>
                  <Grid size={12}>
                    <InfoRow label="Наименование субсидирования" value={app.subsidy_type || "—"} />
                  </Grid>
                  {app.bin_iin && (
                    <Grid size={12}>
                      <InfoRow label="БИН/ИИН" value={app.bin_iin} />
                    </Grid>
                  )}
                </Grid>
              </CardContent>
            </Card>
          </Grid>
          <Grid size={{ xs: 12, lg: 4 }}>
            <Card sx={{ height: "100%" }}>
              <CardContent sx={{ p: 3, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100%", gap: 2 }}>
                <Typography variant="subtitle2" alignSelf="flex-start">AI-оценка</Typography>
                <ScoreGauge score={score} size={160} />
                <Stack spacing={1} sx={{ width: "100%", mt: 1 }}>
                  <Box sx={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid #f5f5f5", py: 0.8 }}>
                    <Typography variant="caption" color="text.secondary">Категория</Typography>
                    <Chip label={app.category} color={catColor as any} size="small" />
                  </Box>
                  <Box sx={{ display: "flex", justifyContent: "space-between", py: 0.8 }}>
                    <Typography variant="caption" color="text.secondary">Версия модели</Typography>
                    <Typography variant="caption" fontWeight={600}>{app.model_version}</Typography>
                  </Box>
                  {(app as any).review_required && (
                    <Chip label="Рекомендуется проверка" size="small" color="warning" variant="outlined"
                      icon={<Warning sx={{ fontSize: 14 }} />}
                      sx={{ alignSelf: "flex-start", mt: 0.5 }}
                    />
                  )}
                </Stack>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        {/* SHAP Explanation */}
        <Card>
          <CardContent sx={{ p: 3 }}>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 0.5 }}>
              <Typography variant="subtitle2">Объяснение оценки (SHAP)</Typography>
              <Chip label="Explainability" size="small" color="info" variant="outlined" sx={{ fontSize: "0.6875rem" }} />
            </Box>
            <Typography variant="caption" display="block" mb={3}>
              Факторы, повлиявшие на решение модели. Зелёный — повышает вероятность одобрения, красный — снижает.
            </Typography>
            {shapFactors.length > 0 || allFactors.length > 0 ? (
              <ShapWaterfall factors={shapFactors.length > 0 ? shapFactors : allFactors.slice(0, 8)} />
            ) : (
              <Alert severity="info" sx={{ borderRadius: 2 }}>
                SHAP-данные недоступны для этой заявки. Возможно, заявка была оценена старой версией модели.
              </Alert>
            )}
          </CardContent>
        </Card>

        {/* Positive and Negative factors side by side */}
        {(positiveFactors.length > 0 || riskFactors.length > 0) && (
          <Grid container spacing={3}>
            <Grid size={{ xs: 12, md: 6 }}>
              <Card sx={{ height: "100%", border: "1px solid #dcfce7" }}>
                <CardContent sx={{ p: 3 }}>
                  <Stack direction="row" spacing={1} alignItems="center" mb={2}>
                    <TrendingUp sx={{ color: "#22c55e", fontSize: 20 }} />
                    <Typography variant="subtitle2" color="#22c55e">Положительные факторы</Typography>
                  </Stack>
                  {positiveFactors.length > 0 ? (
                    <Stack spacing={1}>
                      {positiveFactors.map((f: any, i: number) => (
                        <Box key={i} sx={{ display: "flex", justifyContent: "space-between", py: 0.8, borderBottom: "1px solid #f5f5f5" }}>
                          <Typography variant="body2">{f.display_name || f.feature}</Typography>
                          <Typography variant="body2" sx={{ fontFamily: "'JetBrains Mono'", color: "#22c55e", fontWeight: 600 }}>
                            +{Number(f.shap_value ?? f.importance ?? 0).toFixed(4)}
                          </Typography>
                        </Box>
                      ))}
                    </Stack>
                  ) : (
                    <Typography variant="body2" color="text.secondary">Нет значимых положительных факторов</Typography>
                  )}
                </CardContent>
              </Card>
            </Grid>
            <Grid size={{ xs: 12, md: 6 }}>
              <Card sx={{ height: "100%", border: "1px solid #fecaca" }}>
                <CardContent sx={{ p: 3 }}>
                  <Stack direction="row" spacing={1} alignItems="center" mb={2}>
                    <TrendingDown sx={{ color: "#ef4444", fontSize: 20 }} />
                    <Typography variant="subtitle2" color="#ef4444">Факторы риска</Typography>
                  </Stack>
                  {riskFactors.length > 0 ? (
                    <Stack spacing={1}>
                      {riskFactors.map((f: any, i: number) => (
                        <Box key={i} sx={{ display: "flex", justifyContent: "space-between", py: 0.8, borderBottom: "1px solid #f5f5f5" }}>
                          <Typography variant="body2">{f.display_name || f.feature}</Typography>
                          <Typography variant="body2" sx={{ fontFamily: "'JetBrains Mono'", color: "#ef4444", fontWeight: 600 }}>
                            {Number(f.shap_value ?? (-f.importance) ?? 0).toFixed(4)}
                          </Typography>
                        </Box>
                      ))}
                    </Stack>
                  ) : (
                    <Typography variant="body2" color="text.secondary">Нет значимых факторов риска</Typography>
                  )}
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        )}

        {/* Risk Assessment (from analysis endpoint) */}
        <Card>
          <CardContent sx={{ p: 3 }}>
            <Stack direction="row" spacing={1} alignItems="center" mb={2}>
              <Security sx={{ color: risks.length > 0 ? "#f59e0b" : "#22c55e", fontSize: 20 }} />
              <Typography variant="subtitle2">Риски и флаги</Typography>
            </Stack>
            {risks.length > 0 ? (
              <Stack spacing={1.5}>
                {risks.map((risk, i) => (
                  <RiskCard key={i} risk={risk} />
                ))}
              </Stack>
            ) : (
              <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, p: 2, bgcolor: "#f0fdf4", borderRadius: 2, border: "1px solid #dcfce7" }}>
                <CheckCircle sx={{ color: "#22c55e", fontSize: 24 }} />
                <Typography variant="body2" color="text.secondary">Рисков не выявлено</Typography>
              </Box>
            )}
          </CardContent>
        </Card>

        {/* Peer Comparison — horizontal bars like the screenshot */}
        <Card>
          <CardContent sx={{ p: 3 }}>
            <Stack direction="row" spacing={1} alignItems="center" mb={2}>
              <CompareArrows sx={{ color: "#3b82f6", fontSize: 20 }} />
              <Typography variant="subtitle2">Сравнение с аналогами</Typography>
            </Stack>
            {peers ? (
              <Stack spacing={1}>
                {/* Current application score */}
                <PeerComparisonBar
                  label="Балл этой заявки"
                  score={app.score}
                  color="#22c55e"
                />

                {/* Region average */}
                {peers.region_stats && peers.region_stats.cnt > 0 && (
                  <PeerComparisonBar
                    label={`Средний по ${app.region || "региону"}`}
                    score={peers.region_stats.mean_score}
                    color="#64748b"
                  />
                )}

                {/* Direction average */}
                {peers.direction_stats && peers.direction_stats.cnt > 0 && (
                  <PeerComparisonBar
                    label="Средний по направлению"
                    score={peers.direction_stats.mean_score}
                    color="#64748b"
                  />
                )}

                {/* Overall average */}
                {peers.total_applications > 0 && (
                  <PeerComparisonBar
                    label="Средний по всем заявкам"
                    score={
                      peers.region_stats?.mean_score && peers.direction_stats?.mean_score
                        ? Math.round(((peers.region_stats.mean_score + peers.direction_stats.mean_score) / 2))
                        : peers.region_stats?.mean_score ?? peers.direction_stats?.mean_score ?? 0
                    }
                    color="#64748b"
                  />
                )}

                {/* Footer stats */}
                {peers.region_stats && peers.region_stats.cnt > 0 && (
                  <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, mt: 1 }}>
                    <Typography variant="caption" color="text.secondary">
                      👥 Заявок по региону: {peers.region_stats.cnt.toLocaleString("ru")}
                      {peers.percentile !== undefined && ` · Перцентиль: ${peers.percentile}%`}
                    </Typography>
                  </Box>
                )}

                {!peers.region_stats && !peers.direction_stats && !peers.subsidy_stats && (
                  <Typography variant="body2" color="text.secondary" textAlign="center" py={2}>
                    Нет аналогичных заявок для сравнения. Загрузите больше заявок для анализа.
                  </Typography>
                )}
              </Stack>
            ) : (
              <Typography variant="body2" color="text.secondary" textAlign="center" py={2}>
                Данные для сравнения загружаются…
              </Typography>
            )}
          </CardContent>
        </Card>

        {/* Similar Applications Table */}
        {peers?.similar_apps && peers.similar_apps.length > 0 && (
          <Card>
            <CardContent sx={{ p: 3 }}>
              <Typography variant="subtitle2" mb={2}>Похожие заявки (тот же регион)</Typography>
              <TableContainer sx={{ maxHeight: 300 }}>
                <Table size="small" stickyHeader>
                  <TableHead>
                    <TableRow>
                      <TableCell width={50}>#</TableCell>
                      <TableCell width={70}>Балл</TableCell>
                      <TableCell>Категория</TableCell>
                      <TableCell>Направление</TableCell>
                      <TableCell>Вид субсидии</TableCell>
                      <TableCell align="right">Сумма</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {peers.similar_apps.map((sa) => (
                      <TableRow
                        key={sa.id} hover sx={{ cursor: "pointer" }}
                        onClick={() => navigate(`/app/${sa.id}`)}
                      >
                        <TableCell sx={{ fontFamily: "'JetBrains Mono'", color: "text.secondary" }}>{sa.id}</TableCell>
                        <TableCell><ScoreBadge score={Math.round(sa.score)} size="sm" /></TableCell>
                        <TableCell>
                          <Chip
                            label={sa.category} size="small" variant="outlined"
                            color={sa.category === "HIGH" ? "success" : sa.category === "MEDIUM" ? "warning" : "error"}
                          />
                        </TableCell>
                        <TableCell sx={{ color: "text.secondary" }}>{sa.direction || "—"}</TableCell>
                        <TableCell sx={{ color: "text.secondary", maxWidth: 200 }}>
                          <Typography variant="body2" noWrap title={sa.subsidy_type}>{sa.subsidy_type || "—"}</Typography>
                        </TableCell>
                        <TableCell align="right" sx={{ fontFamily: "'JetBrains Mono'", fontWeight: 600 }}>
                          ₸{(sa.amount ?? 0).toLocaleString("ru")}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        )}

        {/* All SHAP factors table */}
        {allFactors.length > 0 && (
          <Card>
            <CardContent sx={{ p: 3 }}>
              <Typography variant="subtitle2" mb={2}>Все факторы SHAP ({allFactors.length})</Typography>
              <Box sx={{ maxHeight: 400, overflow: "auto" }}>
                {allFactors.map((f: any, i: number) => (
                  <Box key={i} sx={{ display: "flex", justifyContent: "space-between", py: 0.8, borderBottom: "1px solid #f5f5f5", alignItems: "center" }}>
                    <Tooltip title={f.feature} placement="left">
                      <Typography variant="body2" sx={{ flex: 1 }}>{f.display_name || f.feature}</Typography>
                    </Tooltip>
                    <Typography variant="body2" sx={{ width: 100, textAlign: "right", fontFamily: "'JetBrains Mono'", color: "text.secondary" }}>
                      {Number(f.value).toFixed(2)}
                    </Typography>
                    <Typography variant="body2" sx={{
                      width: 110, textAlign: "right", fontFamily: "'JetBrains Mono'",
                      color: (f.shap_value ?? 0) >= 0 ? "#22c55e" : "#ef4444", fontWeight: 600,
                    }}>
                      {(f.shap_value ?? 0) >= 0 ? "+" : ""}{Number(f.shap_value ?? 0).toFixed(4)}
                    </Typography>
                  </Box>
                ))}
              </Box>
            </CardContent>
          </Card>
        )}
      </Stack>
    </Box>
  );
}
