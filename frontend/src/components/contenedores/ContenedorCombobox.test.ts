import { describe, expect, it } from "vitest";

import { combinarResultadosContenedores } from "./ContenedorCombobox";

describe("resultados del selector de contenedores", () => {
  it("combina páginas sin duplicar ni mutar los arrays recibidos", () => {
    const actuales = [{ id: 2 }, { id: 1 }];
    const nuevos = [{ id: 1 }, { id: 3 }];
    const copiaActuales = [...actuales];
    const copiaNuevos = [...nuevos];

    const combinados = combinarResultadosContenedores(actuales, nuevos);

    expect(combinados.map((item) => item.id)).toEqual([2, 1, 3]);
    expect(actuales).toEqual(copiaActuales);
    expect(nuevos).toEqual(copiaNuevos);
    expect(combinados).not.toBe(actuales);
  });
});
