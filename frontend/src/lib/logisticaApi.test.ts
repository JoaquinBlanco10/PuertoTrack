import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "./api";
import {
  buscarContenedorPorCodigo,
  corregirCodigoContenedor,
  actualizarUbicacion,
  crearContenedor,
  crearUbicacion,
  listarContenedores,
  listarUbicaciones,
  listarMovimientos,
  listarMovimientosPorContenedor,
  obtenerContextoMovimiento,
  regularizarUbicacionContenedor,
  registrarMovimiento,
} from "./logisticaApi";

const contenedor = {
  id: 12,
  codigo: "MSCU1234567",
  ubicacion_actual: "Patio Norte",
  ubicacion_actual_id: 3,
  situacion: "dentro_puerto",
  coherencia_operacional: "coherente",
  tiene_evidencia_historica: true,
  regularizacion_permitida: false,
  estado: "en_patio",
  fecha_creacion: "2026-10-18T10:00:00",
  fecha_actualizacion: "2026-10-18T10:00:00",
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

describe("cliente de contenedores", () => {
  it("envía paginación y JWT al listar", async () => {
    const fetchMock = vi.fn().mockResolvedValue(respuestaJson([contenedor]));
    vi.stubGlobal("fetch", fetchMock);

    await listarContenedores("jwt-prueba", { offset: 10, limite: 11 });

    const [url, opciones] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/contenedores?offset=10&limite=11");
    expect(new Headers(opciones.headers).get("Authorization")).toBe("Bearer jwt-prueba");
  });

  it("codifica el código en la ruta de búsqueda", async () => {
    const fetchMock = vi.fn().mockResolvedValue(respuestaJson(contenedor));
    vi.stubGlobal("fetch", fetchMock);

    await buscarContenedorPorCodigo("jwt", " ABC/123 ");

    expect(fetchMock.mock.calls[0][0]).toContain("/contenedores/codigo/ABC%2F123");
  });

  it("crea el contenedor con el contrato exacto", async () => {
    const fetchMock = vi.fn().mockResolvedValue(respuestaJson(contenedor, 201));
    vi.stubGlobal("fetch", fetchMock);
    const datos = { codigo: "MSCU1234567" };

    await crearContenedor("jwt", datos);

    const [, opciones] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(opciones.method).toBe("POST");
    expect(JSON.parse(opciones.body as string)).toEqual(datos);
  });

  it("filtra por situación o coherencia y regulariza usando un ID", async () => {
    const fetchMock = vi.fn().mockResolvedValue(respuestaJson([contenedor]));
    vi.stubGlobal("fetch", fetchMock);
    await listarContenedores("jwt", { offset: 0, limite: 10, situacion: "dentro_puerto" });
    expect(fetchMock.mock.calls[0][0]).toContain("situacion=dentro_puerto");

    fetchMock.mockResolvedValueOnce(respuestaJson([contenedor]));
    await listarContenedores("jwt", { offset: 0, limite: 10, coherencia: "inconsistente" });
    expect(fetchMock.mock.calls[1][0]).toContain("coherencia=inconsistente");

    fetchMock.mockResolvedValueOnce(respuestaJson(contenedor));
    await regularizarUbicacionContenedor("jwt", 12, {
      ubicacion_id: 3,
      estado: "en_patio",
      justificacion: "Manifiesto histórico verificado.",
    });
    const [, opciones] = fetchMock.mock.calls[2] as [string, RequestInit];
    expect(opciones.method).toBe("POST");
    expect(JSON.parse(opciones.body as string)).toEqual({
      ubicacion_id: 3,
      estado: "en_patio",
      justificacion: "Manifiesto histórico verificado.",
    });
  });

  it("busca por prefijo de código conservando paginación y situación", async () => {
    const fetchMock = vi.fn().mockResolvedValue(respuestaJson([contenedor]));
    vi.stubGlobal("fetch", fetchMock);

    await listarContenedores("jwt", {
      offset: 100,
      limite: 21,
      codigo: " MSCU ",
      situacion: "dentro_puerto",
    });

    const url = new URL(fetchMock.mock.calls[0][0] as string);
    expect(url.searchParams.get("offset")).toBe("100");
    expect(url.searchParams.get("limite")).toBe("21");
    expect(url.searchParams.get("codigo")).toBe("MSCU");
    expect(url.searchParams.get("situacion")).toBe("dentro_puerto");
  });

  it("la corrección solo envía el código", async () => {
    const fetchMock = vi.fn().mockResolvedValue(respuestaJson(contendorCorregido()));
    vi.stubGlobal("fetch", fetchMock);

    await corregirCodigoContenedor("jwt", 12, { codigo: "TGHU7654321" });

    const [url, opciones] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/contenedores/12");
    expect(opciones.method).toBe("PATCH");
    expect(JSON.parse(opciones.body as string)).toEqual({ codigo: "TGHU7654321" });
  });

  it("preserva el 409 devuelto por un código duplicado", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        respuestaJson({ detail: "Ya existe un contenedor con ese código." }, 409),
      ),
    );

    await expect(
      corregirCodigoContenedor("jwt", 12, { codigo: "DUPLICADO" }),
    ).rejects.toMatchObject<Partial<ApiError>>({ status: 409 });
  });
});

describe("cliente de movimientos", () => {
  it("consulta historial por contenedor con paginación", async () => {
    const fetchMock = vi.fn().mockResolvedValue(respuestaJson([]));
    vi.stubGlobal("fetch", fetchMock);

    await listarMovimientosPorContenedor("jwt", 12, { offset: 20, limite: 11 });

    expect(fetchMock.mock.calls[0][0]).toContain(
      "/movimientos/contenedor/12?offset=20&limite=11",
    );
  });

  it("solicita orden descendente sin cambiar el valor por defecto", async () => {
    const fetchMock = vi.fn().mockImplementation(() =>
      Promise.resolve(respuestaJson([])),
    );
    vi.stubGlobal("fetch", fetchMock);

    await listarMovimientos("jwt", { offset: 0, limite: 11, orden: "desc" });
    await listarMovimientos("jwt", { offset: 0, limite: 11 });

    expect(new URL(fetchMock.mock.calls[0][0] as string).searchParams.get("orden")).toBe("desc");
    expect(new URL(fetchMock.mock.calls[1][0] as string).searchParams.has("orden")).toBe(false);
  });

  it("registra una salida con el identificador de catálogo", async () => {
    const movimiento = {
      id: 4,
      contenedor_id: 12,
      usuario_id: 2,
      tipo: "salida",
      ubicacion_origen: "Patio Norte",
      ubicacion_destino: "Fuera del puerto",
      ubicacion_origen_id: 3,
      ubicacion_destino_id: 9,
      fecha_movimiento: "2026-10-18T12:00:00",
      observacion: null,
    };
    const fetchMock = vi.fn().mockResolvedValue(respuestaJson(movimiento, 201));
    vi.stubGlobal("fetch", fetchMock);

    await registrarMovimiento("jwt", { contenedor_id: 12, tipo: "salida", ubicacion_destino_id: 9 });

    const [, opciones] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(opciones.method).toBe("POST");
    expect(JSON.parse(opciones.body as string)).toEqual({
      contenedor_id: 12,
      tipo: "salida",
      ubicacion_destino_id: 9,
    });
  });

  it("consulta el contexto del contenedor", async () => {
    const fetchMock = vi.fn().mockResolvedValue(respuestaJson({ contenedor_id: 12, tiene_movimientos: true, tiene_salida_previa: true, etiqueta_entrada: "reingreso" }));
    vi.stubGlobal("fetch", fetchMock);
    await obtenerContextoMovimiento("jwt", 12);
    expect(fetchMock.mock.calls[0][0]).toContain("/movimientos/contenedor/12/contexto");
  });
});

describe("cliente de ubicaciones", () => {
  it("lista con filtros y conserva el contrato de administración", async () => {
    const ubicacion = { id: 3, codigo: "PATIO_A", nombre: "Patio A", tipo: "interna", activo: true };
    const fetchMock = vi.fn().mockResolvedValue(respuestaJson([ubicacion]));
    vi.stubGlobal("fetch", fetchMock);
    await listarUbicaciones("jwt", { offset: 0, limite: 100, tipo: "interna", incluirInactivas: true });
    expect(fetchMock.mock.calls[0][0]).toContain("tipo=interna");
    expect(fetchMock.mock.calls[0][0]).toContain("incluir_inactivas=true");

    fetchMock.mockResolvedValueOnce(respuestaJson(ubicacion, 201));
    await crearUbicacion("jwt", { codigo: "PATIO_A", nombre: "Patio A", tipo: "interna" });
    expect(JSON.parse(fetchMock.mock.calls[1][1].body as string)).toEqual({ codigo: "PATIO_A", nombre: "Patio A", tipo: "interna" });

    fetchMock.mockResolvedValueOnce(respuestaJson({ ...ubicacion, activo: false }));
    await actualizarUbicacion("jwt", 3, { activo: false });
    expect(JSON.parse(fetchMock.mock.calls[2][1].body as string)).toEqual({ activo: false });
  });
});

function contendorCorregido() {
  return { ...contenedor, codigo: "TGHU7654321" };
}
