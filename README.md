# Favarcia Picking Performance Analysis
### Warehouse Operations — Statistical Process Control Applied to Order Fulfillment

**Autor:** Mauricio Araya  
**Inicio:** Abril 2026  
**Estado:** ✅ Análisis base completo — esperando datos reales de producción

---

## 🎯 Objetivo

Demostrar mediante análisis estadístico que la variabilidad en tiempos de picking en Grupo Favarcia S.A. es un problema **sistémico** — cajones vacíos, ubicaciones incorrectas en WMS, reposición tardía — y no un problema de desempeño individual de los operadores.

**Hipótesis central:**  
El KPI actual (1 min/línea) mide *output*, no *proceso*. El tiempo de búsqueda de producto cuando un cajón está vacío no está capturado en ninguna métrica existente — pero sí aparece como variabilidad estadística en los datos de pedidos individuales.

---

## 🔑 Resultados con Datos de Muestra

> Los resultados abajo fueron generados con datos sintéticos calibrados con parámetros operacionales reales (ver sección *Sample Data*). Los resultados con datos reales de producción se agregarán cuando estén disponibles.

### Distribución de tiempos y variabilidad por operador
![Distribución](outputs/sample/distribucion_picking.png)

**Hallazgo:** Todos los operadores muestran la misma forma de distribución y la misma cola superior. Las medianas son casi idénticas (~65–75s). Si el problema fuera individual, las cajas y colas serían de tamaños muy diferentes entre personas.

---

### Fricción por hora del día
![Fricción por hora](outputs/sample/friccion_por_hora.png)

**Hallazgo:** La fricción aumenta +11% en las últimas horas del turno (hora 16 = 82s/línea vs hora 6 = 74s/línea). Este patrón es consistente con cajones que se van vaciando a lo largo del día sin reposición suficiente — *no* con fatiga individual del operador.

---

### Control Chart — SPC
![Control Chart](outputs/sample/control_chart_todos.png)

**Hallazgo:** Los 214 puntos fuera de control (1.5%) están distribuidos uniformemente a lo largo del tiempo y entre todos los operadores. Si la causa fuera individual, los puntos se agruparían alrededor de ciertos operadores o períodos.

---

### Análisis de Capacidad — Cpk
![Cpk](outputs/sample/cpk_analysis.png)

| Índice | Valor | Interpretación |
|--------|-------|----------------|
| Cp | 0.50 | Capacidad potencial si el proceso estuviera centrado |
| Cpk | **0.29** | **Proceso INCAPAZ** — 19.4% de pedidos superan USL |
| USL | 120 seg/línea | Umbral de fricción (2× meta) |
| Target | 60 seg/línea | Meta operacional actual |

**Para alcanzar Cpk = 1.33** (mínimo aceptable en manufactura):
- Reducir media de 85s → 60s (−25s/línea)
- Reducir σ de 40s → 25s
- Equivale a eliminar la fricción sistémica de cajones vacíos y ubicaciones incorrectas en WMS

---

### CV por grupo de experiencia

| Grupo | Fricción promedio | CV interno | Interpretación |
|-------|------------------|-----------|----------------|
| Expertos | 7.4% | 8.5% ✅ | Uniforme dentro del grupo |
| Medios | 18.3% | 9.5% ✅ | Uniforme dentro del grupo |
| Nuevos | 43.4% | 5.5% ✅ | Uniforme dentro del grupo |
| **Global** | — | **66.8%** | Alto por mezcla de perfiles, no por variación individual |

**Conclusión:** La diferencia entre grupos refleja curva de aprendizaje sistémica. Dentro de cada grupo la variación es mínima — todos experimentan la misma fricción de cajones vacíos.

---

## 🗄️ Sample Data

El repositorio incluye datos sintéticos en `data/sample/` que permiten reproducir el análisis completo sin necesidad de datos reales de producción.

### Calibración de los datos sintéticos

| Parámetro | Valor real observado | Valor en datos sintéticos |
|-----------|---------------------|--------------------------|
| Pedidos (ene 2026, 2a quincena) | 4,924 | ~4,800 |
| Pedidos (feb 2026, mes completo) | 8,814 | ~8,600 |
| Efectividad | 97.4% | ~97.1% |
| Operadores activos | 30 | 30 |
| Turno operacional | 6am–5pm | 6am–5pm |

### Generar los datos de muestra

```bash
python generar_datos_prueba.py
# Genera: data/raw/datos_prueba_favarcia.xlsx
```

---

## 🛠️ Stack Técnico

```
pandas      — manipulación de datos
numpy       — cálculos matemáticos y estadísticos
matplotlib  — visualizaciones base
seaborn     — visualizaciones estadísticas
scipy       — análisis estadístico (distribuciones, Cpk, SPC)
openpyxl    — lectura/escritura de archivos Excel
```

### Instalación

```bash
pip install pandas numpy matplotlib seaborn scipy openpyxl
```

---

## 🚀 Cómo Correr el Análisis

```bash
# 1. Clonar el repositorio
git clone https://github.com/tu-usuario/favarcia-analytics.git
cd favarcia-analytics

# 2. Instalar dependencias
pip install pandas numpy matplotlib seaborn scipy openpyxl

# 3. Generar datos de muestra
python generar_datos_prueba.py

# 4. Correr análisis completo
python favarcia_picking_analysis.py
# Outputs guardados en outputs/
```

### Con datos reales

Coloca el Excel en `data/raw/` y actualiza en `favarcia_picking_analysis.py`:

```python
ARCHIVO = os.path.join(DATA_DIR, "tu_archivo_real.xlsx")
```

---

## 📁 Estructura del Proyecto

```
favarcia-analytics/
│
├── README.md
├── .gitignore
├── favarcia_picking_analysis.py         ← análisis principal
├── generar_datos_prueba.py              ← generador de datos sintéticos
│
├── data/
│   ├── sample/                          ← datos sintéticos (en git)
│   │   └── datos_prueba_favarcia.xlsx
│   └── raw/                             ← datos reales (excluidos, .gitignore)
│       └── .gitkeep
│
└── outputs/
    ├── sample/                          ← outputs sintéticos (en git)
    │   ├── distribucion_picking.png
    │   ├── friccion_por_hora.png
    │   ├── control_chart_todos.png
    │   └── cpk_analysis.png
    └── *.png                            ← outputs locales (excluidos, .gitignore)
```

---

## 📈 Conexión con Manufactura de Dispositivos Médicos

| Favarcia (Warehouse) | Medtech (Manufactura) |
|---|---|
| Tiempo por línea de picking | Cycle time por operación |
| Tasa de errores por operador | Defect rate por estación |
| Distribución de tiempos | Process capability analysis |
| Control Chart ±3σ | SPC — Statistical Process Control |
| Cpk = 0.29 → proceso incapaz | Cpk < 1.0 → detener línea |
| Fricción sistémica vs individual | Common cause vs special cause variation |

**Relevancia para entrevistas:** Abbott, Cirtec, Confluent Medical, Boston Scientific usan SPC y Cpk diariamente en sus líneas de producción en Coyol Free Zone, Costa Rica.

---

## 🗺️ Roadmap

- [x] Definir hipótesis y métricas clave
- [x] Generador de datos sintéticos calibrados con parámetros reales
- [x] Pipeline de carga y limpieza de datos
- [x] Análisis de distribución de tiempos
- [x] Análisis sistémico vs individual — CV por grupos
- [x] Interpretación automática de resultados
- [x] Control Chart con SPC (±3σ)
- [x] Análisis de capacidad Cpk
- [ ] Correr con datos reales de producción
- [ ] Validar hipótesis con datos reales
- [ ] Dashboard interactivo en Streamlit
- [ ] Análisis de correlación errores vs volumen
- [ ] Publicar caso de estudio en LinkedIn

---

## 📝 Contexto Operacional

**Empresa:** Grupo Favarcia S.A. — distribuidora de productos automotrices, motocicletas, bicicletas y pesca. Fundada hace 61 años en Costa Rica.

**Operación:** 400–500 pedidos diarios, ~30 operadores de picking, warehouse de 3,000 m².

**Metodología:** Intel Seven Steps aplicada a operaciones de warehouse. Este proyecto es parte del FPM (Favarcia Plan de Mejora), iniciativa de documentación y mejora continua.

---

*Autor: Mauricio Araya | Logistics & Process Improvement Coordinator*  
*Background: 7 años Intel Corporation — Process Engineering | Die Prep*