# Revisión verificable de BASE-01

Fecha: **2026-10-16**. Rama: **BASE-01**, autorizada expresamente por el usuario durante
el encargo. Se contrastó la implementación de Copilot con el texto íntegro del encargo
original y con las fuentes disponibles. Este documento registra evidencia, no sustituye
la ERS ni cierra historias de usuario.

**Estado:** implementación técnica preparada y verificada localmente. El cierre integral
queda **parcialmente bloqueado en la revisión documental** porque el enunciado original
`Proyecto_Lab_Soft_2026-02.pdf` no está disponible en el clon. GitHub Actions está preparado,
pero su ejecución remota sigue pendiente; no fue autorizada la publicación de estos cambios.
Las verificaciones externas de despliegue pertenecen a una etapa posterior.

## Inspección y fuentes

- Raíz comprobada: `Aerolinea-Web`, sin repositorio anidado ni cambio de rama.
- Se conservaron los cambios locales de Copilot. No se hicieron commits, push, PR, merges,
  modificaciones remotas ni instalaciones globales durante esta revisión.
- Se leyeron `README.md`, `REGLASCOMMITS.md`, los dos `AGENTS.md` y el complemento completo.
  Las instrucciones de los agentes y las reglas de commits no se modificaron para justificar
  decisiones de implementación.
- Se consultaron ERS, HU-007/008/009, CU-07/08/09, ER, diagramas de usuarios/finanzas y mockups.
  Las huellas de los PDF y el DOCX coinciden con las documentadas. `ERS.pdf` corresponde a
  la fuente denominada `ERS(1).pdf` en el complemento.
- No están `Proyecto_Lab_Soft_2026-02.pdf` ni el programa `is714-laboratorio-de-software(1).pdf`.
  No se inventó su contenido. El segundo es contexto académico; el primero impide cerrar
  la comparación completa solicitada con el enunciado.
- `.venv` usa Python 3.12.3 y se conservó. Ya hay Python 3.13.16 disponible; las verificaciones
  finales se realizaron en Linux con Python 3.13.16, principalmente dentro de Docker.
- El impedimento inicial de Docker/WSL ya no existe: se detectaron Docker 29.8.2 y Compose
  5.6.0. El sandbox requirió acceso autorizado al socket Docker.
- El volumen existente `aerolinea-web_postgres_data` contenía PostgreSQL 17.11, la migración
  `users.0001_initial` aplicada y **cero cuentas**. Se conservó; no se reinicializó.

## Hallazgos y correcciones

| Hallazgo en la primera implementación | Corrección y ubicación |
|---|---|
| Faltaban datos personales de RF-USU-05/06. | `apps/users/models.py`: documento textual no único, nacimiento, lugar, facturación, género y referencia opcional a imagen. Conserva nombres/apellidos y fecha de creación de Django. |
| `username` era reemplazado por el correo; root descartaba el correo opcional. | Se separan nombre de perfil, correo normalizado y `root_id`; correo opcional root conservado y único entre las cuentas que lo utilizan. |
| La búsqueda ambigua por username/correo podía mezclar identidades. | `AccountBackend` recibe explícitamente `email` o `root_id`, conserva las mismas reglas en llamadas síncronas y asíncronas y deniega cuentas inactivas. No hay endpoint de login. |
| Separar ROOT de privilegios Django se interpretó como prohibirle tenerlos. | Se retiró esa prohibición en una migración nueva; el rol no activa privilegios técnicos automáticamente. No se añadieron permisos de negocio. |
| Faltaba la billetera mínima; bootstrap podía crear una cuenta sin ella. | Nuevo modelo `Wallet`, usuario único, saldo decimal cero, restricción no negativo, sin fecha propia. Bootstrap técnico en servicio transaccional con pruebas de rollback y concurrencia. |
| Era necesario preservar la migración inicial y cualquier dato previo. | `users.0001_initial` intacta; nueva `0002` adapta identificadores y perfil. `wallets.0001/0002` crean el modelo y las billeteras de cuentas previas. Sin datos personales inventados ni borrado de tablas anteriores. |
| `/admin/` incorporaba un acceso y gestión fuera de los flujos acordados. | Ruta y aplicación admin retiradas. Sus tablas previas se conservan; no se altera su historial. |
| Settings compartidos incluían secreto y conexión por defecto; podían aceptar otros motores. | Parámetros obligatorios, solo PostgreSQL, sin fallback; producción no lee `.env` local. |
| Pruebas heredaban configuración local y usaban MD5. | `TEST_DATABASE_URL` explícita con base `test_*`, sin leer `.env`; correo en memoria y Argon2 real. |
| Producción confiaba siempre en cabeceras del proxy y activaba preload/subdominios sin contexto. | Confianza explícita y opcional en proxy; HSTS positivo obligatorio; advertencias de preload/subdominios conservadas y documentadas. |
| Salud no distinguía aplicación y base. | Respuesta con estado de ambos, 503 controlado y tiempo de conexión limitado; validado con PostgreSQL realmente detenido. |
| Faltaban logging seguro, convenciones API y SMTP. | Formato sin mensajes arbitrarios/SQL/cuerpos/tracebacks, errores comunes, paginación, decimales, configuración SMTP sin envíos reales y guía del proxy del frontend. |
| Imagen PostgreSQL sin parche explícito, sin healthcheck del backend ni `.dockerignore`. | PostgreSQL 17.11, comprobaciones de ambos servicios, instalación con hashes, usuario no privilegiado y exclusión de archivos sensibles/generados del contexto. |
| Faltaban migración explícita y validación de esquema en CI. | Workflow con PostgreSQL vacío, `migrate`, detección de cambios pendientes, Ruff, pytest y validación estricta de OpenAPI. |
| Plantilla vacía con nombre no reconocido y documentación incompleta. | `.github/pull_request_template.md`, guía operativa actualizada y este reporte. La plantilla no aprueba la convención P-07. |

## Matriz del encargo original

| Área solicitada | Resultado verificable |
|---|---|
| Diagnóstico real y conservación del trabajo | Rama y raíz comprobadas; migración inicial, `.venv` y volumen conservados. Fuentes ausentes identificadas. |
| Alcance y decisiones | DEC-03/04/10/11/12 aplicadas a la base; DEC-15 registra la autorización limitada de P-02. Otros P-XX no se resolvieron por inferencia. |
| Dependencias por grupo | `.in`/`.txt` existentes preservados, hashes instalados y grupos contrastados; desarrollo/producción coinciden con base, herramientas con desarrollo. Sin dependencias nuevas del producto. |
| Django | Configuración por entorno, PostgreSQL obligatorio, sesiones/CSRF/Argon2, UTC, API, logging y correo sin envío real. |
| Usuario y billetera | Usuario en primera migración; migraciones adicionales compatibles, perfil mínimo y billetera sin operaciones financieras. |
| Docker y contrato | Compose de desarrollo, opción de puerto local, stages separados, Gunicorn comprobado y Nginx como referencia futura. Contrato documentado. |
| Pruebas y CI | 40 pruebas, PostgreSQL real, comprobaciones estáticas/migraciones/OpenAPI y workflow preparado. GitHub no ejecutado. |
| Documentación | README general conservado y actualizado, guía ejecutable, decisiones trazables y plantilla reconocida. |
| Límites del encargo | Sin frontend, CRUD general, JWT, Redis/Celery, pasarelas, AWS, cuentas reales, correo real ni operaciones Git remotas. |
| Entrega | Comandos y versiones en `backend/README.md`; evidencia y límites en este archivo. |

## Evidencia ejecutada

Python 3.13.16; Django 5.2.18; DRF 3.18.3; PostgreSQL 17.11; psycopg 3.3.6;
drf-spectacular 0.30.0; argon2-cffi 25.1.0; Gunicorn 26.2.0; pip-tools 7.6.2;
Ruff 0.17.1; pytest 9.1.1, pytest-django 4.14.0 y pytest-cov 7.1.0.

| Comprobación | Resultado observado |
|---|---|
| Instalación Docker desarrollo y producción con `--require-hashes` | Correcta; versiones instaladas coinciden con los locks. |
| `python -m pip check` y consistencia entre los cuatro locks | Sin dependencias rotas ni versiones comunes divergentes. |
| `ruff check .`, `ruff format --check .` | Correctos. |
| `manage.py check` | Sin incidencias. |
| Migraciones sobre el volumen anterior | Nuevas migraciones aplicadas sin reinicializarlo. |
| `migrate` sobre base PostgreSQL nueva y vacía | Correcto; secuencia de CI reproducida localmente en una base efímera propia. |
| `migrate --check`, `makemigrations --check --dry-run` | Sin migraciones pendientes ni cambios sin migración. |
| `pytest --cov --cov-report=term-missing --cov-fail-under=70` | **40 pruebas aprobadas; 80,12 %** sobre `apps` + `config`. |
| Actualización de cuentas del esquema inicial | Conserva PK, correo, datos existentes y hashes; root pasa a ID explícito; billeteras cero. |
| Bootstrap concurrente | Dos conexiones, barrera real: una cuenta root y una billetera, sin duplicados. |
| Restricciones y seguridad | Perfil de cliente, documento no único, correo normalizado/único, saldo no negativo, rollback, Argon2, CSRF y credenciales síncronas/asíncronas comprobados. |
| Configuración de producción en subprocesos | Rechaza secretos/parámetros ausentes, SQLite, comodines y SMTP incompatible. No envía correos. |
| `spectacular --validate --fail-on-warn` | Correcto, sin advertencias. |
| Salud con caída real de PostgreSQL | HTTP 503 sin detalle sensible; recupera HTTP 200 al restaurar PostgreSQL. |
| Imagen de producción / Gunicorn | Build correcto; Gunicorn responde sin root, sin puertos publicados y con filesystem en solo lectura. Salud 200; admin/docs/schema 404 en producción. |
| `check --deploy --fail-level ERROR` | Sin errores; **W005 y W021** visibles por HSTS de subdominios/preload. No se ocultaron. |
| Compose/YAML y `git diff --check` | Configuración y sintaxis comprobadas; diff sin errores de espacios. |

La cobertura es una medida del código local evaluado. La configuración de producción
se prueba en subprocesos y no aporta a ese porcentaje. No acredita la cobertura de las
HU futuras, cumplimiento de seguridad normativo, disponibilidad ni rendimiento productivo.

Los resultados anteriores son de esta revisión local, no una reproducción de las afirmaciones
del resumen de Copilot. El workflow de GitHub todavía no tiene una ejecución remota atribuible
a estos cambios.

## Archivos y decisiones de mantenimiento

- Se conservan y completan `backend/apps/users/`, `config/`, `Dockerfile`, `pyproject.toml`,
  `requirements/` y `scripts/`; se añade `apps/wallets/` y pruebas de configuración/seguridad.
- Se completan `compose.yaml`, `.env.example`, `.github/workflows/backend-ci.yml` y los README.
  Se añaden `compose.local.yaml`, `backend/.dockerignore`, la plantilla de PR reconocida y
  `deploy/nginx.conf.example`.
- Se documenta P-02/DEC-15 en el complemento 1.0.1 con fecha y autorización; se conserva
  la distinción entre base del modelo y permisos financieros aún no acordados.
- `.env` local quedó preparado e ignorado por Git. Conserva las credenciales compatibles
  con el volumen previo y una clave de aplicación generada; no debe reutilizarse en producción.
  Cambiar la contraseña de una base ya inicializada requiere rotarla en PostgreSQL y actualizar
  su configuración, no solo editar `.env`.
- Al cerrar se detuvieron los servicios de validación y se conservó el volumen PostgreSQL.
  Para reanudar, ejecutar `docker compose up --build -d --wait` desde la raíz.
- No se creó root ni ninguna cuenta de negocio en la base de desarrollo. Los datos sintéticos
  usados para probar migraciones y concurrencia pertenecieron a bases/esquemas efímeros.
- La guía explica las migraciones de datos sin reversión automática. No se borró la primera
  migración para simplificar el resultado.

## Pendientes y límites explícitos

1. **Documento faltante:** incorporar el enunciado original para completar la comparación
   solicitada. La ausencia se conserva como limitación, no como permiso para inferir reglas.
2. **GitHub:** ejecutar el workflow cuando el equipo autorice el flujo de Git/PR. P-07 sigue
   pendiente; esta tarea local y su plantilla no lo resuelven.
3. **HU futuras:** registro/login/logout, verificación/recuperación, cierre por inactividad,
   control de intentos, listas de contraseñas comprometidas y permisos de rol/propiedad.
   `CommonPasswordValidator` solo aporta la lista común de Django, no una verificación completa
   de contraseñas comprometidas. Los 1800 s de cookie no implementan por sí solos inactividad.
4. **Otros pendientes del complemento:** P-01, P-03, P-04, P-05 y P-06 conservan sus estados.
   Moneda común y permisos financieros deben definirse antes de sus endpoints. No hay depósitos,
   retiros, reservas, compras, reembolsos ni algoritmos de promociones.
5. **Integración y despliegue:** frontend no inicializado; proxy Vite documentado, no probado.
   Nginx es una referencia sin ejecutar; faltan DNS/certificados, infraestructura, backups y
   verificaciones operativas del despliegue. AWS y correo real no se utilizaron.
6. **Interfaz de documentación:** Swagger UI usa un CDN con versión explícita; se comprobó
   la respuesta HTML y el contrato OpenAPI, no una sesión visual de navegador.

## Referencias técnicas de la revisión

- [Django 5.2: compatibilidad de Python](https://docs.djangoproject.com/en/5.2/releases/5.2/).
- [Django 5.2: PostgreSQL y psycopg](https://docs.djangoproject.com/en/5.2/ref/databases/).
- [DRF: sesiones y CSRF](https://www.django-rest-framework.org/api-guide/authentication/).
- [pip-tools: compilación de dependencias](https://pip-tools.pypa.io/en/stable/).
- [Swagger UI: proyecto y versiones oficiales](https://github.com/swagger-api/swagger-ui).

Las fuentes técnicas respaldan compatibilidad y uso de herramientas; las reglas del dominio
proceden de los documentos del proyecto y de las decisiones expresamente autorizadas.
