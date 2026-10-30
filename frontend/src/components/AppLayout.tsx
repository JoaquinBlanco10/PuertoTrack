import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import { etiquetaRol } from "../lib/authUi";
import { Brand } from "./Brand";

const IconoPanel = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5" aria-hidden="true">
    <path d="M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h6v6h-6z" />
  </svg>
);

const IconoCaja = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5" aria-hidden="true">
    <path d="m4 7 8-3 8 3-8 3-8-3Z" /><path d="M4 7v10l8 3 8-3V7M12 10v10" />
  </svg>
);

const IconoRuta = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5" aria-hidden="true">
    <circle cx="6" cy="18" r="2" /><circle cx="18" cy="6" r="2" /><path d="M8 18h3a3 3 0 0 0 3-3V9a3 3 0 0 1 3-3" />
  </svg>
);

const IconoUbicacion = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5" aria-hidden="true">
    <path d="M12 21s6-5.1 6-11a6 6 0 1 0-12 0c0 5.9 6 11 6 11Z" /><circle cx="12" cy="10" r="2" />
  </svg>
);

const IconoAuditoria = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5" aria-hidden="true">
    <path d="M9 4h6l1 2h3v14H5V6h3l1-2Z" /><path d="m9 13 2 2 4-5" />
  </svg>
);

const IconoAcceso = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5" aria-hidden="true">
    <path d="M4 20V7l8-3 8 3v13M8 20v-7h8v7M2 20h20" />
    <path d="m9 9 2 2 4-4" />
  </svg>
);

const IconoSalir = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="h-5 w-5" aria-hidden="true">
    <path d="M10 5H5v14h5M14 8l4 4-4 4M8 12h10" />
  </svg>
);

export function AppLayout() {
  const [menuAbierto, setMenuAbierto] = useState(false);
  const { usuario, logout } = useAuth();

  if (!usuario) return null;

  const iniciales = usuario.nombre
    .split(" ")
    .slice(0, 2)
    .map((parte) => parte[0])
    .join("")
    .toUpperCase();

  const cerrarMenu = () => setMenuAbierto(false);

  const sidebar = (
    <div className="flex h-full flex-col bg-ink-900 text-slate-300">
      <div className="flex h-24 items-center border-b border-white/10 px-6">
        <Brand clara />
      </div>

      <nav className="flex-1 px-4 py-7" aria-label="Navegación principal">
        <p className="mb-3 px-3 text-[10px] font-bold uppercase tracking-[0.2em] text-slate-500">
          Operaciones
        </p>
        <NavLink
          to="/"
          end
          onClick={cerrarMenu}
          className={({ isActive }) =>
            `flex items-center gap-3 rounded-xl px-3 py-3 text-sm font-semibold transition ${
              isActive
                ? "bg-harbor-500 text-white shadow-glow"
                : "text-slate-300 hover:bg-white/5 hover:text-white"
            }`
          }
        >
          <IconoPanel />
          Panel general
        </NavLink>

        <div className="mt-2 space-y-1">
          {[
            { nombre: "Contenedores", ruta: "/contenedores", icono: <IconoCaja /> },
            { nombre: "Movimientos", ruta: "/movimientos", icono: <IconoRuta /> },
            { nombre: "Ubicaciones", ruta: "/ubicaciones", icono: <IconoUbicacion /> },
          ].map((item) => (
            <NavLink
              key={item.nombre}
              to={item.ruta}
              onClick={cerrarMenu}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-xl px-3 py-3 text-sm font-semibold transition ${
                  isActive
                    ? "bg-harbor-500 text-white shadow-glow"
                    : "text-slate-300 hover:bg-white/5 hover:text-white"
                }`
              }
            >
              {item.icono}
              <span>{item.nombre}</span>
            </NavLink>
          ))}
          {usuario.rol === "supervisor" && (
            <>
              <NavLink
                to="/accesos"
                onClick={cerrarMenu}
                className={({ isActive }) =>
                  `flex items-center gap-3 rounded-xl px-3 py-3 text-sm font-semibold transition ${
                    isActive
                      ? "bg-harbor-500 text-white shadow-glow"
                      : "text-slate-300 hover:bg-white/5 hover:text-white"
                  }`
                }
              >
                <IconoAcceso />
                <span>Accesos</span>
              </NavLink>
              <NavLink
                to="/auditoria"
                onClick={cerrarMenu}
                className={({ isActive }) =>
                  `flex items-center gap-3 rounded-xl px-3 py-3 text-sm font-semibold transition ${
                    isActive
                      ? "bg-harbor-500 text-white shadow-glow"
                      : "text-slate-300 hover:bg-white/5 hover:text-white"
                  }`
                }
              >
                <IconoAuditoria />
                <span>Auditoría</span>
              </NavLink>
            </>
          )}
        </div>
      </nav>

      <div className="border-t border-white/10 p-4">
        <div className="mb-3 flex items-center gap-3 rounded-xl bg-white/[0.04] p-3">
          <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-harbor-400/15 text-xs font-bold text-harbor-300">
            {iniciales}
          </span>
          <span className="min-w-0">
            <span className="block truncate text-sm font-semibold text-white">{usuario.nombre}</span>
            <span className="block truncate text-xs text-slate-500">
              {etiquetaRol(usuario.rol)}
            </span>
          </span>
        </div>
        <button
          type="button"
          onClick={logout}
          className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-semibold text-slate-400 transition hover:bg-rose-500/10 hover:text-rose-300 focus:outline-none focus:ring-2 focus:ring-rose-300/50"
        >
          <IconoSalir />
          Cerrar sesión
        </button>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-slate-100 text-slate-800">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-72 lg:block">{sidebar}</aside>

      {menuAbierto && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <button
            type="button"
            aria-label="Cerrar menú"
            className="absolute inset-0 bg-ink-900/70 backdrop-blur-sm"
            onClick={cerrarMenu}
          />
          <aside className="relative h-full w-[min(82vw,18rem)] shadow-2xl">{sidebar}</aside>
        </div>
      )}

      <div className="lg:pl-72">
        <header className="sticky top-0 z-20 flex h-20 items-center justify-between border-b border-slate-200/80 bg-white/90 px-4 backdrop-blur-xl sm:px-7 lg:px-10">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setMenuAbierto(true)}
              className="grid h-10 w-10 place-items-center rounded-xl border border-slate-200 text-slate-600 transition hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-harbor-400 lg:hidden"
              aria-label="Abrir menú"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-5 w-5" aria-hidden="true">
                <path d="M4 7h16M4 12h16M4 17h16" />
              </svg>
            </button>
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.16em] text-harbor-600">Centro de control</p>
              <p className="text-sm font-medium text-slate-500">Operación portuaria en línea</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <span className="hidden rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-bold text-emerald-700 sm:inline-flex sm:items-center sm:gap-2">
              <span className="h-2 w-2 rounded-full bg-emerald-500" />
              Sesión activa
            </span>
            <span className="grid h-10 w-10 place-items-center rounded-xl bg-ink-900 text-xs font-bold text-white">
              {iniciales}
            </span>
          </div>
        </header>

        <main className="min-h-[calc(100vh-5rem)] p-4 sm:p-7 lg:p-10">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
