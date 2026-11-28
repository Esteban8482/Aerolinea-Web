# Frontend de Aerolínea

Interfaz web inicial de Alas, construida con React, TypeScript y Vite.

## Ejecutar

```bash
npm install
npm run dev
```

El build de producción se verifica con:

```bash
npm run build
```

## Alcance actual

La interfaz implementa el espacio visual del cliente: resumen, perfil, actividad reciente, búsqueda de vuelos, reservas y compras, cancelaciones, cambio de silla y estados responsive.

La interfaz de autenticación incluye ingreso, creación de cuenta, recuperación de contraseña y verificación de correo, integrada con sesiones, CSRF y los endpoints disponibles.

## Iteración 3

- En **Vuelos → Gestión**, los administradores pueden editar/cancelar vuelos programados y crear promociones temporales por vuelo y clase. La edición requiere motivo y las promociones envían fechas ISO 8601 con zona horaria al backend.
- En **Mi perfil**, el cliente consulta reservas/compras, puede cancelarlas según las reglas vigentes y cambiar una vez la silla antes del check-in.
- La ruta **Check-in** permite confirmar tiquetes dentro de las 24 horas previas a la salida y descargar el pasabordo PDF. Los viajeros sin sesión pueden solicitar un enlace seguro con localizador, documento y correo.
- El acceso de invitado conserva el token solo en memoria después de leerlo del fragmento `#token=...`, lo elimina de la barra de direcciones y lo envía exclusivamente en `X-Checkin-Token`. Las operaciones y ventanas permitidas las valida el backend.

Estas pantallas requieren que el backend de la iteración 3 esté integrado y sus migraciones/procesadores estén configurados; el build del frontend no verifica entrega de correos ni disponibilidad de PostgreSQL.
## Sistema visual — Hito 1

Los tokens compartidos se mantienen en `src/styles.css` y los componentes de formulario,
feedback, carga, contenedor de acceso y diálogo en `src/components/UI.tsx`. `RemoteSelect`
usa una selección cerrada y búsqueda remota paginada dentro del desplegable; no descarga
el catálogo geográfico completo. Los selectores comerciales conservan su API independiente.
Los breakpoints comunes de composición son 760 px y 460 px; los ajustes existentes de
pantallas de negocio se conservan hasta su hito correspondiente.

Las rutas de autenticación y sus contratos siguen vigentes. El estado de sesión descarta
respuestas iniciadas antes del logout, y los tokens de verificación/restablecimiento se
retiran del fragmento de URL. Las comprobaciones y capturas reales, con limitaciones
explícitas, están en [el checkpoint del Hito 1](../docs/design/IMPLEMENTATION_PROGRESS.md).
