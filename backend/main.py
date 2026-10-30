import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from access_internal import router as access_internal_router
from accesos import router as accesos_router
from auditoria import router as auditoria_router
from auth import router as auth_router
from contenedores import router as contenedores_router
from database import comprobar_conexion
from dashboard import router as dashboard_router
from movimientos import router as movimientos_router
from rfid_internal import router as rfid_internal_router
from security import validar_configuracion_seguridad
from ubicaciones import router as ubicaciones_router


@asynccontextmanager
async def ciclo_vida(_: FastAPI) -> AsyncIterator[None]:
    validar_configuracion_seguridad()
    yield


app = FastAPI(
    title="PuertoTrack API",
    description="Sistema de Gestión Logística Portuaria",
    version="0.1.0",
    lifespan=ciclo_vida,
)

FRONTEND_ORIGIN = os.getenv(
    "FRONTEND_ORIGIN", "http://localhost:5173"
).rstrip("/")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth_router)
app.include_router(contenedores_router)
app.include_router(movimientos_router)
app.include_router(auditoria_router)
app.include_router(ubicaciones_router)
app.include_router(dashboard_router)
app.include_router(rfid_internal_router)
app.include_router(access_internal_router)
app.include_router(accesos_router)


@app.exception_handler(RequestValidationError)
async def manejar_error_validacion(
    request: Request, error: RequestValidationError
):
    if request.url.path.startswith(
        ("/contenedores", "/movimientos", "/ubicaciones")
    ):
        entidad = (
            "movimiento"
            if request.url.path.startswith("/movimientos")
            else "ubicación"
            if request.url.path.startswith("/ubicaciones")
            else "contenedor"
        )
        return JSONResponse(
            status_code=400,
            content={
                "detail": f"Datos de {entidad} inválidos",
                "errors": jsonable_encoder(error.errors()),
            },
        )
    return await request_validation_exception_handler(request, error)


@app.get("/")
def inicio():
    return {
        "sistema": "PuertoTrack",
        "mensaje": "Backend funcionando correctamente"
    }


@app.get("/health")
def verificar_estado():
    return {
        "estado": "ok"
    }


@app.get("/health/database", tags=["Sistema"])
def verificar_base_de_datos():
    try:
        comprobar_conexion()
        return {"base_de_datos": "conectada"}
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="No se pudo conectar a la base de datos"
        )

