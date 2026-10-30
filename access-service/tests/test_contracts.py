import json
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from access_service.contracts import IdentificacionRFID


def datos_validos() -> dict:
    return {
        "version": 1,
        "evento_id": str(uuid4()),
        "codigo_contenedor": "cont123",
        "contenedor_id": 7,
        "lector": "PORTICO_NORTE",
        "fecha_utc": datetime.now(timezone.utc).isoformat(),
        "identificado_en": datetime.now(timezone.utc).isoformat(),
        "resultado_identificacion": "valido",
    }


def test_contrato_versionado_normaliza_codigo() -> None:
    contrato = IdentificacionRFID.model_validate(datos_validos())

    assert contrato.version == 1
    assert contrato.codigo_contenedor == "CONT123"


@pytest.mark.parametrize(
    "cambio",
    [
        {"version": 2},
        {"fecha_utc": "2026-10-19T09:00:00-03:00"},
        {"campo_extra": True},
    ],
)
def test_rechaza_version_fecha_o_campos_incompatibles(cambio: dict) -> None:
    datos = datos_validos()
    datos.update(cambio)

    with pytest.raises(ValidationError):
        IdentificacionRFID.model_validate_json(json.dumps(datos))
