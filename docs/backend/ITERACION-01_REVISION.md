# Iteración 1 — revisión conjunta del backend

Revisión iniciada el 2026-10-20 y completada el **2026-10-21**, America/Bogota.
[Guía de entrega](ITERACION-01.md). Trabajo sobre `iteracion/01-usuarios`, sin crear rama,
commits, push, PR, merge, despliegue ni correo real. Estado inicial limpio en `32ab93a`;
se conserva la corrección de `docs/AGENTS.md` de ese commit y se añaden referencias puntuales.

## Base y alcance comprobados

La rama contiene HU-007 (`ff8a193`/`5325578`), HU-008 (`82295d5`) y HU-009 (`a5a69bd`).
Entre HU-009 y el punto inicial solo cambia `docs/AGENTS.md`; no hay cambios backend que
invaliden por sí solos la evidencia de 319 pruebas/93,22 % del informe HU-009. Las nuevas
correcciones indicadas abajo sí motivan su comprobación adicional.

Fuentes: instrucciones raíz/docs, README, reglas Git, complemento 1.0.5, ERS (`ERS.pdf`,
RF-USU-01–19), historias HU-007/008/009, CU-07/08/09, modelos, migraciones, pruebas y guías.
Se revisó el texto extraído de `Diagramas de Clases.pdf`, páginas 1, 5 y 7; no se atribuye
una validación visual de flechas en el PDF ni de los mockups HTML. El enunciado original y
programa académico no están presentes. No se cambian decisiones resueltas ni reglas Git.

| Área | Evaluación conjunta |
|---|---|
| Cuenta/roles | Un User con correo normalizado, root_id separado y restricciones PostgreSQL. Roles de negocio independientes de staff/superuser; no hay elevación por campos HTTP |
| HU-007 / CU-07 | Registro, consentimiento versionado, billetera cero, imagen privada, verificación y reenvío persistentes. Política real pendiente; recuperación no verifica automáticamente |
| HU-008 / CU-08 | Login por identificador correcto, sesión compartida, CSRF, actividad explícita, bloqueo, recuperación y auditoría. Inactivos no acceden; sin verificar sí autentica |
| HU-009 / CU-09 | Alta/listado solo ROOT y cambio propio de contraseña, límites separados, transacciones y avisos. Se rechazan objetivos/campos ajenos |
| Contraseñas/enlaces | Cambio invalida sesiones y recuperaciones ligadas al hash anterior; propósito de verificación separado. Proveedor externo fuera de transacciones y fallo cerrado |
| Persistencia | Cuenta/billetera/intención/eventos atómicos; unicidad y bloqueos existentes; users.0006 y wallets.0002 son hojas actuales. Sin migración nueva |
| Correo | Tres procesadores específicos comparten patrón de leases/reintentos; efectos externos después del commit. No se introduce una cola genérica por refactorización |
| Contratos | Rutas actuales y OpenAPI validado; guías por HU conservadas y enlazadas. Proveedor real por rango, sin corpus operativo |

No se encontraron endpoints de otras historias añadidos sin respaldo. La lista mínima de
administradores figura también como `Root.listarAdministradores()` en el diseño. Los
permisos `IsAdministrator`, `IsClient` y `HasVerifiedEmail` no demuestran que vuelos,
reservas, compras o finanzas estén implementados: deben aplicarse en esas futuras HU.

## Hallazgos y correcciones

1. **Carrera en actualización de hashes heredados (corregida).** Un login leía una clave
   PBKDF2 y quedaba en curso; recuperación confirmaba una contraseña nueva; el setter
   automático de Django rehasheaba la clave antigua y la sobrescribía. Reproducido en
   conexiones PostgreSQL independientes para ROOT y ADMINISTRADOR. `User.check_password`
   conserva la verificación/hashing de Django y actualiza el hash solo si la base aún
   contiene el anterior. Si perdió la carrera, devuelve falso y login responde 401;
   prevalece la contraseña restablecida. La variante async usa la misma implementación.
   No cambia el contrato HTTP ni la política de contraseñas.
2. **Aviso a destinatario obsoleto (corregido).** El procesador de HU-007 no filtraba
   `recipient == user.email`, aunque la confirmación sí lo exigía y los otros procesadores
   ya lo comprobaban. Reproducido: enviaba un enlace que el sistema rechazaría. Ahora omite
   ese trabajo sin enviarlo ni incrementar intentos. No se añade edición pública de correo.
3. **Prueba sensible al reloj de pared (corregida).** La primera suite nueva tuvo 325 éxitos
   y un fallo: la hora posterior al registro fue menor que accepted_at. El test comprobaba
   un intervalo de reloj real. Ahora fija el reloj del servidor y exige la fecha exacta,
   manteniendo el requisito de consentimiento sin atribuir la causa del ajuste temporal.
4. **Entrega documental dispersa (corregida).** Guía única de entrada, configuración de
   pantallas y proxy/CSRF, tres procesadores y limpieza de sesiones; README con estado
   vigente, nombre real de ERS y fuentes ausentes. Guías HU distinguen evidencia histórica
   de esta revisión. AGENTS enlaza alcance, componentes reutilizables y verificación.

Archivos de ejecución: `backend/apps/users/models.py`, `mail.py`; regresiones nuevas en
`tests/test_iteration1.py`; ajuste determinista en `tests/test_registration_agreements.py`.
Sin cambios a contratos, dependencias, secretos, esquema ni infraestructura.

## Correspondencia con el diseño inicial

Esta tabla distingue reglas acordadas de decisiones de implementación. No sustituye la
revisión del diagrama por el equipo ni declara que todas las diferencias estén aprobadas.

| Diseño original | Implementación / responsabilidad | Clasificación y revisión necesaria |
|---|---|---|
| Usuario con id UUID, correo, hash, perfil, correoVerificado | User(AbstractUser), BigAutoField, email, password, campos de perfil, is_email_verified | DEC-04 autoriza PK entera; DEC-15 resuelve correo opcional e ID de ROOT. Nombres en inglés son adaptación técnica |
| Root, Administrador y Cliente como especializaciones | Un único User.role, sin tablas/subclases de esos roles; IsRoot/IsAdministrator/IsClient | DEC-10 fija usuario personalizado y roles explícitos. **No contiene una aprobación expresa de sustituir toda la herencia por esta estructura**; equipo debe ratificar la correspondencia y actualizar el diseño. No migrar a herencia automáticamente |
| Root.crearAdministrador / listarAdministradores | administration_services.create_administrator y AdministratorsView | Responsabilidades implementadas con autorización ROOT; asociación «crea» trazada por AdministrationEvent.actor/target, sin FK created_by permanente |
| Usuario.autenticar / cerrarSesion | AccountBackend, start_session/end_session; AccountSession y middleware | Servicios en vez de métodos del dominio: adaptación conforme a DEC-12. root_id frente a correo: DEC-15 |
| Usuario.solicitarRecuperacion / restablecerContrasena / verificarCorreo | request_recovery/reset_password/confirm_email, modelos de intención y consumo | HU-007/008, DEC-11/19; métodos trasladados a servicios; tokens y propósitos separados |
| intentosFallidos / bloqueadoHasta en Usuario | LoginGuard por identificador HMAC, incluso inexistente; ámbito propio HU-009 | Adaptación necesaria para DEC-18/22; no son campos de perfil ni se exponen. RegistrationRateBucket gestiona cuotas compartidas |
| Usuario.puedeOperar | IsAuthenticated, permisos por rol/verificación y futuras comprobaciones de propiedad | No hay booleano universal: cada operación exige su combinación. Revisión de permisos financieros pendiente en sus HU |
| Usuario.cargarImagen | sanitize_profile_image y almacenamiento privado durante registro | DEC-17 aprueba esta entrada. Actualización/descarga de perfil aún sin endpoint; no equivale a implementar RF-USU-10/11 completos |
| Usuario.consultarPerfil / actualizarPerfil | Campos persistidos; session_state solo ofrece rol/estado | **No implementados como operaciones de perfil.** RF-USU-10/11 necesitan asignación de alcance; no presumir que otra HU ya los cubre |
| Administrador.registroCompleto / completarRegistro | Se permite perfil parcial; no existe flag ni servicio de completado | **RF-USU-06 pendiente**, citado por CU-09. No hay acuerdo que elimine el requisito ni asignación explícita a una HU posterior. No cerrar conformidad completa de CU-09/ERS hasta asignarlo y resolver su contrato |
| Usuario posee Billetera 1:1; saldo y fechaCreacion | Wallet.user OneToOne, saldo Decimal cero, sin fecha propia | DEC-03 autoriza creación conjunta y eliminación de fecha redundante; métodos financieros quedan en HU-010/011 y compras |
| BitacoraEvento y registrar / consultarPorCliente | RegistrationEvent, AuthenticationEvent, AdministrationEvent y helpers | Separación técnica por flujo; fecha/actor/objetivo y origen HMAC donde corresponde, sin detalles libres con secretos. No hay consulta general por cliente; estructura/retención deben revisarse, no se presume bitácora universal terminada |
| Suscripciones, vuelos, promociones, reservas, compras, check-in e historial | Sin API de esas operaciones en iteración 1 | HU-001–006, 010–021 según dominio. El rol identifica al actor, no implementa esos métodos |
| Componentes no dibujados | RegistrationConsent, EmailVerification, PasswordRecovery, AdministratorNotification, Session/AccountSession, serializers, políticas y cuotas | Adaptaciones técnicas para consentimiento, uso único, entrega persistente y seguridad de DEC-11/13/16–22; no nuevos actores de negocio |

El bootstrap ROOT usa `create_root`, idempotente e interactivo, previsto como adaptación
operativa en §11.4 del complemento. Integración debe incorporarlo al aprovisionamiento
inicial; no hay credenciales predeterminadas ni creación automática al aplicar migraciones.

## Verificación y evidencia

La revisión inicial no requería repetir todo: se reutilizaron las 319 pruebas/93,22 % y
las migraciones sobre base heredada/nueva documentadas en HU-009, además de matrices de
HU-007/008. Las reproducciones del defecto compartido de contraseñas justificaron luego
una suite completa. No se repitió el ensayo HTTP real contra Pwned Passwords ni SMTP.

- Antes de corregir: **3 fallos reproducidos** (carrera para dos roles y destinatario obsoleto).
- Tras corregir: **7 pruebas focalizadas aprobadas** en 11,76 s, incluido flujo cliente
  registro → login → recuperación → verificación y ROOT → cambio → enlace anterior inválido.
- Primera suite posterior: **325 aprobadas, 1 fallo de reloj**, diagnosticado y corregido.
- Resultado final: **326 pruebas aprobadas** en 190,29 s; **93,45 % de cobertura global**
  (mínimo configurado 70 %). Incluye regresiones HU-007/008/009 y pruebas de migración.
- Ruff y formato correctos (78 archivos); Django check sin incidencias; migrate --check
  sin pendientes; makemigrations --check --dry-run sin diferencias; OpenAPI estricto sin avisos.
- PostgreSQL real confirmado: **17.11 (Debian 17.11-1.pgdg13+2)**; settings de pruebas
  explícitos, sin SQLite, servicios externos simulados y correo en memoria.

Comandos nuevos ejecutados en esta revisión, desde la raíz:

```bash
docker compose exec -T -e DJANGO_SETTINGS_MODULE=config.settings.test backend pytest -q apps/users/tests/test_iteration1.py --tb=short
docker compose exec -T -e DJANGO_SETTINGS_MODULE=config.settings.test backend pytest -q --cov --cov-report=term-missing --cov-fail-under=70 --tb=short
docker compose exec -T backend ruff check .
docker compose exec -T backend ruff format --check .
docker compose exec -T backend python manage.py check
docker compose exec -T backend python manage.py migrate --check
docker compose exec -T backend python manage.py makemigrations --check --dry-run
docker compose exec -T -e DJANGO_SETTINGS_MODULE=config.settings.test backend python manage.py spectacular --validate --fail-on-warn --file /tmp/iteracion1-schema.yaml
git diff --check
```

La suite crea su base de pruebas; las pruebas heredadas de migración usan esquemas efímeros.
No se borraron datos/volúmenes existentes ni se aplicó una migración nueva. No se observaron
CI remota, entrega SMTP, despliegue o integración visual. La comprobación manual del punto
de entrada es una guía para el equipo, no una ejecución atribuida a esta revisión.

## Pendientes y conclusión de entrega

| Pendiente / responsable sugerido | Efecto concreto |
|---|---|
| Política real aprobada — responsable funcional/institucional, integración configura | **Bloquea registro productivo** y cierre completo HU-007. Desarrollo sintético sí puede continuar |
| RF-USU-06, perfil RF-USU-10/11 — responsable funcional y backend | Asignar historia/alcance y contrato. No prometer completado/perfil en frontend; impide declarar toda la ERS de usuarios cubierta |
| Correspondencia de herencia, bitácora y dibujo actualizado — equipo backend y revisor de diseño | Ratificar/adaptar diagrama; no bloquea consumir API actual, sí la aprobación de correspondencia completa con diseño |
| Pantallas, cookies/proxy, actividad y estados — frontend/integración | Falta prueba de extremo a extremo con navegador; contratos disponibles |
| SMTP, tareas, monitorización, backups y HTTPS — integración | Falta evidencia operativa y entrega real; consola/memoria no equivalen a producción |
| Permisos de vuelos/finanzas/compra — responsables de futuras HU | Aplicar rol, verificación y propiedad allí; no habilitar acciones por interfaz solamente |
| P-05 restante y demás P-XX — equipo funcional según complemento | Bloquean sus operaciones específicas, no login/registro de prueba/administración aprobados |

**Conclusión:** el backend del alcance implementado puede entregarse para desarrollar e
integrar registro, verificación, autenticación, recuperación y administración ROOT. La
entrega conserva los límites anteriores y permite trabajar sin esta conversación. No
supone cierre completo de CU-09/ERS de usuarios, validación académica del diseño, historia
integrada de extremo a extremo ni preparación productiva. Consolidar los procesadores en
una abstracción común sería una mejora opcional; no se necesita para esta entrega.
