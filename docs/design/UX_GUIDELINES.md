# Alas — Guía de experiencia y contratos funcionales

## Prioridad de fuentes

Instrucciones explícitas del usuario y decisiones vigentes del proyecto > documentación Markdown actualizada > contratos y tests actuales > estas referencias visuales > requisitos históricos supersedidos. Los HTML no son fuente normativa del backend. No reintroducir Pwned Passwords ni reglas obsoletas. Esta guía incorpora los cambios solicitados en el chat, y distingue las propuestas todavía abiertas.

## Reglas explícitas del nuevo encargo

- Registro: datos personales, fecha y lugar de nacimiento, datos de contacto/acceso y consentimiento. Eliminar facturación obligatoria de registro y moverla al método de pago. Catálogo geográfico mundial independiente del comercial. Conservar datos históricos y migrar sin pérdida.
- Billetera: cliente nuevo inicia con saldo cero y sin métodos. Mostrar métodos registrados y añadir uno durante depósito/checkout. No depositar sin medio propio, activo y elegible. Solo CLIENTE con correo verificado; ROOT y ADMINISTRADOR sin billetera personal.
- Tarjeta: titular, 16 dígitos ASCII en grupos de cuatro, fecha de vencimiento (ya requerida en contrato anterior), CVV de tres dígitos para demostración, dirección de facturación con país/división/ciudad. La restricción de 16 es del proyecto, no una afirmación universal de Visa. Mantener términos comerciales naturales. Procesamiento interno sin bancos ni pasarela.
- Privacidad: **exclusivamente datos sintéticos de prueba**, aviso discreto antes de introducirlos; sin credenciales financieras reales. Preferir campo CVV solo en el cliente, descartar sin transmitir; jamás persistir, loguear, enviar a analytics, incluir en errores o devolver por API. No almacenar PAN completo; últimos cuatro y HMAC vigente. Usar únicamente ejemplos de prueba aprobados por el equipo, no aceptar PAN real en entorno de demostración. El mock no hace solicitudes externas ni persiste datos.
- Búsqueda: filtro de rango y orden ascendente/descendente por precio y hora de salida. La tarifa debe ser la vigente para la clase seleccionada y elegible para la capacidad solicitada. Rutas comerciales dependientes solo con oferta válida. No ampliar rutas internacionales inversas sin autorización.
- ADMINISTRADOR y ROOT: revisar todas las interfaces y permisos; diseño operativo coherente, no expandir atribuciones.

## Recorrido comercial

1. Portada → búsqueda → resultados de vuelos disponibles. Edición de criterios conserva contexto. En ida/regreso, seleccionar regreso compatible con llegada de ida. Precio por persona/trayecto inequívoco; total del grupo en revisión.
2. Visitante puede buscar; login/registro cuando se reserva o compra. Verificación de correo necesaria. Conservar intención y ruta de retorno, validar destino interno seguro.
3. Viajeros y contacto de emergencia → cotización → aceptación explícita. Validar máximo cinco, adulto al momento del viaje, identidad normalizada y duplicados. Reserva sin pago retiene cupos y no congela precio.
4. Compra con billetera. Si falta saldo, abrir flujo de añadir dinero en contexto y volver a cotización sin perder viajeros ni selección. No cobrar automáticamente tras recarga; comprador vuelve a aceptar. Clave idempotente estable durante reintento del mismo payload, nueva clave ante cambio material autorizado; no doble débito ni falsa confirmación.
5. Mis viajes: reservas, compras y resoluciones básicas necesarias para las HU actuales, no historial avanzado HU-015. Mostrar estado y fechas límite. Cancelación voluntaria respeta 1 h nacional / 3 h internacional; si existen tiquetes pendientes de resolución, bloquear cancelación general y enlazar flujo específico.
6. Cancelación de aerolínea: admin revisa impacto, motivo, doble confirmación. Comprador recibe enlace de navegación autenticado; misma ruta/clase, futuro, grupo completo, disponibilidad y compatibilidad temporal; reubicación sin cargo y conserva precio. Reembolso siempre como alternativa, a billetera de quien pagó. En ida cancelada, tratamiento de regreso según regla acordada; mostrar importe total y alcance antes de confirmar, no reembolsar servicios realizados sin política explícita. Revisar defectos pendientes de trazabilidad/importes y reprogramación incompatible; no inventar derechos adicionales. Panel admin por viajero: pendiente, reubicado, reembolsado. Reserva sin pago se libera sin abono.
7. Check-in: por compra/localizador y vuelo, selección atómica, ventana 24 h antes de salida. Invitado con magic link limitado a viajero/compra, sin datos financieros; respuesta genérica para solicitud. Token en fragmento, retirado de URL, en memoria y header autorizado. Cambiar silla una vez antes del check-in, misma clase, disponible. No confundir cambio de asiento con cambio de vuelo. PDF de backend, no mock. 
8. ROOT: administración de cuentas y cambio propio mediante contraseña actual/nueva/confirmación, revocación de todas sus sesiones y login manual. Conservar endpoints y validación local; no reenviar credenciales por correo.

## Microcopy canónica

| Interno / evitar | Visible |
|---|---|
| `TARJETA`, medio simulado | Tarjeta, método de pago |
| Depósito simulado | Dinero añadido / Depósito |
| Registrar medio | Añadir método de pago |
| Alias | Nombre de la tarjeta (opcional si se aprueba) |
| Desactivar medio | Eliminar método de pago (conservar historial) |
| `COMPLETO` | Ida y regreso |
| `UNICO` | Solo ida |
| `PROGRAMADO` | Programado |
| `PENDIENTE_RESOLUCION` | Requiere atención / Pendiente de resolución |
| `REALIZADO` | Realizado |
| `price_changed` | El precio cambió. Revisa y acepta el nuevo importe. |
| `csrf_failed` | No se pudo verificar la solicitud. Intenta nuevamente. (corregir causa, no ocultarla) |
| `insufficient_funds` (verificar código real) | Saldo insuficiente. Añade dinero para continuar. |
| timeout / resultado incierto | No se pudo confirmar el resultado. Consulta el estado o reintenta la misma operación. |

No afirmar que se hizo un cargo bancario. La confirmación se refiere al saldo interno. No incluir términos técnicos en botones ni enumeraciones sin traducir. Aviso de demostración solo donde evita confusión con pagos reales, no en toda la experiencia.

## Decisiones abiertas (no implementar sin aprobación)

| Tema | Propuesta visible en referencia |
|---|---|
| Navegación | Mis viajes / Billetera / Mi cuenta y sidebar por rol. URLs finales y cambios de IA de información requieren aprobación. |
| Cuenta bancaria | Conservar soporte existente; decidir exposición y requisitos, especialmente retiros HU-011. El prototipo prioriza tarjeta. |
| Franquicia y débito/crédito | Admitir Visa y Mastercard de prueba; definir identificación fiable por fixture, sin consulta externa. No asumir que todas las tarjetas reales tienen 16 dígitos. |
| Medio preferido y alias | Preferida en ejemplo, alias opcional autogenerado; no añadir persistencia ni operación nueva antes de confirmar. |
| Edición facturación y código postal | Dirección adicional opcional; código postal según país, edición y reactivación requieren acuerdo. |
| Orden por defecto y clase vacía | Menor precio y tarifa mínima elegible identificando clase son propuestas. Si no se aprueban, mantener regla actual. |
| Métricas de administrador | Números ilustrativos. No crear nuevos KPIs, consultas agregadas ni dashboard de reporting si no se autoriza. |
| Aeropuertos, asientos | IATA y mapa alfabético son ejemplos visuales; modelo actual y datos autorizados prevalecen. |
| Reprogramaciones y devolución de regreso realizado | Resolver las políticas pendientes antes de modificar servicios o dinero. |

HU-011 retiros/2FA, HU-015 historial avanzado y HU-018–021 siguen fuera del alcance. No crear botones operativos engañosos para funcionalidades aún no implementadas.
