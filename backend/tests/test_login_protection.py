from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from login_protection import LimitadorLogin


def test_limitador_expira_la_ventana_y_controla_email_e_ip() -> None:
    instante = [100.0]
    limitador = LimitadorLogin(
        ventana_segundos=60,
        max_fallos_email=2,
        max_fallos_ip=3,
        reloj=lambda: instante[0],
    )

    limitador.registrar_fallo(email="uno@test", ip="127.0.0.1")
    limitador.registrar_fallo(email="uno@test", ip="127.0.0.1")
    assert (
        limitador.segundos_para_reintentar(
            email="uno@test", ip="otra-ip"
        )
        == 60
    )

    limitador.registrar_fallo(email="dos@test", ip="127.0.0.1")
    assert (
        limitador.segundos_para_reintentar(
            email="sin-fallos@test", ip="127.0.0.1"
        )
        == 60
    )

    instante[0] = 161.0
    assert (
        limitador.segundos_para_reintentar(
            email="uno@test", ip="127.0.0.1"
        )
        == 0
    )


def test_limitador_reserva_capacidad_de_forma_atomica() -> None:
    participantes = 12
    barrera = Barrier(participantes)
    limitador = LimitadorLogin(
        ventana_segundos=60,
        max_fallos_email=3,
        max_fallos_ip=20,
        reloj=lambda: 100.0,
    )

    def intentar() -> int:
        barrera.wait()
        return limitador.iniciar_intento(
            email="concurrente@test", ip="127.0.0.1"
        )

    with ThreadPoolExecutor(max_workers=participantes) as ejecutor:
        resultados = list(ejecutor.map(lambda _: intentar(), range(participantes)))

    assert resultados.count(0) == 3
    assert resultados.count(1) == participantes - 3

    for _ in range(3):
        limitador.cancelar_intento(
            email="concurrente@test", ip="127.0.0.1"
        )
    assert limitador.segundos_para_reintentar(
        email="concurrente@test", ip="127.0.0.1"
    ) == 0
