"""
=============================================================
FAVARCIA — PERFIL INDIVIDUAL DE ALISTADOR
=============================================================
Uso:
    python perfil_alistador.py EM047
    python perfil_alistador.py EM564

Separa métricas de volumen (todos los pedidos) de métricas
de tiempo (solo pedidos con tiempo registrado > 0).

Contexto operacional documentado:
    - 51% de pedidos tienen tiempo=0 (trabajados sin abrir)
    - Pedidos agrupados: varios pedidos trabajados juntos
    - Pedidos olvidados: cerrados al día siguiente
    - Ventanas de café: 9:00/9:15 y 15:00/15:15 (+15 min)
    - Ayuda no registrada en pedidos grandes
    - Pedidos partidos al almuerzo: segunda parte invisible
=============================================================
"""

import pandas as pd
import numpy as np
import sys
import os

# ── Rutas ancladas al directorio del script ──────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data", "raw")

# ── Recibir código del alistador ─────────────────────────
if len(sys.argv) > 1:
    PICKER = sys.argv[1].upper()
else:
    PICKER = input("Código del alistador (ej: EM047): ").strip().upper()

# ── Cargar datos ─────────────────────────────────────────
archivo = os.path.join(DATA_DIR, "FPM_Datos.xlsx")
print(f"\n📊 Cargando datos...")
df = pd.read_excel(archivo)

# Estandarizar nombres de columnas
df.columns = (df.columns
              .str.lower()
              .str.strip()
              .str.replace(' ', '_')
              .str.replace('(', '')
              .str.replace(')', ''))

# Renombrar columnas reales a nombres estándar
df = df.rename(columns={
    'alistador':             'picker_id',
    'tiempo_alisto_minutos': 'tiempo_minutos',
    'inicio_alisto':         'hora_inicio',
    'fecha_pedido':          'fecha',
})

# Limpiar filas sin alistador
df = df.dropna(subset=['picker_id'])

# ── Separar dos datasets ──────────────────────────────────
# df_vol    → todos los pedidos incluyendo tiempo=0
#             para métricas de VOLUMEN real
# df_tiempo → solo pedidos con tiempo registrado > 0
#             para métricas de TIEMPO
df_vol    = df.copy()
df_tiempo = df[df['tiempo_minutos'] > 0].copy()

# Calcular seg_por_linea
df_tiempo['seg_por_linea'] = (
    df_tiempo['tiempo_minutos'] * 60 / df_tiempo['cant_lineas']
)

# Clasificar outliers en df_tiempo
df_tiempo['es_outlier'] = (
    ((df_tiempo['tiempo_minutos'] < 1) & (df_tiempo['cant_lineas'] > 3)) |
    (df_tiempo['tiempo_minutos'] > 240) |
    ((df_tiempo['cant_lineas'] <= 2) & (df_tiempo['tiempo_minutos'] > 30))
)

# Extraer hora del día
df_tiempo['hora'] = pd.to_datetime(
    df_tiempo['hora_inicio'], errors='coerce'
).dt.hour

# ── Resumen de calidad de datos ───────────────────────────
print(f"\n🔍 Calidad de datos — operación completa:")
print(f"   Total pedidos:              {len(df_vol):,}")
print(f"   Con tiempo registrado:      {len(df_tiempo):,} ({len(df_tiempo)/len(df_vol)*100:.1f}%)")
print(f"   Sin tiempo (tiempo=0):      {(df_vol['tiempo_minutos']==0).sum():,} ({(df_vol['tiempo_minutos']==0).mean()*100:.1f}%)")
print(f"   Outliers en con-tiempo:     {df_tiempo['es_outlier'].sum():,} ({df_tiempo['es_outlier'].mean()*100:.1f}%)")

# ── Filtrar por alistador ─────────────────────────────────
picker_vol    = df_vol[df_vol['picker_id'] == PICKER]
picker_tiempo = df_tiempo[df_tiempo['picker_id'] == PICKER]
picker_limpio = picker_tiempo[~picker_tiempo['es_outlier']]

if len(picker_vol) == 0:
    print(f"\n❌ Alistador {PICKER} no encontrado.")
    print(f"   Códigos disponibles: {sorted(df_vol['picker_id'].unique())}")
    sys.exit()

# Nombre del alistador
nombre = picker_vol['nombre'].iloc[0] if 'nombre' in picker_vol.columns else PICKER

print(f"\n{'='*50}")
print(f"PERFIL: {nombre} ({PICKER})")
print(f"{'='*50}")

# ── VOLUMEN REAL ──────────────────────────────────────────
print(f"\n📦 VOLUMEN REAL (todos los pedidos)")
print(f"   Pedidos totales:           {len(picker_vol):,}")
print(f"   Con tiempo registrado:     {len(picker_tiempo):,} ({len(picker_tiempo)/len(picker_vol)*100:.1f}%)")
print(f"   Sin tiempo (sin abrir):    {(picker_vol['tiempo_minutos']==0).sum():,} ({(picker_vol['tiempo_minutos']==0).mean()*100:.1f}%)")
print(f"   Líneas totales:            {picker_vol['cant_lineas'].sum():,}")
print(f"   Unidades totales:          {picker_vol['cant_unidades'].sum():,.0f}")
print(f"   Líneas por pedido:         {picker_vol['cant_lineas'].mean():.1f} promedio  |  {picker_vol['cant_lineas'].median():.0f} mediana")
print(f"   Pedido más grande:         {picker_vol['cant_lineas'].max():.0f} líneas")

# ── AJUSTE POR DISPONIBILIDAD PARCIAL ────────────────────
# Solo aplica para alistadores con roles adicionales
# que reducen su tiempo disponible de picking
AJUSTES_DISPONIBILIDAD = {
    'EM047': {
        'descripcion': 'Documentación FPM — 3 mañanas/semana',
        'horas_doc_semana':  13.5,   # 3 mañanas × 4.5 hrs
        'horas_turno_total': 55,     # 11hrs × 5 días
    }
}

if PICKER in AJUSTES_DISPONIBILIDAD:
    aj = AJUSTES_DISPONIBILIDAD[PICKER]
    horas_picking = aj['horas_turno_total'] - aj['horas_doc_semana']
    factor        = aj['horas_turno_total'] / horas_picking
    ped_ajustados = len(picker_vol) * factor
    lin_ajustadas = picker_vol['cant_lineas'].sum() * factor

    print(f"\n⚙️  AJUSTE POR DISPONIBILIDAD PARCIAL")
    print(f"   Motivo:                   {aj['descripcion']}")
    print(f"   Horas en otra función:    {aj['horas_doc_semana']}h/semana")
    print(f"   Horas reales de picking:  {horas_picking:.1f}h/semana")
    print(f"   Factor de ajuste:         {factor:.2f}x")
    print(f"   Pedidos reales:           {len(picker_vol):,}")
    print(f"   Pedidos equiv. full-time: {ped_ajustados:,.0f}")
    print(f"   Líneas equiv. full-time:  {lin_ajustadas:,.0f}")

    # Ranking ajustado vs operación completa
    vol_otros = df_vol[df_vol['picker_id'] != PICKER].groupby('picker_id').size()
    ranking_aj = (vol_otros > ped_ajustados).sum() + 1
    total_pickers = len(vol_otros[vol_otros >= 200]) + 1
    print(f"   Ranking volumen ajustado: #{ranking_aj} de {total_pickers} alistadores")
    print(f"   (vs ranking actual sin ajuste basado en volumen real)")

# ── TIEMPO POR LÍNEA ──────────────────────────────────────
if len(picker_tiempo) == 0:
    print(f"\n⚠️  Sin pedidos con tiempo registrado para análisis de tiempo.")
else:
    print(f"\n⏱️  TIEMPO POR LÍNEA (solo pedidos con tiempo registrado)")
    print(f"   Pedidos con tiempo:  {len(picker_tiempo):,} de {len(picker_vol):,} totales")
    print(f"   Mediana:   {picker_tiempo.seg_por_linea.median():.1f}s  (meta: 60s)")
    print(f"   Promedio:  {picker_tiempo.seg_por_linea.mean():.1f}s")
    print(f"   P25:       {picker_tiempo.seg_por_linea.quantile(0.25):.1f}s")
    print(f"   P75:       {picker_tiempo.seg_por_linea.quantile(0.75):.1f}s")
    print(f"   P90:       {picker_tiempo.seg_por_linea.quantile(0.90):.1f}s")
    print(f"   Máximo:    {picker_tiempo.seg_por_linea.max():.1f}s")

    # ── FRICCIÓN ──────────────────────────────────────────
    print(f"\n⚠️  FRICCIÓN (pedidos con tiempo registrado)")
    umbral = 120
    friccion = (picker_tiempo.seg_por_linea > umbral).mean() * 100
    friccion_op = (df_tiempo.seg_por_linea > umbral).mean() * 100
    diff = friccion - friccion_op
    simbolo = "▲" if diff > 0 else "▼"
    print(f"   Pedidos con alta fricción (>{umbral}s): {friccion:.1f}%")
    print(f"   Promedio operación:                    {friccion_op:.1f}%")
    print(f"   Diferencia vs operación:               {simbolo} {abs(diff):.1f} puntos")

    # ── FRICCIÓN POR HORA ─────────────────────────────────
    print(f"\n⏰  FRICCIÓN POR HORA DEL DÍA")
    por_hora = (picker_tiempo.groupby('hora')['seg_por_linea']
                .agg(['median', 'count'])
                .round(1))
    por_hora.columns = ['mediana_seg', 'pedidos']
    print(por_hora.to_string())

    # ── CAPACIDAD vs OPERACIÓN ────────────────────────────
    print(f"\n📐 CAPACIDAD vs OPERACIÓN")
    mediana_op     = df_tiempo.seg_por_linea.median()
    mediana_picker = picker_tiempo.seg_por_linea.median()
    ranking = (df_tiempo.groupby('picker_id')['seg_por_linea']
               .median()
               .rank(ascending=True))
    pos = ranking.get(PICKER, None)
    total_pickers = len(ranking)
    print(f"   Mediana operación:  {mediana_op:.1f}s")
    print(f"   Mediana {PICKER}:     {mediana_picker:.1f}s")
    if pos:
        print(f"   Ranking velocidad:  #{int(pos)} de {total_pickers} alistadores")
        print(f"   (donde #1 = más rápido, basado en pedidos con tiempo registrado)")

    # ── PERFIL LIMPIO ─────────────────────────────────────
    print(f"\n🔍 PERFIL LIMPIO (sin outliers)")
    print(f"   Pedidos outlier removidos: {picker_tiempo['es_outlier'].sum():,} ({picker_tiempo['es_outlier'].mean()*100:.1f}%)")
    print(f"   Pedidos limpios:           {len(picker_limpio):,}")
    if len(picker_limpio) > 0:
        print(f"   Mediana limpia:            {picker_limpio.seg_por_linea.median():.1f}s")
        print(f"   Promedio limpio:           {picker_limpio.seg_por_linea.mean():.1f}s")
        print(f"   P75 limpio:                {picker_limpio.seg_por_linea.quantile(0.75):.1f}s")
        print(f"   P90 limpio:                {picker_limpio.seg_por_linea.quantile(0.90):.1f}s")
        print(f"   Fricción limpia:           {(picker_limpio.seg_por_linea > umbral).mean()*100:.1f}%")

        ranking_limpio = (df_tiempo[~df_tiempo['es_outlier']]
                          .groupby('picker_id')['seg_por_linea']
                          .median()
                          .rank(ascending=True))
        pos_limpio = ranking_limpio.get(PICKER, None)
        if pos_limpio:
            print(f"   Ranking limpio:            #{int(pos_limpio)} de {len(ranking_limpio)} alistadores")

    # ── TOP 10 FRICCIÓN ───────────────────────────────────
    print(f"\n📋 PEDIDOS CON MAYOR FRICCIÓN (top 10)")
    top_friccion = (picker_tiempo[picker_tiempo.seg_por_linea > umbral]
                    .sort_values('seg_por_linea', ascending=False)
                    [['fecha', 'cant_lineas', 'tiempo_minutos', 'seg_por_linea']]
                    .head(10))
    if len(top_friccion) > 0:
        print(top_friccion.to_string(index=False))
    else:
        print("   Ninguno — sin pedidos con alta fricción ✅")

# ── NOTA SOBRE LIMITACIONES ───────────────────────────────
print(f"\n{'='*50}")
print(f"⚠️  LIMITACIONES DEL SISTEMA DE MEDICIÓN")
print(f"{'='*50}")
print(f"   Los siguientes factores afectan la calidad de los datos:")
print(f"   1. {(df_vol['tiempo_minutos']==0).mean()*100:.1f}% de pedidos con tiempo=0 (trabajados sin abrir)")
print(f"   2. Pedidos agrupados: tiempo registrado no refleja trabajo individual")
print(f"   3. Pedidos olvidados: cerrados al día siguiente")
print(f"   4. Ventanas de café: 9:00/9:15 y 15:00/15:15 inflan hasta 15 min")
print(f"   5. Ayuda no registrada en pedidos grandes")
print(f"   6. Pedidos partidos al almuerzo: segunda parte invisible al sistema")
print(f"   Las métricas de tiempo deben interpretarse con estas limitaciones en mente.")