import {
  etiquetaCampo,
  obtenerCambiosAuditoria,
  presentarValor,
} from "../../lib/auditoriaUi";
import type { RegistroAuditoria } from "../../types/auditoria";
import { EstadoVacio } from "../ui/Feedback";
import { Modal } from "../ui/Modal";

interface Props {
  registro: RegistroAuditoria | null;
  nombreUsuario: string;
  onCerrar: () => void;
}

function formatearFecha(valor: string): string {
  return new Intl.DateTimeFormat("es-CL", {
    dateStyle: "long",
    timeStyle: "medium",
  }).format(new Date(valor));
}

function Valor({ valor, existe }: { valor: unknown; existe: boolean }) {
  const presentado = presentarValor(valor, existe);
  const estructurado = typeof valor === "object" && valor !== null;
  return estructurado ? (
    <pre className="mt-1 overflow-x-auto whitespace-pre-wrap break-words rounded-lg bg-white/70 p-2 font-mono text-xs leading-5 text-slate-700">
      {presentado}
    </pre>
  ) : (
    <span className={`mt-1 block break-words text-sm ${existe ? "font-semibold text-ink-900" : "italic text-slate-400"}`}>
      {presentado}
    </span>
  );
}

export function AuditoriaDetalleModal({
  registro,
  nombreUsuario,
  onCerrar,
}: Props) {
  const cambios = registro ? obtenerCambiosAuditoria(registro) : [];

  return (
    <Modal
      abierto={Boolean(registro)}
      titulo={registro ? `Auditoría #${registro.id}` : "Detalle de auditoría"}
      descripcion="Comparación de los datos persistidos antes y después de la operación."
      onCerrar={onCerrar}
      ancho="amplio"
    >
      {registro && (
        <div>
          <dl className="grid gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-4 sm:grid-cols-2">
            <div><dt className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Fecha</dt><dd className="mt-1 text-sm font-semibold text-slate-700">{formatearFecha(registro.fecha)}</dd></div>
            <div><dt className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Responsable</dt><dd className="mt-1 text-sm font-semibold text-slate-700">{nombreUsuario}</dd></div>
            <div><dt className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Acción</dt><dd className="mt-1 text-sm font-semibold capitalize text-slate-700">{registro.accion.replaceAll("_", " ")}</dd></div>
            <div><dt className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Registro afectado</dt><dd className="mt-1 text-sm font-semibold capitalize text-slate-700">{registro.entidad} #{registro.entidad_id}</dd></div>
          </dl>

          <div className="mt-6">
            <div className="flex flex-wrap items-end justify-between gap-2">
              <div><h3 className="font-bold text-ink-900">Cambios registrados</h3><p className="mt-1 text-xs text-slate-500">Solo se muestran campos presentes en los snapshots de auditoría.</p></div>
              <span className="rounded-full bg-harbor-50 px-3 py-1 text-xs font-bold text-harbor-700">{cambios.filter((cambio) => cambio.modificado).length} campos modificados</span>
            </div>

            {cambios.length === 0 ? (
              <EstadoVacio titulo="Sin datos comparables" descripcion="Este registro no contiene datos anteriores ni nuevos." />
            ) : (
              <div className="mt-4 space-y-3">
                {cambios.map((cambio) => (
                  <article key={cambio.campo} className={`overflow-hidden rounded-2xl border ${cambio.modificado ? "border-amber-200" : "border-slate-200"}`}>
                    <header className={`flex items-center justify-between gap-3 px-4 py-2.5 ${cambio.modificado ? "bg-amber-50" : "bg-slate-50"}`}>
                      <h4 className="text-xs font-bold text-slate-700">{etiquetaCampo(cambio.campo)}</h4>
                      <span className={`rounded-full px-2 py-1 text-[9px] font-bold uppercase tracking-wider ${cambio.modificado ? "bg-amber-100 text-amber-700" : "bg-slate-200 text-slate-500"}`}>{cambio.modificado ? "Modificado" : "Sin cambio"}</span>
                    </header>
                    <div className="grid gap-px bg-slate-200 sm:grid-cols-2">
                      <div className="bg-white p-4"><p className="text-[9px] font-bold uppercase tracking-wider text-slate-400">Antes</p><Valor valor={cambio.anterior} existe={cambio.tieneAnterior} /></div>
                      <div className="bg-white p-4"><p className="text-[9px] font-bold uppercase tracking-wider text-harbor-600">Después</p><Valor valor={cambio.nuevo} existe={cambio.tieneNuevo} /></div>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </Modal>
  );
}
