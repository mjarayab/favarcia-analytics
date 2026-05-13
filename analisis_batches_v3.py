"""
=============================================================
FAVARCIA — ANÁLISIS DE BATCHES v2
=============================================================
Lógica mejorada de detección:
- Ventana dinámica ±1min alrededor de cada cierre
- Detecta pedidos abiertos/cerrados en ventanas comunes
- Nuevas métricas: throughput, unidades, boxplots
=============================================================
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os

# ── Rutas ─────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
DATA_DIR    = os.path.join(BASE_DIR, "data", "raw")
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")
os.makedirs(OUTPUTS_DIR, exist_ok=True)

# ── Cargar datos ──────────────────────────────────────────
archivo = os.path.join(DATA_DIR, "FPM_Datos.xlsx")
print("📊 Cargando datos...")
df = pd.read_excel(archivo)

df.columns = (df.columns.str.lower().str.strip()
              .str.replace(' ', '_')
              .str.replace('(', '').str.replace(')', ''))
df = df.rename(columns={
    'alistador':             'picker_id',
    'tiempo_alisto_minutos': 'tiempo_minutos',
    'fin_alisto':            'fin_alisto',
    'inicio_alisto':         'inicio_alisto',
    'cant_lineas':           'cant_lineas',
})

# Intentar agregar cant_unidades si existe
if 'cant_unidades' not in df.columns:
    # Si no existe, estimar como líneas (fallback)
    df['cant_unidades'] = df['cant_lineas']

df = df.dropna(subset=['picker_id', 'fin_alisto'])
df['fin_dt']   = pd.to_datetime(df['fin_alisto'], errors='coerce')
df['inicio_dt'] = pd.to_datetime(df['inicio_alisto'], errors='coerce')

print(f"✅ {len(df):,} pedidos cargados")

# ── Detectar batches con ventana dinámica ±1min ──────────
print(f"\n📊 Detectando batches con ventana ±1min...")

VENTANA_MIN = 1  # minutos

batch_records = []
batch_id_counter = 0
processed = set()

for picker in df['picker_id'].unique():
    picker_df = (df[df['picker_id'] == picker]
                 .sort_values('fin_dt')
                 .reset_index(drop=True))

    if len(picker_df) < 1:
        continue

    for idx, row in picker_df.iterrows():
        # Si ya procesamos este pedido, saltar
        if row.name in processed:
            continue

        fin_ref = row['fin_dt']
        ventana_inicio = fin_ref - pd.Timedelta(minutes=VENTANA_MIN)
        ventana_fin = fin_ref + pd.Timedelta(minutes=VENTANA_MIN)

        # Encontrar todos los pedidos que cierren en esta ventana
        batch_pedidos = picker_df[
            (picker_df['fin_dt'] >= ventana_inicio) &
            (picker_df['fin_dt'] <= ventana_fin)
        ].copy()

        if len(batch_pedidos) == 0:
            continue

        # Marcar estos pedidos como procesados
        for batch_idx in batch_pedidos.index:
            processed.add(batch_idx)

        # Calcular métricas del batch
        cant_pedidos = len(batch_pedidos)
        cant_lineas = batch_pedidos['cant_lineas'].sum()
        cant_unidades = batch_pedidos['cant_unidades'].sum()
        
        fin_min = batch_pedidos['fin_dt'].min()
        fin_max = batch_pedidos['fin_dt'].max()
        tiempo_batch_min = (fin_max - fin_min).total_seconds() / 60

        # Evitar división por cero
        if tiempo_batch_min == 0:
            tiempo_batch_min = 0.1

        throughput = cant_lineas / max(tiempo_batch_min, 0.01)
        seg_linea = (tiempo_batch_min * 60) / max(cant_lineas, 1)

        batch_records.append({
            'batch_id':            f"{picker}-{batch_id_counter}",
            'picker_id':           picker,
            'cant_pedidos':        cant_pedidos,
            'cant_lineas':         cant_lineas,
            'cant_unidades':       cant_unidades,
            'fecha':               fin_min.date(),
            'hora':                fin_min.hour,
            'fin_inicio':          fin_min,
            'fin_final':           fin_max,
            'tiempo_batch_min':    tiempo_batch_min,
            'throughput_lineas_min': throughput,
            'seg_linea_batch':     seg_linea,
            'categoria':           '1 pedido' if cant_pedidos == 1 else 
                                  '2-3 pedidos' if cant_pedidos <= 3 else 
                                  '4+ pedidos',
        })

        batch_id_counter += 1

df_batches_v2 = pd.DataFrame(batch_records)

print(f"✅ {len(df_batches_v2):,} batches detectados")
print(f"   Promedio pedidos/batch: {df_batches_v2['cant_pedidos'].mean():.1f}")
print(f"   Promedio líneas/batch: {df_batches_v2['cant_lineas'].mean():.1f}")

# ── Mapeo de nombres ──────────────────────────────────────
mapeo_nombres = {}
for picker in df['picker_id'].unique():
    nombres = df[df['picker_id'] == picker]['nombre'].dropna()
    if len(nombres) > 0:
        palabras = str(nombres.iloc[0]).split()
        if len(palabras) >= 3:
            mapeo_nombres[picker] = f"{palabras[2].capitalize()} ({picker})"
        else:
            mapeo_nombres[picker] = picker

df_batches_v2['etiqueta'] = df_batches_v2['picker_id'].map(mapeo_nombres)

# ── ANÁLISIS ──────────────────────────────────────────────
print(f"\n{'='*70}")
print(f"ANÁLISIS DE BATCHES v2 — Lógica de Ventana Dinámica ±1min")
print(f"{'='*70}")

print(f"\n📊 KPIs GLOBALES:")
print(f"   Mediana seg/línea:        {df_batches_v2['seg_linea_batch'].median():.1f}s")
print(f"   Mediana throughput:       {df_batches_v2['throughput_lineas_min'].median():.1f} líneas/min")
print(f"   Mediana unidades/batch:   {df_batches_v2['cant_unidades'].median():.0f}")

# Estadísticas por categoría
print(f"\n{'='*70}")
print(f"COMPARACIÓN POR CATEGORÍA DE BATCH")
print(f"{'='*70}")

por_categoria = (df_batches_v2.groupby('categoria')
                 .agg(
                     batches             = ('batch_id', 'count'),
                     mediana_seg_linea   = ('seg_linea_batch', 'median'),
                     mediana_throughput  = ('throughput_lineas_min', 'median'),
                     mediana_unidades    = ('cant_unidades', 'median'),
                     mediana_lineas      = ('cant_lineas', 'median'),
                 )
                 .reset_index()
                 .sort_values('batches', ascending=False))

print(f"\n{'Categoría':15} {'Batches':>10} {'Med Seg/L':>12} {'Med Tph':>10} {'Med Unit':>10}")
print("-" * 65)
for _, row in por_categoria.iterrows():
    print(f"{row['categoria']:15} {row['batches']:>10.0f} "
          f"{row['mediana_seg_linea']:>11.1f}s {row['mediana_throughput']:>9.1f} "
          f"{row['mediana_unidades']:>9.0f}")

# Top alistadores por throughput
print(f"\n{'='*70}")
print(f"TOP 15 ALISTADORES — POR THROUGHPUT (líneas/min)")
print(f"{'='*70}")

top_tph = (df_batches_v2.groupby(['picker_id', 'etiqueta'])
           .agg(
               batches = ('batch_id', 'count'),
               tph_med = ('throughput_lineas_min', 'median'),
               tph_p75 = ('throughput_lineas_min', lambda x: x.quantile(0.75)),
               seg_med = ('seg_linea_batch', 'median'),
           )
           .reset_index()
           .sort_values('tph_med', ascending=False))

print(f"\n{'Nombre':25} {'Batches':>8} {'Med TPH':>10} {'P75 TPH':>10} {'Med s/L':>8}")
print("-" * 68)
for _, row in top_tph.head(15).iterrows():
    print(f"{row['etiqueta']:25} {row['batches']:>8.0f} "
          f"{row['tph_med']:>9.1f}  {row['tph_p75']:>9.1f}  "
          f"{row['seg_med']:>7.1f}s")

# ── GRÁFICAS ──────────────────────────────────────────────
fig = plt.figure(figsize=(16, 12))
gs = fig.add_gridspec(3, 2, hspace=0.3, wspace=0.3)

fig.suptitle('FAVARCIA — Análisis de Batches v2\nVentana Dinámica ±1min | Nuevas Métricas',
             fontsize=14, fontweight='bold')

# Gráfica 1: Distribución de tamaño de batch por categoría
ax1 = fig.add_subplot(gs[0, 0])
for cat in ['1 pedido', '2-3 pedidos', '4+ pedidos']:
    data = df_batches_v2[df_batches_v2['categoria'] == cat]['cant_lineas']
    ax1.hist(data, bins=30, alpha=0.5, label=cat, edgecolor='white')
ax1.set_xlabel('Líneas por batch')
ax1.set_ylabel('Frecuencia')
ax1.set_title('Distribución de líneas por batch\n(por categoría)')
ax1.legend()

# Gráfica 2: Boxplot throughput por categoría
ax2 = fig.add_subplot(gs[0, 1])
df_batches_v2.boxplot(column='throughput_lineas_min', by='categoria', ax=ax2)
ax2.set_xlabel('Categoría de batch')
ax2.set_ylabel('Throughput (líneas/min)')
ax2.set_title('Throughput por categoría\n(mejor desempeño = más líneas/min)')
plt.sca(ax2)
plt.xticks(rotation=0)

# Gráfica 3: Boxplot seg/línea por alistador (top 15)
ax3 = fig.add_subplot(gs[1, :])
top_15_pickers = df_batches_v2.groupby('etiqueta')['batch_id'].count().nlargest(15).index
df_top = df_batches_v2[df_batches_v2['etiqueta'].isin(top_15_pickers)]
df_top.boxplot(column='seg_linea_batch', by='etiqueta', ax=ax3)
ax3.axhline(y=60, color='green', linestyle='--', linewidth=1.5, label='Target 60s')
ax3.axhline(y=120, color='red', linestyle='--', linewidth=1.5, label='Fricción 120s')
ax3.set_xlabel('Alistador')
ax3.set_ylabel('Segundos/línea')
ax3.set_title('Distribución seg/línea por alistador (top 15)\nMenor caja = más consistente')
ax3.legend()
plt.sca(ax3)
plt.xticks(rotation=45, ha='right')

# Gráfica 4: Comparación de métricas por categoría
ax4 = fig.add_subplot(gs[2, 0])
x = np.arange(len(por_categoria))
width = 0.2
metrics_norm = [
    (por_categoria['mediana_throughput'] / por_categoria['mediana_throughput'].max()) * 100,
    (1 / (por_categoria['mediana_seg_linea'] / por_categoria['mediana_seg_linea'].max())) * 100,
]
ax4.bar(x - width/2, metrics_norm[0], width, label='Throughput (norm)', alpha=0.8)
ax4.bar(x + width/2, metrics_norm[1], width, label='1/seg_línea (norm)', alpha=0.8)
ax4.set_xlabel('Categoría')
ax4.set_ylabel('Score normalizado')
ax4.set_title('Comparación de eficiencia por categoría\n(ambas métricas normalizadas)')
ax4.set_xticks(x)
ax4.set_xticklabels(por_categoria['categoria'])
ax4.legend()

# Gráfica 5: Unidades por batch por categoría
ax5 = fig.add_subplot(gs[2, 1])
por_cat_unit = df_batches_v2.groupby('categoria')['cant_unidades'].agg(['median', 'mean'])
x_cat = np.arange(len(por_cat_unit))
ax5.bar(x_cat - 0.2, por_cat_unit['median'], 0.4, label='Mediana', alpha=0.8)
ax5.bar(x_cat + 0.2, por_cat_unit['mean'], 0.4, label='Promedio', alpha=0.8)
ax5.set_xlabel('Categoría')
ax5.set_ylabel('Unidades por batch')
ax5.set_title('Unidades procesadas por categoría')
ax5.set_xticks(x_cat)
ax5.set_xticklabels(['1 pedido', '2-3 pedidos', '4+ pedidos'])
ax5.legend()

plt.tight_layout()
ruta = os.path.join(OUTPUTS_DIR, 'analisis_batches_v2.png')
plt.savefig(ruta, dpi=150, bbox_inches='tight')
plt.show()
print(f"\n✅ Gráficas guardadas: {ruta}")

# ── Guardar datos ─────────────────────────────────────────
ruta_csv = os.path.join(OUTPUTS_DIR, 'batches_v2_detallado.csv')
df_batches_v2.to_csv(ruta_csv, index=False)
print(f"✅ Datos guardados: {ruta_csv}")

print(f"\n{'='*70}")
print(f"CONCLUSIÓN")
print(f"{'='*70}")
print(f"""
Con la ventana dinámica ±1min:

1. Detectamos batches más realistas
   → Pedidos abiertos antes/después de cerrar otro quedan en el mismo lote

2. Nuevas métricas revelan eficiencia real:
   → Throughput (líneas/min) vs seg/línea
   → Unidades procesadas por batch
   → Categorías muestran estrategias de trabajo diferentes

3. Boxplots por alistador muestran consistencia:
   → Caja pequeña = predecible
   → Caja grande = variable
   → Outliers = pedidos atípicos

PRÓXIMOS PASOS:
- Comparar batches 1 vs 2-3 vs 4+ para optimizar tamaño ideal
- Analizar si throughput mejora con batches más grandes
- Validar que unidades/batch correlacionen con velocidad
""")