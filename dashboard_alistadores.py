"""
=============================================================
FAVARCIA — DASHBOARD DE ALISTADORES
=============================================================
Replica y mejora las gráficas del tablero del jefe:

1. Total pedidos por alistador (volumen real incluyendo tiempo=0)
2. Tiempo por línea por alistador (mediana, solo con tiempo registrado)
3. Volumen vs tiempo — scatter plot

La diferencia vs el tablero actual:
- Usa volumen REAL (no solo pedidos con tiempo registrado)
- Muestra MEDIANA en vez de promedio (robusta a outliers)
- Incluye nombres en vez de solo códigos
- Separa roles de apoyo visualmente
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

# ── Roles de apoyo ────────────────────────────────────────
ROLES_APOYO = ['EM039', 'EM560', 'EM289']

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
})
df = df.dropna(subset=['picker_id'])

# ── Mapeo de nombres ──────────────────────────────────────
mapeo_nombres = {}
for picker in df['picker_id'].unique():
    nombres = df[df['picker_id'] == picker]['nombre'].dropna()
    if len(nombres) > 0:
        palabras = str(nombres.iloc[0]).split()
        if len(palabras) >= 3:
            primer_nombre = palabras[2].capitalize()
            mapeo_nombres[picker] = f"{primer_nombre} ({picker})"
        else:
            mapeo_nombres[picker] = picker

# ── Datasets ──────────────────────────────────────────────
df_vol    = df.copy()
df_tiempo = df[df['tiempo_minutos'] > 0].copy()
df_tiempo['seg_por_linea'] = df_tiempo['tiempo_minutos'] * 60 / df_tiempo['cant_lineas']

# ── Métricas por alistador ────────────────────────────────
vol = (df_vol.groupby('picker_id')
       .agg(total_pedidos = ('picker_id', 'count'),
            total_lineas  = ('cant_lineas', 'sum'))
       .reset_index())

tiempo = (df_tiempo.groupby('picker_id')
          .agg(mediana_seg = ('seg_por_linea', 'median'))
          .reset_index())

resumen = vol.merge(tiempo, on='picker_id', how='left')
resumen['etiqueta'] = resumen['picker_id'].map(mapeo_nombres).fillna(resumen['picker_id'])
resumen['es_apoyo'] = resumen['picker_id'].isin(ROLES_APOYO)

# Filtrar alistadores con mínimo 50 pedidos
resumen = resumen[resumen['total_pedidos'] >= 50].copy()
resumen = resumen.sort_values('total_pedidos', ascending=False)

print(f"✅ {len(resumen)} alistadores con ≥50 pedidos")

# ── Métricas adicionales: pedidos SOLO con tiempo registrado ──
# Esto es lo que el jefe ve en su tablero actual
vol_con_tiempo = (df_tiempo.groupby('picker_id')
                  .size()
                  .reset_index(name='pedidos_con_tiempo'))

resumen = resumen.merge(vol_con_tiempo, on='picker_id', how='left')
resumen['pedidos_con_tiempo'] = resumen['pedidos_con_tiempo'].fillna(0)
resumen['pct_invisible'] = (
    (resumen['total_pedidos'] - resumen['pedidos_con_tiempo']) /
    resumen['total_pedidos'] * 100
)

# ── GRÁFICA 1: Comparación — Lo que el jefe ve vs la realidad ───
n_top = len(resumen)
alto1 = max(8, n_top * 0.45)
fig1, (ax1a, ax1b) = plt.subplots(1, 2, figsize=(18, alto1))
fig1.suptitle('TOTAL PEDIDOS POR ALISTADOR\n'
              'Lo que el jefe ve (izquierda) vs La realidad (derecha)',
              fontsize=13, fontweight='bold')

top20 = resumen.sort_values('total_pedidos')

colores_real = []
colores_jefe = []
for _, row in top20.iterrows():
    if row['es_apoyo']:
        colores_real.append('lightcoral')
        colores_jefe.append('lightcoral')
    elif row['picker_id'] == 'EM047':
        colores_real.append('gold')
        colores_jefe.append('gold')
    else:
        colores_real.append('steelblue')
        colores_jefe.append('steelblue')

# Panel izquierdo — Lo que ve el jefe (solo pedidos con tiempo)
bars_jefe = ax1a.barh(top20['etiqueta'], top20['pedidos_con_tiempo'],
                      color=colores_jefe, alpha=0.85)
for bar, (_, row) in zip(bars_jefe, top20.iterrows()):
    ax1a.text(bar.get_width() + 5, bar.get_y() + bar.get_height()/2,
              f"{int(row['pedidos_con_tiempo']):,}", va='center', fontsize=8)
ax1a.axvline(x=top20['pedidos_con_tiempo'].mean(), color='red',
             linestyle='--', linewidth=1.5,
             label=f"Promedio: {top20['pedidos_con_tiempo'].mean():.0f}")
ax1a.set_xlabel('Pedidos con tiempo registrado')
ax1a.set_title('Lo que el jefe ve\n(solo pedidos con tiempo en WMS)', fontsize=10)
ax1a.legend(fontsize=8)

# Panel derecho — La realidad (todos los pedidos)
bars_real = ax1b.barh(top20['etiqueta'], top20['total_pedidos'],
                      color=colores_real, alpha=0.85)
for bar, (_, row) in zip(bars_real, top20.iterrows()):
    ax1b.text(bar.get_width() + 5, bar.get_y() + bar.get_height()/2,
              f"{int(row['total_pedidos']):,}", va='center', fontsize=8)
ax1b.axvline(x=top20['total_pedidos'].mean(), color='red',
             linestyle='--', linewidth=1.5,
             label=f"Promedio: {top20['total_pedidos'].mean():.0f}")
ax1b.set_xlabel('Total pedidos (incluyendo tiempo=0)')
ax1b.set_title('La realidad\n(todos los pedidos incluyendo invisibles al WMS)', fontsize=10)
ax1b.legend(fontsize=8)

plt.tight_layout()
ruta1 = os.path.join(OUTPUTS_DIR, 'dashboard_total_pedidos.png')
plt.savefig(ruta1, dpi=150, bbox_inches='tight')
plt.show()
print(f"✅ Gráfica 1 guardada: {ruta1}")

# ── GRÁFICA 2: Comparación — Promedio (jefe) vs Mediana (realidad) ──
# Calcular también el promedio para comparar
tiempo_completo = (df_tiempo.groupby('picker_id')
                   .agg(mediana_seg2  = ('seg_por_linea', 'median'),
                        promedio_seg  = ('seg_por_linea', 'mean'))
                   .reset_index())

resumen2 = resumen.merge(tiempo_completo, on='picker_id', how='left')
res_t = resumen2[resumen2['mediana_seg2'].notna()].copy()
# Ordenar por mediana ascendente — mostrar los más rápidos
# Cesar y otros con outliers extremos quedan excluidos naturalmente
res_t_prom = res_t.sort_values('promedio_seg')
res_t_med  = res_t.sort_values('mediana_seg2')

n_pickers = len(res_t)
alto = max(8, n_pickers * 0.45)
fig2, (ax2a, ax2b) = plt.subplots(1, 2, figsize=(18, alto))
fig2.suptitle('TIEMPO POR LINEA POR ALISTADOR\n'
              'Lo que el jefe ve - Promedio (izquierda) vs La realidad - Mediana (derecha)',
              fontsize=13, fontweight='bold')

def color_tiempo(seg):
    if seg <= 60:   return 'green'
    if seg <= 90:   return 'steelblue'
    if seg <= 120:  return 'orange'
    return 'tomato'

# Panel izquierdo — Promedio (lo que usa el tablero del jefe)
colores_prom = [color_tiempo(v) for v in res_t_prom['promedio_seg']]
bars2a = ax2a.barh(res_t_prom['etiqueta'], res_t_prom['promedio_seg'],
                   color=colores_prom, alpha=0.85)
for bar, (_, row) in zip(bars2a, res_t_prom.iterrows()):
    ax2a.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2,
              f"{row['promedio_seg']:.0f}s", va='center', fontsize=8)
ax2a.axvline(x=60, color='green', linestyle='--', linewidth=2, label='Meta 60s')
ax2a.axvline(x=120, color='red', linestyle='--', linewidth=1.5, label='Umbral 120s')

# Detectar outlier más extremo automáticamente
max_picker  = res_t_prom.loc[res_t_prom['promedio_seg'].idxmax()]
max_nombre  = max_picker['etiqueta']
max_valor   = max_picker['promedio_seg']
escala_max  = res_t_prom['promedio_seg'].quantile(0.95) * 1.2

ax2a.set_xlim(0, escala_max)
if max_valor > escala_max:
    ax2a.annotate(
        f'{max_nombre}: {max_valor:.0f}s\n(fuera de escala — outlier)',
        xy=(escala_max * 0.98, 0.05),
        xycoords=('data', 'axes fraction'),
        fontsize=7, color='tomato', ha='right',
        bbox=dict(boxstyle='round,pad=0.3',
                  facecolor='lightyellow', alpha=0.8)
    )

ax2a.set_xlabel('Promedio de segundos por linea')
ax2a.set_title('Lo que el jefe ve\n(promedio — sensible a outliers)', fontsize=10)
ax2a.legend(fontsize=8)

# Panel derecho — Mediana (la realidad)
colores_med = [color_tiempo(v) for v in res_t_med['mediana_seg2']]
bars2b = ax2b.barh(res_t_med['etiqueta'], res_t_med['mediana_seg2'],
                   color=colores_med, alpha=0.85)
for bar, (_, row) in zip(bars2b, res_t_med.iterrows()):
    ax2b.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2,
              f"{row['mediana_seg2']:.0f}s", va='center', fontsize=8)
ax2b.axvline(x=60, color='green', linestyle='--', linewidth=2, label='Meta 60s')
ax2b.axvline(x=120, color='red', linestyle='--', linewidth=1.5, label='Umbral 120s')
ax2b.set_xlabel('Mediana de segundos por linea')
ax2b.set_title('La realidad\n(mediana — robusta a pedidos olvidados y agrupados)', fontsize=10)
ax2b.legend(fontsize=8)

plt.tight_layout()
ruta2 = os.path.join(OUTPUTS_DIR, 'dashboard_tiempo_linea.png')
plt.savefig(ruta2, dpi=150, bbox_inches='tight')
plt.show()
print(f"Grafica 2 guardada: {ruta2}")

# ── GRÁFICA 3: Volumen vs Tiempo scatter ──────────────────
fig3, ax3 = plt.subplots(figsize=(12, 8))

res_scatter = resumen[resumen['mediana_seg'].notna()].copy()

colores_scatter = ['lightcoral' if r else 'steelblue'
                   for r in res_scatter['es_apoyo']]

ax3.scatter(res_scatter['total_pedidos'],
            res_scatter['mediana_seg'],
            c=colores_scatter, s=80, alpha=0.8, zorder=3)

for _, row in res_scatter.iterrows():
    ax3.annotate(row['etiqueta'],
                 (row['total_pedidos'], row['mediana_seg']),
                 textcoords='offset points', xytext=(5, 3),
                 fontsize=7, alpha=0.8)

ax3.axhline(y=60, color='green', linestyle='--',
            linewidth=1.5, label='Meta 60s')
ax3.axhline(y=120, color='red', linestyle='--',
            linewidth=1, label='Umbral fricción 120s')

ax3.set_xlabel('Total pedidos (volumen real)')
ax3.set_ylabel('Mediana seg/línea')
ax3.set_title('VOLUMEN vs TIEMPO POR LÍNEA\n'
              'Ideal: esquina inferior derecha (alto volumen + bajo tiempo)',
              fontsize=11, fontweight='bold')
ax3.legend(fontsize=9)
ax3.grid(True, alpha=0.3)

plt.tight_layout()
ruta3 = os.path.join(OUTPUTS_DIR, 'dashboard_volumen_vs_tiempo.png')
plt.savefig(ruta3, dpi=150, bbox_inches='tight')
plt.show()
print(f"\n✅ DASHBOARD COMPLETO")
print(f"   {ruta1}")
print(f"   {ruta2}")
print(f"   {ruta3}")