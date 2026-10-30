import { type KeyboardEvent, useEffect, useId, useMemo, useState } from "react";

import type { Ubicacion } from "../../types/logistica";

interface UbicacionComboboxProps {
  id?: string;
  etiqueta: string;
  ubicaciones: Ubicacion[];
  seleccionada: Ubicacion | null;
  onSeleccionar: (ubicacion: Ubicacion | null) => void;
  ayuda?: string;
  autoFocus?: boolean;
  disabled?: boolean;
}

function normalizar(valor: string): string {
  return valor
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLocaleLowerCase()
    .trim();
}

export function textoSeleccionUbicacion(ubicacion: Ubicacion): string {
  return `${ubicacion.nombre} · ${ubicacion.codigo}`;
}

export function UbicacionCombobox({
  id,
  etiqueta,
  ubicaciones,
  seleccionada,
  onSeleccionar,
  ayuda,
  autoFocus = false,
  disabled = false,
}: UbicacionComboboxProps) {
  const reactId = useId().replaceAll(":", "");
  const inputId = id ?? `ubicacion-${reactId}`;
  const listaId = `${inputId}-lista`;
  const [consulta, setConsulta] = useState("");
  const [abierto, setAbierto] = useState(false);
  const [indiceActivo, setIndiceActivo] = useState(-1);

  useEffect(() => {
    setConsulta(seleccionada ? textoSeleccionUbicacion(seleccionada) : "");
  }, [seleccionada]);

  const resultados = useMemo(() => {
    const termino = normalizar(consulta);
    if (!termino || seleccionada && consulta === textoSeleccionUbicacion(seleccionada)) {
      return ubicaciones;
    }
    return ubicaciones.filter((ubicacion) =>
      normalizar(`${ubicacion.codigo} ${ubicacion.nombre} ${ubicacion.tipo}`).includes(termino),
    );
  }, [consulta, seleccionada, ubicaciones]);

  useEffect(() => {
    setIndiceActivo(abierto && resultados.length ? 0 : -1);
  }, [abierto, consulta, resultados.length]);

  useEffect(() => {
    if (indiceActivo >= 0) {
      document.getElementById(`${listaId}-opcion-${indiceActivo}`)?.scrollIntoView({ block: "nearest" });
    }
  }, [indiceActivo, listaId]);

  const seleccionar = (ubicacion: Ubicacion) => {
    onSeleccionar(ubicacion);
    setConsulta(textoSeleccionUbicacion(ubicacion));
    setAbierto(false);
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
    } else if (evento.key === "Enter" && abierto && indiceActivo >= 0) {
      evento.preventDefault();
      const opcion = resultados[indiceActivo];
      if (opcion) seleccionar(opcion);
    } else if (evento.key === "Escape" || evento.key === "Tab") {
      setAbierto(false);
    }
  };

  return (
    <div>
      <label htmlFor={inputId} className="mb-2 block text-sm font-bold text-slate-700">{etiqueta}</label>
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
          value={consulta}
          onChange={(evento) => {
            setConsulta(evento.target.value);
            setAbierto(true);
            if (seleccionada) onSeleccionar(null);
          }}
          onFocus={() => setAbierto(true)}
          onBlur={() => window.setTimeout(() => setAbierto(false), 120)}
          onKeyDown={manejarTeclado}
          autoComplete="off"
          autoFocus={autoFocus}
          disabled={disabled}
          placeholder="Buscar por código o nombre"
          className="h-12 w-full rounded-xl border border-slate-200 bg-white pl-12 pr-10 text-sm font-semibold text-ink-900 outline-none transition focus:border-harbor-500 focus:ring-4 focus:ring-harbor-100 disabled:bg-slate-100"
        />
        <span className="pointer-events-none absolute right-4 top-1/2 -translate-y-1/2 text-slate-400" aria-hidden="true">⌄</span>

        {abierto && !disabled && (
          <div className="absolute z-40 mt-2 w-full overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl">
            <div id={listaId} role="listbox" aria-label="Ubicaciones disponibles" className="max-h-64 overflow-y-auto overscroll-contain p-2">
              {resultados.length ? resultados.map((ubicacion, indice) => (
                <div
                  id={`${listaId}-opcion-${indice}`}
                  key={ubicacion.id}
                  role="option"
                  aria-selected={seleccionada?.id === ubicacion.id}
                  onMouseDown={(evento) => { evento.preventDefault(); seleccionar(ubicacion); }}
                  onMouseEnter={() => setIndiceActivo(indice)}
                  className={`cursor-pointer rounded-xl px-3 py-3 transition ${indiceActivo === indice ? "bg-harbor-50" : "hover:bg-slate-50"}`}
                >
                  <div className="flex items-center justify-between gap-3">
                    <span className="truncate text-sm font-bold text-ink-900">{ubicacion.nombre}</span>
                    <span className={`rounded-full px-2 py-1 text-[10px] font-bold uppercase ${ubicacion.tipo === "interna" ? "bg-harbor-50 text-harbor-700" : "bg-amber-50 text-amber-700"}`}>{ubicacion.tipo}</span>
                  </div>
                  <p className="mt-1 truncate font-mono text-xs font-semibold tracking-wide text-slate-500">{ubicacion.codigo}</p>
                </div>
              )) : (
                <p className="p-5 text-center text-sm text-slate-500">No hay ubicaciones coincidentes. Debes seleccionar una opción del catálogo.</p>
              )}
            </div>
            {resultados.length > 0 && <p className="border-t border-slate-100 px-4 py-2 text-[10px] text-slate-400">Usa ↑ ↓ para navegar, Enter para seleccionar y Esc para cerrar.</p>}
          </div>
        )}
      </div>
      {ayuda && <p className="mt-1.5 text-xs text-slate-400">{ayuda}</p>}
      <span className="sr-only" aria-live="polite">{seleccionada ? `Seleccionada ${seleccionada.nombre}` : ""}</span>
    </div>
  );
}
