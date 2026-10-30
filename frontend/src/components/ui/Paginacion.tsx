interface PaginacionProps {
  pagina: number;
  haySiguiente: boolean;
  cargando?: boolean;
  onCambiar: (pagina: number) => void;
}

export function Paginacion({
  pagina,
  haySiguiente,
  cargando = false,
  onCambiar,
}: PaginacionProps) {
  return (
    <nav className="flex items-center justify-between border-t border-slate-100 px-4 py-4 sm:px-6" aria-label="Paginación">
      <p className="text-xs font-semibold text-slate-500">Página {pagina + 1}</p>
      <div className="flex gap-2">
        <button
          type="button"
          disabled={pagina === 0 || cargando}
          onClick={() => onCambiar(pagina - 1)}
          className="rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-xs font-bold text-slate-600 transition hover:border-harbor-300 hover:text-harbor-700 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Anterior
        </button>
        <button
          type="button"
          disabled={!haySiguiente || cargando}
          onClick={() => onCambiar(pagina + 1)}
          className="rounded-xl bg-ink-900 px-3.5 py-2 text-xs font-bold text-white transition hover:bg-ink-700 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Siguiente
        </button>
      </div>
    </nav>
  );
}
