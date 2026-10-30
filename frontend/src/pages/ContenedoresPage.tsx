import { type FormEvent, useCallback, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { ContenedorDetalleModal } from "../components/contenedores/ContenedorDetalleModal";
import { ContenedorFormModal } from "../components/contenedores/ContenedorFormModal";
import { RegularizarUbicacionModal } from "../components/contenedores/RegularizarUbicacionModal";
import { Alerta, CargandoPanel, EstadoVacio } from "../components/ui/Feedback";
import { EstadoBadge } from "../components/ui/EstadoBadge";
import { Paginacion } from "../components/ui/Paginacion";
import { useAuth } from "../context/AuthContext";
import {
  consultaParaFiltro,
  filtroDesdeParametros,
  parametrosDeFiltro,
  type FiltroContenedores,
} from "../lib/contenedoresUi";
import { esCancelacion, mensajeErrorApi } from "../lib/errores";
import {
  buscarContenedorPorCodigo,
  buscarContenedorPorId,
  corregirCodigoContenedor,
  crearContenedor,
  listarContenedores,
  listarUbicaciones,
  regularizarUbicacionContenedor,
} from "../lib/logisticaApi";
import type { Contenedor, CrearContenedorInput, RegularizarContenedorInput, SituacionContenedor, Ubicacion } from "../types/logistica";

const TAMANO_PAGINA = 10;
const FILTROS: FiltroContenedores[] = [
  "todas",
  "dentro_puerto",
  "fuera_puerto",
  "presencia_sin_confirmar",
  "inconsistentes",
];

export function ContenedoresPage() {
  const { usuario, ejecutarAutenticado } = useAuth();
  const [parametrosBusqueda, setParametrosBusqueda] = useSearchParams();
  const filtro = filtroDesdeParametros(parametrosBusqueda);
  const [contenedores, setContenedores] = useState<Contenedor[]>([]);
  const [pagina, setPagina] = useState(0);
  const [haySiguiente, setHaySiguiente] = useState(false);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [confirmacion, setConfirmacion] = useState<string | null>(null);
  const [busqueda, setBusqueda] = useState("");
  const [busquedaActiva, setBusquedaActiva] = useState(false);
  const [revision, setRevision] = useState(0);
  const [formularioAbierto, setFormularioAbierto] = useState(false);
  const [contenedorEditado, setContenedorEditado] = useState<Contenedor | null>(null);
  const [detalleAbierto, setDetalleAbierto] = useState(false);
  const [detalle, setDetalle] = useState<Contenedor | null>(null);
  const [cargandoDetalle, setCargandoDetalle] = useState(false);
  const [regularizado, setRegularizado] = useState<Contenedor | null>(null);
  const [ubicaciones, setUbicaciones] = useState<Ubicacion[]>([]);

  const cargarPagina = useCallback(
    async (signal?: AbortSignal) => {
      setCargando(true);
      setError(null);
      try {
        const datos = await ejecutarAutenticado((token) =>
          listarContenedores(token, {
            offset: pagina * TAMANO_PAGINA,
            limite: TAMANO_PAGINA + 1,
            signal,
            ...consultaParaFiltro(filtro),
          }),
        );
        setHaySiguiente(datos.length > TAMANO_PAGINA);
        setContenedores(datos.slice(0, TAMANO_PAGINA));
      } catch (motivo) {
        if (!esCancelacion(motivo)) setError(mensajeErrorApi(motivo, "No fue posible cargar los contenedores."));
      } finally {
        if (!signal?.aborted) setCargando(false);
      }
    },
    [ejecutarAutenticado, filtro, pagina],
  );

  useEffect(() => {
    if (busquedaActiva) return;
    const controller = new AbortController();
    void cargarPagina(controller.signal);
    return () => controller.abort();
  }, [busquedaActiva, cargarPagina, revision]);

  const buscar = async (evento: FormEvent<HTMLFormElement>) => {
    evento.preventDefault();
    setConfirmacion(null);
    if (!busqueda.trim()) {
      setBusquedaActiva(false);
      setPagina(0);
      setRevision((valor) => valor + 1);
      return;
    }

    setCargando(true);
    setError(null);
    try {
      const resultado = await ejecutarAutenticado((token) =>
        buscarContenedorPorCodigo(token, busqueda),
      );
      setContenedores([resultado]);
      setBusquedaActiva(true);
      setHaySiguiente(false);
    } catch (motivo) {
      setContenedores([]);
      setBusquedaActiva(true);
      setError(mensajeErrorApi(motivo, "No fue posible buscar el contenedor."));
    } finally {
      setCargando(false);
    }
  };

  const limpiarBusqueda = () => {
    setBusqueda("");
    setBusquedaActiva(false);
    setPagina(0);
    setError(null);
    setRevision((valor) => valor + 1);
  };

  const abrirDetalle = async (contenedorId: number) => {
    setDetalle(null);
    setDetalleAbierto(true);
    setCargandoDetalle(true);
    try {
      const resultado = await ejecutarAutenticado((token) =>
        buscarContenedorPorId(token, contenedorId),
      );
      setDetalle(resultado);
    } catch (motivo) {
      setDetalleAbierto(false);
      setError(mensajeErrorApi(motivo, "No fue posible consultar el detalle."));
    } finally {
      setCargandoDetalle(false);
    }
  };

  const refrescarDespuesDeCambio = (mensaje: string) => {
    setFormularioAbierto(false);
    setContenedorEditado(null);
    setConfirmacion(mensaje);
    setBusqueda("");
    setBusquedaActiva(false);
    setPagina(0);
    setRevision((valor) => valor + 1);
  };

  const crear = async (datos: CrearContenedorInput) => {
    const creado = await ejecutarAutenticado((token) => crearContenedor(token, datos));
    refrescarDespuesDeCambio(`Contenedor ${creado.codigo} creado correctamente.`);
  };

  const corregir = async (contenedorId: number, codigo: string) => {
    const actualizado = await ejecutarAutenticado((token) =>
      corregirCodigoContenedor(token, contenedorId, { codigo }),
    );
    refrescarDespuesDeCambio(`Código actualizado a ${actualizado.codigo}.`);
  };

  const abrirCreacion = () => {
    setContenedorEditado(null);
    setFormularioAbierto(true);
  };

  const abrirEdicion = (contenedor: Contenedor) => {
    setContenedorEditado(contenedor);
    setFormularioAbierto(true);
  };

  const abrirRegularizacion = async (contenedor: Contenedor) => {
    setError(null);
    try {
      const catalogo = await ejecutarAutenticado(async (token) => {
        const todas: Ubicacion[] = [];
        for (let offset = 0; ; offset += 100) {
          const lote = await listarUbicaciones(token, {
            offset,
            limite: 100,
          });
          todas.push(...lote);
          if (lote.length < 100) return todas;
        }
      });
      setUbicaciones(catalogo);
      setRegularizado(contenedor);
    } catch (motivo) {
      setError(mensajeErrorApi(motivo, "No fue posible cargar las ubicaciones."));
    }
  };

  const regularizar = async (
    contenedorId: number,
    datos: RegularizarContenedorInput,
  ) => {
    const actualizado = await ejecutarAutenticado((token) =>
      regularizarUbicacionContenedor(token, contenedorId, datos),
    );
    setRegularizado(null);
    refrescarDespuesDeCambio(`Ubicación de ${actualizado.codigo} regularizada y auditada.`);
  };

  const etiquetaSituacion: Record<SituacionContenedor, string> = {
    dentro_puerto: "Dentro del puerto",
    fuera_puerto: "Fuera del puerto",
    presencia_sin_confirmar: "Presencia sin confirmar",
  };
  const etiquetaFiltro: Record<FiltroContenedores, string> = {
    todas: "Todos",
    ...etiquetaSituacion,
    inconsistentes: "Con inconsistencias",
  };

  const cambiarFiltro = (nuevoFiltro: FiltroContenedores) => {
    setPagina(0);
    setBusqueda("");
    setBusquedaActiva(false);
    setParametrosBusqueda(parametrosDeFiltro(nuevoFiltro), { replace: true });
  };

  const requiereRevision = (contenedor: Contenedor) =>
    contenedor.coherencia_operacional === "inconsistente" ||
    (contenedor.coherencia_operacional === "sin_confirmar" &&
      contenedor.estado === "en_patio");

  return (
    <div className="mx-auto max-w-7xl">
      <header className="flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-harbor-600">Inventario portuario</p>
          <h1 className="mt-2 text-3xl font-bold tracking-tight text-ink-900">Contenedores</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">
            Consulta ubicación y estado. Los cambios operacionales se realizan exclusivamente desde Movimientos.
          </p>
        </div>
        {usuario?.rol === "supervisor" && (
          <button
            type="button"
            onClick={abrirCreacion}
            className="inline-flex items-center justify-center gap-2 rounded-xl bg-ink-900 px-5 py-3 text-sm font-bold text-white shadow-panel transition hover:bg-ink-700 focus:outline-none focus:ring-4 focus:ring-harbor-200"
          >
            <span className="text-lg leading-none" aria-hidden="true">＋</span>
            Nuevo contenedor
          </button>
        )}
      </header>

      <section className="mt-7 rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-100 p-4 sm:p-6">
          <form onSubmit={buscar} className="flex flex-col gap-3 sm:flex-row">
            <div className="relative flex-1">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" aria-hidden="true">
                <circle cx="11" cy="11" r="6" /><path d="m16 16 4 4" />
              </svg>
              <input
                value={busqueda}
                onChange={(evento) => setBusqueda(evento.target.value.toUpperCase())}
                maxLength={20}
                placeholder="Buscar por código exacto"
                aria-label="Código del contenedor"
                className="h-12 w-full rounded-xl border border-slate-200 pl-12 pr-4 font-mono text-sm font-semibold uppercase outline-none transition focus:border-harbor-500 focus:ring-4 focus:ring-harbor-100"
              />
            </div>
            <button type="submit" disabled={cargando} className="h-12 rounded-xl bg-harbor-600 px-5 text-sm font-bold text-white transition hover:bg-harbor-700 disabled:opacity-50">
              Buscar
            </button>
            {busquedaActiva && (
              <button type="button" onClick={limpiarBusqueda} className="h-12 rounded-xl border border-slate-200 px-5 text-sm font-bold text-slate-600 transition hover:bg-slate-50">
                Ver todos
              </button>
            )}
          </form>
          {!busquedaActiva && (
            <div className="mt-4 flex flex-wrap gap-2" aria-label="Filtrar contenedores">
              {FILTROS.map((valor) => (
                <button key={valor} type="button" onClick={() => cambiarFiltro(valor)} className={`rounded-full px-3 py-2 text-xs font-bold ${filtro === valor ? "bg-ink-900 text-white" : "bg-slate-100 text-slate-600"}`}>{etiquetaFiltro[valor]}</button>
              ))}
            </div>
          )}
        </div>

        <div className="space-y-3 p-4 empty:hidden sm:px-6 sm:pt-5">
          {confirmacion && <Alerta tipo="exito">{confirmacion}</Alerta>}
          {error && <Alerta tipo="error">{error}</Alerta>}
        </div>

        {cargando ? (
          <CargandoPanel texto="Cargando contenedores…" />
        ) : contenedores.length === 0 ? (
          <EstadoVacio
            titulo={busquedaActiva ? "No encontramos ese contenedor" : filtro === "todas" ? "Aún no hay contenedores" : "No hay contenedores con este filtro"}
            descripcion={busquedaActiva ? "Comprueba el código o vuelve al listado completo." : filtro === "todas" ? "Los contenedores registrados aparecerán aquí." : "Selecciona otro filtro para consultar el inventario."}
          />
        ) : (
          <>
            <div className="hidden overflow-x-auto md:block">
              <table className="w-full text-left">
                <thead className="bg-slate-50 text-[10px] font-bold uppercase tracking-[0.16em] text-slate-400">
                  <tr>
                    <th className="px-6 py-3.5">Código</th>
                    <th className="px-6 py-3.5">Ubicación actual</th>
                    <th className="px-6 py-3.5">Estado</th>
                    <th className="px-6 py-3.5">Situación</th>
                    <th className="px-6 py-3.5 text-right">Acciones</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {contenedores.map((contenedor) => (
                    <tr key={contenedor.id} className="transition hover:bg-slate-50/70">
                      <td className="px-6 py-4 font-mono text-sm font-bold tracking-wide text-ink-900">{contenedor.codigo}</td>
                      <td className="px-6 py-4 text-sm text-slate-600">{contenedor.ubicacion_actual}</td>
                      <td className="px-6 py-4"><EstadoBadge estado={contenedor.estado} /></td>
                      <td className="px-6 py-4 text-xs font-semibold text-slate-500">
                        <span className="block">{etiquetaSituacion[contenedor.situacion]}</span>
                        {requiereRevision(contenedor) && <span className="mt-1 block font-bold text-rose-600">⚠ Requiere revisar coherencia</span>}
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex justify-end gap-2">
                          <button type="button" onClick={() => void abrirDetalle(contenedor.id)} className="rounded-lg border border-slate-200 px-3 py-2 text-xs font-bold text-slate-600 transition hover:border-harbor-300 hover:text-harbor-700">Ver detalle</button>
                          {usuario?.rol === "supervisor" && (
                            <><button type="button" onClick={() => abrirEdicion(contenedor)} className="rounded-lg bg-slate-100 px-3 py-2 text-xs font-bold text-slate-700 transition hover:bg-slate-200">Corregir código</button>{contenedor.regularizacion_permitida && <button type="button" onClick={() => void abrirRegularizacion(contenedor)} className="rounded-lg bg-amber-50 px-3 py-2 text-xs font-bold text-amber-700">Regularizar historial</button>}</>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="divide-y divide-slate-100 md:hidden">
              {contenedores.map((contenedor) => (
                <article key={contenedor.id} className="p-5">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-mono text-base font-bold tracking-wide text-ink-900">{contenedor.codigo}</p>
                      <p className="mt-1 text-sm text-slate-500">{contenedor.ubicacion_actual}</p>
                      <p className="mt-1 text-xs font-semibold text-harbor-700">{etiquetaSituacion[contenedor.situacion]}</p>
                      {requiereRevision(contenedor) && <p className="mt-1 text-xs font-bold text-rose-600">⚠ Requiere revisar coherencia</p>}
                    </div>
                    <EstadoBadge estado={contenedor.estado} />
                  </div>
                  <div className="mt-4 flex flex-wrap gap-2">
                    <button type="button" onClick={() => void abrirDetalle(contenedor.id)} className="rounded-lg border border-slate-200 px-3 py-2 text-xs font-bold text-slate-600">Ver detalle</button>
                    {usuario?.rol === "supervisor" && (
                      <><button type="button" onClick={() => abrirEdicion(contenedor)} className="rounded-lg bg-slate-100 px-3 py-2 text-xs font-bold text-slate-700">Corregir código</button>{contenedor.regularizacion_permitida && <button type="button" onClick={() => void abrirRegularizacion(contenedor)} className="rounded-lg bg-amber-50 px-3 py-2 text-xs font-bold text-amber-700">Regularizar historial</button>}</>
                    )}
                  </div>
                </article>
              ))}
            </div>
          </>
        )}

        {!busquedaActiva && !cargando && (
          <Paginacion pagina={pagina} haySiguiente={haySiguiente} onCambiar={setPagina} />
        )}
      </section>

      <ContenedorFormModal
        abierto={formularioAbierto}
        contenedor={contenedorEditado}
        onCerrar={() => {
          setFormularioAbierto(false);
          setContenedorEditado(null);
        }}
        onCrear={crear}
        onCorregir={corregir}
      />
      <ContenedorDetalleModal
        abierto={detalleAbierto}
        contenedor={detalle}
        cargando={cargandoDetalle}
        onCerrar={() => setDetalleAbierto(false)}
      />
      <RegularizarUbicacionModal abierto={Boolean(regularizado)} contenedor={regularizado} ubicaciones={ubicaciones} onCerrar={() => setRegularizado(null)} onConfirmar={regularizar} />
    </div>
  );
}
