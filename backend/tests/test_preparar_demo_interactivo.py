import pytest

from scripts.preparar_demo_interactivo import (
    CODIGOS_CONTENEDORES_DEMO,
    NOMBRE_SUPERVISOR_DEMO,
    _leer_password,
)


def test_catalogo_demo_es_estable_y_las_claves_no_tienen_fallback(
    monkeypatch,
) -> None:
    assert "DEMOENTRADA" in CODIGOS_CONTENEDORES_DEMO
    assert "DEMOTRASLADO" in CODIGOS_CONTENEDORES_DEMO
    assert len(set(CODIGOS_CONTENEDORES_DEMO)) == len(
        CODIGOS_CONTENEDORES_DEMO
    )
    assert NOMBRE_SUPERVISOR_DEMO == "Supervisor Demo"

    monkeypatch.delenv("PUERTOTRACK_DEMO_PASSWORD", raising=False)
    with pytest.raises(ValueError):
        _leer_password("PUERTOTRACK_DEMO_PASSWORD")
