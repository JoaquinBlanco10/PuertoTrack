# Pruebas de integración PostgreSQL

Esta suite valida comportamientos que SQLite no reproduce fielmente: bloqueos
`SELECT FOR UPDATE`, concurrencia real, restricciones y atomicidad sobre
PostgreSQL 17. No forma parte de la ejecución normal de `pytest`.

## Aislamiento y protecciones

El servicio de Compose publica PostgreSQL únicamente en `127.0.0.1:55432`, usa
una base y un usuario exclusivos de prueba y almacena el clúster en `tmpfs`.
No comparte volúmenes con PuertoTrack ni lee los archivos `.env` del proyecto.

Antes de ejecutar Alembic, `conftest.py` exige las tres condiciones siguientes:

1. `PUERTOTRACK_RUN_POSTGRES_TESTS` contiene el valor literal de confirmación.
2. `PUERTOTRACK_TEST_DATABASE_URL` usa PostgreSQL y el nombre de base cumple el
   patrón `puertotrack..._test`; además no puede coincidir con `DATABASE_URL` si
   esta ya existe en el entorno del proceso.
3. La propia base contiene el comentario
   `puertotrack:integration-test-only`, creado durante su inicialización.
4. PostgreSQL confirma que `current_database()` y `current_user` coinciden con
   la URL de pruebas validada.

Si falla una barrera, pytest termina antes de ejecutar migraciones. La suite
solo aplica `alembic upgrade head`; nunca ejecuta `downgrade`, `DROP` ni borra
registros. Al detener Compose, el `tmpfs` descarta el clúster completo.

## Ejecución autorizada (Bash)

Desde `backend/`:

```bash
docker compose -f compose.postgres-test.yml up -d --wait
export PUERTOTRACK_RUN_POSTGRES_TESTS=PUERTOTRACK_POSTGRES_TEST_ONLY
export PUERTOTRACK_TEST_DATABASE_URL='postgresql+psycopg://puertotrack_test:puertotrack_test_local_only@127.0.0.1:55432/puertotrack_integration_test'
.venv/Scripts/python.exe -m pytest -q postgres_integration
docker compose -f compose.postgres-test.yml down
unset PUERTOTRACK_RUN_POSTGRES_TESTS PUERTOTRACK_TEST_DATABASE_URL
```

En PowerShell, el procedimiento completo y seguro es:

```powershell
Set-Location C:\Users\<usuario>\Documents\PuertoTrack\backend
docker.exe compose -f compose.postgres-test.yml up -d --wait

# No heredar una URL de aplicación hacia los procesos de la demostración.
Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
$env:PUERTOTRACK_RUN_POSTGRES_TESTS = 'PUERTOTRACK_POSTGRES_TEST_ONLY'
$env:PUERTOTRACK_TEST_DATABASE_URL = 'postgresql+psycopg://puertotrack_test:puertotrack_test_local_only@127.0.0.1:55432/puertotrack_integration_test'
& .\.venv\Scripts\python.exe -m pytest -q postgres_integration
& .\.venv\Scripts\python.exe -m scripts.preparar_demo_rfid

# Solo después de ambas verificaciones se prepara el fixture aislado.
& .\.venv\Scripts\python.exe -m scripts.preparar_demo_rfid --crear-contenedor RFIDDEMO001
```

`scripts.preparar_demo_rfid` construye su propio motor desde la URL exclusiva
de pruebas. No usa `SessionLocal` y valida nombre de base, usuario y marcador
antes de abrir una transacción que pueda escribir. Para iniciar el backend de
la demostración, asigne `DATABASE_URL` únicamente después de que esos comandos
terminen correctamente:

```powershell
$env:DATABASE_URL = $env:PUERTOTRACK_TEST_DATABASE_URL
```

Al terminar:

```powershell
docker.exe compose -f compose.postgres-test.yml down
Remove-Item Env:DATABASE_URL, Env:PUERTOTRACK_RUN_POSTGRES_TESTS, Env:PUERTOTRACK_TEST_DATABASE_URL -ErrorAction SilentlyContinue
```

No ejecute `python.exe` de Windows desde WSL confiando en una asignación como
`DATABASE_URL=... python.exe`: las variables WSL no se propagan automáticamente
a ejecutables Windows salvo configuración explícita de `WSLENV`.

Las credenciales anteriores pertenecen exclusivamente al servicio local y
efímero descrito en `compose.postgres-test.yml`; no son secretos de la
aplicación. Para ejecutar las pruebas SQLite habituales basta con:

```bash
.venv/Scripts/python.exe -m pytest -q
```

Para validar además el recorrido RFID → Accesos, use desde la raíz y en
PowerShell de Windows:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\access-service\scripts\validar-integracion.ps1
```

Ese verificador reutiliza estas barreras y aplica Alembic únicamente dentro del
contenedor PostgreSQL efímero. Nunca debe ejecutarse con una URL habitual.
