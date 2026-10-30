import type {
  Contenedor,
  ContextoMovimientoContenedor,
  Movimiento,
  TipoMovimiento,
  Ubicacion,
} from "../types/logistica";

const PERMITIDAS_POR_ESTADO: Record<string, TipoMovimiento[]> = {
  disponible: ["entrada"],
  en_transito: ["entrada"],
  en_patio: ["traslado", "salida"],
};

function normalizarBusqueda(valor: string): string {
  return valor
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLocaleLowerCase()
    .trim();
}

export function filtrarContenedores(
  contenedores: Contenedor[],
  consulta: string,
): Contenedor[] {
  const termino = normalizarBusqueda(consulta);
  if (!termino) return contenedores;
  return contenedores.filter((contenedor) =>
    normalizarBusqueda(
      `${contenedor.codigo} ${contenedor.ubicacion_actual} ${contenedor.estado.replaceAll("_", " ")} ${contenedor.situacion.replaceAll("_", " ")}`,
    ).includes(termino),
  );
}

export function operacionesPermitidas(
  valor: string | Contenedor,
): TipoMovimiento[] {
  if (typeof valor !== "string") {
    if (valor.coherencia_operacional === "inconsistente") return [];
    if (
      valor.coherencia_operacional === "sin_confirmar" &&
      valor.estado === "en_patio"
    ) return [];
    return PERMITIDAS_POR_ESTADO[valor.estado] ?? [];
  }
  return PERMITIDAS_POR_ESTADO[valor] ?? [];
}

export interface ResumenMovimiento {
  origen: string;
  destino: string;
  estadoEsperado: string;
}

export function resumirMovimiento(
  contenedor: Contenedor,
  tipo: TipoMovimiento,
  destino: Ubicacion | null,
): ResumenMovimiento {
  return {
    origen: contenedor.ubicacion_actual,
    destino: destino?.nombre ?? "",
    estadoEsperado: tipo === "salida" ? "en_transito" : "en_patio",
  };
}

export function destinoCoincideConOrigen(
  contenedor: Contenedor,
  destino: Ubicacion,
): boolean {
  return contenedor.ubicacion_actual_id === destino.id;
}

export function destinosPermitidos(
  ubicaciones: Ubicacion[],
  tipo: TipoMovimiento,
  contenedor: Contenedor,
): Ubicacion[] {
  const tipoEsperado = tipo === "salida" ? "externa" : "interna";
  return ubicaciones.filter(
    (ubicacion) =>
      ubicacion.activo &&
      ubicacion.tipo === tipoEsperado &&
      (tipo !== "traslado" || ubicacion.id !== contenedor.ubicacion_actual_id),
  );
}

export function etiquetaEntrada(
  contexto: ContextoMovimientoContenedor | null,
): string {
  if (contexto?.etiqueta_entrada === "primera_entrada") return "Primera entrada";
  if (contexto?.etiqueta_entrada === "reingreso") return "Registrar reingreso";
  return "Entrada";
}

export function incorporarMovimientoReciente(
  movimientos: Movimiento[],
  nuevo: Movimiento,
  limite: number,
): Movimiento[] {
  const unicos = new Map<number, Movimiento>();
  for (const movimiento of [nuevo, ...movimientos]) {
    if (!unicos.has(movimiento.id)) unicos.set(movimiento.id, movimiento);
  }
  return [...unicos.values()]
    .sort((a, b) => {
      const diferenciaFecha =
        new Date(b.fecha_movimiento).getTime() -
        new Date(a.fecha_movimiento).getTime();
      return diferenciaFecha || b.id - a.id;
    })
    .slice(0, limite);
}
