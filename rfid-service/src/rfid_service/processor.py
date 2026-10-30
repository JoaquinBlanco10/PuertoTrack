import json
import logging
from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import ValidationError

from .backend_client import (
    ClienteBackend,
    CodigoContenedorDesconocido,
    ErrorBackendOperacional,
)
from .contracts import DeteccionRFID, EstadoProcesamiento, ProcesamientoRFID
from .state import AlmacenProcesamientos


logger = logging.getLogger("puertotrack.rfid")


class ProcesadorRFID:
    def __init__(
        self,
        *,
        backend: ClienteBackend,
        almacen: AlmacenProcesamientos,
        max_payload_bytes: int,
    ) -> None:
        self._backend = backend
        self._almacen = almacen
        self._max_payload_bytes = max_payload_bytes

    def procesar(self, payload: bytes) -> ProcesamientoRFID:
        if len(payload) > self._max_payload_bytes:
            return self._registrar(
                self._resultado_invalido("El mensaje supera el límite permitido.")
            )
        try:
            deteccion = DeteccionRFID.model_validate_json(payload)
        except (ValidationError, ValueError):
            return self._registrar(
                self._resultado_invalido("El mensaje JSON no cumple el contrato RFID.")
            )

        evento_id = str(deteccion.evento_id)
        if not self._almacen.reservar_evento(evento_id):
            return self._registrar(
                self._resultado(
                    deteccion,
                    EstadoProcesamiento.DUPLICADO,
                    "El evento ya fue procesado dentro de la ventana de deduplicación.",
                )
            )

        try:
            contenedor = self._backend.identificar(deteccion.codigo_contenedor)
        except CodigoContenedorDesconocido:
            resultado = self._resultado(
                deteccion,
                EstadoProcesamiento.DESCONOCIDO,
                "El código no corresponde a un contenedor registrado.",
            )
        except ErrorBackendOperacional:
            self._almacen.liberar_evento(evento_id)
            resultado = self._resultado(
                deteccion,
                EstadoProcesamiento.ERROR,
                "No fue posible validar el contenedor en el backend.",
            )
        else:
            resultado = self._resultado(
                deteccion,
                EstadoProcesamiento.VALIDO,
                "Contenedor identificado; no se realizó ningún cambio operacional.",
                contenedor_id=contenedor.id,
            )
        return self._registrar(resultado)

    def _resultado(
        self,
        deteccion: DeteccionRFID,
        estado: EstadoProcesamiento,
        detalle: str,
        *,
        contenedor_id: int | None = None,
    ) -> ProcesamientoRFID:
        return ProcesamientoRFID(
            procesamiento_id=uuid4(),
            evento_id=deteccion.evento_id,
            codigo_contenedor=deteccion.codigo_contenedor,
            lector=deteccion.lector,
            fecha_evento=deteccion.fecha_utc,
            recibido_en=datetime.now(timezone.utc),
            estado=estado,
            detalle=detalle,
            contenedor_id=contenedor_id,
        )

    def _resultado_invalido(self, detalle: str) -> ProcesamientoRFID:
        return ProcesamientoRFID(
            procesamiento_id=uuid4(),
            evento_id=None,
            codigo_contenedor=None,
            lector=None,
            fecha_evento=None,
            recibido_en=datetime.now(timezone.utc),
            estado=EstadoProcesamiento.INVALIDO,
            detalle=detalle,
        )

    def _registrar(self, resultado: ProcesamientoRFID) -> ProcesamientoRFID:
        self._almacen.registrar(resultado)
        logger.info(
            json.dumps(
                {
                    "evento": "rfid_procesado",
                    "procesamiento_id": str(resultado.procesamiento_id),
                    "evento_id": str(resultado.evento_id)
                    if resultado.evento_id
                    else None,
                    "codigo_contenedor": resultado.codigo_contenedor,
                    "lector": resultado.lector,
                    "estado": resultado.estado.value,
                },
                ensure_ascii=False,
            )
        )
        return resultado
