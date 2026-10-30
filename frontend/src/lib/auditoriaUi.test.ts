import { describe, expect, it } from "vitest";

import type { RegistroAuditoria } from "../types/auditoria";
import {
  etiquetaAccion,
  etiquetaCampo,
  obtenerCambiosAuditoria,
  presentarValor,
} from "./auditoriaUi";

function registro(
  datosAnteriores: Record<string, unknown> | null,
  datosNuevos: Record<string, unknown> | null,
): RegistroAuditoria {
  return {
    id: 1,
    usuario_id: 2,
    accion: "actualizar",
    entidad: "contenedor",
    entidad_id: 3,
    datos_anteriores: datosAnteriores,
    datos_nuevos: datosNuevos,
    fecha: "2026-10-18T12:00:00",
  };
}

describe("presentación del detalle de auditoría", () => {
  it("une ambos snapshots y distingue campos modificados", () => {
    const cambios = obtenerCambiosAuditoria(
      registro(
        { codigo: "ABC1", estado: "disponible", eliminado: true },
        { codigo: "ABC2", estado: "disponible", ubicacion_actual: "Muelle 1" },
      ),
    );

    expect(cambios.map((cambio) => cambio.campo)).toEqual([
      "codigo",
      "eliminado",
      "estado",
      "ubicacion_actual",
    ]);
    expect(cambios.find((cambio) => cambio.campo === "codigo")?.modificado).toBe(true);
    expect(cambios.find((cambio) => cambio.campo === "estado")?.modificado).toBe(false);
    expect(cambios.find((cambio) => cambio.campo === "eliminado")).toMatchObject({
      tieneAnterior: true,
      tieneNuevo: false,
      modificado: true,
    });
  });

  it("diferencia un valor nulo de un campo no informado", () => {
    expect(presentarValor(null, true)).toBe("Nulo");
    expect(presentarValor(undefined, false)).toBe("No informado");
  });

  it("formatea etiquetas y estructuras sin inventar valores", () => {
    expect(etiquetaCampo("ubicacion_actual_id")).toBe("Ubicacion actual id");
    expect(etiquetaAccion("regularizar_ubicacion")).toBe(
      "regularizar ubicacion",
    );
    expect(presentarValor({ codigo: "PATIO_A" }, true)).toContain(
      '"codigo": "PATIO_A"',
    );
  });
});
