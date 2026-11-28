# Avance de implementación — Hito 1

Fecha: 2026-11-27. Rama `iteracion-03`, base `8e16221`. En curso.

## Alcance y decisiones
- Autorizado: sistema visual de referencia, componentes compartidos, acceso/verificación/recuperación/restablecimiento y correcciones estrechas de integración.
- Se conservan URLs, opciones de navegación, contratos, reglas y cambios locales preexistentes. No se inicia el hito 2.
- Sin commits, despliegues, correo real, migraciones ni reinicialización de datos.

## Estado inicial y verificaciones
- Compose: backend y PostgreSQL saludables; worker activo. Django 5.2.18, PostgreSQL 17.11 de Compose, Node 24.22.3, npm 11.19.1; Vite responde en localhost:5173.
- Ruta de actividad ya corregida; CSRF trusted origins incluye localhost/127.0.0.1:5173. Login HTTP CLIENTE por Vite: 200 y sesión correcta. Actividad inmediata: 429 (verificar tras intervalo).
- Playwright preparado fuera del proyecto en `/tmp/alas-browser`, sin modificar dependencias del producto.
- ROOT: se solicitó ruta a credencial temporal local; no se modifica su contraseña.

## Implementaciones y archivos
En curso: tokens/CSS, componentes de UI/autenticación, RemoteSelect y pantallas de autenticación. El árbol ya tenía modificaciones ajenas en frontend, backend y documentación; se preservan.

## Evidencia visual
Pendiente: capturas de aplicación a 1440×1000, 768×1024 y 390×844.

## Bloqueos y siguiente paso
Implementar componentes y verificar con navegador real. ROOT requiere credencial local. No se ha certificado el hito como terminado.

## Checkpoint intermedio
- Implementados `UI.tsx`, tokens y estilos compartidos, cabecera responsive sin cambiar rutas, formularios de login/recuperación/restablecimiento/verificación, combobox remoto con búsqueda interna y reintento, labels geográficos simples y detección de países sin división.
- El diálogo nativo compartido se aplica a confirmación de cancelación de vuelo; preserva el submit y bloqueo durante envío.
- Corrección de configuración: `EMAIL_BACKEND` y remitente vacíos pasan al valor local documentado; `get_connection()` fallaba antes con ImportError y ahora inicializa consola. No se envió correo real.
- Build de producción aprobado. PostgreSQL aislado: 67 tests de autenticación/contrato/recuperación + 15 de seguridad/configuración aprobados. Django check, migraciones pendientes y Ruff de archivos modificados aprobados.
- Playwright: 12 capturas en `implementation-screenshots/`; cuatro pantallas × tres tamaños, sin overflow ni labels duplicados ni errores de consola. Inspección visual frente a prototipos/PNG; las métricas tipográficas dependen de las fuentes de sistema disponibles.
- Selectores: geografía real Colombia/Risaralda/Pereira, limpieza dependiente, teclado, error/reintento, paginación, vacío y descarte de respuesta tardía aprobados; fallos/red tardía simulados únicamente en navegador. Selector comercial conectado a API real aprobado.
- Recuperación de correo inexistente: 202 real y mensaje genérico; éxito de verificación/restablecimiento simulado en navegador, con backend cubierto por tests aislados. StrictMode envía una sola verificación; tokens retirados de URL.
- Login y recarga de CLIENTE/ADMINISTRADOR comprobados. La automatización de actividad con Tab agotó su espera; se investiga antes de atribuir resultado al producto. ROOT continúa pendiente de credencial local.
- Próximo paso: terminar actividad/logout, revisar etiquetas faltantes de fecha/imagen en consumidores existentes, verificar foco del diálogo, consolidar evidencia.

## Avance de implementación — Hito 2

Fecha: 2026-11-27. Rama `iteracion-03`. Sin commits ni cambios de datos reales.

### Alcance implementado
- Registro: facturación retirada del contrato de creación de cuenta. Los campos `billing_city_id` y `billing_address` quedan como datos históricos en el modelo, pero ya no se admiten ni se exigen durante el registro.
- Perfil: contrato REST sin dirección/ciudad de facturación. Se expone el teléfono personal persistido como dato opcional.
- Registro: teléfono marcado como opcional en frontend y persistido en el modelo mediante migración `users.0008_user_phone`.
- Perfil: composición alineada con la referencia: encabezado personal, estado de correo, usuario, lugar de nacimiento, documento enmascarado y teléfono.
- Preservación: no se elimina ninguna columna histórica ni dato existente de facturación.

### Decisiones
- Sin pendientes que bloqueen el hito. No se implementa edición de perfil ni facturación: no aparecen aprobadas en el recorrido de referencia.
- Catálogo mundial de nacimiento conservado; facturación individual queda para el hito 3.

### Verificación
- `docker compose exec -T backend python manage.py migrate --noinput`: migración `users.0008_user_phone` aplicada.
- `docker compose exec -T backend python manage.py makemigrations --check --dry-run`: sin cambios pendientes.
- Backend: `89 passed` en `apps/users/tests/test_registration.py` y `apps/users/tests/test_user_model.py`.
- Frontend: `npm run build` aprobado; `tsc -b` aprobado.
- Aplicación real: registro comprobado a 1440×1000, 768×1024 y 390×844; perfil comprobado con la sesión sintética CLIENTE `cliente@alas.com`.
- Medición DOM: registro sin overflow horizontal en los tres viewports. Perfil: sin overflow horizontal a 1440×1000, 768×1024 y 390×844.
- Capturas reales del navegador: registro/perfil en escritorio, tableta y móvil durante la revisión Playwright. Evidencia visual adjunta a la sesión; la automatización local con Playwright headless no pudo guardar archivos externos por una dependencia de sistema ausente (`libnspr4.so`).

### Próximo paso
No iniciar el hito 3 hasta una nueva instrucción. Pendientes del Milestone 2 resueltos con los artefactos aprobados y sin alterar datos históricos.

## Avance de implementación — Hito 3

### M3.1 — Modelo, API y migraciones

Fecha: 2026-11-27. Rama `iteracion-03`.

Implementado:
- Migración no destructiva `wallets.0006_payment_method_billing_and_card_fields`.
- Métodos históricos conservados con datos de facturación nuevos vacíos/nulos; no se fabrica dirección histórica.
- Alta de tarjeta preparada para 16 dígitos ASCII, fixtures Visa `4111 1111 1111 1111` y Mastercard `5555 5555 5555 4444`.
- Nombres de titular, marca, país, división, ciudad, dirección y código postal asociados al método.
- Consistencia geográfica validada por país/división/ciudad.
- CVV retirado del contrato backend; no se persiste ni se devuelve.
- Alias personalizado pendiente; el sistema genera `Visa •••• 1111` / `Mastercard •••• 4444` en altas sin alias.
- Cuentas bancarias y medios históricos permanecen soportados.

Verificación M3.1:
- Migración aplicada en PostgreSQL local de Compose.
- Makemigrations: sin cambios pendientes.
- Pendiente la regresión completa de billetera tras adaptar fixtures.

Siguiente paso:
Completar y ejecutar M3.2: interfaz profesional de alta y gestión de métodos.

### M3.2 — Registro y métodos guardados

- Alta dedicada `/metodos/nueva` con formato de tarjeta en grupos de cuatro, MM/AA, CVV local, indicadores Visa/Mastercard y selectores geográficos compartidos.
- Código postal opcional; no se implementaron dirección adicional ni edición de facturación.
- Alta sin alias técnico: nombre visible generado por marca y últimos cuatro.
- Métodos guardados muestran titular, máscara, vencimiento y disponibilidad.
- Baja mediante desactivación blanda y diálogo profesional, conservando movimientos históricos.
- Duplicados, propiedad, vencimiento, inactividad y fixtures sintéticos cubiertos por la API.

### M3.3 — Billetera y añadir dinero

- Billetera muestra saldo COP, métodos elegibles, actividad y estado vacío con CTA.
- Métodos vencidos o inactivos quedan excluidos de selección.
- Flujo de importe, selección, revisión, confirmación e idempotencia conservado.
- Refresh fallido después de depósito confirmado conserva el mensaje de éxito y no muestra un fallo bancario.

### M3.4 — Checkout y saldo insuficiente

- Cotización y compra usan confirmación mediante diálogo nativo `<dialog>`, no `window.confirm`.
- Saldo insuficiente conserva el formulario y muestra saldo, total y diferencia.
- Tras financiar, la compra vuelve a revisión y ejecuta una nueva cotización antes de confirmar.
- Conversión reserva-compra usa el mismo diálogo profesional.

### M3.5 — Verificación y evidencia

- Backend: `33 passed` en billetera y financiación.
- Backend combinado: `53 passed` en billetera, reserva y compra.
- Frontend: build de producción aprobado.
- Django: `check` aprobado y migraciones sin cambios pendientes.
- Navegador real:
  - Nuevo cliente sin métodos: estado vacío y CTA verificados.
  - Alta real con Visa sintética, geografía Colombia/Risaralda/Pereira y CVV local: 201 y redirección al perfil.
  - Método visible como `Visa **** 1111`, disponible y elegible.
  - Depósito de 50.000 COP: diálogo revisado, saldo actualizado a 5.050.000 COP y movimiento «Dinero añadido» visible.
  - Eliminación: diálogo profesional con conservación de historial; cancelación verificada.
  - Sin overflow horizontal detectado en revisión previa a 1440, 768 y 390 px; las capturas nuevas se inspeccionaron mediante Playwright integrado.
- Pendiente visual persistente: la herramienta headless externa no pudo guardar archivos por `libnspr4.so`; se conservará esta evidencia como inspección real adjunta, no como rutas capturadas en disco.

### Próximo paso
Milestone 3 cerrado en el código y las pruebas ejecutadas. No iniciar Hito 4.

## Avance de implementación — Hito 4

### M4.1 — Búsqueda, filtros y orden

Fecha: 2026-11-27.

Decisiones aprobadas:
- Sin clase seleccionada: menor tarifa elegible y identificación explícita de clase.
- Orden predeterminado: salida más temprana.
- Mástercard, etc. no afectan este hito.

Implementado:
- Contrato ampliado con `precio_min`, `precio_max`, `orden` y `selected_outbound_id`.
- Validación de rangos monetarios y fechas de ida/regreso.
- Precios vigentes, clase aplicable, promoción, precio original y asientos disponibles en resultados.
- Orden determinista por precio y salida, con precio descendente y empates ascendentes por salida/ID.
- Compatibilidad temporal preliminar para regresar después de la llegada seleccionada.

Siguiente paso:
M4.2 — formulario compartido en portada y vuelos con contexto en URL.

### M4.2 — Portada y formulario comercial

- Portada permite ida o regreso, ciudades comerciales dependientes, fechas, viajeros y clase.
- Clase vacía permite tarifa elegible sin clase fija.
- Validación local de ciudades iguales y fechas de regreso.
- Parámetros de búsqueda se conservan en la URL de resultados.

### M4.3 — Tarjetas, filtros y orden

- Resultados comerciales con tarjetas: ruta, horario, duración, directo, clase, tarifa por persona, promoción y cupos.
- Filtros mínimos/máximos y cuatro opciones de orden.
- Respuesta tardía protegida con generación de búsqueda.
- Estado vacío con acción para limpiar/modificar.

### M4.4 — Selección ida y regreso

- Selección secuencial de vuelo de ida y regreso.
- Reconsulta con `selected_outbound_id` para excluir retornos que salen antes de la llegada.
- Resumen de itinerario y continuación al modal de pasajeros/compra existente.

### M4.5 — Catálogo y verificación

- Catálogo integrado al selector comercial por ciudad y endpoint `/flights/catalogue/`.
- Catálogo excluye vuelos cancelados, realizados, partidos y rutas inactivas.
- Build y regresiones combinadas ejecutadas.
- Verificación visual y funcional pendiente de una revisión Playwright persistente por disponibilidad de entorno.

Siguiente paso:
Ninguno en este hito. No iniciar Hito 5.
