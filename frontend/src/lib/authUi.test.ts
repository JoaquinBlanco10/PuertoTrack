import { describe, expect, it } from "vitest";

import { etiquetaRol } from "./authUi";

describe("etiquetaRol", () => {
  it("presenta los roles con las etiquetas fijas del sistema", () => {
    expect(etiquetaRol("supervisor")).toBe("Supervisor");
    expect(etiquetaRol("operador")).toBe("Operador");
  });
});
