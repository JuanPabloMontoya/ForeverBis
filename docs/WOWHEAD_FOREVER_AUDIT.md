# Auditoría de Wowhead — World of Warcraft: Forever

**Consulta:** 7 de noviembre de 2026. Se revisaron páginas públicas e interfaces documentadas; no se automatizó la descarga de páginas ni feeds.

## Información visible en Wowhead Forever

El namespace Forever tiene base de objetos, páginas por ID y un Item Finder que muestra filtros para nivel (rangos), fuente, slot y clase/especialización. La página de un objeto puede mostrar nombre, item level, required level, tipo/slot, calidad visual, estadísticas, armadura, daño/velocidad, restricciones de clase y fuentes relacionadas.

Ejemplos públicos revisados:

| Página | Campos visibles en la consulta |
|---|---|
| [Worn Shortsword, ID 25](https://www.wowhead.com/forever/item=25/worn-shortsword) | Forever ID/nombre; item level 2; Main Hand Sword; daño y velocidad; localización de vendedor. La página consultada no mostraba una línea `Requires Level`; eso no prueba que no exista requisito. |
| [Bent Staff, ID 35](https://www.wowhead.com/forever/item=35/bent-staff) | Forever ID/nombre; item level 2; Two-Hand Staff; daño y velocidad; vendedor. |
| [Worn Mace, ID 36](https://www.wowhead.com/forever/item=36/worn-mace) | La búsqueda pública de Wowhead mostró Forever, item level 2, Main Hand Mace y daño/velocidad. La página directa presentó protección anti-bot en esta sesión, por lo que no se inspeccionó íntegra. |
| [Premier Mail Helm, ID 272486](https://www.wowhead.com/forever/item=272486/premier-mail-helm) | Item level 60, 288 armor, +Stamina/+Intellect, clase Shaman, required level 55 y efectos de equipamiento. |
| [Pattern: Mender’s Mail Boots, ID 252899](https://www.wowhead.com/forever/item=252899/pattern-menders-mail-boots) | Patrón de Leatherworking, materiales, botas de mail, armor y stats, required level 40, NPC Arcanist Doan y drop chance mostrada por Wowhead. Es una página con origen compuesto: receta y objeto creado. |
| [Tome of Dalaran, ID 275989](https://www.wowhead.com/forever/item=275989/tome-of-dalaran) | La página y sus aportes de comunidad muestran incertidumbre explícita sobre el uso/requisitos; el tooltip puede faltar. La propia página pide contribuciones para completar datos que permanecen ocultos hasta ser descubiertos. |

Las fuentes visibles no tienen un grado uniforme de certeza: la página del patrón, por ejemplo, presenta material de fuente y una tasa observada, mientras que la página del Tome contiene comentarios de jugadores y partes especulativas. La interfaz pública no garantiza que cada campo tenga igual procedencia o verificación. No se tomaron comentarios especulativos como hechos.

## Evaluación de campos

| Campo | Estado | Evidencia y límite |
|---|---|---|
| Item ID y URL Forever | Verificado | IDs en la ruta `/forever/item={id}/...`; 25, 35 y 36 corresponden a los tres nombres persistidos en Forever. No generalizar equivalencia a otras versiones. |
| Nombre | Verificado | Visible en las páginas consultadas. |
| Icono | Parcial | Las páginas muestran iconografía y Quick Facts pueden exponer nombre de icono; no se comprobó una exportación de assets ni derecho de rehosting. |
| Calidad | Parcial | UI/tooltip usa presentación de calidad; no se registró una columna de rareza verificable en los ejemplos seleccionados. El color visual no es una licencia ni prueba de exportabilidad. |
| Slot/tipo | Verificado | Ejemplos explícitos: Main Hand sword/mace, Two-Hand staff, Head Mail y Feet Mail. |
| Required level | Parcial | Visible en objetos de nivel alto y medio (por ejemplo 40, 42, 50, 55); ausente en páginas revisadas de objetos de inicio. Campo omitido no se interpreta como “sin requisito”. |
| Item level | Verificado | Visible en ejemplos de nivel bajo a alto. No equivale al required level del personaje. |
| Estadísticas | Parcial | Algunas páginas muestran valores concretos y otras indican que los stats están ocultos hasta descubrirse. Cobertura no completa por definición de la fuente. |
| Daño/velocidad | Parcial | Visibles en páginas de armas muestreadas; no se comprobó consistencia para todas las armas/builds. |
| Armadura | Parcial | Valor visible en el ejemplo de casco y en otras páginas; no se midió integridad por tipo/slot. |
| Restricción de clase | Parcial | El casco de ejemplo declara `Classes: Shaman`. No se verificó que las listas de restricciones estén completas. |
| Restricción de raza | No comprobado | No se verificó un caso representativo con restricción de raza en Forever. |
| Restricción de facción | Parcial | Finder ofrece clase y filtros; páginas pueden presentar `Side` y reacción de vendedores. No se validó un objeto ligado a facción ni exhaustividad de ese dato. |
| NPC/drop | Parcial | La receta de Mender’s Mail Boots muestra Arcanist Doan y una tasa; no se validó metodología ni completitud de tasas. |
| Quest/recompensa | Parcial | Finder expone fuente `Quest`; no se verificó aquí una página con cadena y prerrequisitos completos. |
| Vendedor | Parcial | Páginas de items de inicio muestran vendedor/localización; el ejemplo de patrón identifica vendedores por facción. Cobertura de stock/prerrequisitos no medida. |
| Profesión/receta | Parcial | El patrón muestra profesión, nivel de habilidad y materiales; no se verificó el grafo completo de recetas/orígenes. |
| Build exacto | Parcial | Algunas páginas indican `Added in patch 1.60.1` o `New in Forever`; no se encontró un identificador de build cliente para cada snapshot. |

## Automatización, consulta y términos

- La página oficial de tooltips documenta un JavaScript para mostrar tooltips de enlaces y describe feeds XML de items por ID/nombre. El ejemplo de XML usa la ruta genérica `/item=...&xml`; la documentación revisada no especifica un contrato de exportación Forever por build, paginación, límites ni una licencia de datos para cargar una copia local.
- El Item Finder y páginas individuales son consultables manualmente en un navegador. El script oficial de tooltips está documentado para presentación en otro sitio; no equivale a permiso para extraer, guardar o republicar el dataset.
- Los términos de Fanbyte/ZAM enlazados desde la página legal de Wowhead prohíben usar software/agentes/crawlers para buscar o descargar contenido, así como el datamining y la creación de derivados, salvo herramientas/búsquedas ofrecidas por ZAM o navegadores web disponibles. Los materiales pertenecen a ZAM o sus licenciantes, salvo autorización expresa. Por lo tanto, esta auditoría no automatizó XML, APIs privadas, páginas, scripts ni otros endpoints. Se necesitaría autorización escrita para una ingesta automatizada/almacenamiento local.
- Wowhead dice que las aportaciones del cliente pasan por revisión y su aceptación suele tardar alrededor de una semana, pero varía. No hay un SLA público de actualización Forever por objeto.
- Las páginas pueden mostrar notas como `Added in patch 1.60.1`, pero no un timestamp de captura ni un build cliente uniforme por objeto. En los resultados consultados, la frescura de indexación variaba; la página visible no demuestra que el dato corresponda a la versión del servidor en el día de consulta.

**Conclusión:** Wowhead ofrece la evidencia pública más rica en páginas consultables, incluidos stats, restricciones y fuentes para algunos objetos Forever. Sin embargo, su propio aviso de datos ocultos y las restricciones de descarga hacen que no sea una fuente autorizada para poblar automáticamente un catálogo local bajo la evidencia pública revisada. Puede usarse para verificación manual y enlaces externos.

## Referencias

- [Forever Item Finder](https://www.wowhead.com/forever/items/finder)
- [Base de datos Forever](https://www.wowhead.com/forever/database)
- [Tooltips, XML y ejemplos](https://www.wowhead.com/tooltips)
- [FAQ de Wowhead: actualización por aportes](https://www.wowhead.com/faq)
- [Términos de servicio de Fanbyte/ZAM](https://corp.fanbyte.com/legal/terms?zaf_referer=https://www.wowhead.com/)
