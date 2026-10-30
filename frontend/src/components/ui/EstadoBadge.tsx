const estilos: Record<string, string> = {
  disponible: "border-sky-200 bg-sky-50 text-sky-700",
  en_patio: "border-emerald-200 bg-emerald-50 text-emerald-700",
  en_transito: "border-violet-200 bg-violet-50 text-violet-700",
  cargado: "border-amber-200 bg-amber-50 text-amber-700",
  descargado: "border-cyan-200 bg-cyan-50 text-cyan-700",
  mantenimiento: "border-rose-200 bg-rose-50 text-rose-700",
};

export function textoEstado(estado: string): string {
  return estado.replaceAll("_", " ");
}

export function EstadoBadge({ estado }: { estado: string }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-bold capitalize ${
        estilos[estado] ?? "border-slate-200 bg-slate-50 text-slate-600"
      }`}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current opacity-70" />
      {textoEstado(estado)}
    </span>
  );
}
