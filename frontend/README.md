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

La iteración 2 incluye prototipos locales para HU-001 (programar vuelo), HU-005 (buscar
y filtrar vuelos), HU-006 (catálogo por ciudad) y HU-010 (medios de pago y depósitos).
Se accede a búsqueda y catálogo desde la navegación; la programación está en
`/admin/vuelos/nuevo` y la billetera en `/billetera`. Estas vistas usan datos de demostración
persistidos en `localStorage`, no realizan operaciones financieras ni de vuelos reales y no
representan operaciones confirmadas en el backend.

La iteración 3 incorpora prototipos locales para HU-012 (reservar tiquetes) y HU-013
(comprar tiquetes). Se accede a `/reservas/nueva` y `/compras/nueva`; incluyen selección
de vuelo, clase, hasta cinco viajeros, validación de mayoría de edad y duplicados,
control de cupos y, para compra, validación y descuento simulado de la billetera.