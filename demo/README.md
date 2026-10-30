# PuertoTrack — Demo interactiva aislada

Este modo inicia la aplicación completa para una revisión visual. Usa
exclusivamente PostgreSQL 17 efímero en Docker y no consulta ni modifica la
base habitual de PuertoTrack.

## Requisitos

- Windows PowerShell 5.1 o posterior.
- Docker Desktop iniciado.
- Entornos virtuales existentes en `backend`, `rfid-service` y
  `access-service`.
- Dependencias del frontend instaladas en `frontend/node_modules`.
- Puertos locales libres: `1883`, `55432`, `8000`, `8100`, `8200` y `5173`.

Todos los comandos siguientes se ejecutan desde PowerShell de Windows:

```powershell
Set-Location C:\Users\<usuario>\Documents\PuertoTrack
```

## Iniciar

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\demo\iniciar-demo.ps1
```

El inicio:

1. rechaza cualquier puerto ocupado sin detener procesos ajenos;
2. inicia PostgreSQL temporal en `127.0.0.1:55432`;
3. exige nombre `_test`, confirmación, marcador, `current_database()` y
   `current_user` antes de aplicar Alembic o escribir fixtures;
4. crea usuarios, ubicaciones, contenedores, movimientos y auditorías mediante
   los servicios reales;
5. inicia Mosquitto, FastAPI, RFID, Accesos y Vite solo en localhost;
6. verifica login, endpoints, roles, MQTT y una decisión de acceso inicial;
7. deja los procesos activos para utilizar el navegador.

Abra:

```text
http://localhost:5173
```

La sesión JWT está solo en memoria. Recargar la pestaña requiere iniciar sesión
de nuevo, pero no reiniciar la demo.

## Credenciales temporales

Las contraseñas se generan aleatoriamente en cada inicio. No aparecen en logs
ni en archivos versionados. PowerShell las guarda con DPAPI en un CLIXML bajo
`%LOCALAPPDATA%\PuertoTrackDemo`, descifrable únicamente por el mismo usuario de
Windows.

Para mostrarlas localmente:

```powershell
.\demo\mostrar-credenciales-demo.ps1
```

Se entregan las cuentas `supervisor` y `operador`. El archivo cifrado se elimina
al detener la demo.

## Datos disponibles

- `DEMOENTRADA`: disponible, sin ubicación catalogada; permite primera entrada
  y habilitación preliminar RFID.
- `DEMOTRASLADO`: en Patio A; permite traslado o salida.
- `DEMOSALIDA`: en Muelle 1; permite demostrar una salida.
- `DEMOREINGRESO`: fuera del puerto con salida previa; permite reingreso.
- `DEMOHISTORIAL`: en Patio B, con entrada y traslado históricos.
- Ubicaciones internas: Muelle 1, Patio A y Patio B.
- Ubicaciones externas: Fuera del puerto y Depósito externo.
- Una ubicación externa inactiva visible solo para supervisores.

## Recorrido visual sugerido

Como supervisor:

1. Dashboard: revise totales, gráfico y últimos movimientos.
2. Contenedores: busque los cinco códigos de demostración.
3. Movimientos: registre, por ejemplo, un traslado de `DEMOTRASLADO` desde
   Patio A hacia Patio B.
4. Ubicaciones: revise activas/inactivas y permisos de administración.
5. Auditoría: confirme que aparecen creación de catálogo, contenedores y
   movimientos.
6. Accesos: observe la decisión inicial `habilitado` y use **Actualizar** tras
   cada simulación RFID.

Como operador:

- Puede consultar Dashboard, Contenedores, Movimientos y ubicaciones activas.
- Puede registrar movimientos válidos.
- No puede crear/corregir contenedores ni administrar ubicaciones.
- Auditoría y Accesos no aparecen en el menú; el backend también responde 403.

## Simulaciones RFID

Contenedor existente y habilitado:

```powershell
.\demo\simular-rfid.ps1 -Escenario habilitado
```

Código desconocido y denegado:

```powershell
.\demo\simular-rfid.ps1 -Escenario desconocido
```

Mismo `evento_id` publicado dos veces:

```powershell
.\demo\simular-rfid.ps1 -Escenario duplicado
```

Después de cada comando, abra **Accesos** como supervisor y pulse
**Actualizar**. El duplicado produce una sola decisión efectiva. Las lecturas
RFID no registran movimientos ni modifican ubicación, estado o auditoría.

## Detener y limpiar

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\demo\detener-demo.ps1
```

La detención usa exclusivamente los PID registrados y comprueba el ejecutable
antes de terminarlo. Luego desmonta los dos proyectos Docker y elimina el
PostgreSQL en `tmpfs`, logs, estado y credenciales temporales. No mata procesos
por número de puerto.

## Validación automatizada

La comprobación de arranque, salud y cierre es:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\demo\validar-demo.ps1
```

Esta variante sí detiene automáticamente el entorno porque está destinada a
pruebas. Para usar el navegador ejecute `iniciar-demo.ps1` directamente.

## Problemas frecuentes

- **Puerto ocupado:** cierre conscientemente la aplicación que lo utiliza o
  cambie su configuración. El script no interfiere con ella.
- **Docker no responde:** inicie Docker Desktop y espere a que el motor esté
  listo.
- **Falta un entorno virtual:** instale las dependencias del directorio indicado
  en el error antes de iniciar.
- **Vite o frontend no inicia:** ejecute `npm install` en `frontend` si falta
  `node_modules`; no es necesario cambiar `.env.local`.
- **Sesión cerrada al recargar:** es el comportamiento esperado del JWT en
  memoria; vuelva a iniciar sesión.
- **Accesos vacío:** espere uno o dos segundos, pulse **Actualizar** o ejecute
  una simulación RFID.
- **`DEMOENTRADA` deja de habilitar:** probablemente se registró su entrada
  desde Movimientos. Detenga y reinicie la demo para recuperar los fixtures.
- **Inicio interrumpido:** el bloque de error desmonta lo que alcanzó a crear.
  Si quedó un estado registrado, ejecute `detener-demo.ps1`.

El registro `RFIDDEMO001` de la base habitual no forma parte de este entorno y
no se consulta, actualiza ni elimina.
