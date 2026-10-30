import { useCallback, useEffect, useMemo, useState } from "react";

import { UbicacionFormModal } from "../components/ubicaciones/UbicacionFormModal";
import { Alerta, CargandoPanel, EstadoVacio } from "../components/ui/Feedback";
import { useAuth } from "../context/AuthContext";
import { esCancelacion, mensajeErrorApi } from "../lib/errores";
import { actualizarUbicacion, crearUbicacion, listarUbicaciones } from "../lib/logisticaApi";
import type { CrearUbicacionInput, TipoUbicacion, Ubicacion } from "../types/logistica";

export function UbicacionesPage() {
  const { usuario, ejecutarAutenticado } = useAuth();
  const [ubicaciones, setUbicaciones] = useState<Ubicacion[]>([]);
  const [busqueda, setBusqueda] = useState("");
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [confirmacion, setConfirmacion] = useState<string | null>(null);
  const [abierto, setAbierto] = useState(false);
  const [editada, setEditada] = useState<Ubicacion | null>(null);
  const [revision, setRevision] = useState(0);

  const cargar = useCallback(async (signal?: AbortSignal) => {
    setCargando(true);
    setError(null);
    try {
      const datos = await ejecutarAutenticado(async (token) => {
        const todas: Ubicacion[] = [];
        for (let offset = 0; ; offset += 100) {
          const lote = await listarUbicaciones(token, { offset, limite: 100, incluirInactivas: usuario?.rol === "supervisor", signal });
          todas.push(...lote);
          if (lote.length < 100) return todas;
        }
      });
      setUbicaciones(datos);
    } catch (motivo) {
      if (!esCancelacion(motivo)) setError(mensajeErrorApi(motivo, "No fue posible cargar el catálogo."));
    } finally {
      if (!signal?.aborted) setCargando(false);
    }
  }, [ejecutarAutenticado, usuario?.rol]);

  useEffect(() => {
    const controller = new AbortController();
    void cargar(controller.signal);
    return () => controller.abort();
  }, [cargar, revision]);

  const visibles = useMemo(() => {
    const termino = busqueda.trim().toLocaleLowerCase();
    return termino ? ubicaciones.filter((u) => `${u.codigo} ${u.nombre} ${u.tipo}`.toLocaleLowerCase().includes(termino)) : ubicaciones;
  }, [busqueda, ubicaciones]);

  const creada = async (datos: CrearUbicacionInput) => {
    const item = await ejecutarAutenticado((token) => crearUbicacion(token, datos));
    setAbierto(false); setConfirmacion(`Ubicación ${item.codigo} creada.`); setRevision((v) => v + 1);
  };
  const actualizada = async (id: number, datos: { nombre: string; tipo: TipoUbicacion; activo: boolean }) => {
    const item = await ejecutarAutenticado((token) => actualizarUbicacion(token, id, datos));
    setAbierto(false); setEditada(null); setConfirmacion(`Ubicación ${item.codigo} actualizada.`); setRevision((v) => v + 1);
  };

  return (
    <div className="mx-auto max-w-7xl">
      <header className="flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
        <div><p className="text-xs font-bold uppercase tracking-[0.18em] text-harbor-600">Catálogo operacional</p><h1 className="mt-2 text-3xl font-bold tracking-tight text-ink-900">Ubicaciones</h1><p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">Destinos internos y externos controlados. Desactivar conserva todas las referencias históricas.</p></div>
        {usuario?.rol === "supervisor" && <button type="button" onClick={() => { setEditada(null); setAbierto(true); }} className="rounded-xl bg-ink-900 px-5 py-3 text-sm font-bold text-white shadow-panel">＋ Nueva ubicación</button>}
      </header>
      <section className="mt-7 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-100 p-4 sm:p-6"><input value={busqueda} onChange={(e) => setBusqueda(e.target.value)} placeholder="Buscar por código, nombre o tipo" className="h-12 w-full rounded-xl border border-slate-200 px-4 text-sm outline-none focus:border-harbor-500 focus:ring-4 focus:ring-harbor-100" /></div>
        <div className="space-y-3 p-4 empty:hidden sm:px-6 sm:pt-5">{confirmacion && <Alerta tipo="exito">{confirmacion}</Alerta>}{error && <Alerta tipo="error">{error}</Alerta>}</div>
        {cargando ? <CargandoPanel texto="Cargando ubicaciones…" /> : !visibles.length ? <EstadoVacio titulo="No hay ubicaciones" descripcion="El supervisor puede crear la primera ubicación del catálogo." /> : (
          <div className="grid gap-3 p-4 sm:grid-cols-2 sm:p-6 xl:grid-cols-3">
            {visibles.map((ubicacion) => <article key={ubicacion.id} className={`rounded-2xl border p-4 ${ubicacion.activo ? "border-slate-200" : "border-slate-100 bg-slate-50 opacity-70"}`}>
              <div className="flex items-start justify-between gap-3"><div><p className="font-mono text-sm font-bold text-ink-900">{ubicacion.codigo}</p><p className="mt-1 text-sm text-slate-600">{ubicacion.nombre}</p></div><span className={`rounded-full px-2 py-1 text-[10px] font-bold uppercase ${ubicacion.tipo === "interna" ? "bg-harbor-50 text-harbor-700" : "bg-amber-50 text-amber-700"}`}>{ubicacion.tipo}</span></div>
              <div className="mt-4 flex items-center justify-between"><span className={`text-xs font-bold ${ubicacion.activo ? "text-emerald-600" : "text-slate-400"}`}>{ubicacion.activo ? "Habilitada" : "Inactiva"}</span>{usuario?.rol === "supervisor" && <button type="button" onClick={() => { setEditada(ubicacion); setAbierto(true); }} className="rounded-lg bg-slate-100 px-3 py-2 text-xs font-bold text-slate-700">Administrar</button>}</div>
            </article>)}
          </div>
        )}
      </section>
      <UbicacionFormModal abierto={abierto} ubicacion={editada} onCerrar={() => { setAbierto(false); setEditada(null); }} onCrear={creada} onActualizar={actualizada} />
    </div>
  );
}
