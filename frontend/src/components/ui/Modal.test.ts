import { describe, expect, it } from "vitest";

import { calcularDestinoTab } from "./Modal";

describe("navegación de foco del modal", () => {
  it("cicla desde el último elemento al primero", () => {
    expect(calcularDestinoTab(3, 2, false)).toBe(0);
  });

  it("cicla desde el primero al último con Shift+Tab", () => {
    expect(calcularDestinoTab(3, 0, true)).toBe(2);
  });

  it("recupera el foco cuando estaba fuera y respeta posiciones intermedias", () => {
    expect(calcularDestinoTab(3, -1, false)).toBe(0);
    expect(calcularDestinoTab(3, -1, true)).toBe(2);
    expect(calcularDestinoTab(3, 1, false)).toBeNull();
  });
});
