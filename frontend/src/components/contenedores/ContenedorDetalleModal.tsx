import type { Contenedor } from "../../types/logistica";
import { CargandoPanel } from "../ui/Feedback";
import { EstadoBadge } from "../ui/EstadoBadge";
import { Modal } from "../ui/Modal";
import { CoherenciaAviso } from "./CoherenciaAviso";

interface ContenedorDetalleModalProps {
  abierto: boolean;
  contenedor: Contenedor | null;
  cargando: boolean;
  onCerrar: () => void;
}

function fecha(valor: string): string {
  return new Intl.DateTimeFormat("es-CL", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(valor));
}

export function ContenedorDetalleModal({
  abierto,
  contenedor,
  cargando,
  onCerrar,
}: ContenedorDetalleModalProps) {
  return (
    <Modal abierto={abierto} titulo="Detalle del contenedor" onCerrar={onCerrar}>
      {cargando || !contenedor ? (
        <CargandoPanel texto="Consultando contenedor…" />
      ) : (
        <div>
          <div className="rounded-2xl bg-ink-900 p-5 text-white">
            <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-harbor-300">Código de identificación</p>
            <p className="mt-2 font-mono text-2xl font-bold tracking-wider">{contenedor.codigo}</p>
            <div className="mt-4"><EstadoBadge estado={contenedor.estado} /></div>
          </div>

          <dl className="mt-6 divide-y divide-slate-100 rounded-2xl border border-slate-200 px-5">
            <div className="grid gap-1 py-4 sm:grid-cols-[10rem_1fr]">
              <dt className="text-xs font-bold uppercase tracking-wider text-slate-400">Identificador</dt>
              <dd className="text-sm font-semibold text-slate-700">#{contenedor.id}</dd>
            </div>
            <div className="grid gap-1 py-4 sm:grid-cols-[10rem_1fr]">
              <dt className="text-xs font-bold uppercase tracking-wider text-slate-400">Ubicación actual</dt>
              <dd className="text-sm font-semibold text-slate-700">{contenedor.ubicacion_actual}</dd>
            </div>
            <div className="grid gap-1 py-4 sm:grid-cols-[10rem_1fr]">
              <dt className="text-xs font-bold uppercase tracking-wider text-slate-400">Creado</dt>
              <dd className="text-sm text-slate-600">{fecha(contenedor.fecha_creacion)}</dd>
            </div>
            <div className="grid gap-1 py-4 sm:grid-cols-[10rem_1fr]">
              <dt className="text-xs font-bold uppercase tracking-wider text-slate-400">Actualizado</dt>
              <dd className="text-sm text-slate-600">{fecha(contenedor.fecha_actualizacion)}</dd>
            </div>
          </dl>
          <div className="mt-5"><CoherenciaAviso contenedor={contenedor} /></div>
        </div>
      )}
    </Modal>
  );
}
