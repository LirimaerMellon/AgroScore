import { Outlet, useLocation, useNavigate } from "react-router";
import { useState, useEffect, useCallback } from "react";
import {
  Box, Drawer, AppBar, Toolbar, List, ListItemButton, ListItemIcon, ListItemText,
  IconButton, Avatar, Typography, Chip, Menu, MenuItem, Divider, useMediaQuery,
  useTheme, CircularProgress, Snackbar, Alert,
} from "@mui/material";
import {
  Dashboard, ListAlt, Insights, Settings, Grass, Menu as MenuIcon,
  Logout, Person, KeyboardArrowDown, BugReport, CloudUpload, ModelTraining,
  CheckCircle, SwapHoriz, AccountBalance,
} from "@mui/icons-material";
import { useAuth, ROLE_LABELS, ROLE_NAV_ACCESS } from "../data/auth";
import { useModel } from "../data/ModelContext";
import { type ModelInfo } from "../data/api";

const DRAWER_WIDTH = 240;

const ALL_NAV = [
  { to: "/dashboard", icon: <Dashboard />, label: "Обзор" },
  { to: "/registry", icon: <ListAlt />, label: "Реестр заявок" },
  { to: "/scoring", icon: <CloudUpload />, label: "Скоринг" },
  { to: "/shortlist", icon: <AccountBalance />, label: "Шорт-лист" },
  { to: "/models", icon: <ModelTraining />, label: "Модели" },
  { to: "/analytics", icon: <Insights />, label: "Исследование модели" },
  { to: "/errors", icon: <BugReport />, label: "Лог ошибок" },
  { to: "/settings", icon: <Settings />, label: "Настройки" },
];

const ROLE_COLORS: Record<string, string> = {
  analyst: "#3b82f6",
  commission: "#f59e0b",
  admin: "#16a34a",
};

export function Layout() {
  const { user, logout } = useAuth();
  const { modelVersion: activeModel, models: allModels, switchModel, refreshModels } = useModel();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("md"));
  const [mobileOpen, setMobileOpen] = useState(false);
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);

  // Model selector state
  const [modelAnchorEl, setModelAnchorEl] = useState<null | HTMLElement>(null);
  const [modelsLoading, setModelsLoading] = useState(false);
  const [switching, setSwitching] = useState(false);

  // Snackbar for feedback
  const [snackOpen, setSnackOpen] = useState(false);
  const [snackMessage, setSnackMessage] = useState("");
  const [snackSeverity, setSnackSeverity] = useState<"success" | "error">("success");

  const handleOpenModelMenu = async (event: React.MouseEvent<HTMLElement>) => {
    setModelAnchorEl(event.currentTarget);
    setModelsLoading(true);
    try {
      await refreshModels();
    } catch {
      setSnackMessage("Не удалось загрузить список моделей");
      setSnackSeverity("error");
      setSnackOpen(true);
    }
    setModelsLoading(false);
  };

  const handleSwitchModel = async (version: string) => {
    setSwitching(true);
    try {
      await switchModel(version);
      setSnackMessage(`Модель ${version} активирована. Данные обновлены.`);
      setSnackSeverity("success");
      setSnackOpen(true);
    } catch (e: any) {
      setSnackMessage(e.message || "Ошибка при переключении модели");
      setSnackSeverity("error");
      setSnackOpen(true);
    }
    setSwitching(false);
    setModelAnchorEl(null);
  };

  const navItems = user
    ? ALL_NAV.filter((item) => ROLE_NAV_ACCESS[user.role]?.includes(item.to))
    : ALL_NAV;

  const handleLogout = () => {
    setAnchorEl(null);
    logout();
    navigate("/login");
  };

  const drawerContent = (
    <Box sx={{ display: "flex", flexDirection: "column", height: "100%" }}>
      {/* Logo */}
      <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, px: 2.5, py: 2, borderBottom: "1px solid #f0f0f0" }}>
        <Avatar sx={{ bgcolor: "primary.main", width: 36, height: 36, borderRadius: 2 }}>
          <Grass sx={{ fontSize: 20 }} />
        </Avatar>
        <Box>
          <Typography variant="subtitle2" sx={{ lineHeight: 1.2 }}>AgriScore KZ</Typography>
          <Typography variant="caption" sx={{ lineHeight: 1.2, display: "block" }}>Скоринг субсидий</Typography>
        </Box>
      </Box>

      {/* Nav */}
      <List sx={{ flex: 1, px: 1.5, py: 1.5 }}>
        {navItems.map(({ to, icon, label }) => {
          const active = pathname === to || (to !== "/dashboard" && pathname.startsWith(to));
          return (
            <ListItemButton
              key={to}
              onClick={() => { navigate(to); if (isMobile) setMobileOpen(false); }}
              sx={{
                borderRadius: 2, mb: 0.5, py: 1,
                bgcolor: active ? "primary.main" : "transparent",
                color: active ? "#fff" : "text.secondary",
                "&:hover": { bgcolor: active ? "primary.dark" : "#f5f5f5" },
              }}
            >
              <ListItemIcon sx={{ color: "inherit", minWidth: 36 }}>{icon}</ListItemIcon>
              <ListItemText primary={label} primaryTypographyProps={{ fontSize: "0.8125rem", fontWeight: active ? 600 : 500 }} />
            </ListItemButton>
          );
        })}
      </List>

      {/* User at bottom */}
      {user && (
        <Box sx={{ p: 2, borderTop: "1px solid #f0f0f0" }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
            <Avatar sx={{ bgcolor: ROLE_COLORS[user.role], width: 34, height: 34, fontSize: "0.875rem", fontWeight: 700 }}>
              {user.name.charAt(0)}
            </Avatar>
            <Box sx={{ flex: 1, minWidth: 0 }}>
              <Typography variant="body2" fontWeight={600} noWrap>{user.name}</Typography>
              <Typography variant="caption" sx={{ display: "block" }}>{ROLE_LABELS[user.role]}</Typography>
            </Box>
          </Box>
        </Box>
      )}
    </Box>
  );

  return (
    <Box sx={{ display: "flex", minHeight: "100dvh" }}>
      {/* Sidebar */}
      {isMobile ? (
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={() => setMobileOpen(false)}
          ModalProps={{ keepMounted: true }}
          sx={{ "& .MuiDrawer-paper": { width: DRAWER_WIDTH, borderRight: "1px solid #f0f0f0" } }}
        >
          {drawerContent}
        </Drawer>
      ) : (
        <Drawer
          variant="permanent"
          sx={{ width: DRAWER_WIDTH, flexShrink: 0, "& .MuiDrawer-paper": { width: DRAWER_WIDTH, borderRight: "1px solid #f0f0f0" } }}
        >
          {drawerContent}
        </Drawer>
      )}

      {/* Main */}
      <Box sx={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
        <AppBar position="sticky" color="inherit" elevation={0} sx={{ borderBottom: "1px solid #f0f0f0", bgcolor: "rgba(255,255,255,0.9)", backdropFilter: "blur(8px)" }}>
          <Toolbar sx={{ gap: 1.5, minHeight: "56px !important" }}>
            {isMobile && (
              <IconButton edge="start" onClick={() => setMobileOpen(true)}>
                <MenuIcon />
              </IconButton>
            )}
            <Typography variant="body2" color="primary" fontWeight={700}>AgriScore KZ</Typography>
            <Typography variant="caption" sx={{ display: { xs: "none", sm: "inline" } }}>·  Министерство сельского хозяйства РК</Typography>

            <Box sx={{ flex: 1 }} />

            {/* Interactive model selector chip */}
            <Chip
              size="small"
              label={activeModel ? `Модель: ${activeModel}` : "Модель не загружена"}
              color={activeModel ? "success" : "default"}
              variant="outlined"
              clickable
              onClick={handleOpenModelMenu}
              onDelete={handleOpenModelMenu}
              deleteIcon={<SwapHoriz sx={{ fontSize: 14 }} />}
              sx={{
                display: { xs: "none", sm: "flex" },
                fontSize: "0.6875rem",
                cursor: "pointer",
                "&:hover": { borderColor: activeModel ? "success.main" : "grey.500" },
              }}
              icon={<Box sx={{ width: 6, height: 6, borderRadius: "50%", bgcolor: activeModel ? "success.main" : "grey.400", ml: 1 }} />}
            />

            {/* Model selector menu */}
            <Menu
              anchorEl={modelAnchorEl}
              open={!!modelAnchorEl}
              onClose={() => setModelAnchorEl(null)}
              PaperProps={{ sx: { width: 340, borderRadius: 3, mt: 1, maxHeight: 400 } }}
            >
              <Box sx={{ px: 2, py: 1.5 }}>
                <Typography variant="subtitle2">Выбор модели</Typography>
                <Typography variant="caption" color="text.secondary">Нажмите для активации</Typography>
              </Box>
              <Divider />
              {modelsLoading ? (
                <Box sx={{ display: "flex", justifyContent: "center", py: 3 }}>
                  <CircularProgress size={24} />
                </Box>
              ) : allModels.length === 0 ? (
                <Box sx={{ px: 2, py: 3, textAlign: "center" }}>
                  <Typography variant="body2" color="text.secondary">Нет обученных моделей</Typography>
                  <Typography
                    variant="caption"
                    color="primary"
                    sx={{ cursor: "pointer", textDecoration: "underline", mt: 0.5, display: "inline-block" }}
                    onClick={() => { setModelAnchorEl(null); navigate("/models"); }}
                  >
                    Перейти к обучению
                  </Typography>
                </Box>
              ) : (
                allModels.map((m) => (
                  <MenuItem
                    key={m.version}
                    selected={m.version === activeModel}
                    disabled={switching}
                    onClick={() => {
                      if (m.version === activeModel) {
                        setModelAnchorEl(null);
                      } else {
                        handleSwitchModel(m.version);
                      }
                    }}
                    sx={{ py: 1.5 }}
                  >
                    <Box sx={{ flex: 1, minWidth: 0 }}>
                      <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                        <Typography variant="body2" fontWeight={600} noWrap>{m.version}</Typography>
                        {m.version === activeModel && <CheckCircle color="success" sx={{ fontSize: 16 }} />}
                        {switching && m.version !== activeModel && (
                          <CircularProgress size={14} />
                        )}
                      </Box>
                      <Typography variant="caption" color="text.secondary" noWrap>
                        {m.train_size.toLocaleString("ru")} записей · {new Date(m.created_at).toLocaleDateString("ru")}
                      </Typography>
                    </Box>
                  </MenuItem>
                ))
              )}
              <Divider />
              <MenuItem
                onClick={() => { setModelAnchorEl(null); navigate("/models"); }}
                sx={{ py: 1.5, color: "primary.main", fontWeight: 600, fontSize: "0.8125rem" }}
              >
                <ModelTraining sx={{ fontSize: 18, mr: 1 }} />
                Управление моделями
              </MenuItem>
            </Menu>

            {/* Profile */}
            {user && (
              <>
                <IconButton onClick={(e) => setAnchorEl(e.currentTarget)} sx={{ gap: 1, borderRadius: 2, px: 1 }}>
                  <Avatar sx={{ bgcolor: ROLE_COLORS[user.role], width: 32, height: 32, fontSize: "0.8125rem", fontWeight: 700 }}>
                    {user.name.charAt(0)}
                  </Avatar>
                  <Box sx={{ textAlign: "left", display: { xs: "none", md: "block" } }}>
                    <Typography variant="body2" fontWeight={600} lineHeight={1.2} noWrap>{user.name}</Typography>
                    <Typography variant="caption" display="block" lineHeight={1.2}>{ROLE_LABELS[user.role]}</Typography>
                  </Box>
                  <KeyboardArrowDown sx={{ fontSize: 16, color: "text.secondary", display: { xs: "none", md: "block" } }} />
                </IconButton>
                <Menu anchorEl={anchorEl} open={!!anchorEl} onClose={() => setAnchorEl(null)}
                  PaperProps={{ sx: { width: 220, borderRadius: 3, mt: 1 } }}>
                  <Box sx={{ px: 2, py: 1.5, display: "flex", alignItems: "center", gap: 1.5 }}>
                    <Avatar sx={{ bgcolor: ROLE_COLORS[user.role], width: 34, height: 34, fontSize: "0.875rem", fontWeight: 700 }}>
                      {user.name.charAt(0)}
                    </Avatar>
                    <Box sx={{ minWidth: 0 }}>
                      <Typography variant="body2" fontWeight={600} noWrap>{user.name}</Typography>
                      <Typography variant="caption" display="block" lineHeight={1.3}>{ROLE_LABELS[user.role]}</Typography>
                    </Box>
                  </Box>
                  <Divider />
                  <MenuItem onClick={() => { setAnchorEl(null); navigate("/dashboard"); }} sx={{ fontSize: "0.8125rem", gap: 1 }}>
                    <Person fontSize="small" /> Профиль
                  </MenuItem>
                  <MenuItem onClick={handleLogout} sx={{ fontSize: "0.8125rem", gap: 1, color: "error.main" }}>
                    <Logout fontSize="small" /> Выйти
                  </MenuItem>
                </Menu>
              </>
            )}
          </Toolbar>
        </AppBar>

        <Box component="main" sx={{ flex: 1, overflow: "auto" }}>
          <Outlet />
        </Box>
      </Box>

      {/* Snackbar for model switch feedback */}
      <Snackbar
        open={snackOpen}
        autoHideDuration={4000}
        onClose={() => setSnackOpen(false)}
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
      >
        <Alert onClose={() => setSnackOpen(false)} severity={snackSeverity} variant="filled" sx={{ borderRadius: 2 }}>
          {snackMessage}
        </Alert>
      </Snackbar>
    </Box>
  );
}
