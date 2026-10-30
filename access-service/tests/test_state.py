from datetime import datetime, timezone
from uuid import uuid4

from access_service.contracts import DecisionAcceso, ResultadoAcceso
from access_service.state import AlmacenDecisiones


def _decision():
    return DecisionAcceso(
        decision_id=uuid4(),
        evento_id=uuid4(),
        codigo_contenedor="CONT123",
        contenedor_id=1,
        lector="PORTICO_NORTE",
        fecha_evento=datetime.now(timezone.utc),
        resultado=ResultadoAcceso.HABILITADO,
        motivo="PRIMERA_ENTRADA_HABILITADA",
        fecha_decision=datetime.now(timezone.utc),
    )


def test_decisiones_expiran_y_el_historial_respeta_limite() -> None:
    instante = [100.0]
    almacen = AlmacenDecisiones(
        max_decisiones=2,
        ttl_deduplicacion=10,
        ttl_decisiones=30,
        reloj=lambda: instante[0],
    )
    primera, segunda, tercera = _decision(), _decision(), _decision()
    almacen.registrar(primera)
    almacen.registrar(segunda)
    almacen.registrar(tercera)

    assert almacen.listar(limite=10) == [tercera, segunda]

    instante[0] = 131.0
    assert almacen.listar(limite=10) == []
    assert almacen.buscar_evento(str(tercera.evento_id)) is None
