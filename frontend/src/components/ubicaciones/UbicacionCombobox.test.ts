import { describe, expect, it } from "vitest";

import type { Ubicacion } from "../../types/logistica";
import { textoSeleccionUbicacion } from "./UbicacionCombobox";

describe("UbicacionCombobox", () => {
  it("presenta primero el nombre amigable y conserva el código", () => {
    const ubicacion: Ubicacion = {
      id: 1,
      codigo: "PATIO_A",
      nombre: "Patio A",
      tipo: "interna",
      activo: true,
    };

    expect(textoSeleccionUbicacion(ubicacion)).toBe("Patio A · PATIO_A");
  });
});
