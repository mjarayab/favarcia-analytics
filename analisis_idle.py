"""
=============================================================
FAVARCIA — ANÁLISIS DE TIEMPO IDLE ENTRE PEDIDOS
=============================================================
Mide el tiempo que pasa entre que un alistador termina
un pedido y empieza el siguiente.

Tiempo idle = INICIO ALISTO(N) - FIN ALISTO(N-1)

Este análisis es un proxy para detectar comportamientos
que los datos no capturan directamente:
- Tiempo perdido entre pedidos
- Patrones de baja productividad en horas específicas
- Diferencias de comportamiento entre alistadores

IMPORTANTE: El tiempo idle tiene causas legítimas:
- Ir a buscar el siguiente pedido a la bandeja
- Ayudar a otro alistador (trabajo no registrado)
- Pausas de café (9:00/9:15 y 15:00/15:15)
- Almuerzo
- Pedidos grandes que requieren planificación

El análisis identifica PATRONES, no causas específicas.
La interpretación requiere conocimiento operacional.
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

# ── Roles de apoyo — excluir del análisis ─────────────────
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
    'inicio_alisto':         'inicio_alisto',
    'fin_alisto':            'fin_alisto',
})
df = df.dropna(subset=['picker_id'])
df = df[~df['picker_id'].isin(ROLES_APOYO)]

# Convertir fechas
df['inicio_dt'] = pd.to_datetime(df['inicio_alisto'], errors='coerce')
df['fin_dt']    = pd.to_datetime(df['fin_alisto'],    errors='coerce')

# Solo pedidos con ambas fechas válidas y tiempo > 0
df_valido = df[
    df['inicio_dt'].notna() &
    df['fin_dt'].notna() &
    (df['tiempo_minutos'] > 0)
].copy()

print(f"✅ {len(df_valido):,} pedidos con tiempos válidos")

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

# ── Calcular tiempo idle por alistador ────────────────────
print(f"\n📊 Calculando tiempo idle entre pedidos...")

idle_records = []

for picker in df_valido['picker_id'].unique():
    picker_df = (df_valido[df_valido['picker_id'] == picker]
                 .sort_values('inicio_dt')
                 .reset_index(drop=True))

    if len(picker_df) < 2:
        continue

    for i in range(1, len(picker_df)):
        fin_anterior   = picker_df.loc[i-1, 'fin_dt']
        inicio_actual  = picker_df.loc[i,   'inicio_dt']

        # Solo si es el mismo día
        if fin_anterior.date() != inicio_actual.date():
            continue

        idle_min = (inicio_actual - fin_anterior).total_seconds() / 60

        # Filtrar idle válidos (0 a 60 minutos)
        # Más de 60 min = almuerzo, fin de turno, o día diferente
        if 0 <= idle_min <= 60:
            idle_records.append({
                'picker_id':   picker,
                'etiqueta':    mapeo_nombres.get(picker, picker),
                'fecha':       fin_anterior.date(),
                'hora':        fin_anterior.hour,
                'idle_min':    idle_min,
                'hora_fin':    fin_anterior.hour,
            })

df_idle = pd.DataFrame(idle_records)
print(f"   Registros de idle válidos: {len(df_idle):,}")

# ── Análisis por alistador ────────────────────────────────
print(f"\n{'='*60}")
print(f"TIEMPO IDLE POR ALISTADOR")
print(f"{'='*60}")

idle_picker = (df_idle.groupby(['picker_id', 'etiqueta'])
               .agg(
                   idle_mediana  = ('idle_min', 'median'),
                   idle_promedio = ('idle_min', 'mean'),
                   idle_p75      = ('idle_min', lambda x: x.quantile(0.75)),
                   idle_p90      = ('idle_min', lambda x: x.quantile(0.90)),
                   n_gaps        = ('idle_min', 'count'),
                   pct_mayor15   = ('idle_min', lambda x: (x > 15).mean() * 100),
               )
               .reset_index()
               .sort_values('idle_mediana', ascending=False))

print(f"\n{'Nombre':25} {'Med':>5} {'P75':>5} {'P90':>5} {'%>15m':>6} {'Gaps':>6}")
print("-" * 60)
for _, row in idle_picker.head(20).iterrows():
    print(f"{row['etiqueta']:25} "
          f"{row['idle_mediana']:>5.1f} "
          f"{row['idle_p75']:>5.1f} "
          f"{row['idle_p90']:>5.1f} "
          f"{row['pct_mayor15']:>5.1f}% "
          f"{row['n_gaps']:>6,}")

# ── Análisis por hora del día ─────────────────────────────
print(f"\n{'='*60}")
print(f"TIEMPO IDLE POR HORA DEL DÍA")
print(f"{'='*60}")

idle_hora = (df_idle.groupby('hora')
             .agg(idle_mediana = ('idle_min', 'median'),
                  n_gaps       = ('idle_min', 'count'))
             .reset_index())

print(f"\n{'Hora':>6} {'Mediana idle':>13} {'Gaps':>6}")
print("-" * 30)
for _, row in idle_hora.iterrows():
    bar = '█' * int(row['idle_mediana'])
    print(f"{row['hora']:>6}h  {row['idle_mediana']:>5.1f} min  "
          f"{row['n_gaps']:>6,}  {bar}")

# ── Patrones sospechosos ──────────────────────────────────
print(f"\n{'='*60}")
print(f"PATRONES DE IDLE ALTO (>15 min)")
print(f"{'='*60}")

mediana_global_idle = df_idle['idle_min'].median()
print(f"\nMediana global de idle: {mediana_global_idle:.1f} min")

print(f"\nAlistadores con idle alto consistente (P75 > 15 min):")
alerta = idle_picker[idle_picker['idle_p75'] > 15].sort_values('idle_p75', ascending=False)
for _, row in alerta.iterrows():
    print(f"   {row['etiqueta']:25} P75={row['idle_p75']:.1f}min  "
          f"P90={row['idle_p90']:.1f}min  {row['pct_mayor15']:.1f}% de gaps >15min")

# Idle por hora tarde del día (posible "esconderse")
print(f"\nIdle por hora — últimas horas del turno:")
horas_tarde = idle_hora[idle_hora['hora'] >= 15].sort_values('idle_mediana', ascending=False)
for _, row in horas_tarde.iterrows():
    print(f"   {row['hora']}:00h → mediana idle: {row['idle_mediana']:.1f} min")

# ── GRÁFICAS ──────────────────────────────────────────────
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle('FAVARCIA — Análisis de Tiempo Idle Entre Pedidos\n'
             'Tiempo entre FIN de un pedido e INICIO del siguiente',
             fontsize=13, fontweight='bold')

# Gráfica 1: Mediana idle por alistador
ax1 = axes[0, 0]
top_idle = idle_picker.head(15).sort_values('idle_mediana')
colores1 = ['tomato' if v > 10 else 'steelblue'
            for v in top_idle['idle_mediana']]
ax1.barh(top_idle['etiqueta'], top_idle['idle_mediana'],
         color=colores1, alpha=0.8)
ax1.axvline(x=mediana_global_idle, color='green', linestyle='--',
            linewidth=1.5, label=f'Global: {mediana_global_idle:.1f} min')
ax1.set_xlabel('Mediana de tiempo idle (min)')
ax1.set_title('Tiempo idle mediano por alistador\n(rojo = por encima de 10 min)')
ax1.legend(fontsize=8)

# Gráfica 2: % gaps > 15 min por alistador
ax2 = axes[0, 1]
top_pct = idle_picker.sort_values('pct_mayor15', ascending=False).head(15)
top_pct = top_pct.sort_values('pct_mayor15')
colores2 = ['tomato' if v > 30 else 'steelblue'
            for v in top_pct['pct_mayor15']]
ax2.barh(top_pct['etiqueta'], top_pct['pct_mayor15'],
         color=colores2, alpha=0.8)
ax2.axvline(x=idle_picker['pct_mayor15'].mean(), color='red',
            linestyle='--', linewidth=1,
            label=f"Promedio: {idle_picker['pct_mayor15'].mean():.1f}%")
ax2.set_xlabel('% de gaps > 15 minutos')
ax2.set_title('% de tiempo idle mayor a 15 min\n(rojo = más del 30%)')
ax2.legend(fontsize=8)

# Gráfica 3: Idle por hora del día
ax3 = axes[1, 0]
hora_pico_idle = idle_hora.loc[idle_hora['idle_mediana'].idxmax(), 'hora']
colores3 = ['tomato' if h == hora_pico_idle else 'steelblue'
            for h in idle_hora['hora']]
ax3.bar(idle_hora['hora'], idle_hora['idle_mediana'],
        color=colores3, alpha=0.8)
ax3.axhline(y=mediana_global_idle, color='green', linestyle='--',
            linewidth=1.5, label=f'Global: {mediana_global_idle:.1f} min')
ax3.set_xlabel('Hora del día')
ax3.set_ylabel('Mediana idle (min)')
ax3.set_title('Tiempo idle por hora del día\n(rojo = hora con más idle)')
ax3.legend(fontsize=8)

# Gráfica 4: Distribución de tiempos idle
ax4 = axes[1, 1]
ax4.hist(df_idle['idle_min'], bins=60, color='steelblue',
         alpha=0.7, edgecolor='white')
ax4.axvline(x=mediana_global_idle, color='black', linewidth=1.5,
            label=f'Mediana: {mediana_global_idle:.1f} min')
ax4.axvline(x=15, color='red', linewidth=1.5, linestyle='--',
            label='15 min (umbral)')
ax4.set_xlabel('Minutos de idle')
ax4.set_ylabel('Frecuencia')
ax4.set_title('Distribución de tiempos idle\n(0 a 60 minutos)')
ax4.legend(fontsize=8)

plt.tight_layout()
ruta = os.path.join(OUTPUTS_DIR, 'analisis_idle.png')
plt.savefig(ruta, dpi=150, bbox_inches='tight')
plt.show()
print(f"\n✅ Gráfica guardada: {ruta}")

print(f"\n{'='*60}")
print(f"INTERPRETACIÓN")
print(f"{'='*60}")
print(f"""
El tiempo idle entre pedidos tiene causas legítimas e ilegítimas:

CAUSAS LEGÍTIMAS:
  - Ir a buscar el siguiente pedido a la bandeja (2-5 min normal)
  - Pausas de café: 9:00/9:15h y 15:00/15:15h (15 min)
  - Ayudar a otro alistador (trabajo no registrado bajo su nombre)
  - Pedidos grandes que requieren planificación previa

CAUSAS A INVESTIGAR (idle > 15 min fuera de horas de pausa):
  - Tiempo perdido entre pedidos
  - Conversaciones prolongadas
  - Dificultad para encontrar productos en bodega
  - Baja productividad al final del turno

PRÓXIMO PASO:
  Cruzar los patrones de idle alto con las horas de pausa
  para separar causas legítimas de patrones sospechosos.
  Requiere observación directa para confirmar causas.
""")