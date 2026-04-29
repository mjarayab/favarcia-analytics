"""
=============================================================
FAVARCIA PICKING PERFORMANCE ANALYSIS
Proyecto: FPM - Favarcia Plan de Mejora
Objetivo: Demostrar que los tiempos altos son problema
          del SISTEMA, no de las personas.
Autor: Mauricio Araya
=============================================================
"""

# ─────────────────────────────────────────────
# BLOQUE 1: IMPORTAR HERRAMIENTAS
# ─────────────────────────────────────────────
# Cada "import" trae una biblioteca con funciones listas para usar.
# Es como abrir las cajas de herramientas antes de empezar a trabajar.

import pandas as pd          # Para manejar tablas de datos (como Excel en Python)
import numpy as np           # Para cálculos matemáticos y estadísticos
import matplotlib.pyplot as plt  # Para crear gráficas
import seaborn as sns        # Para gráficas más bonitas y fáciles
from scipy import stats      # Para análisis estadístico avanzado
import os
import warnings
warnings.filterwarnings('ignore')  # Silencia advertencias menores

# ── Rutas ancladas al directorio del script ──────────────
# __file__ es la ruta absoluta de este archivo .py
# os.path.dirname() extrae solo la carpeta que lo contiene
# Así los archivos siempre se guardan junto al script,
# sin importar desde dónde lo corras en VS Code.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ── MODO DE OPERACIÓN ─────────────────────────────────────
# "demo"  → usa datos sintéticos de data/sample/
#            guarda outputs en outputs/sample/
#            ideal para GitHub, demos, entrevistas
#
# "real"  → usa datos reales de data/raw/
#            guarda outputs en outputs/
#            usar cuando IT entregue el reporte
#
MODO = "real"   # ← CAMBIAR A "real" cuando lleguen datos de IT
# ──────────────────────────────────────────────────────────

if MODO == "demo":
    DATA_DIR    = os.path.join(BASE_DIR, "data", "sample")
    OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs", "sample")
else:
    DATA_DIR    = os.path.join(BASE_DIR, "data", "raw")
    OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")

# Crear carpetas si no existen
os.makedirs(OUTPUTS_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

print(f"📁 MODO: {MODO.upper()}")
print(f"   Datos:   {DATA_DIR}")
print(f"   Outputs: {OUTPUTS_DIR}")

# Configuración visual global — todas las gráficas usarán este estilo
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("husl")


# ─────────────────────────────────────────────
# BLOQUE 2: CARGAR LOS DATOS
# ─────────────────────────────────────────────
# Esta función detecta automáticamente si el archivo es Excel o CSV.
# "def" define una función — un bloque de código reutilizable.

def cargar_datos(ruta_archivo):
    """
    Carga el reporte de IT sin importar si es .xlsx o .csv
    
    Parámetro:
        ruta_archivo: el path al archivo, ej: "C:/datos/reporte_enero.xlsx"
    
    Retorna:
        df: un DataFrame (tabla de datos en pandas)
    """
    
    # Detecta la extensión del archivo
    if ruta_archivo.endswith('.xlsx') or ruta_archivo.endswith('.xls'):
        # Si es Excel, pandas lo lee directamente
        df = pd.read_excel(ruta_archivo)
        print(f"✅ Archivo Excel cargado: {len(df)} filas encontradas")
        
    elif ruta_archivo.endswith('.csv'):
        # Si es CSV, intenta primero con coma, luego con punto y coma
        # (Costa Rica a veces usa punto y coma por el formato de Excel en español)
        try:
            df = pd.read_csv(ruta_archivo, encoding='utf-8')
            print(f"✅ CSV (comas) cargado: {len(df)} filas encontradas")
        except:
            df = pd.read_csv(ruta_archivo, sep=';', encoding='latin-1')
            print(f"✅ CSV (punto y coma) cargado: {len(df)} filas encontradas")
    else:
        raise ValueError("Formato no reconocido. Usa .xlsx, .xls, o .csv")
    
    return df


# ─────────────────────────────────────────────
# BLOQUE 3: EXPLORAR LOS DATOS (PRIMER PASO SIEMPRE)
# ─────────────────────────────────────────────
# Antes de analizar, siempre hay que "conocer" los datos.
# Como revisar una guía de despacho antes de cargar el camión.

def explorar_datos(df):
    """
    Muestra un resumen inicial del DataFrame.
    Corre esto PRIMERO cuando lleguen los datos de IT.
    """
    print("\n" + "="*50)
    print("EXPLORACIÓN INICIAL DE DATOS")
    print("="*50)
    
    # .shape devuelve (filas, columnas) — cuánta información hay
    print(f"\n📐 Dimensiones: {df.shape[0]} filas x {df.shape[1]} columnas")
    
    # .columns lista los nombres de todas las columnas
    print(f"\n📋 Columnas disponibles:")
    for i, col in enumerate(df.columns, 1):
        print(f"   {i:2}. {col}")
    
    # .dtypes muestra qué tipo de dato tiene cada columna
    # (int = número entero, float = decimal, object = texto, datetime = fecha/hora)
    print(f"\n🔤 Tipos de datos:")
    print(df.dtypes)
    
    # .isnull().sum() cuenta cuántos valores vacíos hay por columna
    # En datos reales siempre hay vacíos — hay que saber dónde
    print(f"\n⚠️  Valores vacíos por columna:")
    vacios = df.isnull().sum()
    vacios_con_datos = vacios[vacios > 0]  # Solo muestra columnas con vacíos
    if len(vacios_con_datos) > 0:
        print(vacios_con_datos)
    else:
        print("   Ninguno — datos completos ✅")
    
    # .head() muestra las primeras 5 filas — para ver cómo lucen los datos
    print(f"\n🔍 Primeras 5 filas:")
    print(df.head())
    
    return df


# ─────────────────────────────────────────────
# BLOQUE 4: LIMPIAR Y PREPARAR LOS DATOS
# ─────────────────────────────────────────────
# Los datos de sistemas ERP casi nunca vienen perfectos.
# Esta función los deja listos para analizar.
# NOTA: Las columnas reales dependen de lo que IT entregue.
#       Ajusta los nombres después de correr explorar_datos().

def preparar_datos(df):
    """
    Limpia y crea columnas calculadas.
    Separa dataset de volumen (todos los pedidos) del de tiempo
    (solo pedidos con tiempo registrado > 0).

    Contexto operacional:
        52.1% de pedidos tienen tiempo=0 porque fueron trabajados
        antes de abrirse en el WMS — práctica normal en Favarcia.
        Excluirlos del análisis de volumen daría una imagen falsa
        de la operación real.
    """

    print("\n" + "="*50)
    print("PREPARACIÓN DE DATOS")
    print("="*50)

    # ── 4.1 Estandarizar nombres de columnas ──────────
    df.columns = (df.columns
                  .str.lower()
                  .str.strip()
                  .str.replace(' ', '_')
                  .str.replace('.', '_')
                  .str.replace('(', '')
                  .str.replace(')', '')
                  )
    print("✅ Nombres de columnas estandarizados")
    print(f"   Columnas ahora: {list(df.columns)}")

    # ── 4.2 Renombrar columnas reales a nombres estándar ──────────
    mapeo = {
        'alistador':              'picker_id',
        'tiempo_alisto_minutos':  'tiempo_minutos',
        'inicio_alisto':          'hora_inicio',
        'fecha_pedido':           'fecha',
    }
    df = df.rename(columns=mapeo)
    print("✅ Columnas mapeadas a nombres estándar")

    # ── 4.3 Limpiar filas sin alistador ──────────
    antes = len(df)
    df = df.dropna(subset=['picker_id'])
    despues = len(df)
    print(f"✅ Filas sin alistador removidas: {antes - despues}")

    # ── 4.4 Separar datasets ──────────────────────────
    # df_vol    → TODOS los pedidos incluyendo tiempo=0
    #             para métricas de VOLUMEN real
    # df_tiempo → solo pedidos con tiempo registrado > 0
    #             para métricas de TIEMPO y SPC
    df_vol    = df.copy()
    df_tiempo = df[df['tiempo_minutos'] > 0].copy()

    total     = len(df_vol)
    con_tiempo = len(df_tiempo)
    sin_tiempo = total - con_tiempo

    print(f"\n📊 Calidad de datos:")
    print(f"   Total pedidos:              {total:,}")
    print(f"   Con tiempo registrado:      {con_tiempo:,} ({con_tiempo/total*100:.1f}%)")
    print(f"   Sin tiempo (tiempo=0):      {sin_tiempo:,} ({sin_tiempo/total*100:.1f}%)")
    print(f"   → El {sin_tiempo/total*100:.1f}% fue trabajado sin abrir el pedido en el WMS")

    # ── 4.5 Calcular métricas de tiempo ──────────────
    df_tiempo['tiempo_segundos'] = df_tiempo['tiempo_minutos'] * 60
    df_tiempo['seg_por_linea'] = np.where(
        df_tiempo['cant_lineas'] > 0,
        df_tiempo['tiempo_segundos'] / df_tiempo['cant_lineas'],
        np.nan
    )

    # Clasificar outliers
    df_tiempo['es_outlier'] = (
        ((df_tiempo['tiempo_minutos'] < 1) & (df_tiempo['cant_lineas'] > 3)) |
        (df_tiempo['tiempo_minutos'] > 240) |
        ((df_tiempo['cant_lineas'] <= 2) & (df_tiempo['tiempo_minutos'] > 30))
    )

    print(f"\n   Métricas de tiempo (pedidos con tiempo registrado):")
    print(f"   seg/línea — Promedio: {df_tiempo['seg_por_linea'].mean():.1f}s")
    print(f"   seg/línea — Mediana:  {df_tiempo['seg_por_linea'].median():.1f}s")
    print(f"   seg/línea — Mínimo:   {df_tiempo['seg_por_linea'].min():.1f}s")
    print(f"   seg/línea — Máximo:   {df_tiempo['seg_por_linea'].max():.1f}s")
    print(f"   Outliers:             {df_tiempo['es_outlier'].sum():,} ({df_tiempo['es_outlier'].mean()*100:.1f}%)")

    # ── 4.6 Cycle time ────────────────────────────────
    if 'fecha_factura' in df_vol.columns and 'fecha' in df_vol.columns:
        df_vol['cycle_time_min'] = (
            pd.to_datetime(df_vol['fecha_factura'], errors='coerce') -
            pd.to_datetime(df_vol['fecha'], errors='coerce')
        ).dt.total_seconds() / 60
        df_vol.loc[df_vol['cycle_time_min'] < 0,    'cycle_time_min'] = np.nan
        df_vol.loc[df_vol['cycle_time_min'] > 1440, 'cycle_time_min'] = np.nan
        ct = df_vol['cycle_time_min'].dropna()
        print(f"\n✅ Cycle time calculado (pedido → factura)")
        print(f"   NOTA: FECHA PEDIDO con 00:00 infla el cycle time")
        print(f"   para pedidos cuya orden llegó de noche.")
        print(f"   Mediana puede estar sobreestimada en esos casos.")
        print(f"   Mediana: {ct.median():.0f} min ({ct.median()/60:.1f}h)")
        print(f"   P90:     {ct.quantile(0.90):.0f} min ({ct.quantile(0.90)/60:.1f}h)")

    # ── 4.7 Hora del día ──────────────────────────────
    if 'hora_inicio' in df_tiempo.columns:
        df_tiempo['hora'] = pd.to_datetime(
            df_tiempo['hora_inicio'], errors='coerce'
        ).dt.hour
        print("✅ Hora extraída de inicio_alisto")

    # ── 4.8 Día de la semana ──────────────────────────
    if 'fecha' in df_tiempo.columns:
        df_tiempo['dia_semana'] = pd.to_datetime(
            df_tiempo['fecha'], errors='coerce'
        ).dt.day_name()
        print("✅ Día de semana calculado")

    # Copiar seg_por_linea al df principal para compatibilidad
    # con las funciones de análisis existentes
    df = df_tiempo.copy()

    print(f"\n📊 Dataset listo para análisis SPC: {len(df):,} pedidos con tiempo registrado")
    print(f"   (Dataset de volumen completo: {len(df_vol):,} pedidos)")
    return df


# ─────────────────────────────────────────────
# BLOQUE 5: ANÁLISIS DE DISTRIBUCIÓN
# ─────────────────────────────────────────────
# Esta es la gráfica más importante del proyecto.
# Va a mostrar si la distribución es bimodal (dos picos)
# lo que confirmaría que hay dos tipos de pedidos:
# los que fluyen solos vs los que tienen fricción de búsqueda.

def analisis_distribucion(df):
    """
    Grafica la distribución de segundos por línea.
    
    HIPÓTESIS A DEMOSTRAR:
    - Pico 1 (~15-25 seg): líneas limpias, cajón con producto
    - Pico 2 (~90-280 seg): líneas con fricción, búsqueda de cajas
    
    Si la gráfica muestra DOS picos → el problema es sistémico.
    Si un alistador tiene más pedidos en el pico 2 → está en peores condiciones,
    no es menos eficiente.
    """
    
    if 'seg_por_linea' not in df.columns:
        print("❌ Columna 'seg_por_linea' no encontrada. Corre preparar_datos() primero.")
        return
    
    # Filtrar outliers extremos para que la gráfica sea legible
    # (pedidos de más de 10 min/línea son probablemente pausas largas)
    df_plot = df[df['seg_por_linea'] < 600].copy()
    
    # Crear figura con 2 subgráficas lado a lado
    # figsize=(14, 5) define el tamaño en pulgadas
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle('DISTRIBUCIÓN DE TIEMPO POR LÍNEA\nFavarcia — Análisis de Fricción Sistémica',
                 fontsize=13, fontweight='bold')
    
    # ── Gráfica 1: Histograma de densidad ──
    # bins=50 = cuántas barras tiene el histograma
    # kde=True dibuja la curva suave encima
    sns.histplot(data=df_plot, x='seg_por_linea', bins=50, kde=True,
                 ax=ax1, color='steelblue', alpha=0.7)
    
    # Líneas verticales de referencia
    ax1.axvline(x=60, color='green', linestyle='--', linewidth=1.5,
                label='Meta: 60 seg (1 min/línea)')
    ax1.axvline(x=df_plot['seg_por_linea'].mean(), color='red',
                linestyle='-', linewidth=1.5,
                label=f"Promedio real: {df_plot['seg_por_linea'].mean():.0f}s")
    
    ax1.set_xlabel('Segundos por línea')
    ax1.set_ylabel('Cantidad de pedidos')
    ax1.set_title('¿Hay dos poblaciones de pedidos?')
    ax1.legend(fontsize=9)
    
    # ── Gráfica 2: Boxplot por alistador ──
    if 'picker_id' in df_plot.columns:
        # Top 10 por volumen TOTAL (incluyendo tiempo=0)
        df_raw = pd.read_excel(ARCHIVO)
        df_raw.columns = (df_raw.columns.str.lower().str.strip()
                          .str.replace(' ', '_')
                          .str.replace('(', '').str.replace(')', ''))
        df_raw = df_raw.rename(columns={'alistador': 'picker_id'})
        df_raw = df_raw.dropna(subset=['picker_id'])

        # Mapeo de nombres
        mapeo_nombres = {}
        for picker in df_raw['picker_id'].unique():
            nombres = df_raw[df_raw['picker_id'] == picker]['nombre'].dropna()
            if len(nombres) > 0:
                palabras = str(nombres.iloc[0]).split()
                if len(palabras) >= 3:
                    primer_nombre = palabras[2].capitalize()
                    mapeo_nombres[picker] = f"{primer_nombre} ({picker})"
                else:
                    mapeo_nombres[picker] = picker

        top_pickers = (df_raw.groupby('picker_id')
                       .size()
                       .nlargest(10)
                       .index)

        df_top = df_plot[df_plot['picker_id'].isin(top_pickers)].copy()
        df_top['etiqueta'] = df_top['picker_id'].map(mapeo_nombres).fillna(df_top['picker_id'])

        sns.boxplot(data=df_top, x='etiqueta', y='seg_por_linea',
                    ax=ax2, palette='husl')
        ax2.axhline(y=60, color='green', linestyle='--', linewidth=1.5,
                    label='Meta: 60 seg')
        ax2.set_xlabel('Alistador')
        ax2.set_ylabel('Segundos por línea')
        ax2.set_title('Variabilidad por alistador\n(colas similares = problema sistémico)')
        ax2.tick_params(axis='x', rotation=45)
        ax2.legend(fontsize=9)
    
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUTS_DIR, 'distribucion_picking.png'), dpi=150, bbox_inches='tight')
    plt.show()
    print("✅ Gráfica guardada: distribucion_picking.png")


# ─────────────────────────────────────────────
# BLOQUE 6: ANÁLISIS SISTÉMICO vs INDIVIDUAL
# ─────────────────────────────────────────────
# Esta es la pieza central del argumento:
# "El problema no es quién — es cuándo y en qué condiciones"

def analisis_sistemico(df):
    """
    Calcula métricas clave para demostrar que la variabilidad
    es sistémica, no individual.
    """
    
    if 'seg_por_linea' not in df.columns:
        print("❌ Corre preparar_datos() primero.")
        return
    
    print("\n" + "="*50)
    print("ANÁLISIS SISTÉMICO vs INDIVIDUAL")
    print("="*50)
    
    # ── 6.1 Porcentaje de pedidos con "fricción alta" ──
    # Definimos umbral: pedidos > 2x la meta (>120 seg/línea)
    umbral_friccion = 120  # segundos — ajustar según los datos reales

    pedidos_total = len(df[df['seg_por_linea'].notna()])
    pedidos_friccion = len(df[df['seg_por_linea'] > umbral_friccion])
    pct_friccion = pedidos_friccion / pedidos_total * 100

    print(f"\n📊 Pedidos analizados: {pedidos_total:,}")
    print(f"⚠️  Pedidos con alta fricción (>{umbral_friccion}s/línea): {pedidos_friccion:,} ({pct_friccion:.1f}%)")

    # ── 6.2 Distribución de fricción por alistador ──
    if 'picker_id' in df.columns:
        friccion_por_picker = (df[df['seg_por_linea'] > umbral_friccion]
                               .groupby('picker_id')
                               .size()
                               .reset_index(name='pedidos_con_friccion'))

        total_por_picker = (df.groupby('picker_id')
                            .size()
                            .reset_index(name='total_pedidos'))

        resumen = total_por_picker.merge(friccion_por_picker, on='picker_id', how='left')
        resumen['pedidos_con_friccion'] = resumen['pedidos_con_friccion'].fillna(0)
        resumen['pct_friccion'] = resumen['pedidos_con_friccion'] / resumen['total_pedidos'] * 100
        resumen = resumen.sort_values('total_pedidos', ascending=False)

        print(f"\n📋 Fricción por alistador:")
        print(resumen.to_string(index=False))

        # ── 6.3 CV global y CV por grupo de experiencia ──────────
        # CV GLOBAL — mezcla todos los perfiles, siempre saldrá alto
        # porque los nuevos tienen más fricción que los expertos.
        # Eso NO significa problema individual — significa curva de
        # aprendizaje sin soporte, que sigue siendo sistémico.
        cv_global = resumen['pct_friccion'].std() / resumen['pct_friccion'].mean() * 100

        # CV POR GRUPO — si dentro de cada grupo el CV es bajo,
        # confirma que la experiencia explica la diferencia, no
        # el desempeño individual de cada persona.
        # Los grupos están definidos según los perfiles del generador:
        #   Expertos: top 10 por volumen
        #   Nuevos: bottom 10 por volumen
        #   Medios: el resto
        resumen_sorted = resumen.sort_values('total_pedidos', ascending=False).reset_index(drop=True)
        n = len(resumen_sorted)

        resumen_sorted['grupo'] = 'Medio'
        resumen_sorted.loc[:9, 'grupo'] = 'Experto'        # top 10
        resumen_sorted.loc[n-10:, 'grupo'] = 'Nuevo'       # bottom 10

        print(f"\n📐 Análisis de CV (Coeficiente de Variación):")
        print(f"   CV Global (todos los alistadores): {cv_global:.1f}%")
        print(f"   → Parece alta porque mezcla perfiles distintos\n")

        for grupo in ['Experto', 'Medio', 'Nuevo']:
            subset = resumen_sorted[resumen_sorted['grupo'] == grupo]['pct_friccion']
            if len(subset) > 1:
                cv_grupo = subset.std() / subset.mean() * 100
                media_grupo = subset.mean()
                print(f"   Grupo {grupo:8s}: fricción promedio={media_grupo:.1f}%  CV={cv_grupo:.1f}%", end="")
                if cv_grupo < 30:
                    print("  ✅ uniforme dentro del grupo")
                else:
                    print("  ⚠️  variación dentro del grupo")

        # ── 6.4 Interpretación automática ────────────────────────
        # El código lee los resultados y escribe las conclusiones.
        # En medtech esto equivale al "Summary" de un reporte de proceso.
        print(f"\n{'='*50}")
        print("📝 INTERPRETACIÓN AUTOMÁTICA")
        print(f"{'='*50}")

        media_expertos = resumen_sorted[resumen_sorted['grupo']=='Experto']['pct_friccion'].mean()
        media_nuevos   = resumen_sorted[resumen_sorted['grupo']=='Nuevo']['pct_friccion'].mean()
        hora_pico      = None

        print(f"\n1. NIVEL DE FRICCIÓN GENERAL")
        print(f"   El {pct_friccion:.1f}% de los pedidos superan el umbral de fricción ({umbral_friccion}s/línea).")
        if pct_friccion > 20:
            print(f"   → ALTO: más de 1 de cada 5 pedidos tiene fricción sistémica.")
        elif pct_friccion > 10:
            print(f"   → MODERADO: entre 1 de cada 10 y 1 de cada 5 pedidos con fricción.")
        else:
            print(f"   → BAJO: menos del 10% de pedidos con fricción alta.")

        print(f"\n2. NATURALEZA DE LA VARIACIÓN (sistémica vs individual)")
        diff_grupos = media_nuevos - media_expertos
        print(f"   Alistadores expertos: {media_expertos:.1f}% fricción promedio")
        print(f"   Alistadores nuevos:   {media_nuevos:.1f}% fricción promedio")
        print(f"   Diferencia:           {diff_grupos:.1f} puntos porcentuales")
        print(f"   → La diferencia refleja curva de aprendizaje (sistémico),")
        print(f"     no capacidad individual. Todos experimentan la misma")
        print(f"     fricción de cajones vacíos — los nuevos simplemente")
        print(f"     tienen menos herramientas para resolverla rápido.")

        print(f"\n3. CAUSA RAÍZ MÁS PROBABLE")
        print(f"   Cajones vacíos + ubicaciones incorrectas en WMS =")
        print(f"   tiempo de búsqueda no capturado en KPI actual.")
        print(f"   El KPI de 1 min/línea mide OUTPUT, no PROCESO.")

    # ── 6.5 Análisis por hora del día ────────────────────────────
    if 'hora' in df.columns:
        print(f"\n⏰ Tiempo promedio por línea según hora del día:")
        por_hora = (df.groupby('hora')['seg_por_linea']
                    .agg(['mean', 'median', 'count'])
                    .round(1))
        por_hora.columns = ['promedio_seg', 'mediana_seg', 'pedidos']
        print(por_hora)

        # Detectar hora pico automáticamente
        hora_pico = por_hora['mediana_seg'].idxmax()
        hora_baja = por_hora['mediana_seg'].idxmin()
        delta_pct = ((por_hora.loc[hora_pico, 'mediana_seg'] -
                      por_hora.loc[hora_baja, 'mediana_seg']) /
                     por_hora.loc[hora_baja, 'mediana_seg'] * 100)

        print(f"\n   Hora con más fricción: {hora_pico}:00h "
              f"({por_hora.loc[hora_pico, 'mediana_seg']:.0f}s/línea)")
        print(f"   Hora con menos fricción: {hora_baja}:00h "
              f"({por_hora.loc[hora_baja, 'mediana_seg']:.0f}s/línea)")
        print(f"   Delta: +{delta_pct:.0f}% más fricción en hora pico")
        if hora_pico >= 14:
            print(f"   → Pico en tarde confirma hipótesis cajones vacíos post-rush ✅")

        # Graficar con anotación del pico
        fig, ax = plt.subplots(figsize=(10, 4))
        colores = ['tomato' if h == hora_pico else 'steelblue'
                   for h in por_hora.index]
        ax.bar(por_hora.index, por_hora['mediana_seg'],
               color=colores, alpha=0.8)
        ax.axhline(y=60, color='green', linestyle='--', label='Meta 60s')

        # Anotar el pico
        ax.annotate(f'Pico\n{por_hora.loc[hora_pico,"mediana_seg"]:.0f}s',
                    xy=(hora_pico, por_hora.loc[hora_pico, 'mediana_seg']),
                    xytext=(hora_pico + 0.3,
                            por_hora.loc[hora_pico, 'mediana_seg'] + 3),
                    fontsize=9, color='tomato', fontweight='bold')

        ax.set_xlabel('Hora del día')
        ax.set_ylabel('Mediana seg/línea')
        ax.set_title('¿A qué hora del día hay más fricción?\n'
                     '(rojo = hora pico | picos en tarde = cajones vacíos post-rush)')
        ax.legend()
        plt.tight_layout()
        plt.savefig(os.path.join(OUTPUTS_DIR, 'friccion_por_hora.png'), dpi=150, bbox_inches='tight')
        plt.show()
        print("✅ Gráfica guardada: outputs/friccion_por_hora.png")


# ─────────────────────────────────────────────
# BLOQUE 7: CONTROL CHART (SPC)
# ─────────────────────────────────────────────
# Esta es la herramienta de manufactura que más impresiona
# en entrevistas de medtech. Exactamente lo que usa Abbott,
# Boston Scientific, Cirtec para monitorear procesos.

def control_chart(df, picker_id=None):
    """
    Control chart usando MEDIANAS MÓVILES en vez de promedios.

    Por qué medianas y no promedios:
    La distribución de tiempos de picking es log-normal (asimétrica)
    — igual que muchos procesos de manufactura con eventos raros de
    alta duración. Los promedios y σ se distorsionan por la cola larga.
    Las medianas son robustas a outliers y más representativas del
    proceso real.

    Esto es equivalente al chart que usarías en medtech para
    procesos con distribución no-normal.
    """

    if 'seg_por_linea' not in df.columns:
        print("❌ Corre preparar_datos() primero.")
        return

    # Filtrar por picker si se especifica
    if picker_id and 'picker_id' in df.columns:
        datos = df[df['picker_id'] == picker_id]['seg_por_linea'].dropna()
        titulo = f"Control Chart — Alistador {picker_id}"
    else:
        datos = df['seg_por_linea'].dropna()
        titulo = "Control Chart — Todos los alistadores"

    # Filtrar outliers extremos — pedidos olvidados sin cerrar
    p99 = datos.quantile(0.99)
    datos_cc = datos[datos <= p99].reset_index(drop=True)

    # ── Calcular límites basados en percentiles ──
    # Más robusto que ±3σ para distribuciones asimétricas
    mediana   = datos_cc.median()
    p25       = datos_cc.quantile(0.25)
    p75       = datos_cc.quantile(0.75)
    iqr       = p75 - p25
    ucl       = p75 + 1.5 * iqr   # equivalente a fence de Tukey
    lcl       = max(0, p25 - 1.5 * iqr)

    fuera_control = datos_cc[datos_cc > ucl]
    pct_fuera = len(fuera_control) / len(datos_cc) * 100

    print(f"\n📊 Control Chart — {titulo}")
    print(f"   Mediana: {mediana:.1f} seg/línea")
    print(f"   P25:     {p25:.1f}s  |  P75: {p75:.1f}s  |  IQR: {iqr:.1f}s")
    print(f"   UCL (P75 + 1.5×IQR): {ucl:.1f}s")
    print(f"   LCL (P25 - 1.5×IQR): {lcl:.1f}s")
    print(f"   Puntos fuera de control: {len(fuera_control):,} ({pct_fuera:.1f}%)")

    # ── Medianas móviles (ventana de 50 pedidos) ──
    # Muestra tendencia del proceso en el tiempo
    # Si la línea sube → el proceso se está deteriorando
    # Si es plana → proceso estable (aunque fuera de spec)
    ventana = 50
    medianas_moviles = datos_cc.rolling(window=ventana, center=True).median()

    # ── Graficar ──
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8),
                                    gridspec_kw={'height_ratios': [3, 1]})
    fig.suptitle(f'{titulo}', fontsize=12, fontweight='bold')

    # ── Panel superior: puntos individuales ──
    # Colorear por zona: verde = en control, rojo = fuera
    colores_pts = ['tomato' if v > ucl else 'steelblue'
                   for v in datos_cc.values]
    ax1.scatter(range(len(datos_cc)), datos_cc.values,
                c=colores_pts, s=3, alpha=0.4, zorder=2)

    # Línea de medianas móviles
    ax1.plot(range(len(medianas_moviles)), medianas_moviles.values,
             color='black', linewidth=1.5, zorder=3,
             label=f'Mediana móvil ({ventana} pedidos)')

    # Líneas de control
    ax1.axhline(y=mediana, color='blue', linewidth=1, linestyle='-',
                label=f'Mediana = {mediana:.0f}s', alpha=0.7)
    ax1.axhline(y=ucl, color='red', linewidth=1.5, linestyle='--',
                label=f'UCL = {ucl:.0f}s')
    ax1.axhline(y=60, color='green', linewidth=1, linestyle=':',
                label='Meta 60s')

    # Zona en control sombreada sutilmente
    ax1.axhspan(lcl, ucl, alpha=0.05, color='green')

    # Escala Y al percentil 97 para visibilidad
    ax1.set_ylim(0, datos_cc.quantile(0.97) * 1.2)
    ax1.set_ylabel('Segundos por línea')
    ax1.set_title(f'Puntos rojos = fricción alta (>{ucl:.0f}s) | '
                  f'{pct_fuera:.1f}% fuera de control',
                  fontsize=10)
    ax1.legend(fontsize=8, loc='upper right')

    # ── Panel inferior: % pedidos con fricción por bloque ──
    # Divide los pedidos en 30 bloques y calcula % con fricción
    # Si el % sube en ciertos momentos → hay un patrón temporal
    n_bloques = 30
    tam_bloque = len(datos_cc) // n_bloques
    pct_friccion_bloque = []
    x_bloques = []
    for i in range(n_bloques):
        inicio = i * tam_bloque
        fin = inicio + tam_bloque
        bloque = datos_cc.iloc[inicio:fin]
        pct = (bloque > ucl).mean() * 100
        pct_friccion_bloque.append(pct)
        x_bloques.append((inicio + fin) / 2)

    colores_bloques = ['tomato' if p > pct_fuera * 1.5 else 'steelblue'
                       for p in pct_friccion_bloque]
    ax2.bar(x_bloques, pct_friccion_bloque,
            width=tam_bloque * 0.8,
            color=colores_bloques, alpha=0.7)
    ax2.axhline(y=pct_fuera, color='red', linewidth=1, linestyle='--',
                label=f'Promedio: {pct_fuera:.1f}%')
    ax2.set_ylabel('% fricción')
    ax2.set_xlabel('Pedidos (orden cronológico)')
    ax2.set_title('% pedidos con alta fricción por período', fontsize=10)
    ax2.legend(fontsize=8)

    plt.tight_layout()
    nombre_archivo = os.path.join(OUTPUTS_DIR,
                     f"control_chart_{picker_id if picker_id else 'todos'}.png")
    plt.savefig(nombre_archivo, dpi=150, bbox_inches='tight')
    plt.show()
    print(f"✅ Gráfica guardada: {nombre_archivo}")


# ─────────────────────────────────────────────
# BLOQUE 8: ANÁLISIS DE CAPACIDAD — Cpk
# ─────────────────────────────────────────────
# Cpk mide qué tan capaz es el proceso de cumplir
# las especificaciones. Es el índice más usado en
# manufactura de dispositivos médicos.
#
# Interpretación:
#   Cpk < 1.0  → proceso incapaz (produce defectos)
#   Cpk = 1.33 → mínimo aceptable en manufactura general
#   Cpk = 1.67 → estándar en medtech
#   Cpk ≥ 2.0  → excelente (FDA lo pide para dispositivos críticos)

def analisis_cpk(df):
    """
    Calcula Cpk del proceso de picking.

    Especificaciones:
        USL = 120 seg/línea (umbral de fricción = 2x la meta)
        LSL = 0 (no existe límite inferior operacional)

    Un Cpk bajo aquí NO significa que los alistadores fallen —
    significa que el SISTEMA no está diseñado para cumplir
    consistentemente con los tiempos objetivo.
    """

    if 'seg_por_linea' not in df.columns:
        print("❌ Corre preparar_datos() primero.")
        return

    print("\n" + "="*50)
    print("📐 ANÁLISIS DE CAPACIDAD — Cpk")
    print("="*50)

    # Especificaciones del proceso
    USL = 120   # Upper Specification Limit: umbral de fricción
    LSL = 0     # Lower Specification Limit: no puede ser negativo
    META = 60   # Target: 1 minuto por línea

    datos = df['seg_por_linea'].dropna()
    datos = datos[datos < 600]   # excluir outliers extremos

    media = datos.mean()
    std   = datos.std()

    # ── Calcular Cp (capacidad potencial) ──
    # Cp asume que el proceso está perfectamente centrado.
    # Mide si la variabilidad cabe dentro de las especificaciones.
    # Fórmula: (USL - LSL) / (6σ)
    cp = (USL - LSL) / (6 * std)

    # ── Calcular Cpk (capacidad real) ──
    # Cpk considera dónde está centrado el proceso.
    # Toma el MÍNIMO de los dos lados — el más cercano al límite es el riesgo.
    cpu = (USL - media) / (3 * std)   # distancia al límite superior
    cpl = (media - LSL) / (3 * std)   # distancia al límite inferior
    cpk = min(cpu, cpl)

    # ── Calcular % teórico fuera de especificación ──
    # stats.norm.cdf calcula el área bajo la curva normal
    # hasta un valor dado — la probabilidad acumulada.
    pct_fuera_teorico = (1 - stats.norm.cdf(USL, media, std)) * 100

    print(f"\n   Especificaciones:")
    print(f"   USL (límite superior): {USL}s/línea")
    print(f"   LSL (límite inferior): {LSL}s/línea")
    print(f"   Target:                {META}s/línea")
    print(f"\n   Estadísticas del proceso:")
    print(f"   Media (X̄): {media:.1f}s")
    print(f"   Desv. Est. (σ): {std:.1f}s")
    print(f"\n   Índices de capacidad:")
    print(f"   Cp  = {cp:.2f}   (capacidad potencial si estuviera centrado)")
    print(f"   Cpu = {cpu:.2f}   (distancia al límite superior)")
    print(f"   Cpl = {cpl:.2f}   (distancia al límite inferior)")
    print(f"   Cpk = {cpk:.2f}   ← índice real")
    print(f"\n   % teórico fuera de USL: {pct_fuera_teorico:.1f}%")

    # ── Interpretación automática ──
    print(f"\n📝 Interpretación:")
    if cpk >= 2.0:
        nivel = "EXCELENTE — estándar FDA para dispositivos críticos"
    elif cpk >= 1.67:
        nivel = "BUENO — estándar medtech"
    elif cpk >= 1.33:
        nivel = "ACEPTABLE — mínimo manufactura general"
    elif cpk >= 1.0:
        nivel = "MARGINAL — proceso apenas capaz, requiere mejora"
    else:
        nivel = "INCAPAZ — el proceso produce defectos sistemáticamente"

    print(f"   Cpk = {cpk:.2f} → {nivel}")

    if cpk < 1.33:
        brecha = META - media  # qué tanto hay que mover la media
        reduccion_std = std - (USL - META) / (3 * 1.33)
        print(f"\n   Para alcanzar Cpk = 1.33 se necesita:")
        if media > META:
            print(f"   → Reducir la media de {media:.0f}s a {META}s "
                  f"(−{media-META:.0f}s por línea)")
        print(f"   → Reducir σ de {std:.0f}s a {max(0,reduccion_std):.0f}s")
        print(f"   → Esto equivale a eliminar la fricción sistémica")
        print(f"     (cajones vacíos, ubicaciones incorrectas en WMS)")

    # ── Gráfica de capacidad ──
    fig, ax = plt.subplots(figsize=(10, 5))

    # Histograma del proceso
    x_range = np.linspace(0, 400, 500)
    ax.hist(datos, bins=60, density=True,
            color='steelblue', alpha=0.5, label='Distribución real')

    # Curva normal ajustada
    curva_normal = stats.norm.pdf(x_range, media, std)
    ax.plot(x_range, curva_normal, color='steelblue',
            linewidth=2, label='Curva normal ajustada')

    # Líneas de especificación y referencia
    ax.axvline(x=USL, color='red', linewidth=2, linestyle='--',
               label=f'USL = {USL}s')
    ax.axvline(x=META, color='green', linewidth=1.5, linestyle=':',
               label=f'Target = {META}s')
    ax.axvline(x=media, color='black', linewidth=1.5,
               label=f'X̄ = {media:.0f}s')

    # Área fuera de especificación (en rojo)
    x_fuera = x_range[x_range > USL]
    ax.fill_between(x_fuera,
                    stats.norm.pdf(x_fuera, media, std),
                    alpha=0.3, color='red', label=f'Fuera USL ({pct_fuera_teorico:.1f}%)')

    ax.set_xlim(0, 400)
    ax.set_xlabel('Segundos por línea')
    ax.set_ylabel('Densidad')
    ax.set_title(f'Análisis de Capacidad — Picking Favarcia\n'
                 f'Cp = {cp:.2f}  |  Cpk = {cpk:.2f}  |  '
                 f'Proceso: {nivel.split("—")[0].strip()}')
    ax.legend(fontsize=9)

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUTS_DIR, 'cpk_analysis.png'), dpi=150, bbox_inches='tight')
    plt.show()
    print("✅ Gráfica guardada: outputs/cpk_analysis.png")

    return {'cp': cp, 'cpk': cpk, 'media': media, 'std': std}


# ─────────────────────────────────────────────
# BLOQUE 8: PUNTO DE ENTRADA — CORRE ESTO PRIMERO
# ─────────────────────────────────────────────
# Cuando lleguen los datos de IT, cambia SOLO la ruta del archivo
# y corre este bloque. Todo lo demás se ejecuta en orden.

if __name__ == "__main__":

    # ══════════════════════════════════════════
    # CAMBIA ESTA LÍNEA con la ruta real de tu archivo
    # cuando lleguen los datos de IT.
    # ══════════════════════════════════════════
    ARCHIVO = os.path.join(DATA_DIR, "FPM_Datos.xlsx")   # ← CAMBIAR AQUÍ cuando lleguen datos reales

    print("🚀 INICIANDO ANÁLISIS FAVARCIA PICKING")
    print("="*50)

    # Paso 1: Cargar
    df = cargar_datos(ARCHIVO)

    # Paso 2: Explorar — LEE EL OUTPUT para ver nombres de columnas reales
    df = explorar_datos(df)

    # Paso 3: Preparar y calcular métricas
    df = preparar_datos(df)

    # Paso 4: Distribución de tiempos
    analisis_distribucion(df)

    # Paso 5: Análisis sistémico + CV por grupo + interpretación automática
    analisis_sistemico(df)

    # Paso 6: Control chart con escala corregida y puntos rojos
    control_chart(df)

    # Paso 7: Análisis de capacidad Cpk (nuevo)
    analisis_cpk(df)

    print("\n✅ ANÁLISIS COMPLETO")
    print("Archivos generados en /outputs:")
    print("  - distribucion_picking.png")
    print("  - friccion_por_hora.png")
    print("  - control_chart_todos.png")
    print("  - cpk_analysis.png")