# Mapa de pantallas

Todas las referencias HTML se encuentran en `prototypes/`. Los PNG comparten el nombre de archivo base. Los slugs son nombres de referencia, no nuevas rutas autorizadas. La navegación del producto se decide con el usuario.

| Pantalla | Referencia HTML | Contexto | HU | Propósito |
|---|---|---|---|---|
| Inicio | `home.html` | public | HU-005/006 | Portada comercial, búsqueda principal y catálogo. |
| Buscar vuelos | `flight-search.html` | public | HU-005 | Formulario comercial con selector integrado. |
| Resultados de vuelos | `flight-results.html` | public | HU-005/006 | Tarjetas comerciales y filtros de precio/horario interactivos. |
| Catálogo de destinos | `flight-catalogue.html` | public | HU-006 | Catálogo público por origen. |
| Seleccionar regreso | `round-trip.html` | public | HU-005/013 | Segundo trayecto compatible. |
| Crear cuenta | `registration.html` | public | HU-007 | Registro sin facturación; catálogo de nacimiento. |
| Iniciar sesión | `login.html` | public | HU-008 | Acceso común por email o ID ROOT. |
| Recuperar acceso | `recovery.html` | public | HU-008 | Recuperación con respuesta no enumerativa. |
| Billetera | `wallet.html` | client | HU-010 | Saldo, métodos de pago y movimientos. |
| Billetera sin métodos | `wallet-empty.html` | client | HU-010 | Estado inicial sin método ni saldo. |
| Añadir tarjeta | `add-card.html` | client | HU-010 | Formulario de 16 dígitos, vencimiento y facturación individual. |
| Información de viajeros | `checkout.html` | client | HU-012/013 | Datos de viajeros y contacto de emergencia. |
| Revisar compra | `checkout-review.html` | client | HU-012/013 | Cotización, aceptación, compra o reserva. |
| Saldo insuficiente | `checkout-funds.html` | client | HU-010/013 | Continuidad de compra al añadir saldo. |
| Mis viajes | `my-trips.html` | client | HU-012/013/014/003 | Reservas, compras y eventualidades sin implementar historial avanzado. |
| Gestionar cancelación | `cancellations.html` | client | HU-003/014 | Resolución grupal; alcance e importe previo al reembolso. |
| Check-in | `guest-checkin.html` | public | HU-016 | Solicitud de enlace privado para viajero. |
| Check-in de grupo | `checkin-group.html` | client | HU-016/017 | Selección por compra y vuelo; confirmación atómica. |
| Cambiar asiento | `seat-selection.html` | client | HU-017 | Mapa de asientos para cliente o invitado autorizado. |
| Pasabordo disponible | `boarding-pass.html` | client | HU-016 | Estado confirmado y descarga del documento real por API. |
| Mi perfil | `profile.html` | client | HU-007/008/010 | Información personal sin datos de facturación. |
| Panel operativo | `admin-dashboard.html` | admin | HU-001/002/003/004 | Composición administrativa; métricas ilustrativas sujetas a aprobación y API. |
| Gestión de vuelos | `admin-flights.html` | admin | HU-001/002/003/004 | Tabla operativa legible y filtros administrativos. |
| Programar vuelo | `admin-flight-create.html` | admin | HU-001 | Formulario administrativo con rutas autorizadas. |
| Editar vuelo | `admin-flight-edit.html` | admin | HU-002 | Edición con motivo, ruta inmutable e impacto. |
| Detalle operativo | `admin-flight-detail.html` | admin | HU-002/003/004 | Panel por vuelo y doble confirmación de cancelación. |
| Promociones | `admin-promotions.html` | admin | HU-004 | Promociones con vigencia y clase explícitas. |
| Seguimiento de cancelaciones | `admin-cancellations.html` | admin | HU-003 | Estados por pasajero y resumen de afectación. |
| Mi cuenta administrativa | `profile-admin.html` | admin | HU-008/009 | Perfil operativo sin servicios comerciales. |
| Administradores | `root-dashboard.html` | root | HU-009 | Listado y accesos a funciones autorizadas de ROOT. |
| Crear administrador | `root-create.html` | root | HU-009 | Alta ROOT; campos exactos dependen del contrato actual. |
| Cambiar contraseña de administrador | `root-admin-password.html` | root | HU-009 | Cambio de clave de otra cuenta administrativa. |
| Mi seguridad | `root-security.html` | root | HU-009 | Cambio propio de ROOT y revocación de sesiones. |
| Verificar correo | `verify-email.html` | public | HU-007 | Estados de verificación y reenvío. |
| Restablecer contraseña | `reset-password.html` | public | HU-008 | Formulario desde enlace de recuperación válido. |
| Check-in del viajero | `guest-authorized.html` | public | HU-016/017 | Vista limitada de invitado mediante enlace privado. |
| Cambiar asiento del viajero | `guest-seat.html` | public | HU-017 | Selección de silla de invitado sin navegación financiera. |
| Cancelación sin alternativas | `cancellation-no-alternatives.html` | client | HU-003/014 | Reembolso accesible incluso cuando no existen vuelos compatibles. |
| Compra confirmada | `purchase-confirmation.html` | client | HU-013 | Confirmación tras respuesta autoritativa del servidor, no tras clic. |

## Mapeo a componentes reales (revisar rama actual)

| Bloque | Componentes/rutas de partida | Contratos a verificar |
|---|---|---|
| Compartidos | `App.tsx`, `Header.tsx`, `api.ts`, `styles.css`, `RemoteSelect`, `CatalogueSelect`, `FlightCitySelect`, `LocationFields` | sesión, CSRF, `/auth/session/activity/`, `/reference/*`, `/flights/city-options/`; BASE `/api/v1` una sola vez |
| Registro y acceso | `RegisterPage`, `LoginPage`, `VerifyEmailPage`, `ResetPasswordPage` | `/auth/register/` (ver ruta real), sesión, verificación/recuperación; nuevos campos de facturación fuera del registro |
| Comercial | `HomePage`, `FlightsPage`, `CatalogPage` (ver si está montado) | `/flights/search/`, catálogo, precios vigentes; rango/orden son extensión propuesta |
| Billetera | `WalletPanel`, `ProfilePage`, componentes nuevos si se aprueban | `/sales/wallet/`, `payment-methods/`, `deposit/`, `movements/`; `Idempotency-Key` y privacidad |
| Compra | `BookingModal`, `ProfilePage`, `operations.ts` | `/sales/quote/`, `/sales/reservations/`, `/sales/purchases/`; `accepted_total`, clave idempotente |
| Viajes y cancelación | `ProfilePage`, `CancellationsPage` | compras/reservas propias, `/sales/cancellations/{id}/`, importe y alcance de resolución autoritativos |
| Check-in | `CheckInPage`, `SeatManager` | `/sales/check-in/`, acceso por enlace, `X-Checkin-Token`, selección, PDF, silla; ver rutas exactas actuales |
| Administración | `FlightsPage`, `CancellationPanel` | administración vuelo, promoción, `performed`, `/sales/flights/{id}/cancellation-panel/` |
| ROOT | `AdministratorsPage`, `ProfilePage` | `/users/administrators/`, `/users/administrators/password/`, `/users/root/password/` |

Los contratos citados proceden de la última revisión de la rama en el chat; comprobar el estado actual antes de implementar. No cambiar URLs o nombres de campos simplemente porque el prototipo use una etiqueta más amigable.
