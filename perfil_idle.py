"""
=============================================================
FAVARCIA — PERFIL DE IDLE TIME INDIVIDUAL
=============================================================
Muestra el patrón de tiempo idle entre pedidos para un
alistador específico.

Uso:
    python perfil_idle.py EM196
    python perfil_idle.py EM239
=============================================================
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import sys

# ── Argumento ─────────────────────────────────────────────
if len(sys.argv) < 2:
    print("❌ Uso: python perfil_idle.py EM196")
    sys.exit(1)

PICKER_ID = sys.argv[1].upper()

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
    'inicio_alisto':         'inicio_alisto',
    'fin_alisto':            'fin_alisto',
})
df = df.dropna(subset=['picker_id'])

# Verificar que el picker existe
if PICKER_ID not in df['picker_id'].values:
    print(f"❌ Alistador {PICKER_ID} no encontrado.")
    print(f"   Disponibles: {sorted(df['picker_id'].unique())}")
    sys.exit(1)

# Nombre del picker
nombres = df[df['picker_id'] == PICKER_ID]['nombre'].dropna()
if len(nombres) > 0:
    palabras = str(nombres.iloc[0]).split()
    nombre = palabras[2].capitalize() if len(palabras) >= 3 else PICKER_ID
else:
    nombre = PICKER_ID

print(f"\n👤 Perfil idle: {nombre} ({PICKER_ID})")

# ── Filtrar pedidos con tiempo registrado ─────────────────
df['inicio_dt'] = pd.to_datetime(df['inicio_alisto'], errors='coerce')
df['fin_dt']    = pd.to_datetime(df['fin_alisto'],    errors='coerce')

df_picker = df[
    (df['picker_id'] == PICKER_ID) &
    df['inicio_dt'].notna() &
    df['fin_dt'].notna() &
    (df['tiempo_minutos'] > 0)
].sort_values('inicio_dt').reset_index(drop=True)

print(f"   Pedidos con tiempo registrado: {len(df_picker):,}")

if len(df_picker) < 2:
    print("❌ No hay suficientes pedidos para calcular idle.")
    sys.exit(1)

# ── Calcular idle ─────────────────────────────────────────
idle_records = []
for i in range(1, len(df_picker)):
    fin_anterior  = df_picker.loc[i-1, 'fin_dt']
    inicio_actual = df_picker.loc[i,   'inicio_dt']

    # Solo mismo día
    if fin_anterior.date() != inicio_actual.date():
        continue

    idle_min = (inicio_actual - fin_anterior).total_seconds() / 60

    if 0 <= idle_min <= 60:
        idle_records.append({
            'fecha':      fin_anterior.date(),
            'hora':       fin_anterior.hour,
            'idle_min':   idle_min,
            'fin_ant':    fin_anterior,
            'ini_act':    inicio_actual,
        })

df_idle = pd.DataFrame(idle_records)

if len(df_idle) == 0:
    print("❌ No se encontraron gaps válidos.")
    sys.exit(1)

print(f"   Gaps idle válidos (0-60 min): {len(df_idle):,}")

# ── Estadísticas ──────────────────────────────────────────
print(f"\n{'='*55}")
print(f"ESTADÍSTICAS DE IDLE — {nombre} ({PICKER_ID})")
print(f"{'='*55}")
print(f"   Mediana:          {df_idle['idle_min'].median():.1f} min")
print(f"   Promedio:         {df_idle['idle_min'].mean():.1f} min")
print(f"   P75:              {df_idle['idle_min'].quantile(0.75):.1f} min")
print(f"   P90:              {df_idle['idle_min'].quantile(0.90):.1f} min")
print(f"   Máximo:           {df_idle['idle_min'].max():.1f} min")
print(f"   % gaps > 10 min:  {(df_idle['idle_min'] > 10).mean()*100:.1f}%")
print(f"   % gaps > 15 min:  {(df_idle['idle_min'] > 15).mean()*100:.1f}%")
print(f"   % gaps > 30 min:  {(df_idle['idle_min'] > 30).mean()*100:.1f}%")

# Mediana por hora
print(f"\n{'='*55}")
print(f"IDLE POR HORA DEL DÍA")
print(f"{'='*55}")
por_hora = df_idle.groupby('hora').agg(
    mediana = ('idle_min', 'median'),
    gaps    = ('idle_min', 'count'),
    pct_15  = ('idle_min', lambda x: (x > 15).mean() * 100)
).reset_index()

print(f"\n{'Hora':>6}  {'Mediana':>8}  {'Gaps':>6}  {'%>15min':>8}")
print("-" * 40)
for _, row in por_hora.iterrows():
    alerta = " ⚠️" if row['mediana'] > 15 else ""
    print(f"  {row['hora']:>4}h  {row['mediana']:>7.1f}m  "
          f"{row['gaps']:>6.0f}  {row['pct_15']:>7.1f}%{alerta}")

# Top 10 gaps más largos
print(f"\n{'='*55}")
print(f"TOP 10 GAPS MÁS LARGOS")
print(f"{'='*55}")
top_gaps = df_idle.nlargest(10, 'idle_min')[['fecha', 'hora', 'idle_min']]
print(f"\n{'Fecha':>12}  {'Hora':>5}  {'Idle':>8}")
print("-" * 35)
for _, row in top_gaps.iterrows():
    print(f"  {str(row['fecha']):>12}  {row['hora']:>4}h  {row['idle_min']:>7.1f} min")

# ── GRÁFICAS ──────────────────────────────────────────────
fig, axes = plt.subplots(2, 2, figsize=(13, 9))
fig.suptitle(f'FAVARCIA — Perfil Idle: {nombre} ({PICKER_ID})\n'
             f'Tiempo entre FIN de un pedido e INICIO del siguiente',
             fontsize=13, fontweight='bold')

mediana_global = df_idle['idle_min'].median()

# Gráfica 1: Distribución de idle
ax1 = axes[0, 0]
ax1.hist(df_idle['idle_min'], bins=40,
         color='steelblue', alpha=0.7, edgecolor='white')
ax1.axvline(x=mediana_global, color='black', linewidth=1.5,
            label=f'Mediana: {mediana_global:.1f} min')
ax1.axvline(x=10, color='orange', linewidth=1.5, linestyle='--',
            label='10 min')
ax1.axvline(x=15, color='red', linewidth=1.5, linestyle='--',
            label='15 min')
ax1.set_xlabel('Minutos idle')
ax1.set_ylabel('Frecuencia')
ax1.set_title('Distribución de tiempo idle')
ax1.legend(fontsize=8)

# Gráfica 2: Mediana idle por hora del día
ax2 = axes[0, 1]
colores = ['tomato' if m > 15 else
           'orange' if m > 10 else 'steelblue'
           for m in por_hora['mediana']]
ax2.bar(por_hora['hora'], por_hora['mediana'],
        color=colores, alpha=0.8)
ax2.axhline(y=10, color='orange', linestyle='--',
            linewidth=1.5, label='10 min')
ax2.axhline(y=15, color='red', linestyle='--',
            linewidth=1.5, label='15 min')
ax2.set_xlabel('Hora del día')
ax2.set_ylabel('Mediana idle (min)')
ax2.set_title('Idle mediano por hora\n(rojo > 15min | naranja > 10min)')
ax2.legend(fontsize=8)

# Gráfica 3: % gaps > 15 min por hora
ax3 = axes[1, 0]
colores3 = ['tomato' if p > 30 else 'steelblue'
            for p in por_hora['pct_15']]
ax3.bar(por_hora['hora'], por_hora['pct_15'],
        color=colores3, alpha=0.8)
ax3.axhline(y=por_hora['pct_15'].mean(), color='red',
            linestyle='--', linewidth=1,
            label=f"Promedio: {por_hora['pct_15'].mean():.1f}%")
ax3.set_xlabel('Hora del día')
ax3.set_ylabel('% gaps > 15 min')
ax3.set_title('% de gaps > 15 min por hora\n(rojo = más del 30%)')
ax3.legend(fontsize=8)

# Gráfica 4: Idle a lo largo del tiempo (scatter)
ax4 = axes[1, 1]
colores4 = ['tomato' if v > 15 else
            'orange' if v > 10 else 'steelblue'
            for v in df_idle['idle_min']]
ax4.scatter(df_idle['fin_ant'], df_idle['idle_min'],
            c=colores4, alpha=0.4, s=15)
ax4.axhline(y=15, color='red', linestyle='--',
            linewidth=1, label='15 min')
ax4.set_xlabel('Fecha')
ax4.set_ylabel('Idle (min)')
ax4.set_title('Idle a lo largo del tiempo\n(¿hay períodos con más idle?)')
ax4.legend(fontsize=8)
plt.setp(ax4.xaxis.get_majorticklabels(), rotation=30, ha='right')

plt.tight_layout()
ruta = os.path.join(OUTPUTS_DIR, f'perfil_idle_{PICKER_ID}.png')
plt.savefig(ruta, dpi=150, bbox_inches='tight')
plt.show()
print(f"\n✅ Gráfica guardada: {ruta}")