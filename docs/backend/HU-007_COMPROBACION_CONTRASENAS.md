# HU-007 — comprobación de contraseñas por rango

Vigente desde **2026-10-20**, autorización del usuario que sustituye exclusivamente la
estrategia local de DEC-17 (§9.5 del complemento). No se descarga el corpus masivo.

La [documentación oficial de Pwned Passwords](https://haveibeenpwned.com/API/v3#PwnedPasswords)
define el servicio gratuito sin API key: SHA-1 de la contraseña UTF-8, primeros cinco
caracteres hexadecimales en una petición GET, sufijos y frecuencias en la respuesta.
`Add-Padding: true` agrega registros con frecuencia cero para reducir información inferible
por el tamaño de respuesta. Estos registros no indican contraseñas comprometidas.

## Configuración y salida de red

`apps/users/password_check.py` fija el host `api.pwnedpasswords.com`, puerto HTTPS 443,
ruta `/range/` y verificación de certificados/hostname con `ssl.create_default_context()`.
`config/settings/base.py` fija `PWNED_PASSWORDS_TIMEOUT_SECONDS = 3`, común a desarrollo,
pruebas y producción. No hay variables para sustituir el destino, desactivar el control,
seguir redirecciones, reintentar o usar un corpus/fallback. No se requiere secreto adicional.

Integración debe permitir DNS y salida TCP 443 a ese host, con almacén de CA del sistema
actualizado y hora correcta. Un proxy que requiera configuración explícita no se utiliza
mediante variables HTTP_PROXY/HTTPS_PROXY: la conexión es directa. Verificar la conectividad
desde el contenedor de backend y sin desactivar TLS. No publicar prefijos, tráfico o cuerpos
capturados en los logs de infraestructura. Salud y otros módulos no realizan estas consultas.

Se usa la biblioteca estándar de Python 3.13.16; no cambian requirements ni locks.
El tiempo de socket por sí solo no incluye DNS ni acota todas las lecturas acumuladas.
Por eso un hilo daemon ejecuta únicamente la conexión HTTP mientras el solicitante espera
como máximo tres segundos. El hilo recibe solo el prefijo y el plazo, nunca la contraseña,
el sufijo, correo ni usuario. No hay pool, cola, tareas persistentes o reintentos. Si DNS
retorna después del plazo, se cierra la conexión antes de enviar la petición. Una operación
de sistema bloqueada puede terminar después de la respuesta 503; no puede crear datos ni
habilitar el registro. Cada etapa de red también comprueba el plazo restante.

## Validación y errores

Se calcula el hash de la contraseña completa sin recortar espacios ni normalizar Unicode.
La respuesta debe ser HTTP 200, texto sin compresión, con framing verificable
(Content-Length exacto o chunked completo), como máximo 1 MiB y al menos 800 entradas
por el padding solicitado. Se aceptan más de 1.000 entradas y un último registro sin salto
final, observados en la consulta real. Cada línea CRLF exige sufijo hexadecimal de 35
caracteres y frecuencia decimal no negativa; duplicados y registros inválidos fallan.
Se analiza toda la respuesta incluso si ya apareció una coincidencia positiva. Se compara
el sufijo completo en el backend; los registros con frecuencia cero se ignoran.

- Coincidencia positiva: 400 con error de campo `password`. El usuario debe elegir otra.
- Ausente o coincidencia con cero: continúa la validación y creación normal.
- Timeout, conexión/TLS, redirección, otro HTTP o respuesta inválida/truncada: 503
  `password_check_unavailable`, `details: {}`, mensaje «No se pudo comprobar la contraseña.
  Intenta de nuevo más tarde.». Frontend conserva el formulario y permite reintento manual.
- Falta política aprobada/configuración: 503 `registration_unavailable`, un bloqueo distinto.

La comprobación ocurre antes de cualquier persistencia de cuenta, billetera, consentimiento,
imagen o notificación. Las cuotas compartidas de intentos sí se conservan, incluso ante 503.
No se registran contraseñas, hashes, prefijos, respuestas ni excepciones del proveedor.
El almacenamiento de la contraseña de cuenta sigue siendo Argon2id.

## Retirada de la estrategia anterior

Se retiran el módulo lector/importador, `prepare_password_corpus`, `PASSWORD_CORPUS_DIR`,
el directorio del Dockerfile, el montaje/declaración `password_corpus` de Compose y
`compose.corpus-readonly.yaml`. No ejecutar `docker volume rm`, `down -v`, limpiezas de datos
ni el comando retirado. No hay instrucciones vigentes para descarga masiva o importación.

Los archivos y volúmenes que existieran antes se conservan y quedan inertes; las exclusiones
Git/Docker de `private-passwords/` se mantienen para no incorporar accidentalmente esos datos.
Recrear el servicio aplica la configuración nueva sin eliminar los volúmenes existentes:

```bash
docker compose up --build -d --wait
```

Las migraciones `users.0003/0004` y el volumen PostgreSQL permanecen intactos. El volumen
`private_media` sigue siendo necesario para las imágenes opcionales de registro.

## Verificación

La suite no depende de Internet: simula únicamente `HTTPSConnection` y sus respuestas.
Cubre presencia, ausencia, padding cero, envío de prefijo/cabeceras/TLS, presupuesto total,
estados HTTP y redirecciones, errores TLS/conexión/timeout y respuesta corrupta/truncada.
Comprueba además 503 sin filas de negocio ni imagen huérfana y sin información sensible.

La [guía HU-007](HU-007.md) contiene comandos, evidencia atribuida y comprobación HTTP real
con PostgreSQL 17.11 y contraseñas exclusivamente sintéticas. Esa comprobación puntual no
certifica disponibilidad futura del proveedor. Siguen pendientes documento de política real,
SMTP, frontend, operación periódica del correo y despliegue.
