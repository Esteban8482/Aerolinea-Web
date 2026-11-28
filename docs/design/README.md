# Alas · Paquete de referencia de diseño

## Abrir

1. Extrae el ZIP. Dentro encontrarás `docs/design/` listo para copiar a la raíz de `Aerolinea-Web` (fusiona con `docs`, no reemplaces el resto).
2. Abre `docs/design/index.html` en el navegador. No necesita npm, Django, Docker, Internet ni instalación de dependencias. Si tu navegador restringe archivos locales, desde la raíz del repositorio ejecuta `python3 -m http.server 8081 --bind 127.0.0.1 --directory docs/design` y abre `http://localhost:8081/`.
3. La galería enlaza cada prototipo y sus capturas en móvil. Las capturas de estados interactivos están en `screenshots/states/`. Las imágenes de escritorio están en `screenshots/desktop/` y las de móvil en `screenshots/mobile/`.
4. Entrega a Codex `docs/design/CODEX_IMPLEMENTATION.md` como instrucción y asigna un solo hito. Revisa `UX_GUIDELINES.md` antes de aprobar propuestas abiertas.

## Contenido

- 39 prototipos HTML en español, con CSS compartido y JavaScript de interacción local.
- 78 capturas PNG de páginas completas y 5 capturas de estados interactivos: escritorio 1440×1000 y móvil 390×844 (altura puede ser mayor por contenido).
- Sistema de diseño, guía UX, mapa de pantallas y contratos, instrucciones de implementación, manifiesto y resultados de renderizado.

## Límites y seguridad

Son referencias visuales nuevas, construidas a partir de los conceptos discutidos en el chat. No son una exportación exacta de los widgets anteriores ni código React listo para producción. No están conectados a Django ni a PostgreSQL, no autentican, no envían correos, no procesan pagos ni guardan datos. Los formularios, filtros, enlaces, diálogos, selecciones de asiento y estados muestran interacciones ilustrativas. No introducir datos personales ni tarjetas reales. La selección geográfica muestra un catálogo pequeño de ejemplo; los IDs, dependencias y paginación reales deben integrarse con la API. Las capturas muestran solo los estados renderizados, no todos los posibles caminos funcionales. Fechas, códigos IATA, cupos, mapas, nombres, saldos y métricas son ficticios. El mapa de asientos y algunas opciones de navegación, preferencia de pago y dashboard requieren validación o aprobación antes de implementar.

No se ha modificado el repositorio ni ejecutado la aplicación real. Las pruebas de este paquete no certifican el backend ni la integración existente.
