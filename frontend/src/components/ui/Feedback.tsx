import type { PropsWithChildren } from "react";

export function Alerta({
  tipo,
  children,
}: PropsWithChildren<{ tipo: "error" | "exito" | "info" }>) {
  const clases = {
    error: "border-rose-200 bg-rose-50 text-rose-700",
    exito: "border-emerald-200 bg-emerald-50 text-emerald-700",
    info: "border-sky-200 bg-sky-50 text-sky-700",
  }[tipo];

  return (
    <div role={tipo === "error" ? "alert" : "status"} className={`rounded-xl border px-4 py-3 text-sm leading-5 ${clases}`}>
      {children}
    </div>
  );
}

export function CargandoPanel({ texto = "Cargando datos…" }: { texto?: string }) {
  return (
    <div className="grid min-h-72 place-items-center px-6 py-12">
      <div className="text-center">
        <span className="mx-auto block h-8 w-8 animate-spin rounded-full border-2 border-harbor-100 border-t-harbor-600" />
        <p className="mt-4 text-sm font-semibold text-slate-500">{texto}</p>
      </div>
    </div>
  );
}

export function EstadoVacio({
  titulo,
  descripcion,
}: {
  titulo: string;
  descripcion: string;
}) {
  return (
    <div className="grid min-h-72 place-items-center px-6 py-12 text-center">
      <div className="max-w-sm">
        <span className="mx-auto grid h-12 w-12 place-items-center rounded-2xl bg-slate-100 text-xl text-slate-400" aria-hidden="true">◇</span>
        <h3 className="mt-4 font-bold text-ink-900">{titulo}</h3>
        <p className="mt-2 text-sm leading-6 text-slate-500">{descripcion}</p>
      </div>
    </div>
  );
}
