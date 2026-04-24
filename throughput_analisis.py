"""
=============================================================
FAVARCIA — ANÁLISIS DE THROUGHPUT
=============================================================
Mide cuántos pedidos se cierran por hora a lo largo del día.
Usa TODOS los pedidos incluyendo tiempo=0 — es el análisis
más limpio porque no depende del comportamiento de apertura.

Fecha de cierre = FECHA FACTURA (cuando el pedido salió)
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
              .str.lower()
              .str.strip()
              .str.replace(' ', '_')
              .str.replace('(', '')
              .str.replace(')', ''))

df = df.rename(columns={
    'alistador':             'picker_id',
    'tiempo_alisto_minutos': 'tiempo_minutos',
    'fecha_factura':         'fecha_cierre',
    'fecha_pedido':          'fecha_creacion',
})

# Limpiar filas sin alistador
df = df.dropna(subset=['picker_id'])

print(f"✅ {len(df):,} pedidos cargados")

# ── Extraer hora de cierre ────────────────────────────────
# Usamos fecha_cierre (fecha factura) porque es cuando
# el pedido realmente salió — no depende de cuándo se abrió
df['hora_cierre'] = pd.to_datetime(
    df['fecha_cierre'], errors='coerce'
).dt.hour

df['fecha'] = pd.to_datetime(
    df['fecha_cierre'], errors='coerce'
).dt.date

df['dia_semana'] = pd.to_datetime(
    df['fecha_cierre'], errors='coerce'
).dt.day_name()

# Filtrar solo horario operacional (5am a 21pm)
df_op = df[df['hora_cierre'].between(5, 21)].copy()

print(f"   En horario operacional (5-21h): {len(df_op):,}")

# ── ANÁLISIS 1: Throughput por hora del día ───────────────
print(f"\n📊 Throughput por hora del día:")
throughput_hora = (df_op.groupby('hora_cierre')
                   .size()
                   .reset_index(name='pedidos'))

throughput_hora['pct'] = (throughput_hora['pedidos'] /
                          throughput_hora['pedidos'].sum() * 100)

print(throughput_hora.to_string(index=False))

hora_pico = throughput_hora.loc[throughput_hora['pedidos'].idxmax(), 'hora_cierre']
print(f"\n   Hora pico: {hora_pico}:00h con {throughput_hora['pedidos'].max():,} pedidos")

# ── ANÁLISIS 2: Throughput por hora y día de semana ───────
print(f"\n📊 Throughput promedio por hora y día de semana:")
orden_dias = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
throughput_dia = (df_op.groupby(['dia_semana', 'hora_cierre'])
                  .size()
                  .reset_index(name='pedidos'))

pivot = throughput_dia.pivot(
    index='hora_cierre',
    columns='dia_semana',
    values='pedidos'
).fillna(0)

# Reordenar columnas por día de semana
cols_presentes = [d for d in orden_dias if d in pivot.columns]
pivot = pivot[cols_presentes]
print(pivot.to_string())

# ── ANÁLISIS 3: Cycle time pedido → factura ───────────────
print(f"\n📊 Cycle time (creación → factura):")
df['cycle_time_min'] = (
    pd.to_datetime(df['fecha_cierre'], errors='coerce') -
    pd.to_datetime(df['fecha_creacion'], errors='coerce')
).dt.total_seconds() / 60

# Filtrar cycle times válidos (0 a 24 horas)
ct = df[(df['cycle_time_min'] > 0) & (df['cycle_time_min'] <= 1440)].copy()

print(f"   Pedidos con cycle time válido: {len(ct):,}")
print(f"   Mediana:  {ct['cycle_time_min'].median():.0f} min ({ct['cycle_time_min'].median()/60:.1f} horas)")
print(f"   Promedio: {ct['cycle_time_min'].mean():.0f} min ({ct['cycle_time_min'].mean()/60:.1f} horas)")
print(f"   P25:      {ct['cycle_time_min'].quantile(0.25):.0f} min")
print(f"   P75:      {ct['cycle_time_min'].quantile(0.75):.0f} min")
print(f"   P90:      {ct['cycle_time_min'].quantile(0.90):.0f} min")

# ── GRÁFICAS ──────────────────────────────────────────────
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle('FAVARCIA — Análisis de Throughput y Cycle Time',
             fontsize=14, fontweight='bold')

# Gráfica 1: Throughput por hora
ax1 = axes[0, 0]
colores = ['tomato' if h == hora_pico else 'steelblue'
           for h in throughput_hora['hora_cierre']]
ax1.bar(throughput_hora['hora_cierre'],
        throughput_hora['pedidos'],
        color=colores, alpha=0.8)
ax1.set_xlabel('Hora del día')
ax1.set_ylabel('Pedidos cerrados')
ax1.set_title('Throughput por hora\n(rojo = hora pico)')
ax1.set_xticks(range(5, 22))

# Gráfica 2: Throughput por día de semana
ax2 = axes[0, 1]
throughput_diasem = (df_op.groupby('dia_semana')
                     .size()
                     .reindex(orden_dias)
                     .dropna())
ax2.bar(range(len(throughput_diasem)),
        throughput_diasem.values,
        color='steelblue', alpha=0.8)
ax2.set_xticks(range(len(throughput_diasem)))
ax2.set_xticklabels([d[:3] for d in throughput_diasem.index], rotation=45)
ax2.set_ylabel('Pedidos cerrados')
ax2.set_title('Throughput por día de semana')

# Gráfica 3: Cycle time distribución
ax3 = axes[1, 0]
ax3.hist(ct['cycle_time_min'] / 60, bins=50,
         color='steelblue', alpha=0.7, edgecolor='white')
ax3.axvline(x=ct['cycle_time_min'].median() / 60,
            color='black', linewidth=1.5,
            label=f"Mediana: {ct['cycle_time_min'].median()/60:.1f}h")
ax3.axvline(x=ct['cycle_time_min'].quantile(0.90) / 60,
            color='red', linewidth=1.5, linestyle='--',
            label=f"P90: {ct['cycle_time_min'].quantile(0.90)/60:.1f}h")
ax3.set_xlabel('Horas')
ax3.set_ylabel('Cantidad de pedidos')
ax3.set_title('Distribución de Cycle Time\n(creación → factura)')
ax3.legend()

# Gráfica 4: Cycle time por hora de creación
ax4 = axes[1, 1]
df['hora_creacion'] = pd.to_datetime(
    df['fecha_creacion'], errors='coerce'
).dt.hour
ct_hora = (ct.groupby(
    pd.to_datetime(ct['fecha_creacion'], errors='coerce').dt.hour
)['cycle_time_min'].median() / 60)
ax4.bar(ct_hora.index, ct_hora.values,
        color='steelblue', alpha=0.8)
ax4.set_xlabel('Hora de creación del pedido')
ax4.set_ylabel('Cycle time mediano (horas)')
ax4.set_title('Cycle time según hora de creación\n(pedidos creados tarde toman más tiempo)')

plt.tight_layout()
ruta = os.path.join(OUTPUTS_DIR, 'throughput_analisis.png')
plt.savefig(ruta, dpi=150, bbox_inches='tight')
plt.show()
print(f"\n✅ Gráfica guardada: {ruta}")

# ── ANÁLISIS 4: Tiempo en cola ────────────────────────────
print(f"\n📊 Tiempo en cola (fecha_pedido → inicio_alisto):")

df['fecha_pedido_dt']  = pd.to_datetime(df['fecha_creacion'], errors='coerce')
df['inicio_alisto_dt'] = pd.to_datetime(df['inicio_alisto'],  errors='coerce')

# Solo pedidos donde la hora de creación no es medianoche
df['hora_creacion'] = df['fecha_pedido_dt'].dt.hour
df_cola = df[
    (df['hora_creacion'] > 0) &
    df['inicio_alisto_dt'].notna() &
    df['fecha_pedido_dt'].notna()
].copy()

df_cola['tiempo_cola_min'] = (
    df_cola['inicio_alisto_dt'] - df_cola['fecha_pedido_dt']
).dt.total_seconds() / 60

# Filtrar tiempos válidos (0 a 8 horas)
df_cola = df_cola[
    (df_cola['tiempo_cola_min'] >= 0) &
    (df_cola['tiempo_cola_min'] <= 480)
]

print(f"   Pedidos con tiempo en cola válido: {len(df_cola):,}")
print(f"   Mediana:  {df_cola['tiempo_cola_min'].median():.0f} min")
print(f"   Promedio: {df_cola['tiempo_cola_min'].mean():.0f} min")
print(f"   P25:      {df_cola['tiempo_cola_min'].quantile(0.25):.0f} min")
print(f"   P75:      {df_cola['tiempo_cola_min'].quantile(0.75):.0f} min")
print(f"   P90:      {df_cola['tiempo_cola_min'].quantile(0.90):.0f} min")
print(f"   % esperó más de 30 min: {(df_cola['tiempo_cola_min'] > 30).mean()*100:.1f}%")
print(f"   % esperó más de 60 min: {(df_cola['tiempo_cola_min'] > 60).mean()*100:.1f}%")
print(f"   % esperó más de 2 horas: {(df_cola['tiempo_cola_min'] > 120).mean()*100:.1f}%")

# Gráfica de tiempo en cola
fig2, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))
fig2.suptitle('FAVARCIA — Tiempo en Cola', fontsize=13, fontweight='bold')

ax1.hist(df_cola['tiempo_cola_min'], bins=50,
         color='steelblue', alpha=0.7, edgecolor='white')
ax1.axvline(x=df_cola['tiempo_cola_min'].median(),
            color='black', linewidth=1.5,
            label=f"Mediana: {df_cola['tiempo_cola_min'].median():.0f} min")
ax1.axvline(x=60, color='red', linewidth=1.5, linestyle='--',
            label='60 min')
ax1.set_xlabel('Minutos en cola')
ax1.set_ylabel('Cantidad de pedidos')
ax1.set_title('Distribución tiempo en cola')
ax1.legend()

cola_hora = df_cola.groupby('hora_creacion')['tiempo_cola_min'].median()
ax2.bar(cola_hora.index, cola_hora.values,
        color='steelblue', alpha=0.8)
ax2.set_xlabel('Hora de creación del pedido')
ax2.set_ylabel('Tiempo mediano en cola (min)')
ax2.set_title('Tiempo en cola según hora de creación')

plt.tight_layout()
ruta2 = os.path.join(OUTPUTS_DIR, 'tiempo_cola.png')
plt.savefig(ruta2, dpi=150, bbox_inches='tight')
plt.show()
print(f"✅ Gráfica guardada: {ruta2}")