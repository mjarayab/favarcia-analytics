"""
=============================================================
FAVARCIA — ANÁLISIS DE ERRORES
=============================================================
Cruza datos de errores en alisto y errores en chequeo
con el volumen real de pedidos por alistador.

Hipótesis a verificar:
- Los errores son proporcionales al volumen (no individuales)
- Los alistadores con más fricción cometen más errores
- Los errores al cliente son una fracción pequeña del total

Limitación conocida:
- Errores de alisto vienen como totales acumulados sin fecha
- El sistema WMS recién comenzó a registrar errores
- La mayoría de valores son 0 por ser datos incompletos
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

archivo = os.path.join(DATA_DIR, "FPM_Datos.xlsx")

# ── Cargar las tres hojas ─────────────────────────────────
print("📊 Cargando datos...")
df_pedidos     = pd.read_excel(archivo, sheet_name=0)
df_err_alisto  = pd.read_excel(archivo, sheet_name=1)
df_err_chequeo = pd.read_excel(archivo, sheet_name=2)

print(f"✅ Pedidos:          {len(df_pedidos):,} filas")
print(f"✅ Errores alisto:   {len(df_err_alisto):,} filas")
print(f"✅ Errores chequeo:  {len(df_err_chequeo):,} filas")

# ── Estandarizar columnas ─────────────────────────────────
df_pedidos.columns = (df_pedidos.columns.str.lower().str.strip()
                      .str.replace(' ', '_').str.replace('(','').str.replace(')',''))
df_pedidos = df_pedidos.rename(columns={'alistador': 'picker_id',
                                         'tiempo_alisto_minutos': 'tiempo_minutos'})
df_pedidos = df_pedidos.dropna(subset=['picker_id'])

df_err_alisto.columns = (df_err_alisto.columns.str.lower().str.strip()
                          .str.replace(' ', '_').str.replace('(','').str.replace(')',''))
df_err_alisto = df_err_alisto.rename(columns={'alistador': 'picker_id'})

df_err_chequeo.columns = (df_err_chequeo.columns.str.lower().str.strip()
                           .str.replace(' ', '_').str.replace('(','').str.replace(')',''))
df_err_chequeo = df_err_chequeo.rename(columns={'alistador': 'picker_id'})

# ── Mapeo de nombres ──────────────────────────────────────
mapeo_nombres = {}
for picker in df_pedidos['picker_id'].unique():
    nombres = df_pedidos[df_pedidos['picker_id'] == picker]['nombre'].dropna()
    if len(nombres) > 0:
        palabras = str(nombres.iloc[0]).split()
        if len(palabras) >= 3:
            mapeo_nombres[picker] = f"{palabras[2].capitalize()} ({picker})"
        else:
            mapeo_nombres[picker] = picker

# ── Volumen real por alistador ────────────────────────────
vol = (df_pedidos.groupby('picker_id')
       .agg(total_pedidos = ('picker_id', 'count'),
            total_lineas  = ('cant_lineas', 'sum'))
       .reset_index())

# ── Errores de alisto — totales acumulados ────────────────
print(f"\n{'='*55}")
print(f"ERRORES EN ALISTO (totales acumulados)")
print(f"{'='*55}")

# Sumar todos los tipos de error por alistador
cols_error = [c for c in df_err_alisto.columns
              if 'error' in c and c not in ['picker_id', 'nombre']]

df_err_alisto['total_errores'] = df_err_alisto[cols_error].sum(axis=1)

# Filtrar solo alistadores con al menos 1 error
con_errores = df_err_alisto[df_err_alisto['total_errores'] > 0].copy()
con_errores['etiqueta'] = con_errores['picker_id'].map(mapeo_nombres).fillna(
    con_errores['picker_id'])

print(f"\nAlistadores con errores registrados: {len(con_errores)}")
print(f"Total errores de faltantes:  {df_err_alisto[cols_error[0]].sum():.0f}")
if len(cols_error) > 1:
    print(f"Total errores sobrantes:     {df_err_alisto[cols_error[1]].sum():.0f}")
if len(cols_error) > 2:
    print(f"Total mercaderia erronea:    {df_err_alisto[cols_error[2]].sum():.0f}")
print(f"TOTAL ERRORES ALISTO:        {df_err_alisto['total_errores'].sum():.0f}")

# Cruzar con volumen
err_vol = vol.merge(
    df_err_alisto[['picker_id', 'total_errores'] + cols_error],
    on='picker_id', how='left'
)
err_vol['total_errores'] = err_vol['total_errores'].fillna(0)
err_vol['tasa_error'] = err_vol['total_errores'] / err_vol['total_pedidos'] * 100
err_vol['etiqueta'] = err_vol['picker_id'].map(mapeo_nombres).fillna(err_vol['picker_id'])
err_vol = err_vol.sort_values('total_errores', ascending=False)

print(f"\n{'Nombre':25} {'Pedidos':>8} {'Errores':>8} {'Tasa%':>7}")
print("-" * 55)
for _, row in err_vol[err_vol['total_errores'] > 0].head(15).iterrows():
    print(f"{row['etiqueta']:25} {row['total_pedidos']:>8,} "
          f"{row['total_errores']:>8.0f} {row['tasa_error']:>6.2f}%")

# ── Errores de chequeo — por fecha ────────────────────────
print(f"\n{'='*55}")
print(f"ERRORES EN CHEQUEO (llegaron al cliente)")
print(f"{'='*55}")

col_err_chq = [c for c in df_err_chequeo.columns
               if 'error' in c and c not in ['picker_id', 'nombre', 'fecha_cliente']]

df_err_chequeo['errores_cliente'] = df_err_chequeo[col_err_chq].sum(axis=1)
total_cliente = df_err_chequeo['errores_cliente'].sum()

print(f"\nTotal errores que llegaron al cliente: {total_cliente:.0f}")
print(f"Alistadores con errores al cliente: "
      f"{len(df_err_chequeo[df_err_chequeo['errores_cliente'] > 0])}")

# Agrupar por alistador
err_chq_picker = (df_err_chequeo.groupby('picker_id')['errores_cliente']
                  .sum()
                  .reset_index())
err_chq_picker = err_chq_picker[err_chq_picker['errores_cliente'] > 0]
err_chq_picker['etiqueta'] = err_chq_picker['picker_id'].map(mapeo_nombres).fillna(
    err_chq_picker['picker_id'])
err_chq_picker = err_chq_picker.sort_values('errores_cliente', ascending=False)

print(f"\n{'Nombre':25} {'Errores al cliente':>18}")
print("-" * 45)
for _, row in err_chq_picker.iterrows():
    print(f"{row['etiqueta']:25} {row['errores_cliente']:>18.0f}")

# ── Análisis sistémico: errores vs volumen ────────────────
print(f"\n{'='*55}")
print(f"ANÁLISIS: ERRORES vs VOLUMEN")
print(f"{'='*55}")

from scipy import stats
err_analisis = err_vol[err_vol['total_pedidos'] >= 100].copy()
corr, pval = stats.pearsonr(err_analisis['total_pedidos'],
                             err_analisis['total_errores'])
print(f"\nCorrelación volumen vs errores: r = {corr:.3f}")
print(f"P-value: {pval:.4f}")
if pval < 0.05:
    print(f"→ Correlación estadísticamente significativa")
    if corr > 0.5:
        print(f"→ Los errores aumentan con el volumen — problema SISTÉMICO")
    else:
        print(f"→ Correlación débil — hay otros factores")
else:
    print(f"→ No hay correlación significativa")

# ── GRÁFICAS ──────────────────────────────────────────────
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle('FAVARCIA — Análisis de Errores\n'
             'Errores en alisto y errores al cliente',
             fontsize=13, fontweight='bold')

# Gráfica 1: Errores totales por alistador
ax1 = axes[0, 0]
top_err = err_vol[err_vol['total_errores'] > 0].head(15).sort_values('total_errores')
ax1.barh(top_err['etiqueta'], top_err['total_errores'],
         color='tomato', alpha=0.8)
for i, (_, row) in enumerate(top_err.iterrows()):
    ax1.text(row['total_errores'] + 0.1, i,
             f"{row['total_errores']:.0f}", va='center', fontsize=8)
ax1.set_xlabel('Total errores')
ax1.set_title('Total errores en alisto\n(absolutos)')

# Gráfica 2: Tasa de error por alistador
ax2 = axes[0, 1]
top_tasa = err_vol[err_vol['total_pedidos'] >= 100].sort_values('tasa_error',
                                                                  ascending=False).head(15)
top_tasa = top_tasa.sort_values('tasa_error')
colores_tasa = ['tomato' if t > 2 else 'orange' if t > 1 else 'steelblue'
                for t in top_tasa['tasa_error']]
ax2.barh(top_tasa['etiqueta'], top_tasa['tasa_error'],
         color=colores_tasa, alpha=0.8)
ax2.axvline(x=err_vol['tasa_error'].mean(), color='red',
            linestyle='--', linewidth=1,
            label=f"Promedio: {err_vol['tasa_error'].mean():.1f}%")
ax2.set_xlabel('% errores / pedidos')
ax2.set_title('Tasa de error por alistador\n(normalizado por volumen)')
ax2.legend(fontsize=8)

# Gráfica 3: Scatter errores vs volumen
ax3 = axes[1, 0]
ax3.scatter(err_analisis['total_pedidos'], err_analisis['total_errores'],
            color='steelblue', s=60, alpha=0.7)
for _, row in err_analisis[err_analisis['total_errores'] > 0].iterrows():
    ax3.annotate(row['etiqueta'],
                 (row['total_pedidos'], row['total_errores']),
                 textcoords='offset points', xytext=(3, 3), fontsize=7)
# Línea de tendencia
z = np.polyfit(err_analisis['total_pedidos'], err_analisis['total_errores'], 1)
p = np.poly1d(z)
x_line = np.linspace(err_analisis['total_pedidos'].min(),
                     err_analisis['total_pedidos'].max(), 100)
ax3.plot(x_line, p(x_line), 'r--', linewidth=1.5,
         label=f'Tendencia (r={corr:.2f})')
ax3.set_xlabel('Total pedidos (volumen real)')
ax3.set_ylabel('Total errores')
ax3.set_title('Errores vs Volumen\n(si la tendencia sube = problema sistémico)')
ax3.legend(fontsize=8)

# Gráfica 4: Errores al cliente por alistador
ax4 = axes[1, 1]
if len(err_chq_picker) > 0:
    err_chq_picker_plot = err_chq_picker.sort_values('errores_cliente')
    ax4.barh(err_chq_picker_plot['etiqueta'],
             err_chq_picker_plot['errores_cliente'],
             color='tomato', alpha=0.8)
    ax4.set_xlabel('Errores que llegaron al cliente')
    ax4.set_title(f'Errores al cliente\n(total: {total_cliente:.0f})')
else:
    ax4.text(0.5, 0.5, 'Sin errores al cliente\nregistrados',
             ha='center', va='center', fontsize=12)
    ax4.set_title('Errores al cliente')

plt.tight_layout()
ruta = os.path.join(OUTPUTS_DIR, 'analisis_errores.png')
plt.savefig(ruta, dpi=150, bbox_inches='tight')
plt.show()
print(f"\n✅ Gráfica guardada: {ruta}")

print(f"\n{'='*55}")
print(f"LIMITACIONES DEL ANÁLISIS DE ERRORES")
print(f"{'='*55}")
print(f"1. Errores de alisto son totales acumulados sin fecha")
print(f"   No se pueden cruzar con períodos específicos")
print(f"2. El WMS recién comenzó a registrar errores")
print(f"   La mayoría de valores son 0 — datos incompletos")
print(f"3. Los errores detectados en bodega no están aquí")
print(f"   Solo errores que llegaron al cliente en hoja 3")
print(f"4. Con más datos históricos el análisis será más preciso")