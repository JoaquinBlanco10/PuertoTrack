[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$raiz = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$backendDir = Join-Path $raiz 'backend'
$rfidDir = Join-Path $raiz 'rfid-service'
$accessDir = Join-Path $raiz 'access-service'
$backendPython = Join-Path $backendDir '.venv\Scripts\python.exe'
$rfidPython = Join-Path $rfidDir '.venv\Scripts\python.exe'
$accessPython = Join-Path $accessDir '.venv\Scripts\python.exe'
$docker = (Get-Command docker.exe -ErrorAction Stop).Source
$env:PATH = (Split-Path $docker) + ';' + $env:PATH
$postgresIniciado = $false
$mqttIniciado = $false
$procesos = @()
$archivosTemporales = @()

function Invoke-CheckedProcess {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][string[]]$ArgumentList,
        [Parameter(Mandatory = $true)][string]$WorkingDirectory
    )
    $proceso = Start-Process -FilePath $FilePath `
        -ArgumentList $ArgumentList -WorkingDirectory $WorkingDirectory `
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
        -ArgumentList $ArgumentList -WorkingDirectory $WorkingDirectory `
        -RedirectStandardOutput $salida -RedirectStandardError $errores `
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
        [int]$TimeoutSeconds = 25
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

function Wait-RfidState {
    param(
        [Parameter(Mandatory = $true)][guid]$EventId,
        [Parameter(Mandatory = $true)][string]$ExpectedState
    )
    $limite = (Get-Date).AddSeconds(15)
    do {
        try {
            $resultado = Invoke-RestMethod `
                -Uri "http://127.0.0.1:8100/procesamientos/$EventId" `
                -TimeoutSec 2
            if ($resultado.estado -eq $ExpectedState) { return $resultado }
        }
        catch { }
        Start-Sleep -Milliseconds 200
    } while ((Get-Date) -lt $limite)
    throw "RFID no alcanzó el estado $ExpectedState para $EventId."
}

function Wait-AccessDecision {
    param(
        [Parameter(Mandatory = $true)][guid]$EventId,
        [Parameter(Mandatory = $true)][string]$ExpectedResult
    )
    $cabecera = @{'X-PuertoTrack-Access-Key' = $env:ACCESS_INTERNAL_API_KEY}
    $limite = (Get-Date).AddSeconds(15)
    do {
        try {
            $decision = Invoke-RestMethod `
                -Uri "http://127.0.0.1:8200/internal/decisiones/$EventId" `
                -Headers $cabecera -TimeoutSec 2
            if ($decision.resultado -eq $ExpectedResult) { return $decision }
        }
        catch { }
        Start-Sleep -Milliseconds 200
    } while ((Get-Date) -lt $limite)
    throw "Accesos no alcanzó el resultado $ExpectedResult para $EventId."
}

function Publish-SimulatedEvent {
    param(
        [Parameter(Mandatory = $true)][string]$Code,
        [Parameter(Mandatory = $true)][guid]$EventId
    )
    Invoke-CheckedProcess -FilePath $rfidPython `
        -ArgumentList @(
            '-m', 'rfid_service.simulator', '--codigo', $Code,
            '--lector', 'PORTICO_DEMO', '--evento-id', $EventId.ToString()
        ) -WorkingDirectory $rfidDir
}

function Assert-HttpStatus {
    param(
        [Parameter(Mandatory = $true)][string]$Uri,
        [Parameter(Mandatory = $true)][hashtable]$Headers,
        [Parameter(Mandatory = $true)][int]$ExpectedStatus
    )
    try {
        $null = Invoke-WebRequest -Uri $Uri -Headers $Headers `
            -UseBasicParsing -ErrorAction Stop
        throw "La solicitud a $Uri fue aceptada inesperadamente."
    }
    catch {
        if ($null -eq $_.Exception.Response) { throw }
        $estado = [int]$_.Exception.Response.StatusCode
        if ($estado -ne $ExpectedStatus) {
            throw "La solicitud a $Uri respondió $estado, se esperaba $ExpectedStatus."
        }
        return $estado
    }
}

try {
    foreach ($ruta in $backendPython, $rfidPython, $accessPython) {
        if (-not (Test-Path $ruta)) { throw "Falta el entorno virtual: $ruta" }
    }
    foreach ($puerto in 1883, 55432, 8000, 8100, 8200) {
        if (Get-NetTCPConnection -LocalPort $puerto -State Listen -ErrorAction SilentlyContinue) {
            throw "El puerto local $puerto ya está ocupado."
        }
    }

    # Ningún proceso puede heredar accidentalmente la conexión habitual.
    Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
    $env:PUERTOTRACK_RUN_POSTGRES_TESTS = 'PUERTOTRACK_POSTGRES_TEST_ONLY'
    $env:PUERTOTRACK_TEST_DATABASE_URL = 'postgresql+psycopg://puertotrack_test:puertotrack_test_local_only@127.0.0.1:55432/puertotrack_integration_test'

    Invoke-CheckedProcess -FilePath $docker `
        -ArgumentList @('compose', '-f', 'compose.postgres-test.yml', 'up', '-d', '--wait') `
        -WorkingDirectory $backendDir
    $postgresIniciado = $true

    # Alembic solo se ejecuta tras URL, marcador, current_database y current_user.
    Invoke-CheckedProcess -FilePath $backendPython `
        -ArgumentList @('-m', 'pytest', '-q', 'postgres_integration') `
        -WorkingDirectory $backendDir
    Invoke-CheckedProcess -FilePath $backendPython `
        -ArgumentList @('-m', 'scripts.preparar_demo_rfid') `
        -WorkingDirectory $backendDir

    $sufijo = Get-Date -Format 'yyMMddHHmmss'
    $codigoDemo = "ACCS$sufijo"
    Invoke-CheckedProcess -FilePath $backendPython `
        -ArgumentList @('-m', 'scripts.preparar_demo_rfid', '--crear-contenedor', $codigoDemo) `
        -WorkingDirectory $backendDir

    $bytesSupervisor = New-Object byte[] 32
    $bytesOperador = New-Object byte[] 32
    $bytesRfid = New-Object byte[] 48
    $bytesAccess = New-Object byte[] 48
    $bytesJwt = New-Object byte[] 48
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    $rng.GetBytes($bytesSupervisor); $rng.GetBytes($bytesOperador)
    $rng.GetBytes($bytesRfid); $rng.GetBytes($bytesAccess); $rng.GetBytes($bytesJwt)
    $rng.Dispose()
    $env:PUERTOTRACK_TEST_SUPERVISOR_EMAIL = "supervisor.$sufijo@puertotrack.test"
    $env:PUERTOTRACK_TEST_OPERADOR_EMAIL = "operador.$sufijo@puertotrack.test"
    $env:PUERTOTRACK_TEST_SUPERVISOR_PASSWORD = [Convert]::ToBase64String($bytesSupervisor)
    $env:PUERTOTRACK_TEST_OPERADOR_PASSWORD = [Convert]::ToBase64String($bytesOperador)
    Invoke-CheckedProcess -FilePath $backendPython `
        -ArgumentList @('-m', 'scripts.preparar_demo_accesos') `
        -WorkingDirectory $backendDir

    $snapshotAntes = Invoke-CapturedProcess -FilePath $backendPython `
        -ArgumentList @('-m', 'scripts.preparar_demo_rfid', '--snapshot-contenedor', $codigoDemo) `
        -WorkingDirectory $backendDir

    $env:DATABASE_URL = $env:PUERTOTRACK_TEST_DATABASE_URL
    $env:RFID_INTERNAL_API_KEY = [Convert]::ToBase64String($bytesRfid)
    $env:ACCESS_INTERNAL_API_KEY = [Convert]::ToBase64String($bytesAccess)
    $env:JWT_SECRET_KEY = [Convert]::ToBase64String($bytesJwt)
    if ($env:RFID_INTERNAL_API_KEY -eq $env:ACCESS_INTERNAL_API_KEY) {
        throw 'Las claves internas RFID y Accesos no son independientes.'
    }
    $env:ACCESS_TOKEN_EXPIRE_MINUTES = '30'
    $env:PUERTOTRACK_API_URL = 'http://127.0.0.1:8000'
    $env:ACCESS_SERVICE_URL = 'http://127.0.0.1:8200'
    $env:RFID_MQTT_HOST = '127.0.0.1'
    $env:RFID_MQTT_PORT = '1883'
    $env:RFID_MQTT_IDENTIFICATIONS_TOPIC = 'puertotrack/rfid/identificaciones.v1'
    $env:ACCESS_MQTT_HOST = '127.0.0.1'
    $env:ACCESS_MQTT_PORT = '1883'
    $env:PYTHONPATH = Join-Path $rfidDir 'src'

    Invoke-CheckedProcess -FilePath $docker `
        -ArgumentList @('compose', 'up', '-d', '--wait') -WorkingDirectory $rfidDir
    $mqttIniciado = $true

    foreach ($servicio in @(
        @{ Python = $backendPython; Dir = $backendDir; Args = @('-m','uvicorn','main:app','--host','127.0.0.1','--port','8000') },
        @{ Python = $rfidPython; Dir = $rfidDir; Args = @('-m','uvicorn','--app-dir','src','rfid_service.main:app','--host','127.0.0.1','--port','8100') },
        @{ Python = $accessPython; Dir = $accessDir; Args = @('-m','uvicorn','--app-dir','src','access_service.main:app','--host','127.0.0.1','--port','8200') }
    )) {
        $salida = [IO.Path]::GetTempFileName(); $errorProceso = [IO.Path]::GetTempFileName()
        $archivosTemporales += $salida, $errorProceso
        $procesos += Start-Process -FilePath $servicio.Python `
            -ArgumentList $servicio.Args -WorkingDirectory $servicio.Dir `
            -RedirectStandardOutput $salida -RedirectStandardError $errorProceso `
            -PassThru
    }

    $null = Wait-JsonEndpoint 'http://127.0.0.1:8000/health'
    $saludRfid = Wait-JsonEndpoint 'http://127.0.0.1:8100/health'
    $saludAccess = Wait-JsonEndpoint 'http://127.0.0.1:8200/health'
    $limiteMqtt = (Get-Date).AddSeconds(15)
    while ((-not $saludRfid.mqtt_conectado -or -not $saludAccess.mqtt_conectado) -and (Get-Date) -lt $limiteMqtt) {
        Start-Sleep -Milliseconds 250
        $saludRfid = Invoke-RestMethod 'http://127.0.0.1:8100/health'
        $saludAccess = Invoke-RestMethod 'http://127.0.0.1:8200/health'
    }
    if (-not $saludRfid.mqtt_conectado -or -not $saludAccess.mqtt_conectado) {
        throw 'Ambos consumidores deben confirmar su conexión MQTT.'
    }

    $cabeceraAccess = @{'X-PuertoTrack-Access-Key' = $env:ACCESS_INTERNAL_API_KEY}
    $hechos = Invoke-RestMethod `
        -Uri "http://127.0.0.1:8000/internal/access/contenedores/$codigoDemo" `
        -Headers $cabeceraAccess
    if (-not $hechos.existe -or $hechos.codigo -ne $codigoDemo) {
        throw 'FastAPI no está consultando el fixture de la base aislada.'
    }
    $estadoClaveBackend = Assert-HttpStatus `
        -Uri "http://127.0.0.1:8000/internal/access/contenedores/$codigoDemo" `
        -Headers @{'X-PuertoTrack-Access-Key' = 'clave-incorrecta'} `
        -ExpectedStatus 401
    $estadoClaveServicio = Assert-HttpStatus `
        -Uri 'http://127.0.0.1:8200/internal/decisiones' `
        -Headers @{'X-PuertoTrack-Access-Key' = 'clave-incorrecta'} `
        -ExpectedStatus 401

    # Captura una publicación real del topic de resultados antes del evento.
    $resultadoMqtt = [IO.Path]::GetTempFileName()
    $errorMqtt = [IO.Path]::GetTempFileName()
    $archivosTemporales += $resultadoMqtt, $errorMqtt
    $suscriptor = Start-Process -FilePath $docker `
        -ArgumentList @('compose','exec','-T','mosquitto','mosquitto_sub','-h','localhost','-t','puertotrack/accesos/resultados.v1','-C','1','-W','20') `
        -WorkingDirectory $rfidDir -RedirectStandardOutput $resultadoMqtt `
        -RedirectStandardError $errorMqtt -PassThru
    # docker compose exec necesita terminar de abrir la suscripción antes de
    # publicar; sin esta espera el flujo puede completarse antes de la captura.
    Start-Sleep -Seconds 2

    $eventoValido = [guid]::NewGuid()
    Publish-SimulatedEvent -Code $codigoDemo -EventId $eventoValido
    $rfidValido = Wait-RfidState $eventoValido 'valido'
    $accesoValido = Wait-AccessDecision $eventoValido 'habilitado'
    # Con salida redirigida, Windows PowerShell 5.1 puede no poblar ExitCode
    # aunque WaitForExit confirme el fin. La evidencia se valida leyendo JSON.
    if (-not $suscriptor.WaitForExit(20000)) {
        throw 'No se capturó la publicación MQTT del resultado de acceso.'
    }
    $publicado = (Get-Content $resultadoMqtt -Raw | ConvertFrom-Json)
    if ($publicado.evento_id -ne $eventoValido.ToString() -or $publicado.resultado -ne 'habilitado') {
        throw 'El resultado MQTT publicado no corresponde al evento válido.'
    }

    $eventoDesconocido = [guid]::NewGuid()
    Publish-SimulatedEvent -Code 'ACCESSNOEXISTE' -EventId $eventoDesconocido
    $rfidDesconocido = Wait-RfidState $eventoDesconocido 'codigo_desconocido'
    $accesoDesconocido = Wait-AccessDecision $eventoDesconocido 'denegado'
    if ($accesoDesconocido.motivo -ne 'CODIGO_DESCONOCIDO') {
        throw 'El código desconocido no conservó su motivo explícito.'
    }

    $eventoDuplicado = [guid]::NewGuid()
    Publish-SimulatedEvent -Code $codigoDemo -EventId $eventoDuplicado
    $null = Wait-AccessDecision $eventoDuplicado 'habilitado'
    Publish-SimulatedEvent -Code $codigoDemo -EventId $eventoDuplicado
    $rfidDuplicado = Wait-RfidState $eventoDuplicado 'duplicado'
    Start-Sleep -Milliseconds 500
    $decisiones = Invoke-RestMethod -Uri 'http://127.0.0.1:8200/internal/decisiones?limite=100' -Headers $cabeceraAccess
    $cantidadDuplicado = @($decisiones | Where-Object { $_.evento_id -eq $eventoDuplicado.ToString() }).Count
    if ($cantidadDuplicado -ne 1) {
        throw 'El evento RFID duplicado produjo más de una decisión efectiva.'
    }

    $invalidosAntes = [int](Invoke-RestMethod 'http://127.0.0.1:8200/health').mensajes_invalidos
    Invoke-CheckedProcess -FilePath $docker `
        -ArgumentList @('compose','exec','-T','mosquitto','mosquitto_pub','-h','localhost','-t','puertotrack/rfid/identificaciones.v1','-m','mensaje-no-json') `
        -WorkingDirectory $rfidDir
    $limiteInvalido = (Get-Date).AddSeconds(10)
    do {
        Start-Sleep -Milliseconds 200
        $invalidosDespues = [int](Invoke-RestMethod 'http://127.0.0.1:8200/health').mensajes_invalidos
    } while ($invalidosDespues -le $invalidosAntes -and (Get-Date) -lt $limiteInvalido)
    if ($invalidosDespues -le $invalidosAntes) {
        throw 'Accesos no controló el mensaje inválido.'
    }

    $loginSupervisor = Invoke-RestMethod -Method Post `
        -Uri 'http://127.0.0.1:8000/auth/login' `
        -ContentType 'application/x-www-form-urlencoded' `
        -Body @{username=$env:PUERTOTRACK_TEST_SUPERVISOR_EMAIL; password=$env:PUERTOTRACK_TEST_SUPERVISOR_PASSWORD}
    $loginOperador = Invoke-RestMethod -Method Post `
        -Uri 'http://127.0.0.1:8000/auth/login' `
        -ContentType 'application/x-www-form-urlencoded' `
        -Body @{username=$env:PUERTOTRACK_TEST_OPERADOR_EMAIL; password=$env:PUERTOTRACK_TEST_OPERADOR_PASSWORD}
    $consultaSupervisor = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/accesos?limite=50' `
        -Headers @{Authorization="Bearer $($loginSupervisor.access_token)"}
    if (@($consultaSupervisor | Where-Object { $_.evento_id -eq $eventoValido.ToString() }).Count -ne 1) {
        throw 'El proxy de supervisor no devolvió la decisión esperada.'
    }
    $estadoOperador = Assert-HttpStatus -Uri 'http://127.0.0.1:8000/accesos' `
        -Headers @{Authorization="Bearer $($loginOperador.access_token)"} `
        -ExpectedStatus 403

    # Vuelve a retirar DATABASE_URL antes de invocar el verificador protegido.
    $databaseAislada = $env:DATABASE_URL
    Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
    try {
        $snapshotDespues = Invoke-CapturedProcess -FilePath $backendPython `
            -ArgumentList @('-m', 'scripts.preparar_demo_rfid', '--snapshot-contenedor', $codigoDemo) `
            -WorkingDirectory $backendDir
    }
    finally { $env:DATABASE_URL = $databaseAislada }
    if ($snapshotAntes -ne $snapshotDespues) {
        throw 'El flujo de accesos modificó datos operacionales.'
    }

    [pscustomobject]@{
        base_aislada_verificada = $true
        fastapi_misma_base = $true
        mqtt_rfid_conectado = $saludRfid.mqtt_conectado
        mqtt_accesos_conectado = $saludAccess.mqtt_conectado
        identificacion_valida = $rfidValido.estado
        acceso_valido = $accesoValido.resultado
        codigo_desconocido = $accesoDesconocido.resultado
        evento_duplicado = $rfidDuplicado.estado
        decisiones_para_duplicado = $cantidadDuplicado
        mensaje_invalido_controlado = $true
        resultado_mqtt_publicado = $publicado.resultado
        clave_backend_incorrecta_http = $estadoClaveBackend
        clave_servicio_incorrecta_http = $estadoClaveServicio
        supervisor_proxy = 'autorizado'
        operador_proxy_http = $estadoOperador
        datos_operacionales_sin_cambios = $true
    } | ConvertTo-Json
}
finally {
    foreach ($proceso in $procesos) {
        if ($null -ne $proceso -and -not $proceso.HasExited) {
            Stop-Process -Id $proceso.Id -Force -ErrorAction SilentlyContinue
        }
    }
    if ($mqttIniciado) {
        $null = Start-Process -FilePath $docker `
            -ArgumentList @('compose', 'down') -WorkingDirectory $rfidDir `
            -Wait -NoNewWindow -PassThru
    }
    if ($postgresIniciado) {
        $null = Start-Process -FilePath $docker `
            -ArgumentList @('compose','-f','compose.postgres-test.yml','down') `
            -WorkingDirectory $backendDir -Wait -NoNewWindow -PassThru
    }
    foreach ($archivo in $archivosTemporales) {
        Remove-Item $archivo -Force -ErrorAction SilentlyContinue
    }
    Remove-Item Env:DATABASE_URL, Env:PUERTOTRACK_TEST_DATABASE_URL, `
        Env:PUERTOTRACK_RUN_POSTGRES_TESTS, Env:RFID_INTERNAL_API_KEY, `
        Env:ACCESS_INTERNAL_API_KEY, Env:JWT_SECRET_KEY, `
        Env:ACCESS_TOKEN_EXPIRE_MINUTES, Env:PUERTOTRACK_API_URL, `
        Env:ACCESS_SERVICE_URL, Env:RFID_MQTT_HOST, Env:RFID_MQTT_PORT, `
        Env:RFID_MQTT_IDENTIFICATIONS_TOPIC, Env:ACCESS_MQTT_HOST, `
        Env:ACCESS_MQTT_PORT, Env:PYTHONPATH, `
        Env:PUERTOTRACK_TEST_SUPERVISOR_EMAIL, `
        Env:PUERTOTRACK_TEST_OPERADOR_EMAIL, `
        Env:PUERTOTRACK_TEST_SUPERVISOR_PASSWORD, `
        Env:PUERTOTRACK_TEST_OPERADOR_PASSWORD -ErrorAction SilentlyContinue
}
