from sqlalchemy import event
from sqlalchemy.orm import Session

from models import Contenedor, Movimiento, Ubicacion, Usuario
from repositories import (
    ContenedorRepository,
    MovimientoRepository,
    UsuarioRepository,
)


def crear_usuario(
    repository: UsuarioRepository,
    email: str = "operador@puertotrack.test",
) -> Usuario:
    return repository.crear(
        Usuario(
            nombre="Operador de prueba",
            email=email,
            password_hash="hash-de-prueba",
            rol="operador",
        )
    )


def crear_contenedor(
    repository: ContenedorRepository,
    codigo: str = "MSCU1234567",
) -> Contenedor:
    return repository.crear(
        Contenedor(
            codigo=codigo,
            ubicacion_actual="Patio A",
            estado="en_patio",
        )
    )


def test_repositorio_usuario_crea_busca_y_lista(session_prueba: Session) -> None:
    repository = UsuarioRepository(session_prueba)
    usuario = crear_usuario(repository)
    otro = crear_usuario(repository, "supervisor@puertotrack.test")

    assert usuario.id is not None
    assert usuario.fecha_creacion is not None
    assert repository.buscar_por_id(usuario.id) is usuario
    assert repository.buscar_por_email(usuario.email) is usuario
    assert repository.buscar_por_email("inexistente@puertotrack.test") is None
    assert repository.listar() == [usuario, otro]
    assert repository.listar(offset=1, limite=1) == [otro]


def test_repositorio_contenedor_crea_busca_y_lista(
    session_prueba: Session,
) -> None:
    repository = ContenedorRepository(session_prueba)
    contenedor = crear_contenedor(repository)

    assert contenedor.id is not None
    assert contenedor.fecha_creacion is not None
    assert contenedor.fecha_actualizacion is not None
    assert repository.buscar_por_id(contenedor.id) is contenedor
    assert repository.buscar_por_codigo(contenedor.codigo) is contenedor
    assert repository.buscar_por_codigo("CODIGO-INEXISTENTE") is None
    assert repository.listar() == [contenedor]


def test_repositorio_movimiento_consulta_por_contenedor_y_usuario(
    session_prueba: Session,
) -> None:
    usuarios = UsuarioRepository(session_prueba)
    contenedores = ContenedorRepository(session_prueba)
    movimientos = MovimientoRepository(session_prueba)

    usuario_uno = crear_usuario(usuarios)
    usuario_dos = crear_usuario(usuarios, "segundo@puertotrack.test")
    contenedor_uno = crear_contenedor(contenedores)
    contenedor_dos = crear_contenedor(contenedores, "TGHU7654321")

    movimiento_uno = movimientos.crear(
        Movimiento(
            contenedor_id=contenedor_uno.id,
            usuario_id=usuario_uno.id,
            ubicacion_origen="Muelle 1",
            ubicacion_destino="Patio A",
        )
    )
    movimiento_dos = movimientos.crear(
        Movimiento(
            contenedor_id=contenedor_uno.id,
            usuario_id=usuario_dos.id,
            ubicacion_origen="Patio A",
            ubicacion_destino="Patio B",
            observacion="Reubicación operativa",
        )
    )
    movimiento_tres = movimientos.crear(
        Movimiento(
            contenedor_id=contenedor_dos.id,
            usuario_id=usuario_uno.id,
            ubicacion_origen="Muelle 2",
            ubicacion_destino="Patio C",
        )
    )

    assert movimientos.buscar_por_id(movimiento_uno.id) is movimiento_uno
    assert movimientos.listar() == [
        movimiento_uno,
        movimiento_dos,
        movimiento_tres,
    ]
    assert movimientos.buscar_por_contenedor(contenedor_uno.id) == [
        movimiento_uno,
        movimiento_dos,
    ]
    assert movimientos.buscar_por_usuario(usuario_uno.id) == [
        movimiento_uno,
        movimiento_tres,
    ]
    assert movimientos.buscar_por_contenedor(9999) == []
    assert movimientos.buscar_por_usuario(9999) == []


def test_listar_contenedores_carga_catalogo_sin_n_mas_uno(
    session_prueba: Session,
) -> None:
    ubicaciones = [
        Ubicacion(
            codigo=f"PATIO_{indice}",
            nombre=f"Patio vigente {indice}",
            tipo="interna",
            activo=True,
        )
        for indice in range(3)
    ]
    session_prueba.add_all(ubicaciones)
    session_prueba.flush()
    session_prueba.add_all(
        [
            Contenedor(
                codigo=f"MSCU12345{indice:02d}",
                ubicacion_actual=f"Snapshot {indice}",
                ubicacion_actual_id=ubicacion.id,
                estado="en_patio",
            )
            for indice, ubicacion in enumerate(ubicaciones)
        ]
    )
    session_prueba.commit()
    session_prueba.expunge_all()

    sentencias_select: list[str] = []

    def registrar_select(
        connection, cursor, statement, parameters, context, executemany
    ) -> None:
        if statement.lstrip().lower().startswith("select"):
            sentencias_select.append(statement.lower())

    motor = session_prueba.get_bind()
    event.listen(motor, "before_cursor_execute", registrar_select)
    try:
        contenedores = ContenedorRepository(session_prueba).listar()
        consultas_tras_listar = len(sentencias_select)
        nombres = [contenedor.ubicacion_actual for contenedor in contenedores]
    finally:
        event.remove(motor, "before_cursor_execute", registrar_select)

    assert nombres == [
        "Patio vigente 0",
        "Patio vigente 1",
        "Patio vigente 2",
    ]
    assert len(sentencias_select) == consultas_tras_listar
    assert sum("from ubicaciones" in sql for sql in sentencias_select) == 1
