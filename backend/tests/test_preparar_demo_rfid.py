import sys

import pytest

from postgres_test_safety import DestinoPostgresInseguro
from scripts.preparar_demo_rfid import main


URL_PRUEBAS = (
    "postgresql+psycopg://usuario_pruebas:clave@localhost:55432/"
    "puertotrack_integration_test"
)


def test_preparacion_rfid_rechaza_falta_de_confirmacion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PUERTOTRACK_TEST_DATABASE_URL", URL_PRUEBAS)
    monkeypatch.delenv("PUERTOTRACK_RUN_POSTGRES_TESTS", raising=False)
    monkeypatch.setattr(sys, "argv", ["preparar_demo_rfid"])

    with pytest.raises(DestinoPostgresInseguro):
        main()


def test_preparacion_rfid_rechaza_destino_habitual(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "PUERTOTRACK_RUN_POSTGRES_TESTS",
        "PUERTOTRACK_POSTGRES_TEST_ONLY",
    )
    monkeypatch.setenv(
        "PUERTOTRACK_TEST_DATABASE_URL",
        "postgresql+psycopg://usuario:clave@localhost:5432/puertotrack",
    )
    monkeypatch.setattr(sys, "argv", ["preparar_demo_rfid"])

    with pytest.raises(DestinoPostgresInseguro):
        main()


def test_preparacion_rfid_valida_codigo_antes_de_conectarse(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "PUERTOTRACK_RUN_POSTGRES_TESTS",
        "PUERTOTRACK_POSTGRES_TEST_ONLY",
    )
    monkeypatch.setenv("PUERTOTRACK_TEST_DATABASE_URL", URL_PRUEBAS)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(
        sys,
        "argv",
        ["preparar_demo_rfid", "--crear-contenedor", "código inválido"],
    )

    with pytest.raises(ValueError):
        main()


def test_preparacion_rfid_no_permite_crear_y_capturar_a_la_vez(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "preparar_demo_rfid",
            "--crear-contenedor",
            "RFIDTEST",
            "--snapshot-contenedor",
            "RFIDTEST",
        ],
    )

    with pytest.raises(SystemExit):
        main()
