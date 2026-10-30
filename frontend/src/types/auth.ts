export type RolUsuario = "operador" | "supervisor";

export interface TokenRespuesta {
  access_token: string;
  token_type: "bearer";
}

export interface Usuario {
  id: number;
  nombre: string;
  email: string;
  rol: RolUsuario;
  activo: boolean;
  fecha_creacion: string;
}
