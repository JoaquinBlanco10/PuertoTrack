# PuertoTrack Backend

## Configuración JWT

La aplicación valida `JWT_SECRET_KEY` durante el arranque y se detiene si el
valor está vacío, tiene menos de 32 bytes, posee muy poca diversidad o coincide
con patrones débiles conocidos. Debe configurarse con un valor aleatorio y
estable por entorno. Cambiarlo invalida los JWT emitidos anteriormente; el
valor nunca debe registrarse ni incluirse en el repositorio.

## Protección local del login

El endpoint de login conserva en memoria los intentos fallidos de los últimos
cinco minutos. Bloquea temporalmente después de 5 fallos para un mismo email o
20 fallos desde una misma IP. El email se normaliza antes de contabilizarlo y
la respuesta de credenciales inválidas no revela si la cuenta existe.

Esta protección es deliberadamente local y no requiere infraestructura
adicional. Su estado se pierde al reiniciar el proceso y no se comparte entre
múltiples workers o réplicas. En un despliegue con más de una instancia debe
complementarse con límites en el proxy o balanceador. La IP usada es la que
FastAPI recibe como cliente directo; los encabezados reenviados solo deben
confiarse cuando el proxy esté configurado explícitamente como confiable.
Como todo límite por identidad, un atacante puede provocar un bloqueo temporal
de un email conocido; y el límite por IP puede agrupar usuarios que comparten
NAT. Por eso el bloqueo es corto y la solución debe revisarse con métricas
reales antes de ajustar sus umbrales.
