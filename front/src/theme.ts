import { createTheme } from "@mui/material/styles";

export const theme = createTheme({
  palette: {
    primary: { main: "#16a34a", light: "#22c55e", dark: "#15803d", contrastText: "#fff" },
    secondary: { main: "#3b82f6" },
    error: { main: "#ef4444" },
    warning: { main: "#f59e0b" },
    success: { main: "#22c55e" },
    background: { default: "#f8fafb", paper: "#ffffff" },
    text: { primary: "#111827", secondary: "#6b7280" },
  },
  typography: {
    fontFamily: '"Inter", system-ui, sans-serif',
    h4: { fontWeight: 700, fontSize: "1.5rem" },
    h5: { fontWeight: 700, fontSize: "1.25rem" },
    h6: { fontWeight: 600, fontSize: "1rem" },
    subtitle2: { fontWeight: 600, fontSize: "0.8125rem" },
    body2: { fontSize: "0.8125rem" },
    caption: { fontSize: "0.6875rem", color: "#9ca3af" },
  },
  shape: { borderRadius: 12 },
  components: {
    MuiButton: {
      styleOverrides: {
        root: { textTransform: "none", fontWeight: 600, borderRadius: 10, padding: "8px 20px" },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: { borderRadius: 16, border: "1px solid #f0f0f0", boxShadow: "0 1px 3px rgba(0,0,0,0.04)" },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: { fontWeight: 600, fontSize: "0.75rem" },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        root: { fontSize: "0.8125rem", borderColor: "#f5f5f5" },
        head: { fontWeight: 600, fontSize: "0.6875rem", color: "#9ca3af", textTransform: "uppercase", letterSpacing: "0.05em" },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: { "& .MuiOutlinedInput-root": { borderRadius: 12 } },
      },
    },
  },
});
