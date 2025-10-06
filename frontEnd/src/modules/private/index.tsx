// src/contexts/AuthContext.tsx
import { createContext, useContext, useState,  type ReactNode } from "react";

interface AuthContextType {
  user: any;
  loginUser: (token: string, userData?: any) => void;
  logoutUser: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<any>(null);

  const loginUser = (token: string, userData?: any) => {
    localStorage.setItem("token", token);
    setUser(userData || { username: "user" });
  };

  const logoutUser = () => {
    localStorage.removeItem("token");
    setUser(null);
  };

  const isAuthenticated = !!localStorage.getItem("token");

  return (
    <AuthContext.Provider value={{ user, loginUser, logoutUser, isAuthenticated }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
};
