import type { TokenRespuesta, Usuario } from "../types/auth";

const API_URL = (import.meta.env.VITE_API_URL ?? "http://localhost:8000").replace(
  /\/$/,
  "",
);

interface ErrorApi {
  detail?: string;
}

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export async function leerRespuesta<T>(respuesta: Response): Promise<T> {
  if (!respuesta.ok) {
    let detalle = "No fue posible completar la solicitud";

    try {
      const cuerpo = (await respuesta.json()) as ErrorApi;
      if (typeof cuerpo.detail === "string") {
        detalle = cuerpo.detail;
      }
    } catch {
      // La API puede responder sin JSON en errores de infraestructura.
    }

    throw new ApiError(respuesta.status, detalle);
  }

  return (await respuesta.json()) as T;
}

export async function iniciarSesion(
  email: string,
  password: string,
): Promise<TokenRespuesta> {
  const formulario = new URLSearchParams({
    username: email.trim().toLowerCase(),
    password,
  });

  const respuesta = await fetch(`${API_URL}/auth/login`, {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: formulario,
  });

  return leerRespuesta<TokenRespuesta>(respuesta);
}

export async function obtenerMiUsuario(
  token: string,
  signal?: AbortSignal,
): Promise<Usuario> {
  const respuesta = await fetch(`${API_URL}/auth/me`, {
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${token}`,
    },
    signal,
  });

  return leerRespuesta<Usuario>(respuesta);
}

export { API_URL };
