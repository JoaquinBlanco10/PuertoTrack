import type { RolUsuario } from "../types/auth";

const ETIQUETAS_ROL: Record<RolUsuario, string> = {
  supervisor: "Supervisor",
  operador: "Operador",
};

export function etiquetaRol(rol: RolUsuario): string {
  return ETIQUETAS_ROL[rol];
}
