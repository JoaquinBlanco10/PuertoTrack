import { type FormEvent, useCallback, useEffect, useState } from "react";

import { AuditoriaDetalleModal } from "../components/auditoria/AuditoriaDetalleModal";
import { Alerta, CargandoPanel, EstadoVacio } from "../components/ui/Feedback";
import { Paginacion } from "../components/ui/Paginacion";
import { useAuth } from "../context/AuthContext";
import { listarAuditoria } from "../lib/auditoriaApi";
import { etiquetaAccion } from "../lib/auditoriaUi";
import { esCancelacion, mensajeErrorApi } from "../lib/errores";
import type { FiltrosAuditoria, RegistroAuditoria } from "../types/auditoria";

const TAMANO_PAGINA = 10;

interface FiltrosFormulario {
  usuarioId: string;
  entidad: string;
  entidadId: string;
  accion: string;
}

const FILTROS_VACIOS: FiltrosFormulario = {
  usuarioId: "",
  entidad: "",
  entidadId: "",
  accion: "",
};

const estilosAccion: Record<string, string> = {
  crear: "border-emerald-200 bg-emerald-50 text-emerald-700",
  actualizar: "border-sky-200 bg-sky-50 text-sky-700",
  registrar_movimiento: "border-violet-200 bg-violet-50 text-violet-700",
  regularizar_ubicacion: "border-amber-200 bg-amber-50 text-amber-700",
};

function formatearFecha(valor: string): string {
  return new Intl.DateTimeFormat("es-CL", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(valor));
}

export function AuditoriaPage() {
  const { usuario, ejecutarAutenticado } = useAuth();
  const [registros, setRegistros] = useState<RegistroAuditoria[]>([]);
  const [formulario, setFormulario] = useState(FILTROS_VACIOS);
  const [filtros, setFiltros] = useState<FiltrosAuditoria>({});
  const [pagina, setPagina] = useState(0);
  const [haySiguiente, setHaySiguiente] = useState(false);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [detalle, setDetalle] = useState<RegistroAuditoria | null>(null);

  const cargar = useCallback(async (signal?: AbortSignal) => {
    setCargando(true);
    setError(null);
    try {
      const datos = await ejecutarAutenticado((token) =>
        listarAuditoria(token, {
          ...filtros,
          offset: pagina * TAMANO_PAGINA,
          limite: TAMANO_PAGINA + 1,
          signal,
        }),
      );
      setHaySiguiente(datos.length > TAMANO_PAGINA);
      setRegistros(datos.slice(0, TAMANO_PAGINA));
    } catch (motivo) {
      if (!esCancelacion(motivo)) {
        setError(mensajeErrorApi(motivo, "No fue posible cargar la auditoría."));
      }
    } finally {
      if (!signal?.aborted) setCargando(false);
    }
  }, [ejecutarAutenticado, filtros, pagina]);

  useEffect(() => {
    const controller = new AbortController();
    void cargar(controller.signal);
    return () => controller.abort();
  }, [cargar]);

  const aplicarFiltros = (evento: FormEvent) => {
    evento.preventDefault();
    const usuarioId = formulario.usuarioId ? Number(formulario.usuarioId) : undefined;
    const entidadId = formulario.entidadId ? Number(formulario.entidadId) : undefined;
    if ((usuarioId !== undefined && usuarioId <= 0) || (entidadId !== undefined && entidadId <= 0)) {
      setError("Los identificadores deben ser números positivos.");
      return;
    }
    setError(null);
    setPagina(0);
    setFiltros({
      usuarioId,
      entidadId,
      entidad: formulario.entidad.trim() || undefined,
      accion: formulario.accion.trim() || undefined,
    });
  };

  const limpiarFiltros = () => {
    setFormulario(FILTROS_VACIOS);
    setFiltros({});
    setPagina(0);
    setError(null);
  };

  const nombreUsuario = (usuarioId: number | null) => {
    if (usuarioId === null) return "Sin usuario asociado";
    if (usuarioId === usuario?.id) return `${usuario.nombre} (tú)`;
    return `Usuario #${usuarioId}`;
  };

  const hayFiltros = Object.keys(filtros).length > 0;

  return (
    <div className="mx-auto max-w-7xl">
      <header>
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-harbor-600">Control y trazabilidad</p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight text-ink-900">Auditoría</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">Consulta las operaciones persistidas y compara sus valores anteriores y nuevos. Los registros se muestran del más reciente al más antiguo.</p>
      </header>

      <section className="mt-7 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <form onSubmit={aplicarFiltros} className="border-b border-slate-100 p-4 sm:p-6">
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <div><label htmlFor="audit-usuario" className="mb-2 block text-xs font-bold text-slate-600">ID de usuario</label><input id="audit-usuario" type="number" min="1" value={formulario.usuarioId} onChange={(e) => setFormulario((actual) => ({ ...actual, usuarioId: e.target.value }))} placeholder="Ej. 4" className="h-11 w-full rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-harbor-500 focus:ring-4 focus:ring-harbor-100" /></div>
            <div><label htmlFor="audit-entidad" className="mb-2 block text-xs font-bold text-slate-600">Entidad</label><input id="audit-entidad" maxLength={50} value={formulario.entidad} onChange={(e) => setFormulario((actual) => ({ ...actual, entidad: e.target.value }))} placeholder="contenedor, movimiento…" className="h-11 w-full rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-harbor-500 focus:ring-4 focus:ring-harbor-100" /></div>
            <div><label htmlFor="audit-entidad-id" className="mb-2 block text-xs font-bold text-slate-600">ID de entidad</label><input id="audit-entidad-id" type="number" min="1" value={formulario.entidadId} onChange={(e) => setFormulario((actual) => ({ ...actual, entidadId: e.target.value }))} placeholder="Ej. 25" className="h-11 w-full rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-harbor-500 focus:ring-4 focus:ring-harbor-100" /></div>
            <div><label htmlFor="audit-accion" className="mb-2 block text-xs font-bold text-slate-600">Acción</label><input id="audit-accion" maxLength={50} value={formulario.accion} onChange={(e) => setFormulario((actual) => ({ ...actual, accion: e.target.value }))} placeholder="crear, actualizar…" className="h-11 w-full rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-harbor-500 focus:ring-4 focus:ring-harbor-100" /></div>
          </div>
          <div className="mt-4 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
            {(hayFiltros || Object.values(formulario).some(Boolean)) && <button type="button" onClick={limpiarFiltros} className="rounded-xl border border-slate-200 px-4 py-2.5 text-xs font-bold text-slate-600 hover:bg-slate-50">Limpiar filtros</button>}
            <button type="submit" disabled={cargando} className="rounded-xl bg-ink-900 px-5 py-2.5 text-xs font-bold text-white transition hover:bg-ink-700 disabled:opacity-50">Aplicar filtros</button>
          </div>
        </form>

        {error && <div className="p-4 sm:px-6"><Alerta tipo="error">{error}</Alerta></div>}

        {cargando ? (
          <CargandoPanel texto="Cargando registros de auditoría…" />
        ) : registros.length === 0 ? (
          <EstadoVacio titulo="No hay registros para mostrar" descripcion={hayFiltros ? "No existen auditorías que coincidan con los filtros aplicados." : "Las operaciones auditadas aparecerán aquí."} />
        ) : (
          <>
            <div className="hidden overflow-x-auto md:block">
              <table className="w-full text-left">
                <thead className="bg-slate-50 text-[10px] font-bold uppercase tracking-[0.16em] text-slate-400"><tr><th className="px-6 py-3.5">Fecha</th><th className="px-6 py-3.5">Responsable</th><th className="px-6 py-3.5">Acción</th><th className="px-6 py-3.5">Registro afectado</th><th className="px-6 py-3.5 text-right">Detalle</th></tr></thead>
                <tbody className="divide-y divide-slate-100">
                  {registros.map((registro) => (
                    <tr key={registro.id} className="transition hover:bg-slate-50/70">
                      <td className="whitespace-nowrap px-6 py-4 text-xs font-semibold text-slate-500"><time dateTime={registro.fecha}>{formatearFecha(registro.fecha)}</time><span className="mt-1 block text-[10px] text-slate-400">Auditoría #{registro.id}</span></td>
                      <td className="px-6 py-4 text-sm font-semibold text-slate-700">{nombreUsuario(registro.usuario_id)}</td>
                      <td className="px-6 py-4"><span className={`inline-flex rounded-full border px-2.5 py-1 text-[10px] font-bold capitalize ${estilosAccion[registro.accion] ?? "border-slate-200 bg-slate-50 text-slate-600"}`}>{etiquetaAccion(registro.accion)}</span></td>
                      <td className="px-6 py-4"><span className="block text-sm font-bold capitalize text-ink-900">{registro.entidad}</span><span className="mt-1 block text-xs text-slate-400">ID #{registro.entidad_id}</span></td>
                      <td className="px-6 py-4 text-right"><button type="button" onClick={() => setDetalle(registro)} className="rounded-lg border border-slate-200 px-3 py-2 text-xs font-bold text-slate-600 transition hover:border-harbor-300 hover:text-harbor-700">Ver cambios</button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="divide-y divide-slate-100 md:hidden">
              {registros.map((registro) => (
                <article key={registro.id} className="p-5">
                  <div className="flex items-start justify-between gap-3"><div><p className="text-xs font-semibold text-slate-500">{formatearFecha(registro.fecha)}</p><p className="mt-1 text-[10px] text-slate-400">Auditoría #{registro.id}</p></div><span className={`rounded-full border px-2.5 py-1 text-[10px] font-bold capitalize ${estilosAccion[registro.accion] ?? "border-slate-200 bg-slate-50 text-slate-600"}`}>{etiquetaAccion(registro.accion)}</span></div>
                  <div className="mt-4 grid grid-cols-2 gap-3"><div><p className="text-[9px] font-bold uppercase tracking-wider text-slate-400">Responsable</p><p className="mt-1 text-sm font-semibold text-slate-700">{nombreUsuario(registro.usuario_id)}</p></div><div><p className="text-[9px] font-bold uppercase tracking-wider text-slate-400">Registro</p><p className="mt-1 text-sm font-bold capitalize text-ink-900">{registro.entidad} #{registro.entidad_id}</p></div></div>
                  <button type="button" onClick={() => setDetalle(registro)} className="mt-4 w-full rounded-xl border border-slate-200 px-4 py-2.5 text-xs font-bold text-slate-600">Ver cambios</button>
                </article>
              ))}
            </div>
          </>
        )}

        {!cargando && <Paginacion pagina={pagina} haySiguiente={haySiguiente} cargando={cargando} onCambiar={setPagina} />}
      </section>

      <AuditoriaDetalleModal registro={detalle} nombreUsuario={detalle ? nombreUsuario(detalle.usuario_id) : ""} onCerrar={() => setDetalle(null)} />
    </div>
  );
}
