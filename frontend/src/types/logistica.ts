export const ESTADOS_CONTENEDOR = [
  "disponible",
  "en_patio",
  "en_transito",
  "cargado",
  "descargado",
  "mantenimiento",
] as const;

export type EstadoContenedor = (typeof ESTADOS_CONTENEDOR)[number];
export type TipoMovimiento = "entrada" | "traslado" | "salida";
export type OrdenMovimientos = "asc" | "desc";
export type TipoUbicacion = "interna" | "externa";
export type SituacionContenedor =
  | "dentro_puerto"
  | "fuera_puerto"
  | "presencia_sin_confirmar";
export type CoherenciaOperacional =
  | "coherente"
  | "sin_confirmar"
  | "inconsistente";

export const MAX_LONGITUD_OBSERVACION = 1000;

export interface Ubicacion {
  id: number;
  codigo: string;
  nombre: string;
  tipo: TipoUbicacion;
  activo: boolean;
}

export interface Contenedor {
  id: number;
  codigo: string;
  ubicacion_actual: string;
  ubicacion_actual_id: number | null;
  situacion: SituacionContenedor;
  coherencia_operacional: CoherenciaOperacional;
  tiene_evidencia_historica: boolean;
  regularizacion_permitida: boolean;
  estado: string;
  fecha_creacion: string;
  fecha_actualizacion: string;
}

export interface CrearContenedorInput {
  codigo: string;
}

export interface ActualizarContenedorInput {
  codigo: string;
}

export interface RegularizarContenedorInput {
  ubicacion_id: number;
  estado: "en_patio" | "en_transito";
  justificacion: string;
}

export interface Movimiento {
  id: number;
  contenedor_id: number;
  usuario_id: number;
  tipo: TipoMovimiento | null;
  ubicacion_origen: string;
  ubicacion_destino: string;
  ubicacion_origen_id: number | null;
  ubicacion_destino_id: number | null;
  fecha_movimiento: string;
  observacion: string | null;
}

export interface CrearMovimientoInput {
  contenedor_id: number;
  tipo: TipoMovimiento;
  ubicacion_destino_id: number;
  observacion?: string;
}

export interface ContextoMovimientoContenedor {
  contenedor_id: number;
  tiene_movimientos: boolean;
  tiene_salida_previa: boolean;
  etiqueta_entrada: "primera_entrada" | "reingreso" | "entrada";
}

export interface CrearUbicacionInput {
  codigo: string;
  nombre: string;
  tipo: TipoUbicacion;
}

export interface ActualizarUbicacionInput {
  nombre?: string;
  tipo?: TipoUbicacion;
  activo?: boolean;
}

export interface ParametrosPagina {
  offset: number;
  limite: number;
  signal?: AbortSignal;
}

export interface ParametrosContenedores extends ParametrosPagina {
  codigo?: string;
  situacion?: SituacionContenedor;
  coherencia?: CoherenciaOperacional;
}

export interface ParametrosMovimientos extends ParametrosPagina {
  orden?: OrdenMovimientos;
}

export interface ParametrosUbicaciones extends ParametrosPagina {
  tipo?: TipoUbicacion;
  incluirInactivas?: boolean;
}
