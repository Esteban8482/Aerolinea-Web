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

La pantalla implementa el espacio visual del cliente: resumen, perfil, actividad reciente, filtro de tabla, formulario de diligenciamiento rápido, diálogo de edición y estados responsive.

La rama de HU-008 añade el flujo visual de autenticación: ingreso, creación de cuenta, recuperación de contraseña y verificación de correo. Cada estado es navegable con datos locales de demostración para validar la experiencia antes de conectar sesiones, CSRF y endpoints.

Por ahora no incluye integración con Buscador, Reservas, Billetera, Mapa de Sillas ni Vistas Administrativas. Los datos mostrados son locales de demostración y no representan operaciones confirmadas en el backend.