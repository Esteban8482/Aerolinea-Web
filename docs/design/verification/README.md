# Verificación local del Hito 1

Ejecutar desde la raíz del repositorio con Django/worker/PostgreSQL de desarrollo y Vite
activos. Los scripts usan Playwright externo al producto; no se modificó `package.json` ni
el lockfile. En esta ejecución se instaló en `/tmp/alas-browser` y Chromium en el caché del
usuario. Las bibliotecas de Chromium que faltaban se extrajeron en `/tmp/alas-browser/libs`
sin instalar paquetes globales.

```bash
NODE_PATH=/tmp/alas-browser/node_modules \
LD_LIBRARY_PATH=/tmp/alas-browser/libs/extracted/usr/lib/x86_64-linux-gnu \
node docs/design/verification/visual.cjs
```

Usar el mismo entorno para `selectors.cjs`, `states.cjs`, `session-race.cjs` y `dialog.cjs`.
En otro equipo adaptar las rutas a su instalación local de Playwright. Ejecutar los scripts
secuencialmente para reducir consumo y evitar competencia por foco. Los scripts de sesión y
diálogo leen las credenciales **ficticias de desarrollo** ya publicadas en README; no usarlos
contra un entorno compartido o de producción. No cambian contraseñas ni confirman compras,
cancelaciones o modificaciones de datos de negocio.

- `visual.cjs`: login, recuperación, verificación sin token y restablecimiento con token
  sintético, en 1440×1000, 768×1024 y 390×844. Captura implementación, overflow y labels.
- `selectors.cjs`: geografía real, dependencias, teclado, paginación y escenarios de red
  simulados (503, vacío y respuestas fuera de orden). No cambia catálogos.
- `states.cjs`: éxito de verificación/reset **simulado en navegador**, validación de
  confirmación, recuperación real de una cuenta inexistente `.invalid`, selector comercial
  real y revisión móvil de consumidores. No envía correo a una cuenta real.
- `session-race.cjs`: login/recarga/logout reales de CLIENTE y ADMINISTRADOR; retiene una
  respuesta autenticada anterior al logout y la libera después para verificar que se ignora.
- `dialog.cjs`: administrador abre confirmación y sale con Escape; verifica ciclo y retorno
  de foco. No envía la cancelación.

Las capturas están en `../implementation-screenshots/`. Los estados simulados acreditan la
interfaz; los tests Django sobre base aislada acreditan los contratos y reglas del servidor.
El checkpoint principal registra resultados, entorno y límites; estos scripts no equivalen
a CI, entrega SMTP, evaluación completa WCAG ni aceptación de hitos posteriores.
