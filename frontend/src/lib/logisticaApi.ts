import { API_URL, leerRespuesta } from "./api";
import type {
  ActualizarContenedorInput,
  ActualizarUbicacionInput,
  Contenedor,
  CrearContenedorInput,
  CrearMovimientoInput,
  CrearUbicacionInput,
  ContextoMovimientoContenedor,
  Movimiento,
  ParametrosContenedores,
  ParametrosMovimientos,
  ParametrosPagina,
  ParametrosUbicaciones,
  RegularizarContenedorInput,
  Ubicacion,
} from "../types/logistica";

async function solicitarConToken<T>(
  ruta: string,
  token: string,
  opciones: RequestInit = {},
): Promise<T> {
  const headers = new Headers(opciones.headers);
  headers.set("Accept", "application/json");
  headers.set("Authorization", `Bearer ${token}`);
  if (opciones.body) headers.set("Content-Type", "application/json");

  const respuesta = await fetch(`${API_URL}${ruta}`, {
    ...opciones,
    headers,
  });

  return leerRespuesta<T>(respuesta);
}

function pagina(parametros: ParametrosPagina): string {
  const consulta = new URLSearchParams({
    offset: String(parametros.offset),
    limite: String(parametros.limite),
  });
  return consulta.toString();
}

export function listarContenedores(
  token: string,
  parametros: ParametrosContenedores,
): Promise<Contenedor[]> {
  const consulta = new URLSearchParams(pagina(parametros));
  if (parametros.codigo) consulta.set("codigo", parametros.codigo.trim());
  if (parametros.situacion) consulta.set("situacion", parametros.situacion);
  if (parametros.coherencia) consulta.set("coherencia", parametros.coherencia);
  return solicitarConToken<Contenedor[]>(
    `/contenedores?${consulta.toString()}`,
    token,
    { signal: parametros.signal },
  );
}

export function regularizarUbicacionContenedor(
  token: string,
  contenedorId: number,
  datos: RegularizarContenedorInput,
): Promise<Contenedor> {
  return solicitarConToken<Contenedor>(
    `/contenedores/${contenedorId}/regularizar-ubicacion`,
    token,
    { method: "POST", body: JSON.stringify(datos) },
  );
}

export function listarUbicaciones(
  token: string,
  parametros: ParametrosUbicaciones,
): Promise<Ubicacion[]> {
  const consulta = new URLSearchParams(pagina(parametros));
  if (parametros.tipo) consulta.set("tipo", parametros.tipo);
  if (parametros.incluirInactivas) consulta.set("incluir_inactivas", "true");
  return solicitarConToken<Ubicacion[]>(
    `/ubicaciones?${consulta.toString()}`,
    token,
    { signal: parametros.signal },
  );
}

export function crearUbicacion(
  token: string,
  datos: CrearUbicacionInput,
): Promise<Ubicacion> {
  return solicitarConToken<Ubicacion>("/ubicaciones", token, {
    method: "POST",
    body: JSON.stringify(datos),
  });
}

export function actualizarUbicacion(
  token: string,
  ubicacionId: number,
  datos: ActualizarUbicacionInput,
): Promise<Ubicacion> {
  return solicitarConToken<Ubicacion>(`/ubicaciones/${ubicacionId}`, token, {
    method: "PATCH",
    body: JSON.stringify(datos),
  });
}

export function buscarContenedorPorCodigo(
  token: string,
  codigo: string,
  signal?: AbortSignal,
): Promise<Contenedor> {
  return solicitarConToken<Contenedor>(
    `/contenedores/codigo/${encodeURIComponent(codigo.trim())}`,
    token,
    { signal },
  );
}

export function buscarContenedorPorId(
  token: string,
  contenedorId: number,
  signal?: AbortSignal,
): Promise<Contenedor> {
  return solicitarConToken<Contenedor>(
    `/contenedores/${contenedorId}`,
    token,
    { signal },
  );
}

export function crearContenedor(
  token: string,
  datos: CrearContenedorInput,
): Promise<Contenedor> {
  return solicitarConToken<Contenedor>("/contenedores", token, {
    method: "POST",
    body: JSON.stringify(datos),
  });
}

export function corregirCodigoContenedor(
  token: string,
  contenedorId: number,
  datos: ActualizarContenedorInput,
): Promise<Contenedor> {
  return solicitarConToken<Contenedor>(`/contenedores/${contenedorId}`, token, {
    method: "PATCH",
    body: JSON.stringify(datos),
  });
}

export function listarMovimientos(
  token: string,
  parametros: ParametrosMovimientos,
): Promise<Movimiento[]> {
  const consulta = new URLSearchParams(pagina(parametros));
  if (parametros.orden) consulta.set("orden", parametros.orden);
  return solicitarConToken<Movimiento[]>(
    `/movimientos?${consulta.toString()}`,
    token,
    { signal: parametros.signal },
  );
}

export function listarMovimientosPorContenedor(
  token: string,
  contenedorId: number,
  parametros: ParametrosMovimientos,
): Promise<Movimiento[]> {
  const consulta = new URLSearchParams(pagina(parametros));
  if (parametros.orden) consulta.set("orden", parametros.orden);
  return solicitarConToken<Movimiento[]>(
    `/movimientos/contenedor/${contenedorId}?${consulta.toString()}`,
    token,
    { signal: parametros.signal },
  );
}

export function registrarMovimiento(
  token: string,
  datos: CrearMovimientoInput,
): Promise<Movimiento> {
  return solicitarConToken<Movimiento>("/movimientos", token, {
    method: "POST",
    body: JSON.stringify(datos),
  });
}

export function obtenerContextoMovimiento(
  token: string,
  contenedorId: number,
  signal?: AbortSignal,
): Promise<ContextoMovimientoContenedor> {
  return solicitarConToken<ContextoMovimientoContenedor>(
    `/movimientos/contenedor/${contenedorId}/contexto`,
    token,
    { signal },
  );
}
