import hmac
from contextlib import asynccontextmanager
from typing import Annotated, AsyncIterator
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status

from .backend_client import ClienteBackend
from .config import Configuracion
from .contracts import DecisionAcceso, ResultadoAcceso, ResumenSalud
from .mqtt_consumer import ConsumidorMQTT
from .policy import PoliticaHabilitacionOperacional
from .processor import ProcesadorAccesos
from .state import AlmacenDecisiones


def crear_app(
    *, configuracion: Configuracion | None = None, iniciar_mqtt: bool = True
) -> FastAPI:
    config = configuracion or Configuracion.desde_entorno()
    almacen = AlmacenDecisiones(
        max_decisiones=config.max_decisions,
        ttl_deduplicacion=config.dedup_ttl_seconds,
        ttl_decisiones=config.decision_ttl_seconds,
    )

    @asynccontextmanager
    async def ciclo_vida(app: FastAPI) -> AsyncIterator[None]:
        backend = ClienteBackend(
            api_url=config.api_url,
            clave_interna=config.clave_interna,
            timeout=config.backend_timeout_seconds,
        )
        procesador = ProcesadorAccesos(
            backend=backend,
            almacen=almacen,
            politica=PoliticaHabilitacionOperacional(),
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
        title="PuertoTrack Access Service",
        description="Habilitación operacional preliminar; no abre barreras.",
        version="0.1.0",
        lifespan=ciclo_vida,
    )
    app.state.almacen = almacen
    app.state.consumidor = None

    def autenticar(
        clave: Annotated[
            str | None, Header(alias="X-PuertoTrack-Access-Key")
        ] = None,
    ) -> None:
        if clave is None or not hmac.compare_digest(
            clave, config.clave_interna
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credencial interna inválida.",
            )

    @app.get("/health", response_model=ResumenSalud)
    def health() -> ResumenSalud:
        cantidad, duplicados, invalidos, por_resultado = almacen.resumen()
        consumidor = app.state.consumidor
        return ResumenSalud(
            mqtt_conectado=bool(consumidor and consumidor.conectado),
            decisiones_conservadas=cantidad,
            duplicados_ignorados=duplicados,
            mensajes_invalidos=invalidos,
            por_resultado=por_resultado,
        )

    @app.get(
        "/internal/decisiones",
        response_model=list[DecisionAcceso],
        dependencies=[Depends(autenticar)],
    )
    def listar_decisiones(
        limite: int = Query(default=50, ge=1, le=100),
        resultado: ResultadoAcceso | None = None,
    ) -> list[DecisionAcceso]:
        return almacen.listar(limite=limite, resultado=resultado)

    @app.get(
        "/internal/decisiones/{evento_id}",
        response_model=DecisionAcceso,
        dependencies=[Depends(autenticar)],
    )
    def buscar_decision(
        evento_id: UUID,
    ) -> DecisionAcceso:
        decision = almacen.buscar_evento(str(evento_id))
        if decision is None:
            raise HTTPException(status_code=404, detail="Decisión no encontrada.")
        return decision

    return app
