"""
=============================================================
FAVARCIA — RANKING REAL DE ALISTADORES
=============================================================
Excluye roles de apoyo (gondoleros, montacargas, chequeadores)
y califica a los alistadores permanentes en 4 dimensiones:

1. VOLUMEN      — pedidos y líneas procesadas (contribución real)
2. CONSISTENCIA — qué tan predecible es su tiempo (baja variabilidad)
3. COMPLEJIDAD  — tamaño promedio de pedidos que maneja
4. REGISTRO     — qué tan bien usa el WMS (% con tiempo registrado)

Cada dimensión se normaliza 0-100 y se promedia ponderado.
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

# ── Roles de apoyo — excluir del ranking ─────────────────
ROLES_APOYO = {
    'EM039': 'Chequeador',
    'EM560': 'Gondolero/Publicidad',
    'EM289': 'Montacargas',
}

# Umbral mínimo de pedidos
MIN_PEDIDOS = 200

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

# ── Mapeo de códigos a nombres legibles ───────────────────
# Formato: "Mauricio (EM047)"
# Estructura del nombre: APELLIDO APELLIDO NOMBRE NOMBRE
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

# Excluir roles de apoyo
df_full = df[~df['picker_id'].isin(ROLES_APOYO.keys())].copy()
df_tiempo = df_full[df_full['tiempo_minutos'] > 0].copy()
df_tiempo['seg_por_linea'] = df_tiempo['tiempo_minutos'] * 60 / df_tiempo['cant_lineas']

print(f"✅ {len(df_full):,} pedidos (excluyendo roles de apoyo)")
print(f"   Roles excluidos: {', '.join([f'{k} ({v})' for k,v in ROLES_APOYO.items()])}")

# ── Calcular métricas por alistador ───────────────────────
vol = df_full.groupby('picker_id').agg(
    total_pedidos    = ('picker_id', 'count'),
    total_lineas     = ('cant_lineas', 'sum'),
    lineas_mediana   = ('cant_lineas', 'median'),
    pct_con_tiempo   = ('tiempo_minutos', lambda x: (x > 0).mean() * 100),
).reset_index()

tiempo = df_tiempo.groupby('picker_id').agg(
    mediana_seg      = ('seg_por_linea', 'median'),
    cv_tiempo        = ('seg_por_linea', lambda x: x.std() / x.mean() * 100),
).reset_index()

resumen = vol.merge(tiempo, on='picker_id', how='left')
resumen = resumen[resumen['total_pedidos'] >= MIN_PEDIDOS].copy()

print(f"\n   Alistadores con ≥{MIN_PEDIDOS} pedidos: {len(resumen)}")

# ── Calcular scores 0-100 ─────────────────────────────────
def normalizar(serie, mayor_es_mejor=True):
    mn, mx = serie.min(), serie.max()
    if mx == mn:
        return pd.Series([50] * len(serie), index=serie.index)
    norm = (serie - mn) / (mx - mn) * 100
    return norm if mayor_es_mejor else 100 - norm

resumen['score_volumen']      = (normalizar(resumen['total_pedidos']) * 0.5 +
                                  normalizar(resumen['total_lineas']) * 0.5)
resumen['score_consistencia'] = normalizar(resumen['cv_tiempo'], mayor_es_mejor=False)
resumen['score_complejidad']  = normalizar(resumen['lineas_mediana'])
resumen['score_registro']     = normalizar(resumen['pct_con_tiempo'])

resumen['score_final'] = (
    resumen['score_volumen']      * 0.35 +
    resumen['score_consistencia'] * 0.30 +
    resumen['score_complejidad']  * 0.20 +
    resumen['score_registro']     * 0.15
)

resumen = resumen.sort_values('score_final', ascending=False)

# Agregar etiqueta con nombre para gráficas
resumen['etiqueta'] = resumen['picker_id'].map(mapeo_nombres).fillna(resumen['picker_id'])

# ── Mostrar resultados ────────────────────────────────────
print(f"\n{'='*65}")
print(f"🏆 RANKING REAL DE ALISTADORES")
print(f"{'='*65}")
print(f"{'#':3} {'Picker':8} {'Pedidos':>8} {'Líneas':>8} "
      f"{'Med s/l':>8} {'CV%':>6} {'%Reg':>6} {'Score':>7}")
print("-" * 65)

for i, (_, row) in enumerate(resumen.head(15).iterrows(), 1):
    mediana = f"{row['mediana_seg']:.0f}s" if pd.notna(row['mediana_seg']) else "N/A"
    cv = f"{row['cv_tiempo']:.0f}%" if pd.notna(row['cv_tiempo']) else "N/A"
    medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i:2}."
    etiqueta = mapeo_nombres.get(row['picker_id'], row['picker_id'])
    print(f"{medal} {etiqueta:25} {row['total_pedidos']:>8,} "
          f"{row['total_lineas']:>8,} {mediana:>8} {cv:>6} "
          f"{row['pct_con_tiempo']:>5.1f}% {row['score_final']:>7.1f}")

# ── Top 5 detallado ───────────────────────────────────────
print(f"\n{'='*65}")
print(f"🔍 TOP 5 — ANÁLISIS DETALLADO")
print(f"{'='*65}")

for i, (_, row) in enumerate(resumen.head(5).iterrows(), 1):
    etiqueta = mapeo_nombres.get(row['picker_id'], row['picker_id'])
    print(f"\n#{i} {etiqueta}")
    print(f"   Volumen:      {row['total_pedidos']:,} pedidos | "
          f"{row['total_lineas']:,} líneas")
    print(f"   Tiempo:       {row['mediana_seg']:.0f}s/línea mediana | "
          f"CV={row['cv_tiempo']:.0f}%")
    print(f"   Complejidad:  {row['lineas_mediana']:.0f} líneas/pedido mediana")
    print(f"   Registro WMS: {row['pct_con_tiempo']:.1f}% pedidos con tiempo")
    print(f"   Score final:  {row['score_final']:.1f}/100")
    print(f"   Scores:  Vol={row['score_volumen']:.0f} | "
          f"Cons={row['score_consistencia']:.0f} | "
          f"Comp={row['score_complejidad']:.0f} | "
          f"Reg={row['score_registro']:.0f}")

# ── Gráfica ───────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(14, 7))
fig.suptitle('FAVARCIA — Ranking Real de Alistadores\n'
             '(excluyendo roles de apoyo | mínimo 200 pedidos)',
             fontsize=12, fontweight='bold')

top15 = resumen.head(15).sort_values('score_final')

# Gráfica 1: Score final
ax1 = axes[0]
colores = ['gold' if i >= len(top15)-3 else 'steelblue'
           for i in range(len(top15))]
bars = ax1.barh(top15['etiqueta'], top15['score_final'],
                color=colores, alpha=0.85)
ax1.set_xlabel('Score final (0-100)')
ax1.set_title('Score compuesto\n(volumen 35% + consistencia 30% +\ncomplej. 20% + registro 15%)')
for bar, (_, row) in zip(bars, top15.iterrows()):
    ax1.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2,
             f"{row['score_final']:.1f}", va='center', fontsize=8)

# Gráfica 2: Perfil de scores top 5
ax2 = axes[1]
top5 = resumen.head(5)
categorias = ['Volumen', 'Consistencia', 'Complejidad', 'Registro']
x = np.arange(len(categorias))
width = 0.15
colores_top5 = ['gold', 'silver', '#CD7F32', 'steelblue', 'lightcoral']

for i, (_, row) in enumerate(top5.iterrows()):
    scores = [row['score_volumen'], row['score_consistencia'],
              row['score_complejidad'], row['score_registro']]
    ax2.bar(x + i * width, scores, width,
            label=row['etiqueta'], color=colores_top5[i], alpha=0.8)

ax2.set_xticks(x + width * 2)
ax2.set_xticklabels(categorias)
ax2.set_ylabel('Score (0-100)')
ax2.set_title('Perfil de scores — Top 5\n(cada dimensión por separado)')
ax2.legend(fontsize=9)
ax2.set_ylim(0, 110)

plt.tight_layout()
ruta = os.path.join(OUTPUTS_DIR, 'ranking_alistadores.png')
plt.savefig(ruta, dpi=150, bbox_inches='tight')
plt.show()
print(f"\n✅ Gráfica guardada: {ruta}")
print(f"\n💡 NOTA: Los pesos del score son configurables.")
print(f"   Ajusta los valores en el bloque 'Score final ponderado'")
print(f"   según lo que la gerencia considera más importante.")