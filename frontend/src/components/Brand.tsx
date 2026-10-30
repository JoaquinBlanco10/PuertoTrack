interface BrandProps {
  compacta?: boolean;
  clara?: boolean;
}

export function Brand({ compacta = false, clara = false }: BrandProps) {
  return (
    <div className="flex items-center gap-3" aria-label="PuertoTrack">
      <span className="relative grid h-11 w-11 shrink-0 place-items-center overflow-hidden rounded-2xl bg-harbor-500 text-white shadow-glow">
        <svg
          viewBox="0 0 24 24"
          className="h-6 w-6"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          aria-hidden="true"
        >
          <path d="M4 15.5 12 19l8-3.5M5.5 13V7.5L12 5l6.5 2.5V13L12 16l-6.5-3Z" />
          <path d="M12 5v11M8.5 8.8 12 10l3.5-1.2M3 19.2c2 .2 2.6 1.3 4.5 1.3s2.5-1.3 4.5-1.3 2.6 1.3 4.5 1.3 2.5-1.1 4.5-1.3" />
        </svg>
        <span className="absolute inset-x-1 bottom-0 h-0.5 bg-signal" />
      </span>
      {!compacta && (
        <span>
          <span
            className={`block text-lg font-bold tracking-tight ${clara ? "text-white" : "text-ink-900"}`}
          >
            Puerto<span className="text-harbor-400">Track</span>
          </span>
          <span
            className={`block text-[10px] font-semibold uppercase tracking-[0.22em] ${clara ? "text-slate-400" : "text-slate-500"}`}
          >
            Control logístico
          </span>
        </span>
      )}
    </div>
  );
}
