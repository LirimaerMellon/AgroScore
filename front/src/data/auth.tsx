import { createContext, useContext, useState, type ReactNode } from "react";
import { Navigate, useLocation } from "react-router";

export type UserRole = "analyst" | "commission" | "admin";

export interface User {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  organization: string;
}

interface AuthContextType {
  user: User | null;
  login: (email: string, password: string) => { success: boolean; error?: string };
  register: (name: string, email: string, password: string, role: UserRole, organization: string) => { success: boolean; error?: string };
  logout: () => void;
}

const _DEMO_TOKEN = "ZGVtby1hY2Nlc3M=";  // internal demo token

const DEMO_USERS: (User & { token: string })[] = [
  { id: "u2", name: "Айгерим Нурланова", email: "commission@minagri.kz", token: _DEMO_TOKEN, role: "commission", organization: "Комиссия по субсидиям МСХ РК" },
];

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(() => {
    const saved = localStorage.getItem("agriscore_user");
    return saved ? JSON.parse(saved) : null;
  });

  function login(email: string, password: string) {
    const found = DEMO_USERS.find((u) => u.email === email);
    if (found && password.length >= 4) {
      const { token: _, ...userData } = found;
      setUser(userData);
      localStorage.setItem("agriscore_user", JSON.stringify(userData));
      return { success: true };
    }
    // Allow any registration-based user
    const saved = localStorage.getItem("agriscore_registered_users");
    if (saved) {
      const users: User[] = JSON.parse(saved);
      const reg = users.find((u) => u.email === email);
      if (reg && password.length >= 4) {
        setUser(reg);
        localStorage.setItem("agriscore_user", JSON.stringify(reg));
        return { success: true };
      }
    }
    return { success: false, error: "Неверный email или пароль" };
  }

  function register(name: string, email: string, _password: string, role: UserRole, organization: string) {
    if (DEMO_USERS.some((u) => u.email === email)) {
      return { success: false, error: "Пользователь с таким email уже существует" };
    }
    const newUser: User = { id: `u${Date.now()}`, name, email, role, organization };
    setUser(newUser);
    localStorage.setItem("agriscore_user", JSON.stringify(newUser));
    return { success: true };
  }

  function logout() {
    setUser(null);
    localStorage.removeItem("agriscore_user");
  }

  return (
    <AuthContext.Provider value={{ user, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be inside AuthProvider");
  return ctx;
}

export function ProtectedRoute({ children, allowedRoles }: { children: ReactNode; allowedRoles?: UserRole[] }) {
  const { user } = useAuth();
  const location = useLocation();

  if (!user) return <Navigate to="/login" state={{ from: location }} replace />;
  if (allowedRoles && !allowedRoles.includes(user.role)) return <Navigate to="/dashboard" replace />;
  return <>{children}</>;
}

export const ROLE_LABELS: Record<UserRole, string> = {
  analyst: "Аналитик МИО",
  commission: "Член комиссии",
  admin: "Администратор",
};

export const ROLE_NAV_ACCESS: Record<UserRole, string[]> = {
  analyst: ["/dashboard", "/registry", "/scoring", "/shortlist", "/models", "/analytics", "/errors"],
  commission: ["/dashboard", "/registry", "/scoring", "/shortlist", "/models", "/analytics", "/errors"],
  admin: ["/dashboard", "/registry", "/scoring", "/shortlist", "/models", "/analytics", "/errors", "/settings"],
};
