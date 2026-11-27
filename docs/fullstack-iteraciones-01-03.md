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

## Diagnóstico confirmado

- Registro envía `birth_place` y códigos de género incompatibles, sin IDs geográficos.
- Perfil hace `Promise.all` de perfil y ventas incluso para roles sin permiso comercial.
- Depósitos omiten medio de pago e idempotencia; falta interfaz de medios registrados.
- Reservas/compras omiten idempotencia; compras/conversión omiten cotización y total aceptado.
- Navegación y gestión de sesión no distinguen carga inicial; logout oculta fallos de revocación.
- Validación frontend exige ocho caracteres y número; backend exige política local Django
  (mínimo doce, no exclusivamente numérica, no común ni similar a datos personales).
- No hay framework de pruebas frontend. Se solicita aprobación para Playwright.
- Node no está en PATH; se prepara runtime local aislado, sin sustituir herramientas del usuario.
- CI remoto del commit e24ced1 terminó en fallo; diagnóstico de anotaciones en curso.

## Decisiones pendientes consultadas

Permiso financiero de administradores; detalles expresamente pendientes de cancelación
(estado/fecha, agrupación, ida/regreso, reservas, plazos, límites de silla, check-in,
confirmaciones, facultades administrativas y notificaciones); dependencia Playwright.
El rediseño principal de resolución por comprador ya está autorizado y no se vuelve a consultar.

## Evidencia anterior, no equivalente a aceptación full-stack

Antes de esta ampliación: 447 pruebas backend de regresión y nueve pruebas adicionales de
catálogos/selectores/ROOT pasaron en PostgreSQL 16.15 aislado. El objetivo Compose es 17.11.
Importación geográfica repetida, migraciones y OpenAPI validados localmente.
