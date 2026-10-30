import { useCallback, useEffect, useState } from "react";

import { ResultadoAccesoBadge } from "../components/accesos/ResultadoAccesoBadge";
import { Alerta, CargandoPanel, EstadoVacio } from "../components/ui/Feedback";
import { useAuth } from "../context/AuthContext";
import { listarDecisionesAcceso } from "../lib/accesosApi";
import { esCancelacion, mensajeErrorApi } from "../lib/errores";
import type { DecisionAcceso, ResultadoAcceso } from "../types/accesos";

function formatearFecha(valor: string): string {
  return new Intl.DateTimeFormat("es-CL", {
    dateStyle: "medium",
    timeStyle: "medium",
  }).format(new Date(valor));
}

export function AccesosPage() {
  const { ejecutarAutenticado } = useAuth();
  const [decisiones, setDecisiones] = useState<DecisionAcceso[]>([]);
  const [resultado, setResultado] = useState<ResultadoAcceso | "">("");
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const cargar = useCallback(
    async (signal?: AbortSignal) => {
      setCargando(true);
      setError(null);
      try {
        const datos = await ejecutarAutenticado((token) =>
          listarDecisionesAcceso(token, {
            limite: 50,
            resultado: resultado || undefined,
            signal,
          }),
        );
        setDecisiones(datos);
      } catch (motivo) {
        if (!esCancelacion(motivo)) {
          setError(
            mensajeErrorApi(
              motivo,
              "No fue posible consultar el servicio de accesos.",
            ),
          );
        }
      } finally {
        if (!signal?.aborted) setCargando(false);
      }
    },
    [ejecutarAutenticado, resultado],
  );

  useEffect(() => {
    const controller = new AbortController();
    void cargar(controller.signal);
    return () => controller.abort();
  }, [cargar]);

  return (
    <div className="mx-auto max-w-7xl">
      <header className="flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-harbor-600">
            Control de acceso
          </p>
          <h1 className="mt-2 text-3xl font-bold tracking-tight text-ink-900">
            Habilitación preliminar
          </h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-500">
            Resultados recientes derivados de identificaciones RFID. Una
            habilitación es informativa: no abre barreras ni registra movimientos.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void cargar()}
          disabled={cargando}
          className="rounded-xl bg-ink-900 px-5 py-2.5 text-xs font-bold text-white transition hover:bg-ink-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {cargando ? "Actualizando…" : "Actualizar"}
        </button>
      </header>

      <section className="mt-7 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div className="flex flex-col gap-3 border-b border-slate-100 p-4 sm:flex-row sm:items-end sm:justify-between sm:p-6">
          <div>
            <label
              htmlFor="filtro-resultado-acceso"
              className="mb-2 block text-xs font-bold text-slate-600"
            >
              Filtrar por resultado
            </label>
            <select
              id="filtro-resultado-acceso"
              value={resultado}
              onChange={(evento) =>
                setResultado(evento.target.value as ResultadoAcceso | "")
              }
              className="h-11 min-w-56 rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-harbor-500 focus:ring-4 focus:ring-harbor-100"
            >
              <option value="">Todos los resultados</option>
              <option value="habilitado">Habilitado</option>
              <option value="denegado">Denegado</option>
              <option value="revision_manual">Revisión manual</option>
              <option value="no_determinado">No determinado</option>
            </select>
          </div>
          <p className="text-xs text-slate-400">
            Se conservan en memoria de forma temporal hasta el límite del servicio.
          </p>
        </div>

        {error && (
          <div className="p-4 sm:px-6">
            <Alerta tipo="error">{error}</Alerta>
          </div>
        )}

        {cargando ? (
          <CargandoPanel texto="Consultando decisiones de acceso…" />
        ) : decisiones.length === 0 ? (
          <EstadoVacio
            titulo="No hay decisiones para mostrar"
            descripcion={
              resultado
                ? "No existen decisiones recientes con el resultado seleccionado."
                : "Las identificaciones procesadas por el servicio de accesos aparecerán aquí."
            }
          />
        ) : (
          <>
            <div className="hidden overflow-x-auto md:block">
              <table className="w-full text-left">
                <thead className="bg-slate-50 text-[10px] font-bold uppercase tracking-[0.16em] text-slate-400">
                  <tr>
                    <th className="px-6 py-3.5">Fecha</th>
                    <th className="px-6 py-3.5">Contenedor</th>
                    <th className="px-6 py-3.5">Lector</th>
                    <th className="px-6 py-3.5">Resultado</th>
                    <th className="px-6 py-3.5">Motivo</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {decisiones.map((decision) => (
                    <tr key={decision.decision_id} className="align-top hover:bg-slate-50/70">
                      <td className="whitespace-nowrap px-6 py-4 text-xs font-semibold text-slate-500">
                        <time dateTime={decision.fecha_decision}>
                          {formatearFecha(decision.fecha_decision)}
                        </time>
                      </td>
                      <td className="px-6 py-4">
                        <span className="block font-bold text-ink-900">
                          {decision.codigo_contenedor}
                        </span>
                        <span className="mt-1 block text-[10px] text-slate-400">
                          {decision.contenedor_id === null
                            ? "Sin registro operacional"
                            : `Contenedor #${decision.contenedor_id}`}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm font-semibold text-slate-600">
                        {decision.lector}
                      </td>
                      <td className="px-6 py-4">
                        <ResultadoAccesoBadge resultado={decision.resultado} />
                      </td>
                      <td className="max-w-md px-6 py-4 text-sm leading-5 text-slate-600">
                        {decision.motivo}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="divide-y divide-slate-100 md:hidden">
              {decisiones.map((decision) => (
                <article key={decision.decision_id} className="p-5">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-bold text-ink-900">
                        {decision.codigo_contenedor}
                      </p>
                      <p className="mt-1 text-xs font-semibold text-slate-500">
                        {decision.lector}
                      </p>
                    </div>
                    <ResultadoAccesoBadge resultado={decision.resultado} />
                  </div>
                  <p className="mt-4 text-sm leading-5 text-slate-600">
                    {decision.motivo}
                  </p>
                  <time
                    dateTime={decision.fecha_decision}
                    className="mt-3 block text-xs text-slate-400"
                  >
                    {formatearFecha(decision.fecha_decision)}
                  </time>
                </article>
              ))}
            </div>
          </>
        )}
      </section>
    </div>
  );
}
