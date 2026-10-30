[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$credentialsPath = Join-Path $env:LOCALAPPDATA 'PuertoTrackDemo\credenciales.clixml'
if (-not (Test-Path $credentialsPath)) {
    throw 'No hay credenciales DEMO activas. Ejecute primero .\demo\iniciar-demo.ps1.'
}

$registros = @(Import-Clixml -Path $credentialsPath)
Write-Host 'Credenciales temporales (visibles solo en esta consola):' -ForegroundColor Yellow
foreach ($registro in $registros) {
    Write-Host ''
    Write-Host "Rol: $($registro.Rol)"
    Write-Host "Correo: $($registro.Credencial.UserName)"
    Write-Host "Contraseña: $($registro.Credencial.GetNetworkCredential().Password)"
}
Write-Host ''
Write-Host 'Se eliminan al ejecutar detener-demo.ps1.'
