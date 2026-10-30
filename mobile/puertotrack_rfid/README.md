# PuertoTrack RFID Mobile

Aplicación Android en Flutter que **simula** una lectura RFID. No lee etiquetas
físicas, no consulta PostgreSQL y no modifica movimientos ni contenedores.

## Contrato y resultado

La app envía `POST /detecciones` al microservicio RFID con
`X-PuertoTrack-Device-Key`. El JSON contiene exclusivamente `evento_id` (UUID
v4), `codigo_contenedor`, `lector` y `fecha_utc` (ISO 8601 UTC). El código se
normaliza a mayúsculas. Cada toque del botón genera un UUID nuevo.

HTTP **202** significa que Mosquitto confirmó la publicación MQTT con QoS 1.
La identificación del contenedor y la decisión de Accesos son posteriores.
Consúltalas en el historial de RFID o en la pantalla Accesos de PuertoTrack.

Los errores 401, 422, 503, desconexión y tiempo de espera se muestran sin
exponer la clave ni el cuerpo interno de error. La clave se ingresa en la app,
permanece solo en memoria y se descarta al cerrar el proceso. No se incluye
en el código, en parámetros de compilación, en archivos ni en logs.

## Preparación en Windows con Android físico por USB

Requiere Flutter SDK, Android SDK y un teléfono con depuración USB. En este
equipo el SDK está instalado, pero `adb.exe` no está en el PATH y quedan
licencias Android por aceptar. Usa la ruta del SDK desde PowerShell, partiendo
de la raíz de PuertoTrack:

```powershell
Set-Location .\mobile\puertotrack_rfid
flutter pub get
flutter doctor
$adb = Join-Path $env:LOCALAPPDATA 'Android\sdk\platform-tools\adb.exe'
& $adb devices
& $adb reverse tcp:8100 tcp:8100
flutter run
```

Si `flutter doctor` sigue mostrando licencias pendientes, acepta las que
correspondan con `flutter doctor --android-licenses` antes de compilar Android.

Autoriza la depuración USB en el teléfono si aparece el aviso. Después de
desconectar y reconectar el cable, repite `& $adb reverse tcp:8100 tcp:8100`.
En la app, usa la URL inicial `http://127.0.0.1:8100`. Con `adb reverse`, esa
dirección del teléfono llega al puerto 8100 de Windows. RFID y Mosquitto pueden
seguir enlazados únicamente a localhost. No es necesario abrir puertos del
firewall ni publicar Mosquitto en la red local.

El modo debug de Android permite HTTP sin cifrar solo a `127.0.0.1`,
`localhost` y `10.0.2.2` (emulador). La app exige HTTPS fuera de debug y el
manifiesto principal prohíbe tráfico HTTP sin cifrar.

## Conexión con la DEMO aislada

El launcher actual de la DEMO no crea una clave de dispositivo. En **otra
ventana PowerShell situada en la raíz del repositorio**, define la clave antes
de iniciar la DEMO. Debe tener al menos 32 bytes y ser distinta de
`RFID_INTERNAL_API_KEY`. El siguiente ejemplo la solicita sin mostrar lo
escrito:

```powershell
$claveTemporal = Read-Host 'Clave temporal RFID Mobile (mínimo 32 caracteres)' -AsSecureString
$env:RFID_DEVICE_API_KEY = [PSCredential]::new('rfid', $claveTemporal).GetNetworkCredential().Password
.\demo\iniciar-demo.ps1
```

Escribe esa misma clave en el campo de la app; no la incluyas en Git, capturas,
mensajes ni comandos impresos. Para probar un contenedor preparado, ingresa
`DEMOENTRADA`. La cuenta y la base de datos deben ser las de la DEMO aislada.
El launcher de la DEMO puede seguir usando el simulador PowerShell: ambos
publicadores llegan al mismo topic y usan el mismo procesamiento.

Al terminar:

```powershell
.\demo\detener-demo.ps1
& $adb reverse --remove tcp:8100
Remove-Item Env:RFID_DEVICE_API_KEY -ErrorAction SilentlyContinue
```

Si el endpoint responde 503, revisa que la clave de dispositivo se haya
heredado al iniciar RFID y que Mosquitto esté conectado. Un 401 indica que la
clave de la app no coincide. Un 422 indica que el contrato JSON fue rechazado.

## Verificación local sin servicios

```powershell
Set-Location .\mobile\puertotrack_rfid
flutter analyze
flutter test
```

Las pruebas usan respuestas HTTP simuladas y no acceden a PostgreSQL. El
cliente está en `lib/src/rfid_api_client.dart`, el modelo en
`lib/src/deteccion_rfid.dart` y la interfaz en `lib/src/rfid_home_page.dart`.
