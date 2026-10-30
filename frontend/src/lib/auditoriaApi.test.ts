import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "./api";
import { listarAuditoria } from "./auditoriaApi";

function respuestaJson(datos: unknown, status = 200): Response {
  return new Response(JSON.stringify(datos), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("cliente de auditoría", () => {
  it("envía filtros, paginación y JWT con el contrato del backend", async () => {
    const fetchMock = vi.fn().mockResolvedValue(respuestaJson([]));
    vi.stubGlobal("fetch", fetchMock);

    await listarAuditoria("jwt-supervisor", {
      usuarioId: 7,
      entidad: " contenedor ",
      entidadId: 25,
      accion: " actualizar ",
      offset: 20,
      limite: 11,
    });

    const [url, opciones] = fetchMock.mock.calls[0] as [string, RequestInit];
    const consulta = new URL(url).searchParams;
    expect(consulta.get("usuario_id")).toBe("7");
    expect(consulta.get("entidad")).toBe("contenedor");
    expect(consulta.get("entidad_id")).toBe("25");
    expect(consulta.get("accion")).toBe("actualizar");
    expect(consulta.get("offset")).toBe("20");
    expect(consulta.get("limite")).toBe("11");
    expect(new Headers(opciones.headers).get("Authorization")).toBe(
      "Bearer jwt-supervisor",
    );
  });

  it("omite filtros vacíos sin alterar la paginación", async () => {
    const fetchMock = vi.fn().mockResolvedValue(respuestaJson([]));
    vi.stubGlobal("fetch", fetchMock);

    await listarAuditoria("jwt", {
      entidad: "   ",
      accion: "",
      offset: 0,
      limite: 11,
    });

    const consulta = new URL(fetchMock.mock.calls[0][0] as string).searchParams;
    expect([...consulta.keys()].sort()).toEqual(["limite", "offset"]);
  });

  it("conserva un 403 para que la aplicación maneje el permiso denegado", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        respuestaJson({ detail: "No tiene permisos suficientes." }, 403),
      ),
    );

    await expect(
      listarAuditoria("jwt-operador", { offset: 0, limite: 11 }),
    ).rejects.toMatchObject<Partial<ApiError>>({
      status: 403,
      message: "No tiene permisos suficientes.",
    });
  });
});
