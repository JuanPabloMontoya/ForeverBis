# Auditoría de TheWoWDB — WoW Forever API

**Consulta:** 7 de noviembre de 2026. API base documentada: `https://thewowdb.com/api/v1/`.

## Endpoints documentados

La documentación oficial de TheWoWDB describe una API JSON pública sin clave:

| Ruta | Función | Hallazgos |
|---|---|---|
| `GET /api/v1/forever/item/?page=&per_page=&q=` | Listado de objetos Forever. | `per_page` de 1 a 100, `page` de 1 a 200; `q` es coincidencia de nombre de hasta 64 caracteres. Respuestas indican `has_more`, pueden incluir `links.next`; `total` puede omitirse en listados grandes. No se documentan filtros por slot, rareza, nivel o fuente. |
| `GET /api/v1/forever/item/{id}` | Detalle de un objeto. | Campos de versión/build, identidad, calidad, niveles, item type/subtype, slot, armadura, arma, stats, effects, class restriction, icon URL, links y attribution. Otros campos observados incluyen binding, sockets, vendor sell price y faction market prices. No se documenta relación de drops/adquisición. |
| `GET /api/v1/forever/search/?q=` | Unos pocos resultados cruzados entre tipos. | No es un índice completo por categoría. No documenta filtros de equipo. Una consulta real `q=worn` devolvió cero grupos; no se tomó como prueba de ausencia en el endpoint de lista. |
| `GET /api/v1/tooltip/forever/item/{id}` | HTML de tooltip y campos planos. | Una consulta real del ID 25 devolvió HTML y campos estructurados; stats seguían vacías. El ejemplo de documentación ID 12640 devolvió 404 en Forever al consultarse. El adaptador actual no consume tooltip y no ingiere HTML. |
| `GET /api/v1/forever/quest/{id}`, `/npc/{id}` y listas paginadas | Registros generales de quests y NPCs. | Existen como entidades separadas, pero el detalle de item no documenta un grafo que enlace item con quest, jefe, vendedor o botín. No se deduce relación por IDs o nombres. |

## Resultado de solicitudes y muestra

### Evidencia existente y reproducible de 10 objetos

La última ejecución completa de dry-run documentada en [DATA_QUALITY_REPORT.md](DATA_QUALITY_REPORT.md) recuperó 10 resúmenes: 8 detalles válidos, dos 404 (IDs 41 y 42), cero persistidos y 32 incidencias de calidad. Build observado: `wow_classic_beta-1.60.1.70532`. Los 8 detalles eran armaduras/armas y cubrían `Main Hand`, `Two-Hand`, `Shirt`, `Legs` y `Feet`. Los objetos válidos tenían `stats=[]`, `effects=[]`, `classes=[]`; detail `required_level` null frente a valores 0/1 del listado. Las armas exponían claves de daño mínimo/máximo, DPS y velocidad; no se contrastaron sus valores en juego. Las filas de pantalón/botas no tenían claves pobladas en el objeto `armor`.

Los tres items que sí están almacenados (25 Worn Shortsword, 35 Bent Staff, 36 Worn Mace) conservan icon URL, item level 2, calidad common, el slot indicado y `required_level=NULL`; todos siguen `needs_review`. Consulta read-only de PostgreSQL en esta fase: 3 filas, sin cambios.

### Intento de 30 objetos en esta fase

Se intentó el endpoint de lista con `per_page=30`, luego el CLI con `--limit 30`, y de nuevo con tres páginas de 10 (`--per-page 10`). Las solicitudes expiraron por timeout antes de obtener un informe completo. Se intentó además una lectura de lista pequeña y tres detalles almacenados; los cuatro requests expiraron. El adaptador/CLI tampoco convierte el `TimeoutError` de socket en un error reintentable consistente. Ninguna prueba escribió a PostgreSQL.

Por ello **no se afirma haber validado 30 objetos**. El límite práctico de esta sesión fue un conjunto previo de 10 resúmenes/8 detalles. El contrato API permite 30, pero las consultas actuales no resultaron operativamente disponibles; no se forzó una importación ni se aumentó la carga. La muestra existente no alcanza la diversidad pedida (slots, bandas de nivel y campos poblados).

## Matriz de campos

Los estados distinguen campos definidos en el contrato de datos realmente poblados y verificados. Array vacío o campo omitido no demuestra ausencia de una propiedad del juego.

| Campo | Estado | Evidencia de TheWoWDB Forever |
|---|---|---|
| Item ID | Verificado | IDs positivos y `version=forever`; item IDs descritos como IDs del cliente beta. |
| Nombre | Verificado | Presente en lista y detalle; el normalizador comprueba igualdad. |
| Icono | Parcial | `icon_url` figura en detalle/tooltips; los tres registros locales tienen URL. No se verificó permiso separado para rehosting de iconos. |
| Calidad | Verificado | Campo `quality` en detalle; muestra almacenada common. No se midió cobertura de valores. |
| Slot/tipo | Parcial | `slot`, `item_type`, `item_subtype` disponibles; primeros 8 detalles cubrieron 5 etiquetas, pero no equipamiento diverso. |
| Required level | Parcial | Campo en lista y detalle, pero discrepancias persistentes (lista 0/1, detalle null). No elegir un lado como verdad. |
| Item level | Verificado | Campo en lista/detalle; 1–2 en los primeros 8 detalles. |
| Estadísticas | Parcial | `stats[]` existe, pero fue vacío en los 8 detalles. Vocabulario/valores no verificados. |
| Efectos/procs | Parcial | `effects[]` existe, pero vacío en los 8 detalles; semántica de vacío desconocida. |
| Daño/velocidad | Parcial | En los objetos Weapon de la muestra se exponen claves `damage_min`, `damage_max`, `dps`, `speed`; cobertura/valores no se contrastaron. |
| Armadura | Parcial | `armor` existe, pero no mostró claves en los detalles de armadura muestreados. |
| Restricción de clase | Parcial | `classes[]` existe, vacío en los 8 detalles; no significa unrestricted. |
| Restricción de raza/facción | No disponible | No se documenta campo de elegibilidad. `faction_prices` es mercado, no una restricción. |
| Fuentes de obtención | No disponible | No hay relación source/drop en item detail/list documentados. `vendor_sell` es valor de venta, no ubicación de vendedor. |
| NPC/quest/vendor/profesión | Parcial | NPCs y quests son recursos independientes, sin enlace documentado desde item; no hay item-to-recipe/loot relation documentada. |
| Build | Verificado | Build incluida en list/detail cuando existe; muestra `wow_classic_beta-1.60.1.70532`. Build no garantiza que los campos estén completos. |
| Consulta automatizada | Verificado | API GET pública, sin clave; paginación y búsqueda por nombre documentadas. La sesión tuvo timeouts. |
| Condiciones de uso | Verificado | Uso gratuito comercial/no comercial con enlace visible a TheWoWDB o página de registro en cada presentación; no revender datos brutos. No se verificó licencia separada de iconos. |

## Cache, límites y mantenimiento

La documentación describe respuestas cacheables por una hora, tooltips por cinco minutos, ETag/304, `Retry-After` en 429, burst 120 y reposición a 2 requests/segundo por worker. El adaptador actual valida host y rutas Forever item; pacea ~0,51 s; usa caché ETag solo en memoria (TTL fijo una hora) y reintenta 429/5xx/`URLError`, pero los `TimeoutError` observados escapan sin completar importación. El techo de 200 páginas limita el recorrido de lista; el importador además limita cada ejecución a 100 y por defecto pide una página de 100, por lo que no constituye ingesta completa ni muestra diversa.

La documentación no promete una frecuencia de actualización de los datos/builds; cada respuesta puede incluir un build, pero ausencia del build o falta de timestamp de campo deja la frescura por confirmar. La página dice que cambios incompatibles de API se publicarán como `/api/v2/`, pero otros cambios de contenido/esquema siguen siendo un riesgo y requieren monitoreo.

Los términos están publicados en [developers](https://thewowdb.com/developers/). Mantener atribución visible y no ofrecer exportación del dataset bruto. Mostrar URL de fuente junto a los registros. Términos de imágenes requieren revisión independiente antes de descargar/proxy.

## Conclusión

TheWoWDB resulta útil para una API inicial de identidades, build y estructura básica de objetos y permite uso con atribución. Esta muestra no respalda una progresión fiable: requisitos en conflicto, listas de stats/efectos/restricciones vacías, falta de relaciones de adquisición y problemas de timeout. No alcanza para elegir candidatos usables por clase y nivel, ni para cubrir 17 slots de 1 a 60.

## Referencias

- [Documentación oficial TheWoWDB Developers](https://thewowdb.com/developers/)
- [TheWoWDB Forever database](https://thewowdb.com/wow-forever/items/)
- [DATA_QUALITY_REPORT.md](DATA_QUALITY_REPORT.md)
- [CATALOG_COVERAGE_AUDIT.md](CATALOG_COVERAGE_AUDIT.md)
