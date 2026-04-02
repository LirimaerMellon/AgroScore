import { useState, useEffect, useCallback } from "react";
import { useSearchParams } from "react-router";
import {
  Box, Card, CardContent, Typography, Stack, Chip, CircularProgress,
  Table, TableHead, TableBody, TableRow, TableCell, TableContainer, TablePagination,
  Collapse, Grid, Button, Alert,
} from "@mui/material";
import { BugReport, ExpandMore, ExpandLess, Refresh } from "@mui/icons-material";
import { Fragment } from "react";
import {
  fetchTraces, fetchErrors, fetchErrorSummary,
  type TraceItem, type ErrorLogItem, type ErrorSummary,
} from "../data/api";

export function ErrorLogs() {
  const [searchParams] = useSearchParams();
  const initialTrace = searchParams.get("trace") || "";

  const [traces, setTraces] = useState<TraceItem[]>([]);
  const [selectedTrace, setSelectedTrace] = useState<string>(initialTrace);
  const [errors, setErrors] = useState<ErrorLogItem[]>([]);
  const [errTotal, setErrTotal] = useState(0);
  const [summary, setSummary] = useState<ErrorSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [errLoading, setErrLoading] = useState(false);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(50);
  const [expandedRow, setExpandedRow] = useState<number | null>(null);

  // Load traces
  useEffect(() => {
    fetchTraces(100).then((r) => setTraces(r.traces)).catch(() => {}).finally(() => setLoading(false));
  }, []);

  // Load errors for selected trace or all
  const loadErrors = useCallback(async () => {
    setErrLoading(true);
    try {
      const [errs, sum] = await Promise.all([
        fetchErrors({ trace_id: selectedTrace || undefined, limit: rowsPerPage, offset: page * rowsPerPage }),
        fetchErrorSummary(selectedTrace || undefined),
      ]);
      setErrors(errs.items);
      setErrTotal(errs.total);
      setSummary(sum);
    } catch { /* graceful */ }
    setErrLoading(false);
  }, [selectedTrace, page, rowsPerPage]);

  useEffect(() => { loadErrors(); }, [loadErrors]);

  if (loading) return (
    <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", height: "60vh" }}>
      <CircularProgress />
    </Box>
  );

  return (
    <Box sx={{ p: { xs: 2.5, md: 4 } }}>
      <Stack spacing={3}>
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <Box>
            <Typography variant="h5">Лог ошибок</Typography>
            <Typography variant="caption">Ошибки валидации данных при загрузке файлов</Typography>
          </Box>
          <Button startIcon={<Refresh />} size="small" onClick={loadErrors}>Обновить</Button>
        </Box>

        {/* Summary */}
        {summary && summary.total_errors > 0 && (
          <Grid container spacing={2}>
            <Grid size={{ xs: 12, md: 4 }}>
              <Card>
                <CardContent sx={{ p: 2.5 }}>
                  <Typography variant="caption" fontWeight={600}>Всего ошибок</Typography>
                  <Typography variant="h4" fontFamily="'JetBrains Mono'" color="error.main">{summary.total_errors}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid size={{ xs: 12, md: 4 }}>
              <Card>
                <CardContent sx={{ p: 2.5 }}>
                  <Typography variant="caption" fontWeight={600}>По кодам ошибок</Typography>
                  <Stack direction="row" spacing={0.5} mt={1} flexWrap="wrap" useFlexGap>
                    {Object.entries(summary.by_error_code).map(([code, cnt]) => (
                      <Chip key={code} label={`${code}: ${cnt}`} size="small" variant="outlined" color="error" />
                    ))}
                  </Stack>
                </CardContent>
              </Card>
            </Grid>
            <Grid size={{ xs: 12, md: 4 }}>
              <Card>
                <CardContent sx={{ p: 2.5 }}>
                  <Typography variant="caption" fontWeight={600}>По колонкам</Typography>
                  <Stack direction="row" spacing={0.5} mt={1} flexWrap="wrap" useFlexGap>
                    {Object.entries(summary.by_column).map(([col, cnt]) => (
                      <Chip key={col} label={`${col}: ${cnt}`} size="small" variant="outlined" color="warning" />
                    ))}
                  </Stack>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        )}

        {/* Traces list */}
        {traces.length > 0 && (
          <Card>
            <CardContent sx={{ p: 2.5 }}>
              <Typography variant="subtitle2" mb={1.5}>Загрузки с ошибками</Typography>
              <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                <Chip label="Все" size="small" variant={selectedTrace === "" ? "filled" : "outlined"}
                  color={selectedTrace === "" ? "primary" : "default"}
                  onClick={() => { setSelectedTrace(""); setPage(0); }} />
                {traces.map((t) => (
                  <Chip key={t.trace_id} size="small"
                    variant={selectedTrace === t.trace_id ? "filled" : "outlined"}
                    color={selectedTrace === t.trace_id ? "primary" : "default"}
                    label={`${t.source_name} (${t.error_count} ош.)`}
                    onClick={() => { setSelectedTrace(t.trace_id); setPage(0); }}
                    title={`trace: ${t.trace_id}\n${t.first_detected}`}
                  />
                ))}
              </Stack>
            </CardContent>
          </Card>
        )}

        {/* Errors table */}
        <Card>
          {errLoading ? (
            <Box sx={{ display: "flex", justifyContent: "center", py: 6 }}><CircularProgress size={28} /></Box>
          ) : errors.length === 0 ? (
            <CardContent sx={{ textAlign: "center", py: 8 }}>
              <BugReport sx={{ fontSize: 40, color: "#d1d5db" }} />
              <Typography variant="body2" color="text.secondary" mt={1}>Ошибок не обнаружено</Typography>
            </CardContent>
          ) : (
            <>
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell width={40} />
                      <TableCell width={60}>ID</TableCell>
                      <TableCell>Источник</TableCell>
                      <TableCell>Коды ошибок</TableCell>
                      <TableCell>Колонки</TableCell>
                      <TableCell width={140}>Дата</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {errors.map((err) => {
                      const isOpen = expandedRow === err.id;
                      return (
                        <Fragment key={err.id}>
                          <TableRow hover sx={{ cursor: "pointer" }} onClick={() => setExpandedRow(isOpen ? null : err.id)}>
                            <TableCell>{isOpen ? <ExpandLess fontSize="small" /> : <ExpandMore fontSize="small" />}</TableCell>
                            <TableCell sx={{ fontFamily: "'JetBrains Mono'" }}>{err.id}</TableCell>
                            <TableCell>
                              <Typography variant="body2" fontWeight={500}>{err.source_name}</Typography>
                              <Typography variant="caption" color="text.secondary">{err.source_type}</Typography>
                            </TableCell>
                            <TableCell>
                              <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
                                {err.error_codes.map((c, i) => <Chip key={i} label={c} size="small" color="error" variant="outlined" />)}
                              </Stack>
                            </TableCell>
                            <TableCell>
                              <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
                                {err.error_cols.map((c, i) => <Chip key={i} label={c} size="small" variant="outlined" />)}
                              </Stack>
                            </TableCell>
                            <TableCell sx={{ fontFamily: "'JetBrains Mono'", fontSize: "0.75rem" }}>
                              {new Date(err.detected_at).toLocaleString("ru")}
                            </TableCell>
                          </TableRow>
                          <TableRow>
                            <TableCell colSpan={6} sx={{ py: 0, border: isOpen ? undefined : 0 }}>
                              <Collapse in={isOpen}>
                                <Box sx={{ p: 2, bgcolor: "#f9fafb", borderRadius: 2, my: 1 }}>
                                  <Grid container spacing={2}>
                                    <Grid size={{ xs: 12, md: 6 }}>
                                      <Typography variant="caption" fontWeight={600}>Trace ID</Typography>
                                      <Typography variant="body2" fontFamily="'JetBrains Mono'" fontSize="0.75rem">{err.trace_id}</Typography>
                                    </Grid>
                                    <Grid size={{ xs: 12, md: 6 }}>
                                      <Typography variant="caption" fontWeight={600}>Locator</Typography>
                                      <Typography variant="body2" fontFamily="'JetBrains Mono'" fontSize="0.75rem">
                                        {JSON.stringify(err.locator)}
                                      </Typography>
                                    </Grid>
                                    {err.violations && err.violations.length > 0 && (
                                      <Grid size={12}>
                                        <Typography variant="caption" fontWeight={600}>Нарушения</Typography>
                                        <Stack spacing={0.5} mt={0.5}>
                                          {err.violations.map((v: any, i: number) => (
                                            <Alert key={i} severity="warning" sx={{ py: 0, borderRadius: 1 }}>
                                              <Typography variant="caption">
                                                <b>{v.code}</b> [{v.cols?.join(", ")}]: {v.display || v.msg}
                                              </Typography>
                                            </Alert>
                                          ))}
                                        </Stack>
                                      </Grid>
                                    )}
                                    {err.raw_payload && (
                                      <Grid size={12}>
                                        <Typography variant="caption" fontWeight={600}>Исходные данные строки</Typography>
                                        <Box sx={{ mt: 0.5, p: 1.5, bgcolor: "white", borderRadius: 1, border: "1px solid #e5e7eb", maxHeight: 200, overflow: "auto" }}>
                                          <pre style={{ margin: 0, fontSize: 11, fontFamily: "'JetBrains Mono', monospace", whiteSpace: "pre-wrap" }}>
                                            {JSON.stringify(err.raw_payload, null, 2)}
                                          </pre>
                                        </Box>
                                      </Grid>
                                    )}
                                  </Grid>
                                </Box>
                              </Collapse>
                            </TableCell>
                          </TableRow>
                        </Fragment>
                      );
                    })}
                  </TableBody>
                </Table>
              </TableContainer>
              <TablePagination
                component="div" count={errTotal} page={page} rowsPerPage={rowsPerPage}
                onPageChange={(_, p) => setPage(p)}
                onRowsPerPageChange={(e) => { setRowsPerPage(parseInt(e.target.value)); setPage(0); }}
                rowsPerPageOptions={[25, 50, 100]}
                labelRowsPerPage="Строк:"
                labelDisplayedRows={({ from, to, count }) => `${from}–${to} из ${count}`}
              />
            </>
          )}
        </Card>
      </Stack>
    </Box>
  );
}

