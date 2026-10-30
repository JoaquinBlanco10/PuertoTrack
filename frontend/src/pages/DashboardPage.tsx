import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { MovimientosChart } from "../components/dashboard/MovimientosChart";
import { MovimientosRecientes } from "../components/dashboard/MovimientosRecientes";
import { Alerta, CargandoPanel } from "../components/ui/Feedback";
import { useAuth } from "../context/AuthContext";
import { etiquetaRol } from "../lib/authUi";
import { obtenerResumenDashboard } from "../lib/dashboardApi";
import {
  etiquetaFechaPeriodo,
  formatearInstanteUtc,
  rutaIndicadorContenedores,
} from "../lib/dashboardUi";
import { esCancelacion, mensajeErrorApi } from "../lib/errores";
import type { ResumenDashboard } from "../types/dashboard";

const tarjetas = [
  {
    campo: "dentro_puerto",
    titulo: "Dentro del puerto",
    descripcion: "Ubicación interna confirmada",
    color: "bg-emerald-50 text-emerald-700 ring-emerald-100",
    icono: "↘",
  },
  {
    campo: "fuera_puerto",
    titulo: "Fuera del puerto",
    descripcion: "Ubicación externa confirmada",
    color: "bg-violet-50 text-violet-700 ring-violet-100",
    icono: "↗",
  },
  {
    campo: "presencia_sin_confirmar",
    titulo: "Sin confirmar",
    descripcion: "Sin ubicación catalogada",
    color: "bg-amber-50 text-amber-700 ring-amber-100",
    icono: "?",
  },
  {
    campo: "inconsistentes",
    titulo: "Inconsistencias",
    descripcion: "Estado y ubicación no coinciden",
    color: "bg-rose-50 text-rose-700 ring-rose-100",
    icono: "!",
  },
] as const;

export function DashboardPage() {
  const { usuario, ejecutarAutenticado } = useAuth();
  const [resumen, setResumen] = useState<ResumenDashboard | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const cargar = useCallback(
    async (signal?: AbortSignal) => {
      setCargando(true);
      setError(null);
      try {
        const datos = await ejecutarAutenticado((token) =>
          obtenerResumenDashboard(token, signal),
        );
        setResumen(datos);
      } catch (motivo) {
        if (!esCancelacion(motivo)) {
          setError(
            mensajeErrorApi(
              motivo,
              "No fue posible cargar el resumen operativo.",
            ),
          );
        }
      } finally {
        if (!signal?.aborted) setCargando(false);
      }
    },
    [ejecutarAutenticado],
  );

  useEffect(() => {
    const controller = new AbortController();
    void cargar(controller.signal);
    return () => controller.abort();
  }, [cargar]);

  if (!usuario) return null;

  if (cargando && !resumen) {
    return (
      <div className="mx-auto max-w-7xl overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <CargandoPanel texto="Preparando el resumen operativo…" />
      </div>
    );
  }

  if (!resumen) {
    return (
      <div className="mx-auto max-w-3xl">
        <Alerta tipo="error">
          {error ?? "No fue posible cargar el dashboard."}
        </Alerta>
        <button
          type="button"
          onClick={() => void cargar()}
          className="mt-4 rounded-xl bg-ink-900 px-5 py-3 text-sm font-bold text-white"
        >
          Reintentar
        </button>
      </div>
    );
  }

  const totalContenedores =
    resumen.contenedores.dentro_puerto +
    resumen.contenedores.fuera_puerto +
    resumen.contenedores.presencia_sin_confirmar;
  const hayAlertas =
    resumen.contenedores.inconsistentes > 0 ||
    resumen.contenedores.presencia_sin_confirmar > 0;

  return (
    <div className="mx-auto max-w-7xl">
      <section className="relative overflow-hidden rounded-3xl bg-ink-900 px-6 py-7 text-white shadow-panel sm:px-9 sm:py-9">
        <div className="port-grid absolute inset-0 opacity-70" aria-hidden="true" />
        <div className="absolute -right-16 -top-20 h-72 w-72 rounded-full border-[45px] border-harbor-500/10" aria-hidden="true" />
        <div className="relative flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-harbor-300">
              Resumen operativo
            </p>
            <h1 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">
              Hola, {etiquetaRol(usuario.rol)}.
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-400">
              Visión consolidada de inventario, actividad y alertas de PuertoTrack.
            </p>
          </div>
          <div className="flex flex-col items-start gap-3 sm:flex-row sm:items-center">
            <p className="text-xs text-slate-400">
              Actualizado{" "}
              <time dateTime={resumen.generado_en}>
                {formatearInstanteUtc(resumen.generado_en)}
              </time>
            </p>
            <button
              type="button"
              onClick={() => void cargar()}
              disabled={cargando}
              className="rounded-xl border border-white/15 bg-white/10 px-4 py-2.5 text-xs font-bold text-white transition hover:bg-white/15 focus:outline-none focus:ring-2 focus:ring-harbor-300 disabled:cursor-wait disabled:opacity-60"
            >
              {cargando ? "Actualizando…" : "Actualizar datos"}
            </button>
          </div>
        </div>
      </section>

      {error && (
        <div className="mt-5">
          <Alerta tipo="error">{error}</Alerta>
        </div>
      )}

      <section
        className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4"
        aria-label={`Indicadores de ${totalContenedores} contenedores`}
      >
        {tarjetas.map((tarjeta) => (
          <Link
            key={tarjeta.campo}
            to={rutaIndicadorContenedores(tarjeta.campo)}
            aria-label={`${tarjeta.titulo}: ${resumen.contenedores[tarjeta.campo]}. Ver contenedores filtrados.`}
            className="group rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:border-harbor-200 hover:shadow-panel focus:outline-none focus:ring-4 focus:ring-harbor-100"
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-xs font-bold uppercase tracking-wider text-slate-400">
                  {tarjeta.titulo}
                </p>
                <p className="mt-3 text-3xl font-bold tracking-tight text-ink-900">
                  {resumen.contenedores[tarjeta.campo]}
                </p>
              </div>
              <span
                className={`grid h-10 w-10 place-items-center rounded-xl text-lg font-bold ring-1 ${tarjeta.color}`}
                aria-hidden="true"
              >
                {tarjeta.icono}
              </span>
            </div>
            <div className="mt-3 flex items-center justify-between gap-3">
              <p className="text-xs text-slate-500">{tarjeta.descripcion}</p>
              <span className="text-sm font-bold text-harbor-600 opacity-0 transition group-hover:opacity-100 group-focus:opacity-100" aria-hidden="true">→</span>
            </div>
          </Link>
        ))}
      </section>

      {!hayAlertas ? (
        <section className="mt-6 flex items-center gap-3 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3" aria-label="Estado operacional sin alertas">
          <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-emerald-100 text-sm font-bold text-emerald-700" aria-hidden="true">✓</span>
          <div>
            <p className="text-sm font-bold text-emerald-950">Operación sin alertas</p>
            <p className="text-xs text-emerald-700">Todos los contenedores tienen ubicación confirmada y coherente con su estado.</p>
          </div>
        </section>
      ) : (
        <section
          className="mt-6 grid gap-4 lg:grid-cols-2"
          aria-label="Alertas operativas"
        >
          {resumen.contenedores.inconsistentes > 0 && (
          <article className="rounded-2xl border border-rose-200 bg-rose-50 p-5">
            <p className="text-xs font-bold uppercase tracking-wider text-rose-700">
              Revisión prioritaria
            </p>
            <p className="mt-2 font-bold text-rose-950">
              {resumen.contenedores.inconsistentes}{" "}
              {resumen.contenedores.inconsistentes === 1
                ? "contenedor presenta"
                : "contenedores presentan"}{" "}
              estado y ubicación incoherentes.
            </p>
            <Link
              to="/contenedores?coherencia=inconsistente"
              className="mt-4 inline-flex text-xs font-bold text-rose-700 underline decoration-rose-300 underline-offset-4"
            >
              Revisar contenedores
            </Link>
          </article>
          )}

          {resumen.contenedores.presencia_sin_confirmar > 0 && (
          <article className="rounded-2xl border border-amber-200 bg-amber-50 p-5">
            <p className="text-xs font-bold uppercase tracking-wider text-amber-700">
              Presencia por confirmar
            </p>
            <p className="mt-2 font-bold text-amber-950">
              {resumen.contenedores.presencia_sin_confirmar}{" "}
              {resumen.contenedores.presencia_sin_confirmar === 1
                ? "contenedor no tiene"
                : "contenedores no tienen"}{" "}
              ubicación catalogada.
            </p>
            <Link
              to="/contenedores?situacion=presencia_sin_confirmar"
              className="mt-4 inline-flex text-xs font-bold text-amber-700 underline decoration-amber-300 underline-offset-4"
            >
              Consultar inventario
            </Link>
          </article>
          )}
        </section>
      )}

      <div className="mt-6 grid gap-6 xl:grid-cols-[minmax(0,1.15fr)_minmax(22rem,0.85fr)]">
        <MovimientosChart datos={resumen.movimientos_ultimos_7_dias} />
        <MovimientosRecientes movimientos={resumen.ultimos_movimientos} />
      </div>

      <p className="mt-4 text-right text-[11px] text-slate-400">
        Período {etiquetaFechaPeriodo(resumen.periodo.desde)} al{" "}
        {etiquetaFechaPeriodo(resumen.periodo.hasta)} · días calendario{" "}
        {resumen.zona_horaria}
      </p>
    </div>
  );
}
