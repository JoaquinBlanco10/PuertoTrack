# PuertoTrack RFID/MQTT

Microservicio independiente para demostrar una integración industrial mediante
eventos RFID **simulados**. No se conecta a lectores físicos, no accede a
PostgreSQL y no registra movimientos ni modifica contenedores.

## Flujo

```text
Simulador -> MQTT/Mosquitto -> Consumidor RFID
                                  |
                                  | GET interno autenticado
                                  v
                         Backend PuertoTrack
                                  |
                         consulta de solo lectura
                                  |
                    identificaciones.v1 (solo pertinentes)
                                  v
                         Microservicio Accesos
```

El mensaje MQTT usa el topic `puertotrack/rfid/detecciones` y este contrato:

```json
{
  "evento_id": "UUID",
  "codigo_contenedor": "CONT123",
  "lector": "PORTICO_NORTE",
  "fecha_utc": "2026-10-19T12:00:00Z"
}
```

Tras procesar una detección `valido` o `codigo_desconocido`, RFID publica una
identificación versionada en `puertotrack/rfid/identificaciones.v1`. No publica
mensajes derivados para estados `duplicado`, `mensaje_invalido` ni
`error_integracion`, por lo que conserva íntegro el contrato original y evita
decisiones repetidas. El servicio de accesos se documenta en
`../access-service/README.md`.

El backend expone únicamente:

```text
GET /internal/rfid/contenedores/{codigo}
X-PuertoTrack-Internal-Key: <clave compartida>
```

Una respuesta exitosa solo contiene `existe`, `id` y `codigo`. Un código no
registrado devuelve `404`. La integración no devuelve ubicación, estado ni
historial.

## Preparación

Crear un entorno Python independiente dentro de `rfid-service/`:

```bash
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
```

En Windows/PowerShell, si Python no está publicado globalmente pero ya existe
el entorno del backend, se puede usar su intérprete solo para crear el entorno
independiente (las dependencias se instalan después en `rfid-service/.venv`):

```powershell
Set-Location C:\Users\<usuario>\Documents\PuertoTrack\rfid-service
& ..\backend\.venv\Scripts\python.exe -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Generar una clave aleatoria sin escribirla en el repositorio, por ejemplo:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

En cada terminal que corresponda, exportar el mismo valor:

```bash
export RFID_INTERNAL_API_KEY='<valor-aleatorio-generado>'
```

No se debe reutilizar `JWT_SECRET_KEY` como clave interna.

En PowerShell puede mantenerse la clave solo en memoria durante la sesión, sin
imprimirla ni escribirla en un archivo:

```powershell
$claveRfid = & .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
$env:RFID_INTERNAL_API_KEY = $claveRfid
```

Repita la asignación de `$env:RFID_INTERNAL_API_KEY` en cada proceso que no sea
hijo de esa terminal. Al terminar, elimínela con
`Remove-Item Env:RFID_INTERNAL_API_KEY` y cierre la terminal.

## Ejecución local

1. Iniciar únicamente el broker local:

```bash
cd rfid-service
docker compose up -d
```

En PowerShell use `docker.exe compose up -d`. Esto evita conflictos en equipos
donde `docker` sin extensión resuelve primero un wrapper de consola.

El puerto MQTT se publica solo en `127.0.0.1:1883`. El modo anónimo es
aceptable exclusivamente para esta demostración local porque el puerto no se
expone a otras interfaces.

2. Iniciar el backend desde otra terminal, apuntando explícitamente a la base
aislada ya verificada y con `RFID_INTERNAL_API_KEY` exportada. No utilice la
configuración habitual para la demostración:

```bash
cd backend
.venv/Scripts/python.exe -m uvicorn main:app --reload
```

3. Iniciar el microservicio:

```bash
cd rfid-service
export RFID_INTERNAL_API_KEY='<el-mismo-valor>'
export PUERTOTRACK_API_URL='http://localhost:8000'
.venv/Scripts/python.exe -m uvicorn --app-dir src rfid_service.main:app --host 127.0.0.1 --port 8100
```

4. Publicar una lectura simulada:

```bash
PYTHONPATH=src .venv/Scripts/python.exe -m rfid_service.simulator --codigo CONT123 --lector PORTICO_NORTE
```

La alternativa recomendada en PowerShell es:

```powershell
$env:PYTHONPATH = 'src'
.venv\Scripts\python.exe -m rfid_service.simulator --codigo CONT123 --lector PORTICO_NORTE
```

Para la integración completa en Windows use exclusivamente PowerShell. Primero
prepare PostgreSQL desde la misma sesión; no invoque `python.exe` de Windows
desde WSL con variables prefijadas:

La opción recomendada para la demostración es el verificador automatizado:

```powershell
Set-Location C:\Users\<usuario>\Documents\PuertoTrack
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\rfid-service\scripts\validar-integracion.ps1
```

El script verifica puertos y barreras PostgreSQL, ejecuta las migraciones solo
en la base efímera, crea un código de contenedor aleatorio, inicia FastAPI y
MQTT en loopback y comprueba los estados `valido`, `codigo_desconocido`,
`duplicado` y `mensaje_invalido`. También exige un HTTP 401 para una clave
interna incorrecta y compara snapshots para confirmar que RFID no modificó
movimientos, ubicaciones, estados ni auditorías. Las claves solo existen en la
memoria del proceso. El bloque `finally` detiene procesos y ejecuta ambos
`docker compose down`, incluso si una comprobación falla.

El procedimiento manual equivalente es:

```powershell
# 1. PostgreSQL efímero: migraciones, identidad real y fixture protegido
$raiz = 'C:\Users\<usuario>\Documents\PuertoTrack'
Set-Location "$raiz\backend"
docker.exe compose -f compose.postgres-test.yml up -d --wait
Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
$env:PUERTOTRACK_RUN_POSTGRES_TESTS = 'PUERTOTRACK_POSTGRES_TEST_ONLY'
$env:PUERTOTRACK_TEST_DATABASE_URL = 'postgresql+psycopg://puertotrack_test:puertotrack_test_local_only@127.0.0.1:55432/puertotrack_integration_test'
& .\.venv\Scripts\python.exe -m pytest -q postgres_integration
& .\.venv\Scripts\python.exe -m scripts.preparar_demo_rfid
& .\.venv\Scripts\python.exe -m scripts.preparar_demo_rfid --crear-contenedor RFIDDEMOAISLADO

# Solo tras superar las barreras se habilita la URL para procesos hijos.
$env:DATABASE_URL = $env:PUERTOTRACK_TEST_DATABASE_URL

# 2. Claves efímeras mantenidas solo en esta sesión
$bytesRfid = New-Object byte[] 48
$bytesJwt = New-Object byte[] 48
$rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
$rng.GetBytes($bytesRfid)
$rng.GetBytes($bytesJwt)
$rng.Dispose()
$env:RFID_INTERNAL_API_KEY = [Convert]::ToBase64String($bytesRfid)
$env:JWT_SECRET_KEY = [Convert]::ToBase64String($bytesJwt)
$env:ACCESS_TOKEN_EXPIRE_MINUTES = '30'
$env:PUERTOTRACK_API_URL = 'http://127.0.0.1:8000'
$env:RFID_MQTT_HOST = '127.0.0.1'

# 3. Broker y procesos hijos; todos heredan exactamente este entorno
Set-Location "$raiz\rfid-service"
docker.exe compose up -d --wait
$backend = Start-Process "$raiz\backend\.venv\Scripts\python.exe" `
  -ArgumentList '-m','uvicorn','main:app','--host','127.0.0.1','--port','8000' `
  -WorkingDirectory "$raiz\backend" -PassThru
$rfid = Start-Process "$raiz\rfid-service\.venv\Scripts\python.exe" `
  -ArgumentList '-m','uvicorn','--app-dir','src','rfid_service.main:app','--host','127.0.0.1','--port','8100' `
  -WorkingDirectory "$raiz\rfid-service" -PassThru
```

Si la suite o cualquiera de las dos verificaciones falla, no asigne
`DATABASE_URL` ni inicie FastAPI. La preparación se bloquea antes de escribir.
Las instrucciones detalladas también están en
`backend/postgres_integration/README.md`.

5. Consultar resultados:

```bash
curl http://127.0.0.1:8100/health
curl http://127.0.0.1:8100/procesamientos
curl http://127.0.0.1:8100/procesamientos/<evento-uuid>
```

Para demostrar deduplicación, publicar dos veces el mismo UUID:

```bash
export EVENTO_DEMO='11111111-1111-4111-8111-111111111111'
PYTHONPATH=src .venv/Scripts/python.exe -m rfid_service.simulator --codigo CONT123 --evento-id "$EVENTO_DEMO"
PYTHONPATH=src .venv/Scripts/python.exe -m rfid_service.simulator --codigo CONT123 --evento-id "$EVENTO_DEMO"
```

El primer evento será `valido` o `codigo_desconocido`; el segundo será
`duplicado`. Los mensajes que no cumplan el JSON se clasifican como
`mensaje_invalido`.

## Pruebas

```bash
cd rfid-service
.venv/Scripts/python.exe -m pytest -q
```

Las pruebas usan dobles y `MockTransport`: no requieren broker, backend ni base
de datos. El contrato interno del backend se prueba separadamente con SQLite:

```bash
cd backend
.venv/Scripts/python.exe -m pytest -q tests/test_rfid_internal.py
```

## Detención

Detener Uvicorn con `Ctrl+C` y luego:

```bash
docker compose down
```

En PowerShell: `docker.exe compose down`. Detenga también ambos procesos de
Uvicorn con `Ctrl+C` y quite las variables temporales de la sesión.

Si se iniciaron con `Start-Process`, la limpieza completa es:

```powershell
Stop-Process -Id $backend.Id, $rfid.Id -Force -ErrorAction SilentlyContinue
Set-Location "$raiz\rfid-service"
docker.exe compose down
Set-Location "$raiz\backend"
docker.exe compose -f compose.postgres-test.yml down
Remove-Item Env:DATABASE_URL, Env:PUERTOTRACK_TEST_DATABASE_URL, Env:PUERTOTRACK_RUN_POSTGRES_TESTS, Env:RFID_INTERNAL_API_KEY, Env:JWT_SECRET_KEY -ErrorAction SilentlyContinue
```

## Limitaciones del prototipo

- Deduplicación y estados son memoria local; se pierden al reiniciar.
- Varias réplicas no comparten eventos vistos.
- MQTT no usa TLS ni credenciales en desarrollo; el puerto está limitado a
  loopback. Producción requiere TLS, autenticación y ACL de topics.
- La clave interna solo debe viajar por loopback o HTTPS; el prototipo local no
  configura certificados entre procesos.
- La API de estado también se inicia en loopback y no tiene autenticación.
- No hay integración con lectores físicos ni garantías de calibración RFID.
- Un evento válido solo confirma que el código existe. No implica entrada,
  traslado, salida ni presencia física confirmada.
- No se generan auditorías operacionales porque no se modifica el dominio.
