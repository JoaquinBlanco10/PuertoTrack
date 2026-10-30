import pytest

from access_service.contracts import HechosOperacionales, ResultadoAcceso
from access_service.policy import PoliticaHabilitacionOperacional


def hechos(**cambios) -> HechosOperacionales:
    datos = {
        "existe": True,
        "id": 7,
        "codigo": "CONT123",
        "estado": "disponible",
        "situacion": "presencia_sin_confirmar",
        "coherencia_operacional": "sin_confirmar",
        "ubicacion_actual_id": None,
        "tiene_movimientos": False,
        "tiene_salida_previa": False,
        "etiqueta_entrada": "primera_entrada",
    }
    datos.update(cambios)
    return HechosOperacionales.model_validate(datos)


@pytest.mark.parametrize(
    ("datos", "resultado", "motivo"),
    [
        (
            {},
            ResultadoAcceso.HABILITADO,
            "PRIMERA_ENTRADA_HABILITADA",
        ),
        (
            {
                "estado": "en_transito",
                "situacion": "fuera_puerto",
                "coherencia_operacional": "coherente",
                "ubicacion_actual_id": 5,
                "tiene_movimientos": True,
                "tiene_salida_previa": True,
                "etiqueta_entrada": "reingreso",
            },
            ResultadoAcceso.HABILITADO,
            "REINGRESO_HABILITADO",
        ),
        (
            {
                "estado": "en_patio",
                "situacion": "dentro_puerto",
                "coherencia_operacional": "coherente",
                "ubicacion_actual_id": 2,
                "tiene_movimientos": True,
                "etiqueta_entrada": "entrada",
            },
            ResultadoAcceso.DENEGADO,
            "YA_SE_ENCUENTRA_EN_PUERTO",
        ),
        (
            {
                "coherencia_operacional": "inconsistente",
                "ubicacion_actual_id": 2,
            },
            ResultadoAcceso.REVISION_MANUAL,
            "DATOS_OPERACIONALES_INCONSISTENTES",
        ),
        (
            {
                "estado": "en_transito",
                "tiene_movimientos": True,
                "etiqueta_entrada": "entrada",
            },
            ResultadoAcceso.REVISION_MANUAL,
            "PRESENCIA_SIN_CONFIRMAR",
        ),
        (
            {
                "estado": "mantenimiento",
                "situacion": "fuera_puerto",
                "coherencia_operacional": "coherente",
                "ubicacion_actual_id": 4,
            },
            ResultadoAcceso.DENEGADO,
            "ESTADO_NO_COMPATIBLE_CON_INGRESO",
        ),
    ],
)
def test_politica_explicita(datos, resultado, motivo) -> None:
    evaluacion = PoliticaHabilitacionOperacional().evaluar(hechos(**datos))

    assert evaluacion.resultado == resultado
    assert evaluacion.motivo == motivo
