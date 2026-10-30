import type { RegistroAuditoria } from "../types/auditoria";

export interface CambioAuditoria {
  campo: string;
  anterior: unknown;
  nuevo: unknown;
  tieneAnterior: boolean;
  tieneNuevo: boolean;
  modificado: boolean;
}

function iguales(anterior: unknown, nuevo: unknown): boolean {
  return JSON.stringify(anterior) === JSON.stringify(nuevo);
}

export function obtenerCambiosAuditoria(
  registro: RegistroAuditoria,
): CambioAuditoria[] {
  const anteriores = registro.datos_anteriores ?? {};
  const nuevos = registro.datos_nuevos ?? {};
  const campos = Array.from(
    new Set([...Object.keys(anteriores), ...Object.keys(nuevos)]),
  ).sort((a, b) => a.localeCompare(b));

  return campos.map((campo) => {
    const tieneAnterior = Object.hasOwn(anteriores, campo);
    const tieneNuevo = Object.hasOwn(nuevos, campo);
    const anterior = anteriores[campo];
    const nuevo = nuevos[campo];
    return {
      campo,
      anterior,
      nuevo,
      tieneAnterior,
      tieneNuevo,
      modificado:
        tieneAnterior !== tieneNuevo || !iguales(anterior, nuevo),
    };
  });
}

export function etiquetaCampo(campo: string): string {
  const texto = campo.replaceAll("_", " ");
  return texto.charAt(0).toLocaleUpperCase() + texto.slice(1);
}

export function presentarValor(valor: unknown, existe: boolean): string {
  if (!existe) return "No informado";
  if (valor === null) return "Nulo";
  if (typeof valor === "boolean") return valor ? "Sí" : "No";
  if (typeof valor === "string") return valor || "Texto vacío";
  if (typeof valor === "number") return String(valor);
  return JSON.stringify(valor, null, 2);
}

export function etiquetaAccion(accion: string): string {
  return accion.replaceAll("_", " ");
}
