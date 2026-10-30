import argparse
import json
import os
from datetime import datetime, timezone
from time import sleep
from uuid import UUID, uuid4


def crear_mensaje_simulado(
    codigo: str,
    lector: str,
    evento_id: UUID | None = None,
) -> dict[str, str]:
    return {
        "evento_id": str(evento_id or uuid4()),
        "codigo_contenedor": codigo.strip().upper(),
        "lector": lector.strip(),
        "fecha_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Publica detecciones RFID simuladas; no controla hardware físico."
    )
    parser.add_argument("--codigo", required=True)
    parser.add_argument("--lector", default="LECTOR_SIMULADO_01")
    parser.add_argument(
        "--evento-id",
        type=UUID,
        help="UUID opcional para demostrar deduplicación de forma controlada.",
    )
    parser.add_argument("--cantidad", type=int, default=1)
    parser.add_argument("--intervalo", type=float, default=1.0)
    argumentos = parser.parse_args()
    if not 1 <= argumentos.cantidad <= 100:
        parser.error("--cantidad debe estar entre 1 y 100")
    if not 0 <= argumentos.intervalo <= 60:
        parser.error("--intervalo debe estar entre 0 y 60")

    import paho.mqtt.client as mqtt

    host = os.getenv("RFID_MQTT_HOST", "localhost")
    puerto = int(os.getenv("RFID_MQTT_PORT", "1883"))
    topic = os.getenv("RFID_MQTT_TOPIC", "puertotrack/rfid/detecciones")
    cliente = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"puertotrack-rfid-simulator-{uuid4().hex[:8]}",
    )
    cliente.connect(host, puerto, keepalive=30)
    cliente.loop_start()
    try:
        for indice in range(argumentos.cantidad):
            mensaje = crear_mensaje_simulado(
                argumentos.codigo,
                argumentos.lector,
                argumentos.evento_id,
            )
            publicacion = cliente.publish(
                topic,
                json.dumps(mensaje, ensure_ascii=False),
                qos=1,
            )
            if publicacion.rc != mqtt.MQTT_ERR_SUCCESS:
                raise RuntimeError(
                    "Mosquitto rechazó la publicación RFID simulada."
                )
            publicacion.wait_for_publish(timeout=5)
            if not publicacion.is_published():
                raise TimeoutError(
                    "Mosquitto no confirmó la publicación RFID simulada."
                )
            print(
                json.dumps(
                    {
                        "evento": "deteccion_rfid_simulada_publicada",
                        **mensaje,
                    },
                    ensure_ascii=False,
                )
            )
            if indice + 1 < argumentos.cantidad:
                sleep(argumentos.intervalo)
    finally:
        cliente.disconnect()
        cliente.loop_stop()


if __name__ == "__main__":
    main()
