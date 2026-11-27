# Consolidación acumulada del backend — Iteraciones 01, 02 y 03

Fecha: 2026-11-27. Rama autorizada: `iteracion-03`. Base revisada: `319dac4`.

Este informe es la referencia actual de la entrega acumulada. Amplía el alcance de
[iteracion-03](iteracion-03.md), conservando sus reglas aprobadas de promociones,
reprogramación, reubicación, check-in y acceso mediante magic link. El alcance comprende
15 historias; no declara terminada la integración frontend ni el despliegue operativo.

## Fuentes y plan de trabajo

La instrucción actual del usuario autoriza diagnóstico, correcciones locales, migraciones,
documentación y pruebas aisladas de las tres primeras iteraciones. No autoriza commits,
push, merges, PR, despliegues, correo real ni modificaciones de bases compartidas.

Se priorizaron el repositorio actual, sus instrucciones, documentación reciente, contratos,
servicios y pruebas. La especificación
[Historias actualizadas](../Historias_Usuario_Sistema_Tiquetes_Aereos_Actualizadas.pdf)
se usa para la distribución en cuatro iteraciones. La ERS y otros artefactos históricos
no se utilizan para restaurar requisitos retirados. La instrucción expresa del usuario
retira la consulta de contraseñas comprometidas; se registra como DEC-27, sin atribuir
aprobación del profesor o del equipo. El PDF actualizado estaba sin seguimiento al iniciar
el trabajo y se conserva sin modificaciones.

Orden de ejecución y dependencia:

1. Revisar rama, contribuciones integradas, árbol de trabajo, instrucciones, especificación,
   servicios, migraciones, pruebas y consumidores frontend.
2. Revisar HU-007/008/009 y retirar exclusivamente el proveedor externo obsoleto; mantener
   validación local, sesiones, CSRF, verificación, límites y revocación.
3. Completar HU-010 sobre billetera y movimientos existentes: medios simulados, propiedad,
   presentación privada, gestión, depósitos transaccionales e idempotencia.
4. Revisar HU-001/005/006 y corregir la coherencia entre precios, clases, disponibilidad
   y catálogo; preservar los contratos existentes cuando funcionan.
5. Verificar HU-012/013 y las seis historias de iteración 03 sobre los mismos servicios,
   con fondos aportados por HU-010 y conservación del historial financiero.
6. Ejecutar recorridos completos y escenarios de permisos, vencimientos, límites,
   rollback, concurrencia, reintentos y fallos de notificación. Revisar también la suite
   acumulada existente, migraciones, Django, OpenAPI, Ruff y dependencias.
7. Consolidar contratos, resultados reales, configuración reproducible y pendientes
   separados para frontend e integración/despliegue.

No se pretende probar literalmente todos los estados posibles del programa. Se verifican
reglas observables y riesgos relevantes, sin presentar cobertura como prueba de corrección total.

## Diagnóstico inicial y decisiones de intervención

El trabajo anterior ya estaba incorporado en `319dac4`; el árbol inicial solo mostraba el
PDF actualizado sin seguimiento. No había un merge pendiente. Se conservaron las
contribuciones de usuarios, vuelos y ventas y sus migraciones compartidas.

| Hallazgo inicial | Clasificación e intervención |
|---|---|
| HU-007/008/009 funcionales con una dependencia HTTP de contraseñas ya retirada por el usuario | Dependencia obsoleta, no defecto de la implementación histórica. Se retira de todos los flujos afectados y de la configuración/contrato. |
| Existían billetera, movimientos, depósitos manuales y débito/reembolso de ventas | HU-010 parcial: faltaban medios registrados, relación depósito/medio, gestión, propiedad del medio y protección contra depósitos repetidos. Se completan reutilizando modelos y bloqueo de billetera. |
| Depósito HTTP aceptaba monto y referencia libre como única fuente de fondos | Se exige medio registrado propio y clave de idempotencia; no se mantiene un atajo HTTP para crear saldo sin medio. |
| El filtro de precio sin clase podía tomar precio de económica llena y capacidad de primera más cara | Defecto confirmado: se exige que una misma clase satisfaga precio y capacidad. |
| Catálogo posible mediante listado filtrado por nombre de origen, sin una API explícita de ciudades con oferta | Se conserva el listado y se añaden endpoints por ID de ciudad, sin fechas obligatorias. |
| Búsqueda existente acepta criterios parciales, aunque una especificación anterior exige todos | Diferencia deliberadamente conservada: sirve al consumidor actual y no vulnera ventas ni permisos. No se introduce una ruptura para imponer el formulario antiguo. |
| HU-002/003/004/014/016/017 ya incorporaban servicios, outbox, PDF, permisos e inventario | Se revisan y se verifican junto al flujo financiero nuevo; no se reescriben. |
| README e informes antiguos exigían Pwned Passwords y excluían HU-010 | Se actualizan puntos de entrada y se marcan explícitamente las secciones históricas sustituidas. |
| Docker no disponible desde esta distribución WSL | Verificación aislada con PostgreSQL real; no se presenta como prueba del entorno Compose objetivo. |

## Estado de las 15 historias

Los estados siguientes corresponden al **backend local**. Las pruebas específicas de vuelos,
usuarios, ventas y configuración se ejecutan junto a las nuevas de financiamiento y recorrido
acumulado. Frontend y operación se detallan aparte.

| Iteración | HU | Estado y funcionalidad esencial |
|---|---|---|
| 01 | HU-007 | Implementada y verificada localmente: registro con consentimiento, usuario/billetera atómicos, correo pendiente persistido, verificación de un uso, restricciones hasta verificar. Proveedor externo retirado. Política real de datos pendiente para habilitar registro productivo. |
| 01 | HU-008 | Implementada y verificada localmente: login/logout, sesión PostgreSQL, inactividad explícita, controles por cuenta/origen, recuperación de un uso y revocación. Validación de contraseña local. |
| 01 | HU-009 | Implementada y verificada localmente: altas exclusivas de ROOT, rol separado de privilegios técnicos, billetera/aviso/auditoría atómicos, cambio de clave y revocación. |
| 02 | HU-001 | Implementada y verificada localmente: rutas autorizadas, códigos únicos, fares por clase, zonas horarias, llegada, sillas, inventario y noticia. |
| 02 | HU-005 | Implementada y verificada localmente: búsqueda pública combinable, ida/regreso, fechas, capacidad y precio vigente; corregida selección de clase para precio/capacidad. |
| 02 | HU-006 | Implementada y verificada localmente: catálogo por origen, ciudades con oferta futura y detalles; vuelos cancelados/realizados/pasados excluidos. |
| 02 | HU-010 | Completada y verificada localmente: tarjetas/cuentas simuladas, enmascaramiento, propiedad, listado, alias/baja, depósitos repetibles seguros, saldo y movimientos; integrada con compras y reembolsos. |
| 02 | HU-012 | Implementada y verificada localmente: viajeros, adulto por vuelo, duplicados/límite cinco, retención, vencimiento y conversión sin doble consumo. |
| 02 | HU-013 | Implementada y verificada localmente: cotización/aceptación del precio, reserva o compra directa, débito atómico, sillas, localizador, correo persistido e idempotencia. |
| 03 | HU-002 | Implementada y verificada localmente: edición con motivo, campos inmutables, recálculo, reservas, notificaciones e invalidación de check-in al reprogramar. |
| 03 | HU-003 | Implementada y verificada localmente: cancelación transaccional, liberación, reembolsos por tiquete, ofertas de reubicación con aceptación y conservación histórica. |
| 03 | HU-004 | Implementada y verificada localmente: promociones por vuelo/clase/intervalo, sin cuota consumible, elegibilidad de nuevas operaciones, noticia y precio vigente. |
| 03 | HU-014 | Implementada y verificada localmente: cancelación propia, límites nacionales/internacionales, reembolso del valor pagado y reintentos sin doble liberación/abono. |
| 03 | HU-016 | Implementada y verificada localmente: acceso comprador o magic link limitado al viajero/compra, ventana de 24 h hasta salida, grupo atómico, PDF privado y correo reintentable. |
| 03 | HU-017 | Implementada y verificada localmente: cambio dentro de clase y ventana, propiedad, disponibilidad, una modificación voluntaria y bloqueo tras check-in. |

Los detalles de DEC-23–26 y las migraciones de la entrega anterior siguen en
[iteracion-03](iteracion-03.md). HU-011, HU-015 y HU-018–021 quedan fuera de esta
consolidación; no se eliminó su infraestructura de apoyo ya existente ni se implementaron
retiros, segundo factor de retiros, suscripciones, recomendaciones, mensajería o chatbot.

## Implementación de HU-010

`apps/wallets/payment_services.py` contiene registro, administración y depósito mediante
medio registrado. Reutiliza `Wallet`, `MovimientoBilletera` y las primitivas de débito,
abono y reembolso existentes. No hay pasarela ni consulta de fondos bancarios reales.

- Se admiten tarjetas simuladas y cuentas bancarias numéricas simuladas. Para tarjetas,
  se exige mes/año no vencidos; el mes actual sigue válido hasta finalizar ese mes.
- El número se normaliza quitando espacios/guiones y se descarta después de obtener los
  últimos cuatro dígitos y una huella HMAC SHA-256 asociada al titular/tipo. No se persiste
  el número íntegro ni se admite CVV. No se inventa una validación bancaria real o Luhn
  como requisito de esta simulación. Las cuentas de este contrato son numéricas, no IBAN.
- La presentación devuelve `**** 1234`; la huella y el número de entrada no se exponen.
  Esta minimización sustituye el almacenamiento reversible cifrado sugerido en el PDF:
  no se necesita recuperar el número para simular operaciones. No representa tokenización
  certificada ni demuestra cifrado de metadatos, discos o respaldos.
- La unicidad por propietario/tipo/huella evita registrar otra vez el mismo medio, incluso
  después de desactivarlo. Las altas concurrentes se serializan mediante la billetera.
- Puede cambiarse el alias y darse de baja mediante desactivación; no se borran medios ni
  movimientos usados. No existe reactivación ni sustitución silenciosa del número.
- La huella depende de `SECRET_KEY`; no rotar esa clave sin planificar la deduplicación
  de medios existentes. Una futura rotación debe considerar que el número íntegro ya no
  está disponible; las nuevas altas tras una rotación podrían no coincidir con huellas antiguas.
- Se conserva el mínimo público existente de **1000.00 COP**. Se rechazan valores no finitos,
  negativos, cero, con más de dos decimales y fuera de la capacidad decimal. El saldo total
  no puede superar **999999999999.99**, capacidad del modelo existente; no es un límite
  bancario aprobado ni un límite diario nuevo. Cualquier techo de negocio distinto requiere
  acuerdo; el pendiente histórico no bloquea esta simulación con sus límites explícitos.
- Depósitos, bajas y cambios de alias bloquean primero la billetera y luego el medio.
  Compra/reembolso reutilizan el mismo bloqueo de billetera, sin imponer el bloqueo global
  de inventario a operaciones financieras independientes.
- El depósito comprueba propietario, estado activo y vencimiento del medio, crea el
  movimiento y actualiza el saldo en una transacción. Un fallo revierte todo.
- La clave de idempotencia es única por billetera; el contenido normalizado incluye medio,
  monto y referencia. La misma clave/contenido recupera el mismo movimiento, incluso si el
  medio fue desactivado después. Una clave con otro contenido falla sin crear saldo.
- Un reintento devuelve el movimiento original en `deposit`; `balance` representa el saldo
  **actual**, que puede haber cambiado por compras u otras operaciones. No interpretar
  `saldo_resultante` de un movimiento como saldo actual.
- Los movimientos antiguos conservan `medio_pago: null`. No se inventan medios de pago
  para saldos históricos ni se reconstruye información que nunca fue guardada.

La API sigue permitida a cuentas activas verificadas de los roles registrados, conforme al
alcance financiero existente. Esto no habilita a ROOT/administradores a comprar o reservar.
Las primitivas internas de saldo no son endpoints de acceso libre; la API de depósitos
siempre exige un medio. Los datos semilla/pruebas pueden seguir aprovisionando fondos
sintéticos mediante servicios internos.

## Contratos e integración

Prefijo: `/api/v1/`. Autenticación mediante sesión Django; mutaciones con CSRF. Los
endpoints financieros requieren correo verificado. Dinero como cadena decimal; COP.

| Método/ruta | Entrada y respuesta |
|---|---|
| `GET sales/wallet/` | Saldo actual, moneda y movimientos del titular; se conserva la forma previa con campos aditivos. |
| `GET sales/wallet/movements/` | Movimientos propios paginados, orden reciente; medio enmascarado o null para históricos. |
| `GET sales/wallet/payment-methods/` | Medios propios paginados, incluidos desactivados. |
| `POST sales/wallet/payment-methods/` | `tipo`, `alias`, `titular`, `entidad`, `numero`; tarjeta exige `mes_vencimiento`/`anio_vencimiento`. Respuesta 201 enmascarada. |
| `PATCH sales/wallet/payment-methods/{id}/` | Solo `alias`; 200. |
| `DELETE sales/wallet/payment-methods/{id}/` | Desactivación propia idempotente; 204, sin borrar historia. |
| `POST sales/wallet/deposit/` | `medio_pago_id`, `monto`, `referencia` opcional; cabecera obligatoria `Idempotency-Key`. 200 con billetera y `deposit`. |
| `GET flights/catalogue/cities/` | Lista de ciudades activas con vuelos programados futuros. |
| `GET flights/catalogue/?origen_id=...` | Vuelos programados futuros del origen, sin exigir fecha; lista vacía cuando no hay oferta. |

Para todas las operaciones existentes de vuelos/ventas/check-in, usar los contratos de
[iteracion-03](iteracion-03.md#api-handoff). Las rutas previas de ciudades, listado y búsqueda
siguen disponibles. Se mantiene la búsqueda flexible con campos opcionales; una lista vacía
representa ausencia de resultados y frontend debe mostrarla explícitamente.

Ejemplo de registro de **cuenta ficticia**:

```http
POST /api/v1/sales/wallet/payment-methods/
X-CSRFToken: <csrf-token>
Content-Type: application/json

{"tipo":"CUENTA_BANCARIA","alias":"Cuenta de prueba","titular":"Persona Ficticia","entidad":"Banco Simulado","numero":"000123456789"}
```

Usar el `id` devuelto; el número no se devuelve. Depósito:

```http
POST /api/v1/sales/wallet/deposit/
X-CSRFToken: <csrf-token>
Idempotency-Key: <unique-client-operation-key>
Content-Type: application/json

{"medio_pago_id":12,"monto":"500000.00","referencia":"Recarga simulada"}
```

Conservar clave y contenido tras un error de red. Nueva recarga requiere nueva clave.
El saldo no se modifica a través de PATCH ni mediante campos de la cuenta. Medio ajeno o
inexistente devuelve 404; medio desactivado/vencido, datos inválidos, clave ausente o reutilizada
con otro contenido devuelven 400. Sin sesión o verificación, 403 según sesión DRF. No distinguir
un 403 de permisos de uno de CSRF únicamente por el estado; consultar `code`.

No se almacena CVV: enviar ese campo produce 400. No usar tarjetas o cuentas reales en la
simulación. No registrar los cuerpos de alta de medios en analytics, logs o herramientas
externas. El transporte HTTPS y la privacidad de base/respaldos siguen siendo operativos.

## Migraciones y dependencias

Nueva migración aditiva:
`wallets/0005_movimientobilletera_idempotency_key_and_more.py`.
Crea `PaymentMethod`, referencia nullable desde movimientos, clave/huella de petición y
restricciones de unicidad y vencimiento estructural. Las migraciones históricas compartidas
no se reescriben. Los vínculos previos de débito/compra y tiquete/reembolso se conservan.

No se añadió ni actualizó ninguna dependencia de ejecución o lock en esta consolidación.
La retirada del proveedor elimina código HTTP y configuración propia, no una librería pip:
el cliente anterior usaba biblioteca estándar. ReportLab sigue siendo dependencia de la
entrega anterior. La herramienta PDF usada para leer el adjunto se instaló exclusivamente
en `/tmp`, sin incorporarla a los requisitos de la aplicación.

## Verificación real

La ejecución final acumulada pasó. El resultado histórico de 455 pruebas pertenece a la
entrega anterior y no se reutiliza como evidencia actual.

Entorno: Python 3.13.16, dependencias con hashes existentes, PostgreSQL 16.15 temporal y
exclusivo en loopback 55439. Pruebas con `config.settings.test`, correo en memoria, sin
`.env`, SMTP real ni bases del proyecto. Docker/Compose no están disponibles en WSL;
PostgreSQL 17.11 de Compose requiere verificación por integración.

La nueva prueba `sales/tests/test_cumulative_delivery.py` recorre por HTTP registro,
verificación y correo pendiente, login/rotación CSRF, cuenta bancaria, depósito, alta de
vuelo administrativa, búsqueda/catálogo, reserva/cotización/conversión, repetición de compra,
correo, cancelación/reembolso, compra directa, reprogramación, check-in autenticado,
magic link, PDF privado, procesador de notificaciones y logout.

`wallets/tests/test_funding.py` cubre tarjetas/cuentas, datos privados, duplicados, CVV,
propiedad, entradas monetarias, medio/clave obligatorios, reutilización de claves, baja,
expiración, desbordamiento de saldo, rollback, CSRF, concurrencia real entre depósitos con
igual/distinta clave y depósito frente a débito concurrente. Se mantienen los escenarios
previos de promociones, cancelación administrativa/reubicación, fronteras temporales,
check-in grupal, reprogramación, inventario, fallos/reintentos y concurrencia de ventas.

Los tests exclusivos del proveedor retirado se sustituyen por validación local y registro
sin dependencia HTTP; se conservan las pruebas de rollback y carreras de cambio/recuperación
con revalidación. Su eliminación reduce el número de casos respecto a la suite antigua y no
representa la supresión de controles vigentes. Los fallos iniciales de fixtures y supuestos
de pruebas se corrigieron; no se relajan validaciones de producción para acomodarlos.

### Resultados finales

| Control | Resultado ejecutado |
|---|---|
| Suite completa de backend, incluidos config y aplicaciones | **445 passed**, 216.69 s |
| Cobertura de sentencias de aplicaciones | **89.98 %**, 3674/4083 |
| Subconjunto de servicios de negocio, incluido HU-010 | **91.89 %**, 1224/1332 |
| Suite dedicada de financiamiento | **27 passed**, 7.63 s; incluida también en la suite completa |
| Concurrencia PostgreSQL real | Aprobada: inventario/códigos/compras/cancelaciones y nuevos depósitos/débitos |
| Migración de actualización `wallets.0005` en base aislada | Aplicada correctamente; la suite también crea el esquema desde migraciones |
| Django `check` | Sin incidencias |
| `migrate --check` | Sin migraciones pendientes |
| `makemigrations --check --dry-run` | Sin cambios detectados |
| OpenAPI `spectacular --validate --fail-on-warn` | Aprobado sin advertencias |
| Ruff lint y formato de todo el backend | Aprobados; 151 archivos Python |
| `pip check` | Sin requisitos incompatibles |
| `git diff --check` | Aprobado |

Artefactos locales temporales: `/tmp/aerolinea-cumulative-full.log`,
`/tmp/aerolinea-cumulative-coverage.json`, `/tmp/aerolinea-cumulative-schema.yaml` y
`/tmp/aerolinea-cumulative-migrations.log`. No son artefactos de CI remoto ni se añaden
al repositorio. La suite usa los archivos de pruebas versionables; no se ejecutó el script
HTTP manual contra el servidor del proyecto. Los últimos ajustes del contrato OpenAPI y
comentarios se validaron de nuevo con su comprobación específica, sin cambios de negocio
posteriores a la suite completa.

## Operación reproducible y responsabilidades

Desde la raíz en WSL, con Docker disponible y configuración local existente válida:

```bash
docker compose exec backend python -m pip check
docker compose exec backend python manage.py migrate --noinput
docker compose exec backend python manage.py check
docker compose exec backend python manage.py migrate --check
docker compose exec backend python manage.py makemigrations --check --dry-run
docker compose exec backend ruff check .
docker compose exec backend ruff format --check .
docker compose exec -e DJANGO_SETTINGS_MODULE=config.settings.test backend pytest --cov=apps --cov-report=term-missing --cov-fail-under=70
docker compose exec -e DJANGO_SETTINGS_MODULE=config.settings.test backend python manage.py spectacular --validate --fail-on-warn --file /tmp/schema.yaml
```

Estos comandos para el entorno objetivo no se presentan como ejecutados con Docker en esta
sesión. Para ejecución local usar Python compatible y `TEST_DATABASE_URL` dedicado `test_*`,
como explica [backend README](../../backend/README.md); nunca credenciales de producción.

Integración debe programar los siguientes comandos; existen, pero su existencia no acredita
que haya un scheduler desplegado:

```bash
python manage.py liberar_reservas_vencidas --batch-size 100
python manage.py process_verification_emails --batch-size 100
python manage.py process_recovery_emails --batch-size 100
python manage.py process_administrator_notifications --batch-size 100
python manage.py process_purchase_emails --batch-size 100
python manage.py process_journey_emails --batch-size 100
```

Vencimientos al menos cada minuto; procesadores de correo con frecuencia suficiente para
el objetivo de entrega y capacidad de lotes según carga. Configurar URLs de frontend de
verificación, recuperación y `GUEST_CHECKIN_FRONTEND_URL`, SMTP real, origen/CSRF/cookies
seguros, política de datos aprobada para registro productivo, media privada y persistencia.
No configurar Pwned Passwords ni un corpus. El PDF se genera con ReportLab fuera de los
bloqueos del negocio y el correo queda pendiente si falla. La entrega de correo es al menos
una vez: una caída después de SMTP pero antes de confirmar puede repetir un correo, no una
compra, depósito o reembolso.

## Instrucciones para frontend y las IAs del equipo

- Leer este informe, DEC-23–27 y el contrato OpenAPI generado; no reintroducir consultas
  de contraseñas ni exigir un dígito o mínimo ocho. El mínimo vigente es doce.
- Adaptar `frontend/src/pages/ProfilePage.tsx`: su recarga actual solo envía monto/referencia;
  ahora debe registrar/seleccionar un medio, enviar `medio_pago_id` y mantener la misma
  `Idempotency-Key` en reintentos. Añadir listado, enmascaramiento, alias y desactivación.
- Nunca persistir números completos/CVV en frontend o analytics. Usar únicamente datos
  ficticios y borrar el número del estado del formulario tras el alta.
- Mostrar el saldo actual devuelto y el movimiento original por separado; no sumar otra
  vez el abono al recibir la misma respuesta. El servidor es la autoridad del saldo.
- Mantener sesión/CSRF y renovación de actividad solo por interacción real. No tratar todos
  los 403 como logout; usar el código de error.
- Reutilizar catálogo/listado y mostrar ausencia de oferta. Presentar precios vigentes,
  clase/capacidad, hora local y moneda; los filtros de búsqueda no fijan la compra.
- Mantener `accepted_total` y claves de reserva/compra, campos de contacto del viajero,
  motivo de edición y tarifas independientes documentados en iteración 03.
- Implementar pantallas de promociones, reubicación/aceptación/reembolso, check-in grupal,
  enlaces mágicos y descargas privadas según el contrato existente. El token del fragmento
  no concede una sesión de usuario y no debe llegar a logs ni a la URL de consulta.
- No alterar migraciones compartidas ni modificar saldos desde vistas/fixtures de producción.
  Coordinar nuevos cambios de esquema por aplicación y probar propiedad/rollback.
- No construir ahora HU-011/015/018–021 para completar pantallas de esta entrega.

## Limitaciones y pendientes materiales

No se verificaron frontend integrado, PostgreSQL 17.11/Compose, CI remoto, SMTP real,
scheduler desplegado, infraestructura, backups/restauración ni objetivos de rendimiento.
La serialización global de inventario documentada en iteración 03 es una decisión de
corrección para carga académica, no una prueba de escalabilidad.

La política real de datos sigue pendiente y bloquea deliberadamente el registro productivo,
no el flujo aislado con política de prueba. P-06 de rutas internacionales inversas sigue
abierto: no se amplió el catálogo por inferencia. Límites bancarios adicionales y segundo
factor de retiros no se inventaron; retiros corresponden a iteración 04.

Los débitos históricos ambiguos no se vinculan automáticamente a compras: la migración
previa solo enlaza coincidencias inequívocas. Una compra legada sin débito enlazado requiere
reconciliación humana antes de reembolsar; se conserva el fallo seguro y no se crea dinero.
No se accedió a bases compartidas para determinar si existen esos registros reales.

No se detectaron defectos críticos sin resolver en los recorridos esenciales verificados
en este entorno aislado; esto no certifica bases legadas, infraestructura ni todos los estados
posibles de ejecución.

El backend se entrega para integración con estas dependencias explícitas. No se declara
completa la entrega de producto ni la operación real de las tres iteraciones.

## Follow-up: controlled options and ROOT

The [catalogue/ROOT addendum](catalogues-and-root.md) records subsequent contract changes,
worldwide geography setup, dependent commercial selectors and required frontend adaptations.
Earlier verification counts in this report predate that follow-up.
