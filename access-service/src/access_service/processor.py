import json
import logging
from datetime import datetime, timezone
from uuid import uuid4

from pydantic import ValidationError

from .backend_client import (
    BackendNoDisponible,
    ClienteBackend,
    ContenedorDesconocido,
)
from .contracts import (
    DecisionAcceso,
    IdentificacionRFID,
    ResultadoAcceso,
    ResultadoIdentificacion,
)
from .policy import PoliticaHabilitacionOperacional
from .state import AlmacenDecisiones


logger = logging.getLogger("puertotrack.access")


class ProcesadorAccesos:
    def __init__(
        self,
        *,
        backend: ClienteBackend,
        almacen: AlmacenDecisiones,
        politica: PoliticaHabilitacionOperacional,
        max_payload_bytes: int,
    ) -> None:
        self._backend = backend
        self._almacen = almacen
        self._politica = politica
        self._max_payload_bytes = max_payload_bytes

    def procesar(self, payload: bytes) -> DecisionAcceso | None:
        if len(payload) > self._max_payload_bytes:
            self._almacen.registrar_invalido()
            return None
        try:
            identificacion = IdentificacionRFID.model_validate_json(payload)
        except (ValidationError, ValueError):
            self._almacen.registrar_invalido()
            return None
        if not self._almacen.reservar_evento(str(identificacion.evento_id)):
            return None

        if (
            identificacion.resultado_identificacion
            == ResultadoIdentificacion.DESCONOCIDO
        ):
            decision = self._crear_decision(
                identificacion,
                resultado=ResultadoAcceso.DENEGADO,
                motivo="CODIGO_DESCONOCIDO",
                contenedor_id=None,
            )
        else:
            try:
                hechos = self._backend.consultar_hechos(
                    identificacion.codigo_contenedor
                )
            except ContenedorDesconocido:
                decision = self._crear_decision(
                    identificacion,
                    resultado=ResultadoAcceso.DENEGADO,
                    motivo="CODIGO_DESCONOCIDO",
                    contenedor_id=None,
                )
            except BackendNoDisponible:
                decision = self._crear_decision(
                    identificacion,
                    resultado=ResultadoAcceso.NO_DETERMINADO,
                    motivo="BACKEND_NO_DISPONIBLE",
                    contenedor_id=identificacion.contenedor_id,
                )
            else:
                evaluacion = self._politica.evaluar(hechos)
                decision = self._crear_decision(
                    identificacion,
                    resultado=evaluacion.resultado,
                    motivo=evaluacion.motivo,
                    contenedor_id=hechos.id,
                )
        self._almacen.registrar(decision)
        logger.info(
            json.dumps(
                {
                    "evento": "acceso_evaluado",
                    "evento_id": str(decision.evento_id),
                    "decision_id": str(decision.decision_id),
                    "codigo_contenedor": decision.codigo_contenedor,
                    "resultado": decision.resultado.value,
                    "motivo": decision.motivo,
                },
                ensure_ascii=False,
            )
        )
        return decision

    @staticmethod
    def _crear_decision(
        identificacion: IdentificacionRFID,
        *,
        resultado: ResultadoAcceso,
        motivo: str,
        contenedor_id: int | None,
    ) -> DecisionAcceso:
        return DecisionAcceso(
            decision_id=uuid4(),
            evento_id=identificacion.evento_id,
            codigo_contenedor=identificacion.codigo_contenedor,
            contenedor_id=contenedor_id,
            lector=identificacion.lector,
            fecha_evento=identificacion.fecha_utc,
            resultado=resultado,
            motivo=motivo,
            fecha_decision=datetime.now(timezone.utc),
        )
