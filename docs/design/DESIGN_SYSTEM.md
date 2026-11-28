# Alas — Sistema de diseño v1.0

**Estado:** referencia propuesta para aprobación visual. Alcance: iteraciones 01–03. El HTML/CSS de `prototypes/` es la referencia de composición; las PNG en `screenshots/` son el resultado renderizado, no imágenes que deban colocarse como fondo. El producto seguirá siendo React + TypeScript + CSS y Django/DRF; no se propone una nueva dependencia.

## Identidad y tokens

| Token | Valor | Uso |
|---|---|---|
| `--primary` | `#500099` | Identidad Alas, CTA principal, navegación |
| `--primary-hover` | `#7135B1` | Interacción principal |
| `--accent` | `#F0E7FA` | Selección, acciones secundarias suaves |
| `--bg` | `#FAF7FC` | Fondo general |
| `--surface` | `#FFFFFF` | Formularios y tarjetas |
| `--ink` | `#191524` | Texto principal |
| `--muted` | `#625C70` | Texto secundario |
| `--line` | `#DED5E6` | Bordes y divisores |
| `--success` | `#166534` | Confirmación |
| `--warning` | `#92400E` | Requiere atención |
| `--danger` | `#B91C1C` | Errores y acciones destructivas |

Púrpura dominante, fondos claros, acento rosa de marca discreto. Sin degradados ornamentales fuera de la portada y la tarjeta de saldo. No introducir fotografías, logotipos de aeropuertos, iconos de marca ni tipografía externa sin aprobación. El pequeño símbolo de avión de los prototipos es una representación provisional: conservar el logotipo aprobado del proyecto si existe. Franquicias en métodos de pago: representar mediante nombre e icono; no implica asociación comercial.

## Tipografía, espaciado, estructura

- Fuente del sistema: `system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif`. Conservar la fuente aprobada del proyecto si difiere; confirmar discrepancias antes de sustituirla.
- Base 15 px, etiquetas 13 px y peso 650, texto auxiliar 13 px, títulos H1 28–38 px, H2 22 px, H3 16 px. Precios y horarios con números tabulares y peso 750.
- Espaciado base: 4/8/12/16/24/32/40/64 px. Controles 46 px mínimos; botones 44 px mínimos. Bordes de 1 px; radio 8 px en controles y 12 px en superficies (16–20 px para hero/saldo). Sombra tenue `0 8px 28px #32104b09`.
- Contenedor comercial máximo 1240 px con padding horizontal 32 px; registro 850 px; login 540 px. La grilla usa `minmax(0,1fr)` para prevenir desbordes. Panel operativo con sidebar 220 px y contenido flexible.
- Escritorio 1440 × 1000, tableta 768 × 1024 y móvil 390 × 844 como viewports de referencia. Hasta 760 px: panel administrativo pasa a navegación compacta, las columnas se apilan. Hasta 460 px: formulario de una columna (excepto pequeños bloques explícitos), CTA principal ancho completo cuando corresponda. Nunca permitir scroll horizontal de todo el documento; una tabla operativa puede tener scroll interno en móvil. En escritorio deben verse acciones y datos completos.
- La cabecera de producto no debe ocultarse al desplazarse o provocar saltos al cambiar la autenticación. El footer de referencia y los enlaces para cambiar de escenario **no se copian al producto**.

## Componentes y variantes

| Componente | Especificación |
|---|---|
| Button | Principal púrpura, secundario borde púrpura, terciario suave/texto, destructivo borde rojo; deshabilitado no es acción válida. Un CTA dominante por sección. |
| Input / Select | Etiqueta única visible, asociación `htmlFor`, mensaje de error junto al campo, hint separado, sin duplicar wrapper ni label. |
| SearchableCombobox | Un solo control cerrado. Búsqueda dentro del desplegable. Resultados remotos paginados, carga, vacío, error, reintento, foco y teclado. El HTML demuestra filtrado local; no es el contrato de producción. |
| LocationFields | País → división territorial si aplica → ciudad. Reset dependientes; impedir selección inválida; mantener IDs. Etiquetas simples dentro del grupo, no repetir el título. |
| FlightCard | Ruta, hora local, duración, clase, tarifa vigente por persona, precio total cuando proceda, CTA; distinguir oferta sin depender solo del color. Si no existe código IATA autoritativo, mostrar ciudad sin inventarlo. |
| WalletBalance | Saldo disponible en COP; sin valores ficticios por defecto. |
| PaymentMethodCard | Nombre de franquicia o medio, últimos cuatro, vencimiento y disponibilidad. Menú de acciones existentes; preferencia y edición de dirección requieren decisión. |
| MovementRow | Tipo legible, fecha, referencia, signo e importe; nunca mostrar datos sensibles. |
| StatusTag | Texto humano y color secundario; no exponer enum crudo. |
| DataTable | Solo gestión operativa o listados que realmente necesiten columnas. Filtrado, paginación, encabezados, acciones legibles; conservar desplazamiento interno en móvil. |
| Dialog | Confirmación explícita, efecto/importe/destinatario visibles, foco inicial seguro, Escape y retorno de foco; cancelar no muta. |
| Feedback | Loading, error con acción de reintento, estado vacío y éxito persistente; error de red no equivale a operación rechazada. |
| SeatMap | Selección disponible de la misma clase, actual y ocupada distinguibles por texto y estilo; mapa y IDs de API. El fragmento alfabético del mock no cambia el modelo real de sillas. |

## Accesibilidad y calidad visual

Objetivo WCAG 2.2 AA como criterio de diseño, no certificación. Contraste de texto normal ≥4.5:1, texto grande ≥3:1, foco visible, etiquetas programáticas, navegación por teclado, `aria-live` para resultados, errores vinculados al campo, diálogos con retorno de foco, sin depender solo del color. Iconografía de producción con `lucide-react` ya presente. Usar `Intl.NumberFormat('es-CO', { currency: 'COP', style: 'currency' })` y horarios locales de vuelo; preservar instantes UTC en API. No truncar precios, códigos ni acciones. No traducir automáticamente las fechas del servidor usando una zona local incorrecta.

## Reglas de fidelidad

1. Comparar el HTML y PNG del módulo correspondiente antes de editar React.
2. Reutilizar tokens y componentes, no copiar datos ficticios ni duplicar CSS por pantalla.
3. Verificar DOM y API reales, capturar a 1440/768/390 px, corregir diferencias de jerarquía, composición, accesibilidad y estados.
4. Cualquier variación significativa de marca, navegación o regla de negocio debe ser aprobada. Los valores visuales son referencia, no autorización para introducir nuevas funcionalidades.
