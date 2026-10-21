
# Instrucciones para agentes de desarrollo
Estas instrucciones aplican al repositorio Aerolínea Web. El encargo del usuario define la tarea y las acciones autorizadas. Este archivo establece las reglas comunes de trabajo; no autoriza por sí solo implementar todo el proyecto.

## 1. Contexto y fuentes

El proyecto es una aplicación web académica de gestión de vuelos, reservas, compras y check-in. El equipo tiene cuatro integrantes: dos de backend, uno de frontend y uno de integración/despliegue.

Antes de planificar o modificar código:

1. Lee `README.md`, `REGLASCOMMITS.md` y los `AGENTS.md` aplicables al área de trabajo.
2. Lee completo `docs/ACLARACIONES_Y_LINEAMIENTOS_DEL_PROYECTO.md` si todavía no lo has leído en la sesión o cambió desde la última lectura.
3. Consulta en `docs/` el enunciado, la ERS, la HU, el caso de uso y los modelos relevantes para la tarea.
4. Inspecciona el código, las migraciones, las dependencias, las pruebas y el contrato API existentes.

El complemento resuelve únicamente las contradicciones que identifica expresamente. Para el resto del alcance se conservan los requisitos originales. El README resume el proyecto; una pantalla, un diagrama o el código actual no sustituyen por sí solos una regla documentada.

No asumas acceso a conversaciones anteriores. Si falta una fuente o no puedes interpretar un documento o diagrama, identifica la información faltante sin inventar su contenido. Si las fuentes se contradicen en un punto no resuelto, registra el conflicto antes de implementar una interpretación.

## 2. Alcance y autonomía

- Identifica el objetivo, la HU o tarea técnica, las decisiones aplicables y los criterios de aceptación.
- Explica brevemente el plan y ejecuta el trabajo autorizado; no te detengas únicamente en una propuesta.
- Resuelve detalles técnicos ordinarios dentro del alcance, reutilizando las convenciones existentes. No solicites confirmación por cada archivo o cambio reversible necesario.
- No añadas funcionalidades, actores, integraciones, parámetros de negocio ni criterios de aceptación que no estén respaldados por las fuentes o autorizados en el encargo.
- Un pendiente `P-XX` no es una decisión aprobada. Expón el punto afectado y una recomendación concreta; solicita la decisión antes de implementar ese comportamiento y continúa las partes independientes.
- Cambios de alcance, stack, arquitectura o dependencias sustanciales requieren acuerdo explícito, salvo que ya estén autorizados en la tarea.
- No modifiques requisitos, aclaraciones o estas instrucciones para justificar una implementación incompatible. Separa propuestas de decisiones adoptadas.

## 3. Repositorio y entorno

- Comprueba la raíz de Git, la rama y el estado del árbol de trabajo antes de modificar archivos.
- Trabaja en la rama autorizada para la tarea. No fijes una rama de configuración como destino permanente para todas las HU.
- Conserva los cambios locales y el trabajo ajeno. Si existe un conflicto de edición, identifica los archivos afectados y evita sobrescribirlos.
- No inicialices un repositorio dentro o alrededor del clon existente.
- Detecta el intérprete y el entorno virtual disponibles. Reutilízalos cuando sean compatibles; no elimines entornos ni reemplaces el Python del sistema sin autorización.
- Distingue los comandos ejecutados en WSL de los ejecutados dentro de contenedores. Comprueba el entorno y la base de datos de destino antes de ejecutar operaciones con efectos persistentes.
- No instales herramientas globales, elimines datos o volúmenes, despliegues, envíes correos reales ni cambies configuración remota sin autorización explícita.
- No hagas commits, push, PR o merges salvo autorización explícita para esas acciones. Conserva las reglas de revisión y squash de `REGLASCOMMITS.md`; no uses `git push --force` ni operaciones Git destructivas.
- No leas, muestres ni copies secretos salvo lo estrictamente necesario para la tarea; nunca los incluyas en logs, respuestas o archivos versionados. Usa ejemplos sin credenciales reales.

## 4. Arquitectura y contratos

Mantén el monolito modular con Django, Django REST Framework y PostgreSQL; el frontend utiliza React y TypeScript. Consulta el README y los archivos de dependencias para el resto del stack y sus versiones.

- Modelos: persistencia, relaciones y restricciones.
- Serializers: representación y validación de entradas y salidas.
- Servicios: reglas de negocio, casos de uso y transacciones.
- Vistas y permisos: HTTP, autenticación, rol y propiedad del recurso.
- Pruebas: comportamientos observables y riesgos reales.

Reutiliza las reglas compartidas; no dupliques cálculos o validaciones entre módulos. El backend es responsable de validar precios, permisos, saldo, disponibilidad y límites temporales.

Respeta sesiones de Django y CSRF conforme al complemento. No introduzcas JWT, microservicios, colas distribuidas ni nuevas capas de abstracción sin una necesidad y un acuerdo documentados. No desactives protecciones para resolver errores de integración.

Mantén coherentes el contrato OpenAPI, el frontend y los servicios. Al cambiar un contrato compartido, identifica sus consumidores y coordina la adaptación. Usa las convenciones documentadas para dinero, fechas, errores y paginación.

## 5. Persistencia y operaciones críticas

- Define el usuario personalizado y `AUTH_USER_MODEL` antes de la primera migración de autenticación. Si existen decisiones pendientes que condicionan ese modelo, no consolides un esquema inventado.
- Gestiona el esquema mediante migraciones versionadas. No borres ni reescribas migraciones compartidas para ocultar conflictos.
- No crees todas las tablas por anticipado: implementa lo necesario para el alcance autorizado, conservando el modelo y las dependencias acordados.
- Usa PostgreSQL en integración y concurrencia. No sustituyas silenciosamente sus comprobaciones por SQLite.
- Aplica transacciones, restricciones y control de concurrencia según la operación. Evita duplicar cargos, reembolsos, compras o liberaciones ante reintentos.
- Conserva el historial y las reglas financieras del complemento. No alteres precios pagados ni generes devoluciones sin un débito previo.
- La creación de cuenta y billetera debe ser conjunta cuando se implemente ese flujo; la billetera no tiene `creada_en` independiente.
- Procesa los efectos externos después de confirmar la transacción y conserva el trabajo pendiente cuando el diseño requiera reintentos.

## 6. Dependencias y configuración inicial

Respeta las versiones fijadas y los archivos de bloqueo existentes. Si todavía no existen, utiliza la propuesta autorizada en la tarea y verifica compatibilidad antes de fijar versiones. No inventes resultados del resolvedor.

Durante la inicialización, prepara configuración, dependencias, entorno reproducible, pruebas y documentación. No declares terminadas HU por haber creado su infraestructura. No generes CRUD, datos de producción ni usuarios con contraseñas predeterminadas sin un requisito explícito.

Los comandos de instalación, ejecución y pruebas deben derivarse de los archivos reales del repositorio. Si todavía no están implementados, indícalo y documenta el pendiente; no presentes comandos supuestos como verificados.

## 7. Verificación y trazabilidad

- Ejecuta las comprobaciones pertinentes al cambio: formato, análisis estático, configuración, migraciones, pruebas y contrato API, según corresponda.
- Prueba reglas y fallos relevantes, no únicamente el camino exitoso. Para concurrencia, utiliza mecanismos que reproduzcan operaciones simultáneas reales.
- No escribas pruebas artificiales para inflar cobertura ni relajes controles para obtener un resultado verde.
- Distingue entre pruebas ejecutadas, comprobaciones estáticas y verificaciones pendientes. No afirmes que CI o producción funcionan solo porque creaste su configuración.
- Mantén trazabilidad de HU/CU/RF/RNF y decisiones `DEC-XX` cuando apliquen. Actualiza los documentos afectados sin duplicar el complemento completo en otros archivos.
- Un paquete de HU organiza el trabajo; no reemplaza la regla de una rama y un PR por historia, salvo un cambio explícito del acuerdo del equipo.

## 8. Entrega al usuario

Comunica en español de forma concreta. Durante trabajos prolongados, informa avances, hallazgos y bloqueos relevantes.

Al finalizar, resume qué cambió y por qué, los archivos afectados, las verificaciones realmente ejecutadas y sus resultados, y los pendientes o decisiones necesarias. Incluye comandos de uso cuando corresponda y aclara en qué entorno deben ejecutarse.

No declares completa una tarea que mantiene criterios bloqueados. Explica qué parte está lista, qué falta y qué decisión o recurso permitirá continuar.
