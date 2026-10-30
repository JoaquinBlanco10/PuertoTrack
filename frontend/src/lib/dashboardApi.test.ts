import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "./api";
import { obtenerResumenDashboard } from "./dashboardApi";

const resumen = {
  generado_en: "2026-10-18T12:00:00Z",
  zona_horaria: "UTC",
  periodo: { desde: "2026-10-12", hasta: "2026-10-18", dias: 7 },
  contenedores: {
    dentro_puerto: 4,
    fuera_puerto: 2,
    presencia_sin_confirmar: 1,
    inconsistentes: 1,
  },
  movimientos_ultimos_7_dias: [],
  ultimos_movimientos: [],
};

function respuestaJson(datos: unknown, status = 200): Response {
  return new Response(JSON.stringify(datos), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("cliente del dashboard", () => {
  it("consume el resumen con JWT y permite cancelar la solicitud", async () => {
    const fetchMock = vi.fn().mockResolvedValue(respuestaJson(resumen));
    vi.stubGlobal("fetch", fetchMock);
    const controller = new AbortController();

    const resultado = await obtenerResumenDashboard(
      "jwt-operativo",
      controller.signal,
    );

    const [url, opciones] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/dashboard/resumen");
    expect(new Headers(opciones.headers).get("Authorization")).toBe(
      "Bearer jwt-operativo",
    );
    expect(opciones.signal).toBe(controller.signal);
    expect(resultado.contenedores.dentro_puerto).toBe(4);
  });

  it("conserva el 401 para que AuthContext cierre la sesión", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        respuestaJson({ detail: "Credenciales inválidas." }, 401),
      ),
    );

    await expect(obtenerResumenDashboard("jwt-vencido")).rejects.toMatchObject<
      Partial<ApiError>
    >({ status: 401, message: "Credenciales inválidas." });
  });
});
