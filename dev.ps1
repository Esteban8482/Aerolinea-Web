# ==============================================================================
# Script PowerShell para desarrollo: Backend (Docker Compose) + Frontend (Vite)
# ==============================================================================
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Iniciando entorno de desarrollo: Alas Aerolinea" -ForegroundColor Cyan
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

# Comprobar si el motor de Docker (Docker Desktop) esta corriendo
Write-Host "==> Comprobando conexion con Docker Desktop..." -ForegroundColor Yellow
$dockerRunning = $false
try {
    $null = docker info 2>&1
    if ($LASTEXITCODE -eq 0) {
        $dockerRunning = $true
    }
} catch {
    $dockerRunning = $false
}

if (-not $dockerRunning) {
    Write-Host ""
    Write-Host "[ALERTA] Docker Desktop NO esta ejecutandose o aun esta arrancando." -ForegroundColor Red
    Write-Host "Por favor abre la aplicacion 'Docker Desktop' en Windows y espera a que el icono este en verde ('Engine running')." -ForegroundColor Yellow
    
    $desktopPath = "$env:LOCALAPPDATA\Programs\DockerDesktop\Docker Desktop.exe"
    if (Test-Path $desktopPath) {
        Write-Host "Intentando abrir Docker Desktop automaticamente..." -ForegroundColor Cyan
        Start-Process $desktopPath
        Write-Host "Esperando a que Docker inicie (puede tardar ~20 segundos)..." -ForegroundColor Yellow
        $retries = 30
        while ($retries -gt 0 -and -not $dockerRunning) {
            Start-Sleep -Seconds 3
            try {
                $null = docker info 2>&1
                if ($LASTEXITCODE -eq 0) { $dockerRunning = $true; break }
            } catch {}
            $retries--
            Write-Host -NoNewline "."
        }
        Write-Host ""
    }

    if (-not $dockerRunning) {
        Write-Host "[ERROR] Docker Desktop no respondio. Inicialo manualmente y vuelve a ejecutar este script." -ForegroundColor Red
        exit 1
    }
    Write-Host "==> Docker Desktop conectado exitosamente." -ForegroundColor Green
}

# 2. Comprobar o inicializar .env
if (-not (Test-Path ".env")) {
    Write-Host "==> Archivo .env no encontrado. Generando uno seguro a partir de .env.example..." -ForegroundColor Yellow
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"

        $secretKey = [Convert]::ToBase64String((1..48 | ForEach-Object { Get-Random -Minimum 0 -Maximum 256 } | ForEach-Object { [byte]$_ }))
        $postgresPassword = -join ((1..32) | ForEach-Object { '{0:x}' -f (Get-Random -Minimum 0 -Maximum 16) })

        (Get-Content ".env") |
            ForEach-Object { $_ -replace "^DJANGO_SECRET_KEY=.*", "DJANGO_SECRET_KEY=$secretKey" } |
            ForEach-Object { $_ -replace "^POSTGRES_PASSWORD=.*", "POSTGRES_PASSWORD=$postgresPassword" } |
            ForEach-Object { $_ -replace "^DJANGO_CSRF_TRUSTED_ORIGINS=.*", "DJANGO_CSRF_TRUSTED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173" } |
            ForEach-Object { $_ -replace "^EMAIL_VERIFICATION_FRONTEND_URL=.*", "EMAIL_VERIFICATION_FRONTEND_URL=http://localhost:5173/verificar" } |
            ForEach-Object { $_ -replace "^PASSWORD_RECOVERY_FRONTEND_URL=.*", "PASSWORD_RECOVERY_FRONTEND_URL=http://localhost:5173/restablecer" } |
            Set-Content ".env"

        Write-Host "==> .env creado con credenciales de desarrollo y origenes CSRF configurados." -ForegroundColor Green
    }
} else {
    $content = Get-Content ".env" -Raw
    if ($content -match "DJANGO_CSRF_TRUSTED_ORIGINS=\r?\n") {
        Write-Host "==> Configurando DJANGO_CSRF_TRUSTED_ORIGINS en .env para conexion con Vite..." -ForegroundColor Yellow
        (Get-Content ".env") |
            ForEach-Object { $_ -replace "^DJANGO_CSRF_TRUSTED_ORIGINS=$", "DJANGO_CSRF_TRUSTED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173" } |
            Set-Content ".env"
    }
}

# 3. Levantar backend
Write-Host "`n==> [1/3] Levantando base de datos (PostgreSQL) y backend (Django)..." -ForegroundColor Yellow
& docker compose up -d --wait backend

Write-Host "==> [2/3] Aplicando migraciones de base de datos..." -ForegroundColor Yellow
& docker compose exec -T backend python manage.py migrate --noinput

Write-Host "==> Comprobando estado del sistema Django..." -ForegroundColor Yellow
& docker compose exec -T backend python manage.py check

# 4. Levantar frontend
Write-Host "`n==> [3/3] Preparando Frontend..." -ForegroundColor Yellow
Set-Location "$scriptDir\frontend"

if (-not (Test-Path "node_modules")) {
    Write-Host "==> Instalando dependencias de frontend (npm install)..." -ForegroundColor Yellow
    npm install
}

Write-Host "`n==========================================================" -ForegroundColor Green
Write-Host "  Servicios listos para desarrollo!" -ForegroundColor Green
Write-Host "  - Frontend (con recarga en vivo):  http://localhost:5173" -ForegroundColor Green
Write-Host "  - Backend API:                     http://127.0.0.1:8000/api/health/" -ForegroundColor Green
Write-Host "  - Documentacion Swagger API:       http://127.0.0.1:8000/api/docs/" -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "Presiona Ctrl+C en esta terminal para detener el Frontend.`n"

npm run dev
