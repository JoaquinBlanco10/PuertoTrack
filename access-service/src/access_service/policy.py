from dataclasses import dataclass

from .contracts import HechosOperacionales, ResultadoAcceso


@dataclass(frozen=True)
class ResultadoPolitica:
    resultado: ResultadoAcceso
    motivo: str


class PoliticaHabilitacionOperacional:
    """Política académica preliminar; no representa permisos legales."""

    def evaluar(self, hechos: HechosOperacionales) -> ResultadoPolitica:
        if hechos.coherencia_operacional == "inconsistente":
            return ResultadoPolitica(
                ResultadoAcceso.REVISION_MANUAL,
                "DATOS_OPERACIONALES_INCONSISTENTES",
            )
        if hechos.estado == "en_patio" or hechos.situacion == "dentro_puerto":
            return ResultadoPolitica(
                ResultadoAcceso.DENEGADO,
                "YA_SE_ENCUENTRA_EN_PUERTO",
            )
        if (
            hechos.estado == "disponible"
            and not hechos.tiene_movimientos
            and hechos.etiqueta_entrada == "primera_entrada"
        ):
            return ResultadoPolitica(
                ResultadoAcceso.HABILITADO,
                "PRIMERA_ENTRADA_HABILITADA",
            )
        if (
            hechos.estado == "en_transito"
            and hechos.situacion == "fuera_puerto"
            and hechos.coherencia_operacional == "coherente"
            and hechos.tiene_salida_previa
        ):
            return ResultadoPolitica(
                ResultadoAcceso.HABILITADO,
                "REINGRESO_HABILITADO",
            )
        if hechos.situacion == "presencia_sin_confirmar":
            return ResultadoPolitica(
                ResultadoAcceso.REVISION_MANUAL,
                "PRESENCIA_SIN_CONFIRMAR",
            )
        return ResultadoPolitica(
            ResultadoAcceso.DENEGADO,
            "ESTADO_NO_COMPATIBLE_CON_INGRESO",
        )
