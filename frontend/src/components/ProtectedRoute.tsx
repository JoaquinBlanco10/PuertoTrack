import { Navigate, Outlet, useLocation } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import type { RolUsuario } from "../types/auth";

interface ProtectedRouteProps {
  roles?: RolUsuario[];
}

export function ProtectedRoute({ roles }: ProtectedRouteProps) {
  const { autenticado, usuario } = useAuth();
  const ubicacion = useLocation();

  if (!autenticado || !usuario) {
    return <Navigate to="/login" replace state={{ desde: ubicacion }} />;
  }

  if (roles && !roles.includes(usuario.rol)) {
    return <Navigate to="/sin-permiso" replace />;
  }

  return <Outlet />;
}
