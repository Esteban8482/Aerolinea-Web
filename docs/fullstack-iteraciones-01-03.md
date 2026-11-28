# Consolidación funcional — iteraciones 01, 02 y 03

Fecha de inicio: 2026-11-27. Rama: `iteracion-03`. Base: `e24ced1`; árbol limpio al
iniciar esta ampliación. Este informe sustituye el alcance solo backend de entregas anteriores;
no atribuye verificación integrada a las pruebas históricas.

## Plan y dependencias

1. Diagnóstico de contratos, entorno y CI: reproducir build y comprobaciones, identificar fallos
   reales, preservar migraciones y datos; preparar PostgreSQL aislado y correo local.
2. Infraestructura compartida de interfaz: solicitudes, errores, sesión/actividad, permisos,
   catálogos buscables con paginación y protección frente a respuestas obsoletas.
3. HU-007/008/009: registro geográfico, validación local de contraseñas, verificación, recuperación,
   navegación por rol y funciones ROOT conservadas salvo billetera.
4. HU-010: medios simulados, gestión, movimientos, depósitos confirmados e idempotentes.
5. HU-001/005/006: rutas administrativas separadas de cobertura comercial, precios vigentes,
   búsqueda dependiente, catálogo y detalle.
6. HU-012/013: viajeros, reservas sin débito, cotización, aceptación expresa, compras y conversión;
   conservar claves ante reintentos y renovar ante cambios materiales.
7. HU-002/003/004/014: gestión administrativa, promociones, cancelación con resolución posterior
   del comprador, grupo atómico, reembolsos históricos y panel administrativo. Implementar las
   reglas pendientes solo después de decisión expresa.
8. HU-016/017: agrupación por compra y vuelo, check-in individual/grupal, invitados, sillas y PDF.
9. Operación: inicialización explícita de referencias, expiraciones y outbox periódicos con
   reintentos, sin nueva infraestructura distribuida.
10. Verificación: suite PostgreSQL y concurrencia, migraciones fresh/upgrade, OpenAPI, Ruff,
    dependencias, build y recorridos reales de navegador; registrar cada resultado y limitación.
11. Consolidar documentación vigente y matriz de entrega de las 15 HU. No adelantar HU-011,
    HU-015 avanzada ni HU-018–021.

## Diagnóstico inicial de la consolidación (estado histórico)

Los puntos siguientes describen el estado encontrado al comenzar la consolidación, no
constituyen una lista de defectos actuales. Consultar el progreso de recuperación y volver a
abrirlos solo si una reproducción vigente confirma que persisten.

- Registro envía `birth_place` y códigos de género incompatibles, sin IDs geográficos.
- Perfil hace `Promise.all` de perfil y ventas incluso para roles sin permiso comercial.
- Depósitos omiten medio de pago e idempotencia; falta interfaz de medios registrados.
- Reservas/compras omiten idempotencia; compras/conversión omiten cotización y total aceptado.
- Navegación y gestión de sesión no distinguen carga inicial; logout oculta fallos de revocación.
- Validación frontend exige ocho caracteres y número; backend exige política local Django
  (mínimo doce, no exclusivamente numérica, no común ni similar a datos personales).
- No hay framework de pruebas frontend. Se usó el navegador integrado para recorridos no
  destructivos y no se añadió dependencia de automatización.
- `npm` no está en PATH; el build se ejecutó con el runtime Node local de VS Code Server, sin
  instalar herramientas globales.
- CI remoto del commit e24ced1 terminó en fallo; diagnóstico de anotaciones en curso.

## Progreso de recuperación frontend — etapa 1: autenticación y CSRF

Verificación en navegador integrado contra `http://localhost:5173/login` y backend local:

- `GET /api/v1/auth/csrf/` a través del proxy Vite: **200**, JSON con `csrf_token` y
  respuesta con cookie `csrftoken`; el navegador confirmó esa cookie en el origen frontend.
- `POST /api/v1/auth/login/` de diagnóstico con credenciales sintéticas: se envió
  `X-CSRFToken` y Django respondió **401 `invalid_credentials`**, no un rechazo CSRF (403).
  No se intentó autenticar ninguna cuenta real.
- Settings activos del backend: orígenes CSRF confiables explícitos
  `http://localhost:5173` y `http://127.0.0.1:5173`; `CSRF_COOKIE_SECURE=false` solo en
  desarrollo local. La configuración Vite actual usa proxy `/api` a
  `http://127.0.0.1:8000` con `changeOrigin: true`.
- El texto reportado «No se pudo verificar la protección CSRF.» no aparece en el código
  fuente frontend. En el entorno local disponible no se reprodujo el error; por eso no se
  debilitó CSRF ni se cambió la lista de orígenes/proxy sin evidencia causal.
- Corregido en `frontend/src/App.tsx` el prefijo repetido de actividad: el cliente común ya
  antepone `/api/v1`, por lo que la ruta ahora es `/auth/session/activity/`.

**Confirmación manual posterior:** ROOT y CLIENTE accedieron correctamente. ADMINISTRADOR
también inició sesión; el perfil muestra `ADMINISTRADOR` y la pestaña «Gestión» aparece en
`/vuelos`. No se encontró un defecto de visibilidad y no se cambió la autorización. Aún falta
verificar llamadas protegidas y logout. El intento sintético confirma la ruta CSRF hasta
autenticación; no sustituye la reproducción del mensaje reportado. Si persiste en el navegador,
se requiere registrar método, URL, status y encabezados desde ese mismo origen (sin compartir
cookies, token CSRF o contraseñas).

## Decisiones aprobadas conservadas

Las aprobaciones de HU-014 y HU-009 están registradas en
[ACLARACIONES_Y_LINEAMIENTOS_DEL_PROYECTO.md](ACLARACIONES_Y_LINEAMIENTOS_DEL_PROYECTO.md),
versión 1.0.8:

- La cancelación voluntaria respeta los plazos nacional/internacional aunque `disrupted` esté
  activo. Una compra con tiquetes `PENDIENTE_RESOLUCION` no puede producir un reembolso
  voluntario parcial; el comprador debe completar primero la resolución de aerolínea.
- En ida/regreso, el reembolso de la ida comprende el regreso relacionado. Las reubicaciones
  deben conservar la secuencia temporal de ida y vuelta; sin alternativa compatible se ofrece
  el reembolso del itinerario.
- Solo `CLIENTE` tiene billetera personal. `ADMINISTRADOR` y `ROOT` permanecen excluidos.
- ROOT puede cambiar su propia contraseña con el endpoint existente, se invalidan sus sesiones
  y debe autenticarse manualmente después. La interfaz no inicia sesión automáticamente.

## Recuperación frontend incremental

### Etapa 1 — sistema compartido y autenticación

**Aprobación visual:** se conserva la identidad Alas y se adoptó el criterio `contextual`:
controles y formularios operativos con esquinas rectas; las tarjetas promocionales del Home
conservan esquinas redondeadas y sombras propias de la marca.

**Corregido:** encabezado, Home y controles compartidos utilizan `lucide-react`; se retiraron
los emojis de interfaz de los componentes tocados, se normalizaron acciones, estados y accesos
con nombres completos y se añadió un estado de carga/bloqueo al cierre de sesión.

**Verificado en navegador:** Home y login sin desbordamiento horizontal en escritorios,
tabletas y móvil; `/vuelos` cargó itinerarios reales usando `127.0.0.1:5173`; el error
transitorio observado desde `localhost` no se reproduce desde el origen alternativo permitido.
La comprobación de `/registro` mostró seis comboboxes geográficos/catálogo sin desbordamiento
móvil y la selección `Colombia → Cundinamarca → Chía` quedó operativa.

**Build:** TypeScript/Vite pasó después de la integración de iconos y normalización del diseño.

### Etapa 2 — contrato de registro personal

**Aplicado:** registro de clientes dejó de solicitar dirección y ubicación de facturación.
La jerarquía mundial sigue exclusiva del lugar de nacimiento. El backend conserva
`billing_city` y `billing_address` para datos históricos, pero ambos son opcionales en
`RegistrationSerializer`; omitirlos crea el perfil sin ubicación ni dirección de facturación.
El frontend eliminó esas validaciones, campos y claves del payload. No se hizo migración
destructiva.

**Pendiente:** ejecución de la prueba de registro dirigida y revisión visual final del formulario
de registro bajo 127.0.0.1. Esta sesión no pudo ejecutar pytest desde WSL porque `docker`
no está disponible y el Python local no tiene pytest instalado. El build frontend sí pasó.

### Etapa 1 — autenticación y CSRF

**Corregido/verificado:** el prefijo duplicado de actividad de sesión quedó eliminado; el
cliente HTTP agrega `/api/v1`. La solicitud CSRF observada en la etapa previa respondió 200,
estableció cookie/token y el POST sintético llegó a autenticación con 401 `invalid_credentials`,
no a rechazo CSRF 403. La visita actual a `/login` no presenta el mensaje de error CSRF. No se
debilitó CSRF ni se cambió el proxy.
El encabezado `Origin` no quedó expuesto en la captura del navegador; no se afirma haber medido
ese encabezado directamente. Los orígenes permitidos se verificaron en la configuración activa
de Django.

**Confirmado manualmente por el usuario:** acceso de los tres roles; para ADMINISTRADOR, el
perfil identifica el rol correctamente y la pestaña «Gestión» está visible en `/vuelos`.
No se verificaron llamadas protegidas ni logout. No se guardaron ni publicaron contraseñas.

### Etapa 2 — selectores compartidos

**Completada en navegador:**

- `RemoteSelect` ofrece un único campo combobox, búsqueda y paginación dentro del menú,
  navegación por teclado, estados de carga/vacío/error y anuncios accesibles. Los catálogos
  grandes se mantienen paginados; no se descarga el catálogo mundial entero.
- Registro: Colombia → Cundinamarca → Chía se seleccionó con búsqueda/teclado. La primera
  página entregó 20 ciudades; «Cargar más» añadió la página siguiente y filtrar `chia` devolvió
  Chía. Cambiar el país limpia las selecciones territoriales dependientes.
- Vuelos: seleccionar Bogotá → Pereira y buscar produjo una solicitud con ambos IDs y una
  fila correspondiente a XX0001. El selector del catálogo usa una etiqueta distinta para
  evitar confundirlo con el origen del formulario.

### Etapa 3 — estructura y consistencia visual

**Corregido:** estilos faltantes de `page-shell`/`page-card`, tabla de vuelos, etiquetas
duplicadas en `BookingModal` y `CheckInPage`, y presentación adaptable de la billetera. Se
conservó la paleta, tipografía y marca existentes; la gestión de medios y depósitos simulados
mantiene sus contratos.

**Evidencia en navegador:** Home se inspeccionó a 1440 px y 390 px; registro, login, vuelos,
check-in de invitado y el formulario de reserva/compra se recorrieron. El Home móvil mide
375 px de contenido en un viewport de 390 px, sin desbordamiento horizontal de página. Para la
tabla de vuelos, escritorio: tabla y contenedor 1033 px; tablet: tabla 900 px dentro de
contenedor 672 px; móvil: tabla 900 px dentro de contenedor 320 px. El desplazamiento interno
queda confinado a tablet/móvil; el body permanece dentro del viewport. El modal muestra una
etiqueta por campo de catálogo y no se envió ninguna reserva ni compra.

**Pendiente:** wallet, pantalla de cambio ROOT, operaciones de gestión administrativa y
cancelaciones no se inspeccionaron bajo sesiones reales. El usuario confirmó la visibilidad de
la pestaña «Gestión» con el rol ADMINISTRADOR, pero no se probaron sus operaciones. La
billetera se inspeccionó en código y compilación, pero no se probaron operaciones financieras
contra los datos persistentes.

### Etapa 4 — verificación funcional y regresiones

**Realizado:**

- Build de producción con TypeScript (`tsc -b`) y Vite: **pasó**. El shell no expone `npm`;
  se usó el runtime Node local del entorno y las dependencias ya presentes.
- Pruebas PostgreSQL aisladas dirigidas a cancelación, resolución, HU-009 y política de
  contraseñas:

  ```bash
  docker compose exec -T -e DJANGO_SETTINGS_MODULE=config.settings.test backend pytest \
    apps/sales/tests/test_cu14_cancelar_reserva_compra.py \
    apps/sales/tests/test_cancellation_resolution.py \
    apps/users/tests/test_administration.py \
    apps/users/tests/test_password_check.py
  ```

  **92 passed**. La primera ejecución descubrió una condición temporal incorrecta que rechazaba
  alternativas válidas antes del regreso; se corrigió comparando la etapa original y los
  horarios. También se ajustaron los datos de prueba (saldo inicial internacional y estado de
  modelos recargado). El entorno de Compose no tenía instalado `reportlab`, aunque la versión
  4.5.1 ya está fijada; se restauró esa dependencia en el contenedor para completar la suite,
  sin cambiar manifiestos ni datos de la aplicación.
- Ruff `check` y `format --check` sobre los archivos backend modificados: **pasaron**.
- `git diff --check`: **pasó**.

**Bloqueado/incompleto:** el usuario confirmó el acceso de ROOT, ADMINISTRADOR y CLIENTE, y
que ADMINISTRADOR ve la pestaña «Gestión» en `/vuelos`; no se verificaron llamadas protegidas,
logout, operaciones de billetera, escritura de reserva/compra, acciones de gestión
administrativa, resolución real de cancelaciones ni check-in/sillas con cuentas locales. No se
ejecutó una operación financiera ni se modificaron reservas, compras o vuelos de la base de
desarrollo. El build no se toma como prueba visual ni de flujos autenticados.

## Evidencia anterior, no equivalente a aceptación full-stack

447 pruebas backend de regresión y nueve pruebas adicionales de catálogos/selectores/ROOT
pasaron históricamente en PostgreSQL 16.15 aislado. El objetivo Compose es 17.11. Importación
geográfica repetida, migraciones y OpenAPI validados localmente. Esa evidencia histórica no
sustituye los flujos autenticados pendientes indicados arriba.
