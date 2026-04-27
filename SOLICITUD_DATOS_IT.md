# Solicitud de Datos a IT — FPM Favarcia
**Fecha:** Abril 2026  
**Solicitante:** Mauricio Araya  
**Propósito:** Análisis estadístico de operaciones de bodega (FPM)

---

## Solicitud

Necesito un reporte de los **últimos 6 meses** con los siguientes datos adicionales a los que ya me proporcionaron:

---

## Hoja 1 — Pedidos (agregar columnas nuevas)

| Columna nueva | Por qué |
|---|---|
| **RUTA** | Separar rutas prioritarias (1 y 2) de secundarias |
| **CHEQUEADOR** | Cruzar errores de chequeo con quien chequeó |

Las demás columnas ya las tenemos: PEDIDO, ALISTADOR, NOMBRE, FECHA PEDIDO, FECHA FACTURA, INICIO ALISTO, FIN ALISTO, TIEMPO ALISTO, CANT_LINEAS, CANT_UNIDADES.

---

## Hoja 2 — Errores en alisto (cambio importante)

Actualmente los errores vienen como **totales acumulados por alistador sin fecha**.

Necesito **un registro por error** con:

| Columna | Estado |
|---|---|
| ALISTADOR | Ya existe |
| NOMBRE | Ya existe |
| CANT ERRORES FALTANTES | Ya existe |
| CANT ERRORES SOBRANTES | Ya existe |
| CANT ERRORES MERCADERÍA ERRONEA | Ya existe |
| **FECHA ALISTO** | CRÍTICO — falta en datos actuales |
| **NUMERO PEDIDO** | Nuevo — para cruzar con tabla de pedidos |

---

## Hoja 3 — Errores de chequeo (corrección importante)

La columna actual dice "ALISTADOR" pero debería ser el chequeador.

| Columna | Estado |
|---|---|
| **CHEQUEADOR** | Cambiar de ALISTADOR a CHEQUEADOR |
| NOMBRE | Ya existe |
| CANT ERRORES AL CLIENTE | Ya existe |
| FECHA | Ya existe |
| **NUMERO PEDIDO** | Nuevo — para cruzar con alistador |

---

## Dato adicional — Calendario de descargas (si existe)

Una tabla simple con:
- Fecha de descarga
- Hora de llegada del camión
- Cantidad de cajas/paletas

Permite correlacionar días de descarga con tiempos de alisto más altos.

---

## Resumen del pedido para IT

> *"Necesito un reporte de los últimos 6 meses. A los datos que ya me dieron necesito agregar:*
> *1. En pedidos: columna RUTA y columna CHEQUEADOR*
> *2. En errores de alisto: agregar FECHA ALISTO y NUMERO DE PEDIDO por cada registro individual (no totales acumulados)*
> *3. En errores de chequeo: cambiar columna ALISTADOR por CHEQUEADOR, agregar NUMERO DE PEDIDO*
> *4. Si existe: registro de fechas y horas de llegada de camiones de mercadería"*