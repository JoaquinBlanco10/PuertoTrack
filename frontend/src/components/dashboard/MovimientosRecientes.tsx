import type { MovimientoRecienteDashboard } from "../../types/dashboard";
import { formatearInstanteUtc } from "../../lib/dashboardUi";
import { EstadoVacio } from "../ui/Feedback";

const estilosTipo: Record<string, string> = {
  entrada: "border-emerald-200 bg-emerald-50 text-emerald-700",
  traslado: "border-sky-200 bg-sky-50 text-sky-700",
  salida: "border-violet-200 bg-violet-50 text-violet-700",
};

export function MovimientosRecientes({
  movimientos,
}: {
  movimientos: MovimientoRecienteDashboard[];
}) {
  return (
    <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <header className="border-b border-slate-100 px-5 py-5 sm:px-6">
        <p className="text-xs font-bold uppercase tracking-[0.16em] text-harbor-600">
          Trazabilidad
        </p>
        <h2 className="mt-1 text-lg font-bold text-ink-900">Últimos movimientos</h2>
      </header>

      {movimientos.length === 0 ? (
        <EstadoVacio
          titulo="Todavía no hay movimientos"
          descripcion="Las entradas, traslados y salidas recientes aparecerán aquí."
        />
      ) : (
        <ol className="divide-y divide-slate-100">
          {movimientos.map((movimiento) => (
            <li key={movimiento.id} className="px-5 py-4 sm:px-6">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-sm font-bold tracking-wide text-ink-900">
                      {movimiento.contenedor_codigo}
                    </span>
                    <span className={`rounded-full border px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider ${movimiento.tipo ? estilosTipo[movimiento.tipo] : "border-slate-200 bg-slate-50 text-slate-500"}`}>
                      {movimiento.tipo ?? "Sin clasificar"}
                    </span>
                  </div>
                  <p className="mt-2 text-xs leading-5 text-slate-500">
                    <span className="font-semibold text-slate-700">{movimiento.ubicacion_origen}</span>
                    <span className="mx-2 text-harbor-500" aria-hidden="true">→</span>
                    <span className="font-semibold text-slate-700">{movimiento.ubicacion_destino}</span>
                  </p>
                </div>
                <div className="text-left sm:text-right">
                  <time dateTime={movimiento.fecha_movimiento} className="block text-xs font-semibold text-slate-500">
                    {formatearInstanteUtc(movimiento.fecha_movimiento)}
                  </time>
                  <span className="mt-1 block text-[11px] text-slate-400">
                    {movimiento.usuario_nombre}
                  </span>
                </div>
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
