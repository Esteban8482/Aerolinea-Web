#!/usr/bin/env bash
# ==============================================================================
# Script de inicio para desarrollo: Backend (Docker Compose) + Frontend (Vite dev)
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================================="
echo "  Iniciando entorno de desarrollo: Alas Aerolinea"
echo "=========================================================="

# 1. Determinar el comando de Docker Compose
if docker compose version >/dev/null 2>&1; then
  COMPOSE_CMD="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE_CMD="docker-compose"
else
  echo "[ERROR] No se encontro 'docker compose' ni 'docker-compose'. Asegurate de que Docker este instalado y en ejecucion." >&2
  exit 1
fi

# Comprobar si el demonio de Docker esta activo
if ! docker info >/dev/null 2>&1; then
  echo ""
  echo "[ALERTA] Docker Desktop no esta ejecutandose."
  echo "Por favor inicia Docker Desktop en Windows y espera a que el motor arranque antes de continuar."
  exit 1
fi

# 2. Verificar o inicializar archivo .env
if [ ! -f ".env" ]; then
  echo "==> Archivo .env no encontrado. Generando uno seguro a partir de .env.example..."
  if [ -f ".env.example" ]; then
    cp .env.example .env
    
    # Generar claves seguras aleatorias
    SECRET_KEY=$(openssl rand -base64 48 2>/dev/null || date +%s%N | sha256sum | head -c 50)
    DB_PASSWORD=$(openssl rand -hex 16 2>/dev/null || date +%s%N | sha256sum | head -c 32)
    
    # Reemplazar valores vacios en .env
    if [[ "$OSTYPE" == "darwin"* ]]; then
      sed -i '' "s/^DJANGO_SECRET_KEY=.*$/DJANGO_SECRET_KEY=${SECRET_KEY}/" .env
      sed -i '' "s/^POSTGRES_PASSWORD=.*$/POSTGRES_PASSWORD=${DB_PASSWORD}/" .env
      sed -i '' "s|^DJANGO_CSRF_TRUSTED_ORIGINS=.*$|DJANGO_CSRF_TRUSTED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173|" .env
      sed -i '' "s|^EMAIL_VERIFICATION_FRONTEND_URL=.*$|EMAIL_VERIFICATION_FRONTEND_URL=http://localhost:5173/verificar|" .env
      sed -i '' "s|^PASSWORD_RECOVERY_FRONTEND_URL=.*$|PASSWORD_RECOVERY_FRONTEND_URL=http://localhost:5173/restablecer|" .env
    else
      sed -i "s/^DJANGO_SECRET_KEY=.*$/DJANGO_SECRET_KEY=${SECRET_KEY}/" .env
      sed -i "s/^POSTGRES_PASSWORD=.*$/POSTGRES_PASSWORD=${DB_PASSWORD}/" .env
      sed -i "s|^DJANGO_CSRF_TRUSTED_ORIGINS=.*$|DJANGO_CSRF_TRUSTED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173|" .env
      sed -i "s|^EMAIL_VERIFICATION_FRONTEND_URL=.*$|EMAIL_VERIFICATION_FRONTEND_URL=http://localhost:5173/verificar|" .env
      sed -i "s|^PASSWORD_RECOVERY_FRONTEND_URL=.*$|PASSWORD_RECOVERY_FRONTEND_URL=http://localhost:5173/restablecer|" .env
    fi
    echo "==> .env creado exitosamente con credenciales locales de desarrollo y origenes CSRF configurados."
  else
    echo "[ERROR] No se encontro el archivo .env.example para generar el entorno." >&2
    exit 1
  fi
else
  # Asegurar que el origen de Vite este en DJANGO_CSRF_TRUSTED_ORIGINS si esta vacio
  if grep -q "^DJANGO_CSRF_TRUSTED_ORIGINS=$" .env; then
    echo "==> Agregando http://localhost:5173 a DJANGO_CSRF_TRUSTED_ORIGINS en .env para conexion segura con Vite..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
      sed -i '' "s|^DJANGO_CSRF_TRUSTED_ORIGINS=.*$|DJANGO_CSRF_TRUSTED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173|" .env
    else
      sed -i "s|^DJANGO_CSRF_TRUSTED_ORIGINS=.*$|DJANGO_CSRF_TRUSTED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173|" .env
    fi
  fi
fi

# 3. Levantar backend con Docker Compose
echo ""
echo "==> [1/3] Levantando base de datos (PostgreSQL) y backend (Django)..."
$COMPOSE_CMD up -d --wait backend

echo "==> [2/3] Aplicando migraciones de base de datos..."
$COMPOSE_CMD exec -T backend python manage.py migrate --noinput

echo "==> Comprobando estado del sistema Django..."
$COMPOSE_CMD exec -T backend python manage.py check

# 4. Verificar Node.js y levantar frontend
echo ""
echo "==> [3/3] Preparando Frontend..."
if ! command -v npm >/dev/null 2>&1; then
  echo "[ADVERTENCIA] No se encontro 'npm' en el PATH actual."
  echo "El backend esta listo en http://127.0.0.1:8000."
  echo "Por favor instala Node.js o ejecuta 'npm run dev' en una terminal con Node."
  exit 0
fi

cd frontend

if [ ! -d "node_modules" ]; then
  echo "==> Instalando dependencias de frontend (npm install)..."
  npm install
fi

# 5. Trap para salida limpia
cleanup() {
  echo ""
  echo "=========================================================="
  echo "  Deteniendo servidor Frontend..."
  echo "=========================================================="
  cd "$SCRIPT_DIR"
  read -t 5 -p "Deseas apagar tambien los contenedores del backend? (s/N, espera 5s): " -r RESPONSE || true
  echo ""
  if [[ "$RESPONSE" =~ ^[Ss]$ ]]; then
    echo "==> Deteniendo contenedores backend..."
    $COMPOSE_CMD stop
  else
    echo "==> Los contenedores del backend siguen activos en segundo plano."
    echo "    (Para detenerlos manualmente luego: $COMPOSE_CMD down o stop)"
  fi
  exit 0
}

trap cleanup INT TERM

echo ""
echo "=========================================================="
echo "  Servicios listos para desarrollo!"
echo "  - Frontend (con recarga en vivo):  http://localhost:5173"
echo "  - Backend API:                     http://127.0.0.1:8000/api/health/"
echo "  - Documentacion Swagger API:       http://127.0.0.1:8000/api/docs/"
echo "=========================================================="
echo "Presiona Ctrl+C en esta terminal para detener el Frontend."
echo ""

npm run dev
