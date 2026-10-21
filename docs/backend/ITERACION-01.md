# Iteración 1 — Usuarios: entrega a frontend e integración

Revisión del **2026-10-21**, rama `iteracion/01-usuarios`. Incluye el backend de HU-007,
HU-008 y HU-009. Punto de entrada operativo; [informe de revisión](ITERACION-01_REVISION.md)
registra hallazgos, evidencia, correspondencia con el diseño y pendientes. El alcance
implementado permite integrar los flujos siguientes; no acredita frontend terminado ni producción.

## Orden de lectura

1. Esta guía y [backend/README.md](../../backend/README.md): arranque y configuración.
2. [Complemento vigente](../ACLARACIONES_Y_LINEAMIENTOS_DEL_PROYECTO.md), especialmente
   §§1.2, 9 y 11: precedencia, DEC-10/11/15–22, seguridad y contrato común.
3. [HU-007](HU-007.md), [HU-008](HU-008.md), [HU-009](HU-009.md): solicitudes, respuestas,
   errores, cuotas, estados y ejemplos. Sus informes de implementación son históricos.
4. OpenAPI servido por el backend: `/api/schema/` y `/api/docs/` en desarrollo/pruebas.
5. [Revisión y diseño](ITERACION-01_REVISION.md): límites de la entrega antes de cerrar la iteración.

Para herramientas IA, leer antes [AGENTS.md](../../AGENTS.md) y [docs/AGENTS.md](../AGENTS.md).
Los contratos describen el código; una discrepancia con requisitos debe registrarse, no
convertirse en aprobación implícita. No se requiere recuperar esta conversación.

## Arranque y configuración

Desde la raíz del clon, en WSL/Linux con Docker Compose. Conservar el `.env` y volúmenes
existentes. En un clon nuevo seguir el generador seguro del [README backend](../../backend/README.md#desarrollo-con-compose):
`.env.example` tiene secretos vacíos. Completar `DJANGO_SECRET_KEY` y `POSTGRES_PASSWORD`
sin versionarlos; Compose proporciona DATABASE_URL y TEST_DATABASE_URL.

```bash
docker compose up --build -d --wait
docker compose exec -T backend python manage.py migrate --noinput
docker compose exec -T backend python manage.py check
docker compose exec -T backend python manage.py migrate --check
```

PostgreSQL fijado en **17.11**. Migraciones actuales: users hasta `0006`, wallets hasta
`0002`, además de auth/contenttypes/sessions. No hay migración nueva por esta revisión.
Salud: `http://localhost:8000/api/health/`; documentación: `http://localhost:8000/api/docs/`.
No usar `down -v` ni recrear la base para aplicar migraciones compartidas.

En `.env` de desarrollo configurar las pantallas que implementará frontend, por ejemplo:

```dotenv
EMAIL_VERIFICATION_FRONTEND_URL=http://localhost:5173/verificar
PASSWORD_RECOVERY_FRONTEND_URL=http://localhost:5173/restablecer
```

Son destinos del navegador, no endpoints POST de API. Deben ser URL absolutas sin query,
fragmento ni credenciales; HTTPS fuera de DEBUG. Tras cambiar variables de Compose,
recrear el contenedor con `docker compose up -d backend`; `exec` hereda su entorno.

La política sintética usa `REGISTRATION_POLICY_REFERENCE`, `REGISTRATION_POLICY_VERSION`
y `REGISTRATION_POLICY_URL`. Frontend debe leer la vigente desde API, mostrar el documento
y exigir aceptación explícita. Producción requiere además aprobación real documentada,
`REGISTRATION_POLICY_APPROVED=true` y `REGISTRATION_POLICY_IS_TEST=false`; permanece
bloqueada sin ella. Los flags no convierten un documento de prueba en política aprobada.

Alta de cliente/administrador y cambios/restablecimientos de clave necesitan DNS y HTTPS
hacia `api.pwnedpasswords.com:443`. [Contrato del proveedor](HU-007_COMPROBACION_CONTRASENAS.md):
3 s, sin fallback; fallo 503 sin guardar la operación. No instalar corpus ni importador.
Login no consulta ese servicio. Bootstrap técnico `create_root` usa validadores locales.
Imágenes privadas: volumen configurado por Compose; nunca publicar su carpeta como estáticos.

## Cuentas y datos de desarrollo

Usar nombres/documentos sintéticos y correos `example.invalid`. No hay seed masivo ni
contraseñas predeterminadas. Aprovisionar ROOT de forma interactiva cuando no exista:

```bash
docker compose exec backend python manage.py create_root --root-id root
```

`--email root@example.invalid` es opcional y permite probar recuperación. El comando es
idempotente: repetirlo no cambia clave ni correo del ROOT existente. No usar SQL directo,
`createsuperuser` o Django Admin como sustitutos de los servicios de negocio.

Crear CLIENTE mediante registro de HU-007; crear ADMINISTRADOR con sesión ROOT mediante
HU-009. Ambos servicios crean su billetera cero. No hay endpoint de edición de perfiles,
completado de administrador, imagen privada descargable ni cambio de roles en esta entrega.
No presentar el estado mínimo de sesión como un perfil completo.

## Integración del navegador

Usar el mismo origen para frontend/API, también mediante proxy de Vite para `/api` en
local. Mantener coherentes host/origen y cookies; si el proxy cambia Host, configurar el
origen frontend concreto en `DJANGO_CSRF_TRUSTED_ORIGINS`. Esa opción no habilita CORS.
No hay configuración CORS para frontend/API en dominios distintos; acordarla antes de
cambiar la topología. No desactivar CSRF ni sustituir sesiones por JWT.

- Usar `credentials: 'include'`. Obtener `GET /api/v1/auth/csrf/`, conservar cookie
  `csrftoken` y enviar el valor `csrf_token` en `X-CSRFToken` para todos los POST.
- `sessionid` es HttpOnly; no leerlo ni almacenarlo en localStorage. Login rota sesión y
  CSRF: obtener CSRF nuevo tras éxito. Cookies Secure en producción, SameSite=Lax.
- Consultar `GET /api/v1/auth/session/` para `authenticated`, `role`, `is_email_verified`.
  Los roles son ROOT/ADMINISTRADOR/CLIENTE; staff/superuser no conceden permisos de negocio.
- Solo `POST /api/v1/auth/session/activity/` renueva los 30 minutos, tras interacción real
  y como máximo una vez/minuto. Polling, CSRF, salud y otros endpoints no renuevan actividad.
- Tras logout o cambio/restablecimiento de clave, limpiar estado de frontend. Todas las
  sesiones anteriores a un cambio de contraseña dejan de autenticar en su próxima petición.
  Una petición ya autenticada y en curso no se deshace retroactivamente.
- Cuenta inactiva no autentica, no recupera y no consume un enlace de verificación. Cuenta
  activa sin verificar sí autentica; no habilitar reserva/compra/billetera por ese motivo.
  Las futuras API deberán combinar rol, verificación y propiedad.

## Flujos que pueden conectarse

| Flujo | Guía y comportamiento que debe respetar frontend |
|---|---|
| Registro | [HU-007](HU-007.md): política vigente, consentimiento, JSON o multipart con imagen opcional; 201 sin login automático |
| Verificación/reenvío | Enlace `#token=...`; extraer al estado de la pantalla y retirar del historial con replaceState. POST explícito, no confirmar con GET ni al cargar la vista. Reenvío sustituye enlaces anteriores |
| Login/logout/actividad | [HU-008](HU-008.md): email para clientes/administradores, root_id para ROOT; claves sin recortar; renovar CSRF tras login |
| Recuperación | Solicitud genérica 202; enlace 30 min en fragmento; confirmar nueva clave y POST. No verifica correo ni inicia sesión. ROOT sin correo no tiene recuperación alternativa |
| Administradores | [HU-009](HU-009.md): solo ROOT crea/lista; campos permitidos estrictos; aviso sin contraseña. El nuevo administrador accede por HU-008 |
| Contraseña ROOT | Actual/nueva/confirmación; solo la propia cuenta, cuotas separadas del login. Invalida también enlaces de recuperación emitidos con su hash anterior |

Recuperar la contraseña de un cliente no consume su enlace de verificación de correo;
verificar el correo no reinicia contraseñas ni cuotas. Si se cambia el hash por actualización
interna durante login, un enlace de recuperación basado en el hash anterior también deja
de ser válido: solicitar uno nuevo. No comunicar que la recuperación verifica identidad
para otras operaciones financieras.

Errores tienen `{code,message,details}`. Usar `code`, no solo HTTP: 403 puede ser sesión,
permiso o CSRF; 401 `current_password_invalid` no es logout; 409 puede ser duplicado,
enlace usado o sesión invalidada concurrentemente. Respetar `Retry-After` en 429 y ofrecer
reintento manual ante 503. No registrar cuerpos con claves/tokens, cookies ni fragmentos.
Los códigos y parámetros completos siguen en cada HU/OpenAPI.

## Correo y tareas periódicas

En desarrollo el backend de consola imprime enlaces: salida privada, datos sintéticos.
Pruebas usan memoria y simulan el proveedor de contraseñas. SMTP real requiere settings de
producción, secretos, remitente y URL de pantalla reales, según README backend; Compose
actual es de desarrollo. No confundir correo aceptado localmente con entrega en destino.

```bash
docker compose exec -T backend python manage.py process_verification_emails --batch-size 100
docker compose exec -T backend python manage.py process_recovery_emails --batch-size 100
docker compose exec -T backend python manage.py process_administrator_notifications --batch-size 100
docker compose exec -T backend python manage.py clearsessions
```

Integración debe programar los tres procesadores cada minuto y `clearsessions` periódicamente
(por ejemplo, diariamente). No existe un scheduler instalado. Los avisos se reclaman después
del commit, con leases/reintentos; son entregas potencialmente repetidas si el proceso cae
tras SMTP. Nunca duplican cuenta ni consumo del enlace. Vigilar pendientes, antigüedad,
fallos y vencimientos; probar SMTP y medir el objetivo de cinco minutos. No borrar eventos,
consentimientos o contadores para simular éxito; su retención requiere acuerdo del equipo.

## Comprobación breve y siguiente paso

En desarrollo, con cuotas disponibles y datos sintéticos: obtener política/CSRF; registrar
cliente; procesar verificación por consola; iniciar sesión antes de verificar y comprobar
`is_email_verified=false`; confirmar enlace y consultar sesión; recuperar contraseña,
comprobar sesión anterior invalidada y nuevo login. En otra sesión ROOT, crear administrador,
procesar aviso y verificar que el administrador no puede crear otro. Cambiar clave de ROOT
y comprobar invalidación. Seguir ejemplos y estados de las HU; no poner tokens en query.

La prueba automatizada focalizada del flujo cruzado, sin red ni correos reales, es:

```bash
docker compose exec -T -e DJANGO_SETTINGS_MODULE=config.settings.test backend pytest -q apps/users/tests/test_iteration1.py
```

La [revisión](ITERACION-01_REVISION.md) distingue lo ejecutado de esta guía manual. Frontend
puede comenzar con estas API. Integración debe resolver configuración de pantallas, proxy,
programación y SMTP; responsable funcional aporta política aprobada y asigna el completado
de perfil pendiente. La aceptación del diseño y revisión humana siguen siendo del equipo.
