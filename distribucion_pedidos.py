"""
=============================================================
FAVARCIA — DISTRIBUCIÓN DE PEDIDOS POR ALISTADOR
=============================================================
Responde: ¿Quién toma qué tipo de pedidos?

Hipótesis a verificar:
1. EM239 recibe pedidos pequeños por instrucción del supervisor
2. Los alistadores expertos toman pedidos más grandes
3. Hay alistadores que evitan pedidos complejos

Usa TODOS los pedidos incluyendo tiempo=0 — el volumen
real no depende de cuándo se abre el pedido.
=============================================================
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
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

df.columns = (df.columns
              .str.lower().str.strip()
              .str.replace(' ', '_')
              .str.replace('(', '').str.replace(')', ''))

df = df.rename(columns={
    'alistador':             'picker_id',
    'tiempo_alisto_minutos': 'tiempo_minutos',
    'fecha_pedido':          'fecha',
})

df = df.dropna(subset=['picker_id'])
print(f"✅ {len(df):,} pedidos cargados (incluyendo tiempo=0)")

# ── Top 15 alistadores por volumen total ──────────────────
top15 = (df.groupby('picker_id')
         .size()
         .nlargest(15)
         .index)

df_top = df[df['picker_id'].isin(top15)].copy()

# ── Métricas por alistador ────────────────────────────────
resumen = df.groupby('picker_id').agg(
    total_pedidos    = ('picker_id', 'count'),
    lineas_promedio  = ('cant_lineas', 'mean'),
    lineas_mediana   = ('cant_lineas', 'median'),
    lineas_max       = ('cant_lineas', 'max'),
    unidades_promedio= ('cant_unidades', 'mean'),
    pct_sin_tiempo   = ('tiempo_minutos', lambda x: (x == 0).mean() * 100),
).reset_index()

resumen = resumen.sort_values('total_pedidos', ascending=False)

print(f"\n📋 DISTRIBUCIÓN DE PEDIDOS POR ALISTADOR (top 20 por volumen):")
print(f"{'Picker':8} {'Pedidos':>8} {'L.Prom':>7} {'L.Med':>6} {'L.Max':>6} {'%Sin T':>7}")
print("-" * 50)
for _, row in resumen.head(20).iterrows():
    print(f"{row['picker_id']:8} {row['total_pedidos']:>8,} "
          f"{row['lineas_promedio']:>7.1f} "
          f"{row['lineas_mediana']:>6.0f} "
          f"{row['lineas_max']:>6.0f} "
          f"{row['pct_sin_tiempo']:>6.1f}%")

# ── Detectar patrones de selección ───────────────────────
mediana_global = df['cant_lineas'].median()
promedio_global = df['cant_lineas'].mean()

print(f"\n📊 Referencia global:")
print(f"   Mediana de líneas por pedido: {mediana_global:.0f}")
print(f"   Promedio de líneas por pedido: {promedio_global:.1f}")

print(f"\n🔍 PATRONES DE SELECCIÓN:")
for _, row in resumen.head(20).iterrows():
    diff = row['lineas_mediana'] - mediana_global
    if diff < -mediana_global * 0.3:
        patron = f"⬇️  pedidos pequeños ({row['lineas_mediana']:.0f} líneas mediana)"
    elif diff > mediana_global * 0.3:
        patron = f"⬆️  pedidos grandes ({row['lineas_mediana']:.0f} líneas mediana)"
    else:
        patron = f"➡️  pedidos típicos ({row['lineas_mediana']:.0f} líneas mediana)"
    print(f"   {row['picker_id']}: {patron}")

# ── Gráficas ──────────────────────────────────────────────
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle('FAVARCIA — Distribución de Pedidos por Alistador\n'
             '¿Quién toma qué tipo de pedidos?',
             fontsize=13, fontweight='bold')

# Gráfica 1: Volumen total por alistador (top 15)
ax1 = axes[0, 0]
vol = resumen.head(15).sort_values('total_pedidos')
colores_vol = ['tomato' if p == 'EM239' else 'steelblue' for p in vol['picker_id']]
ax1.barh(vol['picker_id'], vol['total_pedidos'], color=colores_vol, alpha=0.8)
ax1.axvline(x=vol['total_pedidos'].mean(), color='red',
            linestyle='--', linewidth=1, label='Promedio')
ax1.set_xlabel('Total pedidos')
ax1.set_title('Volumen total por alistador\n(rojo = EM239)')
ax1.legend(fontsize=8)

# Gráfica 2: Mediana de líneas por pedido (top 15)
ax2 = axes[0, 1]
med = resumen.head(15).sort_values('lineas_mediana')
colores_med = ['tomato' if p == 'EM239' else 'steelblue' for p in med['picker_id']]
ax2.barh(med['picker_id'], med['lineas_mediana'], color=colores_med, alpha=0.8)
ax2.axvline(x=mediana_global, color='green', linestyle='--',
            linewidth=1.5, label=f'Global: {mediana_global:.0f} líneas')
ax2.set_xlabel('Mediana de líneas por pedido')
ax2.set_title('Complejidad de pedidos por alistador\n(rojo = EM239)')
ax2.legend(fontsize=8)

# Gráfica 3: % pedidos sin tiempo registrado
ax3 = axes[1, 0]
sin_t = resumen.head(15).sort_values('pct_sin_tiempo')
colores_st = ['tomato' if p in ['EM564', 'EM239'] else 'steelblue'
              for p in sin_t['picker_id']]
ax3.barh(sin_t['picker_id'], sin_t['pct_sin_tiempo'], color=colores_st, alpha=0.8)
ax3.axvline(x=resumen['pct_sin_tiempo'].mean(), color='red',
            linestyle='--', linewidth=1, label='Promedio')
ax3.set_xlabel('% pedidos sin tiempo registrado')
ax3.set_title('% trabajo invisible al WMS por alistador\n(rojo = EM564 y EM239)')
ax3.legend(fontsize=8)

# Gráfica 4: Boxplot de líneas por pedido (top 10)
ax4 = axes[1, 1]
top10 = resumen.nlargest(10, 'total_pedidos')['picker_id']
data_box = [df[df['picker_id'] == p]['cant_lineas'].values for p in top10]
bp = ax4.boxplot(data_box, labels=top10, patch_artist=True,
                 medianprops={'color': 'red', 'linewidth': 2})
for patch, picker in zip(bp['boxes'], top10):
    patch.set_facecolor('tomato' if picker == 'EM239' else 'steelblue')
    patch.set_alpha(0.6)
ax4.axhline(y=mediana_global, color='green', linestyle='--',
            linewidth=1.5, label=f'Mediana global: {mediana_global:.0f}')
ax4.set_ylabel('Líneas por pedido')
ax4.set_title('Distribución de tamaño de pedidos\n(top 10 por volumen)')
ax4.tick_params(axis='x', rotation=45)
ax4.legend(fontsize=8)

plt.tight_layout()
ruta = os.path.join(OUTPUTS_DIR, 'distribucion_pedidos.png')
plt.savefig(ruta, dpi=150, bbox_inches='tight')
plt.show()
print(f"\n✅ Gráfica guardada: {ruta}")