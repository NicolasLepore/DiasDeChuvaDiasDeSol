import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";

interface PrivateRouteProps {
  children: ReactNode;
}

export const PrivateRoute = ({ children }: PrivateRouteProps) => {
  const token = localStorage.getItem("token"); // ou qualquer chave que você usar para guardar a autenticação

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
};