import type { ResultadoAcceso } from "../../types/accesos";

const presentacion: Record<
  ResultadoAcceso,
  { etiqueta: string; clases: string }
> = {
  habilitado: {
    etiqueta: "Habilitado",
    clases: "border-emerald-200 bg-emerald-50 text-emerald-700",
  },
  denegado: {
    etiqueta: "Denegado",
    clases: "border-rose-200 bg-rose-50 text-rose-700",
  },
  revision_manual: {
    etiqueta: "Revisión manual",
    clases: "border-amber-200 bg-amber-50 text-amber-700",
  },
  no_determinado: {
    etiqueta: "No determinado",
    clases: "border-slate-200 bg-slate-50 text-slate-600",
  },
};

export function ResultadoAccesoBadge({
  resultado,
}: {
  resultado: ResultadoAcceso;
}) {
  const vista = presentacion[resultado];
  return (
    <span
      className={`inline-flex rounded-full border px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide ${vista.clases}`}
    >
      {vista.etiqueta}
    </span>
  );
}
