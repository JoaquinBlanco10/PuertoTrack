import type { DecisionAcceso, ParametrosAccesos } from "../types/accesos";
import { API_URL, leerRespuesta } from "./api";

export async function listarDecisionesAcceso(
  token: string,
  parametros: ParametrosAccesos = {},
): Promise<DecisionAcceso[]> {
  const consulta = new URLSearchParams({
    limite: String(parametros.limite ?? 50),
  });
  if (parametros.resultado) consulta.set("resultado", parametros.resultado);

  const respuesta = await fetch(`${API_URL}/accesos?${consulta.toString()}`, {
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${token}`,
    },
    signal: parametros.signal,
  });

  return leerRespuesta<DecisionAcceso[]>(respuesta);
}
