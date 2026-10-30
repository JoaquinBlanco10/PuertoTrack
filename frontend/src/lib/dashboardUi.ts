import type {
  MovimientoDiarioDashboard,
  TotalesContenedoresDashboard,
} from "../types/dashboard";

export function totalMovimientosDia(dia: MovimientoDiarioDashboard): number {
  return dia.entrada + dia.traslado + dia.salida;
}

export function maximoMovimientosDiarios(
  serie: MovimientoDiarioDashboard[],
): number {
  return Math.max(
    0,
    ...serie.flatMap((dia) => [dia.entrada, dia.traslado, dia.salida]),
  );
}

export function etiquetaDia(fecha: string): string {
  const fechaUtc = fechaCalendarioUtc(fecha);
  return new Intl.DateTimeFormat("es-CL", {
    weekday: "short",
    day: "numeric",
    timeZone: "UTC",
  })
    .format(fechaUtc)
    .replace(".", "");
}

export function etiquetaFechaPeriodo(fecha: string): string {
  return new Intl.DateTimeFormat("es-CL", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  })
    .format(fechaCalendarioUtc(fecha))
    .replace(".", "");
}

export function formatearInstanteUtc(valor: string): string {
  return `${new Intl.DateTimeFormat("es-CL", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  }).format(new Date(valor))} UTC`;
}

export function rutaIndicadorContenedores(
  campo: keyof TotalesContenedoresDashboard,
): string {
  if (campo === "inconsistentes") {
    return "/contenedores?coherencia=inconsistente";
  }
  return `/contenedores?situacion=${campo}`;
}

function fechaCalendarioUtc(fecha: string): Date {
  const [anio, mes, dia] = fecha.split("-").map(Number);
  return new Date(Date.UTC(anio, mes - 1, dia));
}
