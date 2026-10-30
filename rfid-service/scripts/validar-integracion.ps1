[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$raiz = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$backendDir = Join-Path $raiz 'backend'
$rfidDir = Join-Path $raiz 'rfid-service'
$backendPython = Join-Path $backendDir '.venv\Scripts\python.exe'
$rfidPython = Join-Path $rfidDir '.venv\Scripts\python.exe'
$docker = (Get-Command docker.exe -ErrorAction Stop).Source
$env:PATH = (Split-Path $docker) + ';' + $env:PATH
$postgresIniciado = $false
$mqttIniciado = $false
$backendProceso = $null
$rfidProceso = $null
$archivosTemporales = @()

function Invoke-CheckedProcess {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][string[]]$ArgumentList,
        [Parameter(Mandatory = $true)][string]$WorkingDirectory
    )
    $proceso = Start-Process -FilePath $FilePath `
        -ArgumentList $ArgumentList `
        -WorkingDirectory $WorkingDirectory `
        -Wait -NoNewWindow -PassThru
    if ($proceso.ExitCode -ne 0) {
        throw "Un proceso de validación terminó con código $($proceso.ExitCode)."
    }
}

function Invoke-CapturedProcess {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][string[]]$ArgumentList,
        [Parameter(Mandatory = $true)][string]$WorkingDirectory
    )
    $salida = [IO.Path]::GetTempFileName()
    $errores = [IO.Path]::GetTempFileName()
    $script:archivosTemporales += $salida, $errores
    $proceso = Start-Process -FilePath $FilePath `
        -ArgumentList $ArgumentList `
        -WorkingDirectory $WorkingDirectory `
        -RedirectStandardOutput $salida `
        -RedirectStandardError $errores `
        -Wait -PassThru
    if ($proceso.ExitCode -ne 0) {
        $detalle = Get-Content $errores -Raw -ErrorAction SilentlyContinue
        throw "Un proceso protegido falló. $detalle"
    }
    return (Get-Content $salida -Raw).Trim()
}

function Wait-JsonEndpoint {
    param(
        [Parameter(Mandatory = $true)][string]$Uri,
        [hashtable]$Headers = @{},
        [int]$TimeoutSeconds = 20
    )
    $limite = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        try {
            return Invoke-RestMethod -Uri $Uri -Headers $Headers -TimeoutSec 2
        }
        catch {
            Start-Sleep -Milliseconds 250
        }
    } while ((Get-Date) -lt $limite)
    throw "El endpoint local no respondió dentro del tiempo esperado: $Uri"
}

function Wait-EventState {
    param(
        [Parameter(Mandatory = $true)][guid]$EventId,
        [Parameter(Mandatory = $true)][string]$ExpectedState
    )
    $uri = "http://127.0.0.1:8100/procesamientos/$EventId"
    $limite = (Get-Date).AddSeconds(15)
    do {
        try {
            $resultado = Invoke-RestMethod -Uri $uri -TimeoutSec 2
            if ($resultado.estado -eq $ExpectedState) {
                return $resultado
            }
        }
        catch {
            # El procesamiento MQTT puede no estar disponible todavía.
        }
        Start-Sleep -Milliseconds 200
    } while ((Get-Date) -lt $limite)
    throw "El evento $EventId no alcanzó el estado $ExpectedState."
}

function Publish-SimulatedEvent {
    param(
        [Parameter(Mandatory = $true)][string]$Code,
        [Parameter(Mandatory = $true)][guid]$EventId
    )
    Invoke-CheckedProcess -FilePath $rfidPython `
        -ArgumentList @(
            '-m', 'rfid_service.simulator',
            '--codigo', $Code,
            '--lector', 'PORTICO_DEMO',
            '--evento-id', $EventId.ToString()
        ) `
        -WorkingDirectory $rfidDir
}

function Stop-LocalListener {
    param([int]$Port)
    Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        ForEach-Object {
            Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
        }
}

try {
    if (-not (Test-Path $backendPython) -or -not (Test-Path $rfidPython)) {
        throw 'Falta alguno de los entornos virtuales requeridos.'
    }
    foreach ($puerto in 1883, 55432, 8000, 8100) {
        if (Get-NetTCPConnection -LocalPort $puerto -State Listen -ErrorAction SilentlyContinue) {
            throw "El puerto local $puerto ya está ocupado."
        }
    }

    Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
    $env:PUERTOTRACK_RUN_POSTGRES_TESTS = 'PUERTOTRACK_POSTGRES_TEST_ONLY'
    $env:PUERTOTRACK_TEST_DATABASE_URL = 'postgresql+psycopg://puertotrack_test:puertotrack_test_local_only@127.0.0.1:55432/puertotrack_integration_test'

    Invoke-CheckedProcess -FilePath $docker `
        -ArgumentList @('compose', '-f', 'compose.postgres-test.yml', 'up', '-d', '--wait') `
        -WorkingDirectory $backendDir
    $postgresIniciado = $true

    Invoke-CheckedProcess -FilePath $backendPython `
        -ArgumentList @('-m', 'pytest', '-q', 'postgres_integration') `
        -WorkingDirectory $backendDir
    Invoke-CheckedProcess -FilePath $backendPython `
        -ArgumentList @('-m', 'scripts.preparar_demo_rfid') `
        -WorkingDirectory $backendDir

    $codigoDemo = 'RFID' + (Get-Date -Format 'yyMMddHHmmss')
    Invoke-CheckedProcess -FilePath $backendPython `
        -ArgumentList @(
            '-m', 'scripts.preparar_demo_rfid',
            '--crear-contenedor', $codigoDemo
        ) `
        -WorkingDirectory $backendDir
    $snapshotAntes = Invoke-CapturedProcess -FilePath $backendPython `
        -ArgumentList @(
            '-m', 'scripts.preparar_demo_rfid',
            '--snapshot-contenedor', $codigoDemo
        ) `
        -WorkingDirectory $backendDir

    $env:DATABASE_URL = $env:PUERTOTRACK_TEST_DATABASE_URL
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
    $env:RFID_MQTT_PORT = '1883'
    $env:PYTHONPATH = Join-Path $rfidDir 'src'

    Invoke-CheckedProcess -FilePath $docker `
        -ArgumentList @('compose', 'up', '-d', '--wait') `
        -WorkingDirectory $rfidDir
    $mqttIniciado = $true

    $backendOut = [IO.Path]::GetTempFileName()
    $backendErr = [IO.Path]::GetTempFileName()
    $rfidOut = [IO.Path]::GetTempFileName()
    $rfidErr = [IO.Path]::GetTempFileName()
    $archivosTemporales += $backendOut, $backendErr, $rfidOut, $rfidErr
    $backendProceso = Start-Process -FilePath $backendPython `
        -ArgumentList @('-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', '8000') `
        -WorkingDirectory $backendDir `
        -RedirectStandardOutput $backendOut `
        -RedirectStandardError $backendErr `
        -PassThru
    $rfidProceso = Start-Process -FilePath $rfidPython `
        -ArgumentList @('-m', 'uvicorn', '--app-dir', 'src', 'rfid_service.main:app', '--host', '127.0.0.1', '--port', '8100') `
        -WorkingDirectory $rfidDir `
        -RedirectStandardOutput $rfidOut `
        -RedirectStandardError $rfidErr `
        -PassThru

    $null = Wait-JsonEndpoint -Uri 'http://127.0.0.1:8000/health'
    $saludRfid = Wait-JsonEndpoint -Uri 'http://127.0.0.1:8100/health'
    $limiteMqtt = (Get-Date).AddSeconds(15)
    while (-not $saludRfid.mqtt_conectado -and (Get-Date) -lt $limiteMqtt) {
        Start-Sleep -Milliseconds 250
        $saludRfid = Invoke-RestMethod 'http://127.0.0.1:8100/health'
    }
    if (-not $saludRfid.mqtt_conectado) {
        throw 'El consumidor no confirmó su conexión MQTT.'
    }

    $cabeceraCorrecta = @{
        'X-PuertoTrack-Internal-Key' = $env:RFID_INTERNAL_API_KEY
    }
    $identificado = Invoke-RestMethod `
        -Uri "http://127.0.0.1:8000/internal/rfid/contenedores/$codigoDemo" `
        -Headers $cabeceraCorrecta
    if (-not $identificado.existe -or $identificado.codigo -ne $codigoDemo) {
        throw 'FastAPI no identificó el fixture exclusivo de la base aislada.'
    }

    $estadoClaveIncorrecta = $null
    try {
        $null = Invoke-WebRequest `
            -Uri "http://127.0.0.1:8000/internal/rfid/contenedores/$codigoDemo" `
            -Headers @{'X-PuertoTrack-Internal-Key' = 'clave-incorrecta'} `
            -UseBasicParsing -ErrorAction Stop
        throw 'La API interna aceptó una clave incorrecta.'
    }
    catch {
        if ($null -eq $_.Exception.Response) {
            throw
        }
        $estadoClaveIncorrecta = [int]$_.Exception.Response.StatusCode
    }
    if ($estadoClaveIncorrecta -ne 401) {
        throw "La API interna respondió $estadoClaveIncorrecta en lugar de 401."
    }

    $eventoValido = [guid]::NewGuid()
    Publish-SimulatedEvent -Code $codigoDemo -EventId $eventoValido
    $resultadoValido = Wait-EventState -EventId $eventoValido -ExpectedState 'valido'

    $eventoDesconocido = [guid]::NewGuid()
    Publish-SimulatedEvent -Code 'RFIDNOEXISTE' -EventId $eventoDesconocido
    $resultadoDesconocido = Wait-EventState `
        -EventId $eventoDesconocido -ExpectedState 'codigo_desconocido'

    $eventoDuplicado = [guid]::NewGuid()
    Publish-SimulatedEvent -Code $codigoDemo -EventId $eventoDuplicado
    $null = Wait-EventState -EventId $eventoDuplicado -ExpectedState 'valido'
    Publish-SimulatedEvent -Code $codigoDemo -EventId $eventoDuplicado
    $resultadoDuplicado = Wait-EventState `
        -EventId $eventoDuplicado -ExpectedState 'duplicado'

    $saludAntesInvalido = Invoke-RestMethod 'http://127.0.0.1:8100/health'
    $invalidosAntes = [int]$saludAntesInvalido.por_estado.mensaje_invalido
    Invoke-CheckedProcess -FilePath $docker `
        -ArgumentList @(
            'compose', 'exec', '-T', 'mosquitto', 'mosquitto_pub',
            '-h', 'localhost', '-t', 'puertotrack/rfid/detecciones',
            '-m', 'mensaje-no-json'
        ) `
        -WorkingDirectory $rfidDir
    $limiteInvalido = (Get-Date).AddSeconds(15)
    do {
        Start-Sleep -Milliseconds 200
        $saludDespuesInvalido = Invoke-RestMethod 'http://127.0.0.1:8100/health'
        $invalidosDespues = [int]$saludDespuesInvalido.por_estado.mensaje_invalido
    } while ($invalidosDespues -le $invalidosAntes -and (Get-Date) -lt $limiteInvalido)
    if ($invalidosDespues -le $invalidosAntes -or -not $saludDespuesInvalido.mqtt_conectado) {
        throw 'El mensaje inválido no fue controlado o el consumidor se desconectó.'
    }

    # El backend hijo ya heredó la URL aislada. El verificador vuelve a usar
    # únicamente PUERTOTRACK_TEST_DATABASE_URL para no confundir la URL del
    # propio entorno de demostración con una URL operacional heredada.
    $databaseUrlAislada = $env:DATABASE_URL
    Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
    try {
        $snapshotDespues = Invoke-CapturedProcess -FilePath $backendPython `
            -ArgumentList @(
                '-m', 'scripts.preparar_demo_rfid',
                '--snapshot-contenedor', $codigoDemo
            ) `
            -WorkingDirectory $backendDir
    }
    finally {
        $env:DATABASE_URL = $databaseUrlAislada
    }
    if ($snapshotAntes -ne $snapshotDespues) {
        throw 'RFID modificó datos operacionales en la base aislada.'
    }

    [pscustomobject]@{
        base_aislada_verificada = $true
        fastapi_misma_base = $true
        mqtt_conectado = $saludDespuesInvalido.mqtt_conectado
        evento_valido = $resultadoValido.estado
        codigo_desconocido = $resultadoDesconocido.estado
        evento_duplicado = $resultadoDuplicado.estado
        mensaje_invalido = 'mensaje_invalido'
        clave_incorrecta_http = $estadoClaveIncorrecta
        datos_operacionales_sin_cambios = $true
    } | ConvertTo-Json
}
finally {
    Stop-LocalListener -Port 8100
    Stop-LocalListener -Port 8000
    if ($null -ne $rfidProceso) {
        Stop-Process -Id $rfidProceso.Id -Force -ErrorAction SilentlyContinue
    }
    if ($null -ne $backendProceso) {
        Stop-Process -Id $backendProceso.Id -Force -ErrorAction SilentlyContinue
    }
    if ($mqttIniciado) {
        $p = Start-Process -FilePath $docker `
            -ArgumentList @('compose', 'down') `
            -WorkingDirectory $rfidDir `
            -Wait -NoNewWindow -PassThru
    }
    if ($postgresIniciado) {
        $p = Start-Process -FilePath $docker `
            -ArgumentList @('compose', '-f', 'compose.postgres-test.yml', 'down') `
            -WorkingDirectory $backendDir `
            -Wait -NoNewWindow -PassThru
    }
    foreach ($archivo in $archivosTemporales) {
        Remove-Item $archivo -Force -ErrorAction SilentlyContinue
    }
    Remove-Item Env:DATABASE_URL, Env:PUERTOTRACK_TEST_DATABASE_URL, `
        Env:PUERTOTRACK_RUN_POSTGRES_TESTS, Env:RFID_INTERNAL_API_KEY, `
        Env:JWT_SECRET_KEY, Env:ACCESS_TOKEN_EXPIRE_MINUTES, `
        Env:PUERTOTRACK_API_URL, Env:RFID_MQTT_HOST, `
        Env:RFID_MQTT_PORT, Env:PYTHONPATH -ErrorAction SilentlyContinue
}
