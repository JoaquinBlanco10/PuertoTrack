import { describe, expect, it } from "vitest";

import {
  destinoCoincideConOrigen,
  destinosPermitidos,
  etiquetaEntrada,
  filtrarContenedores,
  incorporarMovimientoReciente,
  operacionesPermitidas,
  resumirMovimiento,
} from "./movimientosUi";
import {
  MAX_LONGITUD_OBSERVACION,
  type Contenedor,
  type Movimiento,
  type Ubicacion,
} from "../types/logistica";

const contenedor: Contenedor = {
  id: 1,
  codigo: "MSCU1234567",
  ubicacion_actual: "Patio A",
  ubicacion_actual_id: 10,
  situacion: "dentro_puerto",
  coherencia_operacional: "coherente",
  tiene_evidencia_historica: true,
  regularizacion_permitida: false,
  estado: "en_patio",
  fecha_creacion: "2026-10-18T10:00:00",
  fecha_actualizacion: "2026-10-18T10:00:00",
};
const patioA: Ubicacion = { id: 10, codigo: "PATIO_A", nombre: "Patio A", tipo: "interna", activo: true };
const patioB: Ubicacion = { id: 11, codigo: "PATIO_B", nombre: "Patio B", tipo: "interna", activo: true };
const fuera: Ubicacion = { id: 12, codigo: "FUERA_PUERTO", nombre: "Fuera del puerto", tipo: "externa", activo: true };
const inactiva: Ubicacion = { id: 13, codigo: "PATIO_X", nombre: "Patio X", tipo: "interna", activo: false };

describe("orientación visual de movimientos", () => {
  it("mantiene el límite de observación alineado con el backend", () => {
    expect(MAX_LONGITUD_OBSERVACION).toBe(1000);
  });

  it.each([
    ["disponible", ["entrada"]],
    ["en_transito", ["entrada"]],
    ["en_patio", ["traslado", "salida"]],
    ["mantenimiento", []],
  ])("orienta operaciones para el estado %s", (estado, esperadas) => {
    expect(operacionesPermitidas(estado as string)).toEqual(esperadas);
  });

  it("no ofrece operaciones si ubicación y estado son incoherentes", () => {
    expect(
      operacionesPermitidas({
        ...contenedor,
        estado: "disponible",
        coherencia_operacional: "inconsistente",
      }),
    ).toEqual([]);
    expect(
      operacionesPermitidas({
        ...contenedor,
        ubicacion_actual_id: null,
        situacion: "presencia_sin_confirmar",
        coherencia_operacional: "sin_confirmar",
      }),
    ).toEqual([]);
  });

  it("filtra destinos activos por tipo y excluye el origen en traslados", () => {
    const catalogo = [patioA, patioB, fuera, inactiva];
    expect(destinosPermitidos(catalogo, "traslado", contenedor)).toEqual([patioB]);
    expect(destinosPermitidos(catalogo, "entrada", contenedor)).toEqual([patioA, patioB]);
    expect(destinosPermitidos(catalogo, "salida", contenedor)).toEqual([fuera]);
  });

  it("resume únicamente el destino seleccionado", () => {
    expect(resumirMovimiento(contenedor, "salida", fuera)).toEqual({
      origen: "Patio A",
      destino: "Fuera del puerto",
      estadoEsperado: "en_transito",
    });
    expect(resumirMovimiento(contenedor, "traslado", null).destino).toBe("");
  });

  it("compara el destino con el origen por identificador", () => {
    expect(destinoCoincideConOrigen(contenedor, patioA)).toBe(true);
    expect(destinoCoincideConOrigen(contenedor, patioB)).toBe(false);
  });

  it("distingue primera entrada, reingreso y contexto histórico ambiguo", () => {
    expect(etiquetaEntrada({ contenedor_id: 1, tiene_movimientos: false, tiene_salida_previa: false, etiqueta_entrada: "primera_entrada" })).toBe("Primera entrada");
    expect(etiquetaEntrada({ contenedor_id: 1, tiene_movimientos: true, tiene_salida_previa: true, etiqueta_entrada: "reingreso" })).toBe("Registrar reingreso");
    expect(etiquetaEntrada({ contenedor_id: 1, tiene_movimientos: true, tiene_salida_previa: false, etiqueta_entrada: "entrada" })).toBe("Entrada");
  });

  it("busca contenedores por código, ubicación, estado y situación", () => {
    const segundo = { ...contenedor, id: 2, codigo: "TGHU7654321", ubicacion_actual: "Zona exterior", ubicacion_actual_id: 12, situacion: "fuera_puerto" as const, estado: "en_transito" };
    expect(filtrarContenedores([contenedor, segundo], "mscu")).toEqual([contenedor]);
    expect(filtrarContenedores([contenedor, segundo], "fuera puerto")).toEqual([segundo]);
  });

  it("incorpora el movimiento registrado primero y evita duplicados", () => {
    const base = (id: number, fecha: string): Movimiento => ({
      id,
      contenedor_id: 1,
      usuario_id: 2,
      tipo: "traslado",
      ubicacion_origen: "Patio A",
      ubicacion_destino: "Patio B",
      ubicacion_origen_id: 10,
      ubicacion_destino_id: 11,
      fecha_movimiento: fecha,
      observacion: null,
    });
    const mismaFecha = "2026-10-18T12:00:00Z";
    const existentes = [base(1, mismaFecha), base(2, mismaFecha)];
    const nuevo = base(3, "2026-10-18T12:01:00Z");

    expect(
      incorporarMovimientoReciente([...existentes, nuevo], nuevo, 10).map(
        (movimiento) => movimiento.id,
      ),
    ).toEqual([3, 2, 1]);
  });
});
