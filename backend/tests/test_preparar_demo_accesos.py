import pytest

from scripts.preparar_demo_accesos import _credencial, _email


def test_credenciales_demo_exigen_entorno_y_dominio_aislado(monkeypatch) -> None:
    monkeypatch.delenv("PUERTOTRACK_TEST_PASSWORD", raising=False)
    with pytest.raises(ValueError):
        _credencial("PUERTOTRACK_TEST_PASSWORD")

    monkeypatch.setenv("PUERTOTRACK_TEST_EMAIL", "admin@empresa.cl")
    with pytest.raises(ValueError):
        _email("PUERTOTRACK_TEST_EMAIL")

    monkeypatch.setenv(
        "PUERTOTRACK_TEST_EMAIL", "Supervisor.Demo@puertotrack.test"
    )
    assert _email("PUERTOTRACK_TEST_EMAIL") == (
        "supervisor.demo@puertotrack.test"
    )
