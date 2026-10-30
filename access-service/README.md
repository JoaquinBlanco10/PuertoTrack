# PuertoTrack Access Service

Microservicio independiente de habilitación operacional preliminar. Consume
identificaciones RFID y consulta hechos mínimos al backend. No abre barreras,
no registra movimientos y no accede directamente a PostgreSQL.

## Arquitectura y contratos

```text
Simulador -- detecciones --> Mosquitto --> RFID
                                           |
                                  identificaciones.v1
                                           v
                                      Accesos
                                           |
                              GET interno de solo lectura
                                           v
                            FastAPI --> PostgreSQL aislado

Accesos -- resultados.v1 --> Mosquitto
React -- JWT supervisor --> FastAPI -- clave interna --> Accesos
```

Topics versionados:

- Entrada: `puertotrack/rfid/identificaciones.v1`.
- Salida: `puertotrack/accesos/resultados.v1`.

El evento de entrada contiene la versión `1`, `evento_id`, código, identificador
operacional opcional, lector, fechas UTC y resultado de identificación. RFID
solo lo publica para `valido` y `codigo_desconocido`; un duplicado no genera una
nueva publicación. El resultado contiene además un `decision_id`, uno de los
cuatro resultados y un motivo estable.

## Política académica reducida

La decisión solo expresa si la situación operacional permite continuar la
evaluación de un ingreso. No representa permisos portuarios, aduaneros,
comerciales ni de seguridad física:

- `habilitado`: primera entrada de un contenedor `disponible` sin movimientos,
  o reingreso coherente de un contenedor `en_transito` con salida previa.
- `denegado`: código desconocido, contenedor ya dentro del puerto o estado no
  compatible con un ingreso.
- `revision_manual`: presencia sin confirmar con evidencia previa o datos
  operacionales inconsistentes.
- `no_determinado`: el backend no respondió o entregó un contrato incompatible.

La política reside en `policy.py`; el backend solo expone hechos de lectura.
No se inventaron permisos que PuertoTrack no almacena.

## Ejecución en PowerShell

```powershell
Set-Location C:\Users\<usuario>\Documents\PuertoTrack\access-service
& ..\backend\.venv\Scripts\python.exe -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
$bytes = New-Object byte[] 48
$rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
$rng.GetBytes($bytes); $rng.Dispose()
$env:ACCESS_INTERNAL_API_KEY = [Convert]::ToBase64String($bytes)
$env:PUERTOTRACK_API_URL = 'http://127.0.0.1:8000'
& .\.venv\Scripts\python.exe -m uvicorn --app-dir src access_service.main:app --host 127.0.0.1 --port 8200
```

El backend y este proceso deben heredar el mismo
`ACCESS_INTERNAL_API_KEY`. Debe ser distinto de `RFID_INTERNAL_API_KEY` y
`JWT_SECRET_KEY`. La clave se mantiene solo en memoria y no se imprime.

Endpoints del microservicio:

- `GET /health`: estado MQTT y contadores, sin secretos.
- `GET /internal/decisiones`: decisiones recientes, requiere
  `X-PuertoTrack-Access-Key`.
- `GET /internal/decisiones/{evento_id}`: una decisión, con la misma clave.

El frontend no llama directamente a este proceso. Usa `GET /accesos` del
backend con JWT de supervisor; FastAPI aplica RBAC y actúa como proxy.

## Pruebas

Pruebas unitarias, sin broker ni PostgreSQL:

```powershell
Set-Location C:\Users\<usuario>\Documents\PuertoTrack\access-service
& .\.venv\Scripts\python.exe -m pytest -q
```

Validación completa y aislada en Windows:

```powershell
Set-Location C:\Users\<usuario>\Documents\PuertoTrack
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\access-service\scripts\validar-integracion.ps1
```

El script usa exclusivamente procesos Windows, inicia PostgreSQL 17 temporal
en `127.0.0.1:55432` y Mosquitto en `127.0.0.1:1883`, y genera claves y usuarios
efímeros en memoria. Antes de cualquier escritura exige:

1. URL PostgreSQL con nombre `puertotrack..._test`;
2. marcador `PUERTOTRACK_POSTGRES_TEST_ONLY`;
3. comentario de base `puertotrack:integration-test-only`;
4. coincidencia real de `current_database()` y `current_user`;
5. ausencia de una `DATABASE_URL` habitual heredada.

Luego inicia FastAPI, RFID y Accesos solo en `127.0.0.1`, crea fixtures en la
base efímera, valida los topics MQTT, las claves internas, los roles supervisor
y operador, y compara snapshots operacionales. El bloque `finally` detiene los
procesos y ejecuta `docker compose down` incluso si una comprobación falla. No
lee ni modifica archivos `.env`.

## Retención y límites

Las decisiones son memoria local y se eliminan por dos límites configurables:

- `ACCESS_MAX_DECISIONS` (predeterminado: 500).
- `ACCESS_DECISION_TTL_SECONDS` (predeterminado: 3600 segundos).

La deduplicación usa `ACCESS_DEDUP_TTL_SECONDS` (predeterminado: 600) y también
es local a una instancia. El payload máximo predeterminado es 4096 bytes. Las
decisiones y eventos vistos se pierden al reiniciar; esto es intencional para
el prototipo académico.

## Detención manual

Detenga Uvicorn con `Ctrl+C`. Para detener el broker:

```powershell
Set-Location C:\Users\<usuario>\Documents\PuertoTrack\rfid-service
docker.exe compose down
Remove-Item Env:ACCESS_INTERNAL_API_KEY -ErrorAction SilentlyContinue
```

No use este servicio para abrir barreras ni como autorización legal. No ofrece
alta disponibilidad, persistencia de decisiones, TLS MQTT ni deduplicación
compartida entre réplicas.
