from uuid import UUID

from rfid_service.simulator import crear_mensaje_simulado


def test_simulador_genera_contrato_utc_sin_datos_operacionales() -> None:
    mensaje = crear_mensaje_simulado(" cont123 ", "LECTOR_SIMULADO")

    UUID(mensaje["evento_id"])
    assert mensaje["codigo_contenedor"] == "CONT123"
    assert mensaje["lector"] == "LECTOR_SIMULADO"
    assert mensaje["fecha_utc"].endswith("Z")
    assert set(mensaje) == {
        "evento_id",
        "codigo_contenedor",
        "lector",
        "fecha_utc",
    }
