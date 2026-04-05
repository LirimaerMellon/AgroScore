import { useState, useEffect, useCallback } from "react";
import {
  Box, Card, CardContent, Typography, Stack, Chip, CircularProgress,
  Table, TableHead, TableBody, TableRow, TableCell, TableContainer, TablePagination,
  Collapse, Grid, Button, Alert, TableSortLabel, TextField, Autocomplete, InputAdornment,
} from "@mui/material";
import { BugReport, ExpandMore, ExpandLess, Refresh, FilterAltOff, FilterList, Search } from "@mui/icons-material";
import { Fragment } from "react";
import { useRef } from "react";
import {
  fetchErrors, fetchErrorSummary,
  type ErrorLogItem, type ErrorSummary,
} from "../data/api";

type SortField = "id" | "detected_at";
type SortDir = "asc" | "desc";

export function ErrorLogs() {
  const [errors, setErrors] = useState<ErrorLogItem[]>([]);
  const [errTotal, setErrTotal] = useState(0);
  const [summary, setSummary] = useState<ErrorSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [errLoading, setErrLoading] = useState(false);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(50);
  const [expandedRow, setExpandedRow] = useState<number | null>(null);

  // Sorting
  const [sortBy, setSortBy] = useState<SortField>("detected_at");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  // Filters
  const [filterCode, setFilterCode] = useState<string>("");
  const [filterCol, setFilterCol] = useState<string>("");
  const [showFilters, setShowFilters] = useState(false);

  // Search
  const [searchText, setSearchText] = useState("");
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();

  // Load summary for filter options
  useEffect(() => {
    fetchErrorSummary().then(setSummary).catch(() => {}).finally(() => setLoading(false));
  }, []);

  // Load errors
  const loadErrors = useCallback(async () => {
    setErrLoading(true);
    try {
      const result = await fetchErrors({
        error_code: filterCode || undefined,
        error_col: filterCol || undefined,
        source_name: searchText || undefined,
        sort_by: sortBy,
        sort_dir: sortDir,
        limit: rowsPerPage,
        offset: page * rowsPerPage,
      });
      setErrors(result.items);
      setErrTotal(result.total);
    } catch { /* graceful */ }
    setErrLoading(false);
  }, [filterCode, filterCol, searchText, sortBy, sortDir, page, rowsPerPage]);

  useEffect(() => { loadErrors(); }, [loadErrors]);

  const handleSort = (field: SortField) => {
    if (sortBy === field) {
      setSortDir((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortBy(field);
      setSortDir("desc");
    }
    setPage(0);
  };

  const clearFilters = () => {
    setFilterCode("");
    setFilterCol("");
    setPage(0);
  };

  const hasFilters = filterCode || filterCol;

  if (loading) return (
    <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", height: "60vh" }}>
      <CircularProgress />
    </Box>
  );

  const codeOptions = summary ? Object.keys(summary.by_error_code) : [];
  const colOptions = summary ? Object.keys(summary.by_column) : [];

  return (
    <Box sx={{ p: { xs: 2.5, md: 4 } }}>
      <Stack spacing={3}>
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <Box>
            <Typography variant="h5">Лог ошибок</Typography>
            <Typography variant="caption">Ошибки валидации данных при загрузке файлов</Typography>
          </Box>
          <Stack direction="row" spacing={1}>
            <Button
              variant={showFilters ? "contained" : "outlined"}
              startIcon={<FilterList />}
              onClick={() => setShowFilters(!showFilters)}
              size="small"
              color={showFilters ? "primary" : "inherit"}
            >
              Фильтры
            </Button>
            <Button startIcon={<Refresh />} size="small" onClick={loadErrors}>Обновить</Button>
          </Stack>
        </Box>

        {/* Универсальный поиск — всегда видим */}
        <TextField
          fullWidth size="small"
          placeholder="Поиск по имени файла / источнику…"
          defaultValue=""
          onChange={(e) => {
            if (debounceRef.current) clearTimeout(debounceRef.current);
            debounceRef.current = setTimeout(() => { setSearchText(e.target.value); setPage(0); }, 350);
          }}
          slotProps={{
            input: {
              startAdornment: (
                <InputAdornment position="start">
                  <Search sx={{ fontSize: 18, color: "text.secondary" }} />
                </InputAdornment>
              ),
            },
          }}
        />

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

        {/* Filters */}
        <Collapse in={showFilters}>
          <Card>
            <CardContent sx={{ p: 2.5 }}>
              <Grid container spacing={2} alignItems="center">
                <Grid size={{ xs: 12, sm: 5 }}>
                  <Autocomplete
                    size="small"
                    options={codeOptions}
                    value={filterCode || null}
                    onChange={(_, v) => { setFilterCode(v || ""); setPage(0); }}
                    renderInput={(params) => <TextField {...params} label="Код ошибки" placeholder="Выберите код" />}
                    freeSolo
                    clearOnBlur
                  />
                </Grid>
                <Grid size={{ xs: 12, sm: 5 }}>
                  <Autocomplete
                    size="small"
                    options={colOptions}
                    value={filterCol || null}
                    onChange={(_, v) => { setFilterCol(v || ""); setPage(0); }}
                    renderInput={(params) => <TextField {...params} label="Колонка" placeholder="Выберите колонку" />}
                    freeSolo
                    clearOnBlur
                  />
                </Grid>
                <Grid size={{ xs: 12, sm: 2 }}>
                  {hasFilters && (
                    <Button
                      size="small"
                      startIcon={<FilterAltOff />}
                      onClick={clearFilters}
                      sx={{ textTransform: "none", whiteSpace: "nowrap" }}
                    >
                      Сброс
                    </Button>
                  )}
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Collapse>

        {/* Errors table */}
        <Card>
          {errLoading ? (
            <Box sx={{ display: "flex", justifyContent: "center", py: 6 }}><CircularProgress size={28} /></Box>
          ) : errors.length === 0 ? (
            <CardContent sx={{ textAlign: "center", py: 8 }}>
              <BugReport sx={{ fontSize: 40, color: "#d1d5db" }} />
              <Typography variant="body2" color="text.secondary" mt={1}>
                {hasFilters ? "Ошибок по заданным фильтрам не найдено" : "Ошибок не обнаружено"}
              </Typography>
            </CardContent>
          ) : (
            <>
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell width={40} />
                      <TableCell width={60} sortDirection={sortBy === "id" ? sortDir : false}>
                        <TableSortLabel
                          active={sortBy === "id"}
                          direction={sortBy === "id" ? sortDir : "asc"}
                          onClick={() => handleSort("id")}
                        >
                          ID
                        </TableSortLabel>
                      </TableCell>
                      <TableCell>Источник</TableCell>
                      <TableCell>Коды ошибок</TableCell>
                      <TableCell>Колонки</TableCell>
                      <TableCell width={140} sortDirection={sortBy === "detected_at" ? sortDir : false}>
                        <TableSortLabel
                          active={sortBy === "detected_at"}
                          direction={sortBy === "detected_at" ? sortDir : "asc"}
                          onClick={() => handleSort("detected_at")}
                        >
                          Дата
                        </TableSortLabel>
                      </TableCell>
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

