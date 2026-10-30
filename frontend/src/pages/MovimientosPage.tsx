import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { ContenedorCombobox } from "../components/contenedores/ContenedorCombobox";
import { MovimientoFormModal } from "../components/movimientos/MovimientoFormModal";
import { MovimientoTimeline } from "../components/movimientos/MovimientoTimeline";
import { Alerta, CargandoPanel, EstadoVacio } from "../components/ui/Feedback";
import { Paginacion } from "../components/ui/Paginacion";
import { useAuth } from "../context/AuthContext";
import { esCancelacion, mensajeErrorApi } from "../lib/errores";
import {
  buscarContenedorPorId,
  listarContenedores,
  listarUbicaciones,
  listarMovimientos,
  listarMovimientosPorContenedor,
  obtenerContextoMovimiento,
  registrarMovimiento,
} from "../lib/logisticaApi";
import { incorporarMovimientoReciente } from "../lib/movimientosUi";
import type {
  Contenedor,
  ContextoMovimientoContenedor,
  CrearMovimientoInput,
  Movimiento,
  ParametrosContenedores,
  Ubicacion,
} from "../types/logistica";

const TAMANO_PAGINA = 10;

export function MovimientosPage() {
  const { usuario, ejecutarAutenticado } = useAuth();
  const [movimientos, setMovimientos] = useState<Movimiento[]>([]);
  const [contenedores, setContenedores] = useState<Contenedor[]>([]);
  const [ubicaciones, setUbicaciones] = useState<Ubicacion[]>([]);
  const [pagina, setPagina] = useState(0);
  const [haySiguiente, setHaySiguiente] = useState(false);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [confirmacion, setConfirmacion] = useState<string | null>(null);
  const [formularioAbierto, setFormularioAbierto] = useState(false);
  const [filtroContenedor, setFiltroContenedor] = useState<Contenedor | null>(null);
  const omitirSiguienteCarga = useRef(false);

  const buscarContenedores = useCallback(async (parametros: ParametrosContenedores) => {
    const encontrados = await ejecutarAutenticado((token) =>
      listarContenedores(token, parametros),
    );
    setContenedores((actuales) => {
      const porId = new Map(actuales.map((item) => [item.id, item]));
      for (const encontrado of encontrados) porId.set(encontrado.id, encontrado);
      return [...porId.values()];
    });
    return encontrados;
  }, [ejecutarAutenticado]);

  const cargarUbicaciones = useCallback(async () => {
    try {
      const catalogoUbicaciones = await ejecutarAutenticado(async (token) => {
        const todas: Ubicacion[] = [];
        for (let offset = 0; ; offset += 100) {
          const lote = await listarUbicaciones(token, { offset, limite: 100 });
          todas.push(...lote);
          if (lote.length < 100) break;
        }
        return todas;
      });
      setUbicaciones(catalogoUbicaciones);
    } catch (motivo) {
      if (!esCancelacion(motivo)) setError(mensajeErrorApi(motivo, "No fue posible cargar las ubicaciones disponibles."));
    }
  }, [ejecutarAutenticado]);

  const consultarContexto = useCallback(
    (contenedorId: number): Promise<ContextoMovimientoContenedor> =>
      ejecutarAutenticado((token) => obtenerContextoMovimiento(token, contenedorId)),
    [ejecutarAutenticado],
  );

  useEffect(() => {
    void cargarUbicaciones();
  }, [cargarUbicaciones]);

  const cargarHistorial = useCallback(
    async (signal?: AbortSignal) => {
      setCargando(true);
      setError(null);
      try {
        const parametros = {
          offset: pagina * TAMANO_PAGINA,
          limite: TAMANO_PAGINA + 1,
          orden: "desc" as const,
          signal,
        };
        const datos = await ejecutarAutenticado((token) =>
          filtroContenedor
            ? listarMovimientosPorContenedor(token, filtroContenedor.id, parametros)
            : listarMovimientos(token, parametros),
        );
        setHaySiguiente(datos.length > TAMANO_PAGINA);
        setMovimientos(datos.slice(0, TAMANO_PAGINA));
      } catch (motivo) {
        if (!esCancelacion(motivo)) setError(mensajeErrorApi(motivo, "No fue posible cargar el historial."));
      } finally {
        if (!signal?.aborted) setCargando(false);
      }
    },
    [ejecutarAutenticado, filtroContenedor?.id, pagina],
  );

  useEffect(() => {
    if (omitirSiguienteCarga.current) {
      omitirSiguienteCarga.current = false;
      return;
    }
    const controller = new AbortController();
    void cargarHistorial(controller.signal);
    return () => controller.abort();
  }, [cargarHistorial]);

  const cambiarFiltro = (contenedor: Contenedor | null) => {
    setConfirmacion(null);
    setError(null);
    setFiltroContenedor(contenedor);
    setPagina(0);
  };

  const limpiarFiltro = () => {
    cambiarFiltro(null);
  };

  const registrar = async (datos: CrearMovimientoInput) => {
    const movimiento = await ejecutarAutenticado((token) => registrarMovimiento(token, datos));
    const contenedorMovimiento = contenedores.find(
      (item) => item.id === movimiento.contenedor_id,
    );
    const cambiaraConsulta =
      pagina !== 0 || filtroContenedor?.id !== contenedorMovimiento?.id;
    if (cambiaraConsulta) omitirSiguienteCarga.current = true;
    setFormularioAbierto(false);
    setFiltroContenedor(contenedorMovimiento ?? null);
    setPagina(0);
    setHaySiguiente(false);
    setMovimientos((actuales) =>
      incorporarMovimientoReciente(actuales, movimiento, TAMANO_PAGINA),
    );
    setConfirmacion(
      `Movimiento #${movimiento.id} para ${contenedorMovimiento?.codigo ?? `contenedor #${movimiento.contenedor_id}`} registrado: ${movimiento.ubicacion_origen} → ${movimiento.ubicacion_destino}.`,
    );

    void ejecutarAutenticado(async (token) => {
      const [contenedorActualizado, historial] = await Promise.all([
        buscarContenedorPorId(token, movimiento.contenedor_id),
        contenedorMovimiento
          ? listarMovimientosPorContenedor(token, movimiento.contenedor_id, {
              offset: 0,
              limite: TAMANO_PAGINA + 1,
              orden: "desc",
            })
          : listarMovimientos(token, {
              offset: 0,
              limite: TAMANO_PAGINA + 1,
              orden: "desc",
            }),
      ]);
      return { contenedorActualizado, historial };
    }).then(({ contenedorActualizado, historial }) => {
      setContenedores((actuales) => {
        const restantes = actuales.filter((item) => item.id !== contenedorActualizado.id);
        return [...restantes, contenedorActualizado];
      });
      if (contenedorMovimiento) setFiltroContenedor(contenedorActualizado);
      setHaySiguiente(historial.length > TAMANO_PAGINA);
      setMovimientos(
        incorporarMovimientoReciente(
          historial.slice(0, TAMANO_PAGINA),
          movimiento,
          TAMANO_PAGINA,
        ),
      );
    }).catch((motivo) => {
      if (!esCancelacion(motivo)) {
        setError(mensajeErrorApi(motivo, "El movimiento fue registrado, pero no se pudo actualizar todo el historial."));
      }
    });
  };

  const codigosPorContenedor = useMemo(
    () => new Map(contenedores.map((contenedor) => [contenedor.id, contenedor.codigo])),
    [contenedores],
  );

  if (!usuario) return null;

  return (
    <div className="mx-auto max-w-7xl">
      <header className="flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-harbor-600">Trazabilidad operacional</p>
          <h1 className="mt-2 text-3xl font-bold tracking-tight text-ink-900">Movimientos</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">
            Registra entradas, traslados y salidas. Las reglas de transición se validan en la API.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setFormularioAbierto(true)}
          className="inline-flex items-center justify-center gap-2 rounded-xl bg-ink-900 px-5 py-3 text-sm font-bold text-white shadow-panel transition hover:bg-ink-700 focus:outline-none focus:ring-4 focus:ring-harbor-200"
        >
          <span className="text-lg leading-none" aria-hidden="true">＋</span>
          Registrar movimiento
        </button>
      </header>

      <section className="mt-7 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-100 p-4 sm:p-6">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="font-bold text-ink-900">
                {filtroContenedor ? `Historial · ${filtroContenedor.codigo}` : "Historial global"}
              </h2>
              <p className="mt-1 text-xs text-slate-400">Movimientos más recientes primero.</p>
            </div>
            {filtroContenedor && (
              <span className="rounded-full bg-harbor-50 px-3 py-1.5 text-xs font-bold text-harbor-700">
                {filtroContenedor.ubicacion_actual}
              </span>
            )}
          </div>

          <div className="grid gap-3 sm:grid-cols-[1fr_auto] sm:items-end">
            <ContenedorCombobox
              id="filtro-historial-contenedor"
              etiqueta="Filtrar historial por contenedor"
              seleccionado={filtroContenedor}
              onSeleccionar={cambiarFiltro}
              onBuscar={buscarContenedores}
              placeholder="Buscar por código"
              ayuda="La selección actualiza el historial automáticamente."
            />
            {filtroContenedor && (
              <button type="button" onClick={limpiarFiltro} className="h-12 rounded-xl border border-slate-200 px-5 text-sm font-bold text-slate-600 transition hover:bg-slate-50">
                Ver historial global
              </button>
            )}
          </div>
        </div>

        <div className="space-y-3 p-4 empty:hidden sm:px-6 sm:pt-5">
          {confirmacion && <Alerta tipo="exito">{confirmacion}</Alerta>}
          {error && <Alerta tipo="error">{error}</Alerta>}
        </div>

        {cargando ? (
          <CargandoPanel texto="Cargando historial…" />
        ) : movimientos.length === 0 ? (
          <EstadoVacio
            titulo="No hay movimientos para mostrar"
            descripcion={filtroContenedor ? "Este contenedor todavía no registra movimientos." : "Los movimientos registrados aparecerán en esta línea de tiempo."}
          />
        ) : (
          <MovimientoTimeline
            movimientos={movimientos}
            usuario={usuario}
            codigosPorContenedor={codigosPorContenedor}
          />
        )}

        {!cargando && (
          <Paginacion pagina={pagina} haySiguiente={haySiguiente} onCambiar={setPagina} />
        )}
      </section>

      <MovimientoFormModal
        abierto={formularioAbierto}
        ubicaciones={ubicaciones}
        onCerrar={() => setFormularioAbierto(false)}
        onBuscarContenedores={buscarContenedores}
        onConsultarContexto={consultarContexto}
        onRegistrar={registrar}
      />
    </div>
  );
}
