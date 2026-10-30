import {
  type PropsWithChildren,
  useEffect,
  useId,
  useRef,
} from "react";

interface ModalProps extends PropsWithChildren {
  abierto: boolean;
  titulo: string;
  descripcion?: string;
  onCerrar: () => void;
  bloqueado?: boolean;
  ancho?: "normal" | "amplio";
}

const SELECTOR_ENFOCABLE = [
  "a[href]",
  "button:not([disabled])",
  "input:not([disabled])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  '[tabindex]:not([tabindex="-1"])',
].join(",");

export function calcularDestinoTab(
  cantidad: number,
  indiceActivo: number,
  retroceder: boolean,
): number | null {
  if (cantidad <= 0) return null;
  if (indiceActivo < 0) return retroceder ? cantidad - 1 : 0;
  if (retroceder && indiceActivo === 0) return cantidad - 1;
  if (!retroceder && indiceActivo === cantidad - 1) return 0;
  return null;
}

function elementosEnfocables(contenedor: HTMLElement): HTMLElement[] {
  return Array.from(
    contenedor.querySelectorAll<HTMLElement>(SELECTOR_ENFOCABLE),
  ).filter(
    (elemento) =>
      elemento.getAttribute("aria-hidden") !== "true" &&
      elemento.getClientRects().length > 0,
  );
}

export function Modal({
  abierto,
  titulo,
  descripcion,
  onCerrar,
  bloqueado = false,
  ancho = "normal",
  children,
}: ModalProps) {
  const reactId = useId().replaceAll(":", "");
  const tituloId = `modal-titulo-${reactId}`;
  const descripcionId = `modal-descripcion-${reactId}`;
  const dialogoRef = useRef<HTMLElement>(null);
  const onCerrarRef = useRef(onCerrar);
  const bloqueadoRef = useRef(bloqueado);
  onCerrarRef.current = onCerrar;
  bloqueadoRef.current = bloqueado;

  useEffect(() => {
    if (!abierto) return;
    const focoAnterior =
      document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;
    const overflowAnterior = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const enfocarInicial = window.requestAnimationFrame(() => {
      const dialogo = dialogoRef.current;
      if (!dialogo) return;
      const automatico = dialogo.querySelector<HTMLElement>("[autofocus]");
      const primero = elementosEnfocables(dialogo)[0];
      (automatico ?? primero ?? dialogo).focus();
    });

    const manejarTeclado = (evento: KeyboardEvent) => {
      const dialogo = dialogoRef.current;
      if (!dialogo) return;
      if (evento.key === "Escape") {
        evento.preventDefault();
        if (!bloqueadoRef.current) onCerrarRef.current();
        return;
      }
      if (evento.key !== "Tab") return;

      const enfocables = elementosEnfocables(dialogo);
      if (enfocables.length === 0) {
        evento.preventDefault();
        dialogo.focus();
        return;
      }
      const indiceActivo = enfocables.indexOf(
        document.activeElement as HTMLElement,
      );
      const destino = calcularDestinoTab(
        enfocables.length,
        indiceActivo,
        evento.shiftKey,
      );
      if (destino !== null) {
        evento.preventDefault();
        enfocables[destino]?.focus();
      }
    };
    document.addEventListener("keydown", manejarTeclado);

    return () => {
      window.cancelAnimationFrame(enfocarInicial);
      document.body.style.overflow = overflowAnterior;
      document.removeEventListener("keydown", manejarTeclado);
      if (focoAnterior?.isConnected) {
        window.requestAnimationFrame(() => focoAnterior.focus());
      }
    };
  }, [abierto]);

  if (!abierto) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center p-0 sm:items-center sm:p-5">
      <button
        type="button"
        tabIndex={-1}
        aria-label="Cerrar ventana"
        className="absolute inset-0 bg-ink-900/65 backdrop-blur-sm"
        onClick={bloqueado ? undefined : onCerrar}
      />
      <section
        ref={dialogoRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={tituloId}
        aria-describedby={descripcion ? descripcionId : undefined}
        tabIndex={-1}
        className={`relative max-h-[92vh] w-full overflow-y-auto rounded-t-3xl bg-white shadow-2xl outline-none sm:rounded-3xl ${
          ancho === "amplio" ? "max-w-3xl" : "max-w-xl"
        }`}
      >
        <header className="sticky top-0 z-10 flex items-start justify-between gap-4 border-b border-slate-100 bg-white/95 px-6 py-5 backdrop-blur sm:px-7">
          <div>
            <h2 id={tituloId} className="text-xl font-bold tracking-tight text-ink-900">
              {titulo}
            </h2>
            {descripcion && <p id={descripcionId} className="mt-1 text-sm text-slate-500">{descripcion}</p>}
          </div>
          <button
            type="button"
            onClick={onCerrar}
            disabled={bloqueado}
            className="grid h-9 w-9 shrink-0 place-items-center rounded-xl text-slate-400 transition hover:bg-slate-100 hover:text-slate-700 focus:outline-none focus:ring-2 focus:ring-harbor-400 disabled:opacity-40"
            aria-label="Cerrar"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-5 w-5" aria-hidden="true">
              <path d="m6 6 12 12M18 6 6 18" />
            </svg>
          </button>
        </header>
        <div className="p-6 sm:p-7">{children}</div>
      </section>
    </div>
  );
}
