import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Routes, Route, Navigate } from "react-router";
import { ThemeProvider, CssBaseline } from "@mui/material";
import { theme } from "./theme";
import "./index.css";
import { AuthProvider, ProtectedRoute } from "./data/auth";
import { Layout } from "./components/Layout";
import { Login } from "./pages/Login";
import { Register } from "./pages/Register";
import { Dashboard } from "./pages/Dashboard";
import { Registry } from "./pages/Registry";
import { AppDetail } from "./pages/AppDetail";
import { Scoring } from "./pages/Shortlist";
import { Analytics } from "./pages/Analytics";
import { ModelManager } from "./pages/ModelManager";
import { Settings } from "./pages/Settings";
import { ErrorLogs } from "./pages/ErrorLogs";
import { ShortlistPage } from "./pages/ShortlistPage";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            <Route path="login" element={<Login />} />
            <Route path="register" element={<Register />} />
            <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
              <Route index element={<Navigate to="/dashboard" replace />} />
              <Route path="dashboard" element={<Dashboard />} />
              <Route path="registry" element={<Registry />} />
              <Route path="app/:id" element={<AppDetail />} />
              <Route path="scoring" element={<Scoring />} />
              <Route path="shortlist" element={<ShortlistPage />} />
              <Route path="models" element={<ProtectedRoute allowedRoles={["analyst", "admin", "commission"]}><ModelManager /></ProtectedRoute>} />
              <Route path="analytics" element={<ProtectedRoute allowedRoles={["analyst", "admin", "commission"]}><Analytics /></ProtectedRoute>} />
              <Route path="errors" element={<ErrorLogs />} />
              <Route path="settings" element={<ProtectedRoute allowedRoles={["admin"]}><Settings /></ProtectedRoute>} />
            </Route>
            <Route path="*" element={<Navigate to="/login" replace />} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </ThemeProvider>
  </StrictMode>
);
