# Verificación del paquete de diseño

## Evidencia ejecutada

- 39 páginas × 2 viewports: **78 capturas PNG** de página completa en Chromium, 1440 × 1000 (escritorio) y 390 × 844 (móvil).
- 39 comprobaciones adicionales de ancho de documento a 768 × 1024 (tableta).
- 20 comprobaciones automatizadas de referencia, incluyendo integridad de enlaces a archivos locales, búsqueda en combobox, selección de ida/regreso, rango y orden de precios/horas, agrupación del número de tarjeta de prueba, formato de vencimiento, importe de depósito, diálogos, doble confirmación, selección grupal, selección de asiento y visibilidad de contraseñas.
- 5 capturas adicionales de estados interactivos en `screenshots/states/`.
- Ninguna excepción JavaScript detectada durante el renderizado final; sin desbordamiento horizontal global en los anchos probados. Las tablas operativas admiten desplazamiento interno en móvil.
- Inspección visual de una muestra de pantallas: resultados comerciales, billetera, tarjeta en móvil y gestión administrativa.

Detalles por página y comprobación: `render-results.json` e `interaction-results.json`.

## Método y límites

Chromium en el entorno de generación bloqueó la navegación directa a archivos locales y localhost. Para renderizar y probar los prototipos se cargó el mismo HTML con CSS/JS incrustados mediante Playwright; los enlaces relativos se verificaron por existencia de archivos, no mediante navegación real. Esta limitación no requiere cambios en los archivos entregados. El lector puede abrir `index.html` directamente o mediante un servidor HTTP local.

No se ejecutó el backend real, no se realizaron llamadas a API, no se probaron sesiones, PostgreSQL ni transacciones, y no se evaluó exhaustivamente WCAG ni el comportamiento de cada interacción. La demostración de catálogo es local y pequeña, los selectores de geografía y comercial no implementan toda la lógica de dependencia real, y las acciones de negocio son ilustrativas. Se requiere validación funcional y visual del sistema integrado después de implementar cada módulo.
