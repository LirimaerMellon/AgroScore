import { useState, useEffect, useCallback, useRef } from "react";
import { useNavigate } from "react-router";
import {
  Box, Card, CardContent, Typography, TextField, InputAdornment, Button,
  Table, TableHead, TableBody, TableRow, TableCell, TableContainer, TableSortLabel,
  Chip, MenuItem, Stack, Grid, Collapse, CircularProgress, TablePagination,
  FormControlLabel, Switch,
} from "@mui/material";
import { Search, FilterList, SearchOff, Download, Warning } from "@mui/icons-material";
import { fetchApplications, downloadExport, type ApplicationItem } from "../data/api";
import { ScoreBadge } from "../components/ScoreBadge";

const CATEGORY_CHIP: Record<string, { color: "success" | "warning" | "error"; label: string }> = {
  HIGH: { color: "success", label: "HIGH" },
  MEDIUM: { color: "warning", label: "MEDIUM" },
  LOW: { color: "error", label: "LOW" },
};

function fmt(n: number) { return `₸${n.toLocaleString("ru")}`; }

type SortKey = "score" | "amount" | "created_at" | "normative";
type SortDir = "asc" | "desc";

export function Registry() {
  const navigate = useNavigate();
  const [items, setItems] = useState<ApplicationItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(50);
  const [searchText, setSearchText] = useState("");
  const [filterCategory, setFilterCategory] = useState("");
  const [filterReviewRequired, setFilterReviewRequired] = useState(false);
  const [sortKey, setSortKey] = useState<SortKey>("score");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [showFilters, setShowFilters] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetchApplications({
        limit: rowsPerPage,
        offset: page * rowsPerPage,
        search: searchText || undefined,
        category: filterCategory || undefined,
        sort_by: sortKey,
        sort_dir: sortDir,
        review_required: filterReviewRequired || undefined,
      });
      setItems(res.items);
      setTotal(res.total);
    } catch { /* empty — graceful */ }
    setLoading(false);
  }, [page, rowsPerPage, searchText, filterCategory, filterReviewRequired, sortKey, sortDir]);

  useEffect(() => { loadData(); }, [loadData]);

  function handleSearchChange(value: string) {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setSearchText(value);
      setPage(0);
    }, 350);
  }

  function toggleSort(key: SortKey) {
    if (sortKey === key) setSortDir(sortDir === "asc" ? "desc" : "asc");
    else { setSortKey(key); setSortDir("desc"); }
  }

  return (
    <Box sx={{ p: { xs: 2.5, md: 4 }, display: "flex", flexDirection: "column", gap: 3, height: "100%" }}>
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 1 }}>
        <Box>
          <Typography variant="h5">Реестр заявок</Typography>
          <Typography variant="caption">{total} заявок в базе</Typography>
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
          <Button variant="outlined" startIcon={<Download />} size="small" onClick={() => downloadExport()}>
            Экспорт Excel
          </Button>
        </Stack>
      </Box>

      {/* Универсальный поиск — всегда видим */}
      <TextField
        fullWidth size="small"
        placeholder="Поиск по всем полям: область, район, направление, БИН/ИИН, вид субсидии…"
        defaultValue=""
        onChange={(e) => handleSearchChange(e.target.value)}
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

      <Collapse in={showFilters}>
        <Card>
          <CardContent sx={{ p: 2.5 }}>
            <Grid container spacing={2} alignItems="center">
              <Grid size={{ xs: 12, sm: 6 }}>
                <TextField select fullWidth size="small" label="Категория" value={filterCategory}
                  onChange={(e) => { setFilterCategory(e.target.value); setPage(0); }}>
                  <MenuItem value="">Все</MenuItem>
                  <MenuItem value="HIGH">HIGH</MenuItem>
                  <MenuItem value="MEDIUM">MEDIUM</MenuItem>
                  <MenuItem value="LOW">LOW</MenuItem>
                </TextField>
              </Grid>
              <Grid size={{ xs: 12, sm: 6 }}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={filterReviewRequired}
                      onChange={(e) => { setFilterReviewRequired(e.target.checked); setPage(0); }}
                      color="warning"
                    />
                  }
                  label={
                    <Stack direction="row" spacing={0.5} alignItems="center">
                      <Warning sx={{ fontSize: 16, color: filterReviewRequired ? "#f59e0b" : "#9ca3af" }} />
                      <Typography variant="body2">Рекомендуется доп. проверка</Typography>
                    </Stack>
                  }
                />
              </Grid>
            </Grid>
          </CardContent>
        </Card>
      </Collapse>

      <Card sx={{ flex: 1, overflow: "hidden", display: "flex", flexDirection: "column" }}>
        {loading ? (
          <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}><CircularProgress size={32} /></Box>
        ) : (
          <>
            <TableContainer sx={{ flex: 1 }}>
              <Table stickyHeader size="small">
                <TableHead>
                  <TableRow>
                    <TableCell width={50}>#</TableCell>
                    <TableCell width={70} sortDirection={sortKey === "score" ? sortDir : false}>
                      <TableSortLabel active={sortKey === "score"} direction={sortDir} onClick={() => toggleSort("score")}>Балл</TableSortLabel>
                    </TableCell>
                    <TableCell>Категория</TableCell>
                    <TableCell>Область</TableCell>
                    <TableCell>Направление</TableCell>
                    <TableCell>Вид субсидии</TableCell>
                    <TableCell align="right" sortDirection={sortKey === "normative" ? sortDir : false}>
                      <TableSortLabel active={sortKey === "normative"} direction={sortDir} onClick={() => toggleSort("normative")}>Норматив</TableSortLabel>
                    </TableCell>
                    <TableCell align="right" sortDirection={sortKey === "amount" ? sortDir : false}>
                      <TableSortLabel active={sortKey === "amount"} direction={sortDir} onClick={() => toggleSort("amount")}>Причитающая сумма</TableSortLabel>
                    </TableCell>
                    <TableCell width={60}>Проверка</TableCell>
                    <TableCell width={90} sortDirection={sortKey === "created_at" ? sortDir : false}>
                      <TableSortLabel active={sortKey === "created_at"} direction={sortDir} onClick={() => toggleSort("created_at")}>Дата</TableSortLabel>
                    </TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {items.map((app, i) => {
                    const cat = CATEGORY_CHIP[app.category] ?? { color: "default" as const, label: app.category };
                    const date = app.created_at ? new Date(app.created_at).toLocaleDateString("ru", { day: "2-digit", month: "2-digit", year: "2-digit" }) : "—";
                    const reviewRequired = (app as any).review_required;
                    return (
                      <TableRow key={app.id} hover sx={{ cursor: "pointer" }} onClick={() => navigate(`/app/${app.id}`)}>
                        <TableCell sx={{ color: "text.secondary", fontFamily: "'JetBrains Mono'" }}>{page * rowsPerPage + i + 1}</TableCell>
                        <TableCell><ScoreBadge score={Math.round(app.score)} /></TableCell>
                        <TableCell><Chip label={cat.label} color={cat.color} size="small" variant="outlined" /></TableCell>
                        <TableCell sx={{ fontWeight: 500 }}>{app.region || "—"}</TableCell>
                        <TableCell sx={{ color: "text.secondary" }}>{app.direction || "—"}</TableCell>
                        <TableCell sx={{ color: "text.secondary", maxWidth: 220 }}>
                          <Typography variant="body2" noWrap title={app.subsidy_type}>{app.subsidy_type || "—"}</Typography>
                        </TableCell>
                        <TableCell align="right" sx={{ fontFamily: "'JetBrains Mono'", fontWeight: 600 }}>{fmt(app.normative ?? 0)}</TableCell>
                        <TableCell align="right" sx={{ fontFamily: "'JetBrains Mono'", fontWeight: 600 }}>{fmt(app.amount)}</TableCell>
                        <TableCell>
                          {reviewRequired && <Warning sx={{ fontSize: 16, color: "#f59e0b" }} titleAccess="Рекомендуется доп. проверка" />}
                        </TableCell>
                        <TableCell sx={{ fontFamily: "'JetBrains Mono'", color: "text.secondary" }}>{date}</TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </TableContainer>
            {items.length === 0 && (
              <Stack alignItems="center" py={8} spacing={1.5}>
                <SearchOff sx={{ fontSize: 40, color: "#d1d5db" }} />
                <Typography variant="body2" color="text.secondary">Нет оценённых заявок</Typography>
              </Stack>
            )}
            <TablePagination
              component="div" count={total} page={page} rowsPerPage={rowsPerPage}
              onPageChange={(_, p) => setPage(p)}
              onRowsPerPageChange={(e) => { setRowsPerPage(parseInt(e.target.value)); setPage(0); }}
              rowsPerPageOptions={[25, 50, 100]}
              labelRowsPerPage="Строк:"
              labelDisplayedRows={({ from, to, count }) => `${from}–${to} из ${count}`}
            />
          </>
        )}
      </Card>
    </Box>
  );
}
