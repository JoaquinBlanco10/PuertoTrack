import type {
  CoherenciaOperacional,
  SituacionContenedor,
} from "../types/logistica";

export type FiltroContenedores =
  | "todas"
  | SituacionContenedor
  | "inconsistentes";

const SITUACIONES = new Set<SituacionContenedor>([
  "dentro_puerto",
  "fuera_puerto",
  "presencia_sin_confirmar",
]);

export function filtroDesdeParametros(
  parametros: URLSearchParams,
): FiltroContenedores {
  if (parametros.get("coherencia") === "inconsistente") {
    return "inconsistentes";
  }
  const situacion = parametros.get("situacion") as SituacionContenedor | null;
  return situacion && SITUACIONES.has(situacion) ? situacion : "todas";
}

export function consultaParaFiltro(filtro: FiltroContenedores): {
  situacion?: SituacionContenedor;
  coherencia?: CoherenciaOperacional;
} {
  if (filtro === "inconsistentes") {
    return { coherencia: "inconsistente" };
  }
  if (filtro === "todas") return {};
  return { situacion: filtro };
}

export function parametrosDeFiltro(
  filtro: FiltroContenedores,
): URLSearchParams {
  const parametros = new URLSearchParams();
  if (filtro === "inconsistentes") {
    parametros.set("coherencia", "inconsistente");
  } else if (filtro !== "todas") {
    parametros.set("situacion", filtro);
  }
  return parametros;
}
