"""
=============================================================
FAVARCIA — ANÁLISIS DE THROUGHPUT Y TIEMPO EN COLA
=============================================================
Mide cuántos pedidos se cierran por hora a lo largo del día.
Usa TODOS los pedidos incluyendo tiempo=0.

DEFINICIONES:
- Cycle time cliente: FECHA FACTURA - FECHA PEDIDO
  Tiempo total desde que el cliente hizo el pedido hasta que
  se facturó. FECHA PEDIDO con 00:00 puede inflar este número
  para pedidos creados de noche.

- Tiempo en cola: INICIO ALISTO - FECHA FACTURA
  Tiempo que esperó el pedido en la bandeja desde que fue
  procesado por contabilidad hasta que un alistador lo tomó.
  Refleja priorización de rutas — no necesariamente ineficiencia.
  Rutas 1 y 2 (prioridad) se alistan primero desde las 6am.
  Rutas 3-6 esperan hasta completar las prioritarias.
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
    'fecha_factura':         'fecha_factura',
    'fecha_pedido':          'fecha_pedido',
    'inicio_alisto':         'inicio_alisto',
    'fin_alisto':            'fin_alisto',
})

df = df.dropna(subset=['picker_id'])
print(f"✅ {len(df):,} pedidos cargados")

# ── Extraer hora de cierre (FECHA FACTURA) ────────────────
df['hora_cierre'] = pd.to_datetime(
    df['fecha_factura'], errors='coerce'
).dt.hour

df['fecha'] = pd.to_datetime(
    df['fecha_factura'], errors='coerce'
).dt.date

df['dia_semana'] = pd.to_datetime(
    df['fecha_factura'], errors='coerce'
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
print(f"\n📊 Throughput por hora y día de semana:")
orden_dias = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
throughput_dia = (df_op.groupby(['dia_semana', 'hora_cierre'])
                  .size()
                  .reset_index(name='pedidos'))
pivot = throughput_dia.pivot(
    index='hora_cierre',
    columns='dia_semana',
    values='pedidos'
).fillna(0)
cols_presentes = [d for d in orden_dias if d in pivot.columns]
pivot = pivot[cols_presentes]
print(pivot.to_string())

# ── ANÁLISIS 3: Cycle time pedido → factura ───────────────
print(f"\n📊 Cycle time cliente (fecha_pedido a fecha_factura):")
print(f"   NOTA: FECHA PEDIDO con 00:00 infla el cycle time")
print(f"   de pedidos cuya orden llegó de noche.")
df['cycle_time_min'] = (
    pd.to_datetime(df['fecha_factura'], errors='coerce') -
    pd.to_datetime(df['fecha_pedido'], errors='coerce')
).dt.total_seconds() / 60

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
ax1.set_xlabel('Hora del dia')
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
ax2.set_title('Throughput por dia de semana')

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
ax3.set_title('Cycle Time cliente\n(fecha_pedido a fecha_factura)')
ax3.legend()

# Gráfica 4: Cycle time por hora de creación del pedido
ax4 = axes[1, 1]
df['hora_pedido'] = pd.to_datetime(
    df['fecha_pedido'], errors='coerce'
).dt.hour
ct_hora = (ct.groupby(
    pd.to_datetime(ct['fecha_pedido'], errors='coerce').dt.hour
)['cycle_time_min'].median() / 60)
ax4.bar(ct_hora.index, ct_hora.values,
        color='steelblue', alpha=0.8)
ax4.set_xlabel('Hora de creacion del pedido por el cliente')
ax4.set_ylabel('Cycle time mediano (horas)')
ax4.set_title('Cycle time segun hora de pedido\n(hora 0 = pedidos de noche)')

plt.tight_layout()
ruta = os.path.join(OUTPUTS_DIR, 'throughput_analisis.png')
plt.savefig(ruta, dpi=150, bbox_inches='tight')
plt.show()
print(f"\n✅ Grafica guardada: {ruta}")

# ── ANÁLISIS 4: Tiempo en cola ────────────────────────────
# Tiempo en cola = INICIO ALISTO - FECHA FACTURA
# Mide cuánto esperó el pedido en la bandeja desde que
# contabilidad lo procesó hasta que un alistador lo tomó.
print(f"\n📊 Tiempo en cola (fecha_factura a inicio_alisto):")

df['fecha_factura_dt'] = pd.to_datetime(df['fecha_factura'], errors='coerce')
df['inicio_alisto_dt'] = pd.to_datetime(df['inicio_alisto'], errors='coerce')

# Filtrar pedidos con ambas fechas válidas
df_cola = df[
    df['inicio_alisto_dt'].notna() &
    df['fecha_factura_dt'].notna()
].copy()

df_cola['tiempo_cola_min'] = (
    df_cola['inicio_alisto_dt'] - df_cola['fecha_factura_dt']
).dt.total_seconds() / 60

# Filtrar tiempos válidos (0 a 16 horas — jornada máxima)
df_cola = df_cola[
    (df_cola['tiempo_cola_min'] >= 0) &
    (df_cola['tiempo_cola_min'] <= 960)
]

print(f"   Pedidos con tiempo en cola valido: {len(df_cola):,}")
print(f"   Mediana:  {df_cola['tiempo_cola_min'].median():.0f} min")
print(f"   Promedio: {df_cola['tiempo_cola_min'].mean():.0f} min")
print(f"   P25:      {df_cola['tiempo_cola_min'].quantile(0.25):.0f} min")
print(f"   P75:      {df_cola['tiempo_cola_min'].quantile(0.75):.0f} min")
print(f"   P90:      {df_cola['tiempo_cola_min'].quantile(0.90):.0f} min")
print(f"   % espero mas de 30 min:  {(df_cola['tiempo_cola_min'] > 30).mean()*100:.1f}%")
print(f"   % espero mas de 60 min:  {(df_cola['tiempo_cola_min'] > 60).mean()*100:.1f}%")
print(f"   % espero mas de 2 horas: {(df_cola['tiempo_cola_min'] > 120).mean()*100:.1f}%")
print(f"\n   NOTA: Tiempo en cola refleja priorización de rutas,")
print(f"   no ineficiencia. Rutas secundarias esperan hasta")
print(f"   completar rutas prioritarias 1 y 2.")
print(f"   Análisis más preciso requiere columna RUTA por pedido.")

# Gráfica de tiempo en cola
fig2, (axc1, axc2) = plt.subplots(1, 2, figsize=(12, 4))
fig2.suptitle('FAVARCIA — Tiempo en Cola\n(INICIO ALISTO - FECHA FACTURA)',
              fontsize=13, fontweight='bold')

axc1.hist(df_cola['tiempo_cola_min'], bins=50,
          color='steelblue', alpha=0.7, edgecolor='white')
axc1.axvline(x=df_cola['tiempo_cola_min'].median(),
             color='black', linewidth=1.5,
             label=f"Mediana: {df_cola['tiempo_cola_min'].median():.0f} min")
axc1.axvline(x=60, color='red', linewidth=1.5, linestyle='--',
             label='60 min')
axc1.set_xlabel('Minutos en cola')
axc1.set_ylabel('Cantidad de pedidos')
axc1.set_title('Distribucion tiempo en cola')
axc1.legend()

# Tiempo en cola por hora de inicio del alisto
df_cola['hora_inicio'] = df_cola['inicio_alisto_dt'].dt.hour
cola_hora = df_cola.groupby('hora_inicio')['tiempo_cola_min'].median()
axc2.bar(cola_hora.index, cola_hora.values,
         color='steelblue', alpha=0.8)
axc2.set_xlabel('Hora de inicio del alisto')
axc2.set_ylabel('Tiempo mediano en cola (min)')
axc2.set_title('Tiempo en cola segun hora de inicio\n(pedidos tomados tarde esperaron mas)')

plt.tight_layout()
ruta2 = os.path.join(OUTPUTS_DIR, 'tiempo_cola.png')
plt.savefig(ruta2, dpi=150, bbox_inches='tight')
plt.show()
print(f"✅ Grafica guardada: {ruta2}")