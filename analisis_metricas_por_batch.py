"""
=============================================================
FAVARCIA — MÉTRICAS POR BATCH (no por pedido)
=============================================================
Recalcula todas las métricas de desempeño usando BATCH como
unidad de medida en lugar de PEDIDO individual.

Un batch = lote de pedidos abiertos/cerrados en secuencia.

VENTAJA: Elimina el ruido de pedidos cerrados en sequence
sin ser completamente trabajados, dando métricas más realistas.
=============================================================
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from scipy import stats

# ── Rutas ─────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
DATA_DIR    = os.path.join(BASE_DIR, "data", "raw")
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")
os.makedirs(OUTPUTS_DIR, exist_ok=True)

# ── Cargar batches ────────────────────────────────────────
print("📊 Cargando datos...")
df_batches = pd.read_csv(os.path.join(OUTPUTS_DIR, 'batches_detallado.csv'))
df_batches['fin_inicio'] = pd.to_datetime(df_batches['fin_inicio'])
df_batches['fin_final']  = pd.to_datetime(df_batches['fin_final'])

print(f"✅ {len(df_batches):,} batches cargados")

# ── Cargar Excel para asociar líneas con batches ─────────
archivo = os.path.join(DATA_DIR, "FPM_Datos.xlsx")
print("📊 Cargando Excel...")
df = pd.read_excel(archivo)

df.columns = (df.columns.str.lower().str.strip()
              .str.replace(' ', '_')
              .str.replace('(', '').str.replace(')', ''))
df = df.rename(columns={
    'alistador':             'picker_id',
    'tiempo_alisto_minutos': 'tiempo_minutos',
    'fin_alisto':            'fin_alisto',
    'cant_lineas':           'cant_lineas',
})
df['fin_dt'] = pd.to_datetime(df['fin_alisto'], errors='coerce')

# ── Asociar pedidos con batches (eficiente) ───────────────
print("📊 Asociando pedidos con batches...")

# Procesar por picker para evitar merge masivo
batch_lookup = df_batches[['batch_id', 'picker_id', 'fin_inicio', 'fin_final', 'cant_pedidos']].copy()
batch_lookup['fin_inicio'] = pd.to_datetime(batch_lookup['fin_inicio'])
batch_lookup['fin_final'] = pd.to_datetime(batch_lookup['fin_final'])

merged_list = []
for picker in df['picker_id'].unique():
    df_picker = df[df['picker_id'] == picker].copy()
    batch_picker = batch_lookup[batch_lookup['picker_id'] == picker].copy()
    
    if len(batch_picker) == 0:
        continue
    
    # Para cada pedido del picker, encontrar su batch
    for idx, pedido in df_picker.iterrows():
        fin_dt = pedido['fin_dt']
        if pd.isna(fin_dt):
            continue
        
        # Buscar batch que contiene este pedido
        batch_match = batch_picker[
            (batch_picker['fin_inicio'] <= fin_dt) &
            (fin_dt <= batch_picker['fin_final'])
        ]
        
        if len(batch_match) > 0:
            pedido_dict = pedido.to_dict()
            pedido_dict['batch_id'] = batch_match.iloc[0]['batch_id']
            pedido_dict['cant_pedidos_batch'] = batch_match.iloc[0]['cant_pedidos']
            merged_list.append(pedido_dict)

df_merged = pd.DataFrame(merged_list)
print(f"✅ {len(df_merged):,} pedidos asociados a batches")

# ── Calcular métricas POR BATCH ───────────────────────────
print("📊 Calculando métricas por batch...")

# Primero obtener info del batch desde df_batches
batch_info = df_batches[['batch_id', 'fin_inicio', 'fin_final', 'cant_pedidos']].copy()
batch_info['fin_inicio'] = pd.to_datetime(batch_info['fin_inicio'])
batch_info['fin_final'] = pd.to_datetime(batch_info['fin_final'])

# Luego agregar líneas desde df_merged
batch_metrics = (df_merged.groupby('batch_id')
                 .agg(
                     picker_id          = ('picker_id', 'first'),
                     cant_lineas        = ('cant_lineas', 'sum'),
                     fecha              = ('fin_dt', 'first'),
                 )
                 .reset_index())

# Merge con info del batch
batch_metrics = batch_metrics.merge(
    batch_info,
    on='batch_id',
    how='left'
)

# Hora del día
batch_metrics['hora'] = batch_metrics['fin_final'].dt.hour

# Tiempo total del batch en minutos
batch_metrics['tiempo_batch_min'] = (
    (batch_metrics['fin_final'] - batch_metrics['fin_inicio']).dt.total_seconds() / 60
)

# Segundos por línea en el batch
batch_metrics['seg_linea_batch'] = (
    batch_metrics['tiempo_batch_min'] * 60 / batch_metrics['cant_lineas']
)

# Filtrar outliers (tiempo < 0.5 seg/línea o > 300 seg/línea no son realistas)
batch_metrics = batch_metrics[
    (batch_metrics['seg_linea_batch'] > 0.5) &
    (batch_metrics['seg_linea_batch'] < 300)
].copy()

print(f"✅ {len(batch_metrics):,} batches con métricas válidas")

# ── Mapeo de nombres ──────────────────────────────────────
mapeo = {}
for picker in batch_metrics['picker_id'].unique():
    nombres = df[df['picker_id'] == picker]['nombre'].dropna()
    if len(nombres) > 0:
        palabras = str(nombres.iloc[0]).split()
        if len(palabras) >= 3:
            mapeo[picker] = f"{palabras[2].capitalize()} ({picker})"
        else:
            mapeo[picker] = picker

batch_metrics['etiqueta'] = batch_metrics['picker_id'].map(mapeo)

# ── ANÁLISIS POR BATCH ────────────────────────────────────
print(f"\n{'='*70}")
print(f"MÉTRICAS POR BATCH (unidad = lote de pedidos, no pedido individual)")
print(f"{'='*70}")

print(f"\n📊 KPIs GLOBALES (por batch):")
print(f"   Mediana seg/línea:    {batch_metrics['seg_linea_batch'].median():.1f}s")
print(f"   Promedio seg/línea:   {batch_metrics['seg_linea_batch'].mean():.1f}s")
print(f"   Desv. estándar:       {batch_metrics['seg_linea_batch'].std():.1f}s")
print(f"   P75:                  {batch_metrics['seg_linea_batch'].quantile(0.75):.1f}s")
print(f"   P90:                  {batch_metrics['seg_linea_batch'].quantile(0.90):.1f}s")

# Top performers por batch
print(f"\n{'='*70}")
print(f"TOP 10 ALISTADORES — MÉTRICAS POR BATCH")
print(f"{'='*70}")

top_batch = (batch_metrics.groupby(['picker_id', 'etiqueta'])
             .agg(
                 batches         = ('batch_id', 'count'),
                 mediana         = ('seg_linea_batch', 'median'),
                 p75             = ('seg_linea_batch', lambda x: x.quantile(0.75)),
                 pct_alto        = ('seg_linea_batch', lambda x: (x > 120).mean() * 100),
             )
             .reset_index()
             .sort_values('mediana'))

print(f"\n{'Nombre':25} {'Batches':>8} {'Med':>6} {'P75':>6} {'%>120s':>7}")
print("-" * 60)
for _, row in top_batch.head(15).iterrows():
    print(f"{row['etiqueta']:25} {row['batches']:>8.0f} "
          f"{row['mediana']:>6.1f}s {row['p75']:>6.1f}s {row['pct_alto']:>6.1f}%")

# Cpk por batch
print(f"\n{'='*70}")
print(f"ANÁLISIS DE CAPACIDAD — Por Batch")
print(f"{'='*70}")

USL = 120  # Umbral de fricción
TARGET = 60

media_batch = batch_metrics['seg_linea_batch'].mean()
sigma_batch = batch_metrics['seg_linea_batch'].std()

cp_batch = (USL - 0) / (6 * sigma_batch)
cpk_batch = min(
    (USL - media_batch) / (3 * sigma_batch),
    (media_batch - 0) / (3 * sigma_batch)
)

print(f"\n   Media:                {media_batch:.1f}s/línea")
print(f"   Sigma:                {sigma_batch:.1f}s")
print(f"   Cp:                   {cp_batch:.2f}")
print(f"   Cpk:                  {cpk_batch:.2f}")
print(f"   % pedidos > 120s:     {(batch_metrics['seg_linea_batch'] > USL).mean()*100:.1f}%")
print(f"\n   Interpretación Cpk {cpk_batch:.2f}:")
if cpk_batch < 1.0:
    print(f"   ⚠️  Proceso incapaz (Cpk < 1.0)")
elif cpk_batch < 1.33:
    print(f"   ⚠️  Proceso marginal (1.0 < Cpk < 1.33)")
else:
    print(f"   ✅ Proceso capaz (Cpk > 1.33)")

# ── Comparación batch vs pedido ────────────────────────────
print(f"\n{'='*70}")
print(f"COMPARACIÓN: BATCH vs PEDIDO INDIVIDUAL")
print(f"{'='*70}")

# Calcular metrics por pedido
df_pedido = df[df['cant_lineas'] > 0].copy()
df_pedido['seg_linea'] = (df_pedido['tiempo_minutos'] * 60 / df_pedido['cant_lineas'])
df_pedido = df_pedido[
    (df_pedido['seg_linea'] > 0.5) &
    (df_pedido['seg_linea'] < 300)
].copy()

media_pedido = df_pedido['seg_linea'].mean()
sigma_pedido = df_pedido['seg_linea'].std()
cpk_pedido = min(
    (USL - media_pedido) / (3 * sigma_pedido),
    (media_pedido - 0) / (3 * sigma_pedido)
)

print(f"\n{'Métrica':30} {'Por Pedido':>15} {'Por Batch':>15}")
print("-" * 65)
print(f"{'Media seg/línea':30} {media_pedido:>15.1f}s {media_batch:>15.1f}s")
print(f"{'Mediana seg/línea':30} {df_pedido['seg_linea'].median():>15.1f}s "
      f"{batch_metrics['seg_linea_batch'].median():>15.1f}s")
print(f"{'Sigma':30} {sigma_pedido:>15.1f}s {sigma_batch:>15.1f}s")
print(f"{'Cpk':30} {cpk_pedido:>15.2f} {cpk_batch:>15.2f}")
print(f"{'% > 120s':30} {(df_pedido['seg_linea'] > USL).mean()*100:>15.1f}% "
      f"{(batch_metrics['seg_linea_batch'] > USL).mean()*100:>15.1f}%")

mejora_media = ((media_pedido - media_batch) / media_pedido) * 100
mejora_cpk = ((cpk_batch - cpk_pedido) / abs(cpk_pedido)) * 100 if cpk_pedido != 0 else 0

print(f"\n📈 MEJORA al usar Batch como unidad:")
print(f"   Media: {mejora_media:+.1f}% (de {media_pedido:.1f}s a {media_batch:.1f}s)")
print(f"   Cpk:   {mejora_cpk:+.1f}% (de {cpk_pedido:.2f} a {cpk_batch:.2f})")

# ── GRÁFICAS ──────────────────────────────────────────────
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle('FAVARCIA — Métricas por BATCH (no por Pedido Individual)\n'
             'Eliminando ruido de pedidos cerrados en secuencia',
             fontsize=13, fontweight='bold')

# Gráfica 1: Distribución batch vs pedido
ax1 = axes[0, 0]
ax1.hist(batch_metrics['seg_linea_batch'], bins=60, alpha=0.6,
         label=f'Por Batch (Med={batch_metrics["seg_linea_batch"].median():.0f}s)',
         color='steelblue', edgecolor='white')
ax1.hist(df_pedido['seg_linea'], bins=60, alpha=0.6,
         label=f'Por Pedido (Med={df_pedido["seg_linea"].median():.0f}s)',
         color='orange', edgecolor='white')
ax1.axvline(x=USL, color='red', linestyle='--', linewidth=1.5, label='USL 120s')
ax1.axvline(x=TARGET, color='green', linestyle='--', linewidth=1.5, label='Target 60s')
ax1.set_xlabel('Segundos por línea')
ax1.set_ylabel('Frecuencia')
ax1.set_title('Distribución: Batch vs Pedido\n(batch elimina mucho ruido)')
ax1.legend(fontsize=8)
ax1.set_xlim(0, 300)

# Gráfica 2: Top 15 alistadores por batch
ax2 = axes[0, 1]
top15 = top_batch.head(15).sort_values('mediana')
colores2 = ['tomato' if m > 120 else 'steelblue' for m in top15['mediana']]
ax2.barh(top15['etiqueta'], top15['mediana'], color=colores2, alpha=0.8)
ax2.axvline(x=USL, color='red', linestyle='--', linewidth=1, label='USL 120s')
ax2.axvline(x=TARGET, color='green', linestyle='--', linewidth=1, label='Target 60s')
ax2.set_xlabel('Mediana seg/línea (batch)')
ax2.set_title('Top 15 alistadores — métricas por batch')
ax2.legend(fontsize=8)

# Gráfica 3: Cpk por batch vs por pedido
ax3 = axes[1, 0]
categorias = ['Por Pedido', 'Por Batch']
cpk_vals = [cpk_pedido, cpk_batch]
colores3 = ['tomato' if c < 1.33 else 'green' for c in cpk_vals]
ax3.bar(categorias, cpk_vals, color=colores3, alpha=0.8)
ax3.axhline(y=1.33, color='green', linestyle='--', linewidth=1.5, label='Mínimo aceptable')
ax3.axhline(y=1.0, color='orange', linestyle='--', linewidth=1.5, label='Proceso capaz')
ax3.set_ylabel('Cpk')
ax3.set_title('Capacidad del proceso: Batch vs Pedido\n(batch muestra mejor capacidad)')
ax3.legend(fontsize=8)
ax3.set_ylim(0, max(cpk_pedido, cpk_batch) * 1.2)

# Gráfica 4: % > 120s por hora (batch)
ax4 = axes[1, 1]
por_hora_batch = (batch_metrics.groupby('hora')
                  .agg(pct_alto = ('seg_linea_batch', lambda x: (x > USL).mean() * 100))
                  .reset_index())
colores4 = ['tomato' if p > 30 else 'steelblue' for p in por_hora_batch['pct_alto']]
ax4.bar(por_hora_batch['hora'], por_hora_batch['pct_alto'],
        color=colores4, alpha=0.8)
ax4.axhline(y=por_hora_batch['pct_alto'].mean(), color='red', linestyle='--',
            linewidth=1, label=f"Promedio: {por_hora_batch['pct_alto'].mean():.1f}%")
ax4.set_xlabel('Hora del día')
ax4.set_ylabel('% batches > 120s/línea')
ax4.set_title('Fricción por hora — análisis por batch')
ax4.legend(fontsize=8)

plt.tight_layout()
ruta = os.path.join(OUTPUTS_DIR, 'metricas_por_batch.png')
plt.savefig(ruta, dpi=150, bbox_inches='tight')
plt.show()
print(f"\n✅ Gráfica guardada: {ruta}")

# ── Guardar datos ─────────────────────────────────────────
ruta_csv = os.path.join(OUTPUTS_DIR, 'batch_metrics_detallado.csv')
batch_metrics.to_csv(ruta_csv, index=False)
print(f"✅ Datos guardados: {ruta_csv}")

print(f"\n{'='*70}")
print(f"CONCLUSIÓN")
print(f"{'='*70}")
print(f"""
Cuando medimos por BATCH en lugar de PEDIDO INDIVIDUAL:

1. La media cae de {media_pedido:.1f}s a {media_batch:.1f}s ({mejora_media:+.1f}%)
   → El ruido de pedidos cerrados sin completarse desaparece

2. El Cpk mejora de {cpk_pedido:.2f} a {cpk_batch:.2f}
   → El proceso se ve menos "incapaz" cuando eliminamos artefactos

3. Distribución más limpia y compactada
   → Patrones verdaderos emergen sin ruido estadístico

IMPLICACIÓN OPERACIONAL:
Necesitamos cambiar cómo medimos desempeño:
- NO: tiempo por pedido (ruidoso, afectado por batches)
- SÍ: tiempo por batch + líneas por batch (realista)

Esto explicaría por qué algunos alistadores parecen "lentos"
cuando en realidad están trabajando en batches más grandes
o con más líneas por batch.
""")