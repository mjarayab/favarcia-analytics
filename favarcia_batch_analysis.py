"""
=============================================================
FAVARCIA BATCH PICKING ANALYSIS
Proyecto: FPM - Favarcia Plan de Mejora

Mismo análisis que favarcia_picking_analysis.py pero los
puntos del control chart son BATCHES: grupos de pedidos
cuyo FIN ALISTO cae dentro de la misma ventana de 1 minuto.

Cada punto = mediana de seg/línea de todos los pedidos
que cerraron en ese minuto.

Autor: Mauricio Araya
=============================================================
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import os
import warnings
warnings.filterwarnings('ignore')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MODO = "real"   # "demo" → data/sample/   |   "real" → data/raw/

if MODO == "demo":
    DATA_DIR    = os.path.join(BASE_DIR, "data", "sample")
    OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs", "sample")
else:
    DATA_DIR    = os.path.join(BASE_DIR, "data", "raw")
    OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")

os.makedirs(OUTPUTS_DIR, exist_ok=True)
os.makedirs(DATA_DIR,    exist_ok=True)

print(f"📁 MODO: {MODO.upper()}")
print(f"   Datos:   {DATA_DIR}")
print(f"   Outputs: {OUTPUTS_DIR}")

plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("husl")


# ─────────────────────────────────────────────
# BLOQUE 1: CARGAR
# ─────────────────────────────────────────────

def cargar_datos(ruta_archivo):
    if ruta_archivo.endswith(('.xlsx', '.xls')):
        df = pd.read_excel(ruta_archivo)
        print(f"✅ Excel cargado: {len(df):,} filas")
    elif ruta_archivo.endswith('.csv'):
        try:
            df = pd.read_csv(ruta_archivo, encoding='utf-8')
        except:
            df = pd.read_csv(ruta_archivo, sep=';', encoding='latin-1')
        print(f"✅ CSV cargado: {len(df):,} filas")
    else:
        raise ValueError("Formato no reconocido. Usa .xlsx o .csv")
    return df


# ─────────────────────────────────────────────
# BLOQUE 2: PREPARAR
# ─────────────────────────────────────────────

def preparar_datos(df):
    """
    Idéntico al script original.
    Incluye pedidos con tiempo=0 — no se excluyen.
    Agrega columna batch_key: FIN ALISTO truncado al minuto.
    """
    print("\n" + "="*50)
    print("PREPARACIÓN DE DATOS")
    print("="*50)

    # Estandarizar nombres
    df.columns = (df.columns
        .str.lower()
        .str.strip()
        .str.replace(' ', '_')
        .str.replace('.', '_')
        .str.replace('(', '')
        .str.replace(')', '')
    )

    mapeo = {
        'alistador':              'picker_id',
        'tiempo_alisto_minutos':  'tiempo_minutos',
        'inicio_alisto':          'hora_inicio',
        'fecha_pedido':           'fecha',
    }
    df = df.rename(columns=mapeo)

    antes = len(df)
    df = df.dropna(subset=['picker_id'])
    print(f"✅ Filas sin alistador removidas: {antes - len(df)}")

    # seg/línea — incluyendo tiempo=0
    df['tiempo_segundos'] = df['tiempo_minutos'] * 60
    df['seg_por_linea'] = np.where(
        df['cant_lineas'] > 0,
        df['tiempo_segundos'] / df['cant_lineas'],
        np.nan
    )

    # Hora del día y día de semana
    if 'hora_inicio' in df.columns:
        df['hora'] = pd.to_datetime(df['hora_inicio'], errors='coerce').dt.hour

    if 'fecha' in df.columns:
        df['dia_semana'] = pd.to_datetime(df['fecha'], errors='coerce').dt.day_name()

    # ── BATCH KEY: FIN ALISTO truncado al minuto ──
    df['batch_key'] = pd.to_datetime(df['fin_alisto'], errors='coerce').dt.floor('min')

    total = len(df)
    con_tiempo = (df['tiempo_minutos'] > 0).sum()
    sin_tiempo = total - con_tiempo

    print(f"\n📊 Dataset completo:")
    print(f"   Total pedidos:          {total:,}")
    print(f"   Con tiempo registrado:  {con_tiempo:,} ({con_tiempo/total*100:.1f}%)")
    print(f"   Sin tiempo (tiempo=0):  {sin_tiempo:,} ({sin_tiempo/total*100:.1f}%)")
    print(f"   → El {sin_tiempo/total*100:.1f}% fue trabajado sin abrir el pedido en el WMS")

    return df


# ─────────────────────────────────────────────
# BLOQUE 3: CONSTRUIR BATCHES
# ─────────────────────────────────────────────

def construir_batches(df):
    """
    Agrupa pedidos por ventana de 1 minuto (FIN ALISTO truncado).
    Cada batch = mediana de seg/línea de los pedidos que cerraron
    en ese minuto.
    Batches con seg/línea NaN (todos tiempo=0 sin líneas) se omiten.
    """
    print("\n" + "="*50)
    print("CONSTRUCCIÓN DE BATCHES (ventana 1 min)")
    print("="*50)

    batches = (df.groupby('batch_key')['seg_por_linea']
        .agg(['median', 'count', 'mean'])
        .reset_index()
        .rename(columns={
            'median': 'mediana_seg',
            'count':  'n_pedidos',
            'mean':   'media_seg',
        })
        .dropna(subset=['mediana_seg'])
        .sort_values('batch_key')
        .reset_index(drop=True)
    )

    # Hora del día para análisis de fricción
    batches['hora'] = batches['batch_key'].dt.hour

    print(f"\n   Total batches (minutos con al menos 1 pedido): {len(batches):,}")
    print(f"\n   Pedidos por batch:")
    print(f"      Mínimo:  {batches['n_pedidos'].min()}")
    print(f"      Mediana: {batches['n_pedidos'].median():.1f}")
    print(f"      Máximo:  {batches['n_pedidos'].max()}")
    print(f"\n   Mediana seg/línea por batch:")
    print(f"      Mínimo:  {batches['mediana_seg'].min():.1f}s")
    print(f"      Mediana: {batches['mediana_seg'].median():.1f}s")
    print(f"      Media:   {batches['mediana_seg'].mean():.1f}s")
    print(f"      Máximo:  {batches['mediana_seg'].max():.1f}s")

    return batches


# ─────────────────────────────────────────────
# BLOQUE 4: DISTRIBUCIÓN DE BATCHES
# ─────────────────────────────────────────────

def analisis_distribucion(batches, df):
    """
    Distribución de la mediana de seg/línea por batch.
    Panel izquierdo: histograma de batches.
    Panel derecho: boxplot por alistador (del dataset original).
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle(
        'DISTRIBUCIÓN DE TIEMPO POR LÍNEA — ANÁLISIS POR BATCH\n'
        'Favarcia | Cada punto = mediana de pedidos cerrados en el mismo minuto',
        fontsize=12, fontweight='bold'
    )

    # Filtrar outliers extremos para legibilidad
    p99 = batches['mediana_seg'].quantile(0.99)
    b_plot = batches[batches['mediana_seg'] < p99]

    # Panel 1: histograma de medianas de batch
    sns.histplot(data=b_plot, x='mediana_seg', bins=50, kde=True,
                 ax=ax1, color='steelblue', alpha=0.7)
    ax1.axvline(x=60, color='green', linestyle='--', linewidth=1.5,
                label='Meta: 60 seg (1 min/línea)')
    ax1.axvline(x=b_plot['mediana_seg'].mean(), color='red',
                linestyle='-', linewidth=1.5,
                label=f"Promedio batches: {b_plot['mediana_seg'].mean():.0f}s")
    ax1.set_xlabel('Mediana seg/línea del batch')
    ax1.set_ylabel('Cantidad de batches')
    ax1.set_title('¿Hay dos poblaciones de batches?')
    ax1.legend(fontsize=9)

    # Panel 2: boxplot por alistador (top 10 por volumen)
    if 'picker_id' in df.columns and 'seg_por_linea' in df.columns:
        top_pickers = (df.groupby('picker_id').size().nlargest(10).index)
        df_top = df[df['picker_id'].isin(top_pickers)].copy()

        # Etiquetas: primer nombre + código
        mapeo_nombres = {}
        for picker in top_pickers:
            nombres = df[df['picker_id'] == picker]['nombre'].dropna()
            if len(nombres) > 0:
                palabras = str(nombres.iloc[0]).split()
                primer_nombre = palabras[2].capitalize() if len(palabras) >= 3 else palabras[0].capitalize()
                mapeo_nombres[picker] = f"{primer_nombre}\n({picker})"
            else:
                mapeo_nombres[picker] = picker

        df_top['etiqueta'] = df_top['picker_id'].map(mapeo_nombres).fillna(df_top['picker_id'])

        # Filtrar outliers para legibilidad
        p99_ind = df_top['seg_por_linea'].quantile(0.99)
        df_top_plot = df_top[df_top['seg_por_linea'] < p99_ind]

        sns.boxplot(data=df_top_plot, x='etiqueta', y='seg_por_linea',
                    ax=ax2, palette='husl')
        ax2.axhline(y=60, color='green', linestyle='--', linewidth=1.5,
                    label='Meta: 60 seg')
        ax2.set_xlabel('Alistador')
        ax2.set_ylabel('Seg/línea (pedido individual)')
        ax2.set_title('Variabilidad por alistador\n(colas similares = problema sistémico)')
        ax2.tick_params(axis='x', rotation=0)
        ax2.legend(fontsize=9)

    plt.tight_layout()
    ruta = os.path.join(OUTPUTS_DIR, 'batch_distribucion.png')
    plt.savefig(ruta, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"\n✅ Gráfica guardada: batch_distribucion.png")


# ─────────────────────────────────────────────
# BLOQUE 5: FRICCIÓN POR HORA
# ─────────────────────────────────────────────

def analisis_friccion_hora(batches):
    """
    Mediana de seg/línea por hora del día, calculada sobre los batches.
    Patrón esperado: picos en tarde = cajones vaciándose post-rush.
    """
    print("\n" + "="*50)
    print("FRICCIÓN POR HORA DEL DÍA (batches)")
    print("="*50)

    por_hora = (batches.groupby('hora')['mediana_seg']
        .agg(['mean', 'median', 'count'])
        .round(1)
        .rename(columns={'mean': 'promedio_seg', 'median': 'mediana_seg', 'count': 'batches'})
    )
    print(por_hora)

    hora_pico = por_hora['mediana_seg'].idxmax()
    hora_baja = por_hora['mediana_seg'].idxmin()
    delta_pct = (
        (por_hora.loc[hora_pico, 'mediana_seg'] - por_hora.loc[hora_baja, 'mediana_seg'])
        / por_hora.loc[hora_baja, 'mediana_seg'] * 100
    )
    print(f"\n   Hora con más fricción:  {hora_pico}:00h ({por_hora.loc[hora_pico,'mediana_seg']:.0f}s/línea)")
    print(f"   Hora con menos fricción: {hora_baja}:00h ({por_hora.loc[hora_baja,'mediana_seg']:.0f}s/línea)")
    print(f"   Delta: +{delta_pct:.0f}% más fricción en hora pico")

    if hora_pico >= 14:
        print(f"   → Pico en tarde confirma hipótesis cajones vacíos post-rush ✅")

    fig, ax = plt.subplots(figsize=(10, 4))
    colores = ['tomato' if h == hora_pico else 'steelblue' for h in por_hora.index]
    ax.bar(por_hora.index, por_hora['mediana_seg'], color=colores, alpha=0.8)
    ax.axhline(y=60, color='green', linestyle='--', label='Meta 60s')
    ax.annotate(
        f'Pico\n{por_hora.loc[hora_pico,"mediana_seg"]:.0f}s',
        xy=(hora_pico, por_hora.loc[hora_pico, 'mediana_seg']),
        xytext=(hora_pico + 0.3, por_hora.loc[hora_pico, 'mediana_seg'] + 3),
        fontsize=9, color='tomato', fontweight='bold'
    )
    ax.set_xlabel('Hora del día')
    ax.set_ylabel('Mediana seg/línea (sobre batches)')
    ax.set_title(
        '¿A qué hora del día hay más fricción? — Análisis por Batch\n'
        '(rojo = hora pico | picos en tarde = cajones vacíos post-rush)'
    )
    ax.legend()
    plt.tight_layout()
    ruta = os.path.join(OUTPUTS_DIR, 'batch_friccion_por_hora.png')
    plt.savefig(ruta, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"✅ Gráfica guardada: batch_friccion_por_hora.png")


# ─────────────────────────────────────────────
# BLOQUE 6: CONTROL CHART
# ─────────────────────────────────────────────

def control_chart(batches):
    """
    Control chart donde cada punto es un batch (1 minuto).
    Límites UCL/LCL por fence de Tukey — igual que el script original.
    Panel superior: serie temporal de medianas de batch.
    Panel inferior: % batches con fricción alta por período.
    """
    datos = batches['mediana_seg'].copy()

    # Filtrar outliers extremos (pedidos olvidados sin cerrar)
    p99 = datos.quantile(0.99)
    mask = datos <= p99
    datos_cc = datos[mask].reset_index(drop=True)
    timestamps_cc = batches.loc[mask, 'batch_key'].reset_index(drop=True)
    n_pedidos_cc  = batches.loc[mask, 'n_pedidos'].reset_index(drop=True)

    # Límites Tukey
    mediana = datos_cc.median()
    p25     = datos_cc.quantile(0.25)
    p75     = datos_cc.quantile(0.75)
    iqr     = p75 - p25
    ucl     = p75 + 1.5 * iqr
    lcl     = max(0, p25 - 1.5 * iqr)

    fuera_control = datos_cc[datos_cc > ucl]
    pct_fuera     = len(fuera_control) / len(datos_cc) * 100

    print(f"\n{'='*50}")
    print(f"CONTROL CHART — BATCHES (ventana 1 min)")
    print(f"{'='*50}")
    print(f"   Total batches en chart: {len(datos_cc):,}")
    print(f"   Mediana:  {mediana:.1f} seg/línea")
    print(f"   P25: {p25:.1f}s | P75: {p75:.1f}s | IQR: {iqr:.1f}s")
    print(f"   UCL (P75 + 1.5×IQR): {ucl:.1f}s")
    print(f"   LCL (P25 - 1.5×IQR): {lcl:.1f}s")
    print(f"   Batches fuera de control: {len(fuera_control):,} ({pct_fuera:.1f}%)")

    # Medianas móviles (ventana 50 batches)
    ventana = 50
    medianas_moviles = datos_cc.rolling(window=ventana, center=True).median()

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 8),
                                    gridspec_kw={'height_ratios': [3, 1]})
    fig.suptitle(
        'Control Chart — Análisis por Batch (ventana 1 min)\n'
        'Cada punto = mediana seg/línea de pedidos cerrados en el mismo minuto',
        fontsize=12, fontweight='bold'
    )

    # Panel superior
    x = range(len(datos_cc))
    colores_pts = ['tomato' if v > ucl else 'steelblue' for v in datos_cc.values]

    # Tamaño proporcional al n de pedidos del batch
    sizes = np.clip(n_pedidos_cc.values * 3, 4, 40)

    ax1.scatter(x, datos_cc.values, c=colores_pts, s=sizes, alpha=0.4, zorder=2)
    ax1.plot(x, medianas_moviles.values, color='black', linewidth=1.5, zorder=3,
             label=f'Mediana móvil ({ventana} batches)')
    ax1.axhline(y=mediana, color='blue',  linewidth=1,   linestyle='-',
                label=f'Mediana = {mediana:.0f}s', alpha=0.7)
    ax1.axhline(y=ucl,     color='red',   linewidth=1.5, linestyle='--',
                label=f'UCL = {ucl:.0f}s')
    ax1.axhline(y=60,      color='green', linewidth=1,   linestyle=':',
                label='Meta 60s')
    ax1.axhspan(lcl, ucl, alpha=0.05, color='green')
    ax1.set_ylim(0, datos_cc.quantile(0.97) * 1.2)
    ax1.set_ylabel('Mediana seg/línea del batch')
    ax1.set_title(
        f'Rojo = batch con fricción alta (>{ucl:.0f}s) | '
        f'{pct_fuera:.1f}% fuera de control | '
        f'Tamaño del punto ∝ pedidos en el batch',
        fontsize=10
    )
    ax1.legend(fontsize=8, loc='upper right')

    # Etiquetas en eje X: fechas cada ~500 batches
    paso = max(1, len(datos_cc) // 10)
    ticks_idx = list(range(0, len(datos_cc), paso))
    ticks_lbl = [timestamps_cc.iloc[i].strftime('%d-%b') for i in ticks_idx]
    ax1.set_xticks(ticks_idx)
    ax1.set_xticklabels(ticks_lbl, rotation=45, fontsize=8)

    # Panel inferior: % batches con fricción por período
    n_bloques = 30
    tam_bloque = max(1, len(datos_cc) // n_bloques)
    pct_friccion_bloque = []
    x_bloques = []

    for i in range(n_bloques):
        inicio = i * tam_bloque
        fin    = min(inicio + tam_bloque, len(datos_cc))
        bloque = datos_cc.iloc[inicio:fin]
        pct    = (bloque > ucl).mean() * 100
        pct_friccion_bloque.append(pct)
        x_bloques.append((inicio + fin) / 2)

    colores_bloques = [
        'tomato' if p > pct_fuera * 1.5 else 'steelblue'
        for p in pct_friccion_bloque
    ]
    ax2.bar(x_bloques, pct_friccion_bloque, width=tam_bloque * 0.8,
            color=colores_bloques, alpha=0.7)
    ax2.axhline(y=pct_fuera, color='red', linewidth=1, linestyle='--',
                label=f'Promedio: {pct_fuera:.1f}%')
    ax2.set_ylabel('% batches con fricción')
    ax2.set_xlabel('Batches (orden cronológico)')
    ax2.set_title('% batches con alta fricción por período', fontsize=10)
    ax2.legend(fontsize=8)

    plt.tight_layout()
    ruta = os.path.join(OUTPUTS_DIR, 'batch_control_chart.png')
    plt.savefig(ruta, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"✅ Gráfica guardada: batch_control_chart.png")

    return {'mediana': mediana, 'ucl': ucl, 'lcl': lcl, 'pct_fuera': pct_fuera}


# ─────────────────────────────────────────────
# BLOQUE 7: ANÁLISIS Cpk
# ─────────────────────────────────────────────

def analisis_cpk(batches):
    """
    Cpk calculado sobre las medianas de batch (no pedidos individuales).
    USL = 120s (2× meta) | LSL = 0 | Target = 60s
    """
    print(f"\n{'='*50}")
    print(f"📐 ANÁLISIS DE CAPACIDAD — Cpk (sobre batches)")
    print(f"{'='*50}")

    USL  = 120
    LSL  = 0
    META = 60

    datos = batches['mediana_seg'].dropna()
    datos = datos[datos < 600]   # excluir outliers extremos

    media = datos.mean()
    std   = datos.std()

    cp  = (USL - LSL) / (6 * std)
    cpu = (USL - media) / (3 * std)
    cpl = (media - LSL) / (3 * std)
    cpk = min(cpu, cpl)

    pct_fuera_teorico = (1 - stats.norm.cdf(USL, media, std)) * 100

    print(f"\n   Especificaciones:")
    print(f"      USL (límite superior): {USL}s/línea")
    print(f"      LSL (límite inferior): {LSL}s/línea")
    print(f"      Target:                {META}s/línea")
    print(f"\n   Estadísticas del proceso (sobre batches):")
    print(f"      Media (X̄):   {media:.1f}s")
    print(f"      Desv. Est.:  {std:.1f}s")
    print(f"\n   Índices de capacidad:")
    print(f"      Cp  = {cp:.2f}")
    print(f"      Cpu = {cpu:.2f}")
    print(f"      Cpl = {cpl:.2f}")
    print(f"      Cpk = {cpk:.2f} ← índice real")
    print(f"\n   % teórico fuera de USL: {pct_fuera_teorico:.1f}%")

    if   cpk >= 2.0:  nivel = "EXCELENTE — estándar FDA para dispositivos críticos"
    elif cpk >= 1.67: nivel = "BUENO — estándar medtech"
    elif cpk >= 1.33: nivel = "ACEPTABLE — mínimo manufactura general"
    elif cpk >= 1.0:  nivel = "MARGINAL — proceso apenas capaz, requiere mejora"
    else:             nivel = "INCAPAZ — el proceso produce defectos sistemáticamente"

    print(f"\n📝 Interpretación:")
    print(f"   Cpk = {cpk:.2f} → {nivel}")

    if cpk < 1.33:
        reduccion_std = std - (USL - META) / (3 * 1.33)
        print(f"\n   Para alcanzar Cpk = 1.33:")
        if media > META:
            print(f"   → Reducir media de {media:.0f}s a {META}s (−{media-META:.0f}s/línea)")
        print(f"   → Reducir σ de {std:.0f}s a {max(0,reduccion_std):.0f}s")
        print(f"   → Equivale a eliminar fricción sistémica (cajones vacíos, WMS incorrecto)")

    # Gráfica
    fig, ax = plt.subplots(figsize=(10, 5))
    x_range = np.linspace(0, 400, 500)

    ax.hist(datos, bins=60, density=True, color='steelblue', alpha=0.5,
            label='Distribución batches')
    ax.plot(x_range, stats.norm.pdf(x_range, media, std),
            color='steelblue', linewidth=2, label='Curva normal ajustada')

    ax.axvline(x=USL,   color='red',   linewidth=2,   linestyle='--', label=f'USL = {USL}s')
    ax.axvline(x=META,  color='green', linewidth=1.5, linestyle=':',  label=f'Target = {META}s')
    ax.axvline(x=media, color='black', linewidth=1.5,                 label=f'X̄ = {media:.0f}s')

    x_fuera = x_range[x_range > USL]
    ax.fill_between(x_fuera, stats.norm.pdf(x_fuera, media, std),
                    alpha=0.3, color='red', label=f'Fuera USL ({pct_fuera_teorico:.1f}%)')

    ax.set_xlim(0, 400)
    ax.set_xlabel('Mediana seg/línea del batch')
    ax.set_ylabel('Densidad')
    ax.set_title(
        f'Análisis de Capacidad — Batches Favarcia\n'
        f'Cp = {cp:.2f} | Cpk = {cpk:.2f} | {nivel.split("—")[0].strip()}'
    )
    ax.legend(fontsize=9)
    plt.tight_layout()
    ruta = os.path.join(OUTPUTS_DIR, 'batch_cpk_analysis.png')
    plt.savefig(ruta, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"✅ Gráfica guardada: batch_cpk_analysis.png")

    return {'cp': cp, 'cpk': cpk, 'media': media, 'std': std}


# ─────────────────────────────────────────────
# PUNTO DE ENTRADA
# ─────────────────────────────────────────────

if __name__ == "__main__":

    ARCHIVO = os.path.join(DATA_DIR, "FPM_Datos.xlsx")   # ← cambiar si es necesario

    print("\n🚀 INICIANDO ANÁLISIS FAVARCIA — BATCH MODE")
    print("="*50)

    df      = cargar_datos(ARCHIVO)
    df      = preparar_datos(df)
    batches = construir_batches(df)

    analisis_distribucion(df=df, batches=batches)
    analisis_friccion_hora(batches)
    control_chart(batches)
    analisis_cpk(batches)

    print("\n✅ ANÁLISIS COMPLETO")
    print("Archivos generados en /outputs:")
    print("   - batch_distribucion.png")
    print("   - batch_friccion_por_hora.png")
    print("   - batch_control_chart.png")
    print("   - batch_cpk_analysis.png")