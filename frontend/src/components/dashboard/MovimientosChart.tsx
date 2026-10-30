import {
  etiquetaDia,
  maximoMovimientosDiarios,
  totalMovimientosDia,
} from "../../lib/dashboardUi";
import type { MovimientoDiarioDashboard } from "../../types/dashboard";
import { EstadoVacio } from "../ui/Feedback";

const series = [
  { campo: "entrada", etiqueta: "Entradas", color: "bg-emerald-500" },
  { campo: "traslado", etiqueta: "Traslados", color: "bg-harbor-500" },
  { campo: "salida", etiqueta: "Salidas", color: "bg-violet-500" },
] as const;

export function MovimientosChart({
  datos,
}: {
  datos: MovimientoDiarioDashboard[];
}) {
  const maximo = maximoMovimientosDiarios(datos);
  const total = datos.reduce(
    (acumulado, dia) => acumulado + totalMovimientosDia(dia),
    0,
  );
  const alturaGrafico = total === 0
    ? "h-20 sm:h-24"
    : "h-28 sm:h-36 lg:h-40";

  return (
    <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <header className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-100 px-5 py-5 sm:px-6">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-harbor-600">
            Actividad reciente
          </p>
          <h2 className="mt-1 text-lg font-bold text-ink-900">
            Movimientos de los últimos 7 días
          </h2>
        </div>
        <div className="flex flex-wrap gap-3" aria-label="Leyenda del gráfico">
          {series.map((serie) => (
            <span key={serie.campo} className="flex items-center gap-1.5 text-[11px] font-semibold text-slate-500">
              <span className={`h-2.5 w-2.5 rounded-sm ${serie.color}`} />
              {serie.etiqueta}
            </span>
          ))}
        </div>
      </header>

      {datos.length === 0 ? (
        <EstadoVacio
          titulo="Sin período disponible"
          descripcion="El resumen no incluyó datos diarios para representar."
        />
      ) : (
        <div className="overflow-x-auto px-4 pb-4 pt-4 sm:px-6">
          <div
            className="grid min-w-[31rem] grid-cols-7 gap-2 sm:gap-3"
            role="img"
            aria-label={`Gráfico de movimientos por tipo durante siete días. Total: ${total}.`}
          >
            {datos.map((dia) => (
              <div key={dia.fecha} className="min-w-0 text-center">
                <div className={`relative flex items-end justify-center gap-1 overflow-hidden rounded-xl border border-slate-100 bg-slate-50/80 px-1.5 pt-2 ${alturaGrafico}`}>
                  <span className="absolute inset-x-0 bottom-1/4 border-t border-dashed border-slate-200" />
                  <span className="absolute inset-x-0 bottom-2/4 border-t border-dashed border-slate-200" />
                  <span className="absolute inset-x-0 bottom-3/4 border-t border-dashed border-slate-200" />
                  {series.map((serie) => {
                    const cantidad = dia[serie.campo];
                    const altura = maximo > 0 ? (cantidad / maximo) * 78 : 0;
                    return (
                      <span
                        key={serie.campo}
                        className="relative z-10 flex h-full min-w-0 flex-1 flex-col items-center justify-end"
                        aria-label={`${serie.etiqueta}: ${cantidad}`}
                        title={`${serie.etiqueta}: ${cantidad}`}
                      >
                        <span className="mb-1 text-[9px] font-bold tabular-nums text-slate-600">
                          {cantidad}
                        </span>
                        <span
                          className={`w-full max-w-4 rounded-t-sm ${serie.color} transition-all`}
                          style={{ height: cantidad > 0 ? `${Math.max(altura, 7)}%` : "2px" }}
                        />
                      </span>
                    );
                  })}
                </div>
                <time dateTime={dia.fecha} className="mt-3 block text-[11px] font-bold capitalize text-slate-500">
                  {etiquetaDia(dia.fecha)}
                </time>
                <span className="mt-0.5 block text-[9px] font-semibold text-slate-400">
                  Total: {totalMovimientosDia(dia)}
                </span>
              </div>
            ))}
          </div>
          <table className="sr-only">
            <caption>Movimientos diarios por tipo</caption>
            <thead>
              <tr>
                <th>Fecha</th>
                <th>Entradas</th>
                <th>Traslados</th>
                <th>Salidas</th>
              </tr>
            </thead>
            <tbody>
              {datos.map((dia) => (
                <tr key={`accesible-${dia.fecha}`}>
                  <th>{dia.fecha}</th>
                  <td>{dia.entrada}</td>
                  <td>{dia.traslado}</td>
                  <td>{dia.salida}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {total === 0 && (
            <p className="mt-5 text-center text-sm text-slate-500">
              No se registraron movimientos durante este período.
            </p>
          )}
        </div>
      )}
    </section>
  );
}
