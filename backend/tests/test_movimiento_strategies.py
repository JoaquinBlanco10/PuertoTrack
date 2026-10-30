import pytest

from models import Contenedor, Ubicacion
from movimiento_strategies import (
    EntradaStrategy,
    MovimientoInvalido,
    SalidaStrategy,
    TrasladoStrategy,
)


def crear_contenedor(
    estado: str, ubicacion: str, ubicacion_id: int | None = None
) -> Contenedor:
    contenedor = Contenedor(
        codigo="MSCU1234567",
        ubicacion_actual=ubicacion,
        ubicacion_actual_id=ubicacion_id,
        estado=estado,
    )
    if ubicacion_id is not None:
        contenedor.ubicacion_actual_catalogo = Ubicacion(
            id=ubicacion_id,
            codigo=f"ORIGEN_{ubicacion_id}",
            nombre=ubicacion,
            tipo="interna",
            activo=True,
        )
    return contenedor


def crear_ubicacion(
    ubicacion_id: int,
    nombre: str,
    tipo: str,
    *,
    activo: bool = True,
) -> Ubicacion:
    return Ubicacion(
        id=ubicacion_id,
        codigo=f"UBI_{ubicacion_id}",
        nombre=nombre,
        tipo=tipo,
        activo=activo,
    )


def test_estrategia_entrada_calcula_transicion_con_destino_interno() -> None:
    destino = crear_ubicacion(1, "Patio A", "interna")
    resultado = EntradaStrategy().procesar(
        crear_contenedor("disponible", "Sin asignar"), destino
    )

    assert resultado.origen == "Sin asignar"
    assert resultado.destino == "Patio A"
    assert resultado.destino_id == destino.id
    assert resultado.nuevo_estado == "en_patio"
    assert resultado.nueva_ubicacion_id == destino.id


def test_estrategia_traslado_exige_en_patio_y_destino_distinto() -> None:
    estrategia = TrasladoStrategy()
    patio_a = crear_ubicacion(1, "Patio A", "interna")
    patio_b = crear_ubicacion(2, "Patio B", "interna")

    with pytest.raises(MovimientoInvalido):
        estrategia.procesar(
            crear_contenedor("en_transito", "Acceso"), patio_b
        )
    with pytest.raises(MovimientoInvalido):
        estrategia.procesar(
            crear_contenedor("en_patio", "Patio A", patio_a.id), patio_a
        )


def test_traslado_con_fk_compara_ids_y_no_nombres() -> None:
    origen = crear_contenedor("en_patio", "Patio compartido", 1)
    destino_distinto = crear_ubicacion(2, "Patio compartido", "interna")

    resultado = TrasladoStrategy().procesar(origen, destino_distinto)

    assert resultado.origen_id == 1
    assert resultado.destino_id == 2


def test_registro_historico_sin_fk_compara_el_texto_del_origen() -> None:
    origen_historico = crear_contenedor(
        "disponible", "  Patio histórico  "
    )
    destino = crear_ubicacion(2, "patio HISTÓRICO", "interna")

    with pytest.raises(MovimientoInvalido, match="distinta"):
        EntradaStrategy().procesar(origen_historico, destino)


def test_estrategia_salida_exige_destino_externo_explicito() -> None:
    destino = crear_ubicacion(3, "Fuera del puerto", "externa")
    resultado = SalidaStrategy().procesar(
        crear_contenedor("en_patio", "Patio A", 1), destino
    )

    assert resultado.origen == "Patio A"
    assert resultado.destino == "Fuera del puerto"
    assert resultado.destino_id == destino.id
    assert resultado.nuevo_estado == "en_transito"


def test_estrategias_bloquean_origen_operacional_incoherente() -> None:
    patio = crear_ubicacion(1, "Patio A", "interna")
    externa = crear_ubicacion(2, "Depósito", "externa")
    interno_disponible = crear_contenedor("disponible", "Patio A", patio.id)
    sin_confirmar_en_patio = crear_contenedor("en_patio", "Texto histórico")

    with pytest.raises(MovimientoInvalido, match="incoherentes"):
        EntradaStrategy().procesar(interno_disponible, patio)
    with pytest.raises(MovimientoInvalido, match="regularizar"):
        SalidaStrategy().procesar(sin_confirmar_en_patio, externa)


@pytest.mark.parametrize(
    ("estrategia", "estado", "destino"),
    [
        (
            EntradaStrategy(),
            "en_patio",
            crear_ubicacion(1, "Patio A", "interna"),
        ),
        (
            SalidaStrategy(),
            "disponible",
            crear_ubicacion(2, "Depósito", "externa"),
        ),
        (
            EntradaStrategy(),
            "disponible",
            crear_ubicacion(3, "Depósito", "externa"),
        ),
        (
            SalidaStrategy(),
            "en_patio",
            crear_ubicacion(4, "Patio B", "interna"),
        ),
        (
            TrasladoStrategy(),
            "en_patio",
            crear_ubicacion(5, "Patio C", "interna", activo=False),
        ),
    ],
)
def test_estrategias_rechazan_transiciones_y_destinos_invalidos(
    estrategia: EntradaStrategy | SalidaStrategy | TrasladoStrategy,
    estado: str,
    destino: Ubicacion,
) -> None:
    with pytest.raises(MovimientoInvalido):
        estrategia.procesar(
            crear_contenedor(estado, "Ubicación inicial"), destino
        )
