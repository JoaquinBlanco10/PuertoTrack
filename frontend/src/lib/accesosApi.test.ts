import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "./api";
import { listarDecisionesAcceso } from "./accesosApi";

function respuestaJson(datos: unknown, status = 200): Response {
  return new Response(JSON.stringify(datos), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

afterEach(() => vi.unstubAllGlobals());

describe("cliente de decisiones de acceso", () => {
  it("envía JWT, límite y filtro al proxy del backend", async () => {
    const fetchMock = vi.fn().mockResolvedValue(respuestaJson([]));
    vi.stubGlobal("fetch", fetchMock);

    await listarDecisionesAcceso("jwt-supervisor", {
      limite: 25,
      resultado: "revision_manual",
    });

    const [url, opciones] = fetchMock.mock.calls[0] as [string, RequestInit];
    const consulta = new URL(url).searchParams;
    expect(consulta.get("limite")).toBe("25");
    expect(consulta.get("resultado")).toBe("revision_manual");
    expect(new Headers(opciones.headers).get("Authorization")).toBe(
      "Bearer jwt-supervisor",
    );
  });

  it("omite el filtro y conserva el límite predeterminado", async () => {
    const fetchMock = vi.fn().mockResolvedValue(respuestaJson([]));
    vi.stubGlobal("fetch", fetchMock);

    await listarDecisionesAcceso("jwt");

    const consulta = new URL(fetchMock.mock.calls[0][0] as string).searchParams;
    expect(consulta.get("limite")).toBe("50");
    expect(consulta.has("resultado")).toBe(false);
  });

  it("conserva el 503 cuando el microservicio no está disponible", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        respuestaJson({ detail: "Servicio de accesos no disponible." }, 503),
      ),
    );

    await expect(listarDecisionesAcceso("jwt")).rejects.toMatchObject<
      Partial<ApiError>
    >({ status: 503, message: "Servicio de accesos no disponible." });
  });
});
