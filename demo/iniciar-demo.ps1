[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$raiz = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$backendDir = Join-Path $raiz 'backend'
$rfidDir = Join-Path $raiz 'rfid-service'
$accessDir = Join-Path $raiz 'access-service'
$frontendDir = Join-Path $raiz 'frontend'
$runtimeDir = Join-Path $env:LOCALAPPDATA 'PuertoTrackDemo'
$logsDir = Join-Path $runtimeDir 'logs'
$statePath = Join-Path $runtimeDir 'state.json'
$credentialsPath = Join-Path $runtimeDir 'credenciales.clixml'
$backendPython = Join-Path $backendDir '.venv\Scripts\python.exe'
$rfidPython = Join-Path $rfidDir '.venv\Scripts\python.exe'
$accessPython = Join-Path $accessDir '.venv\Scripts\python.exe'
$viteScript = Join-Path $frontendDir 'node_modules\vite\bin\vite.js'
$docker = (Get-Command docker.exe -ErrorAction Stop).Source
$node = (Get-Command node.exe -ErrorAction Stop).Source
$env:PATH = (Split-Path $docker) + ';' + $env:PATH
$postgresIniciado = $false
$mqttIniciado = $false
$procesos = @()

$variablesDemo = @(
    'DATABASE_URL', 'PUERTOTRACK_TEST_DATABASE_URL',
    'PUERTOTRACK_RUN_POSTGRES_TESTS', 'RFID_INTERNAL_API_KEY',
    'ACCESS_INTERNAL_API_KEY', 'JWT_SECRET_KEY',
    'ACCESS_TOKEN_EXPIRE_MINUTES', 'PUERTOTRACK_API_URL',
    'ACCESS_SERVICE_URL', 'RFID_MQTT_HOST', 'RFID_MQTT_PORT',
    'RFID_MQTT_IDENTIFICATIONS_TOPIC', 'ACCESS_MQTT_HOST',
    'ACCESS_MQTT_PORT', 'FRONTEND_ORIGIN', 'VITE_API_URL', 'PYTHONPATH',
    'PUERTOTRACK_DEMO_SUPERVISOR_PASSWORD',
    'PUERTOTRACK_DEMO_OPERADOR_PASSWORD'
)
$entornoAnterior = @{}
foreach ($nombre in $variablesDemo) {
    $entornoAnterior[$nombre] = [Environment]::GetEnvironmentVariable(
        $nombre, [EnvironmentVariableTarget]::Process
    )
}

function Restore-CallerEnvironment {
    foreach ($nombre in $script:variablesDemo) {
        $valor = $script:entornoAnterior[$nombre]
        if ($null -eq $valor) {
            Remove-Item "Env:$nombre" -ErrorAction SilentlyContinue
        }
        else {
            [Environment]::SetEnvironmentVariable(
                $nombre, $valor, [EnvironmentVariableTarget]::Process
            )
        }
    }
}

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
        throw "Un proceso de preparación terminó con código $($proceso.ExitCode)."
    }
}

function Start-DemoProcess {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][string[]]$ArgumentList,
        [Parameter(Mandatory = $true)][string]$WorkingDirectory
    )
    $salida = Join-Path $script:logsDir "$Name.out.log"
    $errores = Join-Path $script:logsDir "$Name.err.log"
    $proceso = Start-Process -FilePath $FilePath `
        -ArgumentList $ArgumentList -WorkingDirectory $WorkingDirectory `
        -RedirectStandardOutput $salida -RedirectStandardError $errores `
        -PassThru
    $script:procesos += [pscustomobject]@{
        Nombre = $Name
        Proceso = $proceso
        Ejecutable = $FilePath
    }
}

function Stop-DemoProcessTree {
    param([int]$ProcessId)
    $hijos = Get-CimInstance Win32_Process `
        -Filter "ParentProcessId = $ProcessId" -ErrorAction SilentlyContinue
    foreach ($hijo in $hijos) {
        Stop-DemoProcessTree -ProcessId ([int]$hijo.ProcessId)
    }
    Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
}

function Wait-JsonEndpoint {
    param(
        [Parameter(Mandatory = $true)][string]$Uri,
        [hashtable]$Headers = @{},
        [int]$TimeoutSeconds = 30
    )
    $limite = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        try { return Invoke-RestMethod -Uri $Uri -Headers $Headers -TimeoutSec 2 }
        catch { Start-Sleep -Milliseconds 300 }
    } while ((Get-Date) -lt $limite)
    throw "El servicio local no respondió: $Uri"
}

function Wait-HttpEndpoint {
    param([Parameter(Mandatory = $true)][string]$Uri)
    $limite = (Get-Date).AddSeconds(30)
    do {
        try {
            $respuesta = Invoke-WebRequest -Uri $Uri -UseBasicParsing -TimeoutSec 2
            if ($respuesta.StatusCode -eq 200) { return }
        }
        catch { Start-Sleep -Milliseconds 300 }
    } while ((Get-Date) -lt $limite)
    throw "El frontend local no respondió: $Uri"
}

function Wait-PortFree {
    param(
        [Parameter(Mandatory = $true)][int]$Port,
        [int]$TimeoutSeconds = 20
    )
    $limite = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        if (-not (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)) {
            return
        }
        Start-Sleep -Milliseconds 250
    } while ((Get-Date) -lt $limite)
    throw "El puerto localhost:$Port no quedó libre después de desmontar PostgreSQL de pruebas."
}

function Assert-GetWithToken {
    param(
        [Parameter(Mandatory = $true)][string]$Uri,
        [Parameter(Mandatory = $true)][string]$Token
    )
    $null = Invoke-RestMethod -Uri $Uri `
        -Headers @{Authorization="Bearer $Token"} -TimeoutSec 4
}

function Get-HttpStatusWithToken {
    param(
        [Parameter(Mandatory = $true)][string]$Uri,
        [Parameter(Mandatory = $true)][string]$Token
    )
    try {
        $null = Invoke-WebRequest -Uri $Uri `
            -Headers @{Authorization="Bearer $Token"} `
            -UseBasicParsing -ErrorAction Stop
        return 200
    }
    catch {
        if ($null -eq $_.Exception.Response) { throw }
        return [int]$_.Exception.Response.StatusCode
    }
}

function New-RandomBase64 {
    param([int]$Bytes = 48)
    $buffer = New-Object byte[] $Bytes
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($buffer) }
    finally { $rng.Dispose() }
    return [Convert]::ToBase64String($buffer)
}

function New-RandomHex {
    param([int]$Bytes = 24)
    $buffer = New-Object byte[] $Bytes
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($buffer) }
    finally { $rng.Dispose() }
    return ([BitConverter]::ToString($buffer)).Replace('-', '').ToLowerInvariant()
}

try {
    if (Test-Path $statePath) {
        throw "Ya existe un estado de demo. Ejecute .\demo\detener-demo.ps1 antes de iniciar otro."
    }
    foreach ($ruta in $backendPython, $rfidPython, $accessPython, $viteScript) {
        if (-not (Test-Path $ruta)) { throw "Falta un requisito local: $ruta" }
    }
    foreach ($puerto in 1883, 55432, 8000, 8100, 8200, 5173) {
        if (Get-NetTCPConnection -LocalPort $puerto -State Listen -ErrorAction SilentlyContinue) {
            throw "El puerto localhost:$puerto ya está ocupado. No se detuvo el proceso ajeno."
        }
    }

    $null = New-Item -ItemType Directory -Path $logsDir -Force

    # URL fija y exclusiva. Los verificadores posteriores también consultan la
    # identidad efectiva y el comentario de la base antes de escribir.
    Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
    $env:PUERTOTRACK_RUN_POSTGRES_TESTS = 'PUERTOTRACK_POSTGRES_TEST_ONLY'
    $env:PUERTOTRACK_TEST_DATABASE_URL = 'postgresql+psycopg://puertotrack_test:puertotrack_test_local_only@127.0.0.1:55432/puertotrack_integration_test'

    Invoke-CheckedProcess -FilePath $docker `
        -ArgumentList @('compose','-f','compose.postgres-test.yml','up','-d','--wait') `
        -WorkingDirectory $backendDir
    $postgresIniciado = $true

    # La suite aplica Alembic solo después de superar todas las barreras.
    Invoke-CheckedProcess -FilePath $backendPython `
        -ArgumentList @('-m','pytest','-q','postgres_integration') `
        -WorkingDirectory $backendDir

    # Las pruebas concurrentes necesitan commits reales. Se descarta todo su
    # PostgreSQL temporal y se crea una instancia limpia para la DEMO.
    Invoke-CheckedProcess -FilePath $docker `
        -ArgumentList @('compose','-f','compose.postgres-test.yml','down','--volumes') `
        -WorkingDirectory $backendDir
    $postgresIniciado = $false
    Wait-PortFree -Port 55432
    Invoke-CheckedProcess -FilePath $docker `
        -ArgumentList @('compose','-f','compose.postgres-test.yml','up','-d','--wait') `
        -WorkingDirectory $backendDir
    $postgresIniciado = $true

    # Primera barrera sobre la nueva instancia: URL, nombre, usuario y marcador
    # se validan sin realizar escrituras antes de ejecutar Alembic.
    Invoke-CheckedProcess -FilePath $backendPython `
        -ArgumentList @('-m','scripts.preparar_demo_rfid') `
        -WorkingDirectory $backendDir
    $env:DATABASE_URL = $env:PUERTOTRACK_TEST_DATABASE_URL
    Invoke-CheckedProcess -FilePath $backendPython `
        -ArgumentList @('-m','alembic','upgrade','head') `
        -WorkingDirectory $backendDir
    Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
    Invoke-CheckedProcess -FilePath $backendPython `
        -ArgumentList @('-m','scripts.verificar_datos_demo','--estado','vacia') `
        -WorkingDirectory $backendDir

    # Hex evita caracteres con semántica especial en formularios URL-encoded.
    $passwordSupervisor = New-RandomHex -Bytes 24
    $passwordOperador = New-RandomHex -Bytes 24
    $env:PUERTOTRACK_DEMO_SUPERVISOR_PASSWORD = $passwordSupervisor
    $env:PUERTOTRACK_DEMO_OPERADOR_PASSWORD = $passwordOperador
    if (
        $env:PUERTOTRACK_DEMO_SUPERVISOR_PASSWORD -cne $passwordSupervisor `
        -or $env:PUERTOTRACK_DEMO_OPERADOR_PASSWORD -cne $passwordOperador
    ) {
        throw 'PowerShell no conservó exactamente las credenciales generadas.'
    }
    Invoke-CheckedProcess -FilePath $backendPython `
        -ArgumentList @('-m','scripts.preparar_demo_interactivo') `
        -WorkingDirectory $backendDir
    Invoke-CheckedProcess -FilePath $backendPython `
        -ArgumentList @('-m','scripts.verificar_datos_demo','--estado','preparada') `
        -WorkingDirectory $backendDir
    Invoke-CheckedProcess -FilePath $backendPython `
        -ArgumentList @('-m','scripts.verificar_credenciales_demo') `
        -WorkingDirectory $backendDir

    $credenciales = @(
        [pscustomobject]@{
            Rol = 'supervisor'
            Credencial = [PSCredential]::new(
                'supervisor.demo@puertotrack.test',
                (ConvertTo-SecureString $passwordSupervisor -AsPlainText -Force)
            )
        },
        [pscustomobject]@{
            Rol = 'operador'
            Credencial = [PSCredential]::new(
                'operador.demo@puertotrack.test',
                (ConvertTo-SecureString $passwordOperador -AsPlainText -Force)
            )
        }
    )
    $credenciales | Export-Clixml -Path $credentialsPath -Force
    Remove-Item Env:PUERTOTRACK_DEMO_SUPERVISOR_PASSWORD, `
        Env:PUERTOTRACK_DEMO_OPERADOR_PASSWORD -ErrorAction SilentlyContinue

    $env:DATABASE_URL = $env:PUERTOTRACK_TEST_DATABASE_URL
    $env:RFID_INTERNAL_API_KEY = New-RandomBase64
    $env:ACCESS_INTERNAL_API_KEY = New-RandomBase64
    $env:JWT_SECRET_KEY = New-RandomBase64
    if ($env:RFID_INTERNAL_API_KEY -eq $env:ACCESS_INTERNAL_API_KEY) {
        throw 'Las claves internas generadas no son independientes.'
    }
    $env:ACCESS_TOKEN_EXPIRE_MINUTES = '120'
    $env:PUERTOTRACK_API_URL = 'http://127.0.0.1:8000'
    $env:ACCESS_SERVICE_URL = 'http://127.0.0.1:8200'
    $env:RFID_MQTT_HOST = '127.0.0.1'
    $env:RFID_MQTT_PORT = '1883'
    $env:RFID_MQTT_IDENTIFICATIONS_TOPIC = 'puertotrack/rfid/identificaciones.v1'
    $env:ACCESS_MQTT_HOST = '127.0.0.1'
    $env:ACCESS_MQTT_PORT = '1883'
    $env:FRONTEND_ORIGIN = 'http://localhost:5173'
    $env:VITE_API_URL = 'http://127.0.0.1:8000'

    Invoke-CheckedProcess -FilePath $docker `
        -ArgumentList @('compose','up','-d','--wait') -WorkingDirectory $rfidDir
    $mqttIniciado = $true

    Start-DemoProcess -Name 'backend' -FilePath $backendPython `
        -ArgumentList @('-m','uvicorn','main:app','--host','127.0.0.1','--port','8000') `
        -WorkingDirectory $backendDir
    Start-DemoProcess -Name 'rfid' -FilePath $rfidPython `
        -ArgumentList @('-m','uvicorn','--app-dir','src','rfid_service.main:app','--host','127.0.0.1','--port','8100') `
        -WorkingDirectory $rfidDir
    Start-DemoProcess -Name 'accesos' -FilePath $accessPython `
        -ArgumentList @('-m','uvicorn','--app-dir','src','access_service.main:app','--host','127.0.0.1','--port','8200') `
        -WorkingDirectory $accessDir
    Start-DemoProcess -Name 'frontend' -FilePath $node `
        -ArgumentList @('node_modules\vite\bin\vite.js','--host','localhost','--port','5173','--strictPort') `
        -WorkingDirectory $frontendDir

    $null = Wait-JsonEndpoint 'http://127.0.0.1:8000/health'
    $saludRfid = Wait-JsonEndpoint 'http://127.0.0.1:8100/health'
    $saludAccess = Wait-JsonEndpoint 'http://127.0.0.1:8200/health'
    Wait-HttpEndpoint 'http://localhost:5173'
    $limiteMqtt = (Get-Date).AddSeconds(15)
    while ((-not $saludRfid.mqtt_conectado -or -not $saludAccess.mqtt_conectado) -and (Get-Date) -lt $limiteMqtt) {
        Start-Sleep -Milliseconds 300
        $saludRfid = Invoke-RestMethod 'http://127.0.0.1:8100/health'
        $saludAccess = Invoke-RestMethod 'http://127.0.0.1:8200/health'
    }
    if (-not $saludRfid.mqtt_conectado -or -not $saludAccess.mqtt_conectado) {
        throw 'Los consumidores RFID y Accesos no confirmaron conexión MQTT.'
    }

    $bodySupervisor = 'username={0}&password={1}' -f `
        [Uri]::EscapeDataString('supervisor.demo@puertotrack.test'), `
        [Uri]::EscapeDataString($passwordSupervisor)
    $bodyOperador = 'username={0}&password={1}' -f `
        [Uri]::EscapeDataString('operador.demo@puertotrack.test'), `
        [Uri]::EscapeDataString($passwordOperador)
    $loginSupervisor = Invoke-RestMethod -Method Post `
        -Uri 'http://127.0.0.1:8000/auth/login' `
        -ContentType 'application/x-www-form-urlencoded' `
        -Body $bodySupervisor
    $loginOperador = Invoke-RestMethod -Method Post `
        -Uri 'http://127.0.0.1:8000/auth/login' `
        -ContentType 'application/x-www-form-urlencoded' `
        -Body $bodyOperador

    foreach ($ruta in @(
        '/dashboard/resumen', '/contenedores?limite=20',
        '/movimientos?limite=20&orden=desc', '/ubicaciones?limite=20'
    )) {
        Assert-GetWithToken "http://127.0.0.1:8000$ruta" $loginSupervisor.access_token
        Assert-GetWithToken "http://127.0.0.1:8000$ruta" $loginOperador.access_token
    }
    Assert-GetWithToken 'http://127.0.0.1:8000/auditoria?limite=20' `
        $loginSupervisor.access_token
    Assert-GetWithToken 'http://127.0.0.1:8000/ubicaciones?incluir_inactivas=true' `
        $loginSupervisor.access_token
    Assert-GetWithToken 'http://127.0.0.1:8000/accesos' `
        $loginSupervisor.access_token
    if ((Get-HttpStatusWithToken 'http://127.0.0.1:8000/auditoria' $loginOperador.access_token) -ne 403) {
        throw 'El operador pudo consultar Auditoría durante la comprobación.'
    }
    if ((Get-HttpStatusWithToken 'http://127.0.0.1:8000/accesos' $loginOperador.access_token) -ne 403) {
        throw 'El operador pudo consultar Accesos durante la comprobación.'
    }

    # Crea una primera decisión visible sin modificar el contenedor.
    $env:PYTHONPATH = Join-Path $rfidDir 'src'
    $eventoInicial = [guid]::NewGuid()
    Invoke-CheckedProcess -FilePath $rfidPython `
        -ArgumentList @('-m','rfid_service.simulator','--codigo','DEMOENTRADA','--lector','PORTICO_DEMO','--evento-id',$eventoInicial.ToString()) `
        -WorkingDirectory $rfidDir
    $cabeceraAccess = @{'X-PuertoTrack-Access-Key'=$env:ACCESS_INTERNAL_API_KEY}
    $decision = Wait-JsonEndpoint `
        -Uri "http://127.0.0.1:8200/internal/decisiones/$eventoInicial" `
        -Headers $cabeceraAccess
    if ($decision.resultado -ne 'habilitado') {
        throw 'La decisión inicial de la demo no fue habilitada.'
    }
    $decisionesProxy = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/accesos' `
        -Headers @{Authorization="Bearer $($loginSupervisor.access_token)"}
    if (@($decisionesProxy | Where-Object { $_.evento_id -eq $eventoInicial.ToString() }).Count -ne 1) {
        throw 'La decisión inicial no quedó visible mediante el proxy supervisor.'
    }

    $estado = [pscustomobject]@{
        Version = 1
        Raiz = $raiz
        IniciadoEn = [DateTime]::UtcNow.ToString('o')
        FrontendUrl = 'http://localhost:5173'
        Procesos = @($procesos | ForEach-Object {
            [pscustomobject]@{
                Nombre = $_.Nombre
                Id = $_.Proceso.Id
                Ejecutable = $_.Ejecutable
            }
        })
        PostgreSqlCompose = (Join-Path $backendDir 'compose.postgres-test.yml')
        MosquittoCompose = (Join-Path $rfidDir 'docker-compose.yml')
    }
    $estado | ConvertTo-Json -Depth 5 | Set-Content -Path $statePath -Encoding UTF8

    Restore-CallerEnvironment
    Write-Host ''
    Write-Host 'PuertoTrack DEMO está activo.' -ForegroundColor Green
    Write-Host 'Frontend: http://localhost:5173'
    Write-Host 'Credenciales: .\demo\mostrar-credenciales-demo.ps1'
    Write-Host 'Simulaciones: .\demo\simular-rfid.ps1 -Escenario habilitado|desconocido|duplicado'
    Write-Host 'Detención: .\demo\detener-demo.ps1'
    Write-Host "Logs locales: $logsDir"
}
catch {
    foreach ($item in $procesos) {
        if ($null -ne $item.Proceso -and -not $item.Proceso.HasExited) {
            Stop-DemoProcessTree -ProcessId $item.Proceso.Id
        }
    }
    if ($mqttIniciado) {
        $null = Start-Process -FilePath $docker `
            -ArgumentList @('compose','-f','docker-compose.yml','down') `
            -WorkingDirectory $rfidDir -Wait -NoNewWindow -PassThru
    }
    if ($postgresIniciado) {
        $null = Start-Process -FilePath $docker `
            -ArgumentList @('compose','-f','compose.postgres-test.yml','down') `
            -WorkingDirectory $backendDir -Wait -NoNewWindow -PassThru
    }
    Remove-Item $runtimeDir -Recurse -Force -ErrorAction SilentlyContinue
    Restore-CallerEnvironment
    throw
}
