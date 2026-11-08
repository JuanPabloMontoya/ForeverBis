# Comparación de proveedores Forever: Wowhead y TheWoWDB

**Fecha de consulta:** 7 de noviembre de 2026. Esta comparación se limita a Wowhead Forever y TheWoWDB Forever.

## Matriz de cobertura observada

Estados: **Verificado**, **Parcial**, **No disponible**, **No comprobado**. “No disponible” se refiere a la interfaz/documentación revisada; no demuestra que el dato no exista en el juego.

| Campo | Wowhead Forever | TheWoWDB Forever |
|---|---|---|
| Item ID | Verificado: página por ID en namespace Forever. Revisados 25, 35 y 36. | Verificado: ID y version=forever en resumen/detalle. |
| Nombre | Verificado en páginas y resultados de búsqueda. | Verificado en resumen/detalle; importador compara ambos. |
| Icono | Parcial: icono visible y algunos Quick Facts muestran nombre del icono; no se verificó autorización para copiar/rehostear. | Parcial: icon_url existe; presente en las tres filas actuales. Reutilización del asset separada no verificada. |
| Calidad | Parcial: color/estilo visual; extracción de calidad normalizada no se validó en la muestra consultada. | Verificado como campo API; muestra local common. Cobertura de valores no medida. |
| Slot | Verificado en páginas: Main Hand, Two-Hand, Head, Waist, Feet, etc. | Parcial: campo slot; primera muestra limitada a Main Hand/Two-Hand/Shirt/Legs/Feet. |
| Nivel requerido | Parcial: visible en varias páginas de niveles 28–55; no aparece en las páginas revisadas de algunos objetos iniciales. Omisión no implica nivel 0. | Parcial: lista/detail discrepan (lista 0/1, detail null) en muestra; valor queda desconocido. |
| Estadísticas | Parcial: algunos items tienen valores, otros indican que quedan ocultos hasta descubrirlos. | Parcial: stats[] existe, pero vacío en los 8 detalles válidos de la muestra documentada. |
| Daño y velocidad | Parcial: visibles en las páginas de armas revisadas; no se comparó una muestra amplia contra el juego. | Parcial: objetos Weapon exponen damage_min/max, dps y speed; no se verificó cobertura ni valores en juego. |
| Armadura | Parcial: visible en páginas de armor (ej. casco con 288 Armor). | Parcial: campo armor existe; muestra de armaduras no expuso claves pobladas. |
| Restricción de clase | Parcial: item de ejemplo declara Classes: Shaman; no se probó exhaustividad. | Parcial: classes[] existe, pero vacío en la muestra; no prueba uso irrestricto. |
| Restricción de raza | No comprobado. | No disponible en el contrato/documentación revisados. |
| Restricción de facción | Parcial: páginas/listados pueden mostrar Side o facción de vendedor; no se verificó un caso de item bloqueado por facción. | No disponible como restricción; faction_prices son precios de mercado y no elegibilidad. |
| Fuente de obtención | Parcial: páginas muestran NPC/drop, vendor, quest, crafted en ejemplos; cobertura y confianza varían por entrada. | No disponible como relación de item en la API documentada. |
| NPC / Quest / Vendor | Parcial: páginas concretas muestran NPC, vendor y fuentes; no se midió completitud. | Parcial solo como registros separados de NPC/quest; no se documentó relación item-to-NPC/quest/vendor. |
| Profesión requerida | Parcial: patrones muestran profesión, habilidad y materiales en ejemplos. | No disponible como relación de receta/item documentada. |
| Build de referencia | Parcial: algunas páginas muestran New in Forever o Added in patch 1.60.1; no un build cliente por registro. | Verificado cuando la respuesta lo incluye; muestra wow_classic_beta-1.60.1.70532. |
| Consulta automatizable | No disponible para ingesta autorizada según términos revisados. Hay páginas/manual, script de tooltip y documentación genérica de XML, pero no contrato Forever de extracción; términos restringen agentes/crawlers/descargas. | Verificado: API pública JSON documentada, paginación y q por nombre. En esta sesión, solicitudes de 30 y refresco pequeño expiraron. |
| Condiciones de reutilización | No disponible para copiar/almacenar dataset. Términos prohíben descargas automatizadas por agentes/crawlers y reservan derechos de los materiales; el script de tooltip sí está documentado para presentación. | Verificado: uso gratuito incluido comercial, con atribución visible; prohibida reventa del dataset bruto. Derechos de iconos no verificados. |

## Diferencia de uso

Wowhead ofrece la interfaz de lectura más rica para un investigador: buscador por slot, franjas de nivel, clase/spec y fuentes, además de páginas con stats, requisitos, armor, weapon data y algunas relaciones de obtención. La información no está completa para cada item y algunos datos permanecen ocultos hasta que son descubiertos. Sus términos públicos no habilitan una ingesta automatizada local en los mecanismos revisados.

TheWoWDB ofrece un contrato JSON y condiciones claras para mostrar registros con atribución, lo que lo hace apropiado como proveedor automatizable de identidades/build/campos estructurales. La muestra real es demasiado estrecha para usarse como catálogo de progresión: required_level está en conflicto; stats/effects/classes están vacíos; adquisición no está vinculada al item; el importador toma IDs iniciales y una muestra de 30 no completó por timeout.

No combinar automáticamente campos solo porque IDs coincidan. Contrastar por Forever URL, nombre, tipo/slot, build e identidad del item, y registrar la evidencia por campo. No transferir a Forever datos de Classic tradicional.

## Recomendación

**Alternativa C, con alcance restringido:** utilizar TheWoWDB para el registro local automatizado de los campos que su API sí expone, manteniendo build, incertidumbre y atribución; usar Wowhead solo como referencia manual y enlace externo a páginas Forever verificadas. No importar ni cachear desde Wowhead sin permiso escrito. No mezclar un valor Wowhead con un registro TheWoWDB sin comprobación individual.

Esta combinación todavía **no permite un catálogo suficientemente confiable** para Gear Planner 1–60 de nueve clases: el acceso automatizable de TheWoWDB no demuestra requisitos, stats y restricciones completos, y Wowhead no habilita el copiado automatizado necesario para cubrir localmente los huecos. La siguiente fase propuesta es una evaluación/solicitud de permiso de datos a Wowhead o una verificación editorial de un alcance pequeño usando páginas públicas; en paralelo, esperar disponibilidad de TheWoWDB y reproducir una muestra diversa de 30 objetos antes de decidir sobre cualquier ingeniería de proveedor. Esta es una propuesta de investigación, no una autorización de implementación.

## Fuentes revisadas

- [TheWoWDB Developers](https://thewowdb.com/developers/)
- [Forever Item Finder](https://www.wowhead.com/forever/items/finder)
- [Wowhead Forever Database](https://www.wowhead.com/forever/database)
- [Wowhead Tooltips / XML information](https://www.wowhead.com/tooltips)
- [Wowhead ToS (Fanbyte/ZAM)](https://corp.fanbyte.com/legal/terms?zaf_referer=https://www.wowhead.com/)
- Ejemplos: [Worn Shortsword 25](https://www.wowhead.com/forever/item=25/worn-shortsword), [Bent Staff 35](https://www.wowhead.com/forever/item=35/bent-staff), [Premier Mail Helm 272486](https://www.wowhead.com/forever/item=272486/premier-mail-helm), [Mender's Mail Boots pattern 252899](https://www.wowhead.com/forever/item=252899/pattern-menders-mail-boots).
