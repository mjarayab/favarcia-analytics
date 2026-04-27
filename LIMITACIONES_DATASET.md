# Limitaciones del Dataset — FPM_Datos.xlsx
**Proyecto:** FPM — Favarcia Plan de Mejora  
**Fecha:** Abril 2026  
**Autor:** Mauricio Araya

---

## Resumen Ejecutivo

El dataset actual tiene limitaciones estructurales que afectan la validez de ciertos análisis. Estas limitaciones no invalidan el análisis — lo contextualizan. Documentarlas es parte del rigor metodológico del proyecto.

---

## Limitación 1 — FECHA PEDIDO con hora 00:00:00

**Qué es:**
La columna FECHA PEDIDO muestra `00:00:00` en muchos registros. Esto no es un error del sistema — es la hora en que el cliente generó la orden, que en muchos casos llega de noche o sin hora específica registrada por el sistema del cliente.

**Qué afecta:**
- **Cycle time inflado:** Pedidos con FECHA PEDIDO a medianoche tienen cycle times más largos de lo real porque el cálculo incluye las horas nocturnas antes de que la operación inicie.
- **Análisis de tiempo en cola sesgado:** El análisis actual filtra pedidos con hora=0 para calcular el tiempo en cola. Esto excluye pedidos válidos y subestima la muestra.
- **Hora de creación no confiable:** No se puede usar FECHA PEDIDO para análisis intra-día (¿a qué hora del día entran más pedidos?).

**Impacto en métricas:**
- Cycle time mediano (10.2h) puede estar sobreestimado
- Análisis de tiempo en cola basado en solo 8,330 pedidos de 31,415 totales

**Solución pendiente:**
Solicitar a IT que incluya la hora real de ingreso del pedido al sistema WMS, no la hora del pedido del cliente.

---

## Limitación 2 — TIEMPO ALISTO = 0 (52.1% de pedidos)

**Qué es:**
El 52.1% de los pedidos tienen TIEMPO ALISTO = 0. Esto significa que el alistador trabajó el pedido **antes de abrirlo** en el WMS y lo abrió y cerró al final. El sistema registra tiempo = 0 porque no hubo tiempo transcurrido entre apertura y cierre.

**Qué afecta:**
- Las métricas de tiempo (mediana, Cpk, fricción) solo son válidas para el 47.9% de pedidos con tiempo > 0.
- El volumen real de trabajo es el 100% — pero el sistema "ve" solo el 47.9%.
- Alistadores que usan esta práctica más frecuentemente (ej: EM564 con 93.2%) tienen métricas de tiempo artificialmente perfectas.

**Impacto en métricas:**
- Ranking de velocidad completamente distorsionado para alistadores con alto % de tiempo=0
- Cpk calculado sobre muestra sesgada (los pedidos con tiempo=0 no son una muestra aleatoria)

**Solución pendiente:**
Política operacional de abrir el pedido antes de empezar a alistarlo. Requiere cambio de cultura y posiblemente soporte del WMS (alerta si se cierra sin tiempo registrado).

---

## Limitación 3 — INICIO ALISTO ≠ Inicio real del trabajo

**Qué es:**
El alistador puede:
- Abrir el pedido y dejarlo abierto durante el almuerzo (1.5h), café (15 min) o pausas no programadas
- Abrir el pedido mucho después de empezar a trabajarlo
- Dejar el pedido abierto de un día para otro si se olvidó cerrarlo

**Qué afecta:**
- Pedidos con tiempos extremos (>240 min) son en su mayoría pedidos con pausas incluidas, no pedidos realmente lentos
- La mediana de 80s/línea está inflada por estos casos
- Imposible distinguir tiempo productivo de tiempo de pausa con los datos actuales

**Casos identificados en los datos:**
- Pedidos de 1-2 líneas con 40-75 minutos → casi certeza de pausa o agrupamiento
- Pedidos con INICIO ALISTO a hora normal pero FIN ALISTO al día siguiente → pedido olvidado
- El alistador EM047 tiene 10 pedidos en su top fricción que son todos de 1-2 líneas con tiempos de 39-211 minutos → ruido de datos, no fricción real

**Solución pendiente:**
El WMS debería implementar función de pausa/reanudación. Solicitar a IT en próxima versión.

---

## Limitación 4 — Ventanas de café no capturadas

**Qué es:**
Dos pausas de café por turno:
- Turno A: 9:00am y 3:00pm (15 min cada una)
- Turno B: 9:15am y 3:15pm (15 min cada una)

Pedidos abiertos antes de estas horas y cerrados después incluyen hasta 15 minutos de pausa en el tiempo registrado.

**Qué afecta:**
- Pedidos que cruzan ventanas de café tienen tiempos inflados hasta 15 minutos
- Afecta especialmente pedidos medianos (20-40 líneas) que toman exactamente ese tiempo

**Solución pendiente:**
Mismo que Limitación 3 — función de pausa en WMS.

---

## Limitación 5 — Errores de alisto sin fecha por registro

**Qué es:**
La hoja de errores de alisto contiene totales acumulados por alistador, no registros individuales con fecha. La mayoría de valores son 0 porque el WMS recién comenzó a registrar errores.

**Qué afecta:**
- No es posible analizar tendencias de errores en el tiempo
- No se pueden correlacionar errores con períodos específicos (temporada alta vs normal)
- Con solo 2 errores registrados en toda la operación, el análisis estadístico no es válido

**Solución pendiente:**
Solicitar a IT datos de errores con fecha por registro individual y número de pedido (incluido en SOLICITUD_DATOS_IT.md).

---

## Limitación 6 — Errores de chequeo ≠ Errores de alisto

**Qué es:**
La hoja de errores de chequeo registra los errores del **chequeador**, no del alistador. La columna se llama ALISTADOR pero contiene el código del empleado que chequeó el pedido.

Algunos alistadores también hacen chequeo (ej: Ismael/EM239). Sus errores en esta hoja corresponden a su función de chequeo, no de picking.

**Qué afecta:**
- No es posible cruzar errores de chequeo con desempeño de alisto
- El análisis de correlación errores/volumen no es válido con estos datos
- Para el análisis correcto se necesita la columna CHEQUEADOR separada de ALISTADOR

**Solución pendiente:**
Incluido en SOLICITUD_DATOS_IT.md — solicitar columna CHEQUEADOR en hoja de pedidos y corregir nombre en hoja de errores de chequeo.

---

## Limitación 7 — Pedidos partidos al almuerzo

**Qué es:**
Cuando un alistador no termina un pedido antes del almuerzo, lo cierra y otro alistador lo continúa. La segunda parte del trabajo no se registra bajo ningún alistador — es trabajo invisible al sistema.

**Qué afecta:**
- Algunos pedidos tienen menos líneas registradas de las reales
- El tiempo por línea de la primera parte puede parecer más alto (las líneas fáciles se hacen primero)

**Solución pendiente:**
No tiene solución con el sistema actual. Requiere cambio de proceso operacional.

---

## Limitación 8 — Ayuda en pedidos grandes no registrada

**Qué es:**
Cuando un pedido es muy grande se envían otros alistadores a ayudar. El tiempo se reduce por la ayuda pero el sistema registra todo el trabajo bajo quien abrió el pedido.

**Qué afecta:**
- El tiempo/línea del pedido se ve bajo (bueno) para quien lo abrió
- El trabajo de los alistadores que ayudaron es completamente invisible
- No hay forma de saber cuántos pedidos en el dataset tuvieron ayuda

**Solución pendiente:**
Solicitar a IT campo de alistadores participantes por pedido en próxima versión del WMS.

---

## Resumen del Impacto

| Limitación | Impacto en Cpk | Impacto en Ranking | Impacto en Fricción |
|---|---|---|---|
| FECHA PEDIDO 00:00 | Bajo | Ninguno | Ninguno |
| Tiempo = 0 (52.1%) | Alto | Alto | Alto |
| Pausas no capturadas | Moderado | Moderado | Alto |
| Ventanas de café | Bajo | Bajo | Bajo |
| Errores sin fecha | N/A | N/A | N/A |
| Errores chequeo/alisto | N/A | N/A | N/A |
| Pedidos partidos | Bajo | Bajo | Bajo |
| Ayuda no registrada | Bajo | Bajo | Bajo |

---

## Conclusión

A pesar de estas limitaciones, el análisis es válido para demostrar que:

1. **El sistema de medición actual no puede evaluar desempeño individual con justicia** — las limitaciones 2, 3 y 4 hacen imposible comparar alistadores directamente.
2. **El 30.6% de fricción es una subestimación** — los pedidos con tiempo=0 (52.1%) no están en el cálculo. Si todos tuvieran tiempo registrado, la fricción real podría ser mayor.
3. **El Cpk de 0.03 es representativo** — aunque calculado sobre muestra sesgada, el proceso claramente es incapaz de cumplir la meta de 60s/línea de forma consistente.
4. **El volumen real es mayor al visible** — el trabajo de la operación es 2x lo que el sistema registra.

---

*FPM — Favarcia Plan de Mejora | Mauricio Araya | Abril 2026*