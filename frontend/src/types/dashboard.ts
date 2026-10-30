import type { TipoMovimiento } from "./logistica";

export interface TotalesContenedoresDashboard {
  dentro_puerto: number;
  fuera_puerto: number;
  presencia_sin_confirmar: number;
  inconsistentes: number;
}

export interface MovimientoDiarioDashboard {
  fecha: string;
  entrada: number;
  traslado: number;
  salida: number;
}

export interface MovimientoRecienteDashboard {
  id: number;
  contenedor_id: number;
  contenedor_codigo: string;
  usuario_id: number;
  usuario_nombre: string;
  tipo: TipoMovimiento | null;
  ubicacion_origen: string;
  ubicacion_destino: string;
  fecha_movimiento: string;
}

export interface ResumenDashboard {
  generado_en: string;
  zona_horaria: "UTC";
  periodo: {
    desde: string;
    hasta: string;
    dias: 7;
  };
  contenedores: TotalesContenedoresDashboard;
  movimientos_ultimos_7_dias: MovimientoDiarioDashboard[];
  ultimos_movimientos: MovimientoRecienteDashboard[];
}
