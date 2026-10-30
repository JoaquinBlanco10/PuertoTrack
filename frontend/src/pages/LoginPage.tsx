import { type FormEvent, useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";

import { Brand } from "../components/Brand";
import { useAuth } from "../context/AuthContext";
import { ApiError } from "../lib/api";

interface LocationState {
  desde?: { pathname?: string };
}

function mensajeDeError(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 401) return "El correo o la contraseña no son correctos.";
    if (error.status === 403) return "Tu cuenta está inactiva. Contacta a un supervisor.";
    if (error.status >= 500) return "La plataforma no está disponible en este momento.";
    return error.message;
  }

  if (error instanceof TypeError) {
    return "No pudimos conectar con la API. Revisa que el backend esté en ejecución.";
  }

  return "Ocurrió un error inesperado. Inténtalo nuevamente.";
}

export function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mostrarPassword, setMostrarPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { login, autenticando, autenticado } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  if (autenticado) return <Navigate to="/" replace />;

  const enviar = async (evento: FormEvent<HTMLFormElement>) => {
    evento.preventDefault();
    setError(null);

    if (!email.trim() || !password) {
      setError("Ingresa tu correo y contraseña para continuar.");
      return;
    }

    try {
      await login(email, password);
      const state = location.state as LocationState | null;
      navigate(state?.desde?.pathname ?? "/", { replace: true });
    } catch (motivo) {
      setError(mensajeDeError(motivo));
    }
  };

  return (
    <main className="relative min-h-screen overflow-hidden bg-ink-900">
      <div className="absolute inset-0 opacity-30" aria-hidden="true">
        <div className="absolute -left-32 top-1/3 h-80 w-80 rounded-full bg-harbor-500 blur-[120px]" />
        <div className="absolute -right-24 top-0 h-96 w-96 rounded-full bg-blue-700 blur-[140px]" />
        <div className="port-grid absolute inset-0" />
      </div>

      <div className="relative mx-auto grid min-h-screen max-w-[1500px] lg:grid-cols-[1.08fr_0.92fr]">
        <section className="hidden flex-col justify-between px-12 py-12 lg:flex xl:px-20 xl:py-16">
          <Brand clara />

          <div className="max-w-2xl pb-10">
            <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-harbor-300/20 bg-harbor-300/10 px-4 py-2 text-xs font-bold uppercase tracking-[0.18em] text-harbor-200">
              <span className="h-2 w-2 animate-pulse rounded-full bg-harbor-300" />
              Plataforma operativa
            </div>
            <h1 className="max-w-xl text-5xl font-bold leading-[1.06] tracking-tight text-white xl:text-6xl">
              Control portuario,
              <span className="block text-harbor-300">claro y conectado.</span>
            </h1>
            <p className="mt-7 max-w-lg text-lg leading-8 text-slate-400">
              Una vista segura para coordinar contenedores, seguir movimientos y mantener la trazabilidad de cada operación.
            </p>

            <div className="mt-12 grid max-w-xl grid-cols-3 gap-3">
              {[
                ["01", "Acceso seguro"],
                ["02", "Roles definidos"],
                ["03", "Trazabilidad"],
              ].map(([numero, texto]) => (
                <div key={numero} className="border-l border-white/15 pl-4">
                  <span className="block text-xs font-bold text-signal">{numero}</span>
                  <span className="mt-1 block text-sm font-semibold text-slate-300">{texto}</span>
                </div>
              ))}
            </div>
          </div>

          <p className="text-xs text-slate-600">PuertoTrack · Gestión logística portuaria</p>
        </section>

        <section className="flex min-h-screen items-center justify-center bg-slate-50 px-5 py-10 sm:px-10 lg:rounded-l-[2.5rem] lg:px-14 xl:px-24">
          <div className="w-full max-w-md">
            <div className="mb-10 lg:hidden">
              <Brand />
            </div>

            <p className="text-xs font-bold uppercase tracking-[0.2em] text-harbor-600">Acceso al sistema</p>
            <h2 className="mt-3 text-3xl font-bold tracking-tight text-ink-900 sm:text-4xl">Bienvenido de vuelta</h2>
            <p className="mt-3 text-sm leading-6 text-slate-500">Ingresa con las credenciales asignadas por tu organización.</p>

            <form className="mt-9 space-y-5" onSubmit={enviar} noValidate>
              <div>
                <label htmlFor="email" className="mb-2 block text-sm font-bold text-slate-700">Correo electrónico</label>
                <div className="relative">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" aria-hidden="true">
                    <path d="M4 6h16v12H4z" /><path d="m4 7 8 6 8-6" />
                  </svg>
                  <input
                    id="email"
                    name="email"
                    type="email"
                    autoComplete="username"
                    required
                    value={email}
                    onChange={(evento) => setEmail(evento.target.value)}
                    placeholder="nombre@empresa.cl"
                    className="h-14 w-full rounded-xl border border-slate-200 bg-white py-3.5 pl-12 pr-4 text-sm text-ink-900 outline-none transition placeholder:text-slate-400 hover:border-slate-300 focus:border-harbor-500 focus:ring-4 focus:ring-harbor-100"
                  />
                </div>
              </div>

              <div>
                <label htmlFor="password" className="mb-2 block text-sm font-bold text-slate-700">Contraseña</label>
                <div className="relative">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" aria-hidden="true">
                    <rect x="5" y="10" width="14" height="10" rx="2" /><path d="M8 10V7a4 4 0 0 1 8 0v3" />
                  </svg>
                  <input
                    id="password"
                    name="password"
                    type={mostrarPassword ? "text" : "password"}
                    autoComplete="current-password"
                    required
                    value={password}
                    onChange={(evento) => setPassword(evento.target.value)}
                    placeholder="Ingresa tu contraseña"
                    className="h-14 w-full rounded-xl border border-slate-200 bg-white py-3.5 pl-12 pr-12 text-sm text-ink-900 outline-none transition placeholder:text-slate-400 hover:border-slate-300 focus:border-harbor-500 focus:ring-4 focus:ring-harbor-100"
                  />
                  <button
                    type="button"
                    onClick={() => setMostrarPassword((valor) => !valor)}
                    className="absolute right-3 top-1/2 grid h-9 w-9 -translate-y-1/2 place-items-center rounded-lg text-slate-400 transition hover:bg-slate-100 hover:text-slate-600 focus:outline-none focus:ring-2 focus:ring-harbor-400"
                    aria-label={mostrarPassword ? "Ocultar contraseña" : "Mostrar contraseña"}
                  >
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5" aria-hidden="true">
                      {mostrarPassword ? <><path d="M3 3l18 18" /><path d="M10.6 10.7a2 2 0 0 0 2.7 2.7M9.9 4.2A10.7 10.7 0 0 1 12 4c5.5 0 9 5 9 5a15.4 15.4 0 0 1-2.1 2.5M6.6 6.7C4.3 8.2 3 10 3 10s3.5 5 9 5c.7 0 1.3-.1 1.9-.2" /></> : <><path d="M3 12s3.5-5 9-5 9 5 9 5-3.5 5-9 5-9-5-9-5Z" /><circle cx="12" cy="12" r="2" /></>}
                    </svg>
                  </button>
                </div>
              </div>

              {error && (
                <div role="alert" className="flex gap-3 rounded-xl border border-rose-200 bg-rose-50 p-3.5 text-sm leading-5 text-rose-700">
                  <span className="mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded-full bg-rose-100 text-xs font-bold">!</span>
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={autenticando}
                className="flex h-14 w-full items-center justify-center gap-2 rounded-xl bg-ink-900 px-5 py-3.5 text-sm font-bold text-white shadow-panel transition hover:bg-ink-700 focus:outline-none focus:ring-4 focus:ring-harbor-200 disabled:cursor-wait disabled:opacity-70"
              >
                {autenticando ? (
                  <>
                    <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                    Verificando acceso…
                  </>
                ) : (
                  <>
                    Ingresar a PuertoTrack
                    <span aria-hidden="true">→</span>
                  </>
                )}
              </button>
            </form>

            <div className="mt-7 flex items-start gap-3 rounded-xl bg-slate-100 p-4 text-xs leading-5 text-slate-500">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="mt-0.5 h-4 w-4 shrink-0 text-harbor-600" aria-hidden="true">
                <circle cx="12" cy="12" r="9" /><path d="M12 11v5M12 8h.01" />
              </svg>
              Por seguridad, esta sesión se cerrará al recargar o cerrar la pestaña.
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
