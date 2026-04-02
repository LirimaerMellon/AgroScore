import { useState } from "react";
import { useNavigate, Link } from "react-router";
import { useAuth, type UserRole, ROLE_LABELS } from "../data/auth";
import {
  Box, Card, CardContent, TextField, Button, Typography, Alert, IconButton,
  InputAdornment, Avatar, Stack, MenuItem,
} from "@mui/material";
import { Visibility, VisibilityOff, Grass } from "@mui/icons-material";

export function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<UserRole>("commission");
  const [organization, setOrganization] = useState("");
  const [showPass, setShowPass] = useState(false);
  const [error, setError] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (password.length < 6) { setError("Пароль должен быть не менее 6 символов"); return; }
    const result = register(name, email, password, role, organization);
    if (result.success) navigate("/dashboard");
    else setError(result.error || "Ошибка регистрации");
  }

  return (
    <Box sx={{ minHeight: "100dvh", display: "flex", alignItems: "center", justifyContent: "center", bgcolor: "#f0fdf4", p: 3 }}>
      <Box sx={{ width: "100%", maxWidth: 440 }}>
        <Stack alignItems="center" spacing={1.5} mb={4}>
          <Avatar sx={{ bgcolor: "primary.main", width: 56, height: 56, borderRadius: 3 }}>
            <Grass sx={{ fontSize: 28 }} />
          </Avatar>
          <Box textAlign="center">
            <Typography variant="h5">AgriScore KZ</Typography>
            <Typography variant="body2" color="text.secondary" mt={0.5}>Регистрация нового пользователя</Typography>
          </Box>
        </Stack>

        <Card>
          <CardContent sx={{ p: { xs: 3, md: 4 } }}>
            <Typography variant="h6" gutterBottom>Создание аккаунта</Typography>
            <Typography variant="caption" display="block" mb={3}>Заполните данные для доступа к системе</Typography>

            {error && <Alert severity="error" sx={{ mb: 2, borderRadius: 2 }}>{error}</Alert>}

            <form onSubmit={handleSubmit}>
              <Stack spacing={2.5}>
                <TextField label="ФИО" fullWidth size="small" value={name} onChange={(e) => setName(e.target.value)} placeholder="Иванов Иван Иванович" required />
                <TextField label="Email" type="email" fullWidth size="small" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="name@minagri.kz" required />
                <TextField
                  label="Пароль" fullWidth size="small" required
                  type={showPass ? "text" : "password"}
                  value={password} onChange={(e) => setPassword(e.target.value)}
                  placeholder="Минимум 6 символов"
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
                <TextField label="Роль" select fullWidth size="small" value={role} onChange={(e) => setRole(e.target.value as UserRole)}>
                  <MenuItem value="commission">{ROLE_LABELS.commission}</MenuItem>
                </TextField>
                <TextField label="Организация" fullWidth size="small" value={organization} onChange={(e) => setOrganization(e.target.value)} placeholder='ГУ "Управление сельского хозяйства"' required />
                <Button type="submit" variant="contained" fullWidth size="large">Зарегистрироваться</Button>
              </Stack>
            </form>

            <Typography variant="body2" textAlign="center" mt={2.5} color="text.secondary">
              Уже есть аккаунт?{" "}
              <Link to="/login" style={{ color: "#16a34a", fontWeight: 600, textDecoration: "none" }}>Войти</Link>
            </Typography>
          </CardContent>
        </Card>
      </Box>
    </Box>
  );
}
