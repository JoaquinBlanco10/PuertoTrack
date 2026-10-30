import pytest

from scripts.verificar_datos_demo import (
    CONTENEDORES_DEMO,
    UBICACIONES_DEMO,
    USUARIOS_DEMO,
    _exigir_preparada,
    _exigir_vacia,
)


def test_exige_una_base_vacia_antes_de_preparar_la_demo() -> None:
    vacia = {
        "conteos": {
            "usuarios": 0,
            "ubicaciones": 0,
            "contenedores": 0,
            "movimientos": 0,
            "audit_logs": 0,
        }
    }
    _exigir_vacia(vacia)
    vacia["conteos"]["ubicaciones"] = 1
    with pytest.raises(RuntimeError):
        _exigir_vacia(vacia)


def test_exige_exclusivamente_los_fixtures_de_la_demo() -> None:
    preparada = {
        "conteos": {
            "usuarios": 2,
            "ubicaciones": 6,
            "contenedores": 5,
            "movimientos": 6,
            "audit_logs": 18,
        },
        "usuarios": set(USUARIOS_DEMO),
        "ubicaciones": dict(UBICACIONES_DEMO),
        "contenedores": set(CONTENEDORES_DEMO),
    }
    _exigir_preparada(preparada)
    preparada["ubicaciones"]["INT_RESIDUAL"] = (
        "Patio rollback residual",
        "interna",
        True,
    )
    with pytest.raises(RuntimeError):
        _exigir_preparada(preparada)
