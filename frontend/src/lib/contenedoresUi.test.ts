import { describe, expect, it } from "vitest";

import {
  consultaParaFiltro,
  filtroDesdeParametros,
  parametrosDeFiltro,
} from "./contenedoresUi";

describe("filtros navegables de contenedores", () => {
  it("recupera una situación válida desde la URL", () => {
    const parametros = new URLSearchParams("situacion=fuera_puerto");
    expect(filtroDesdeParametros(parametros)).toBe("fuera_puerto");
    expect(consultaParaFiltro("fuera_puerto")).toEqual({
      situacion: "fuera_puerto",
    });
  });

  it("prioriza el filtro de inconsistencias", () => {
    const parametros = new URLSearchParams(
      "situacion=dentro_puerto&coherencia=inconsistente",
    );
    expect(filtroDesdeParametros(parametros)).toBe("inconsistentes");
    expect(consultaParaFiltro("inconsistentes")).toEqual({
      coherencia: "inconsistente",
    });
    expect(parametrosDeFiltro("inconsistentes").toString()).toBe(
      "coherencia=inconsistente",
    );
  });

  it("ignora filtros desconocidos sin enviarlos al backend", () => {
    expect(
      filtroDesdeParametros(new URLSearchParams("situacion=desconocida")),
    ).toBe("todas");
    expect(consultaParaFiltro("todas")).toEqual({});
  });
});
