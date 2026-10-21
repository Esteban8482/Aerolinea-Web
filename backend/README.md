# Backend de Aerolínea Web

Punto de entrada para el equipo: [entrega de iteración 1](../docs/backend/ITERACION-01.md),
con flujos conjuntos, tareas periódicas, revisión y pendientes.

Base técnica del monolito Django/DRF con PostgreSQL. El estado y la evidencia de BASE-01
están en [la revisión técnica](../docs/BASE-01_VERIFICACION.md). Las reglas de negocio
siguen en [el complemento](../docs/ACLARACIONES_Y_LINEAMIENTOS_DEL_PROYECTO.md).
HU-007 incorpora un núcleo de registro y verificación con correo persistente y pruebas.
El registro en desarrollo admite una política identificada como prueba y requiere salida
HTTPS a la API oficial de Pwned Passwords. El registro público en producción queda deshabilitado sin política
real aprobada. Consulta [contrato, estado y evidencia de HU-007](../docs/backend/HU-007.md)
y [comprobación de contraseñas](../docs/backend/HU-007_COMPROBACION_CONTRASENAS.md).
La consulta tiene tres segundos de espera total y falla con 503 `password_check_unavailable`;
no necesita API key, corpus, importador, volúmenes adicionales ni dependencias nuevas.
La evidencia histórica del usuario y la nueva ejecución del agente se atribuyen en la guía.
HU-008 incorpora login/logout, actividad explícita, bloqueo y recuperación; consulta
[contratos y operación de HU-008](../docs/backend/HU-008.md). Ventas y operaciones de billetera
siguen fuera de estas entregas.
HU-009 añade altas/listado de administradores y cambio propio de contraseña ROOT;
[guía HU-009](../docs/backend/HU-009.md) documenta permisos, límites, migración y avisos.
El procesador adicional se ejecuta después de migrar:

```bash
docker compose exec -T backend python manage.py process_administrator_notifications --batch-size 100
```

Programarlo junto a los procesadores existentes corresponde a integración. No requiere
variables ni dependencias nuevas y no envía contraseñas por correo.

## Versiones y requisitos

| Componente | Versión comprobada |
|---|---|
| Python | 3.13.16, Linux |
| Django | 5.2.18, serie 5.2 LTS |
| DRF / drf-spectacular | 3.18.3 / 0.30.0 |
| PostgreSQL / psycopg | 17.11 / 3.3.6 |
| Argon2 / Gunicorn | argon2-cffi 25.1.0 / 26.2.0 |
| pytest / pytest-django / pytest-cov | 9.1.1 / 4.14.0 / 7.1.0 |
| Ruff / pip-tools | 0.17.1 / 7.6.2 |

Docker Engine y Compose deben estar disponibles desde WSL. En esta revisión se usaron
Docker 29.8.2 y Compose 5.6.0. No se modificó `.venv`, que aún usa Python 3.12.3.
Las dependencias exactas y sus hashes están en `requirements/*.txt`.

## Desarrollo con Compose

Ejecuta los siguientes comandos **en WSL, desde la raíz del repositorio**. En este clon
ya quedó un `.env` local ignorado por Git, compatible con el volumen existente. No lo
sobrescribas ni cambies la contraseña de ese volumen solo editando variables.

En un clon nuevo, sin `.env` ni base inicializada, genera valores locales sin mostrarlos:

```bash
python3 - <<'PY'
from pathlib import Path
import os, secrets
text = Path('.env.example').read_text()
text = text.replace('DJANGO_SECRET_KEY=\n', 'DJANGO_SECRET_KEY=' + secrets.token_urlsafe(64) + '\n')
text = text.replace('POSTGRES_PASSWORD=\n', 'POSTGRES_PASSWORD=' + secrets.token_hex(32) + '\n')
fd = os.open('.env', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, 'w') as file:
    file.write(text)
PY
```

El ejemplo contiene valores vacíos a propósito: **no ejecutes Compose con
`--env-file .env.example`**. El archivo `.env` de desarrollo no es una configuración de
producción. Si el volumen ya existe, utiliza sus credenciales; los valores `POSTGRES_*`
solo inicializan una base vacía y no rotan contraseñas existentes.

```bash
docker compose up --build -d --wait
docker compose exec backend python manage.py migrate --noinput
docker compose exec backend python manage.py check
```

`exec backend` ejecuta la parte posterior **dentro del contenedor**, en `/app`.
PostgreSQL usa el volumen `aerolinea-web_postgres_data`; Compose no publica su puerto.
El backend se publica únicamente en `127.0.0.1:8000`. Las migraciones son explícitas,
no se ejecutan automáticamente al iniciar cada proceso web.

- Salud: <http://localhost:8000/api/health/>.
- OpenAPI: <http://localhost:8000/api/schema/>.
- Swagger UI: <http://localhost:8000/api/docs/>.

La documentación usa Swagger UI 5.32.9 desde un CDN; el navegador necesita conectividad
para cargar la interfaz. El JSON/YAML de OpenAPI y su validación no dependen del CDN.

Para crear deliberadamente la cuenta inicial, desde WSL con terminal interactiva:

```bash
docker compose exec backend python manage.py create_root --root-id root
```

Solicita la contraseña dos veces; no existe una contraseña predeterminada. Admite
`--email` opcional. Crea root y billetera en una transacción, valida la contraseña y es
idempotente incluso ante dos ejecuciones simultáneas. Una repetición conserva las
credenciales existentes. No se creó ninguna cuenta real durante la revisión.
`createsuperuser` y Django Admin no son los flujos de administración del negocio.

Para detener sin eliminar el volumen:

```bash
docker compose stop
```

## Variables

| Variable | Uso |
|---|---|
| `DJANGO_SECRET_KEY` | Obligatoria en desarrollo/producción; generar aleatoriamente. |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | Inicialización local de PostgreSQL; contraseña obligatoria. |
| `BACKEND_PORT` | Puerto local del backend, 8000 por defecto. |
| `POSTGRES_PORT` | Puerto local opcional de `compose.local.yaml`, 5432 por defecto. |
| `DATABASE_URL` | Obligatoria para Django en desarrollo/producción. Solo PostgreSQL; sin fallback. Compose la construye con host `db`. |
| `TEST_DATABASE_URL` | Obligatoria y separada para pruebas; nombre de base `test_*`. Compose la proporciona con host `db`. |
| `DJANGO_SETTINGS_MODULE` | `config.settings.development`, `.test` o `.production`. |
| `DJANGO_DEBUG` | Solo desarrollo. Producción y pruebas fijan `False`. |
| `DJANGO_ALLOWED_HOSTS` | Lista separada por comas; obligatoria y sin `*` en producción. |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Vacía para desarrollo con mismo origen; en producción exige orígenes HTTPS explícitos. |
| `DB_CONN_MAX_AGE` | Reutilización de conexiones en producción; desarrollo/pruebas usan 0. |
| `DJANGO_SECURE_HSTS_SECONDS` | Obligatoria y positiva en producción. |
| `DJANGO_TRUST_PROXY` | `false` por defecto; habilitar solo detrás de un proxy que reemplace las cabeceras recibidas. |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | SMTP obligatorio en producción. |
| `EMAIL_USE_TLS`, `EMAIL_USE_SSL`, `DEFAULT_FROM_EMAIL` | SMTP: exactamente uno de TLS/SSL; remitente explícito. |
| `EMAIL_VERIFICATION_FRONTEND_URL` | HU-007: pantalla de verificación, sin query ni fragmento; HTTPS fuera de DEBUG. Vacía mientras no se configure; necesaria para procesar correo. |
| `PASSWORD_RECOVERY_FRONTEND_URL` | HU-008: pantalla de restablecimiento, sin query/fragmento; HTTPS fuera de DEBUG. Necesaria para procesar correo de recuperación. |
| `REGISTRATION_POLICY_REFERENCE`, `REGISTRATION_POLICY_VERSION`, `REGISTRATION_POLICY_URL` | Política vigente validada por el servidor; documento de prueba en desarrollo. |
| `REGISTRATION_POLICY_APPROVED`, `REGISTRATION_POLICY_IS_TEST` | Producción exige aprobación real y documento no sintético; pendiente documental. |
| `PRIVATE_MEDIA_ROOT` | Almacenamiento privado de imágenes; Compose monta su volumen, sin URL pública. |
| `REGISTRATION_TRUSTED_PROXIES` | Peers autorizados para X-Real-IP, compartidos por los controles de origen de HU-007/HU-008/HU-009; vacía por defecto. |
| `WEB_CONCURRENCY` | Procesos Gunicorn; 2 por defecto, ajustar con mediciones al desplegar. |

Desarrollo lee `.env` de la raíz, sin sustituir variables ya exportadas; fuerza correo de
consola. Pruebas **no leen `.env`**, usan correo en memoria y mantienen Argon2. Producción
solo toma variables del proceso y no utiliza credenciales de desarrollo como fallback.
Nunca se probó el envío SMTP real. En desarrollo utiliza únicamente destinatarios y datos
ficticios: el backend de consola imprime el contenido del correo deliberadamente.

## Django directamente en WSL (opcional)

Con Python **3.13.16** disponible, desde la raíz, sin reemplazar el entorno anterior:

```bash
python3.13 -m venv .venv-313
source .venv-313/bin/activate
python -m pip install --require-hashes -r backend/requirements/development.txt
docker compose -f compose.yaml -f compose.local.yaml up -d db
```

Configura `DATABASE_URL` en `.env` con las credenciales del volumen y el host
`127.0.0.1:5432` (o `POSTGRES_PORT`). Dentro de Compose el host es **`db:5432`**;
ese nombre no resuelve desde WSL. Codifica caracteres reservados de la contraseña al
construir una URL. El generador anterior usa hexadecimal para la clave PostgreSQL.
Si mantienes también el backend de Compose, utiliza otro puerto para el proceso local:

```bash
cd backend
python manage.py migrate --noinput
python manage.py runserver 127.0.0.1:8001
```

Para pruebas locales, exporta explícitamente `TEST_DATABASE_URL` con una base dedicada
como `test_aerolinea`; no basta con añadirla al `.env`, que las pruebas no leen.
pytest crea y elimina su propia base `test_test_aerolinea`. El rol de pruebas necesita
`CREATEDB`; nunca uses credenciales de producción para estas comprobaciones.

## Verificación y dependencias

Desde WSL, raíz del repositorio, con los servicios iniciados:

```bash
docker compose exec backend python -m pip check
docker compose exec backend ruff check .
docker compose exec backend ruff format --check .
docker compose exec backend python manage.py check
docker compose exec backend python manage.py migrate --check
docker compose exec backend python manage.py makemigrations --check --dry-run
docker compose exec -e DJANGO_SETTINGS_MODULE=config.settings.test backend pytest --cov --cov-report=term-missing --cov-fail-under=70
docker compose exec -e DJANGO_SETTINGS_MODULE=config.settings.test backend python manage.py spectacular --validate --fail-on-warn --file /tmp/schema.yaml
```

El `-e` de pytest es necesario: el contenedor normalmente exporta settings de desarrollo.
CI utiliza un PostgreSQL vacío, ejecuta migraciones explícitas y también estas verificaciones.
La prueba de actualización usa un esquema efímero en la base de pytest para verificar datos
del modelo anterior. La prueba concurrente usa conexiones separadas y una barrera real.

La cobertura de configuración ejecutada en subprocesos no se incorpora al porcentaje.
No se declara cumplimiento de las HU ni del objetivo completo de cobertura de negocio
por medir esta infraestructura.

Para modificar dependencias, usa Python 3.13.16/Linux, con las herramientas fijadas,
y ejecuta **desde `backend/` en el entorno virtual**:

```bash
python -m pip install --require-hashes -r requirements/tools.txt
bash scripts/compile_requirements.sh
python -m pip install --require-hashes -r requirements/development.txt
python -m pip check
```

Se resuelve primero `tools`, luego `base`, `development` y `production`. Los dos últimos
incluyen base y la restringen con `base.txt`; desarrollo también respeta `tools.txt`.
No edites a mano versiones ni hashes en los `.txt`. El script conserva las fijaciones
existentes; una actualización deliberada debe revisar el diff y volver a verificar el stack.

## Estructura y usuario mínimo

- `config/settings/`: configuración común y diferencias explícitas por entorno.
- `config/`: rutas, salud, contrato de errores y logging de infraestructura.
- `apps/users/`: usuario, bootstrap y backend HU-007/008/009 con pruebas; ver sus guías.
- `apps/wallets/`: persistencia mínima de billetera, sin operaciones financieras.
- `requirements/`, `scripts/`, `Dockerfile`: entorno y resolución reproducible.

Mantener modelos para persistencia/restricciones, serializers para entradas/salidas,
servicios para transacciones/casos de uso, y vistas/permisos para HTTP y autorización.
No se generaron aplicaciones vacías ni repositorios genéricos para todas las HU.

El modelo conserva los nombres de campos existentes en inglés. Correspondencia con ERS/ER:

| Concepto | Campo |
|---|---|
| ID técnico | `id`, BigAutoField |
| ID de acceso root | `root_id`; solo para ROOT, independiente del ID técnico |
| Correo de acceso cliente/administrador | `email`, normalizado, único sin distinguir mayúsculas |
| Nombre de usuario de perfil | `username`; no es el correo ni una credencial de acceso |
| Nombres/apellidos | `first_name`, `last_name` |
| Tipo y número documental (DNI) | `document_type`, `document_number`; número textual, no único |
| Nacimiento | `birth_date`, `birth_place` |
| Facturación/género | `billing_address`, `gender` |
| Imagen opcional de registro | `profile_image`, archivo privado validado y recodificado por HU-007; `profile_image_url` queda como campo anterior no admitido en registro HTTP |
| Creación/verificación | `date_joined`, `is_email_verified` |

Clientes: `full_clean()` exige los datos de RF-USU-05. Administradores: correo obligatorio
con perfil completado posteriormente según RF-USU-06. Root: ID y contraseña, con correo y
perfil opcionales. No se inventaron catálogos de género/documentos. DEC-17 establece las
reglas de imagen de HU-007. Los managers son primitivas de persistencia; el registro público
usa servicios para validar entradas, fijar rol y crear cuenta+billetera atómicamente. Django
no llama automáticamente `full_clean()` al hacer un `save()` directo.

La billetera tiene usuario único, saldo `Decimal(14,2)` inicialmente cero y restricción
contra saldo negativo; no contiene fecha de creación ni movimientos. `PROTECT` evita
eliminar una cuenta que tenga billetera. No habilita permisos financieros para ningún rol.

`users.0001_initial` se conserva. `0002_user_profile_and_identifiers` traslada los antiguos
IDs root y separa las copias técnicas del correo del nombre de perfil. Las cuentas anteriores
sin datos de perfil no reciben datos ficticios. La migración se detiene si encuentra un nombre
real de más de 40 caracteres; necesita revisión humana, no truncamiento. Las migraciones de
billetera crean cuentas de saldo cero para los usuarios previos a este módulo. Estas
migraciones de datos no tienen reversión automática; cualquier vuelta atrás requiere un
plan y respaldo. No se borraron tablas anteriores de Django Admin ni registros de migración.

## Contrato API e integración futura

| Ruta | Estado |
|---|---|
| `/api/health/` | Pública, ejecuta `SELECT 1` en PostgreSQL. |
| `/api/schema/`, `/api/docs/` | Públicas solo en desarrollo/pruebas; deshabilitadas en producción. |
| `/api/v1/auth/` | HU-007: CSRF, política vigente, registro, confirmación y reenvío; [contrato y comandos](../docs/backend/HU-007.md). |

Salud devuelve `status`, `application` y `database`: HTTP 200 con los tres valores `ok`;
HTTP 503 con `application: ok` y los otros dos `unavailable` si falla la consulta. No
certifica migraciones aplicadas, integridad financiera ni disponibilidad de SMTP.

Convenciones compartidas:

- Sesión en PostgreSQL, cookie HttpOnly y SameSite=Lax; cookies Secure en producción.
  Autenticación DRF exclusivamente por sesión; permisos `IsAuthenticated` por defecto.
  Los permisos por rol y propiedad deben añadirse con cada HU, incluidos los usuarios
  con privilegios técnicos. El rol ROOT no concede automáticamente `is_staff`/`is_superuser`.
- CSRF obligatorio para operaciones autenticadas y para los POST públicos de HU-007/HU-008.
  Obtener `csrf_token` de `GET /api/v1/auth/csrf/`, enviar `X-CSRFToken` y cookie `csrftoken`.
  DRF por sí solo no protege visitantes; las vistas públicas usan `csrf_protect`. Login
  de HU-008 también exige CSRF sin sesión y rota el token tras autenticar.
- HU-008 verifica los 1800 s de inactividad mediante estado compartido en PostgreSQL.
  Solo POST `/api/v1/auth/session/activity/` tras interacción real renueva el plazo; GET y
  polling no renuevan. Logout revoca en servidor. Ver contrato y límites en la guía de HU-008.
- Dinero en JSON como cadena decimal y moneda explícita; la moneda común aún debe acordarse
  antes de los endpoints financieros. No usar float. Fechas ISO 8601 con zona; UTC interno
  y zona IANA para la presentación local de futuros vuelos.
- Paginación por `page`, 20 elementos, respuesta `count`, `next`, `previous`, `results`.
  Los filtros se documentarán al existir las listas.
- Errores DRF: `code` estable, `message` en español y `details` por campo para validación.
  Fallos inesperados devuelven `internal_error` sin traceback. Con sesiones, ausencia de
  autenticación puede ser 403 `not_authenticated`; un 403 `csrf_failed` o `permission_denied`
  tiene otro significado. Las rutas inexistentes devuelven `not_found` con DEBUG=False.
  Salud tiene el contrato específico anterior. Conflictos de negocio se definirán con sus HU.

Durante desarrollo, el futuro Vite debe servir un solo origen para el navegador y pasar
`/api` al backend con proxy, preservando `Host` (`changeOrigin: false`). Añadir
`localhost`/`127.0.0.1` a hosts ya está previsto; no desactivar CSRF ni habilitar CORS universal.
Ejemplo orientativo para la configuración futura de Vite, sin inicializar frontend:

```ts
server: {
  proxy: {
    '/api': { target: 'http://127.0.0.1:8000', changeOrigin: false }
  }
}
```

Usar rutas relativas (`fetch('/api/...', { credentials: 'same-origin', ... })`) y token CSRF
para métodos que cambien datos. Si el proxy se ejecuta en otro contenedor, adaptar el destino
a `backend:8000`. Esta integración no está probada porque el frontend no existe aún.

## Destino de producción

El stage `production` instala únicamente base + Gunicorn y ejecuta como usuario `app`.
`compose.yaml` es exclusivamente desarrollo: no es un despliegue productivo.

```bash
docker build --target production -t aerolinea-backend:base01 ./backend
```

Antes de un despliegue autorizado, integración debe proporcionar variables y secretos reales,
red privada para Gunicorn/PostgreSQL, rol de base con privilegios mínimos, DNS, certificados,
backups y almacenamiento de estáticos. El rol creado por la imagen PostgreSQL local es de
administración del entorno de desarrollo; no reutilizarlo como rol productivo.

[deploy/nginx.conf.example](../deploy/nginx.conf.example) muestra el destino Nginx/TLS y el
reemplazo de cabeceras del proxy. Es una referencia sin desplegar ni validar con certificados
reales. Deben coordinarse `collectstatic`, migraciones y reinicio de workers. No hay AWS ni
automatización de despliegue en BASE-01.

Producción fuerza HTTPS, cookies seguras, HSTS y rechaza parámetros faltantes. `check --deploy`
reporta W005 y W021: no se fuerza HSTS en todos los subdominios ni inscripción en preload sin
una decisión del dominio. No están silenciadas. Cambiar esos valores requiere revisar la
infraestructura real. Logging de Django emite fecha, severidad, logger, evento seguro y código
HTTP cuando está disponible; no serializa SQL, mensajes arbitrarios, cuerpos ni excepciones.
Gunicorn omite rutas, consultas y cabeceras en el access log y también usa el formato seguro
para sus errores. No sustituye la futura bitácora.

## Problemas frecuentes en WSL

- `docker` no encontrado: activar integración con la distribución en Docker Desktop, o
  verificar el motor Docker ya instalado. No reinstalar ni cambiar grupos automáticamente.
- Permiso denegado en `/var/run/docker.sock`: comprobar el acceso del usuario al motor;
  en esta sesión el sandbox necesitó autorización para acceder al socket.
- `db` no resuelve desde WSL: utilizar `compose.local.yaml` y `127.0.0.1` para el backend local.
- Puerto ocupado: ajustar `BACKEND_PORT`/`POSTGRES_PORT` o usar otro puerto local para Django.
- Fallo de contraseña tras editar `.env`: un volumen existente conserva su contraseña anterior;
  recuperar la configuración correcta o coordinar una rotación. No borrar el volumen.
- Fallo de escritura al generar migraciones dentro del contenedor: el proceso no es root;
  generarlas en el entorno Python local compatible o ejecutar Compose con el UID/GID del
  propietario para esa operación. Revisar siempre el diff de las migraciones generadas.
- PyPI/CDN inaccesible: comprobar conectividad. No fabricar locks, quitar hashes ni sustituir
  PostgreSQL por SQLite para aparentar una verificación exitosa.
