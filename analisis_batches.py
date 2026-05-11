"""
=============================================================
FAVARCIA — ANÁLISIS DE BATCHES DE PEDIDOS
=============================================================
Detecta cuando un alistador abre/cierra varios pedidos en
secuencia rápida (batch) en vez de uno por uno.

Un batch típico:
  14:23:10 — cierra pedido A
  14:23:45 — cierra pedido B (gap 35s)
  14:24:20 — cierra pedido C (gap 35s)
  14:24:55 — cierra pedido D (gap 35s)
  14:30:10 — cierra pedido E (gap 5m) ← quiebra patrón

Pedidos A-D = 1 batch
Pedido E = 1 batch separado

Este análisis permite calcular métricas reales por batch
en vez de métricas distorsionadas por pedido individual.
=============================================================
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from datetime import datetime

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
})
df = df.dropna(subset=['picker_id'])

# Convertir fecha de cierre
df['fin_dt'] = pd.to_datetime(df['fin_alisto'], errors='coerce')
df['fecha']  = df['fin_dt'].dt.date
df['hora']   = df['fin_dt'].dt.hour

print(f"✅ {len(df):,} pedidos cargados")

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

# ── Detectar batches ──────────────────────────────────────
print(f"\n📊 Detectando batches de pedidos...")

UMBRAL_GAP = 120  # gap máximo en segundos para considerar batch (2 minutos)

batch_records = []
batch_counter = 0

for picker in df['picker_id'].unique():
    picker_df = (df[df['picker_id'] == picker]
                 .sort_values('fin_dt')
                 .reset_index(drop=True))

    if len(picker_df) < 1:
        continue

    current_batch = [picker_df.iloc[0].to_dict()]
    batch_id = f"{picker}-{batch_counter}"
    batch_counter += 1

    for i in range(1, len(picker_df)):
        pedido_actual = picker_df.iloc[i]
        pedido_anterior = picker_df.iloc[i-1]

        fin_anterior = pedido_anterior['fin_dt']
        fin_actual   = pedido_actual['fin_dt']

        # Solo mismo día
        if fin_anterior.date() != fin_actual.date():
            # Guardar batch anterior
            batch_records.append({
                'picker_id':     picker,
                'etiqueta':      mapeo_nombres.get(picker, picker),
                'batch_id':      batch_id,
                'fecha':         fin_anterior.date(),
                'hora':          fin_anterior.hour,
                'cant_pedidos':  len(current_batch),
                'tiempo_total_min': (current_batch[-1]['fin_dt'] - 
                                    current_batch[0]['fin_dt']).total_seconds() / 60,
                'fin_inicio':    current_batch[0]['fin_dt'],
                'fin_final':     current_batch[-1]['fin_dt'],
            })
            # Nuevo batch
            current_batch = [pedido_actual.to_dict()]
            batch_id = f"{picker}-{batch_counter}"
            batch_counter += 1
            continue

        # Calcular gap entre cierres
        gap_segundos = (fin_actual - fin_anterior).total_seconds()

        if gap_segundos <= UMBRAL_GAP:
            # Parte del batch actual
            current_batch.append(pedido_actual.to_dict())
        else:
            # Gap grande → fin del batch
            batch_records.append({
                'picker_id':     picker,
                'etiqueta':      mapeo_nombres.get(picker, picker),
                'batch_id':      batch_id,
                'fecha':         fin_anterior.date(),
                'hora':          fin_anterior.hour,
                'cant_pedidos':  len(current_batch),
                'tiempo_total_min': (current_batch[-1]['fin_dt'] - 
                                    current_batch[0]['fin_dt']).total_seconds() / 60,
                'fin_inicio':    current_batch[0]['fin_dt'],
                'fin_final':     current_batch[-1]['fin_dt'],
            })
            # Nuevo batch
            current_batch = [pedido_actual.to_dict()]
            batch_id = f"{picker}-{batch_counter}"
            batch_counter += 1

    # Guardar último batch
    if current_batch:
        batch_records.append({
            'picker_id':     picker,
            'etiqueta':      mapeo_nombres.get(picker, picker),
            'batch_id':      batch_id,
            'fecha':         current_batch[-1]['fin_dt'].date(),
            'hora':          current_batch[-1]['fin_dt'].hour,
            'cant_pedidos':  len(current_batch),
            'tiempo_total_min': (current_batch[-1]['fin_dt'] - 
                                current_batch[0]['fin_dt']).total_seconds() / 60,
            'fin_inicio':    current_batch[0]['fin_dt'],
            'fin_final':     current_batch[-1]['fin_dt'],
        })

df_batches = pd.DataFrame(batch_records)

print(f"✅ {len(df_batches):,} batches detectados")
print(f"   Promedio pedidos por batch: {df_batches['cant_pedidos'].mean():.1f}")

# ── Análisis ──────────────────────────────────────────────
print(f"\n{'='*60}")
print(f"ANÁLISIS DE BATCHES")
print(f"{'='*60}")

# Top alistadores que usan batches
print(f"\n📊 Alistadores con más batches:")
batches_por_picker = (df_batches.groupby(['picker_id', 'etiqueta'])
                      .agg(
                          total_batches     = ('batch_id', 'count'),
                          pedidos_totales   = ('cant_pedidos', 'sum'),
                          pedidos_promedio  = ('cant_pedidos', 'mean'),
                          pct_batch_multi   = ('cant_pedidos', 
                                              lambda x: (x > 1).mean() * 100),
                      )
                      .reset_index()
                      .sort_values('total_batches', ascending=False))

print(f"\n{'Nombre':25} {'Batches':>8} {'Ped/B':>7} {'%Multi':>7}")
print("-" * 55)
for _, row in batches_por_picker.head(15).iterrows():
    print(f"{row['etiqueta']:25} {row['total_batches']:>8.0f} "
          f"{row['pedidos_promedio']:>6.1f}  {row['pct_batch_multi']:>6.1f}%")

# Distribución de tamaños de batch
print(f"\n{'='*60}")
print(f"DISTRIBUCIÓN DE TAMAÑO DE BATCH")
print(f"{'='*60}")

dist_batch = (df_batches['cant_pedidos']
              .value_counts()
              .sort_index())

print(f"\n{'Tamaño batch':>15} {'Cantidad':>12} {'%':>6}")
print("-" * 40)
for tamaño, cant in dist_batch.items():
    pct = cant / len(df_batches) * 100
    print(f"{tamaño:>15} pedidos  {cant:>12,}  {pct:>5.1f}%")

# Batches de múltiples pedidos
batches_multi = df_batches[df_batches['cant_pedidos'] > 1]
print(f"\n{'='*60}")
print(f"BATCHES CON MÚLTIPLES PEDIDOS (>1)")
print(f"{'='*60}")
print(f"   Total batches multi: {len(batches_multi):,}")
print(f"   % del total: {len(batches_multi)/len(df_batches)*100:.1f}%")
print(f"   Promedio pedidos en batch multi: {batches_multi['cant_pedidos'].mean():.1f}")
print(f"   Máximo: {batches_multi['cant_pedidos'].max():.0f} pedidos en un batch")

# ── GRÁFICAS ──────────────────────────────────────────────
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle('FAVARCIA — Análisis de Batches de Pedidos\n'
             'Detectando pedidos abiertos/cerrados en secuencia',
             fontsize=13, fontweight='bold')

# Gráfica 1: Distribución de tamaño de batch
ax1 = axes[0, 0]
dist_batch_sorted = dist_batch.sort_index()
colores1 = ['tomato' if t > 1 else 'steelblue' for t in dist_batch_sorted.index]
ax1.bar(dist_batch_sorted.index, dist_batch_sorted.values,
        color=colores1, alpha=0.8)
ax1.set_xlabel('Pedidos por batch')
ax1.set_ylabel('Cantidad de batches')
ax1.set_title('Distribución de tamaño de batch\n(rojo = múltiples pedidos)')
ax1.set_xticks(range(1, dist_batch_sorted.index.max() + 1))

# Gráfica 2: % de batches multi por alistador (top 15)
ax2 = axes[0, 1]
top_pct = batches_por_picker.head(15).sort_values('pct_batch_multi')
colores2 = ['tomato' if p > 20 else 'steelblue'
            for p in top_pct['pct_batch_multi']]
ax2.barh(top_pct['etiqueta'], top_pct['pct_batch_multi'],
         color=colores2, alpha=0.8)
ax2.axvline(x=batches_por_picker['pct_batch_multi'].mean(),
            color='red', linestyle='--', linewidth=1,
            label=f"Promedio: {batches_por_picker['pct_batch_multi'].mean():.1f}%")
ax2.set_xlabel('% batches con múltiples pedidos')
ax2.set_title('Quiénes usan más batches\n(rojo = más del 20%)')
ax2.legend(fontsize=8)

# Gráfica 3: Total batches por alistador (top 15)
ax3 = axes[1, 0]
top_batches = batches_por_picker.head(15).sort_values('total_batches')
ax3.barh(top_batches['etiqueta'], top_batches['total_batches'],
         color='steelblue', alpha=0.8)
ax3.set_xlabel('Total de batches')
ax3.set_title('Volumen de batches por alistador\n(top 15)')

# Gráfica 4: Batches por hora del día
ax4 = axes[1, 1]
batches_hora = (df_batches.groupby('hora')
                .agg(
                    total_batches = ('batch_id', 'count'),
                    pct_multi     = ('cant_pedidos', lambda x: (x > 1).mean() * 100)
                )
                .reset_index())
colores4 = ['tomato' if p > batches_hora['pct_multi'].mean() else 'steelblue'
            for p in batches_hora['pct_multi']]
ax4.bar(batches_hora['hora'], batches_hora['pct_multi'],
        color=colores4, alpha=0.8)
ax4.axhline(y=batches_hora['pct_multi'].mean(),
            color='red', linestyle='--', linewidth=1,
            label=f"Promedio: {batches_hora['pct_multi'].mean():.1f}%")
ax4.set_xlabel('Hora del día')
ax4.set_ylabel('% batches con múltiples pedidos')
ax4.set_title('Batches múltiples por hora\n(¿cuándo más se agrupan pedidos?)')
ax4.legend(fontsize=8)

plt.tight_layout()
ruta = os.path.join(OUTPUTS_DIR, 'analisis_batches.png')
plt.savefig(ruta, dpi=150, bbox_inches='tight')
plt.show()
print(f"\n✅ Gráfica guardada: {ruta}")

# ── Guardar datos de batches ──────────────────────────────
ruta_csv = os.path.join(OUTPUTS_DIR, 'batches_detallado.csv')
df_batches.to_csv(ruta_csv, index=False)
print(f"✅ Datos de batches guardados: {ruta_csv}")

print(f"\n{'='*60}")
print(f"INTERPRETACIÓN")
print(f"{'='*60}")
print(f"""
Un "batch" es un lote de pedidos que un alistador abre y cierra
en secuencia rápida (gap < 2 minutos entre cierres).

PATRONES A OBSERVAR:

1. Alistadores con alto % de batches multi:
   → Probablemente trabajan varios pedidos juntos
   → Las métricas individuales por pedido están distorsionadas
   → Necesitamos analizar tiempos de BATCH, no de pedido

2. Horas con más batches multi:
   → Horarios de presión (cerca de deadline de rutas)
   → O alistadores amontonándose para cerrar rápido

3. Tamaño típico de batch:
   → Si la mayoría son 1 = alisten pedidos individuales
   → Si la mayoría son 2-3+ = sistema de trabajo por lotes

PRÓXIMO PASO:
Crear script de análisis por BATCH en vez de por PEDIDO.
Esto daría métricas mucho más precisas de desempeño real.
""")