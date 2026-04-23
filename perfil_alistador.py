import pandas as pd
import sys
import os

# ─────────────────────────────────────────────
# PERFIL INDIVIDUAL DE ALISTADOR
# Uso: python perfil_alistador.py EM047
#      python perfil_alistador.py EM452
# ─────────────────────────────────────────────

# Recibe el código como argumento o pregunta si no se especifica
if len(sys.argv) > 1:
    PICKER = sys.argv[1].upper()
else:
    PICKER = input("Código del alistador (ej: EM047): ").strip().upper()

# Cargar datos
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
archivo = os.path.join(BASE_DIR, 'data', 'raw', 'FPM_Datos.xlsx')

print(f"\n📊 Cargando datos...")
df = pd.read_excel(archivo)
df.columns = (df.columns.str.lower().str.strip()
              .str.replace(' ', '_')
              .str.replace('(', '').str.replace(')', ''))
df = df.rename(columns={
    'alistador': 'picker_id',
    'tiempo_alisto_minutos': 'tiempo_minutos',
    'inicio_alisto': 'hora_inicio',
    'fecha_pedido': 'fecha'
})
df = df.dropna(subset=['picker_id', 'tiempo_minutos'])
df = df[df['tiempo_minutos'] > 0]
df['seg_por_linea'] = df['tiempo_minutos'] * 60 / df['cant_lineas']

# Clasificar outliers — pedidos con tiempo imposible
# Tres categorías de ruido identificadas en operación real:
# 1. Pedidos cerrados sin trabajar (tiempo < 1 min con más de 3 líneas)
# 2. Pedidos olvidados sin cerrar (más de 240 minutos)
# 3. Pedidos agrupados — 1-2 líneas con más de 30 minutos
df['es_outlier'] = (
    ((df['tiempo_minutos'] < 1) & (df['cant_lineas'] > 3)) |
    (df['tiempo_minutos'] > 240) |
    ((df['cant_lineas'] <= 2) & (df['tiempo_minutos'] > 30))
)

print(f"\n🔍 Calidad de datos — operación completa:")
print(f"   Total pedidos:        {len(df):,}")
print(f"   Pedidos outlier:      {df['es_outlier'].sum():,} ({df['es_outlier'].mean()*100:.1f}%)")
print(f"   Pedidos limpios:      {(~df['es_outlier']).sum():,}")

df['hora'] = pd.to_datetime(df['hora_inicio'], errors='coerce').dt.hour

# Filtrar alistador
picker = df[df['picker_id'] == PICKER]

picker_limpio = picker[~picker['es_outlier']]

if len(picker) == 0:
    print(f"\n❌ Alistador {PICKER} no encontrado.")
    print(f"   Códigos disponibles: {sorted(df['picker_id'].unique())}")
    sys.exit()

# Nombre del alistador
nombre = picker['nombre'].iloc[0] if 'nombre' in picker.columns else PICKER

print(f"\n{'='*50}")
print(f"PERFIL: {nombre} ({PICKER})")
print(f"{'='*50}")

# ── Métricas generales ──
total = len(picker)
operacion_completa = df.copy()

print(f"\n📦 VOLUMEN")
print(f"   Pedidos totales:     {total:,}")
print(f"   Líneas totales:      {picker['cant_lineas'].sum():,}")
print(f"   Unidades totales:    {picker['cant_unidades'].sum():,.0f}")
print(f"   Líneas por pedido:   {picker['cant_lineas'].mean():.1f} promedio  |  {picker['cant_lineas'].median():.0f} mediana")
print(f"   Pedido más grande:   {picker['cant_lineas'].max():.0f} líneas")

print(f"\n⏱️  TIEMPO POR LÍNEA")
print(f"   Mediana:   {picker.seg_por_linea.median():.1f}s  (meta: 60s)")
print(f"   Promedio:  {picker.seg_por_linea.mean():.1f}s")
print(f"   P25:       {picker.seg_por_linea.quantile(0.25):.1f}s  (75% de pedidos son más lentos que esto)")
print(f"   P75:       {picker.seg_por_linea.quantile(0.75):.1f}s  (25% de pedidos son más lentos que esto)")
print(f"   P90:       {picker.seg_por_linea.quantile(0.90):.1f}s  (10% de pedidos son más lentos que esto)")
print(f"   Máximo:    {picker.seg_por_linea.max():.1f}s")

print(f"\n⚠️  FRICCIÓN")
umbral = 120
friccion = (picker.seg_por_linea > umbral).mean() * 100
print(f"   Pedidos con alta fricción (>{umbral}s): {friccion:.1f}%")

# Comparar con el promedio de la operación
friccion_op = (operacion_completa.seg_por_linea > umbral).mean() * 100
diff = friccion - friccion_op
simbolo = "▲" if diff > 0 else "▼"
print(f"   Promedio operación:                  {friccion_op:.1f}%")
print(f"   Diferencia vs operación:             {simbolo} {abs(diff):.1f} puntos")

print(f"\n⏰  FRICCIÓN POR HORA DEL DÍA")
por_hora = (picker.groupby('hora')['seg_por_linea']
            .agg(['median', 'count'])
            .round(1))
por_hora.columns = ['mediana_seg', 'pedidos']
print(por_hora.to_string())

print(f"\n📐 CAPACIDAD vs OPERACIÓN")
mediana_op = operacion_completa.seg_por_linea.median()
mediana_picker = picker.seg_por_linea.median()
ranking = (operacion_completa.groupby('picker_id')['seg_por_linea']
           .median()
           .rank(ascending=True))
pos = ranking.get(PICKER, None)
total_pickers = len(ranking)
print(f"   Mediana operación:  {mediana_op:.1f}s")
print(f"   Mediana {PICKER}:     {mediana_picker:.1f}s")
if pos:
    print(f"   Ranking velocidad:  #{int(pos)} de {total_pickers} alistadores")
    print(f"   (donde #1 = más rápido)")

print(f"\n🔍 PERFIL LIMPIO (sin outliers)")
print(f"   Pedidos outlier removidos: {picker['es_outlier'].sum():,} ({picker['es_outlier'].mean()*100:.1f}%)")
print(f"   Pedidos limpios:           {len(picker_limpio):,}")
print(f"   Mediana limpia:            {picker_limpio.seg_por_linea.median():.1f}s")
print(f"   Promedio limpio:           {picker_limpio.seg_por_linea.mean():.1f}s")
print(f"   P75 limpio:                {picker_limpio.seg_por_linea.quantile(0.75):.1f}s")
print(f"   P90 limpio:                {picker_limpio.seg_por_linea.quantile(0.90):.1f}s")
print(f"   Fricción limpia:           {(picker_limpio.seg_por_linea > 120).mean()*100:.1f}%")

ranking_limpio = (df[~df['es_outlier']]
                  .groupby('picker_id')['seg_por_linea']
                  .median()
                  .rank(ascending=True))
pos_limpio = ranking_limpio.get(PICKER, None)
if pos_limpio:
    print(f"   Ranking limpio:            #{int(pos_limpio)} de {len(ranking_limpio)} alistadores")

print(f"\n📋 PEDIDOS CON MAYOR FRICCIÓN (top 10)")
top_friccion = (picker[picker.seg_por_linea > umbral]
                .sort_values('seg_por_linea', ascending=False)
                [['fecha', 'cant_lineas', 'tiempo_minutos', 'seg_por_linea']]
                .head(10))
print(top_friccion.to_string(index=False))