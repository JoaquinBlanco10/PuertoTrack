export type SnapshotAuditoria = Record<string, unknown>;

export interface RegistroAuditoria {
  id: number;
  usuario_id: number | null;
  accion: string;
  entidad: string;
  entidad_id: number;
  datos_anteriores: SnapshotAuditoria | null;
  datos_nuevos: SnapshotAuditoria | null;
  fecha: string;
}

export interface FiltrosAuditoria {
  usuarioId?: number;
  entidad?: string;
  entidadId?: number;
  accion?: string;
}

export interface ParametrosAuditoria extends FiltrosAuditoria {
  offset: number;
  limite: number;
  signal?: AbortSignal;
}
