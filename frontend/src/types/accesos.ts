export type ResultadoAcceso =
  | "habilitado"
  | "denegado"
  | "revision_manual"
  | "no_determinado";

export interface DecisionAcceso {
  version: 1;
  decision_id: string;
  evento_id: string;
  codigo_contenedor: string;
  contenedor_id: number | null;
  lector: string;
  fecha_evento: string;
  resultado: ResultadoAcceso;
  motivo: string;
  fecha_decision: string;
}

export interface ParametrosAccesos {
  limite?: number;
  resultado?: ResultadoAcceso;
  signal?: AbortSignal;
}
