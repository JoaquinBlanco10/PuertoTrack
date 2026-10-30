import json
import logging
from threading import Event
from typing import Any

from .config import Configuracion
from .processor import ProcesadorAccesos


logger = logging.getLogger("puertotrack.access.mqtt")


class ConsumidorMQTT:
    def __init__(
        self, configuracion: Configuracion, procesador: ProcesadorAccesos
    ) -> None:
        self._config = configuracion
        self._procesador = procesador
        self._cliente: Any | None = None
        self._conectado = Event()

    @property
    def conectado(self) -> bool:
        return self._conectado.is_set()

    def iniciar(self) -> None:
        import paho.mqtt.client as mqtt

        cliente = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=self._config.mqtt_client_id,
            protocol=mqtt.MQTTv311,
        )
        cliente.on_connect = self._al_conectar
        cliente.on_disconnect = self._al_desconectar
        cliente.on_message = self._al_recibir
        cliente.connect_async(
            self._config.mqtt_host,
            self._config.mqtt_port,
            keepalive=30,
        )
        cliente.loop_start()
        self._cliente = cliente

    def detener(self) -> None:
        if self._cliente is not None:
            self._cliente.disconnect()
            self._cliente.loop_stop()
            self._cliente = None
        self._conectado.clear()

    def _al_conectar(
        self, cliente: Any, userdata: Any, flags: Any,
        reason_code: Any, properties: Any
    ) -> None:
        if getattr(reason_code, "is_failure", False):
            logger.error(json.dumps({"evento": "mqtt_conexion_fallida"}))
            return
        cliente.subscribe(self._config.input_topic, qos=1)
        self._conectado.set()
        logger.info(json.dumps({"evento": "mqtt_accesos_conectado"}))

    def _al_desconectar(self, *args: Any) -> None:
        self._conectado.clear()

    def _al_recibir(self, cliente: Any, userdata: Any, mensaje: Any) -> None:
        try:
            decision = self._procesador.procesar(mensaje.payload)
            if decision is not None:
                publicacion = cliente.publish(
                    self._config.output_topic,
                    decision.model_dump_json(),
                    qos=1,
                )
                if getattr(publicacion, "rc", 0) != 0:
                    logger.error(
                        json.dumps(
                            {
                                "evento": "resultado_acceso_no_publicado",
                                "evento_id": str(decision.evento_id),
                            }
                        )
                    )
        except Exception:
            logger.exception(json.dumps({"evento": "mqtt_error_no_controlado"}))
