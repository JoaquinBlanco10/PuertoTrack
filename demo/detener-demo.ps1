[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$runtimeDir = Join-Path $env:LOCALAPPDATA 'PuertoTrackDemo'
$statePath = Join-Path $runtimeDir 'state.json'
$docker = (Get-Command docker.exe -ErrorAction Stop).Source

function Stop-DemoProcessTree {
    param([int]$ProcessId)
    $hijos = Get-CimInstance Win32_Process `
        -Filter "ParentProcessId = $ProcessId" -ErrorAction SilentlyContinue
    foreach ($hijo in $hijos) {
        Stop-DemoProcessTree -ProcessId ([int]$hijo.ProcessId)
    }
    Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
}

if (-not (Test-Path $statePath)) {
    Write-Host 'No existe un entorno DEMO registrado; no se detuvo ningún proceso.'
    exit 0
}

$estado = Get-Content $statePath -Raw | ConvertFrom-Json
$raizEsperada = [IO.Path]::GetFullPath((Resolve-Path (Join-Path $PSScriptRoot '..')).Path)
$raizEstado = [IO.Path]::GetFullPath([string]$estado.Raiz)
if ($raizEstado -ne $raizEsperada) {
    throw 'El estado DEMO pertenece a otro directorio. No se detuvo nada.'
}

foreach ($registro in @($estado.Procesos)) {
    $actual = Get-CimInstance Win32_Process `
        -Filter "ProcessId = $([int]$registro.Id)" -ErrorAction SilentlyContinue
    if ($null -eq $actual) { continue }
    $ejecutableActual = [IO.Path]::GetFullPath([string]$actual.ExecutablePath)
    $ejecutableEsperado = [IO.Path]::GetFullPath([string]$registro.Ejecutable)
    if ($ejecutableActual -ne $ejecutableEsperado) {
        Write-Warning "PID $($registro.Id) fue reutilizado por otro ejecutable; no se detuvo."
        continue
    }
    Stop-DemoProcessTree -ProcessId ([int]$registro.Id)
}

$backendDir = Join-Path $raizEstado 'backend'
$rfidDir = Join-Path $raizEstado 'rfid-service'
$env:PATH = (Split-Path $docker) + ';' + $env:PATH

# Solo se desmontan los dos proyectos Compose registrados por iniciar-demo.
$mqtt = Start-Process -FilePath $docker `
    -ArgumentList @('compose','-f','docker-compose.yml','down') `
    -WorkingDirectory $rfidDir -Wait -NoNewWindow -PassThru
$postgres = Start-Process -FilePath $docker `
    -ArgumentList @('compose','-f','compose.postgres-test.yml','down') `
    -WorkingDirectory $backendDir -Wait -NoNewWindow -PassThru

if ($mqtt.ExitCode -ne 0 -or $postgres.ExitCode -ne 0) {
    throw 'Docker no pudo desmontar completamente el entorno efímero.'
}

Remove-Item $runtimeDir -Recurse -Force
Write-Host 'PuertoTrack DEMO detenido. PostgreSQL efímero, Mosquitto, procesos, logs y credenciales fueron eliminados.' -ForegroundColor Green
