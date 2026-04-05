import { useParams, useNavigate } from "react-router";
import { useState, useEffect } from "react";
import {
  Box, Card, CardContent, Typography, Button, Chip, Grid, Stack,
  Breadcrumbs, Link as MuiLink, CircularProgress, Alert,
  Dialog, DialogTitle, DialogContent, IconButton,
} from "@mui/material";
import {
  ArrowBack, Warning,
  CompareArrows, Close, ZoomIn,
} from "@mui/icons-material";
import {
  fetchApplication, fetchApplicationAnalysis, fetchShapExplanation,
  type ApplicationItem, type ApplicationAnalysis, type ShapResponse,
} from "../data/api";
import { ScoreGauge } from "../components/ScoreGauge";
import { ShapWaterfall, type ShapEntry } from "../components/ShapWaterfall";
import { featureDisplayName } from "../data/featureNames";

function InfoRow({ label, value }: { label: string; value: string | number }) {
  return (
    <Box sx={{ py: 1.5, borderBottom: "1px solid #f5f5f5", "&:last-child": { borderBottom: 0 } }}>
      <Typography variant="caption" fontWeight={600} textTransform="uppercase" letterSpacing={0.5}>{label}</Typography>
      <Typography variant="body2" fontWeight={500} mt={0.3}>{value}</Typography>
    </Box>
  );
}

function PeerComparisonBar({
  label, score, maxScore = 100, color = "#64748b", count,
}: { label: string; score: number; maxScore?: number; color?: string; count?: number }) {
  return (
    <Box sx={{ mb: 2 }}>
      <Box sx={{ display: "flex", justifyContent: "space-between", mb: 0.5 }}>
        <Typography variant="body2" color="text.secondary">
          {label}{count != null ? ` (${count} заявок)` : ""}
        </Typography>
        <Typography variant="body2" fontWeight={700} fontFamily="'JetBrains Mono'" color={color}>{Math.round(score)}</Typography>
      </Box>
      <Box sx={{ height: 14, bgcolor: "#f1f5f9", borderRadius: 5, overflow: "hidden" }}>
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

/** Маппинг полей для баннера доп. проверки */
const FIELD_DISPLAY: Record<string, string> = {
  district: "Район",
  subsidy_type: "Вид субсидии",
  direction: "Направление",
};

export function AppDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [app, setApp] = useState<ApplicationItem | null>(null);
  const [analysis, setAnalysis] = useState<ApplicationAnalysis | null>(null);
  const [shapData, setShapData] = useState<ShapResponse | null>(null);
  const [shapDetailed, setShapDetailed] = useState<ShapResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [shapModal, setShapModal] = useState(false);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    Promise.allSettled([
      fetchApplication(Number(id)),
      fetchApplicationAnalysis(Number(id)),
      fetchShapExplanation(Number(id), false),
    ]).then(([appRes, analysisRes, shapRes]) => {
      if (appRes.status === "fulfilled") setApp(appRes.value.application);
      else setError(appRes.reason?.message || "Не удалось загрузить заявку");
      if (analysisRes.status === "fulfilled") setAnalysis(analysisRes.value);
      if (shapRes.status === "fulfilled") setShapData(shapRes.value);
    }).finally(() => setLoading(false));
  }, [id]);

  const openDetailedModal = async () => {
    setShapModal(true);
    if (!shapDetailed && id) {
      try {
        const detailed = await fetchShapExplanation(Number(id), true);
        setShapDetailed(detailed);
      } catch { /* ignore */ }
    }
  };

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
  // Используем SHAP-балл если доступен — гарантирует совпадение gauge и waterfall
  const score = shapData?.score != null ? Math.round(shapData.score) : Math.round(app.score);
  const needsReview = app.review_required === true;
  const dataWarnings: Array<{ field: string; display_name: string; value: string; message: string }> =
    (app.data_warnings ?? []).filter((w: any) => w.field !== "_review");

  // SHAP factors: from new endpoint or fallback to legacy
  const shapFactors: ShapEntry[] = shapData
    ? shapData.factors.map((f) => ({ feature: f.feature, display_name: featureDisplayName(f.feature), shap_points: f.shap_points }))
    : (app.shap_explanation?.all_factors ?? app.shap_explanation?.top_factors ?? []);

  const baseScore: number = shapData?.base_value ?? app.shap_explanation?.base_score ?? 50;
  const predictedScore: number = shapData?.score ?? score;

  // All factors for detailed modal (from rest.factors or legacy)
  const allDetailedFactors: ShapEntry[] = shapDetailed
    ? [
        ...shapDetailed.factors.map((f) => ({ feature: f.feature, display_name: featureDisplayName(f.feature), shap_points: f.shap_points })),
        ...(shapDetailed.rest?.factors?.map((f) => ({ feature: f.feature, display_name: featureDisplayName(f.feature), shap_points: f.shap_points })) ?? []),
      ]
    : (app.shap_explanation?.all_factors ?? []);

  const restCount = shapData?.rest?.count ?? 0;
  const restSum = shapData?.rest?.shap_points ?? 0;

  const peers = analysis?.peers;

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
            {needsReview && (
              <Chip label="Доп. проверка" size="small" color="warning" variant="outlined"
                icon={<Warning sx={{ fontSize: 14 }} />}
              />
            )}
          </Stack>
        </Box>

        {/* Баннер доп. проверки */}
        {needsReview && (
          <Alert
            severity="warning"
            icon={<Warning />}
            sx={{ borderRadius: 2 }}
          >
            <Typography variant="body2" fontWeight={600} mb={0.5}>
              Рекомендуется дополнительная проверка комиссией
            </Typography>
            {dataWarnings.length > 0 ? (
              dataWarnings.map((w, i) => (
                <Typography key={i} variant="caption" display="block" sx={{ ml: 1, color: "text.secondary" }}>
                  • <b>{FIELD_DISPLAY[w.field] || w.display_name || w.field}</b>: «{w.value}» — не встречалось в обучающих данных
                </Typography>
              ))
            ) : (
              /* Фоллбэк для старых заявок без data_warnings — показать unknown_fields */
              (app.unknown_fields ?? []).map((field: string, i: number) => {
                const rawVal = (app as any)[field];
                return (
                  <Typography key={i} variant="caption" display="block" sx={{ ml: 1, color: "text.secondary" }}>
                    • <b>{FIELD_DISPLAY[field] || field}</b>{rawVal ? <>: «{rawVal}»</> : ""} — не встречалось в обучающих данных
                  </Typography>
                );
              })
            )}
          </Alert>
        )}

        {/* Info + Score */}
        <Grid container spacing={3} sx={{ alignItems: "stretch" }}>
          <Grid size={{ xs: 12, lg: 8 }}>
            <Card sx={{ height: "100%", border: "none" }}>
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
                    <InfoRow label="Вид субсидии" value={app.subsidy_type || "—"} />
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
            <Card sx={{ height: "100%", border: "none" }}>
              <CardContent sx={{ p: 3, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100%", gap: 2 }}>
                <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", width: "100%" }}>
                  <Typography variant="subtitle2">AI-оценка</Typography>
                </Box>
                <ScoreGauge score={score} size={160} category={app.category} />
                <Stack spacing={1} sx={{ width: "100%", mt: 1 }}>
                  <Box sx={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid #f5f5f5", py: 0.8 }}>
                    <Typography variant="caption" color="text.secondary">Категория</Typography>
                    <Chip label={shapData?.category ?? app.category} color={catColor as any} size="small" />
                  </Box>
                  {shapData?.fits_budget != null && (
                    <Box sx={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid #f5f5f5", py: 0.8 }}>
                      <Typography variant="caption" color="text.secondary">В рамках бюджета</Typography>
                      <Chip
                        label={shapData.fits_budget ? "Да" : "Нет"}
                        size="small"
                        color={shapData.fits_budget ? "success" : "default"}
                        variant="outlined"
                      />
                    </Box>
                  )}
                  <Box sx={{ display: "flex", justifyContent: "space-between", py: 0.8 }}>
                    <Typography variant="caption" color="text.secondary">Версия модели</Typography>
                    <Typography variant="caption" fontWeight={600}>{app.model_version}</Typography>
                  </Box>
                </Stack>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        {/* SHAP Explanation */}
        <Card>
          <CardContent sx={{ p: 3 }}>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 2 }}>
              <Typography variant="subtitle2">Объяснение оценки</Typography>
              <Chip label="SHAP" size="small" color="info" variant="outlined" sx={{ fontSize: "0.6875rem" }} />
            </Box>

            {shapFactors.length > 0 ? (
              <>
                <ShapWaterfall
                  factors={shapFactors}
                  baseScore={baseScore}
                  predictedScore={predictedScore}
                  maxBars={5}
                  restShapPoints={restSum}
                  restCount={restCount}
                />
                {(restCount > 0 || allDetailedFactors.length > 5) && (
                  <Box sx={{ textAlign: "center", mt: 1.5 }}>
                    <Button
                      size="small" variant="text" startIcon={<ZoomIn />}
                      onClick={openDetailedModal}
                      sx={{ fontSize: "0.8125rem", textTransform: "none" }}
                    >
                      Подробнее — все факторы
                    </Button>
                  </Box>
                )}
                {/* Disclaimer */}
                <Typography
                  variant="caption"
                  display="block"
                  mt={2}
                  color="text.secondary"
                  textAlign="center"
                  sx={{ fontStyle: "italic" }}
                >
                  AI-оценка носит рекомендательный характер. Итоговое решение принимает комиссия.
                </Typography>
              </>
            ) : (
              <Alert severity="info" sx={{ borderRadius: 2 }}>
                SHAP-данные недоступны для этой заявки.
              </Alert>
            )}
          </CardContent>
        </Card>

        {/* Peer Comparison */}
        <Card>
          <CardContent sx={{ p: 3 }}>
            <Stack direction="row" spacing={1} alignItems="center" mb={2}>
              <CompareArrows sx={{ color: "#3b82f6", fontSize: 20 }} />
              <Typography variant="subtitle2">Сравнение с аналогами</Typography>
            </Stack>
            {peers ? (
              <Stack spacing={0}>
                {/* Средний по виду субсидии */}
                {peers.subsidy_stats && peers.subsidy_stats.cnt >= 10 ? (
                  <PeerComparisonBar
                    label={`Средний по виду субсидии`}
                    score={peers.subsidy_stats.mean_score}
                    color="#3b82f6"
                    count={peers.subsidy_stats.cnt}
                  />
                ) : (
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2, fontStyle: "italic" }}>
                    Средний по виду субсидии — недостаточно данных для сравнения
                  </Typography>
                )}

                {/* Средний по району */}
                {peers.district_stats && peers.district_stats.cnt >= 10 ? (
                  <PeerComparisonBar
                    label={`Средний по району`}
                    score={peers.district_stats.mean_score}
                    color="#38bdf8"
                    count={peers.district_stats.cnt}
                  />
                ) : (
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2, fontStyle: "italic" }}>
                    Средний по району — недостаточно данных для сравнения
                  </Typography>
                )}

                {/* Средний по всем заявкам */}
                {peers.global_stats && peers.global_stats.cnt >= 10 ? (
                  <PeerComparisonBar
                    label={`Средний по всем заявкам`}
                    score={peers.global_stats.mean_score}
                    color="#64748b"
                    count={peers.global_stats.cnt}
                  />
                ) : (
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2, fontStyle: "italic" }}>
                    Средний по всем заявкам — недостаточно данных для сравнения
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

        {/* SHAP Detail Modal */}
        <Dialog
          open={shapModal}
          onClose={() => setShapModal(false)}
          maxWidth="lg"
          fullWidth
          PaperProps={{ sx: { borderRadius: 3 } }}
        >
          <DialogTitle sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", pb: 1 }}>
            <Typography variant="subtitle1" fontWeight={600}>
              Все факторы SHAP
            </Typography>
            <IconButton size="small" onClick={() => setShapModal(false)}><Close fontSize="small" /></IconButton>
          </DialogTitle>
          <DialogContent sx={{ pt: 1 }}>
            <Typography variant="caption" display="block" mb={2} color="text.secondary">
              Полный список факторов, повлиявших на оценку. Зелёный — повышает балл, красный — снижает.
            </Typography>
            <Box sx={{ maxHeight: "70vh", overflowY: "auto", overflowX: "hidden", minWidth: 0 }}>
              <ShapWaterfall
                factors={allDetailedFactors}
                baseScore={baseScore}
                predictedScore={predictedScore}
                showAll
              />
            </Box>
            <Typography
              variant="caption"
              display="block"
              mt={2}
              color="text.secondary"
              textAlign="center"
              sx={{ fontStyle: "italic" }}
            >
              AI-оценка носит рекомендательный характер. Итоговое решение принимает комиссия.
            </Typography>
          </DialogContent>
        </Dialog>
      </Stack>
    </Box>
  );
}
