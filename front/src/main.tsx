import { StrictMode, Suspense, lazy } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Routes, Route, Navigate } from "react-router";
import { ThemeProvider, CssBaseline, CircularProgress, Box } from "@mui/material";
import { theme } from "./theme";
import "./index.css";
import { AuthProvider, ProtectedRoute } from "./data/auth";
import { ModelProvider } from "./data/ModelContext";
import { Layout } from "./components/Layout";

const Login = lazy(() => import("./pages/Login").then((m) => ({ default: m.Login })));
const Register = lazy(() => import("./pages/Register").then((m) => ({ default: m.Register })));
const Dashboard = lazy(() => import("./pages/Dashboard").then((m) => ({ default: m.Dashboard })));
const Registry = lazy(() => import("./pages/Registry").then((m) => ({ default: m.Registry })));
const AppDetail = lazy(() => import("./pages/AppDetail").then((m) => ({ default: m.AppDetail })));
const Scoring = lazy(() => import("./pages/Shortlist").then((m) => ({ default: m.Scoring })));
const Analytics = lazy(() => import("./pages/Analytics").then((m) => ({ default: m.Analytics })));
const ModelManager = lazy(() => import("./pages/ModelManager").then((m) => ({ default: m.ModelManager })));
const Settings = lazy(() => import("./pages/Settings").then((m) => ({ default: m.Settings })));
const ErrorLogs = lazy(() => import("./pages/ErrorLogs").then((m) => ({ default: m.ErrorLogs })));
const ShortlistPage = lazy(() => import("./pages/ShortlistPage").then((m) => ({ default: m.ShortlistPage })));

function PageLoader() {
  return (
    <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", height: "60vh" }}>
      <CircularProgress />
    </Box>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <BrowserRouter>
        <AuthProvider>
          <ModelProvider>
            <Suspense fallback={<PageLoader />}>
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
            </Suspense>
          </ModelProvider>
        </AuthProvider>
      </BrowserRouter>
    </ThemeProvider>
  </StrictMode>
);
