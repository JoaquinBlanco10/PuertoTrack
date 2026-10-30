import {
  createContext,
  type PropsWithChildren,
  useCallback,
  useContext,
  useMemo,
  useState,
} from "react";

import { ApiError, iniciarSesion, obtenerMiUsuario } from "../lib/api";
import type { Usuario } from "../types/auth";

interface AuthContextValue {
  usuario: Usuario | null;
  token: string | null;
  autenticando: boolean;
  autenticado: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  ejecutarAutenticado: <T>(
    operacion: (token: string) => Promise<T>,
  ) => Promise<T>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: PropsWithChildren) {
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [autenticando, setAutenticando] = useState(false);

  const logout = useCallback(() => {
    setToken(null);
    setUsuario(null);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    setAutenticando(true);

    try {
      const credencial = await iniciarSesion(email, password);
      const perfil = await obtenerMiUsuario(credencial.access_token);
      setToken(credencial.access_token);
      setUsuario(perfil);
    } catch (error) {
      setToken(null);
      setUsuario(null);
      throw error;
    } finally {
      setAutenticando(false);
    }
  }, []);

  const ejecutarAutenticado = useCallback(
    async <T,>(operacion: (token: string) => Promise<T>): Promise<T> => {
      if (!token) {
        logout();
        throw new ApiError(401, "La sesión no está disponible");
      }

      try {
        return await operacion(token);
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) logout();
        throw error;
      }
    },
    [logout, token],
  );

  const valor = useMemo<AuthContextValue>(
    () => ({
      usuario,
      token,
      autenticando,
      autenticado: Boolean(usuario && token),
      login,
      logout,
      ejecutarAutenticado,
    }),
    [autenticando, ejecutarAutenticado, login, logout, token, usuario],
  );

  return <AuthContext.Provider value={valor}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const contexto = useContext(AuthContext);

  if (!contexto) {
    throw new Error("useAuth debe utilizarse dentro de AuthProvider");
  }

  return contexto;
}
