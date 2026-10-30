import json
from uuid import uuid4

from rfid_service.backend_client import (
    CodigoContenedorDesconocido,
    ErrorBackendOperacional,
)
from rfid_service.contracts import ContenedorIdentificado, EstadoProcesamiento
from rfid_service.processor import ProcesadorRFID
from rfid_service.state import AlmacenProcesamientos


class BackendFalso:
    def __init__(self) -> None:
        self.codigos: dict[str, int] = {"CONT123": 42}
        self.fallar = False
        self.consultas = 0

    def identificar(self, codigo: str) -> ContenedorIdentificado:
        self.consultas += 1
        if self.fallar:
            raise ErrorBackendOperacional("fallo simulado")
        if codigo not in self.codigos:
            raise CodigoContenedorDesconocido(codigo)
        return ContenedorIdentificado(
            existe=True,
            id=self.codigos[codigo],
            codigo=codigo,
        )


def mensaje(
    *,
    evento_id: str | None = None,
    codigo: str = "cont123",
) -> bytes:
    return json.dumps(
        {
            "evento_id": evento_id or str(uuid4()),
            "codigo_contenedor": codigo,
            "lector": "PORTICO_NORTE",
            "fecha_utc": "2026-10-19T12:00:00Z",
        }
    ).encode()


def crear_procesador() -> tuple[ProcesadorRFID, BackendFalso]:
    backend = BackendFalso()
    almacen = AlmacenProcesamientos(max_registros=20, ttl_deduplicacion=600)
    return (
        ProcesadorRFID(
            backend=backend,  # type: ignore[arg-type]
            almacen=almacen,
            max_payload_bytes=512,
        ),
        backend,
    )


def test_identifica_contenedor_sin_generar_operacion() -> None:
    procesador, backend = crear_procesador()

    resultado = procesador.procesar(mensaje())

    assert resultado.estado == EstadoProcesamiento.VALIDO
    assert resultado.codigo_contenedor == "CONT123"
    assert resultado.contenedor_id == 42
    assert "ningún cambio operacional" in resultado.detalle
    assert backend.consultas == 1


def test_distingue_codigo_desconocido_y_evento_duplicado() -> None:
    procesador, backend = crear_procesador()
    evento_id = str(uuid4())

    desconocido = procesador.procesar(
        mensaje(evento_id=evento_id, codigo="NOEXISTE")
    )
    duplicado = procesador.procesar(
        mensaje(evento_id=evento_id, codigo="NOEXISTE")
    )

    assert desconocido.estado == EstadoProcesamiento.DESCONOCIDO
    assert duplicado.estado == EstadoProcesamiento.DUPLICADO
    assert backend.consultas == 1


def test_rechaza_json_invalido_campos_extra_fecha_no_utc_y_payload_grande() -> None:
    procesador, backend = crear_procesador()
    con_extra = json.loads(mensaje())
    con_extra["estado"] = "en_patio"
    fecha_local = json.loads(mensaje())
    fecha_local["fecha_utc"] = "2026-10-19T09:00:00-03:00"

    resultados = [
        procesador.procesar(b"no-json"),
        procesador.procesar(json.dumps(con_extra).encode()),
        procesador.procesar(json.dumps(fecha_local).encode()),
        procesador.procesar(b"x" * 513),
    ]

    assert all(
        item.estado == EstadoProcesamiento.INVALIDO for item in resultados
    )
    assert backend.consultas == 0


def test_error_transitorio_libera_evento_para_reintento() -> None:
    procesador, backend = crear_procesador()
    evento_id = str(uuid4())
    payload = mensaje(evento_id=evento_id)
    backend.fallar = True

    error = procesador.procesar(payload)
    backend.fallar = False
    reintento = procesador.procesar(payload)

    assert error.estado == EstadoProcesamiento.ERROR
    assert reintento.estado == EstadoProcesamiento.VALIDO
    assert backend.consultas == 2
