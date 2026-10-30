import json
from datetime import datetime, timezone
from uuid import uuid4

from access_service.backend_client import BackendNoDisponible
from access_service.contracts import HechosOperacionales, ResultadoAcceso
from access_service.policy import PoliticaHabilitacionOperacional
from access_service.processor import ProcesadorAccesos
from access_service.state import AlmacenDecisiones


class BackendFalso:
    def __init__(self) -> None:
        self.fallar = False
        self.consultas = 0

    def consultar_hechos(self, codigo: str) -> HechosOperacionales:
        self.consultas += 1
        if self.fallar:
            raise BackendNoDisponible()
        return HechosOperacionales(
            existe=True,
            id=7,
            codigo=codigo,
            estado="disponible",
            situacion="presencia_sin_confirmar",
            coherencia_operacional="sin_confirmar",
            ubicacion_actual_id=None,
            tiene_movimientos=False,
            tiene_salida_previa=False,
            etiqueta_entrada="primera_entrada",
        )


def mensaje(*, evento_id=None, resultado="valido") -> bytes:
    return json.dumps(
        {
            "version": 1,
            "evento_id": str(evento_id or uuid4()),
            "codigo_contenedor": "CONT123",
            "contenedor_id": 7 if resultado == "valido" else None,
            "lector": "PORTICO_NORTE",
            "fecha_utc": datetime.now(timezone.utc).isoformat(),
            "identificado_en": datetime.now(timezone.utc).isoformat(),
            "resultado_identificacion": resultado,
        }
    ).encode()


def crear_procesador():
    backend = BackendFalso()
    almacen = AlmacenDecisiones(max_decisiones=20, ttl_deduplicacion=600)
    return (
        ProcesadorAccesos(
            backend=backend,  # type: ignore[arg-type]
            almacen=almacen,
            politica=PoliticaHabilitacionOperacional(),
            max_payload_bytes=1024,
        ),
        backend,
        almacen,
    )


def test_habilita_contenedor_y_deduplica_sin_segunda_consulta() -> None:
    procesador, backend, almacen = crear_procesador()
    evento_id = uuid4()

    primera = procesador.procesar(mensaje(evento_id=evento_id))
    duplicada = procesador.procesar(mensaje(evento_id=evento_id))

    assert primera is not None
    assert primera.resultado == ResultadoAcceso.HABILITADO
    assert duplicada is None
    assert backend.consultas == 1
    assert almacen.resumen()[1] == 1


def test_codigo_desconocido_no_consulta_backend() -> None:
    procesador, backend, _ = crear_procesador()

    decision = procesador.procesar(mensaje(resultado="codigo_desconocido"))

    assert decision is not None
    assert decision.resultado == ResultadoAcceso.DENEGADO
    assert decision.motivo == "CODIGO_DESCONOCIDO"
    assert backend.consultas == 0


def test_backend_no_disponible_no_autoriza() -> None:
    procesador, backend, _ = crear_procesador()
    backend.fallar = True

    decision = procesador.procesar(mensaje())

    assert decision is not None
    assert decision.resultado == ResultadoAcceso.NO_DETERMINADO
    assert decision.motivo == "BACKEND_NO_DISPONIBLE"


def test_rechaza_contrato_invalido_y_payload_grande() -> None:
    procesador, backend, almacen = crear_procesador()

    assert procesador.procesar(b"no-json") is None
    assert procesador.procesar(b"x" * 1025) is None
    assert backend.consultas == 0
    assert almacen.resumen()[2] == 2
