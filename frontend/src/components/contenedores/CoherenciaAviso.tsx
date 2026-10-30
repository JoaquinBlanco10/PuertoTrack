import type { Contenedor } from "../../types/logistica";
import { Alerta } from "../ui/Feedback";

export function CoherenciaAviso({ contenedor }: { contenedor: Contenedor }) {
  if (contenedor.coherencia_operacional === "inconsistente") {
    return (
      <Alerta tipo="error">
        La ubicación catalogada y el estado operacional no coinciden. No se
        pueden registrar movimientos hasta que un supervisor regularice los
        datos con evidencia histórica.
      </Alerta>
    );
  }
  if (
    contenedor.coherencia_operacional === "sin_confirmar" &&
    contenedor.estado === "en_patio"
  ) {
    return (
      <Alerta tipo="error">
        El contenedor figura en patio, pero su ubicación no está confirmada en
        el catálogo. Debe regularizarse antes de trasladarlo o darle salida.
      </Alerta>
    );
  }
  return null;
}
