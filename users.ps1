# ==============================================================================
# Script PowerShell para desarrollo: Listar usuarios y credenciales conocidas
# ==============================================================================
param(
    # Restablece las contrasenas de los usuarios demo a sus valores sinteticos.
    [switch]$ResetDemo
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Usuarios del entorno de desarrollo: Alas Aerolinea" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Comprobar Docker Compose y Docker Engine
$composeCmd = ""
if (Get-Command "docker" -ErrorAction SilentlyContinue) {
    try {
        docker compose version | Out-Null
        $composeCmd = "docker compose"
    } catch {
        if (Get-Command "docker-compose" -ErrorAction SilentlyContinue) {
            $composeCmd = "docker-compose"
        }
    }
}

if (-not $composeCmd) {
    Write-Host "[ERROR] No se encontro 'docker compose' en el sistema." -ForegroundColor Red
    exit 1
}

try {
    $null = docker info 2>&1
    if ($LASTEXITCODE -ne 0) { throw }
} catch {
    Write-Host "[ERROR] Docker Desktop no esta ejecutandose. Inicialo y vuelve a intentar." -ForegroundColor Red
    exit 1
}

# 2. Asegurar que el backend este activo
$backendRunning = $false
try {
    $containerId = (docker compose ps -q backend 2>$null)
    if ($containerId) { $backendRunning = $true }
} catch {}

if (-not $backendRunning) {
    Write-Host "==> El backend no esta activo. Levantandolo..." -ForegroundColor Yellow
    docker compose up -d --wait backend
}

# 3. Listar usuarios
if ($ResetDemo) {
    docker compose exec -T backend python manage.py list_dev_users --reset-demo
} else {
    docker compose exec -T backend python manage.py list_dev_users
}
