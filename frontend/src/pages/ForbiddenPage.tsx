import { Link } from "react-router-dom";

export function ForbiddenPage() {
  return (
    <div className="mx-auto flex min-h-[60vh] max-w-xl items-center justify-center">
      <div className="w-full rounded-3xl border border-slate-200 bg-white p-8 text-center shadow-panel sm:p-12">
        <span className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-amber-50 text-2xl font-bold text-amber-600">!</span>
        <p className="mt-6 text-xs font-bold uppercase tracking-[0.2em] text-amber-600">Acceso restringido</p>
        <h1 className="mt-3 text-2xl font-bold text-ink-900">No tienes permisos para esta sección</h1>
        <p className="mt-3 text-sm leading-6 text-slate-500">Tu sesión es válida, pero el rol asignado no permite acceder a este recurso.</p>
        <Link to="/" className="mt-7 inline-flex rounded-xl bg-ink-900 px-5 py-3 text-sm font-bold text-white transition hover:bg-ink-700 focus:outline-none focus:ring-4 focus:ring-harbor-200">Volver al panel</Link>
      </div>
    </div>
  );
}
