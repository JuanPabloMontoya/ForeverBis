# Forever BIS — Plan del proyecto

**Estado:** Fase 3.1: auditoria de cobertura y proveedores completada; pendiente aprobacion humana antes de la siguiente fase (7 nov 2026)
**Investigación consultada:** 7 de noviembre de 2026  
**Alcance:** decisiones de arquitectura, planificación y estado de ejecución por fase.

## 1. Objetivo y principios

Forever BIS es ante todo un planificador de progresion de equipo nivel por nivel para WoW Forever. La experiencia principal configura clase, especializacion y faccion; la barra horizontal de niveles 1-60 conduce a un paper doll de 17 espacios. El catalogo de objetos es una herramienta secundaria y una fuente de datos interna.

- WoW Forever es una fuente de datos distinta de Classic Era. No completar registros de Forever con valores de Era de forma silenciosa.
- Cada dato publicado debe tener fuente, versión/build, fecha de captura y estado de verificación. Los campos desconocidos se representan como desconocidos.
- «Mejor» depende de contexto y criterios. Las recomendaciones deben incluir criterios explicables y revisión editorial, no presentar una puntuación opaca como verdad oficial.
- Separar datos del juego, fuentes de obtención y decisiones editoriales BIS para poder actualizar cada parte por separado.
- Atribuir las fuentes externas junto a los datos requeridos por sus términos. Verificar las condiciones de cada proveedor antes de importar o redistribuir datos.

## 2. Fuentes de datos investigadas

| Fuente | Qué ofrece / evidencia | Uso propuesto | Límites y confianza |
|---|---|---|---|
| [TheWoWDB: API de desarrolladores](https://thewowdb.com/developers/) | API JSON pública, sin clave, con endpoints de Forever para objetos, hechizos, misiones, NPC, zonas y tooltips. Documenta búsqueda, paginación, ETag, caché y límite de peticiones. Sus términos publicados permiten uso gratuito incluso comercial con enlace visible a TheWoWDB y prohíben revender el dataset bruto. | Primer adaptador de ingesta candidato para datos básicos de objetos y referencias. Atribuir cada registro mostrado y respetar caché/ETag/límites. Antes de adoptarla, validar cobertura, campos y términos vigentes del contenido concreto. | Fuente comunitaria y no oficial. Puede cambiar. La API no garantiza por sí sola drops completos, disponibilidad por fase ni elegibilidad de cada personaje. |
| [Eternadex: base de objetos](https://eternadex.com/en/datenbank/?m=finder) | Declara que calcula estadísticas desde datos de juego y construye fuentes desde atlas de mazmorras y base de misiones; advierte que cambios server-side pueden diferir y prevalece el tooltip del juego. | Referencia cruzada y auditoría manual de cobertura de stats y fuentes. No importar automáticamente hasta confirmar permiso/licencia y atribución. | Base de terceros; las fuentes de adquisición se combinan con referencias editoriales propias. No asumir que una fila coincide con el estado vigente del servidor. |
| [WoWhead Forever](https://www.wowhead.com/forever/database) | Existe una base y una ruta de páginas para Forever. Wowhead documenta integración de tooltips y mantiene datos aportados por usuarios y datamining. | Enlaces externos solo cuando la página del objeto se resuelva y corresponda al ID/versión de Forever. Investigar permiso antes de reutilizar contenido; por ahora solo enlazar. | La compatibilidad de una URL no prueba que los datos estén completos ni que exista una API pública autorizada para ingesta. No usar la base Classic como sustituto. |
| [Foro oficial: observaciones de API Forever](https://us.forums.blizzard.com/en/blizzard/t/wow-forever-api-what-works-so-far-plus-a-ts-client/60334) | Un miembro de la comunidad describe namespaces static-forever, dynamic-forever y profile-forever y endpoints observados. El hilo dice que la API no está documentada y puede cambiar. | Vigilar como posible fuente futura y reevaluar si Blizzard publica documentación y habilita acceso autorizado estable. | No es documentación oficial ni contrato de estabilidad. No basar el MVP en endpoints descubiertos mediante sondeo ni recolectar datos por métodos no autorizados. |
| [Condiciones de API de Blizzard](https://www.blizzard.com/es-es/legal/a2989b50-5f16-43b1-abec-2ae17cc09dd6/condiciones-de-uso-de-las-api-para-desarrolladores-de-blizzard) | Blizzard mantiene términos específicos para APIs de desarrolladores. | Revisar versión vigente si se incorpora API oficial, antes de crear credenciales o guardar/publicar datos. | La página legal no se pudo abrir directamente durante esta revisión; no se presupone autorización, cobertura Forever ni acceso a datos estáticos. |

### Conclusión de disponibilidad

Hay fuentes comunitarias utilizables para comenzar una evaluación, pero calidad, cobertura y licencia de cada campo deben confirmarse antes de publicar recomendaciones. La API de TheWoWDB es la candidata más clara porque publica endpoints y condiciones de uso; la ingesta debe conservar atribución y no ofrecer descarga del dataset bruto.

La información pública consultada no confirma una API de Blizzard para Forever documentada y estable. El foro citado documenta exploración de terceros. No se encontró una fuente única que garantice datos completos y actuales de requisitos, restricciones, drops y disponibilidad por facción para todos los objetos 1–60. Los objetos ocultos/no revelados y cambios posteriores al build de origen son un riesgo concreto: registrar faltantes y diferencias en vez de completar con Era.

### Política para enlaces Wowhead

Generar enlaces mediante un campo external_url o una regla versionada por proveedor. Solo asignarlo cuando se verifique que la página existe y el ID representa el mismo objeto en Forever. No inferir compatibilidad por nombre o igualdad de ID. Si no hay coincidencia verificada, mostrar el objeto sin enlace. La página de destino es referencia externa, no certificación de la recomendación.

## 3. Arquitectura propuesta

Monolito modular al inicio, con contratos claros. Evita operar varios servicios antes de validar fuente y catálogo; los módulos podrán separarse si el volumen lo requiere.

    React + TypeScript + Vite + Tailwind
                  │ REST / JSON
                  ▼
    FastAPI — API de lectura y validación Pydantic
                  │
                  ├── Catálogo y consultas (SQLAlchemy)
                  ├── Motor de elegibilidad y recomendaciones BIS
                  └── Adaptadores de fuentes / proceso de actualización
                             │
                             ├── API(s) comunitarias autorizadas
                             └── revisión editorial de fuentes y listas BIS
                  ▼
    PostgreSQL — catálogo versionado, relaciones, procedencia y recomendaciones

- **Frontend:** selección de clase/especialización/facción, slider 1–60, 17 slots, tarjetas y estados de carga/sin datos. El backend devuelve candidatos filtrados y metadatos explicables; no duplicar reglas del juego en UI.
- **Backend:** endpoints REST versionados (/api/v1), esquemas Pydantic, consultas, elegibilidad, puntuación y trazabilidad.
- **Database:** PostgreSQL como persistencia; SQLAlchemy con migraciones Alembic e índices por clase, spec, slot, nivel, facción y estado de verificación.
- **Data ingestion:** adaptadores por proveedor, normalización, validación de esquema, ETag/caché, límites, comparación con build anterior y reporte de cambios antes de publicar.
- **BIS recommendation engine:** módulo Python puro, separado de FastAPI y SQLAlchemy. Filtra primero por reglas duras; ordena después con criterios versionados y configurables. Las recomendaciones publicadas requieren evidencia y revisión.

### Contrato de recomendación

La consulta mínima será class_id, spec_id, faction_id, level y ruleset_version. La respuesta devolverá recomendación por slot con objeto y nivel aplicable, categoría editorial (BIS, Alternative, Easy to Obtain, Upgrade), razones/criterios, restricciones y fuente conocidas, procedencia/fecha/build y enlace externo opcional verificado.

Upgrade describe una mejora relativa al contexto elegido (equipo actual o nivel anterior), mientras que las otras categorías expresan el tipo de recomendación. La API y UI deben permitir que las etiquetas no sean excluyentes si el producto las necesita como ejes distintos.

## 4. Estructura inicial de carpetas

    forever-bis/
    ├── PROJECT_PLAN.md
    ├── README.md
    ├── pyproject.toml                 # dependencias, Ruff, pytest
    ├── alembic.ini
    ├── alembic/                        # migraciones SQLAlchemy
    ├── backend/
    │   ├── app/
    │   │   ├── main.py
    │   │   ├── api/v1/                 # routers HTTP
    │   │   ├── core/                   # configuración, logging
    │   │   ├── schemas/                # modelos Pydantic
    │   │   ├── db/                     # sesión y base SQLAlchemy
    │   │   ├── models/                 # entidades ORM
    │   │   ├── catalog/                # consultas de catálogo
    │   │   ├── recommendations/        # elegibilidad, scoring, publicación BIS
    │   │   └── ingestion/              # adaptadores, normalización y diff
    │   └── tests/                      # unitarios, integración, contratos API
    ├── frontend/
    │   ├── package.json
    │   └── src/
    │       ├── app/
    │       ├── api/                    # cliente tipado
    │       ├── features/planner/       # selector, niveles, equipo y slots
    │       ├── components/
    │       └── styles/
    ├── data/
    │   ├── fixtures/                   # muestras pequeñas autorizadas
    │   └── reports/                    # diffs/validaciones, sin credenciales
    └── docs/
        ├── adr/                        # decisiones técnicas fechadas
        ├── DATA_SOURCES.md             # licencias, atribución y cobertura
        └── recommendation-method.md    # criterios y versión del método BIS

No incluir dumps completos de bases ajenas en Git. Credenciales y configuración local irán en variables de entorno ignoradas por Git.

## 5. Modelo de datos inicial

| Entidad | Campos principales / propósito |
|---|---|
| GameVersion | id, game_key (wow_forever), build, región, observed_at, source_id, is_current. Delimita snapshot representado. |
| DataSource | id, name, base_url, terms_url, attribution_text, license_status, last_checked_at. Control de uso y atribución. |
| Item | id, source_id, source_item_id, game_version_id, name, quality, item_level, required_level nullable, inventory_type/slot, armor_type, weapon_type, icon_url, wowhead_url nullable, availability_status, verification_status. Único por fuente + versión + ID de origen. |
| ItemStat | item_id, stat_type, value, school opcional. Permite stats desconocidas y campos nuevos sin inventar valores. |
| ItemEffect | item_id, effect_type, description, spell_id nullable y datos estructurados opcionales. |
| Class / Specialization | catálogo propio con IDs estables; spec asociada a clase y active_from_version opcional. Evita fijar el sistema de talentos para siempre. |
| Faction | Alliance, Horde y opción neutral/ambas. Restricciones específicas se expresan aparte, sin supuestos globales. |
| ItemRestriction | item_id, tipo (clase, facción, raza, prof., reputación, quest, arma/armadura), valor requerido y fuente de verificación. |
| AcquisitionSource | método, NPC/quest/encuentro/receta/vendedor, zona, dificultad, cantidad/tasa nullable, notas y referencia. No registrar una tasa sin verificación. |
| ItemAcquisition | relación muchos-a-muchos entre objeto y fuente, con requisitos de disponibilidad/versión y estado de verificación. |
| RecommendationMethod | id, version, pesos/reglas y descripción legible. Inmutable una vez usada en publicación. |
| RecommendationSet | clase, spec, facción, intervalo de nivel, método, versión del juego, estado (draft/reviewed/published), responsable y fecha de revisión. |
| RecommendationEntry | set, slot, item, categoría, prioridad, explicación/evidencia y vigencia. |

Los 17 slots visibles serán un catálogo estable. Los dos anillos y abalorios se guardan como slots de equipo finger y trinket con hasta dos entradas; mano principal, mano secundaria y mano única usan tipo de arma y reglas de compatibilidad.

Los datos externos no se considerarán completos por defecto. required_level, stats, facción, restricciones y fuente aceptan unknown o ausencia nullable con razón/procedencia. Una ausencia no equivale a «sin restricción».

## 6. Estrategia de actualización y calidad

1. Mantener un registro de fuentes con URL, términos, atribución, campos permitidos, fecha de verificación, cobertura probada y contacto.
2. Ejecutar ingesta como tarea explícita (CLI/job), no en cada petición. Respetar paginación, ETag, caché, Retry-After y límites del proveedor.
3. Guardar proveedor/build/fecha y calcular diff de campos normalizados. Retener lo necesario para explicar procedencia sin publicar dumps brutos no autorizados.
4. Validar IDs, slots, tipos de stats, restricciones, rangos y relaciones. Ante diferencias, marcar needs_review; nunca sustituir por Era.
5. Revisar cambios por versión/build y aprobar publicación de nuevo catálogo. Mantener la versión anterior consultable para reproducibilidad.
6. Actualizar tras cambios de build y revisar semanalmente mientras Forever cambie con frecuencia. Alertar por proveedor caído, esquema roto, objetos retirados o cambios masivos.
7. Contrastar una muestra con tooltips/fuentes visibles del juego y revisión humana. Registrar discrepancias.

## 7. Roadmap por fases

Cada fase se revisará antes de iniciar la siguiente. Tests y automatización comienzan con la primera fase de código; no se ejecutan como parte de esta planificación.

1. **Validación de fuentes y alcance (antes del código).** Confirmar términos de TheWoWDB, probar cobertura real de campos y límites, revisar enlaces Wowhead y documentar una muestra de discrepancias. Definir fuente de obtención y significado de etiquetas BIS.
2. **Esqueleto técnico y decisiones.** Crear backend/frontend, configuración local, PostgreSQL/Alembic y contratos API; registrar ADR de fuente/modelo BIS.
3. **Catálogo vertical mínimo.** Ingestar muestra limitada y autorizada de objetos equipables de Forever, persistir procedencia y validar consulta y slots. Sin BIS masivo ni datos de Era como relleno.
4. **Motor de elegibilidad.** Implementar reglas duras (nivel, clase, facción, slot, restricciones y disponibilidad) con método versionado; devolver razones y estados desconocidos.
5. **Curación de una combinación.** Cubrir una clase/spec/facción y tramo de niveles pequeño con evidencia por recomendación y etiquetas acordadas.
6. **Planner web.** UI responsive con selección, slider 1–60 y representación de 17 slots conectada al endpoint. Estados vacíos/parciales y atribución visibles.
7. **Cobertura y operación.** Ampliar combinaciones, ingesta incremental, reportes de cambios, revisión editorial y publicación versionada.
8. **Lanzamiento.** Despliegue, observabilidad, política de actualización y atribuciones; revisar rendimiento y accesibilidad.

## 8. Riesgos y dependencias

- **Cobertura/frescura:** datos de terceros pueden omitir contenido no revelado, drops o restricciones. Mitigar con procedencia/build, estado desconocido y publicación gradual.
- **Cambios de Forever:** balance, talentos, clases por facción, objetos y fuentes pueden cambiar. Snapshots por build y método BIS versionado; no asumir invariancia de Era.
- **Derechos/condiciones:** datos, iconos, nombres y tooltips pueden tener términos distintos; APIs Blizzard/comunitarias tienen condiciones distintas. Registrar licencia por fuente, atribuir y evitar descargas públicas del dataset fuente. Este plan no es dictamen legal.
- **API Blizzard inestable/incompleta:** lo observado no es documentación oficial. No depender de endpoints no documentados; adoptar solo si se documenta y autoriza.
- **Enlaces Wowhead:** IDs/slugs parecidos pueden llevar a una variante incorrecta. Mapping explícito y verificación.
- **Significado de BIS al subir:** pesos varían por spec, talentos, estilo y esfuerzo de obtención. Método transparente, revisión y esfuerzo separado de potencia.
- **Fuentes de obtención:** drop chance y elegibilidad incompletos o variables. No inventar tasas ni accesos.
- **Combinatoria:** 9 clases × specs × 2 facciones × 60 niveles × versiones. Reglas reutilizables y publicación por tramos.
- **Dependencias:** PostgreSQL, Alembic/SQLAlchemy, FastAPI/Pydantic, React/Vite/Tailwind, Pytest/Vitest y cliente HTTP. Fijar versiones al iniciar Fase 2; no hace falta elegir cloud ahora.

## 9. Decisiones pendientes de revisión

- Confirmar TheWoWDB como fuente inicial preferida y aceptar atribución visible.
- Acordar criterio de BIS para niveles 1–60 y si Upgrade usa equipo actual o nivel anterior.
- Acordar cómo mostrar recomendaciones parciales cuando falte información.
- Confirmar prioridad de facción, disponibilidad por fase/build y tratamiento de objetos neutrales.

## Estado de ejecución

### Fase 1 — Validación de fuentes

Completada y aprobada con reservas. Hallazgos, cobertura, muestra y límites de TheWoWDB están en `docs/DATA_SOURCE_AUDIT.md`.

### Fase 2 — Base técnica

La implementación de la base técnica incluye el monorepo con FastAPI, contratos Pydantic v1, conexión SQLAlchemy/psycopg, Alembic y una migración inicial vacía; React/TypeScript/Vite/Tailwind con shell responsive y slider accesible 1–60; PostgreSQL Compose; pruebas y documentación PowerShell.

**Verificado el 7 de noviembre de 2026 (America/Bogota):** Docker Desktop 4.98.0 y Engine 29.9.2 estaban disponibles. `docker compose config --quiet` pasó. Se inició únicamente el servicio `db` de Compose, con imagen `postgres:17.6-alpine`; el contenedor `foreverbis-db-1` reportó `running` y healthcheck `healthy`, publicó `127.0.0.1:5432` y montó el volumen persistente `foreverbis_forever_bis_postgres_data` en `/var/lib/postgresql/data`. El inventario previo no mostró contenedores ni volúmenes; no se borró ni reinicializó un volumen existente.

Las variables de base configuradas en `.env`, Compose y `DATABASE_URL` coincidieron (el valor de la contraseña no se imprime). PostgreSQL aceptó conexiones; SQLAlchemy consultó la base `foreverbis`. Se aplicó la migración Alembic inicial y una consulta SQL confirmó que `alembic_version` contiene `20261107_0001`; es la única tabla pública, sin tablas de dominio.

FastAPI inició y `GET /api/v1/health` respondió `status: healthy`, `database: healthy`; el endpoint raíz devolvió metadatos. El frontend Vite respondió HTTP 200 y la API devolvió el encabezado CORS permitido para `http://localhost:5173`. Además de las pruebas frontend normales (que usan respuestas mockeadas), una prueba temporal ejecutó el cliente real `fetchHealth` contra FastAPI/PostgreSQL en ejecución y pasó; el archivo temporal se retiró después. No se completó una prueba end-to-end en navegador: Edge headless no produjo DOM y Chrome headless falló al inicializar GPU/sandbox en este entorno.

Pytest: 23 aprobadas. Vitest: 8 aprobadas. Ruff lint y formato, TypeScript y build de producción Vite pasaron. `.gitignore` excluye `.env` y `.env.*` excepto `.env.example`, entornos virtuales, `node_modules`, artefactos de build y cachés. No se hizo commit; Git aún no tiene commits y los archivos del proyecto aparecen sin seguimiento. Para el primer commit se recomienda incluir los archivos de fuente, documentación, pruebas, migraciones y `frontend/package-lock.json`, excluyendo secretos/configuración local y artefactos generados. La siguiente fase requiere aprobación explícita.

## Referencias consultadas

- [TheWoWDB — Developers / API, límites y términos](https://thewowdb.com/developers/)
- [TheWoWDB — About / origen de datos](https://thewowdb.com/about/)
- [Eternadex — base de objetos y metodología declarada](https://eternadex.com/en/datenbank/?m=finder)
- [Wowhead — Forever database](https://www.wowhead.com/forever/database)
- [Wowhead — FAQ](https://www.wowhead.com/faq)
- [Wowhead — tooltips](https://www.wowhead.com/classic/fr/tooltips)
- [Foro de Blizzard — observaciones comunitarias de la API Forever](https://us.forums.blizzard.com/en/blizzard/t/wow-forever-api-what-works-so-far-plus-a-ts-client/60334)
- [Blizzard — condiciones de uso de API para desarrolladores](https://www.blizzard.com/es-es/legal/a2989b50-5f16-43b1-abec-2ae17cc09dd6/condiciones-de-uso-de-las-api-para-desarrolladores-de-blizzard)


## Phase 3 — Catálogo de objetos Forever

Implementado y validado el 7 de noviembre de 2026 (America/Bogota), sin iniciar recomendaciones BIS:

- Se añadió el dominio SQLAlchemy para fuente, snapshot de versión/build, objeto, estadísticas, efectos, restricciones y problemas de calidad. Las migraciones nuevas son `20261107_0002` y `20261107_0003`; Alembic informa `20261107_0003 (head)` y `alembic check` confirmó que no hay diferencias pendientes. No se borraron ni reinicializaron datos o volúmenes.
- El adaptador usa únicamente las rutas documentadas de lista y detalle de objetos Forever de TheWoWDB, valida host/ruta, límites y esquemas; gestiona paginación, ETag/304, ritmo de solicitudes, 429 y fallos transitorios. El proveedor queda desacoplado de SQLAlchemy y FastAPI.
- La importación limita cada ejecución a 100 registros, por defecto no escribe, y requiere `--write` con confirmación o `--confirm-write`. Importación real acotada: 3 recuperados, 3 validados, 0 fallidos y 3 persistidos. Una segunda ejecución creó 0 y actualizó 3; no duplicó registros.
- En los tres objetos muestreados, `required_level` fue 1 en lista y null en detalle. Se dejó el campo null y se guardaron ambas observaciones como problema de calidad. Las listas vacías de estadísticas, efectos y restricciones de clase quedaron marcadas como no verificadas. Los tres objetos requieren revisión. El informe detallado está en `docs/DATA_QUALITY_REPORT.md`.
- Se guardaron tres enlaces Wowhead Forever mediante la lista explícita del informe de Fase 1, con coincidencia actual de ID, nombre y nivel de objeto; fuera de esos tres casos, la URL permanece null. No se hizo scraping ni se importó contenido protegido.
- API de catálogo, resumen y detalle implementadas; la interfaz React consume esas rutas y muestra búsqueda, filtros, paginación, detalle, estado de verificación, incertidumbre y atribución visible. La consulta en vivo del cliente frontend al resumen/listado/detalle devolvió registros del PostgreSQL activo; Vite sirvió la aplicación con HTTP 200. Las pruebas de componente usan datos mockeados. No se completó una prueba end-to-end de navegador.
- Verificaciones: Pytest 41 aprobadas (4 subtests); Vitest 10 aprobadas; Ruff lint y formato aprobados; TypeScript y build de producción aprobados; Compose configurado; PostgreSQL 17.6 reportó `healthy`; FastAPI health reportó aplicación y base `healthy`; migraciones y conexión SQLAlchemy confirmadas.
- Documentación de fuentes, modelo, importación y calidad añadida en `docs/DATA_SOURCES.md`, `docs/CATALOG_DATA_MODEL.md`, `docs/CATALOG_IMPORT.md` y `docs/DATA_QUALITY_REPORT.md`; instrucciones de README actualizadas.

**Alcance y limitación:** solo se importó una muestra acotada de tres objetos. Los hallazgos no representan cobertura total. La fuente resulta adecuada para el MVP de catálogo y pruebas técnicas, pero los registros actuales no bastan para establecer elegibilidad, restricciones completas, fuentes de obtención ni recomendaciones. Los términos requieren atribución visible y prohíben revender el dataset bruto; los términos de iconos no fueron verificados de forma independiente. No se implementaron cálculos BIS, puntuación, recomendaciones de subida ni listas por clase.


## Correccion de direccion de producto - prototipo frontend

La pagina principal es Gear Planner; Item Database permanece accesible como seccion secundaria. El prototipo implementa selectores de las nueve clases y sus especializaciones, faccion Alliance/Horde, progresion horizontal accesible para niveles 1-60 y la distribucion paper doll de 17 espacios. Cada espacio indica recomendacion no disponible y permite abrir registros de catalogo coincidentes; dichos registros se identifican como datos de proveedor, nunca como recomendaciones. El detalle reutiliza el catalogo existente.

La base observada sigue siendo de solo tres objetos marcados `needs_review`. No se inventaron objetos, iconos ni recomendaciones. No hay calculo BIS ni cambio de ingesta o base de datos. Las pruebas frontend pasaron: 16 pruebas; TypeScript y build de produccion tambien pasaron. La direccion corregida de producto se conserva: Gear Planner es la pagina principal y el catalogo es secundario.

## Fase 3.1 - auditoria de cobertura, proveedores y calidad

Completada el 7 de noviembre de 2026 (America/Bogota), con lectura de PostgreSQL y pruebas HTTP acotadas. El estado inicial se verifico antes de investigar: 3 items, todos `needs_review`, sin cambios en filas, migraciones ni volumen durante esta fase.

- La documentacion vigente de TheWoWDB confirma lista de items paginada (hasta 100 por pagina/200 paginas), detalle, busqueda por nombre y tooltip renderizado. No documenta filtros por slot, calidad o nivel ni relaciones de adquisicion. El importer toma IDs iniciales sin diversidad y la ejecucion por defecto (`per_page=100`) solo consulta una pagina; el limite duro por ejecucion sigue siendo 100.
- Dry-run de 10: 10 resumenes recuperados, 8 detalles validados, 2 detalles 404 (IDs 41,42), 0 persistidos. Los 8 objetos eran armor/weapons, pero solo cubrieron Main Hand, Two-Hand, Shirt, Legs y Feet; shirt no es un slot del planner. Sus arrays `stats`, `effects` y `classes` estaban vacios; `required_level` en detalle era null frente a valores 0/1 en lista. Se registraron 32 issues. La ejecucion de 100 no termino por socket read timeout y no produce conteo completo.
- Tooltip de ID 25 devolvio campos estructurados y HTML, pero stats vacias; el tooltip de ejemplo ID 12640 de la documentacion devolvio 404. La busqueda generica documentada `q=worn` no devolvio resultados agrupados; no se interpreta como ausencia del listado. No se infirieron stats ni fuentes a partir de campos vacios.
- Eternadex es una referencia visual potencial: declara stats desde datos del cliente Forever y fuentes desde atlas de mazmorras/base de misiones, con observaciones comunitarias para vendors/loot. No se encontro API publica de datos ni licencia explicita de reutilizacion de base completa. Wowhead Forever ofrece paginas, pero no se identifico API publica autorizada para ingesta. La revision de APIs oficiales de Blizzard no encontro un endpoint Forever de catalogo documentado.
- Los tres enlaces Wowhead guardados corresponden a verificaciones individuales previas. Esta revision reabrió los destinos: Forever de IDs 25 y 35 mostró nombres e item level coincidentes; la pagina de ID 36 mostró una pantalla anti-bot, por lo que no se repitió su comprobación. De los 8 detalles validos, 25,35,36 están en la allowlist previa; 37,38,39,40,43 siguen sin mapear. No se amplió la allowlist.
- Recomendacion: **estrategia hibrida**: TheWoWDB para registros basicos atribuidos, fuentes complementarias solo con permiso explicito y verificacion editorial por campo/build. No basta para un planner 1-60 de las nueve clases.
- Para iniciar un motor BIS faltan datos autorizados y versionados de stats y requisitos, restricciones clase/faccion/raza/armas, relaciones de obtencion y prerequisitos; resolucion de la contradiccion required_level; cobertura de slots/niveles, criterio explicable por spec y evidencia editorial. Ningun BIS, scoring, recomendacion ni contenido de planner fue implementado.

Los resultados reproducibles, matrices por nivel/slot, endpoint inventory, licencias y limitaciones se documentan en `docs/CATALOG_COVERAGE_AUDIT.md`, `docs/ITEM_STATISTICS_AUDIT.md`, `docs/ACQUISITION_SOURCES_AUDIT.md`, `docs/PROVIDER_COMPARISON.md`, `docs/LEVELING_COVERAGE_MATRIX.md`, `docs/DATA_SOURCES.md` y `docs/DATA_QUALITY_REPORT.md`.

**Decision de fase:** no declarar lista la implementacion de recomendaciones. La siguiente fase requiere aprobacion humana explicita y una decision sobre fuente autorizada complementaria y alcance inicial de cobertura.
