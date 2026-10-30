import { type FormEvent, useEffect, useMemo, useState } from "react";

import { mensajeErrorApi } from "../../lib/errores";
import {
  destinosPermitidos,
  etiquetaEntrada,
  operacionesPermitidas,
  resumirMovimiento,
} from "../../lib/movimientosUi";
import {
  MAX_LONGITUD_OBSERVACION,
  type Contenedor,
  type ContextoMovimientoContenedor,
  type CrearMovimientoInput,
  type ParametrosContenedores,
  type TipoMovimiento,
  type Ubicacion,
} from "../../types/logistica";
import { ContenedorCombobox } from "../contenedores/ContenedorCombobox";
import { CoherenciaAviso } from "../contenedores/CoherenciaAviso";
import { UbicacionCombobox } from "../ubicaciones/UbicacionCombobox";
import { Alerta } from "../ui/Feedback";
import { EstadoBadge, textoEstado } from "../ui/EstadoBadge";
import { Modal } from "../ui/Modal";

interface MovimientoFormModalProps {
  abierto: boolean;
  ubicaciones: Ubicacion[];
  onCerrar: () => void;
  onBuscarContenedores: (
    parametros: ParametrosContenedores,
  ) => Promise<Contenedor[]>;
  onConsultarContexto: (contenedorId: number) => Promise<ContextoMovimientoContenedor>;
  onRegistrar: (datos: CrearMovimientoInput) => Promise<void>;
}

const TIPOS: Array<{ valor: TipoMovimiento; titulo: string; descripcion: string; icono: string }> = [
  { valor: "entrada", titulo: "Entrada", descripcion: "Ingreso a una ubicación interna", icono: "↘" },
  { valor: "traslado", titulo: "Traslado", descripcion: "Cambio de ubicación dentro del puerto", icono: "↝" },
  { valor: "salida", titulo: "Salida", descripcion: "Egreso hacia un destino externo", icono: "↗" },
];

const PASOS = ["Contenedor", "Operación", "Destino"];

export function MovimientoFormModal({
  abierto,
  ubicaciones,
  onCerrar,
  onBuscarContenedores,
  onConsultarContexto,
  onRegistrar,
}: MovimientoFormModalProps) {
  const [paso, setPaso] = useState(1);
  const [contenedor, setContenedor] = useState<Contenedor | null>(null);
  const [contexto, setContexto] = useState<ContextoMovimientoContenedor | null>(null);
  const [tipo, setTipo] = useState<TipoMovimiento | null>(null);
  const [destino, setDestino] = useState<Ubicacion | null>(null);
  const [observacion, setObservacion] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [cargandoContexto, setCargandoContexto] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!abierto) return;
    setPaso(1);
    setContenedor(null);
    setContexto(null);
    setTipo(null);
    setDestino(null);
    setObservacion("");
    setError(null);
  }, [abierto]);

  const permitidas = useMemo(
    () => contenedor ? operacionesPermitidas(contenedor) : [],
    [contenedor],
  );
  const destinos = useMemo(
    () => contenedor && tipo ? destinosPermitidos(ubicaciones, tipo, contenedor) : [],
    [contenedor, tipo, ubicaciones],
  );
  const resumen = useMemo(
    () => contenedor && tipo ? resumirMovimiento(contenedor, tipo, destino) : null,
    [contenedor, destino, tipo],
  );

  const seleccionarContenedor = (seleccion: Contenedor | null) => {
    setContenedor(seleccion);
    setContexto(null);
    setDestino(null);
    setError(null);
    if (!seleccion) {
      setTipo(null);
      return;
    }
    const disponibles = operacionesPermitidas(seleccion);
    setTipo(disponibles.length === 1 ? disponibles[0] : null);
    setCargandoContexto(true);
    void onConsultarContexto(seleccion.id)
      .then(setContexto)
      .catch((motivo) => setError(mensajeErrorApi(motivo, "No fue posible consultar el historial del contenedor.")))
      .finally(() => setCargandoContexto(false));
  };

  const avanzarDesdeContenedor = () => {
    if (!contenedor) return setError("Selecciona un contenedor para continuar.");
    setError(null);
    setPaso(2);
  };

  const avanzarDesdeOperacion = () => {
    if (!tipo || !permitidas.includes(tipo)) return setError("Selecciona una operación habilitada para el estado actual.");
    setError(null);
    setPaso(3);
  };

  const enviar = async (evento: FormEvent<HTMLFormElement>) => {
    evento.preventDefault();
    setError(null);
    if (!contenedor || !tipo || !permitidas.includes(tipo)) return setError("Revisa el contenedor y la operación seleccionada.");
    if (!destino || !destinos.some((item) => item.id === destino.id)) return setError("Selecciona un destino válido del catálogo.");

    const datos: CrearMovimientoInput = {
      contenedor_id: contenedor.id,
      tipo,
      ubicacion_destino_id: destino.id,
    };
    if (observacion.trim()) datos.observacion = observacion.trim();

    setEnviando(true);
    try {
      await onRegistrar(datos);
    } catch (motivo) {
      setError(mensajeErrorApi(motivo, "No fue posible registrar el movimiento."));
    } finally {
      setEnviando(false);
    }
  };

  return (
    <Modal abierto={abierto} titulo="Registrar movimiento" descripcion="El usuario responsable se obtiene de tu sesión autenticada." onCerrar={onCerrar} bloqueado={enviando} ancho="amplio">
      <ol className="mb-7 grid grid-cols-3 gap-2" aria-label="Progreso del registro">
        {PASOS.map((nombre, indice) => {
          const numero = indice + 1;
          const activo = paso === numero;
          const completado = paso > numero;
          return (
            <li key={nombre} aria-current={activo ? "step" : undefined}>
              <div className={`h-1 rounded-full ${activo || completado ? "bg-harbor-500" : "bg-slate-200"}`} />
              <div className="mt-2 flex items-center gap-2">
                <span className={`grid h-6 w-6 shrink-0 place-items-center rounded-full text-[10px] font-bold ${activo ? "bg-harbor-500 text-white" : completado ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-400"}`}>{completado ? "✓" : numero}</span>
                <span className={`hidden text-xs font-bold sm:block ${activo ? "text-ink-900" : "text-slate-400"}`}>{nombre}</span>
              </div>
            </li>
          );
        })}
      </ol>

      <form onSubmit={enviar}>
        {paso === 1 && (
          <section aria-labelledby="paso-contenedor">
            <p id="paso-contenedor" className="mb-5 text-sm leading-6 text-slate-500">Busca y filtra contenedores por su situación portuaria. La ubicación solo se considera confirmada cuando posee referencia al catálogo.</p>
            <ContenedorCombobox id="movimiento-contenedor" etiqueta="1. Selecciona el contenedor" seleccionado={contenedor} onSeleccionar={seleccionarContenedor} onBuscar={onBuscarContenedores} ayuda="Escribe el inicio del código o carga más resultados. Usa las flechas y Enter para seleccionar." autoFocus />
            {contenedor && (
              <div className="mt-5 space-y-3">
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="font-mono text-base font-bold tracking-wide text-ink-900">{contenedor.codigo}</p>
                    <p className="mt-1 text-sm text-slate-500">{contenedor.ubicacion_actual}</p>
                    <p className="mt-1 text-xs font-semibold text-harbor-700">{cargandoContexto ? "Consultando historial…" : etiquetaEntrada(contexto)}</p>
                  </div>
                  <EstadoBadge estado={contenedor.estado} />
                </div>
              </div>
              <CoherenciaAviso contenedor={contenedor} />
              </div>
            )}
          </section>
        )}

        {paso === 2 && contenedor && (
          <section aria-labelledby="paso-operacion">
            <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
              <div><h3 id="paso-operacion" className="text-sm font-bold text-slate-700">2. Elige la operación</h3><p className="mt-1 text-xs text-slate-500">{contenedor.codigo} está en <strong className="capitalize">{textoEstado(contenedor.estado)}</strong>.</p></div>
              <button type="button" onClick={() => setPaso(1)} className="text-xs font-bold text-harbor-700">Cambiar contenedor</button>
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              {TIPOS.map((opcion) => {
                const habilitada = permitidas.includes(opcion.valor);
                const titulo = opcion.valor === "entrada" ? etiquetaEntrada(contexto) : opcion.titulo;
                return (
                  <label key={opcion.valor} className={`relative rounded-2xl border p-4 transition ${!habilitada ? "cursor-not-allowed border-slate-100 bg-slate-50 opacity-55" : tipo === opcion.valor ? "cursor-pointer border-harbor-500 bg-harbor-50 ring-2 ring-harbor-100" : "cursor-pointer border-slate-200 hover:border-harbor-300"}`}>
                    <input type="radio" name="tipo" value={opcion.valor} checked={tipo === opcion.valor} disabled={!habilitada} onChange={() => { setTipo(opcion.valor); setDestino(null); setError(null); }} className="sr-only" />
                    <span className={`grid h-9 w-9 place-items-center rounded-xl text-xl ${habilitada ? "bg-white text-harbor-700 shadow-sm" : "bg-slate-100 text-slate-400"}`} aria-hidden="true">{opcion.icono}</span>
                    <span className="mt-4 block text-sm font-bold text-ink-900">{titulo}</span>
                    <span className="mt-1 block text-xs leading-5 text-slate-500">{opcion.descripcion}</span>
                    {!habilitada && <span className="mt-3 block text-[10px] font-bold uppercase tracking-wider text-slate-400">No disponible</span>}
                  </label>
                );
              })}
            </div>
            {permitidas.length === 0 && <div className="mt-5"><Alerta tipo="error">El estado actual no admite operaciones según las reglas vigentes.</Alerta></div>}
          </section>
        )}

        {paso === 3 && contenedor && tipo && resumen && (
          <section aria-labelledby="paso-destino">
            <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
              <div><h3 id="paso-destino" className="text-sm font-bold text-slate-700">3. Define el destino</h3><p className="mt-1 text-xs text-slate-500 capitalize">{tipo} · {contenedor.codigo}</p></div>
              <button type="button" onClick={() => setPaso(2)} className="text-xs font-bold text-harbor-700">Cambiar operación</button>
            </div>
            <UbicacionCombobox
              id="movimiento-destino"
              etiqueta={tipo === "salida" ? "Destino externo" : "Ubicación interna de destino"}
              ubicaciones={destinos}
              seleccionada={destino}
              onSeleccionar={(seleccion) => { setDestino(seleccion); setError(null); }}
              ayuda={destinos.length ? "Solo se muestran ubicaciones activas compatibles con la operación." : "No hay destinos activos compatibles. Solicita al supervisor revisar el catálogo."}
              autoFocus
            />
            <div className="mt-5">
              <label htmlFor="movimiento-observacion" className="mb-2 block text-sm font-bold text-slate-700">Observación <span className="font-normal text-slate-400">(opcional)</span></label>
              <textarea id="movimiento-observacion" value={observacion} onChange={(evento) => setObservacion(evento.target.value)} maxLength={MAX_LONGITUD_OBSERVACION} rows={3} placeholder="Información relevante para la operación" className="w-full resize-y rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none transition focus:border-harbor-500 focus:ring-4 focus:ring-harbor-100" />
              <p className="mt-1 text-right text-[10px] tabular-nums text-slate-400">{observacion.length}/{MAX_LONGITUD_OBSERVACION}</p>
            </div>
            <div className="mt-6 overflow-hidden rounded-2xl border border-harbor-100 bg-harbor-50/60">
              <div className="border-b border-harbor-100 px-4 py-3"><p className="text-[10px] font-bold uppercase tracking-[0.18em] text-harbor-700">Vista previa de la operación</p></div>
              <div className="grid gap-4 p-4 sm:grid-cols-[1fr_auto_1fr] sm:items-center">
                <div><p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Origen actual</p><p className="mt-1 text-sm font-bold text-ink-900">{resumen.origen}</p><p className="mt-1 text-xs capitalize text-slate-500">{textoEstado(contenedor.estado)}</p></div>
                <span className="text-2xl text-harbor-500" aria-hidden="true">→</span>
                <div><p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Destino seleccionado</p><p className={`mt-1 text-sm font-bold ${resumen.destino ? "text-ink-900" : "text-amber-600"}`}>{resumen.destino || "Falta seleccionar destino"}</p><p className="mt-1 text-xs capitalize text-slate-500">Estado: {textoEstado(resumen.estadoEsperado)}</p></div>
              </div>
            </div>
          </section>
        )}

        {error && <div className="mt-5"><Alerta tipo="error">{error}</Alerta></div>}
        <div className="mt-7 flex flex-col-reverse gap-3 border-t border-slate-100 pt-5 sm:flex-row sm:justify-between">
          <button type="button" onClick={paso === 1 ? onCerrar : () => setPaso((actual) => actual - 1)} disabled={enviando} className="rounded-xl border border-slate-200 px-5 py-3 text-sm font-bold text-slate-600 disabled:opacity-50">{paso === 1 ? "Cancelar" : "Atrás"}</button>
          {paso === 1 && <button type="button" onClick={avanzarDesdeContenedor} disabled={!contenedor} className="rounded-xl bg-ink-900 px-5 py-3 text-sm font-bold text-white disabled:opacity-40">Continuar a operación</button>}
          {paso === 2 && <button type="button" onClick={avanzarDesdeOperacion} disabled={!tipo || permitidas.length === 0} className="rounded-xl bg-ink-900 px-5 py-3 text-sm font-bold text-white disabled:opacity-40">Continuar a destino</button>}
          {paso === 3 && <button type="submit" disabled={enviando || !destino} className="rounded-xl bg-ink-900 px-5 py-3 text-sm font-bold text-white disabled:opacity-40">{enviando ? "Registrando…" : "Confirmar movimiento"}</button>}
        </div>
      </form>
    </Modal>
  );
}
