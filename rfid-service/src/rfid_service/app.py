import hmac
from contextlib import asynccontextmanager
from typing import Annotated, AsyncIterator
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status

from .backend_client import ClienteBackend
from .config import Configuracion
from .contracts import (
    DeteccionAceptada,
    DeteccionRFID,
    EstadoProcesamiento,
    ProcesamientoRFID,
    ResumenEstado,
)
from .mqtt_consumer import (
    ConsumidorMQTT,
    MQTTNoDisponible,
    PublicacionMQTTFallida,
)
from .processor import ProcesadorRFID
from .state import AlmacenProcesamientos


def crear_app(
    *,
    configuracion: Configuracion | None = None,
    iniciar_mqtt: bool = True,
) -> FastAPI:
    config = configuracion or Configuracion.desde_entorno()
    almacen = AlmacenProcesamientos(
        max_registros=config.max_processing_records,
        ttl_deduplicacion=config.dedup_ttl_seconds,
    )

    @asynccontextmanager
    async def ciclo_vida(app: FastAPI) -> AsyncIterator[None]:
        backend = ClienteBackend(
            api_url=config.api_url,
            clave_interna=config.clave_interna,
            timeout=config.backend_timeout_seconds,
        )
        procesador = ProcesadorRFID(
            backend=backend,
            almacen=almacen,
            max_payload_bytes=config.max_payload_bytes,
        )
        consumidor = ConsumidorMQTT(config, procesador)
        app.state.consumidor = consumidor
        if iniciar_mqtt:
            consumidor.iniciar()
        try:
            yield
        finally:
            consumidor.detener()
            backend.cerrar()

    app = FastAPI(
        title="PuertoTrack RFID Service",
        description=(
            "Procesa detecciones RFID simuladas sin modificar datos operacionales."
        ),
        version="0.1.0",
        lifespan=ciclo_vida,
    )
    app.state.almacen = almacen
    app.state.consumidor = None

    def autenticar_dispositivo(
        clave_recibida: Annotated[
            str | None,
            Header(alias="X-PuertoTrack-Device-Key"),
        ] = None,
    ) -> None:
        clave_configurada = config.clave_dispositivo
        if len(clave_configurada.encode("utf-8")) < 32:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="El ingreso desde dispositivos no está configurado.",
            )
        if clave_recibida is None or not hmac.compare_digest(
            clave_recibida,
            clave_configurada,
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credencial de dispositivo inválida.",
            )

    @app.get("/health")
    def health() -> ResumenEstado:
        cantidad, por_estado = almacen.resumen()
        consumidor = app.state.consumidor
        return ResumenEstado(
            mqtt_conectado=bool(consumidor and consumidor.conectado),
            procesamientos_conservados=cantidad,
            por_estado=por_estado,
        )

    @app.post(
        "/detecciones",
        response_model=DeteccionAceptada,
        status_code=status.HTTP_202_ACCEPTED,
        dependencies=[Depends(autenticar_dispositivo)],
    )
    def recibir_deteccion(deteccion: DeteccionRFID) -> DeteccionAceptada:
        consumidor = app.state.consumidor
        if consumidor is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="El publicador MQTT no está disponible.",
            )
        try:
            consumidor.publicar_deteccion(deteccion)
        except (MQTTNoDisponible, PublicacionMQTTFallida) as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No fue posible confirmar la detección con el broker MQTT.",
            ) from error
        return DeteccionAceptada(evento_id=deteccion.evento_id)

    @app.get("/procesamientos", response_model=list[ProcesamientoRFID])
    def listar_procesamientos(
        limite: int = Query(default=50, ge=1, le=100),
        estado: EstadoProcesamiento | None = None,
    ) -> list[ProcesamientoRFID]:
        return almacen.listar(limite=limite, estado=estado)

    @app.get("/procesamientos/{evento_id}", response_model=ProcesamientoRFID)
    def buscar_procesamiento(evento_id: UUID) -> ProcesamientoRFID:
        resultado = almacen.buscar_evento(str(evento_id))
        if resultado is None:
            raise HTTPException(status_code=404, detail="Evento no encontrado.")
        return resultado

    return app
