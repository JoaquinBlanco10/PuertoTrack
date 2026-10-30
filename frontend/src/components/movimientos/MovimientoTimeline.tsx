import type { Movimiento, TipoMovimiento } from "../../types/logistica";
import type { Usuario } from "../../types/auth";

const estilosTipo: Record<TipoMovimiento, string> = {
  entrada: "border-emerald-200 bg-emerald-50 text-emerald-700",
  traslado: "border-sky-200 bg-sky-50 text-sky-700",
  salida: "border-violet-200 bg-violet-50 text-violet-700",
};

function fecha(valor: string): string {
  return new Intl.DateTimeFormat("es-CL", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(valor));
}

function responsable(movimiento: Movimiento, usuario: Usuario): string {
  return movimiento.usuario_id === usuario.id
    ? `${usuario.nombre} (tú)`
    : `Usuario #${movimiento.usuario_id}`;
}

export function MovimientoTimeline({
  movimientos,
  usuario,
  codigosPorContenedor,
}: {
  movimientos: Movimiento[];
  usuario: Usuario;
  codigosPorContenedor: ReadonlyMap<number, string>;
}) {
  return (
    <ol className="divide-y divide-slate-100">
      {movimientos.map((movimiento) => (
        <li key={movimiento.id} className="relative px-5 py-5 sm:px-7">
          <div className="grid gap-4 sm:grid-cols-[2.5rem_1fr_auto] sm:items-start">
            <span className={`hidden h-10 w-10 place-items-center rounded-xl text-lg font-bold sm:grid ${
              movimiento.tipo ? estilosTipo[movimiento.tipo] : "border border-slate-200 bg-slate-50 text-slate-500"
            }`} aria-hidden="true">
              {movimiento.tipo === "entrada" ? "↘" : movimiento.tipo === "traslado" ? "↝" : movimiento.tipo === "salida" ? "↗" : "·"}
            </span>
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-mono text-sm font-bold tracking-wide text-ink-900">
                  {codigosPorContenedor.get(movimiento.contenedor_id) ?? `Contenedor #${movimiento.contenedor_id}`}
                </span>
                <span
                  className={`inline-flex rounded-full border px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider ${
                    movimiento.tipo
                      ? estilosTipo[movimiento.tipo]
                      : "border-slate-200 bg-slate-50 text-slate-500"
                  }`}
                >
                  {movimiento.tipo ?? "Sin clasificar"}
                </span>
                <span className="text-[10px] font-semibold text-slate-400">Movimiento #{movimiento.id}</span>
              </div>

              <div className="mt-4 grid gap-2 sm:grid-cols-[1fr_auto_1fr] sm:items-center">
                <div className="rounded-xl bg-slate-50 px-3 py-2.5">
                  <span className="block text-[9px] font-bold uppercase tracking-wider text-slate-400">Origen</span>
                  <span className="mt-1 block text-sm font-semibold text-ink-900">{movimiento.ubicacion_origen}</span>
                </div>
                <span className="px-1 text-harbor-500" aria-hidden="true">→</span>
                <div className="rounded-xl bg-harbor-50/70 px-3 py-2.5">
                  <span className="block text-[9px] font-bold uppercase tracking-wider text-harbor-600">Destino</span>
                  <span className="mt-1 block text-sm font-semibold text-ink-900">{movimiento.ubicacion_destino}</span>
                </div>
              </div>

              {movimiento.observacion && (
                <p className="mt-3 rounded-lg bg-slate-50 px-3 py-2 text-xs leading-5 text-slate-500">
                  {movimiento.observacion}
                </p>
              )}
            </div>
            <div className="text-left sm:text-right">
              <time className="block text-xs font-semibold text-slate-500" dateTime={movimiento.fecha_movimiento}>
                {fecha(movimiento.fecha_movimiento)}
              </time>
              <span className="mt-1 block text-xs text-slate-400">{responsable(movimiento, usuario)}</span>
            </div>
          </div>
        </li>
      ))}
    </ol>
  );
}
