import type { ResumenDashboard } from "../types/dashboard";
import { API_URL, leerRespuesta } from "./api";

export async function obtenerResumenDashboard(
  token: string,
  signal?: AbortSignal,
): Promise<ResumenDashboard> {
  const respuesta = await fetch(`${API_URL}/dashboard/resumen`, {
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${token}`,
    },
    signal,
  });

  return leerRespuesta<ResumenDashboard>(respuesta);
}
