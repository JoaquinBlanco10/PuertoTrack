import { ApiError } from "./api";

export function mensajeErrorApi(
  error: unknown,
  mensajePredeterminado = "No fue posible completar la operación.",
): string {
  if (error instanceof ApiError) {
    const mensajes: Partial<Record<number, string>> = {
      400: error.message,
      401: "Tu sesión expiró. Vuelve a iniciar sesión.",
      403: "No tienes permisos para realizar esta operación.",
      404: error.message || "El recurso solicitado no existe.",
      409: error.message || "La operación entra en conflicto con los datos actuales.",
    };
    return mensajes[error.status] ?? error.message ?? mensajePredeterminado;
  }

  if (error instanceof TypeError) {
    return "No fue posible conectar con la API. Comprueba que el backend esté disponible.";
  }

  return mensajePredeterminado;
}

export function esCancelacion(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}
