import {
  type KeyboardEvent,
  useCallback,
  useEffect,
  useId,
  useRef,
  useState,
} from "react";

import { esCancelacion, mensajeErrorApi } from "../../lib/errores";
import type {
  Contenedor,
  ParametrosContenedores,
  SituacionContenedor,
} from "../../types/logistica";
import { EstadoBadge } from "../ui/EstadoBadge";

const TAMANO_PAGINA = 20;
const RETRASO_BUSQUEDA_MS = 250;

export function combinarResultadosContenedores<T extends { id: number }>(
  actuales: readonly T[],
  nuevos: readonly T[],
): T[] {
  const ids = new Set(actuales.map((item) => item.id));
  return [...actuales, ...nuevos.filter((item) => !ids.has(item.id))];
}

interface ContenedorComboboxProps {
  id?: string;
  etiqueta: string;
  seleccionado: Contenedor | null;
  onSeleccionar: (contenedor: Contenedor | null) => void;
  onBuscar: (parametros: ParametrosContenedores) => Promise<Contenedor[]>;
  placeholder?: string;
  ayuda?: string;
  autoFocus?: boolean;
  disabled?: boolean;
}

export function ContenedorCombobox({
  id,
  etiqueta,
  seleccionado,
  onSeleccionar,
  onBuscar,
  placeholder = "Buscar por código",
  ayuda,
  autoFocus = false,
  disabled = false,
}: ContenedorComboboxProps) {
  const reactId = useId().replaceAll(":", "");
  const inputId = id ?? `contenedor-${reactId}`;
  const listaId = `${inputId}-lista`;
  const controladorCarga = useRef<AbortController | null>(null);
  const [consulta, setConsulta] = useState(seleccionado?.codigo ?? "");
  const [resultados, setResultados] = useState<Contenedor[]>([]);
  const [abierto, setAbierto] = useState(false);
  const [indiceActivo, setIndiceActivo] = useState(-1);
  const [buscando, setBuscando] = useState(false);
  const [cargandoMas, setCargandoMas] = useState(false);
  const [hayMas, setHayMas] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [situacion, setSituacion] = useState<SituacionContenedor | "todas">("todas");

  useEffect(() => {
    setConsulta(seleccionado?.codigo ?? "");
  }, [seleccionado]);

  const consultarPagina = useCallback(
    async (offset: number, signal: AbortSignal) => {
      const lote = await onBuscar({
        offset,
        limite: TAMANO_PAGINA + 1,
        codigo: consulta.trim() || undefined,
        situacion: situacion === "todas" ? undefined : situacion,
        signal,
      });
      return {
        items: lote.slice(0, TAMANO_PAGINA),
        hayMas: lote.length > TAMANO_PAGINA,
      };
    },
    [consulta, onBuscar, situacion],
  );

  const buscarPrimeraPagina = useCallback(
    async (signal: AbortSignal) => {
      setBuscando(true);
      setError(null);
      try {
        const pagina = await consultarPagina(0, signal);
        if (signal.aborted) return;
        setResultados(pagina.items);
        setHayMas(pagina.hayMas);
      } catch (motivo) {
        if (!esCancelacion(motivo) && !signal.aborted) {
          setResultados([]);
          setHayMas(false);
          setError(mensajeErrorApi(motivo, "No fue posible buscar contenedores."));
        }
      } finally {
        if (!signal.aborted) setBuscando(false);
      }
    },
    [consultarPagina],
  );

  useEffect(() => {
    if (!abierto || disabled) return;
    const controller = new AbortController();
    const espera = window.setTimeout(
      () => void buscarPrimeraPagina(controller.signal),
      consulta.trim() ? RETRASO_BUSQUEDA_MS : 0,
    );
    return () => {
      window.clearTimeout(espera);
      controller.abort();
    };
  }, [abierto, buscarPrimeraPagina, consulta, disabled, situacion]);

  useEffect(() => () => controladorCarga.current?.abort(), []);

  useEffect(() => {
    if (!abierto || resultados.length === 0) {
      setIndiceActivo(-1);
      return;
    }
    setIndiceActivo(0);
  }, [abierto, consulta, resultados.length, situacion]);

  useEffect(() => {
    if (indiceActivo < 0) return;
    document
      .getElementById(`${listaId}-opcion-${indiceActivo}`)
      ?.scrollIntoView({ block: "nearest" });
  }, [indiceActivo, listaId]);

  const seleccionar = (contenedor: Contenedor) => {
    onSeleccionar(contenedor);
    setConsulta(contenedor.codigo);
    setAbierto(false);
    setError(null);
  };

  const cargarMas = async () => {
    if (cargandoMas || !hayMas) return;
    controladorCarga.current?.abort();
    const controller = new AbortController();
    controladorCarga.current = controller;
    setCargandoMas(true);
    setError(null);
    try {
      const pagina = await consultarPagina(resultados.length, controller.signal);
      if (controller.signal.aborted) return;
      setResultados((actuales) =>
        combinarResultadosContenedores(actuales, pagina.items),
      );
      setHayMas(pagina.hayMas);
    } catch (motivo) {
      if (!esCancelacion(motivo) && !controller.signal.aborted) {
        setError(mensajeErrorApi(motivo, "No fue posible cargar más contenedores."));
      }
    } finally {
      if (!controller.signal.aborted) setCargandoMas(false);
    }
  };

  const manejarTeclado = (evento: KeyboardEvent<HTMLInputElement>) => {
    if (evento.key === "ArrowDown") {
      evento.preventDefault();
      setAbierto(true);
      setIndiceActivo((actual) => Math.min(actual + 1, resultados.length - 1));
    } else if (evento.key === "ArrowUp") {
      evento.preventDefault();
      setAbierto(true);
      setIndiceActivo((actual) => Math.max(actual - 1, 0));
    } else if (evento.key === "Enter") {
      evento.preventDefault();
      if (abierto && indiceActivo >= 0 && resultados[indiceActivo]) {
        seleccionar(resultados[indiceActivo]);
      } else {
        setAbierto(true);
      }
    } else if (evento.key === "Escape" || evento.key === "Tab") {
      setAbierto(false);
    }
  };

  const etiquetasSituacion: Record<SituacionContenedor, string> = {
    dentro_puerto: "Dentro del puerto",
    fuera_puerto: "Fuera del puerto",
    presencia_sin_confirmar: "Presencia sin confirmar",
  };

  return (
    <div>
      <label htmlFor={inputId} className="mb-2 block text-sm font-bold text-slate-700">
        {etiqueta}
      </label>
      <div className="relative">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="pointer-events-none absolute left-4 top-3.5 z-10 h-5 w-5 text-slate-400" aria-hidden="true">
          <circle cx="11" cy="11" r="6" /><path d="m16 16 4 4" />
        </svg>
        <input
          id={inputId}
          role="combobox"
          aria-autocomplete="list"
          aria-expanded={abierto}
          aria-controls={listaId}
          aria-activedescendant={indiceActivo >= 0 ? `${listaId}-opcion-${indiceActivo}` : undefined}
          aria-invalid={Boolean(error)}
          value={consulta}
          onChange={(evento) => {
            const valor = evento.target.value.toUpperCase();
            setConsulta(valor);
            setAbierto(true);
            setError(null);
            if (seleccionado && valor !== seleccionado.codigo) onSeleccionar(null);
          }}
          onFocus={() => setAbierto(true)}
          onBlur={() => window.setTimeout(() => setAbierto(false), 120)}
          onKeyDown={manejarTeclado}
          autoFocus={autoFocus}
          autoComplete="off"
          maxLength={20}
          disabled={disabled}
          placeholder={placeholder}
          className="h-12 w-full rounded-xl border border-slate-200 bg-white pl-12 pr-20 font-mono text-sm font-bold uppercase tracking-wide text-ink-900 outline-none transition placeholder:font-sans placeholder:font-normal placeholder:normal-case placeholder:tracking-normal focus:border-harbor-500 focus:ring-4 focus:ring-harbor-100 disabled:bg-slate-50 disabled:text-slate-400"
        />
        {seleccionado ? (
          <button
            type="button"
            onMouseDown={(evento) => evento.preventDefault()}
            onClick={() => {
              onSeleccionar(null);
              setConsulta("");
              setAbierto(true);
            }}
            className="absolute right-3 top-1/2 -translate-y-1/2 rounded-lg px-2 py-1 text-xs font-bold text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
            aria-label="Quitar contenedor seleccionado"
          >
            Limpiar
          </button>
        ) : (
          <span className="pointer-events-none absolute right-4 top-1/2 -translate-y-1/2 text-slate-400" aria-hidden="true">⌄</span>
        )}

        {abierto && !disabled && (
          <div className="absolute z-30 mt-2 w-full overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl">
            <div className="flex gap-1 overflow-x-auto border-b border-slate-100 p-2" aria-label="Filtrar por situación">
              {(["todas", "dentro_puerto", "fuera_puerto", "presencia_sin_confirmar"] as const).map((valor) => (
                <button
                  key={valor}
                  type="button"
                  onMouseDown={(evento) => evento.preventDefault()}
                  onClick={() => setSituacion(valor)}
                  className={`whitespace-nowrap rounded-lg px-2.5 py-1.5 text-[10px] font-bold ${situacion === valor ? "bg-ink-900 text-white" : "bg-slate-50 text-slate-500 hover:bg-slate-100"}`}
                >
                  {valor === "todas" ? "Todos" : etiquetasSituacion[valor]}
                </button>
              ))}
            </div>
            <div id={listaId} role="listbox" aria-label="Resultados de contenedores" className="max-h-64 overflow-y-auto overscroll-contain p-2">
              {buscando ? (
                <p className="p-4 text-center text-sm font-semibold text-slate-500">Buscando contenedores…</p>
              ) : resultados.length > 0 ? (
                <>
                  {resultados.map((contenedor, indice) => (
                    <div
                      key={contenedor.id}
                      id={`${listaId}-opcion-${indice}`}
                      role="option"
                      aria-selected={seleccionado?.id === contenedor.id}
                      onMouseDown={(evento) => {
                        evento.preventDefault();
                        seleccionar(contenedor);
                      }}
                      onMouseEnter={() => setIndiceActivo(indice)}
                      className={`cursor-pointer rounded-xl px-3 py-3 transition ${indiceActivo === indice ? "bg-harbor-50" : "hover:bg-slate-50"}`}
                    >
                      <div className="flex items-center justify-between gap-3">
                        <span className="font-mono text-sm font-bold tracking-wide text-ink-900">{contenedor.codigo}</span>
                        <EstadoBadge estado={contenedor.estado} />
                      </div>
                      <p className="mt-1 truncate text-xs text-slate-500">{contenedor.ubicacion_actual}</p>
                      <p className="mt-1 text-[10px] font-semibold text-harbor-700">{etiquetasSituacion[contenedor.situacion]}</p>
                    </div>
                  ))}
                  {hayMas && (
                    <button
                      type="button"
                      onMouseDown={(evento) => evento.preventDefault()}
                      onClick={() => void cargarMas()}
                      disabled={cargandoMas}
                      className="mt-2 w-full rounded-xl bg-slate-50 px-3 py-2.5 text-xs font-bold text-harbor-700 transition hover:bg-harbor-50 disabled:opacity-50"
                    >
                      {cargandoMas ? "Cargando…" : "Cargar más resultados"}
                    </button>
                  )}
                </>
              ) : (
                <p className="p-4 text-center text-sm font-semibold text-slate-600">No hay contenedores que coincidan.</p>
              )}
            </div>
            <p className="border-t border-slate-100 px-4 py-2 text-[10px] text-slate-400">
              Usa ↑ ↓ para navegar, Enter para seleccionar y Esc para cerrar.
            </p>
          </div>
        )}
      </div>
      {ayuda && <p className="mt-1.5 text-xs text-slate-400">{ayuda}</p>}
      {error && <p role="alert" className="mt-2 text-xs font-semibold text-rose-600">{error}</p>}
      <span className="sr-only" aria-live="polite">
        {buscando
          ? "Buscando contenedores"
          : seleccionado
            ? `Seleccionado ${seleccionado.codigo}`
            : `${resultados.length} contenedores disponibles`}
      </span>
    </div>
  );
}
