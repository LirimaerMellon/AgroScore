import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router";
import {
  Box, Card, CardContent, Typography, Button, Grid, Stack, Alert,
  Table, TableHead, TableBody, TableRow, TableCell, TableContainer, Chip, LinearProgress,
} from "@mui/material";
import { Download, CloudUpload, CheckCircle, Warning } from "@mui/icons-material";
import { downloadTemplate, scoreFromFile, downloadExport, fetchHealth } from "../data/api";
import { ScoreBadge } from "../components/ScoreBadge";

function fmt(n: number) {
  if (n >= 1e9) return `₸${(n / 1e9).toFixed(1)} млрд`;
  if (n >= 1e6) return `₸${(n / 1e6).toFixed(1)} млн`;
  return `₸${n.toLocaleString("ru")}`;
}

export function Scoring() {
  const navigate = useNavigate();
  const fileRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState("");
  const [modelLoaded, setModelLoaded] = useState<boolean | null>(null);
  const [activeModel, setActiveModel] = useState<string | null>(null);

  useEffect(() => {
    fetchHealth()
      .then((h) => {
        setModelLoaded(h.model_loaded);
        setActiveModel(h.active_model);
      })
      .catch(() => setModelLoaded(false));
  }, [result]);

  async function handleUpload(file: File) {
    setUploading(true);
    setError("");
    setResult(null);
    try {
      const res = await scoreFromFile(file);
      setResult(res);
    } catch (e: any) {
      setError(e.message || "Ошибка скоринга");
    }
    setUploading(false);
  }

  const apps = result?.applications ?? [];
  const categories = result?.categories ?? {};

  return (
    <Box sx={{ p: { xs: 2.5, md: 4 } }}>
      <Stack spacing={3}>
        <Box>
          <Typography variant="h5">Скоринг заявок</Typography>
          <Typography variant="caption">Загрузите файл с заявками для AI-оценки или скачайте пустой шаблон</Typography>
        </Box>

        {modelLoaded === false && (
          <Alert
            severity="warning"
            icon={<Warning />}
            action={
               <Button color="inherit" size="small" onClick={() => navigate("/models")}>
                Перейти к обучению
              </Button>
            }
            sx={{ borderRadius: 2 }}
          >
            <Typography variant="body2" fontWeight={600}>Модель не обучена</Typography>
            <Typography variant="caption">
              Для оценки заявок необходимо сначала обучить модель. Перейдите на страницу «Модели» и загрузите исторические данные для обучения.
            </Typography>
          </Alert>
        )}

        {modelLoaded === true && activeModel && (
          <Alert severity="success" sx={{ borderRadius: 2 }}>
            Активная модель: <b>{activeModel}</b> — готова к скорингу
          </Alert>
        )}

        {/* Actions */}
        <Grid container spacing={3}>
          <Grid size={{ xs: 12, md: 6 }}>
            <Card sx={{ height: "100%" }}>
              <CardContent sx={{ p: 3, display: "flex", flexDirection: "column", alignItems: "center", gap: 2, textAlign: "center" }}>
                <Download sx={{ fontSize: 40, color: "primary.main" }} />
                <Typography variant="subtitle2">Скачать шаблон</Typography>
                <Typography variant="caption" color="text.secondary">
                  Скачайте пустой Excel-шаблон, заполните данными заявок и загрузите обратно для скоринга
                </Typography>
                <Button variant="outlined" startIcon={<Download />} onClick={downloadTemplate}>
                  Скачать шаблон Excel
                </Button>
              </CardContent>
            </Card>
          </Grid>
          <Grid size={{ xs: 12, md: 6 }}>
            <Card sx={{ height: "100%", border: uploading ? "2px solid #22c55e" : undefined }}>
              <CardContent sx={{ p: 3, display: "flex", flexDirection: "column", alignItems: "center", gap: 2, textAlign: "center" }}>
                <CloudUpload sx={{ fontSize: 40, color: "#3b82f6" }} />
                <Typography variant="subtitle2">Загрузить для скоринга</Typography>
                <Typography variant="caption" color="text.secondary">
                  Загрузите заполненный шаблон (Excel/CSV) — модель оценит каждую заявку и покажет результат
                </Typography>
                <input ref={fileRef} type="file" accept=".xlsx,.xls,.csv" hidden
                  onChange={(e) => { if (e.target.files?.[0]) handleUpload(e.target.files[0]); }} />
                <Button variant="contained" startIcon={<CloudUpload />} disabled={uploading}
                  onClick={() => fileRef.current?.click()}>
                  {uploading ? "Оценка…" : "Загрузить файл"}
                </Button>
                {uploading && <LinearProgress sx={{ width: "100%", borderRadius: 2 }} />}
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        {error && <Alert severity="error" sx={{ borderRadius: 2 }}>{error}</Alert>}

        {/* Warnings about data quality */}
        {result?.warnings && result.warnings.length > 0 && (
          <Alert severity="warning" sx={{ borderRadius: 2 }}>
            <Typography variant="body2" fontWeight={600}>⚠ Предупреждения о качестве данных</Typography>
            {result.warnings.map((w: string, i: number) => (
              <Typography key={i} variant="caption" display="block">{w}</Typography>
            ))}
          </Alert>
        )}

        {/* Results */}
        {result && (
          <>
            <Card>
              <CardContent sx={{ p: 3 }}>
                <Stack direction="row" spacing={2} alignItems="center" flexWrap="wrap">
                  <CheckCircle color="success" />
                  <Typography variant="subtitle2">Скоринг завершён</Typography>
                  <Chip label={`Модель ${result.model_version}`} size="small" color="primary" variant="outlined" />
                  <Typography variant="body2" color="text.secondary">
                    {result.total_scored} из {result.total_raw} строк оценено
                  </Typography>
                  {result.trace_id && (
                    <Chip label={`trace: ${result.trace_id.slice(0, 8)}…`} size="small" variant="outlined"
                      onClick={() => navigate(`/errors?trace=${result.trace_id}`)} sx={{ cursor: "pointer" }} />
                  )}
                </Stack>
                <Grid container spacing={2} mt={1}>
                  {[
                    { label: "HIGH", count: categories.HIGH ?? 0, color: "#22c55e" },
                    { label: "MEDIUM", count: categories.MEDIUM ?? 0, color: "#f59e0b" },
                    { label: "LOW", count: categories.LOW ?? 0, color: "#ef4444" },
                  ].map(({ label, count, color }) => (
                    <Grid size={{ xs: 4 }} key={label}>
                      <Box sx={{ textAlign: "center", p: 1.5, bgcolor: `${color}08`, borderRadius: 2 }}>
                        <Typography variant="h6" fontFamily="'JetBrains Mono'" color={color}>{count}</Typography>
                        <Typography variant="caption">{label}</Typography>
                      </Box>
                    </Grid>
                  ))}
                </Grid>
              </CardContent>
            </Card>

            <Card>
              <Box sx={{ px: 3, py: 2, borderBottom: "1px solid #f0f0f0", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <Typography variant="subtitle2">{apps.length} оценённых заявок</Typography>
                <Button size="small" startIcon={<Download />} onClick={() => downloadExport(result.model_version)}>
                  Экспорт Excel
                </Button>
              </Box>
              <TableContainer sx={{ maxHeight: 500 }}>
                <Table stickyHeader size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell width={50}>#</TableCell>
                      <TableCell width={60}>Балл</TableCell>
                      <TableCell>Категория</TableCell>
                      <TableCell>Область</TableCell>
                      <TableCell>Направление</TableCell>
                      <TableCell align="right">Сумма</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {apps.map((app: any, i: number) => (
                      <TableRow key={app.id ?? i} hover sx={{ cursor: app.id ? "pointer" : "default" }}
                        onClick={() => app.id && navigate(`/app/${app.id}`)}>
                        <TableCell sx={{ fontFamily: "'JetBrains Mono'" }}>{i + 1}</TableCell>
                        <TableCell><ScoreBadge score={Math.round(app.score)} size="sm" /></TableCell>
                        <TableCell>
                          <Chip label={app.category} size="small" variant="outlined"
                            color={app.category === "HIGH" ? "success" : app.category === "MEDIUM" ? "warning" : "error"} />
                        </TableCell>
                        <TableCell>{app.region || "—"}</TableCell>
                        <TableCell sx={{ color: "text.secondary" }}>{app.direction || "—"}</TableCell>
                        <TableCell align="right" sx={{ fontFamily: "'JetBrains Mono'", fontWeight: 600 }}>{fmt(app.amount ?? 0)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </Card>
          </>
        )}
      </Stack>
    </Box>
  );
}
