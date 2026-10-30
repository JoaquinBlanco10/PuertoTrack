import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, iniciarSesion, obtenerMiUsuario } from "./api";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("cliente de autenticación", () => {
  it("envía el email en username según OAuth2", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({ access_token: "token-prueba", token_type: "bearer" }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    await iniciarSesion("  USUARIO@EJEMPLO.CL ", "clave-segura");

    const [, opciones] = fetchMock.mock.calls[0] as [string, RequestInit];
    const cuerpo = opciones.body as URLSearchParams;
    expect(opciones.method).toBe("POST");
    expect(cuerpo.get("username")).toBe("usuario@ejemplo.cl");
    expect(cuerpo.get("password")).toBe("clave-segura");
  });

  it("envía el JWT como Bearer al consultar el perfil", async () => {
    const usuario = {
      id: 7,
      nombre: "María Operadora",
      email: "maria@ejemplo.cl",
      rol: "operador",
      activo: true,
      fecha_creacion: "2026-10-18T12:00:00",
    };
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(usuario), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(obtenerMiUsuario("jwt-prueba")).resolves.toEqual(usuario);

    const [, opciones] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect((opciones.headers as Record<string, string>).Authorization).toBe(
      "Bearer jwt-prueba",
    );
  });

  it("conserva el estado HTTP de errores de autorización", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "El usuario está inactivo" }), {
          status: 403,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    await expect(iniciarSesion("inactivo@ejemplo.cl", "clave")).rejects.toMatchObject<
      Partial<ApiError>
    >({ status: 403, message: "El usuario está inactivo" });
  });
});
