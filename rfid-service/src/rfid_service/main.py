import logging

from .app import crear_app


logging.basicConfig(level=logging.INFO, format="%(message)s")
app = crear_app()
