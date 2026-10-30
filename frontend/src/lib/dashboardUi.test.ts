import { describe, expect, it } from "vitest";

import {
  etiquetaDia,
  etiquetaFechaPeriodo,
  formatearInstanteUtc,
  maximoMovimientosDiarios,
  rutaIndicadorContenedores,
  totalMovimientosDia,
} from "./dashboardUi";

const dia = {
  fecha: "2026-10-18",
  entrada: 2,
  traslado: 5,
  salida: 1,
};

describe("presentación del dashboard", () => {
  it("calcula el total diario y la escala máxima por tipo", () => {
    expect(totalMovimientosDia(dia)).toBe(8);
    expect(
      maximoMovimientosDiarios([
        dia,
        { fecha: "2026-10-17", entrada: 3, traslado: 0, salida: 2 },
      ]),
    ).toBe(5);
  });

  it("admite una serie vacía o días sin movimientos", () => {
    expect(maximoMovimientosDiarios([])).toBe(0);
    expect(
      maximoMovimientosDiarios([
        { fecha: "2026-10-18", entrada: 0, traslado: 0, salida: 0 },
      ]),
    ).toBe(0);
  });

  it("formatea fechas calendario e instantes en UTC sin desplazar el día", () => {
    expect(etiquetaDia("2026-10-18")).toContain("18");
    expect(etiquetaFechaPeriodo("2026-10-18")).toContain("18");
    const instanteCercanoAlCambioDeDia = formatearInstanteUtc(
      "2026-10-18T00:30:00Z",
    );
    expect(instanteCercanoAlCambioDeDia).toContain("18");
    expect(instanteCercanoAlCambioDeDia).toContain("UTC");
  });

  it("genera enlaces con el filtro correspondiente a cada indicador", () => {
    expect(rutaIndicadorContenedores("dentro_puerto")).toBe(
      "/contenedores?situacion=dentro_puerto",
    );
    expect(rutaIndicadorContenedores("inconsistentes")).toBe(
      "/contenedores?coherencia=inconsistente",
    );
  });
});
