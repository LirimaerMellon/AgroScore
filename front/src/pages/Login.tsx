import { useState } from "react";
import { useNavigate, Link } from "react-router";
import { useAuth } from "../data/auth";
import {
  Box, Card, CardContent, TextField, Button, Typography, Alert, IconButton,
  InputAdornment, Avatar, Stack, Divider,
} from "@mui/material";
import { Visibility, VisibilityOff, Grass } from "@mui/icons-material";

const DEMOS = [
  { email: "commission@minagri.kz", role: "Член комиссии", color: "#16a34a" },
];

export function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPass, setShowPass] = useState(false);
  const [error, setError] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    const result = login(email, password);
    if (result.success) navigate("/dashboard");
    else setError(result.error || "Ошибка входа");
  }

  return (
    <Box sx={{ minHeight: "100dvh", display: "flex", alignItems: "center", justifyContent: "center", bgcolor: "#f0fdf4", p: 3 }}>
      <Box sx={{ width: "100%", maxWidth: 440 }}>
        {/* Logo */}
        <Stack alignItems="center" spacing={1.5} mb={4}>
          <Avatar sx={{ bgcolor: "primary.main", width: 56, height: 56, borderRadius: 3 }}>
            <Grass sx={{ fontSize: 28 }} />
          </Avatar>
          <Box textAlign="center">
            <Typography variant="h5">AgriScore KZ</Typography>
            <Typography variant="body2" color="text.secondary" mt={0.5}>AI-скоринг субсидий сельхозпроизводителей</Typography>
          </Box>
        </Stack>

        {/* Form */}
        <Card>
          <CardContent sx={{ p: { xs: 3, md: 4 } }}>
            <Typography variant="h6" gutterBottom>Вход в систему</Typography>
            <Typography variant="caption" display="block" mb={3}>Используйте рабочий email для входа</Typography>

            {error && <Alert severity="error" sx={{ mb: 2, borderRadius: 2 }}>{error}</Alert>}

            <form onSubmit={handleSubmit}>
              <Stack spacing={2.5}>
                <TextField
                  label="Email" type="email" fullWidth size="small"
                  value={email} onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@minagri.kz" required
                />
                <TextField
                  label="Пароль" fullWidth size="small" required
                  type={showPass ? "text" : "password"}
                  value={password} onChange={(e) => setPassword(e.target.value)}
                  placeholder="Введите пароль"
                  slotProps={{
                    input: {
                      endAdornment: (
                        <InputAdornment position="end">
                          <IconButton size="small" onClick={() => setShowPass(!showPass)}>
                            {showPass ? <VisibilityOff fontSize="small" /> : <Visibility fontSize="small" />}
                          </IconButton>
                        </InputAdornment>
                      ),
                    },
                  }}
                />
                <Button type="submit" variant="contained" fullWidth size="large">
                  Войти
                </Button>
              </Stack>
            </form>

            <Typography variant="body2" textAlign="center" mt={2.5} color="text.secondary">
              Нет аккаунта?{" "}
              <Link to="/register" style={{ color: "#16a34a", fontWeight: 600, textDecoration: "none" }}>Регистрация</Link>
            </Typography>
          </CardContent>
        </Card>

        {/* Demo access */}
        <Card sx={{ mt: 2 }}>
          <CardContent sx={{ p: 2.5, "&:last-child": { pb: 2.5 } }}>
            <Typography variant="caption" fontWeight={600} textTransform="uppercase" letterSpacing={0.5}>
              Быстрый вход
            </Typography>
            <Stack spacing={0.5} mt={1.5}>
              {DEMOS.map(({ email: e, role, color }) => (
                <Button
                  key={e}
                  variant="text"
                  fullWidth
                  onClick={() => {
                    const result = login(e, "demo");
                    if (result.success) navigate("/dashboard");
                  }}
                  sx={{ justifyContent: "flex-start", gap: 1.5, py: 1, px: 1.5, borderRadius: 2, textTransform: "none", color: "text.primary" }}
                >
                  <Box sx={{ width: 8, height: 8, borderRadius: "50%", bgcolor: color, flexShrink: 0 }} />
                  <Box textAlign="left">
                    <Typography variant="body2" fontWeight={600}>{role}</Typography>
                    <Typography variant="caption">Войти как демо-пользователь</Typography>
                  </Box>
                </Button>
              ))}
            </Stack>
          </CardContent>
        </Card>
      </Box>
    </Box>
  );
}
