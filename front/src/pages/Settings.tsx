import { useState } from "react";
import {
  Box, Card, CardContent, Typography, Button, Stack, Alert, Chip,
  Dialog, DialogTitle, DialogContent, DialogActions, Checkbox, FormControlLabel,
} from "@mui/material";
import { DeleteForever, Warning } from "@mui/icons-material";

export function Settings() {
  const [actionMsg, setActionMsg] = useState("");
  const [actionError, setActionError] = useState("");
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [resetApps, setResetApps] = useState(true);
  const [resetModels, setResetModels] = useState(true);
  const [resetErrors, setResetErrors] = useState(true);
  const [resetting, setResetting] = useState(false);

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
    } catch (e: any) {
      setActionError(e.message || "Ошибка сброса");
    }
    setResetting(false);
    setConfirmOpen(false);
  }

  return (
    <Box sx={{ p: { xs: 2.5, md: 4 } }}>
      <Stack spacing={3}>
        <Box>
          <Typography variant="h5">Настройки</Typography>
          <Typography variant="caption">Администрирование системы</Typography>
        </Box>

        {actionMsg && <Alert severity="success" sx={{ borderRadius: 2 }} onClose={() => setActionMsg("")}>{actionMsg}</Alert>}
        {actionError && <Alert severity="error" sx={{ borderRadius: 2 }} onClose={() => setActionError("")}>{actionError}</Alert>}

        {/* Reset section */}
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
            Там можно обучить новую модель, выбрать активную и настроить fine-tuning.
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
