import json
import logging
from threading import Event
from typing import Any

from .config import Configuracion
from .contracts import DeteccionRFID, crear_identificacion
from .processor import ProcesadorRFID


logger = logging.getLogger("puertotrack.rfid.mqtt")


class MQTTNoDisponible(RuntimeError):
    pass


class PublicacionMQTTFallida(RuntimeError):
    pass


class ConsumidorMQTT:
    def __init__(
        self,
        configuracion: Configuracion,
        procesador: ProcesadorRFID,
    ) -> None:
        self._configuracion = configuracion
        self._procesador = procesador
        self._cliente: Any | None = None
        self._conectado = Event()

    @property
    def conectado(self) -> bool:
        return self._conectado.is_set()

    def iniciar(self) -> None:
        # Importación diferida: permite probar contrato y procesamiento sin
        # instalar ni iniciar infraestructura MQTT.
        import paho.mqtt.client as mqtt

        cliente = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=self._configuracion.mqtt_client_id,
            protocol=mqtt.MQTTv311,
        )
        cliente.on_connect = self._al_conectar
        cliente.on_disconnect = self._al_desconectar
        cliente.on_message = self._al_recibir
        cliente.connect_async(
            self._configuracion.mqtt_host,
            self._configuracion.mqtt_port,
            keepalive=30,
        )
        cliente.loop_start()
        self._cliente = cliente
        logger.info(
            json.dumps(
                {
                    "evento": "mqtt_iniciando",
                    "host": self._configuracion.mqtt_host,
                    "puerto": self._configuracion.mqtt_port,
                    "topic": self._configuracion.mqtt_topic,
                }
            )
        )

    def detener(self) -> None:
        cliente = self._cliente
        if cliente is None:
            return
        cliente.disconnect()
        cliente.loop_stop()
        self._cliente = None
        self._conectado.clear()

    def publicar_deteccion(self, deteccion: DeteccionRFID) -> None:
        """Publica una detección y espera la confirmación QoS 1 del broker."""

        cliente = self._cliente
        if cliente is None or not self.conectado:
            raise MQTTNoDisponible("El broker MQTT no está conectado.")
        try:
            publicacion = cliente.publish(
                self._configuracion.mqtt_topic,
                deteccion.model_dump_json(),
                qos=1,
                retain=False,
            )
            if getattr(publicacion, "rc", 1) != 0:
                raise PublicacionMQTTFallida(
                    "El broker rechazó la publicación MQTT."
                )
            publicacion.wait_for_publish(timeout=5)
            if not publicacion.is_published():
                raise PublicacionMQTTFallida(
                    "El broker no confirmó la publicación MQTT."
                )
        except PublicacionMQTTFallida:
            raise
        except Exception as error:
            raise PublicacionMQTTFallida(
                "No fue posible confirmar la publicación MQTT."
            ) from error

    def _al_conectar(
        self,
        cliente: Any,
        userdata: Any,
        flags: Any,
        reason_code: Any,
        properties: Any,
    ) -> None:
        if getattr(reason_code, "is_failure", False):
            logger.error(
                json.dumps(
                    {"evento": "mqtt_conexion_fallida", "codigo": str(reason_code)}
                )
            )
            return
        cliente.subscribe(self._configuracion.mqtt_topic, qos=1)
        self._conectado.set()
        logger.info(json.dumps({"evento": "mqtt_conectado"}))

    def _al_desconectar(self, *args: Any) -> None:
        self._conectado.clear()
        logger.warning(json.dumps({"evento": "mqtt_desconectado"}))

    def _al_recibir(self, cliente: Any, userdata: Any, mensaje: Any) -> None:
        try:
            resultado = self._procesador.procesar(mensaje.payload)
            identificacion = crear_identificacion(resultado)
            if identificacion is not None:
                publicacion = cliente.publish(
                    self._configuracion.mqtt_identifications_topic,
                    identificacion.model_dump_json(),
                    qos=1,
                )
                if getattr(publicacion, "rc", 0) != 0:
                    logger.error(
                        json.dumps(
                            {
                                "evento": "mqtt_identificacion_no_publicada",
                                "evento_id": str(identificacion.evento_id),
                            }
                        )
                    )
        except Exception:
            # El callback no debe finalizar el loop MQTT. No se registra el
            # payload ni información de configuración.
            logger.exception(json.dumps({"evento": "mqtt_error_no_controlado"}))
