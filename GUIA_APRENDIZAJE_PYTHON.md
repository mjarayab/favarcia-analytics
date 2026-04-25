# 📚 Guía de Aprendizaje — Favarcia Analytics
### Explicación de conceptos y código Python usado en el proyecto

---

## 🗂️ Índice

1. [Conceptos fundamentales de Python](#1-conceptos-fundamentales)
2. [Pandas — trabajar con tablas de datos](#2-pandas)
3. [NumPy — cálculos matemáticos](#3-numpy)
4. [Matplotlib y Seaborn — gráficas](#4-visualización)
5. [Estadística aplicada al proyecto](#5-estadística)
6. [Patrones de código que se repiten](#6-patrones-comunes)
7. [Glosario rápido](#7-glosario)

---

## 1. Conceptos Fundamentales

### Variables y tipos de datos
```python
# String (texto)
picker_id = "EM047"

# Integer (número entero)
total_pedidos = 2059

# Float (número decimal)
mediana_seg = 130.5

# Boolean (verdadero/falso)
tiene_tiempo = True

# Lista (colección ordenada)
codigos = ["EM047", "EM452", "EM564"]

# Diccionario (pares clave:valor — como un Excel con encabezados)
roles_apoyo = {
    'EM039': 'Chequeador',
    'EM560': 'Gondolero',
}
```

---

### Funciones — def
Una función es un bloque de código reutilizable. Como una macro en Excel.

```python
# Definir una función
def calcular_seg_por_linea(tiempo_minutos, cant_lineas):
    """
    El texto entre triple comilla es el docstring —
    explica qué hace la función. Buena práctica siempre.
    """
    if cant_lineas == 0:
        return 0  # evitar división por cero
    return (tiempo_minutos * 60) / cant_lineas

# Llamar la función
resultado = calcular_seg_por_linea(14, 20)
print(resultado)  # → 42.0
```

**Por qué usamos funciones:**
- Evitan repetir el mismo código
- Hacen el código más fácil de leer
- Si hay un error, se corrige en un solo lugar

---

### Condicionales — if / elif / else
```python
seg = 130

if seg < 60:
    print("Dentro de meta")
elif seg < 120:
    print("Moderado")
else:
    print("Alta fricción")
```

---

### Loops — for
Ejecuta código repetidamente para cada elemento de una lista.
Equivale a "arrastrar una fórmula" en Excel, pero más poderoso.

```python
pickers = ["EM047", "EM452", "EM564"]

for picker in pickers:
    print(f"Procesando: {picker}")
    # aquí iría el análisis de cada picker
```

---

### f-strings — formatear texto con variables
```python
nombre = "Mauricio"
pedidos = 2059
mediana = 130.0

# El f antes de las comillas permite insertar variables con {}
print(f"Alistador: {nombre}")
print(f"Pedidos: {pedidos:,}")          # :, agrega separador de miles
print(f"Mediana: {mediana:.1f}s")       # :.1f = 1 decimal
print(f"Porcentaje: {0.306:.1%}")       # :.1% convierte a porcentaje
```

Output:
```
Alistador: Mauricio
Pedidos: 2,059
Mediana: 130.0s
Porcentaje: 30.6%
```

---

### os.path — manejo de rutas de archivos
```python
import os

# __file__ = ruta completa de este script
# os.path.dirname() = extrae solo la carpeta
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# os.path.join() construye rutas de forma segura
# funciona igual en Windows, Mac y Linux
archivo = os.path.join(BASE_DIR, "data", "raw", "FPM_Datos.xlsx")

# Crear carpeta si no existe (exist_ok=True evita error si ya existe)
os.makedirs("outputs", exist_ok=True)
```

**Por qué usamos esto:**
Sin `os.path.join()` tendrías que escribir rutas diferentes en Windows
(`C:\carpeta\archivo`) y Mac (`/Users/carpeta/archivo`). Con `join()` el
código funciona igual en ambos sistemas.

---

## 2. Pandas

Pandas es la biblioteca más importante del proyecto. Trabaja con
**DataFrames** — tablas de datos equivalentes a hojas de Excel.

### Cargar datos
```python
import pandas as pd

# Leer Excel
df = pd.read_excel("FPM_Datos.xlsx")

# Leer CSV
df = pd.read_csv("datos.csv")

# Ver primeras 5 filas (como hacer scroll en Excel)
df.head()

# Ver últimas 5 filas
df.tail()

# Dimensiones: (filas, columnas)
print(df.shape)  # → (32373, 10)

# Nombres de columnas
print(df.columns)

# Tipos de datos por columna
print(df.dtypes)

# Estadísticas básicas de todas las columnas numéricas
print(df.describe())
```

---

### Seleccionar columnas
```python
# Una columna → Series (como una columna de Excel)
tiempos = df['tiempo_alisto_minutos']

# Varias columnas → DataFrame
subset = df[['picker_id', 'cant_lineas', 'tiempo_alisto_minutos']]

# Acceder a un valor específico (fila 0, columna picker_id)
valor = df.loc[0, 'picker_id']
```

---

### Filtrar filas — equivalente a AutoFiltro en Excel
```python
# Filtrar donde tiempo > 0
df_con_tiempo = df[df['tiempo_alisto_minutos'] > 0]

# Filtrar por valor específico
em047 = df[df['picker_id'] == 'EM047']

# Múltiples condiciones (& = AND, | = OR)
df_filtrado = df[(df['picker_id'] == 'EM047') & (df['tiempo_alisto_minutos'] > 0)]

# Filtrar valores no nulos (no vacíos)
df_limpio = df[df['picker_id'].notna()]

# Equivalente: dropna() elimina filas con valores vacíos
df_limpio = df.dropna(subset=['picker_id'])
```

---

### Crear columnas calculadas — equivalente a fórmulas en Excel
```python
# Nueva columna = operación sobre columnas existentes
df['tiempo_segundos'] = df['tiempo_alisto_minutos'] * 60

df['seg_por_linea'] = df['tiempo_segundos'] / df['cant_lineas']

# np.where = equivalente a IF() en Excel
# np.where(condición, valor_si_true, valor_si_false)
import numpy as np
df['seg_por_linea'] = np.where(
    df['cant_lineas'] > 0,            # condición
    df['tiempo_segundos'] / df['cant_lineas'],  # si true
    np.nan                             # si false (NaN = vacío)
)
```

---

### Renombrar columnas
```python
# Renombrar columnas específicas
df = df.rename(columns={
    'ALISTADOR':             'picker_id',
    'TIEMPO ALISTO (MINUTOS)': 'tiempo_minutos',
})

# Estandarizar todos los nombres de una vez
df.columns = (df.columns
              .str.lower()           # MAYÚSCULAS → minúsculas
              .str.strip()           # quitar espacios al inicio/fin
              .str.replace(' ', '_') # espacios → guiones bajos
              .str.replace('(', '')  # quitar paréntesis
              .str.replace(')', '')
              )
```

---

### groupby — equivalente a Tabla Dinámica en Excel
```python
# Agrupar por picker_id y contar pedidos
conteo = df.groupby('picker_id').size()

# Múltiples métricas a la vez
resumen = df.groupby('picker_id').agg(
    total_pedidos = ('picker_id', 'count'),      # contar filas
    lineas_total  = ('cant_lineas', 'sum'),       # suma
    lineas_media  = ('cant_lineas', 'mean'),      # promedio
    lineas_mediana= ('cant_lineas', 'median'),    # mediana
    lineas_max    = ('cant_lineas', 'max'),       # máximo
)

# Equivalente a una Tabla Dinámica con:
# Filas: picker_id
# Valores: count, sum, mean, median, max de cant_lineas
```

---

### merge — equivalente a VLOOKUP / buscarv en Excel
```python
# Tabla A: volumen por picker
vol = df.groupby('picker_id').size().reset_index(name='pedidos')

# Tabla B: tiempo por picker
tiempo = df_tiempo.groupby('picker_id')['seg_por_linea'].median().reset_index()

# Combinar ambas tablas por picker_id
# how='left' = mantener todos los registros de la tabla izquierda
resultado = vol.merge(tiempo, on='picker_id', how='left')
```

---

### sort_values — ordenar
```python
# Ordenar de mayor a menor
df_ordenado = df.sort_values('total_pedidos', ascending=False)

# Ordenar de menor a mayor
df_ordenado = df.sort_values('seg_por_linea', ascending=True)

# Ordenar por múltiples columnas
df_ordenado = df.sort_values(['picker_id', 'fecha'], ascending=[True, False])
```

---

### Estadísticas descriptivas
```python
serie = df['seg_por_linea']

serie.mean()           # promedio
serie.median()         # mediana (el valor del medio)
serie.std()            # desviación estándar
serie.min()            # mínimo
serie.max()            # máximo
serie.quantile(0.25)   # percentil 25 (P25)
serie.quantile(0.75)   # percentil 75 (P75)
serie.quantile(0.90)   # percentil 90 (P90)

# Contar valores que cumplen una condición
(serie > 120).sum()    # cantidad de pedidos con más de 120s
(serie > 120).mean()   # proporción (0.0 a 1.0)
(serie > 120).mean() * 100  # porcentaje
```

---

## 3. NumPy

NumPy hace cálculos matemáticos sobre arrays (listas de números).

```python
import numpy as np

# np.where — condicional vectorizado (equivalente a IF en Excel)
resultado = np.where(condicion, valor_si_true, valor_si_false)

# np.nan — valor vacío/nulo (Not a Number)
# Se usa cuando no hay valor válido para una celda
df.loc[df['tiempo'] < 0, 'tiempo'] = np.nan

# Estadísticas ignorando NaN
np.nanmean(array)    # promedio ignorando vacíos
np.nanmedian(array)  # mediana ignorando vacíos

# Crear array de números
x = np.linspace(0, 400, 500)  # 500 puntos entre 0 y 400
```

---

## 4. Visualización

### Estructura básica de una gráfica
```python
import matplotlib.pyplot as plt

# Crear figura y ejes
fig, ax = plt.subplots(figsize=(10, 5))
# figsize = (ancho, alto) en pulgadas

# Agregar elementos
ax.bar(x_values, y_values, color='steelblue', alpha=0.8)
ax.axhline(y=60, color='green', linestyle='--', label='Meta 60s')

# Títulos y etiquetas
ax.set_title('Mi gráfica')
ax.set_xlabel('Eje X')
ax.set_ylabel('Eje Y')
ax.legend()  # mostrar leyenda

# Guardar y mostrar
plt.tight_layout()  # ajustar espaciado automáticamente
plt.savefig('outputs/mi_grafica.png', dpi=150, bbox_inches='tight')
plt.show()
```

---

### Múltiples gráficas en una figura
```python
# 2 filas, 2 columnas = 4 gráficas
fig, axes = plt.subplots(2, 2, figsize=(14, 10))

ax1 = axes[0, 0]  # fila 0, columna 0 (arriba izquierda)
ax2 = axes[0, 1]  # fila 0, columna 1 (arriba derecha)
ax3 = axes[1, 0]  # fila 1, columna 0 (abajo izquierda)
ax4 = axes[1, 1]  # fila 1, columna 1 (abajo derecha)

# 2 filas, 1 columna con alturas diferentes
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8),
                                gridspec_kw={'height_ratios': [3, 1]})
# ax1 tendrá 3x la altura de ax2
```

---

### Tipos de gráficas usadas en el proyecto
```python
# Barras verticales
ax.bar(x, y, color='steelblue', alpha=0.8)

# Barras horizontales
ax.barh(y_labels, x_values, color='steelblue')

# Línea
ax.plot(x, y, color='black', linewidth=1.5)

# Puntos dispersos (scatter)
ax.scatter(x, y, c=colores, s=3, alpha=0.4)

# Histograma — distribución de frecuencias
ax.hist(datos, bins=50, color='steelblue', alpha=0.7)

# Boxplot — distribución con cuartiles
ax.boxplot(data_list, tick_labels=etiquetas, patch_artist=True)

# Línea horizontal de referencia
ax.axhline(y=60, color='green', linestyle='--', label='Meta')

# Área sombreada entre dos valores
ax.axhspan(ymin, ymax, alpha=0.05, color='green')
```

---

## 5. Estadística

### Promedio vs Mediana — cuándo usar cada uno

**Promedio (mean):** suma de todos los valores dividida entre la cantidad.
Se distorsiona fácilmente con valores extremos.

**Mediana:** el valor del medio cuando los datos están ordenados.
Robusta a valores extremos — por eso la usamos en este proyecto.

```
Ejemplo con pedidos de Favarcia:
Tiempos: [30, 45, 60, 80, 95, 120, 6330]
Promedio: (30+45+60+80+95+120+6330) / 7 = 965.7s  ← distorsionado
Mediana:  80s  ← más representativo
```

El pedido de 6330s (un pedido olvidado sin cerrar) distorsiona el
promedio pero no afecta la mediana.

---

### Percentiles
```
P25 = el 25% de los datos están POR DEBAJO de este valor
P50 = la mediana
P75 = el 75% de los datos están POR DEBAJO de este valor
P90 = el 90% de los datos están POR DEBAJO de este valor

Ejemplo:
P25 = 72.9s  → el 25% de tus pedidos toman menos de 72.9s
P75 = 240s   → el 75% de tus pedidos toman menos de 240s
```

---

### IQR — Rango Intercuartílico
```
IQR = P75 - P25

Es la "anchura" del 50% central de los datos.
IQR pequeño = proceso consistente
IQR grande  = proceso muy variable

En el control chart usamos:
UCL = P75 + 1.5 × IQR  (límite superior)
LCL = P25 - 1.5 × IQR  (límite inferior)

Esto es más robusto que ±3σ para distribuciones asimétricas
como la de tiempos de picking.
```

---

### CV — Coeficiente de Variación
```
CV = (desviación estándar / promedio) × 100

Mide la variabilidad relativa al promedio.

CV < 30% → proceso consistente (variación baja)
CV > 30% → proceso variable

En el proyecto:
CV global = 69.1% (mezcla de perfiles distintos)
CV por grupo = 5-9% (dentro de cada grupo, consistente)
→ La variación es entre grupos, no dentro de ellos
→ El problema es sistémico, no individual
```

---

### Cpk — Process Capability Index
```
Cpk = min(
    (USL - Media) / (3σ),   ← distancia al límite superior
    (Media - LSL) / (3σ)    ← distancia al límite inferior
)

Interpretación:
Cpk < 1.0  → INCAPAZ (produce defectos garantizados)
Cpk = 1.33 → Mínimo aceptable manufactura general
Cpk = 1.67 → Estándar en medtech
Cpk ≥ 2.0  → Excelente (FDA dispositivos críticos)

En Favarcia: Cpk = 0.03 → proceso completamente incapaz
```

---

### Distribución Log-Normal
Los tiempos de picking siguen una distribución log-normal:
- La mayoría de pedidos tienen tiempos bajos (30-80s)
- Hay una cola larga hacia la derecha (pedidos con fricción)
- El promedio es mucho mayor que la mediana

Esta distribución aparece en procesos donde hay un tiempo mínimo
físico pero no hay límite superior (siempre puede haber más fricción).

Por eso usamos medianas en vez de promedios, e IQR en vez de σ
para el control chart.

---

## 6. Patrones Comunes

### Patrón: cargar y limpiar datos
Este patrón aparece en todos los scripts del proyecto:

```python
# 1. Cargar
df = pd.read_excel(archivo)

# 2. Estandarizar nombres
df.columns = df.columns.str.lower().str.strip().str.replace(' ', '_')

# 3. Renombrar a nombres internos
df = df.rename(columns={'ALISTADOR': 'picker_id'})

# 4. Limpiar nulos
df = df.dropna(subset=['picker_id'])

# 5. Separar datasets según necesidad
df_vol    = df.copy()                        # todos los pedidos
df_tiempo = df[df['tiempo_minutos'] > 0]     # solo con tiempo
```

---

### Patrón: normalizar scores 0-100
Usado en `ranking_alistadores.py`:

```python
def normalizar(serie, mayor_es_mejor=True):
    mn, mx = serie.min(), serie.max()
    norm = (serie - mn) / (mx - mn) * 100
    return norm if mayor_es_mejor else 100 - norm

# Si mayor valor = mejor (ej: volumen de pedidos)
score_volumen = normalizar(df['total_pedidos'], mayor_es_mejor=True)

# Si menor valor = mejor (ej: tiempo por línea)
score_tiempo = normalizar(df['mediana_seg'], mayor_es_mejor=False)
```

---

### Patrón: detección de outliers con IQR
```python
Q1  = serie.quantile(0.25)
Q3  = serie.quantile(0.75)
IQR = Q3 - Q1

limite_superior = Q3 + 1.5 * IQR
limite_inferior = Q1 - 1.5 * IQR

outliers = serie[(serie > limite_superior) | (serie < limite_inferior)]
```

---

### Patrón: medianas móviles (rolling)
Usado en el control chart para suavizar la tendencia:

```python
# Calcular mediana de los últimos 50 pedidos
# center=True centra la ventana en el punto actual
mediana_movil = datos.rolling(window=50, center=True).median()

# Esto suaviza el ruido y muestra la tendencia real del proceso
# Si la línea sube → el proceso se está deteriorando
# Si es plana → proceso estable
```

---

## 7. Glosario Rápido

| Término | Significado en el proyecto |
|---|---|
| `df` | DataFrame — la tabla de datos principal |
| `NaN` | Not a Number — valor vacío/nulo |
| `dropna()` | Eliminar filas con valores vacíos |
| `reset_index()` | Reiniciar el índice de filas a 0,1,2... |
| `copy()` | Crear copia independiente del DataFrame |
| `apply()` | Aplicar una función a cada fila/columna |
| `merge()` | Combinar dos tablas (como VLOOKUP) |
| `groupby()` | Agrupar datos (como Tabla Dinámica) |
| `agg()` | Calcular múltiples métricas en groupby |
| `sort_values()` | Ordenar el DataFrame |
| `nlargest(n)` | Los n valores más grandes |
| `idxmax()` | Índice del valor máximo |
| `rolling()` | Ventana móvil para suavizar series |
| `quantile(0.9)` | Percentil 90 |
| `str.lower()` | Convertir texto a minúsculas |
| `str.replace()` | Reemplazar texto |
| `figsize` | Tamaño de la gráfica en pulgadas |
| `alpha` | Transparencia (0=invisible, 1=sólido) |
| `dpi` | Resolución de la imagen guardada |
| `tight_layout()` | Ajustar espaciado entre gráficas |

---

## 📌 Notas de Aprendizaje

### Lo que aprendiste en este proyecto

1. **Separar volumen de tiempo** — El 52% de pedidos tiene tiempo=0 porque se trabajan antes de abrirse. Sin esta separación, el análisis pierde el 52% del trabajo real.

2. **Medianas sobre promedios** — Los datos de picking son log-normales. Un pedido olvidado de 63 horas distorsiona el promedio pero no afecta la mediana.

3. **IQR sobre σ para control charts** — Cuando la distribución no es normal, los límites ±3σ son inútiles. Los límites de Tukey (P75 ± 1.5×IQR) son más robustos.

4. **Normalización para rankings** — Para comparar métricas con unidades distintas (pedidos vs segundos vs porcentajes), hay que normalizarlas a la misma escala (0-100).

5. **Roles operacionales en los datos** — EM039, EM560, EM289 tienen patrones estadísticos distintos no porque sean mejores o peores sino porque su función es diferente. Los datos reflejan el sistema, no solo las personas.

---

*Proyecto: FPM — Favarcia Plan de Mejora*
*Autor: Mauricio Araya | Metodología: Intel Seven Steps + SPC*