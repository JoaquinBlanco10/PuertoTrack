[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$raiz = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$inicio = Join-Path $PSScriptRoot 'iniciar-demo.ps1'
$detencion = Join-Path $PSScriptRoot 'detener-demo.ps1'
$simulador = Join-Path $PSScriptRoot 'simular-rfid.ps1'
$runtimeDir = Join-Path $env:LOCALAPPDATA 'PuertoTrackDemo'
$statePath = Join-Path $runtimeDir 'state.json'
$resultado = $null

function Assert-ExactValues {
    param(
        [Parameter(Mandatory = $true)][object[]]$Actual,
        [Parameter(Mandatory = $true)][object[]]$Expected,
        [Parameter(Mandatory = $true)][string]$Label
    )
    $diferencias = @(Compare-Object `
        -ReferenceObject @($Expected | Sort-Object) `
        -DifferenceObject @($Actual | Sort-Object))
    if ($diferencias.Count -ne 0) {
        throw "$Label no contiene exclusivamente los datos esperados de la DEMO."
    }
}

try {
    & $inicio
    if (-not (Test-Path $statePath)) { throw 'No se creó el estado de la demo.' }
    $estado = Get-Content $statePath -Raw | ConvertFrom-Json
    foreach ($proceso in @($estado.Procesos)) {
        if (-not (Get-Process -Id ([int]$proceso.Id) -ErrorAction SilentlyContinue)) {
            throw "El proceso $($proceso.Nombre) no quedó activo."
        }
    }
    $backend = Invoke-RestMethod 'http://127.0.0.1:8000/health' -TimeoutSec 3
    $rfid = Invoke-RestMethod 'http://127.0.0.1:8100/health' -TimeoutSec 3
    $accesos = Invoke-RestMethod 'http://127.0.0.1:8200/health' -TimeoutSec 3
    $frontend = Invoke-WebRequest 'http://localhost:5173' -UseBasicParsing -TimeoutSec 3
    if ($backend.estado -ne 'ok' -or -not $rfid.mqtt_conectado -or `
        -not $accesos.mqtt_conectado -or $frontend.StatusCode -ne 200) {
        throw 'Una comprobación de salud posterior al inicio falló.'
    }

    $credenciales = @(Import-Clixml (Join-Path $runtimeDir 'credenciales.clixml'))
    $credencialSupervisor = ($credenciales | Where-Object Rol -eq 'supervisor').Credencial
    $passwordSupervisor = $credencialSupervisor.GetNetworkCredential().Password
    $body = 'username={0}&password={1}' -f `
        [Uri]::EscapeDataString($credencialSupervisor.UserName), `
        [Uri]::EscapeDataString($passwordSupervisor)
    $login = Invoke-RestMethod -Method Post `
        -Uri 'http://127.0.0.1:8000/auth/login' `
        -ContentType 'application/x-www-form-urlencoded' -Body $body
    $headers = @{Authorization="Bearer $($login.access_token)"}
    $perfilSupervisor = Invoke-RestMethod `
        'http://127.0.0.1:8000/auth/me' -Headers $headers
    if (
        $perfilSupervisor.nombre -ne 'Supervisor Demo' -or `
        $perfilSupervisor.rol -ne 'supervisor'
    ) {
        throw 'El perfil supervisor de la demo no conserva el nombre y rol esperados.'
    }
    # Windows PowerShell 5 puede envolver un array JSON dentro de otro array
    # cuando Invoke-RestMethod se usa directamente en @(...). La asignación
    # intermedia garantiza que Where-Object recorra cada ubicación.
    $ubicacionesActivasRespuesta = Invoke-RestMethod `
        'http://127.0.0.1:8000/ubicaciones?limite=100' -Headers $headers
    $ubicacionesActivas = @($ubicacionesActivasRespuesta)
    $ubicacionesTodasRespuesta = Invoke-RestMethod `
        'http://127.0.0.1:8000/ubicaciones?limite=100&incluir_inactivas=true' `
        -Headers $headers
    $ubicacionesTodas = @($ubicacionesTodasRespuesta)
    Assert-ExactValues `
        -Actual @($ubicacionesTodas.codigo) `
        -Expected @('MUELLE_1','PATIO_A','PATIO_B','FUERA_PUERTO','DEPOSITO_EXT','ZONA_INACTIVA') `
        -Label 'El catálogo de ubicaciones'
    Assert-ExactValues `
        -Actual @($ubicacionesActivas.codigo) `
        -Expected @('MUELLE_1','PATIO_A','PATIO_B','FUERA_PUERTO','DEPOSITO_EXT') `
        -Label 'El catálogo activo de ubicaciones'
    if (
        @($ubicacionesActivas | Where-Object tipo -eq 'interna').Count -ne 3 -or `
        @($ubicacionesActivas | Where-Object tipo -eq 'externa').Count -ne 2
    ) {
        throw 'Los destinos activos internos y externos de la DEMO son inesperados.'
    }

    $contenedoresDemoRespuesta = Invoke-RestMethod `
        'http://127.0.0.1:8000/contenedores?limite=100' -Headers $headers
    $contenedoresDemo = @($contenedoresDemoRespuesta)
    Assert-ExactValues `
        -Actual @($contenedoresDemo.codigo) `
        -Expected @('DEMOENTRADA','DEMOTRASLADO','DEMOSALIDA','DEMOREINGRESO','DEMOHISTORIAL') `
        -Label 'El inventario de contenedores'
    $dashboardDemo = Invoke-RestMethod `
        'http://127.0.0.1:8000/dashboard/resumen' -Headers $headers
    if (
        $dashboardDemo.contenedores.dentro_puerto -ne 3 -or `
        $dashboardDemo.contenedores.fuera_puerto -ne 1 -or `
        $dashboardDemo.contenedores.presencia_sin_confirmar -ne 1 -or `
        $dashboardDemo.contenedores.inconsistentes -ne 0
    ) {
        throw 'El Dashboard contiene totales ajenos a los fixtures de la DEMO.'
    }
    $contenedorAntes = Invoke-RestMethod `
        'http://127.0.0.1:8000/contenedores/codigo/DEMOENTRADA' -Headers $headers
    $movimientosRespuestaAntes = Invoke-RestMethod `
        'http://127.0.0.1:8000/movimientos?limite=100&orden=desc' -Headers $headers
    $movimientosAntes = @($movimientosRespuestaAntes)
    $auditoriaRespuestaAntes = Invoke-RestMethod `
        'http://127.0.0.1:8000/auditoria?limite=100' -Headers $headers
    $auditoriaAntes = @($auditoriaRespuestaAntes)
    if ($movimientosAntes.Count -ne 6 -or $auditoriaAntes.Count -ne 18) {
        throw 'El historial o la auditoría contienen datos residuales de pruebas.'
    }

    $eventoHabilitado = & $simulador -Escenario habilitado -Passthru
    $eventoDesconocido = & $simulador -Escenario desconocido -Passthru
    $eventoDuplicado = & $simulador -Escenario duplicado -Passthru

    $limiteDecisiones = (Get-Date).AddSeconds(15)
    do {
        Start-Sleep -Milliseconds 300
        $decisionesRespuesta = Invoke-RestMethod `
            'http://127.0.0.1:8000/accesos?limite=100' -Headers $headers
        $decisiones = @($decisionesRespuesta)
        $habilitada = @($decisiones | Where-Object evento_id -eq $eventoHabilitado.EventoId)
        $desconocida = @($decisiones | Where-Object evento_id -eq $eventoDesconocido.EventoId)
        $duplicada = @($decisiones | Where-Object evento_id -eq $eventoDuplicado.EventoId)
    } while (
        ($habilitada.Count -ne 1 -or $desconocida.Count -ne 1 -or `
        $duplicada.Count -ne 1) -and (Get-Date) -lt $limiteDecisiones
    )
    if ($habilitada.Count -ne 1 -or $habilitada[0].resultado -ne 'habilitado') {
        $resultadoObservado = if ($habilitada.Count -eq 1) {
            [string]$habilitada[0].resultado
        } else { 'ausente' }
        throw "La simulación habilitada no apareció correctamente en el proxy React (cantidad=$($habilitada.Count), resultado=$resultadoObservado)."
    }
    if ($desconocida.Count -ne 1 -or $desconocida[0].resultado -ne 'denegado') {
        throw 'La simulación desconocida no apareció como denegada.'
    }
    if ($duplicada.Count -ne 1) {
        throw 'El evento duplicado no produjo exactamente una decisión.'
    }

    $contenedorDespues = Invoke-RestMethod `
        'http://127.0.0.1:8000/contenedores/codigo/DEMOENTRADA' -Headers $headers
    $movimientosRespuestaDespues = Invoke-RestMethod `
        'http://127.0.0.1:8000/movimientos?limite=100&orden=desc' -Headers $headers
    $movimientosDespues = @($movimientosRespuestaDespues)
    $auditoriaRespuestaDespues = Invoke-RestMethod `
        'http://127.0.0.1:8000/auditoria?limite=100' -Headers $headers
    $auditoriaDespues = @($auditoriaRespuestaDespues)
    if (
        $contenedorAntes.estado -ne $contenedorDespues.estado -or `
        $contenedorAntes.ubicacion_actual_id -ne $contenedorDespues.ubicacion_actual_id -or `
        $movimientosAntes.Count -ne $movimientosDespues.Count -or `
        $auditoriaAntes.Count -ne $auditoriaDespues.Count
    ) {
        throw 'Una simulación RFID modificó datos operacionales o auditoría.'
    }

    # Comprueba una operación real únicamente en la base efímera, después de
    # verificar que RFID no modificó datos operacionales.
    $contenedorTraslado = Invoke-RestMethod `
        'http://127.0.0.1:8000/contenedores/codigo/DEMOTRASLADO' -Headers $headers
    $patioB = $ubicacionesActivas | Where-Object codigo -eq 'PATIO_B' | Select-Object -First 1
    if ($null -eq $patioB -or $contenedorTraslado.ubicacion_actual_id -eq $patioB.id) {
        throw 'No existe un destino alternativo válido para comprobar el traslado.'
    }
    $movimientoRegistrado = Invoke-RestMethod -Method Post `
        -Uri 'http://127.0.0.1:8000/movimientos' `
        -Headers $headers -ContentType 'application/json' `
        -Body (@{
            contenedor_id = $contenedorTraslado.id
            tipo = 'traslado'
            ubicacion_destino_id = $patioB.id
            observacion = 'Validación automatizada de la DEMO aislada.'
        } | ConvertTo-Json)
    $contenedorTrasladado = Invoke-RestMethod `
        'http://127.0.0.1:8000/contenedores/codigo/DEMOTRASLADO' -Headers $headers
    if (
        $movimientoRegistrado.tipo -ne 'traslado' -or `
        $contenedorTrasladado.ubicacion_actual_id -ne $patioB.id -or `
        $contenedorTrasladado.estado -ne 'en_patio'
    ) {
        throw 'El traslado de comprobación no actualizó coherentemente la DEMO.'
    }
    $resultado = [pscustomobject]@{
        inicio = 'correcto'
        backend = $backend.estado
        rfid_mqtt = $rfid.mqtt_conectado
        accesos_mqtt = $accesos.mqtt_conectado
        frontend_http = $frontend.StatusCode
        perfil_supervisor = $perfilSupervisor.nombre
        rol_supervisor = $perfilSupervisor.rol
        escenario_habilitado = $habilitada[0].resultado
        escenario_desconocido = $desconocida[0].resultado
        decisiones_evento_duplicado = $duplicada.Count
        datos_operacionales_sin_cambios = $true
        ubicaciones_demo = $ubicacionesTodas.Count
        ubicaciones_activas = $ubicacionesActivas.Count
        movimiento_demo = $movimientoRegistrado.tipo
    }
}
finally {
    if (Test-Path $statePath) { & $detencion }
}

foreach ($puerto in 1883, 55432, 8000, 8100, 8200, 5173) {
    if (Get-NetTCPConnection -LocalPort $puerto -State Listen -ErrorAction SilentlyContinue) {
        throw "El puerto $puerto continuó ocupado después de detener la demo."
    }
}
if (Test-Path $runtimeDir) {
    throw 'El directorio temporal de la demo no fue eliminado.'
}
$resultado | Add-Member -NotePropertyName detencion -NotePropertyValue 'correcta'
$resultado | ConvertTo-Json
