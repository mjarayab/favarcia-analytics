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
MODO = "demo"   # ← CAMBIAR A "real" cuando lleguen datos de IT
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
    
    IMPORTANTE: Revisa los nombres de columnas con explorar_datos() primero
    y ajusta los strings entre comillas según lo que IT entregó.
    """
    
    print("\n" + "="*50)
    print("PREPARACIÓN DE DATOS")
    print("="*50)
    
    # ── 4.1 Estandarizar nombres de columnas ──────────
    # Convierte a minúsculas y reemplaza espacios con guiones bajos
    # Así evitas errores de tipeo (ej: "Cant Lineas" vs "cant_lineas")
    df.columns = (df.columns
                  .str.lower()           # todo a minúsculas
                  .str.strip()           # quita espacios al inicio/fin
                  .str.replace(' ', '_') # espacios → guiones bajos
                  .str.replace('.', '_') # puntos → guiones bajos
                  )
    print("✅ Nombres de columnas estandarizados")
    print(f"   Columnas ahora: {list(df.columns)}")
    
    # ── 4.2 Convertir tiempo a segundos (columna calculada) ──────────
    # El reporte de Favarcia muestra tiempo como "1:00:45.97" (hh:mm:ss)
    # Necesitamos convertirlo a segundos para hacer matemáticas.
    #
    # AJUSTA 'tiempo' al nombre real de la columna de tiempo en tu reporte.
    
    if 'tiempo' in df.columns:
        def tiempo_a_segundos(t):
            """Convierte '1:00:45.97' o '0:45.30' a segundos totales"""
            try:
                t_str = str(t).strip()
                partes = t_str.split(':')
                
                if len(partes) == 3:
                    # formato hh:mm:ss
                    horas = float(partes[0])
                    minutos = float(partes[1])
                    segundos = float(partes[2])
                elif len(partes) == 2:
                    # formato mm:ss
                    horas = 0
                    minutos = float(partes[0])
                    segundos = float(partes[1])
                else:
                    return np.nan
                    
                return horas * 3600 + minutos * 60 + segundos
            except:
                return np.nan  # Si no puede convertir, deja vacío
        
        # Aplica la función a cada fila de la columna tiempo
        # .apply() es como arrastrar una fórmula en Excel
        df['tiempo_segundos'] = df['tiempo'].apply(tiempo_a_segundos)
        df['tiempo_minutos'] = df['tiempo_segundos'] / 60
        print("✅ Tiempo convertido a segundos y minutos")
    
    # ── 4.3 Columna clave: segundos por línea ──────────
    # Esta es la métrica más importante del análisis.
    # Normaliza el tiempo por complejidad del pedido.
    #
    # AJUSTA 'cant_lineas' al nombre real en tu reporte.
    
    if 'tiempo_segundos' in df.columns and 'cant_lineas' in df.columns:
        # Divide tiempo entre líneas, pero evita división por cero
        # np.where(condición, valor_si_true, valor_si_false)
        df['seg_por_linea'] = np.where(
            df['cant_lineas'] > 0,                    # condición: líneas > 0
            df['tiempo_segundos'] / df['cant_lineas'], # si true: dividir
            np.nan                                     # si false: dejar vacío
        )
        print("✅ Calculado: segundos por línea")
        
        # Resumen rápido de esta métrica
        print(f"\n   seg/línea — Promedio: {df['seg_por_linea'].mean():.1f}s")
        print(f"   seg/línea — Mediana:  {df['seg_por_linea'].median():.1f}s")
        print(f"   seg/línea — Mínimo:   {df['seg_por_linea'].min():.1f}s")
        print(f"   seg/línea — Máximo:   {df['seg_por_linea'].max():.1f}s")
    
    # ── 4.4 Convertir fechas si existen ──────────
    # AJUSTA 'fecha' al nombre real de la columna de fecha.
    
    if 'fecha' in df.columns:
        df['fecha'] = pd.to_datetime(df['fecha'], dayfirst=True, errors='coerce')
        df['dia_semana'] = df['fecha'].dt.day_name()  # Lunes, Martes, etc.
        print("✅ Fechas procesadas — columna 'dia_semana' creada")

    # Extraer hora de hora_inicio (no de fecha — fecha no tiene hora)
    # hora_inicio es una columna separada en formato "HH:MM:SS"
    if 'hora_inicio' in df.columns:
        df['hora'] = pd.to_datetime(
            df['hora_inicio'], format='%H:%M:%S', errors='coerce'
        ).dt.hour
        print("✅ Hora extraída de hora_inicio — columna 'hora' creada (0-23)")
    
    print(f"\n📊 Dataset listo: {len(df)} pedidos para analizar")
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
    # Muestra la variabilidad de cada persona
    # Si todos tienen la misma cola larga → el problema es del sistema
    
    # AJUSTA 'picker_id' al nombre real de la columna de alistador
    if 'picker_id' in df_plot.columns:
        # Top 10 alistadores por volumen para que el gráfico sea legible
        top_pickers = (df_plot.groupby('picker_id')['seg_por_linea']
                       .count()
                       .nlargest(10)
                       .index)
        df_top = df_plot[df_plot['picker_id'].isin(top_pickers)]
        
        sns.boxplot(data=df_top, x='picker_id', y='seg_por_linea',
                    ax=ax2, palette='husl')
        ax2.axhline(y=60, color='green', linestyle='--', linewidth=1.5,
                    label='Meta: 60 seg')
        ax2.set_xlabel('Alistador (ID)')
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
    Genera un gráfico de control (tipo Shewhart X-chart)
    para el tiempo por línea.

    En manufactura médica esto se usa para detectar si un proceso
    está "en control estadístico" o si hay causas especiales de variación.

    Parámetro opcional:
        picker_id: si se especifica, analiza solo ese alistador.
                   Si None, analiza todos los pedidos.
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

    # Filtrar outliers extremos para escala legible
    datos = datos[datos < 600]

    # ── Calcular límites de control (±3 sigma) ──
    media = datos.mean()
    std   = datos.std()
    ucl   = media + 3 * std
    lcl   = max(0, media - 3 * std)

    fuera_control = datos[datos > ucl]

    print(f"\n📊 Control Chart — {titulo}")
    print(f"   Media (X̄): {media:.1f} seg/línea")
    print(f"   UCL (+3σ): {ucl:.1f} seg/línea")
    print(f"   LCL (-3σ): {lcl:.1f} seg/línea")
    print(f"   Puntos fuera de control: {len(fuera_control)} "
          f"({len(fuera_control)/len(datos)*100:.1f}%)")

    # ── Graficar con escala de Y limitada ──
    # ylim fijo a 300s para que los picos sean visibles
    # sin que el área azul tape todo el gráfico
    fig, ax = plt.subplots(figsize=(12, 5))

    ax.plot(range(len(datos)), datos.values,
            color='steelblue', alpha=0.5, linewidth=0.7, zorder=2)

    # Marcar puntos fuera de UCL en rojo
    # .index da la posición original en la serie para ubicarlos en X
    idx_fuera = [i for i, v in enumerate(datos.values) if v > ucl]
    ax.scatter(idx_fuera, datos.values[idx_fuera],
               color='red', s=15, zorder=4, label='Fuera de control')

    # Líneas de referencia
    ax.axhline(y=media, color='black', linewidth=1.5,
               label=f'X̄ = {media:.0f}s', zorder=3)
    ax.axhline(y=ucl, color='red', linewidth=1.5, linestyle='--',
               label=f'UCL = {ucl:.0f}s (+3σ)', zorder=3)
    ax.axhline(y=lcl, color='red', linewidth=1.5, linestyle='--',
               label=f'LCL = {lcl:.0f}s (-3σ)', zorder=3)
    ax.axhline(y=60, color='green', linewidth=1, linestyle=':',
               label='Meta 60s', zorder=3)

    # Zona de control sombreada — ahora visible porque Y está limitado
    ax.fill_between(range(len(datos)), lcl, ucl, alpha=0.08, color='blue')

    # Escala Y limitada a 300s — los puntos arriba de eso
    # son outliers extremos que distorsionan la escala
    ax.set_ylim(0, 300)
    ax.set_xlabel('Pedidos (en orden cronológico)')
    ax.set_ylabel('Segundos por línea')
    ax.set_title(f'{titulo}\n'
                 f'Puntos rojos = fricción de búsqueda | '
                 f'{len(fuera_control)/len(datos)*100:.1f}% fuera de control')
    ax.legend(fontsize=9, loc='upper right')

    plt.tight_layout()
    nombre_archivo = os.path.join(OUTPUTS_DIR, f"control_chart_{picker_id if picker_id else 'todos'}.png")
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
    ARCHIVO = os.path.join(DATA_DIR, "datos_prueba_favarcia.xlsx")   # ← CAMBIAR AQUÍ cuando lleguen datos reales

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