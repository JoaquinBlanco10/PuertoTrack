[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('habilitado', 'desconocido', 'duplicado')]
    [string]$Escenario,
    [switch]$Passthru
)

$ErrorActionPreference = 'Stop'
$raiz = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$runtimeDir = Join-Path $env:LOCALAPPDATA 'PuertoTrackDemo'
$statePath = Join-Path $runtimeDir 'state.json'
$rfidDir = Join-Path $raiz 'rfid-service'
$rfidPython = Join-Path $rfidDir '.venv\Scripts\python.exe'

if (-not (Test-Path $statePath)) {
    throw 'El entorno DEMO no está activo. Ejecute primero iniciar-demo.ps1.'
}
if (-not (Get-NetTCPConnection -LocalPort 1883 -State Listen -ErrorAction SilentlyContinue)) {
    throw 'Mosquitto no está disponible en localhost:1883.'
}

$eventoId = [guid]::NewGuid()
$codigo = if ($Escenario -eq 'desconocido') { 'DEMONOEXISTE' } else { 'DEMOENTRADA' }
$variablesTemporales = @('PYTHONPATH','RFID_MQTT_HOST','RFID_MQTT_PORT','RFID_MQTT_TOPIC')
$entornoAnterior = @{}
foreach ($nombre in $variablesTemporales) {
    $entornoAnterior[$nombre] = [Environment]::GetEnvironmentVariable(
        $nombre, [EnvironmentVariableTarget]::Process
    )
}
$env:PYTHONPATH = Join-Path $rfidDir 'src'
$env:RFID_MQTT_HOST = '127.0.0.1'
$env:RFID_MQTT_PORT = '1883'
$env:RFID_MQTT_TOPIC = 'puertotrack/rfid/detecciones'

function Publish-Event {
    $proceso = Start-Process -FilePath $rfidPython `
        -ArgumentList @(
            '-m','rfid_service.simulator','--codigo',$codigo,
            '--lector','PORTICO_DEMO_INTERACTIVA','--evento-id',$eventoId.ToString()
        ) -WorkingDirectory $rfidDir -Wait -NoNewWindow -PassThru
    if ($proceso.ExitCode -ne 0) { throw 'No fue posible publicar el evento RFID.' }
}

try {
    Publish-Event
    if ($Escenario -eq 'duplicado') {
        Start-Sleep -Seconds 1
        Publish-Event
    }
}
finally {
    foreach ($nombre in $variablesTemporales) {
        $valor = $entornoAnterior[$nombre]
        if ($null -eq $valor) {
            Remove-Item "Env:$nombre" -ErrorAction SilentlyContinue
        }
        else { [Environment]::SetEnvironmentVariable($nombre, $valor, 'Process') }
    }
}

Write-Host ''
Write-Host "Escenario '$Escenario' publicado con evento_id=$eventoId." -ForegroundColor Green
Write-Host 'En React: ingrese como supervisor, abra Accesos y pulse Actualizar.'
if ($Passthru) {
    Write-Output ([pscustomobject]@{
        Escenario = $Escenario
        EventoId = $eventoId.ToString()
    })
}
