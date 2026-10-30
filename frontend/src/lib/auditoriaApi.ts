import type {
  ParametrosAuditoria,
  RegistroAuditoria,
} from "../types/auditoria";
import { API_URL, leerRespuesta } from "./api";

export async function listarAuditoria(
  token: string,
  parametros: ParametrosAuditoria,
): Promise<RegistroAuditoria[]> {
  const consulta = new URLSearchParams({
    offset: String(parametros.offset),
    limite: String(parametros.limite),
  });
  if (parametros.usuarioId !== undefined) {
    consulta.set("usuario_id", String(parametros.usuarioId));
  }
  if (parametros.entidad?.trim()) {
    consulta.set("entidad", parametros.entidad.trim());
  }
  if (parametros.entidadId !== undefined) {
    consulta.set("entidad_id", String(parametros.entidadId));
  }
  if (parametros.accion?.trim()) {
    consulta.set("accion", parametros.accion.trim());
  }

  const respuesta = await fetch(`${API_URL}/auditoria?${consulta.toString()}`, {
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${token}`,
    },
    signal: parametros.signal,
  });

  return leerRespuesta<RegistroAuditoria[]>(respuesta);
}
