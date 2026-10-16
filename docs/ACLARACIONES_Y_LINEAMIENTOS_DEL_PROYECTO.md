# Aclaraciones y lineamientos compartidos del proyecto

**Proyecto:** Sistema de Gestión de Compra y Reserva de Tiquetes Aéreos en Línea  
**Asignatura:** Laboratorio de Software — Universidad Tecnológica de Pereira  
**Versión:** 1.0.1
**Fecha:** 2026-10-16
**Ubicación propuesta:** `docs/ACLARACIONES_Y_LINEAMIENTOS_DEL_PROYECTO.md`  
**Destinatarios:** backend, frontend, integración/despliegue y herramientas de IA del equipo.  
**Estado:** complemento consolidado para revisión e incorporación al repositorio mediante el flujo de trabajo del equipo. No acredita aprobación del profesor ni implementación del código.

**Índice de consulta**

- [1. Propósito y uso](#1-propósito-y-forma-de-uso)
- [2. Fuentes revisadas](#2-fuentes-y-alcance-de-la-revisión)
- [3. Decisiones resueltas](#3-resumen-de-decisiones-resueltas)
- [4. Identificadores y códigos](#4-identificadores-y-códigos)
- [5. Billetera](#5-billetera-y-operaciones-financieras)
- [6. Administración, reprogramaciones y precios](#6-administración-de-vuelos-reprogramaciones-y-precios)
- [7. Reservas, viajeros, cupos y sillas](#7-reservas-viajeros-cupos-y-sillas)
- [8. Transacciones y concurrencia](#8-dec-09--transacciones-concurrencia-e-idempotencia)
- [9. Usuarios y seguridad](#9-usuarios-roles-y-seguridad)
- [10. Fechas y rutas](#10-fechas-rutas-y-reglas-comunes-de-cálculo)
- [11. Arquitectura y contrato](#11-dec-12--arquitectura-y-contrato-de-desarrollo)
- [12. Notificaciones y funciones de apoyo](#12-dec-13--correos-noticias-pdf-y-funciones-de-apoyo)
- [13. Git, coordinación y calidad](#13-dec-14--git-coordinación-y-criterio-de-terminado)
- [14. Pendientes por resolver](#14-decisiones-pendientes-registro-único)
- [15. Matriz de correcciones](#15-matriz-de-correcciones-de-los-artefactos)
- [16. Casos de aceptación](#16-casos-mínimos-de-aceptación-compartidos)
- [17. Instrucciones para IA](#17-instrucciones-reutilizables-para-herramientas-de-ia)
- [18. Mantenimiento del documento](#18-mantenimiento-y-evolución-de-la-base-común)
- [19. Referencias técnicas](#19-referencias-técnicas-de-apoyo)
- [20. Huellas de los adjuntos](#20-huellas-de-los-documentos-base)

## 1. Propósito y forma de uso

Este documento establece una base común para resolver inconsistencias entre el enunciado, la ERS, los diagramas, las historias de usuario, los casos de uso y los mockups. Incluye las aclaraciones discutidas durante la preparación del desarrollo, sus consecuencias técnicas y las decisiones que todavía necesitan una definición compartida.

La documentación original continúa describiendo el alcance completo. Este complemento corrige o precisa únicamente los puntos identificados aquí. No se debe deducir que una funcionalidad desapareció porque no se repite en estas páginas.

Al incorporar esta versión al repositorio, sus reglas resueltas constituyen la línea común de implementación. Las decisiones marcadas **P** no pueden convertirse silenciosamente en reglas distintas en cada rama. Debe resolverse el punto concreto y registrar la respuesta en este archivo; el resto del trabajo puede continuar.

### 1.1. Procedencia de las decisiones

| Marca | Significado | Tratamiento |
|---|---|---|
| **C** | Aclaración expresa del usuario durante la conversación. | Conservarla; no restaurar una interpretación anterior incompatible. |
| **R** | Regla de la documentación o recomendación consolidada durante la conversación. | Adoptarla como base al incorporar este complemento. |
| **T** | Convención técnica o detalle operativo propuesto aquí para evitar implementaciones divergentes. | Aplicarlo de forma uniforme; cualquier cambio se documenta y coordina. |
| **P** | Decisión de negocio, parámetro o dependencia todavía sin acuerdo suficiente. | Resolverla en conjunto antes de completar el comportamiento afectado. |

Las marcas describen procedencia, no niveles de importancia. Este documento no presenta recomendaciones anteriores como si todas hubieran sido aprobadas expresamente por cada integrante.

### 1.2. Precedencia y contradicciones

1. Una aclaración posterior registrada y adoptada por el equipo actualiza la decisión correspondiente de este complemento.
2. Las decisiones resueltas de este complemento prevalecen sobre los fragmentos originales expresamente señalados como inconsistentes.
3. Para lo demás, se utilizan conjuntamente el enunciado y los requisitos vigentes; la ERS aporta el detalle que no contradiga decisiones resueltas.
4. Diagramas, historias, casos de uso y mockups deben representar esas reglas. Una pantalla o una columna del ER no crea por sí sola una regla de negocio nueva.
5. El código existente, las migraciones y OpenAPI muestran lo implementado. Una diferencia entre código y requisitos debe registrarse; no se considera automáticamente un nuevo requisito.
6. Si aparece un conflicto no resuelto, registrar fuentes, alcance afectado y propuesta. No escoger una interpretación privada ni copiar automáticamente la solución sugerida por otra IA.

Las ampliaciones frente al enunciado se identifican expresamente. La incorporación al repositorio permite al equipo mantener una base común, pero no sustituye una validación académica cuando corresponda.

### 1.3. Lectura obligatoria para cada tarea asistida por IA

- Leer este archivo completo y comprobar su versión.
- Leer `README.md`, `REGLASCOMMITS.md` y los `AGENTS.md` aplicables.
- Leer los requisitos, historia y caso de uso de la tarea, junto con los modelos afectados.
- Inspeccionar el código, las migraciones, las pruebas y el contrato de API existentes antes de proponer cambios.
- Identificar las decisiones pendientes que afecten la tarea.
- Indicar en el PR los identificadores de HU, RF/RNF y decisiones de este complemento que se implementan.

El historial de un chat individual no sustituye los acuerdos versionados del repositorio.

## 2. Fuentes y alcance de la revisión

| Referencia | Documento revisado | Función |
|---|---|---|
| S1 | `Proyecto_Lab_Soft_2026-02.pdf` | Enunciado específico del sistema de tiquetes. |
| S2 | `ERS(1).pdf` | Requisitos funcionales, reglas de negocio y atributos de calidad. |
| S3 | `Diagramas de Clases.pdf` | Modelo de dominio por módulos. |
| S4 | `er.pdf` | Propuesta de modelo de datos. |
| S5 | `Historias_Usuario_Sistema_Tiquetes_Aereos.pdf` | Historias HU-001 a HU-021 y criterios de aceptación. |
| S6 | `Acta_Casos_de_Uso_Tiquetes_Aereos.docx` | Casos de uso, precondiciones y flujos alternos. |
| S7 | `Mockups · Sistema de Tiquetes Aéreos.html` | Referencia de vistas y navegación; el nombre puede variar por codificación del acento. |
| S8 | `REGLASCOMMITS.md` | Ramas, commits y pull requests. |
| S9 | `is714-laboratorio-de-software(1).pdf` | Programa general de la asignatura; no reemplaza S1. |
| S10 | Conversación de definición de stack y aclaraciones del 11 de octubre de 2026 | Decisiones y recomendaciones consolidadas en este complemento. |

La revisión parte de los adjuntos compartidos. La captura `image.png` únicamente muestra carpetas del repositorio; no permite afirmar qué código existe. No se inspeccionó el clon local de VS Code ni una rama remota del proyecto para elaborar este documento.

## 3. Resumen de decisiones resueltas

| ID | Marca | Decisión |
|---|---|---|
| DEC-01 | C/R | Código de vuelo alfanumérico: prefijo de aerolínea y consecutivo, separado del ID interno. |
| DEC-02 | R | Localizador único compartido por compra; cada tiquete conserva su ID individual. |
| DEC-03 | C/R | Billetera separada de movimientos y sin `creada_en`; nace junto con la cuenta. |
| DEC-04 | R | Claves primarias internas enteras autogeneradas mediante `BigAutoField`. |
| DEC-05 | C | Administradores pueden reprogramar y cambiar tarifa base aunque existan ventas. |
| DEC-06 | C/R | Distinguir tarifa base, promoción temporal y precio efectivamente pagado. |
| DEC-07 | R | Reservas vencen al primero de sus límites; la reprogramación no reinicia sus 24 horas. |
| DEC-08 | R/T | Reserva retiene cupos; asignación inicial de silla al confirmar la compra. |
| DEC-09 | R/T | Compras, cancelaciones y billetera se resuelven con transacciones y protección contra duplicados. |
| DEC-10 | R | Usuario personalizado, roles explícitos y propiedad de recursos comprobada en backend. |
| DEC-11 | R | Sesiones compartidas en base de datos, verificación de correo y controles de seguridad de la ERS. |
| DEC-12 | R/T | Monolito modular Django/DRF/PostgreSQL, contrato de API común y entorno reproducible. |
| DEC-13 | R | Notificaciones persistentes con reintentos; correo y PDF no revierten una compra confirmada. |
| DEC-14 | R/T | Un PR por HU, trazabilidad, revisión por otra persona y pruebas de reglas reales. |
| DEC-15 | C/R | P-02: root inicia sesión con ID y contraseña, sin correo ni datos personales obligatorios; clientes y administradores usan correo único sin distinguir mayúsculas. El rol de negocio no concede privilegios de Django. |

## 4. Identificadores y códigos

### 4.1. DEC-01 — Código de vuelo

**Problema:** el ER no incluye un campo explícito para el código de vuelo. La primera recomendación de mostrar un entero fue corregida para utilizar una representación comercial alfanumérica.

**Regla:** el código visible combina un prefijo de aerolínea de dos caracteres con un consecutivo de cuatro dígitos: `XX0001`, `XX0002`, etc. `XX` es un valor de demostración configurable y no una afirmación de asignación oficial IATA.

| Elemento | Tipo conceptual | Ejemplo | Uso |
|---|---|---|---|
| `id_vuelo` | Entero de 64 bits autogenerado | `42` | PK y relaciones internas. |
| Consecutivo de emisión | Entero entre 1 y 9999 | `123` | Generación del código; contador común en base de datos. |
| `codigo_vuelo` | Cadena de seis caracteres, única | `XX0123` | Búsqueda, interfaces, correos y pasabordos. |

- El servidor genera el código y lo conserva inmutable. El cliente HTTP no puede elegirlo ni modificarlo.
- El prefijo se configura para el proyecto. Los designadores reales no siempre son dos letras; también existen combinaciones de letra y número.
- El código completo queda almacenado: cambiar una configuración no modifica códigos emitidos.
- La generación se hace con un contador preexistente en base de datos, bloqueado e incrementado en la misma transacción que crea el vuelo. Puede emplearse una entidad pequeña de secuencias; no usar contadores en memoria ni `COUNT + 1` o `MAX + 1` sin control de concurrencia.
- Los vuelos cancelados conservan su código; no se borran para reutilizar números.
- No se reinicia el contador por fecha ni se genera `XX10000`. Agotar 9999 números produce un error controlado y exige revisar la convención antes de continuar.
- Para esta versión, el código es único por registro de vuelo, tal como establece la ERS. En sistemas reales, el número comercial puede repetirse en distintas fechas y la identificación de una operación incorpora más datos. Aquí se documenta esa simplificación; no implementar unilateralmente reutilización diaria.

**Ajustes:** S4, entidad `vuelo`; S3, clase `Vuelo`; RF-ADM-02, HU-001/CU-01; contratos y ejemplos del frontend.

**Verificación:** dos altas concurrentes obtienen códigos distintos y consecutivos; un alta revertida no deja un vuelo parcial; editar o cancelar conserva el código; el formato y el límite se validan.

### 4.2. DEC-02 — Localizador compartido e identificación de tiquetes

**Problema:** RF-COM-18/19 y algunas clases describen un código por tiquete; el ER usa `compra.localizador` y el check-in grupal necesita varios tiquetes bajo un mismo código.

**Regla:** generar un localizador alfanumérico de seis caracteres por compra confirmada y enviarlo a cada viajero incluido. El localizador agrupa los tiquetes de esa compra. Cada tiquete conserva una PK diferente.

| Identificador | Significado |
|---|---|
| `id_reserva` | Apartado temporal pendiente de pago. |
| `id_compra` | Operación interna de compra. |
| `compra.localizador` | Código comercial compartido para consultar y gestionar los tiquetes comprados. |
| `id_tiquete` | Participación de un viajero en un vuelo específico. |

Una compra de ida y regreso para dos viajeros contiene cuatro tiquetes, un localizador, dos vuelos y dos viajeros. El límite de cinco se comprueba **por cliente y vuelo**, no sobre la cantidad total de filas de una compra de ida y regreso.

- Generar el localizador al confirmar la compra, incluso cuando procede de una reserva temporal.
- Usar generación aleatoria segura, normalización a mayúsculas, unicidad en la base de datos y reintento controlado ante colisión.
- Conservar el localizador aunque se cancele la compra; filtrar los tiquetes habilitados para cada operación.
- Los estados, la silla, el cambio de silla y el check-in pertenecen al tiquete. Una consulta por localizador no confirma automáticamente todos los check-ins.
- Para operaciones grupales, verificar permisos y condiciones de cada tiquete y vuelo. El regreso puede tener una ventana de check-in distinta.
- El código no autoriza por sí solo retiros, reembolsos ni consulta de datos financieros. Ver P-03 para la verificación del viajero en check-in rápido.
- `id_tiquete` no equivale al número comercial de un e-ticket real de 13 dígitos. La emisión conforme a ese estándar no fue acordada como requisito; no inventar prefijos oficiales ni sustituir el ID interno por un supuesto número certificado.

**Corrección textual a aplicar:** donde RF-COM-18/19 y los flujos de compra dicen «código de reserva de cada tiquete», interpretar «localizador de la compra, asociado a sus tiquetes y enviado a cada viajero».

**Ajustes:** RF-COM-18/19, RF-CHK-01/11, sección 3.5 de S2; HU-013/015/016; CU-13/16; clases `Compra` y `Tiquete`. Mantener `compra.localizador` del ER. La vista de confirmación muestra un localizador y el detalle individual de los tiquetes.

### 4.3. DEC-04 — Claves primarias internas

Usar `BigAutoField` para las entidades persistentes que necesiten una PK artificial: usuarios, vuelos, reservas, compras, viajeros, tiquetes, billeteras, movimientos y demás entidades del dominio.

- Actualizar los UUID del diagrama de clases y los tipos de claves correspondientes del ER para mantener consistencia.
- Las claves foráneas deben usar el tipo de la PK referenciada.
- Claves naturales de catálogos o configuraciones pueden conservar su función cuando esté explícitamente justificada.
- Las combinaciones de negocio se protegen con restricciones únicas, aunque exista una PK artificial.
- El correo y el documento no se utilizan como PK. El correo identifica una cuenta; la PK permite mantener las relaciones sin depender de datos de perfil.
- Conocer una PK o un localizador nunca reemplaza la comprobación de autorización.

Si el repositorio ya contiene migraciones o datos compartidos, revisar primero su estado. No borrar migraciones aplicadas ni recrear bases de datos compartidas para imponer esta convención.

## 5. Billetera y operaciones financieras

### 5.1. DEC-03 — Modelo mínimo

La tabla llamada `billetera` en S4 contiene atributos de movimientos. Debe distinguirse la cuenta de saldo de su historial.

| Entidad | Campos y reglas mínimas |
|---|---|
| `billetera` | `id_billetera`; `id_usuario` obligatorio y único; `saldo` decimal, inicialmente cero. |
| `movimiento_billetera` | `id_movimiento`; `id_billetera`; `tipo`; `valor`; `saldo_resultante`; referencias a medio de pago y operación según corresponda; `creado_en`. |

**Aclaración expresa:** la billetera no lleva `creada_en`. Se crea simultáneamente con el usuario, dentro de una misma transacción, y su fecha de origen se obtiene de `usuario.creado_en`. Esta decisión supone una billetera por cuenta durante todo su ciclo de vida; no se recrea al cerrar sesión ni al cambiar el perfil.

La ERS asocia el espacio financiero a cada usuario registrado. Eso no habilita a root ni a administradores para reservar o comprar. Los movimientos sí tienen fecha propia.

### 5.2. Saldo y trazabilidad

- Usar `Decimal` en Python y campos decimales en PostgreSQL. Referencia común: `DecimalField(max_digits=14, decimal_places=2)` para saldo y movimientos.
- El saldo almacenado facilita la consulta y debe ser reconstruible a partir del historial.
- `valor` es positivo; el tipo determina el signo: depósito/reembolso suman, compra/retiro restan.
- `saldo_resultante` registra el saldo después del movimiento y no sustituye el saldo actual de la billetera.
- Aplicar restricciones de saldo no negativo y valor de movimiento mayor que cero.
- Los movimientos confirmados se conservan. Una corrección financiera requiere una operación compensatoria trazable, no editar el historial para ocultar el cambio.
- Rechazar compras o retiros sin fondos, sin dejar cambios parciales.
- El reembolso vuelve a la billetera del **cliente que pagó**, aunque los viajeros sean otras personas.
- Cancelar una reserva sin pago no genera un reembolso ficticio. Solo se devuelve dinero previamente debitado y todavía no reembolsado.
- La prevención de duplicados debe identificar la operación concreta. No imponer una unicidad global «compra + tipo REEMBOLSO» que impida varios reembolsos legítimos de tiquetes diferentes de una misma compra.

### 5.3. Alcance financiero y referencias incorrectas

S2, secciones 2.4 y 2.6, excluye pasarelas y entidades financieras reales. Los depósitos y retiros de esta versión se representan mediante el módulo interno. No introducir una integración bancaria real como dependencia obligatoria de la HU-010 o HU-011.

En desarrollo y demostraciones, utilizar datos de prueba. Los medios se presentan enmascarados y no se conserva CVV. La tokenización interna de datos de prueba no debe describirse como tokenización certificada de una pasarela real.

RF-COM-13 remite a RF-GFI-05, pero RF-GFI-05 describe **depósitos**, no el débito por compra. Para el débito, relacionar RF-COM-13 con RF-GFI-03/04/07 y con DEC-09. Corregir esa referencia sin renumerar los requisitos existentes.

Los límites de depósito/retiro y el detalle del segundo factor deben fijarse de manera común según P-05. La moneda única se configura para todo el sistema; se propone COP para la demostración colombiana, sin conversiones ni multimoneda.

## 6. Administración de vuelos, reprogramaciones y precios

### 6.1. DEC-05 — Edición con reservas y ventas

**Aclaración expresa:** el administrador puede modificar fecha, hora y tarifa base de un vuelo pendiente de operación aunque existan reservas, compras o check-ins.

Se descarta la recomendación anterior de bloquear cualquier edición por tener tiquetes vendidos. El enunciado original incluye esa restricción; esta decisión constituye una ampliación aclarada durante la conversación. Debe reflejarse en los artefactos derivados y dejarse registrada como diferencia frente a S1.

| Acción | Tratamiento común |
|---|---|
| Cambiar fecha/hora | Recalcular llegada, revisar plazos y notificar a los afectados. |
| Cambiar precio base | Cambiar la tarifa para futuras confirmaciones de compra; conservar precios pagados. |
| Crear promoción | Aplicar el precio temporal a los cupos y operaciones elegibles. |
| Cancelar vuelo | Conservar el registro y resolver las afectaciones mediante reembolso o reubicación. |

Código, origen, destino y tipo de vuelo conservan la inmutabilidad definida en la ERS. Una modificación de ruta se gestiona mediante cancelación/reubicación, no alterando silenciosamente la ruta de tiquetes vendidos.

### 6.2. Efectos de una reprogramación

- Conservar la identidad del vuelo, el localizador y el precio pagado de los tiquetes confirmados.
- Registrar usuario responsable, motivo, instante y valores anteriores/nuevos en bitácora.
- Recalcular llegada con la duración de la ruta y las zonas horarias.
- Recalcular límites de reservas, cancelación y habilitación del check-in según la nueva salida.
- No reiniciar el plazo de 24 horas desde la creación de una reserva.
- Evaluar todos los trayectos afectados: un cambio no puede dejar sin advertencia un regreso anterior a la ida o a su llegada. La solución se registra mediante el flujo de afectaciones, reubicación o reembolso definido; no corregir silenciosamente el otro vuelo.
- Avisar al cliente comprador y a los viajeros afectados; registrar los envíos para reintento.
- Actualizar o reemitir pasabordos afectados. El tratamiento de un check-in ya confirmado ante una reprogramación requiere P-01.
- Resolver el cambio y sus efectos persistentes de manera transaccional. Los envíos externos se procesan después.

### 6.3. DEC-06 — Precio base, promoción y precio pagado

| Concepto | Regla |
|---|---|
| Precio base | Tarifa regular vigente, editable por el administrador. |
| Promoción | Descuento temporal con vigencia y condiciones. |
| Precio cotizado | Valor mostrado antes de confirmar; puede perder vigencia. |
| `precio_pagado` | Valor efectivo de un tiquete confirmado, conservado para historial y reembolso. |

Una compra por COP 400.000 conserva ese valor aunque el precio base suba después a COP 450.000. No se cobra la diferencia retroactivamente ni se altera el historial. El reembolso se calcula sobre el pago correspondiente al tiquete afectado, no sobre la tarifa actual.

El total se calcula en backend. Si el valor vigente difiere del último total aceptado por el cliente, devolver el nuevo total y exigir una nueva confirmación antes del débito. No confiar en precios, descuentos o totales enviados por el navegador.

Para reservas pendientes de pago, la base consolidada es **recalcular al confirmar la compra**; retener un cupo no congela automáticamente el precio. El usuario debe ver y aceptar cualquier diferencia.

En S5, HU-004 exige que el valor promocional sea positivo e inferior al precio regular. Un incremento temporal sería un ajuste temporal de tarifa; no ampliar silenciosamente «promoción» para incluir recargos. Si el equipo decide soportarlos, debe actualizar alcance, modelo y reglas de ese módulo.

Al cambiar la tarifa base, revisar promociones activas. Desactivar para futuras operaciones aquellas que dejen de representar un descuento y registrar la causa. Las compras ya confirmadas no se recalculan.

**Pendiente P-04:** concretar el significado de `cupos_afectados`, la elegibilidad de reservas anteriores a una promoción y la política de promociones superpuestas. Hasta resolverlo, no implementar algoritmos distintos de selección de promociones.

El ER almacena precios por clase (`vuelo_clase`). No se ha definido un multiplicador para primera clase: ninguna IA debe inventar porcentajes. Ver P-04 para el contrato de entrada de esas tarifas.

### 6.4. Estado real del vuelo y venta

No confundir «hora programada alcanzada» con «operación efectivamente realizada». RF-ADM-13 y parte de RNF-DIS-02 usan el paso de la hora de salida para marcar `REALIZADO`, lo que puede impedir reprogramar retrasos.

El mecanismo definitivo de transición está en **P-01**. Se mantiene la exigencia de conservar vuelos realizados/cancelados y excluirlos de nuevas operaciones, pero no se implementa una transición automática incompatible con la administración de retrasos sin cerrar esa decisión.

Independientemente del nombre del estado, búsqueda, reserva y compra deben comprobar la salida vigente y los límites temporales. Un registro desactualizado como `PROGRAMADO` no autoriza vender una salida que ya quedó en el pasado.

### 6.5. Cancelación y reubicación

- HU-003 exige resolver cada tiquete vendido mediante reembolso o reubicación y registrar la alternativa aplicada. Si no hay vuelos alternativos con cupos suficientes, corresponde el reembolso.
- El destinatario del reembolso es el comprador que realizó el débito. La referencia de algunos textos a «billetera del pasajero» no exige crear una cuenta a un viajero sin registro.
- La reubicación comprueba capacidad, clase, identidad del viajero y coherencia de los trayectos en el vuelo de destino. Conserva una relación trazable entre tiquete original y sustituto; no puede producir simultáneamente un reembolso completo y un tiquete sustituto activo por el mismo pago.
- No inventar cobros adicionales, reglas de consentimiento ni criterios de selección del vuelo alternativo. Acordar ese flujo y el tratamiento del pasabordo junto con P-01 antes de completar la reubicación. Esto no impide implementar el reembolso previsto.
- Cancelar el vuelo libera también las reservas sin pago afectadas; estas no reciben abonos. El vuelo y las operaciones originales se conservan como historial.
- HU-003 exige revertir la cancelación si falla un abono obligatorio. La falla posterior de un correo se recupera mediante reintento y no revierte los movimientos confirmados.

## 7. Reservas, viajeros, cupos y sillas

### 7.1. DEC-07 — Vigencia y fronteras temporales

La ERS establece:

```text
margen_reserva = 1 hora para nacional; 3 horas para internacional
limite_por_salida = salida_vigente - margen_reserva
vence_en = min(creada_en + 24 horas, limite_por_salida)
vigente si: estado == VIGENTE y ahora < vence_en
```

- Al alcanzar el límite (`ahora >= vence_en`), esa reserva ya no puede convertirse en compra.
- Crear una nueva reserva exige `ahora < limite_por_salida`, disponibilidad y las demás validaciones. Su vencimiento se calcula nuevamente con la fórmula; no equivale a revivir o extender la reserva anterior.
- En ida y regreso, aplicar el límite más temprano de todos los vuelos incluidos; no dejar una reserva parcialmente vigente sin una regla explícita de división.
- La reprogramación recalcula el límite por salida, conservando `creada_en + 24 horas` como máximo. No revivir reservas ya vencidas, compradas o canceladas.
- Si el nuevo límite ya se alcanzó, vencer y liberar la reserva afectada de forma transaccional.
- La tarea automática debe liberar dentro del minuto siguiente al vencimiento, conforme al objetivo RNF-REN-05. Los endpoints verifican siempre el tiempo real, aunque la tarea todavía no haya corrido.
- Para reservas vencidas detectadas durante una consulta o compra, la recuperación de cupos debe pasar por el mismo servicio idempotente de liberación.

Para cancelación voluntaria de compras se conserva la base de S2: una hora antes en nacionales y tres horas antes en internacionales. En el instante límite se rechaza la cancelación. S1 solo menciona una hora y no distingue tipos; documentar esta diferencia y no mezclar ambos criterios entre frontend y backend. Los cambios operacionales del administrador se tratan separadamente de la cancelación voluntaria del cliente.

RF-COM-24 permite compra directa cuando ya no se admite reserva temporal. Esto no autoriza comprar vuelos cancelados, realizados, sin cupos o con salida alcanzada.

### 7.2. Reglas de viajeros

- Cliente comprador y viajero son conceptos diferentes. El comprador puede viajar o comprar para otras personas.
- Un cliente no puede superar cinco tiquetes activos para el mismo vuelo, sumando reservas vigentes y compras confirmadas, incluso si realizó varias operaciones separadas.
- Un mismo viajero no puede tener dos participaciones activas en el mismo vuelo. La comprobación se basa en la identidad documental normalizada, no solo en el ID de una fila `viajero`.
- El documento puede repetirse entre **cuentas de usuario**, según RN-19. Esa regla no permite duplicar un viajero activo en un vuelo.
- Cada grupo de viajeros de una operación por vuelo debe incluir al menos un mayor de edad; calcular la edad en la fecha de salida local del vuelo. Un adulto que solo participa en otro vuelo no satisface la condición.
- En este proyecto se utiliza mayoría de edad de 18 años como convención común. Mantener la validación en un único servicio.
- Exigir los datos de identidad, contacto y contacto de emergencia especificados por la ERS para cada viajero.
- No exponer datos de otro viajero únicamente porque se conoce un documento. Aplicar propiedad/autorización en cada consulta.

### 7.3. DEC-08 — Retención de cupos y asignación de sillas

El enunciado asigna la silla inicialmente al comprar. Para resolver el uso ambiguo de «confirmar la operación» en RF-COM-10/RN-14, adoptar esta secuencia:

1. El carrito contiene selecciones y cotizaciones; no bloquea cupos ni sillas.
2. Una reserva confirmada retiene cupos de la clase, pero no asigna una silla numerada.
3. Una compra directa consume cupos disponibles y asigna sillas aleatorias dentro de la clase.
4. Comprar una reserva vigente convierte sus cupos retenidos en vendidos y asigna sillas; no vuelve a descontar los mismos cupos.
5. Cancelación o vencimiento libera exactamente la ocupación que existía, una sola vez.

| Tipo de vuelo | Capacidad | Primera clase | Económica |
|---|---:|---|---|
| Nacional | 150 | Números 1–25: 25 sillas | Números 26–150: 125 sillas |
| Internacional | 250 | Números 1–50: 50 sillas | Números 51–250: 200 sillas |

El número de silla del negocio es único dentro del vuelo. Una etiqueta gráfica como `15A` debe mapearse explícitamente al número y a la clase; el mockup no cambia la distribución exigida. En particular, un dibujo con cuatro filas de seis asientos no equivale a las 25 sillas de primera clase nacionales.

Las reservas retienen una cantidad, no sillas específicas. El mapa debe mostrar los cupos retenidos como información agregada y no inventar qué asiento numerado está «reservado». Ajustar RF-CHK-04 y el mockup para reflejar esta decisión.

Para cada vuelo y clase, debe cumplirse:

```text
cupos_disponibles = cupos_total - cupos_reservados_vigentes - cupos_comprados_activos
```

Si `cupos_disponibles` se almacena, es un dato derivado que se actualiza únicamente mediante los servicios transaccionales. No dejar que distintos módulos editen el contador con reglas independientes.

En PostgreSQL, proteger las asignaciones activas con restricciones de unicidad por vuelo/silla y vuelo/identidad del viajero. Los registros históricos cancelados o liberados no deben impedir nuevas asignaciones legítimas. Los campos `silla_activa` y `viajero_activo` del ER se traducen a una estrategia explícita de restricciones condicionadas o equivalente; no copiar sintaxis de otro motor sin revisar su semántica.

La protección de identidad debe cubrir conjuntamente reservas y compras. Dos restricciones aisladas en tablas distintas no impiden que la misma persona esté activa en ambas. Usar una representación común de ocupación o una validación compartida bajo el bloqueo del vuelo, y documentar la solución en el modelo. Comparar el tipo y número documental normalizados; conservar el número como texto, incluidos sus ceros iniciales, y centralizar la normalización. Una restricción sobre `id_viajero` solo basta si ese ID representa de forma única esa identidad; no suponerlo por existir una clave foránea.

### 7.4. Check-in y cambio de silla

- Se habilita desde 24 horas antes de la salida vigente y antes de la salida; se comprueba que el tiquete esté comprado y activo.
- Cada tiquete permite un único cambio voluntario de silla antes de confirmar check-in, dentro de su clase y hacia una silla disponible.
- La asignación aleatoria inicial no consume ese cambio. Confirmar la misma silla no se registra como cambio.
- Tras confirmar check-in no se permite el cambio voluntario de silla.
- Los cambios impuestos por reubicación no deben confundirse con el cambio voluntario; el nuevo tiquete y su relación con el original deben quedar trazados.
- Generar un pasabordo por viajero y vuelo, y registrar el envío o la necesidad de reintento.
- El check-in grupal valida cada tiquete. Si una selección contiene tiquetes no habilitados, informar el motivo y pedir una selección válida, sin confirmar parcialmente y en silencio la selección original.
- El acceso rápido sin cuenta es una excepción funcional al enunciado general de RNF-SEG-01. Su mecanismo de verificación está en P-03; no tratar el documento o localizador como autorización universal.

## 8. DEC-09 — Transacciones, concurrencia e idempotencia

Una compra debe validar y confirmar de forma coordinada: estado/tiempo de vuelos, identidad y edad de viajeros, límite por cliente, cupos, precio aceptado, saldo, conversión de reserva si existe, creación de tiquetes, asignación de sillas, movimiento financiero, localizador y eventos de auditoría/notificación.

- Utilizar `transaction.atomic()` y bloqueo de las filas necesarias mediante `select_for_update()` o un mecanismo equivalente probado.
- Una transacción, por sí sola, no sustituye el bloqueo o las restricciones contra carreras concurrentes.
- Usar PostgreSQL en pruebas de integración y concurrencia; SQLite no reproduce los bloqueos de filas utilizados.
- Definir un orden común de bloqueo. Propuesta para estos servicios: vuelos ordenados por ID, inventarios de sus clases, billeteras ordenadas por ID y registros de reserva/compra/tiquete necesarios. Las operaciones que usan un subconjunto respetan el mismo orden.
- Cancelación de un vuelo: bloquear el vuelo antes de enumerar definitivamente las ventas afectadas; después, las billeteras implicadas en orden. Si hay reubicaciones, bloquear el conjunto de vuelos de origen y destino respetando el orden global por ID. Una venta concurrente no puede quedar fuera del tratamiento por una lectura previa sin bloqueo.
- Mantener las transacciones breves y evitar llamadas SMTP, generación pesada de PDF o servicios externos mientras se retienen bloqueos.
- Si falla la persistencia de un cargo o reembolso obligatorio, revertir la operación de negocio que depende de él.
- Si falla posteriormente un correo, conservar la operación confirmada y reintentar el envío.

**Idempotencia:** repetir la misma solicitud por doble clic o reintento de red no puede duplicar una compra, débito, retiro, reembolso, liberación o check-in. Adoptar una clave de operación asociada al actor y al tipo de acción, guardar su resultado de manera consistente y rechazar reutilización con un contenido diferente. Operaciones legítimas distintas deben poder usar claves diferentes.

No resolver la idempotencia exclusivamente deshabilitando un botón. Las tareas automáticas también deben ser seguras al repetirse o ejecutarse desde más de una instancia.

Una reserva conserva su historia al convertirse en compra; una cancelación conserva compra y tiquetes originales. La relación entre reserva y compra debe ser trazable mediante una referencia de origen explícita o una relación equivalente documentada. No eliminar y recrear operaciones para simular una transición.

## 9. Usuarios, roles y seguridad

### 9.1. DEC-10 — Usuario personalizado y autorización

- Definir `AUTH_USER_MODEL` al inicio y crear el usuario personalizado en la primera migración de su aplicación. Si ya existen migraciones compartidas, planear la adaptación antes de cambiarlo.
- Correo único para las cuentas que lo utilizan, con una política común de normalización. Se propone comparación sin distinción de mayúsculas para el identificador de acceso del proyecto.
- Documento de usuario no único: RN-19 permite varias cuentas con el mismo documento.
- Roles de negocio: `ROOT`, `ADMINISTRADOR`, `CLIENTE`; visitante es la condición no autenticada, no una cuenta creada en la base de datos.
- Separar el rol `ROOT` de `is_superuser` e `is_staff` de Django. Ninguno de estos indicadores puede hacer que root compre o que cualquier administrador cree otros administradores.
- P-02 quedó resuelta el 16 de octubre de 2026: root inicia con ID y contraseña, puede omitir correo y datos personales, y no obtiene automáticamente `is_staff` ni `is_superuser` por su rol; los privilegios técnicos se administran por separado. Clientes y administradores acceden con correo obligatorio y único sin distinguir mayúsculas; sus datos personales se exigen según los requisitos de su historia.
- Crear usuario y billetera conjuntamente. En registro público, el servidor fija el rol `CLIENTE` e impide que el cuerpo HTTP eleve privilegios.

| Operación | Autorización de negocio |
|---|---|
| Crear administradores | Solo root. |
| Gestionar vuelos/promociones | Administrador. |
| Reservar/comprar | Cliente autenticado y con correo verificado. |
| Ver historial, billetera y medios | Titular autorizado; comprobar propiedad. |
| Búsqueda y catálogo públicos | Visitante o usuario; conservar restricciones de acciones por rol. |
| Recomendaciones personales | Cliente autenticado. |
| Mensajería | Usuario registrado; clientes consultan sus conversaciones y administradores atienden las permitidas. |
| Check-in rápido | Excepción sin cuenta, con verificación de viajero según P-03. |

Filtrar consultas y verificar propiedad en cada endpoint. Un UUID, entero, código o filtro del frontend no es un control de acceso.

### 9.2. DEC-11 — Autenticación, sesiones y contraseñas

Para frontend y API bajo el mismo dominio, la recomendación consolidada es `SessionAuthentication` de DRF con sesiones de Django almacenadas en PostgreSQL, cookie de sesión `HttpOnly`, `Secure` en producción y protección CSRF en operaciones que modifican datos, incluido el login.

Las sesiones persistidas permiten compartir el estado entre instancias: el requisito de no depender de sesión en memoria local no obliga a usar JWT. No mezclar sesiones y JWT en módulos diferentes sin una decisión común. En desarrollo, coordinar proxy de Vite u orígenes permitidos y el envío de cookies/CSRF.

- Implementar y probar cierre tras 30 minutos de inactividad; una duración absoluta de token no equivale por sí sola a ese comportamiento.
- Revocar sesión al cerrar sesión. Definir qué actividad prolonga la sesión; se propone actividad autenticada del usuario y excluir sondeos automáticos de fondo.
- Configurar Argon2id mediante los mecanismos de Django; no implementar hashing propio ni almacenar contraseñas reversibles.
- Aplicar la política de la ERS: mínimo 12 caracteres, control de contraseñas comprometidas y ausencia de expiración periódica obligatoria. Esa cifra se cita como requisito del proyecto; no demuestra por sí sola conformidad con una edición vigente de NIST.
- Verificación de correo de un solo uso, con vigencia máxima de 24 horas. Una cuenta sin verificar puede iniciar sesión, pero no reservar, comprar ni operar su billetera.
- Recuperación de contraseña mediante enlace de un solo uso y vigencia limitada.
- Limitar intentos por cuenta y origen y aplicar bloqueo temporal; concretar parámetros comunes en P-05.
- Exigir segundo factor en retiros; la alternativa escogida se fija en P-05.
- Validar tamaño y formato de imágenes de perfil; no aceptar ejecutables ni exponer rutas internas.
- Mantener secretos fuera del repositorio y datos personales/credenciales fuera de logs y mensajes de error.

### 9.3. Requisitos de despliegue y evidencia

La ERS incluye TLS 1.2 o superior, HSTS, cifrado en reposo, control de acceso, política de datos, copias y verificaciones de seguridad. Cada exigencia necesita responsable y evidencia. Usar Django, Docker o AWS no permite afirmar automáticamente cumplimiento de PCI DSS, ASVS, WCAG o una norma legal.

Para cifrado en reposo, describir qué cubre la infraestructura (discos, base y backups) y qué campos requieren tratamiento adicional. Un campo llamado `numero_token` o una contraseña hasheada no demuestra cifrado de toda la información personal.

## 10. Fechas, rutas y reglas comunes de cálculo

- Guardar instantes con zona horaria y operar internamente en UTC.
- Mantener una zona horaria IANA por ciudad; convertir la salida ingresada en hora local del origen y mostrar la llegada en hora local del destino.
- Calcular duración desde el catálogo de rutas y llegada desde salida + duración. No pedir al administrador que duplique cálculos que el sistema debe realizar.
- No fijar diferencias horarias constantes para ciudades sujetas a horario de verano. Una entrada local ambigua o inexistente debe resolverse o rechazarse claramente.
- Búsqueda por fecha se interpreta según la fecha local de salida en el origen.
- Edad se calcula según la fecha local del vuelo, no dividiendo días entre 365.
- Usar un mismo reloj lógico de referencia por operación y un mecanismo de tiempo controlable en pruebas.
- Mantener los límites en servicios compartidos; el frontend los muestra, pero no los impone como única validación.

Rutas nacionales: catálogo acordado de capitales principales; el listado y las duraciones se versionan como datos de referencia. No deducir tiempos de vuelo de la distancia geográfica ni inventarlos en producción.

Rutas internacionales: orígenes Pereira, Bogotá, Medellín, Cali y Cartagena; destinos Madrid, Londres, Nueva York, Buenos Aires y Miami; vuelos directos. La admisión de trayectos internacionales de regreso entra en conflicto con la restricción direccional: ver P-06. No introducir rutas inversas como si ya estuvieran autorizadas.

## 11. DEC-12 — Arquitectura y contrato de desarrollo

### 11.1. Stack común

| Capa | Base consolidada |
|---|---|
| Backend | Python + Django + Django REST Framework. |
| Arquitectura | Monolito modular, base transaccional común. |
| Persistencia | PostgreSQL. |
| Frontend | React + TypeScript + Vite; Material UI como biblioteca propuesta. |
| API | OpenAPI generado con drf-spectacular y documentación navegable. |
| Pruebas backend | pytest, pytest-django y cobertura. |
| Entorno | Docker Compose. |
| Integración | GitHub Actions. |
| Despliegue inicial | AWS EC2, Nginx y Gunicorn; PostgreSQL con persistencia, o RDS si integración lo acuerda. |
| Comunicación/documentos | SMTP y generación de PDF; ReportLab como herramienta propuesta. |

Django 5.2 LTS fue la versión sugerida cuando no existía una versión fijada. El repositorio debe declarar la versión concreta de Python, Django, DRF, PostgreSQL y demás dependencias compatibles. No elegir una versión nueva en cada máquina ni sobrescribir una decisión vigente del repositorio sin revisar su impacto.

### 11.2. Organización y propiedad del código

Organizar aplicaciones por dominio: usuarios, vuelos/promociones, reservas/compras, billetera, check-in y comunicación/recomendaciones. La ubicación exacta se ajusta a lo ya existente en el repositorio, manteniendo límites claros.

| Componente | Responsabilidad |
|---|---|
| Modelos | Persistencia, relaciones y restricciones. |
| Serializers | Contratos de entrada/salida y validación de representación. |
| Servicios | Casos de uso, reglas y transacciones. |
| Vistas | Adaptación HTTP, autenticación/permisos y llamada a servicios. |
| Permisos | Roles, propiedad y capacidades. |
| Pruebas | Reglas, aceptación, errores e integración. |

Las operaciones financieras y de cupos tienen un servicio común; no duplicar lógica en vistas, señales, comandos y tareas. Reutilizar el ORM; no introducir una capa genérica de repositorios o microservicios sin una necesidad concreta compartida.

El reparto propuesto durante la conversación fue reservas/compras/check-in para Victor y usuarios/billetera para la otra persona de backend, con revisión conjunta de vuelos y transacciones críticas. Es una **propuesta**, no evidencia de asignación definitiva. Registrar responsables reales por HU en el tablero y usar un autor principal y un revisor por cambio.

### 11.3. Contrato HTTP común

Antes del primer endpoint, alinear con frontend:

- Prefijo propuesto de negocio: `/api/v1/`. Salud: `/api/health/`; esquema y documentación: `/api/schema/` y `/api/docs/`. Reutilizar rutas existentes si ya hay un acuerdo documentado, y registrar la convención definitiva.
- Nombres y campos coherentes entre endpoints; no publicar dos nombres para el mismo concepto sin una transición explícita.
- Dinero serializado como cadena decimal y moneda explícita; fechas ISO 8601 con zona/desplazamiento y datos necesarios para representación local.
- IDs técnicos separados de códigos visibles.
- Listas paginadas y filtros documentados.
- Errores con código estable, mensaje en español y detalles por campo cuando corresponda.
- Conflictos de precio, disponibilidad o estado deben ser distinguibles de errores de validación de campos y de fallos inesperados.
- No asumir que toda falta de sesión produce HTTP 401: DRF con `SessionAuthentication` puede devolver 403. Documentar el comportamiento real y no equiparar automáticamente todos los 403 con «sesión vencida».
- Los endpoints de salud distinguen disponibilidad de aplicación y base de datos, sin exponer secretos o configuración sensible.

OpenAPI es el contrato compartido de lo implementado; debe reflejar esta especificación. Los mockups son una referencia visual y deben adaptarse a las reglas resueltas.

### 11.4. Entorno, ejecución y procesos programados

- Versionar dependencias, migraciones, configuración de contenedores, instrucciones y datos de referencia reproducibles.
- Mantener `.env.example` sin secretos; separar configuración por entorno y no publicar credenciales de root.
- Crear root mediante un procedimiento idempotente con credenciales externas al código y sin contraseñas predeterminadas. La elección de un comando interactivo es una decisión técnica de BASE-01, no una nueva restricción del negocio.
- Usar PostgreSQL tanto en integración local como en CI para los comportamientos dependientes del motor.
- Disponer de persistencia y backups; ejecutar migraciones de manera coordinada al desplegar.
- El proceso de vencimiento debe ejecutarse automáticamente; puede iniciarse con comandos Django y un programador de tareas bajo responsabilidad de integración. No necesita introducir una cola distribuida solo por existir una tarea periódica.
- Varias instancias no deben generar códigos, ejecutar débitos ni liberar cupos de forma duplicada.
- Nginx/Gunicorn, HTTPS, configuración de cookies y orígenes deben integrarse antes de declarar completado el flujo de autenticación del frontend.

## 12. DEC-13 — Correos, noticias, PDF y funciones de apoyo

La entidad `notificacion_correo` del ER permite registrar destinatario, tipo, parámetros, estado e intentos. Registrar la intención de envío junto con la operación de negocio y procesarla tras confirmar la transacción. El uso aislado de `on_commit()` no garantiza persistencia si el proceso cae antes de enviar; una fila pendiente permite recuperar el trabajo.

- Reintentos controlados y trazabilidad de errores; no producir compras duplicadas por reenviar un correo.
- Un fallo de correo no revierte compra o check-in ya confirmados. Mantener consulta del resultado y permitir reintento del documento o envío.
- Verificación de cuenta fallida: conservar la cuenta sin verificar y permitir reenvío según los límites definidos.
- Código/localizador y pasabordo se envían al correo del viajero; notificaciones de afectación incluyen al comprador cuando corresponda.
- Un vuelo nuevo y una promoción generan noticias. Ocultar noticias y recomendaciones de vuelos cancelados o realizados, conservando la historia necesaria.
- Recomendaciones para clientes a partir de búsquedas/compras; sin historia, mostrar oferta vigente reciente. No añadir aprendizaje automático como requisito de esta versión.
- Mensajería conserva conversaciones y respuestas; comprobar acceso de cada participante.
- Chatbot orienta y remite a las vistas con criterios. Reservas, compras, cancelaciones y operaciones de billetera se confirman en los flujos del sistema. No otorgar al modelo permisos de escritura directa sobre saldo, cupos o tiquetes.
- Si el chatbot falla, conservar la búsqueda convencional y el acceso a mensajería conforme al rol.

## 13. DEC-14 — Git, coordinación y criterio de terminado

### 13.1. Reglas existentes que se conservan

S8 establece:

- Rama por HU, creada desde `main`: `feat/HU-N-descripcion`.
- Tipos de commit: `feat`, `fix`, `docs`, `test`, `chore`.
- Un PR por historia; mínimo una aprobación de otra persona; integración con **Squash and merge** y eliminación de la rama.
- No subir directamente a `main`, no usar `git push --force` y no subir `.env`, claves o contraseñas.

**Corrección del ejemplo de S8:** `HU-12-busqueda-vuelos` usa un número que no corresponde a S5. Búsqueda es **HU-005**; reserva es **HU-012**. Los ejemplos no redefinen la numeración oficial.

Convención propuesta: usar tres dígitos en ramas, commits y referencias (`HU-005`), respetando el patrón existente. No renumerar historias ni requisitos para «ordenarlos». S2 omite RF-BSQ-10 en su secuencia; conservar los IDs existentes y registrar cualquier incorporación futura.

Las reglas no definen PR técnicos sin HU. Resolver P-07 para incorporar configuración compartida o este complemento; no inventar HU-000 ni atribuir una autorización inexistente. Si el equipo conserva estrictamente un PR por HU, incluir solo la base indispensable en la primera historia correspondiente.

### 13.2. Inicio coordinado

1. Diagnosticar el repositorio real: dependencias, usuario, migraciones, CI, contenedores y comandos disponibles.
2. Incorporar este complemento y resolver los pendientes que bloqueen la primera historia.
3. Preparar juntos el usuario personalizado, PostgreSQL, configuración, contrato API y pruebas base.
4. HU-009 es una primera entrega útil porque aparece en iteración 1, pero depende de autenticación. Coordinar la base de HU-008; no afirmar que la numeración elimina esa dependencia.
5. Construir/revisar el flujo de HU-001 para establecer vuelos, rutas e inventario que necesitan las compras.
6. Desarrollar en paralelo módulos con contratos acordados y un responsable de migraciones por aplicación durante cada cambio.

Ante migraciones concurrentes, revisar el grafo y producir una migración de unión cuando corresponda. No resolver el conflicto borrando migraciones compartidas ni haciendo cambios manuales invisibles en una base.

### 13.3. Definición de terminado de una historia

- Criterios de aceptación implementados, incluidos errores y acceso indebido.
- Reglas de este complemento referenciadas y aplicadas.
- Migraciones y datos de referencia necesarios versionados.
- Contrato OpenAPI y documentación de uso actualizados.
- Pruebas relevantes ejecutadas con resultados verificables.
- Integración con frontend verificada cuando sea parte del criterio de la historia.
- Bitácora y notificaciones incluidas si el caso de uso las exige.
- PR revisado por otra persona, con alcance y pendientes explícitos.

No dar por terminada una historia solo porque existe un endpoint o una pantalla. No afirmar pruebas que no se ejecutaron.

### 13.4. Calidad exigida y responsabilidades

| Requisito de la ERS | Evidencia/acción |
|---|---|
| Cobertura mínima del 70 % sobre lógica de negocio, RNF-MAN-03 | Informe de cobertura de esa capa y ejecución en cada integración. |
| Trazabilidad, RNF-MAN-02 | HU/CU/RF/RNF → decisión → componente → prueba. |
| Transacciones, RNF-FIA-01 | Fallos intermedios controlados y ausencia de estados parciales. |
| Auditoría, RNF-FIA-02 | Actor, operación, fecha, entidad y origen cuando corresponda, sin secretos. |
| Backup diario y RPO ≤ 24 h, RNF-FIA-03 | Copia y prueba de restauración; responsable de integración. |
| Salud de aplicación/base, RNF-DIS-03 | Endpoint y comprobación de fallos. |
| Objetivo de disponibilidad mensual 99 % | Ventana operativa y medición; no prometerlo por la elección de hosting. |
| Escalamiento sin sesión en memoria local | Sesión compartida y prueba del despliegue acordado. |
| Responsive/WCAG 2.1 AA | Revisión de frontend, teclado, contraste y formularios. |

Los objetivos de rendimiento de S2 se presentan como iniciales y pendientes de confirmación de carga nominal. Conservar su referencia: búsqueda p95 ≤ 3 s; detalle/catálogo p95 ≤ 2 s; compra ≤ 5 s excluyendo entrega de correo; 100 usuarios concurrentes; liberación dentro de un minuto; correos dentro de cinco minutos; errores 5xx ≤ 1 %. Definir datos y entorno de medición antes de reportar cumplimiento.

## 14. Decisiones pendientes: registro único

Los siguientes puntos permanecen abiertos; no son permiso para inventar una respuesta individual. La propuesta ayuda a resolverlos, pero **no equivale a una decisión ya aprobada**. Bloquear únicamente el comportamiento afectado, no el proyecto completo.

| ID | Punto por cerrar | Propuesta o criterio de resolución | Área afectada |
|---|---|---|---|
| **P-01** | Evento que marca `REALIZADO`, tratamiento de retrasos, check-ins/pasabordos al reprogramar y flujo de reubicación. | Separar hora prevista de confirmación de operación; considerar confirmación administrativa o evento explícito. Definir conservación o invalidación de check-in y documentos, selección/aceptación de vuelo sustituto y tratamiento de diferencias de tarifa, sin cobros silenciosos. Actualizar RF-ADM-12/13/RNF-DIS-02 y HU-002/003. | Vuelos, tareas automáticas, reubicación y check-in. |
| **P-03** | Check-in rápido por documento/localizador frente a privacidad y autorización. | Mantener acceso sin cuenta, pero proponer un código de un solo uso enviado al correo registrado antes de mostrar datos o confirmar cambios. No revelar destinatarios completos ni permitir acceso a información financiera. Acordar el flujo exacto. | API pública, check-in y frontend. |
| **P-04** | Promociones, `cupos_afectados`, reservas previas y tarifa por clase. | Definir si cupos es cuota consumible o instantánea; elegibilidad de reservas ya retenidas; tratamiento de superposición; y cómo se ingresan precios de ambas clases. Propuesta de simplicidad: una promoción activa por vuelo/clase. No inventar recargos de primera clase. | Vuelos, promociones, cotización, reserva/compra. |
| **P-05** | Parámetros no especificados: límites monetarios, intentos/bloqueo, TTL de recuperación, frecuencia de reenvío, segundo factor e imagen. | Fijar valores en una configuración común y reflejarlos en pruebas. Elegir correo OTP o TOTP para retiros y definir uso único, vencimiento y vinculación a la operación. | Seguridad, billetera, perfil. |
| **P-06** | Ida y regreso internacional frente a rutas autorizadas solo Colombia → exterior. | Aclarar si se autorizan rutas inversas del mismo conjunto o si esa modalidad queda limitada. Hasta resolverlo, no ampliar el catálogo silenciosamente. | Rutas, búsqueda y compra internacional. |
| **P-07** | Rama/PR para tareas técnicas o documentación transversal sin HU propia. | Registrar una convención explícita en S8, manteniendo revisión y squash. No crear historias ficticias. | Integración y todo el equipo. |

**P-02 — Base del modelo resuelta (16 de octubre de 2026; DEC-15):** se aprobó que root use su ID para iniciar sesión y no requiera correo ni datos personales; clientes y administradores usan un correo obligatorio, único sin distinguir mayúsculas. `ROOT` es un rol de negocio independiente de `is_staff` e `is_superuser`. Esta decisión no define permisos financieros ni cambia los flujos de las HU.

**Acuerdo:** autorización expresa del usuario responsable del encargo el 2026-10-16; incorporación local, sin PR ni aprobación académica atribuida. Afecta RF-USU-01/05/06/07/08, HU-007/008/009 y usuario. **Validación de la base:** root puede omitir correo y perfil; los demás roles requieren correo único sin distinguir mayúsculas; el nombre de perfil se conserva separado del acceso. La revisión y las pruebas se registran en [BASE-01_VERIFICACION.md](BASE-01_VERIFICACION.md). Quedan para sus HU los flujos públicos, la recuperación de root sin correo y los permisos financieros; no se aprobó una excepción a la verificación de correo.

Para cerrar un pendiente, registrar respuesta, responsable del acuerdo, fecha, referencias afectadas y criterio de aceptación. Sustituir su estado por una decisión vigente y actualizar las pruebas relacionadas.

## 15. Matriz de correcciones de los artefactos

| Inconsistencia o especificación | Regla común | Artefactos a alinear |
|---|---|---|
| Código de vuelo ausente y ejemplo puramente numérico | DEC-01: alfanumérico con consecutivo | S3/S4, RF-ADM-02, HU-001/CU-01, API/mockups. |
| Código por tiquete frente a localizador grupal | DEC-02 | RF-COM-18/19, RF-CHK-01/11, S2 §3.5, S3/S4, HU-013/015/016, CU-13/16. |
| Tabla billetera representa movimientos | DEC-03 | S3/S4, RF-GFI-02/03/04, HU-007/010/011. |
| Fecha de creación redundante en billetera | Omitirla; usuario y billetera nacen juntos | S3/S4, modelos y serializers. |
| UUID y enteros sin criterio compartido | DEC-04 | S3/S4 y migraciones. |
| Edición bloqueada por ventas en enunciado | DEC-05: permitir edición de fecha/hora/precio | S1 como antecedente de cambio, RF-ADM-10/20, HU-002/CU-02. |
| Cambio de precio puede alterar compras históricas | DEC-06: preservar precio pagado | Modelo de tiquete/compra, HU-002/004/013/014, servicios financieros. |
| Promoción tratada como cualquier ajuste temporal | Descuento temporal; P-04 para condiciones no fijadas | HU-004/CU-04, promoción, cotización. |
| Reprogramación sin efectos sobre reservas y documentos | §6.2, DEC-07 y P-01 | HU-002/012/016, tareas y notificaciones. |
| Pasar hora programada implica vuelo realizado | P-01; no cerrar el estado sin resolverlo | RF-ADM-13, RNF-DIS-02, estados y filtros. |
| Reserva de 24 h interpretada sin límite por salida | DEC-07: mínimo de límites | RF-COM-15/16/17/24, RN-05, HU-012, CU-12/13. |
| Cancelación de reserva sin pago genera devolución | Reembolso solo sobre dinero debitado | RF-GFI-08, HU-014/CU-14, billetera. |
| «Billetera del pasajero» cuando paga otro cliente | §5.2/§6.5: devolver a la billetera que pagó | RF-ADM-12, RN-17/20, HU-003, HU-014 y cancelaciones. |
| RF-COM-13 cita depósitos como débito de compra | Referenciar RF-GFI-03/04/07 | Matriz de trazabilidad y S2. |
| Asignación de silla en reserva y compra ambiguas | DEC-08: cupo al reservar, silla al comprar | RF-COM-10, RN-14, RF-CHK-04, S3/S4 y mapa de sillas. |
| Dobles descuentos al comprar una reserva | Conversión de retenido a vendido | HU-012/013, inventario y pruebas. |
| Unicidad de silla/viajero bloquea historia cancelada | Restricciones sobre ocupaciones activas | S4, modelos y migraciones. |
| Check-in rápido contradice autenticación general | Excepción funcional y P-03 | RF-CHK-01, RNF-SEG-01/12, HU-016/CU-16. |
| Root con ID/contraseña frente a correo obligatorio | DEC-15 | RF-USU-01/07/08, HU-008/009, usuario. |
| Ida/vuelta internacional no cubierta por rutas inversas | P-06 | RF-ADM-05, RF-BSQ-12, RF-COM-08. |
| Autorización de root confundida con superusuario | DEC-10: rol explícito | Permisos y pruebas por rol. |
| Ejemplo HU-12 denominado búsqueda | HU-005 es búsqueda; HU-012 es reserva | S8 y ejemplos de ramas/commits. |
| Infraestructura sin HU en reglas de PR | P-07 | S8, tablero y plantillas de PR. |

## 16. Casos mínimos de aceptación compartidos

Son escenarios para convertir en pruebas de las historias correspondientes. No constituyen resultados ejecutados.

| Caso | Resultado esperado |
|---|---|
| CA-01 — Dos administradores crean vuelos simultáneamente | Códigos válidos, distintos, consecutivos; sin registros parciales. |
| CA-02 — Intento de cambiar `codigo_vuelo` | Rechazo de la modificación; código conservado. |
| CA-03 — Dos viajeros con ida y regreso | Cuatro tiquetes y un localizador; check-in individual por vuelo. |
| CA-04 — Fallo al crear billetera durante registro | No queda una cuenta creada parcialmente. |
| CA-05 — Dos compras disputan el último cupo | Solo una consume el cupo; la otra no debita saldo. |
| CA-06 — Dos débitos concurrentes excederían el saldo | No se produce saldo negativo; se rechaza lo que no puede pagarse. |
| CA-07 — Falla intermedia al confirmar compra | No quedan débito, sillas, cupos o tiquetes parcialmente confirmados. |
| CA-08 — Repetición de solicitud con misma clave y contenido | Mismo resultado, sin segundo cargo ni segunda compra. |
| CA-09 — Conversión de reserva vigente | No duplica el consumo de cupos; asigna silla y genera compra/localizador. |
| CA-10 — Compra justo al vencimiento | Rechazo aunque no haya corrido el proceso de liberación. |
| CA-11 — Reprogramación posterior | No extiende una reserva más allá de sus 24 h originales. |
| CA-12 — Cliente acumula más de cinco tiquetes en un vuelo | Rechazo al sumar reservas vigentes y compras activas. |
| CA-13 — Mismo viajero en dos operaciones activas del vuelo | Rechazo aunque se hayan creado filas `viajero` diferentes. |
| CA-14 — Grupo sin adulto en el vuelo | Rechazo; edad calculada para la salida local. |
| CA-15 — Precio base cambia tras una compra | El pago histórico y su base de reembolso permanecen intactos. |
| CA-16 — Precio cambia entre cotización y confirmación | Se informa nuevo total; no se debita sin aceptarlo. |
| CA-17 — Cancelación de reserva sin pago | Libera cupos y conserva historial; no crea dinero en la billetera. |
| CA-18 — Reintento de cancelación/reembolso | No libera dos veces ni duplica el abono. |
| CA-19 — Cliente consulta compra ajena por ID/localizador | Acceso denegado y datos personales protegidos. |
| CA-20 — Root/administrador intenta comprar | Rechazo aun si tiene privilegios técnicos elevados. |
| CA-21 — Cuenta sin correo verificado | Puede autenticarse; no reserva, compra ni opera billetera. |
| CA-22 — Un cambio de silla y segundo intento | Primer cambio válido; segundo rechazado; clase y disponibilidad respetadas. |
| CA-23 — Cambio de silla después del check-in | Rechazo. |
| CA-24 — Falla SMTP tras compra | Compra conservada y notificación pendiente/reintentable. |
| CA-25 — Paso por horario de verano | Cálculo con zona IANA y tratamiento explícito de hora ambigua/inexistente. |
| CA-26 — Cierre de sesión e inactividad | Sesión revocada al salir y caducidad según los 30 minutos acordados. |
| CA-27 — Cancelación de vuelo con varios compradores y fallo en un abono | Operación persistente revertida; no quedan afectados tratados parcialmente. |
| CA-28 — Dos ejecuciones del proceso de vencimiento | Una sola liberación por reserva. |
| CA-29 — Alta de administrador por usuario distinto de root | Rechazo, incluido el intento de elevar privilegios desde el cuerpo HTTP. |
| CA-30 — Registro con correo ya utilizado | Rechazo coherente con la normalización acordada; sin usuario ni billetera adicionales. |
| CA-31 — Cancelación de vuelo sin alternativas | Reembolso del precio pagado a cada comprador; viajeros sin cuenta no requieren billetera propia. |
| CA-32 — Nueva reserva después de una anterior vencida | Solo se acepta si sigue abierta la ventana del vuelo y se cumplen cupos y validaciones; no se reactiva la reserva anterior. |

Agregar casos para cada pendiente cuando se cierre. Para bloqueos y concurrencia, usar pruebas transaccionales con conexiones separadas y sincronización controlada; no simular concurrencia mediante llamadas secuenciales ni asumir que una prueba envuelta automáticamente en una transacción demuestra el bloqueo real.

## 17. Instrucciones reutilizables para herramientas de IA

Incorporar una referencia a este archivo en el `AGENTS.md` raíz y en las instrucciones equivalentes de las otras herramientas utilizadas. Evitar copias completas divergentes del complemento.

```markdown
## Contexto común del proyecto

Antes de planificar o implementar una tarea, lee completo
docs/ACLARACIONES_Y_LINEAMIENTOS_DEL_PROYECTO.md,
README.md, REGLASCOMMITS.md y los requisitos de la HU afectada.

Contrasta esas reglas con el código, las migraciones, OpenAPI
y las pruebas actuales. Aplica las decisiones resueltas del
complemento en los puntos donde corrigen documentos anteriores.

No conviertas un pendiente P-XX en una regla de negocio privada.
Identifica el comportamiento afectado, registra el conflicto y
continúa las partes independientes de la tarea.

Conserva trazabilidad HU/CU/RF/RNF/DEC y actualiza pruebas y
contratos afectados. No sustituyas reglas de negocio por lo que
parezca más cómodo de generar. No declares verificaciones no
ejecutadas ni sobrescribas trabajo ajeno o migraciones compartidas.
```

Cada encargo debe indicar HU, alcance, decisiones aplicables, dependencias, criterios de aceptación y validación esperada. Pedir una explicación del cambio y revisar el diff antes de integrarlo.

## 18. Mantenimiento y evolución de la base común

1. Mantener este archivo en Git como referencia única. Los chats aportan propuestas, pero los acuerdos se trasladan aquí.
2. Registrar en el PR cualquier cambio de regla, su motivo, fuentes afectadas y plan de migración si corresponde.
3. Actualizar la versión y el historial de cambios; no cambiar silenciosamente el significado de DEC-XX.
4. Cuando una regla se sustituya, indicar cuál la reemplaza para que las IA no recuperen ambas como vigentes.
5. Mantener el avance de implementación en el tablero/PR y, si hace falta, en un registro de estado separado. Este complemento describe comportamiento esperado, no certifica que esté construido.
6. Al cambiar documentación original, comprobar si queda alineada con este complemento; conservar la trazabilidad histórica sin mantener contradicciones activas.
7. Versionar los parámetros acordados en configuración común y reflejar los valores relevantes en ejemplos y pruebas.

### 18.1. Plantilla para modificar una decisión

| Campo | Contenido requerido |
|---|---|
| Identificador | DEC-XX o P-XX resuelto. |
| Problema | Contradicción o vacío específico. |
| Decisión | Regla inequívoca y fronteras de aplicación. |
| Motivo | Requisito o necesidad que la justifica. |
| Procedencia | Aclaración expresa, requisito o convención técnica. |
| Impacto | Documentos, endpoints, modelos, datos, pantallas y tareas afectados. |
| Validación | Escenarios de aceptación y resultados cuando se ejecuten. |
| Acuerdo | Fecha, responsable y PR de incorporación. |

### 18.2. Historial

| Versión | Fecha | Cambio |
|---|---|---|
| 1.0.1 | 2026-10-16 | Registra la autorización del usuario sobre la base de P-02/DEC-15, su alcance y evidencia; aclara que separar roles de privilegios técnicos no equivale a prohibirlos. No resuelve permisos financieros ni otras HU. |
| 1.0.0 | 2026-10-14 | Consolidación inicial de correcciones y aclaraciones de la conversación; convenciones comunes, matriz de trazabilidad, escenarios de aceptación y pendientes explícitos. |

## 19. Referencias técnicas de apoyo

Estas referencias apoyan decisiones técnicas; no reemplazan los requisitos propios del proyecto. Se consultaron durante la conversación del 11 de octubre de 2026. Verificar compatibilidad con las versiones efectivamente fijadas en el repositorio.

- [Django: usuario personalizado](https://docs.djangoproject.com/en/5.2/topics/auth/customizing/).
- [Django: transacciones y acciones tras commit](https://docs.djangoproject.com/en/5.2/topics/db/transactions/).
- [Django: select_for_update y QuerySets](https://docs.djangoproject.com/en/5.2/ref/models/querysets/).
- [Django: campos, BigAutoField y DecimalField](https://docs.djangoproject.com/en/5.2/ref/models/fields/).
- [Django: restricciones de base de datos](https://docs.djangoproject.com/en/5.2/ref/models/constraints/).
- [Django: gestión de contraseñas y Argon2id](https://docs.djangoproject.com/en/5.2/topics/auth/passwords/).
- [DRF: autenticación y SessionAuthentication](https://www.django-rest-framework.org/api-guide/authentication/).
- [OpenAI: instrucciones de proyecto mediante AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md).
- [IATA AIDM: número de vuelo de uno a cuatro dígitos](https://airtechzone.iata.org/aidm_model/25.2/EARoot/EA6/EA2/EA3/EA1/EA1/EA12375.htm).
- [FIXM: designador comercial de vuelo](https://fixm.aero/releases/FIXM-4.3.0/doc/schema_documentation/Fixm_IataFlightDesignatorType.html).

## 20. Huellas de los documentos base

Las siguientes huellas SHA-256 identifican los adjuntos utilizados. Si una fuente posterior cambia, revisar su impacto en las decisiones antes de reutilizar este complemento sin actualización. Las huellas no significan que esos archivos ya estén dentro del repositorio.

```text
Proyecto_Lab_Soft_2026-02.pdf
843255532ad77cdd64b14c75f46c270aa885a393974e0e64e73b017920a0e3e6

ERS(1).pdf
3aba37724c832237ea1e482c5f2e668e4bade75956f8334bdb1fd4c9270665dd

Diagramas de Clases.pdf
411af96e19529530763af911885d2470f83ffd8684dd0bec4aad18970d1149d8

er.pdf
601184f904a693eb68222b62e094602c7093bde1f537353030c60c297c37e6b2

Historias_Usuario_Sistema_Tiquetes_Aereos.pdf
1c692536e508ec70da39db9ab566eecf4057f018295c2e18291d196f263c90ff

Acta_Casos_de_Uso_Tiquetes_Aereos.docx
f5ea812ec92c64e7c5bc4aa63997295965e590960212a5fadd994ab8afe0750a

Mockups · Sistema de Tiquetes Aéreos.html
af4fb9f5052b77729b9cc853ec7674cf7a4e97bfbb5d3c7be11eae6396e1ff8c

REGLASCOMMITS.md
efca50a4dbf752c84c0f08ff40140b8a0bfd931d00210d2ebdd2b4ad405df1c4

is714-laboratorio-de-software(1).pdf
b664db5f0562b24fa6327b93a7cbba45937230030ae9724f3d3fbadd03555ebb
```
