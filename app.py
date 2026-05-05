"""
=============================================================
FAVARCIA — APP DE ANÁLISIS DE OPERACIONES
=============================================================
Dashboard interactivo construido con Streamlit.
Corre con: streamlit run app.py
=============================================================
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from scipy import stats
import os

# ── Configuración de la página ────────────────────────────
st.set_page_config(
    page_title="Favarcia — Análisis de Operaciones",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Rutas ─────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data", "raw")

# ── Cargar datos con cache ────────────────────────────────
# @st.cache_data guarda los datos en memoria
# No los recarga cada vez que el usuario interactúa con la app
@st.cache_data
def cargar_datos():
    archivo = os.path.join(DATA_DIR, "FPM_Datos.xlsx")
    df = pd.read_excel(archivo)
    df.columns = (df.columns.str.lower().str.strip()
                  .str.replace(' ', '_')
                  .str.replace('(', '').str.replace(')', ''))
    df = df.rename(columns={
        'alistador':             'picker_id',
        'tiempo_alisto_minutos': 'tiempo_minutos',
        'inicio_alisto':         'hora_inicio',
        'fecha_pedido':          'fecha',
    })
    df = df.dropna(subset=['picker_id'])

    # Mapeo de nombres
    mapeo = {}
    for picker in df['picker_id'].unique():
        nombres = df[df['picker_id'] == picker]['nombre'].dropna()
        if len(nombres) > 0:
            palabras = str(nombres.iloc[0]).split()
            if len(palabras) >= 3:
                mapeo[picker] = f"{palabras[2].capitalize()} ({picker})"
            else:
                mapeo[picker] = picker
    df['etiqueta'] = df['picker_id'].map(mapeo).fillna(df['picker_id'])

    # Datasets
    df_vol    = df.copy()
    df_tiempo = df[df['tiempo_minutos'] > 0].copy()
    df_tiempo['seg_por_linea'] = df_tiempo['tiempo_minutos'] * 60 / df_tiempo['cant_lineas']
    df_tiempo['hora'] = pd.to_datetime(df_tiempo['hora_inicio'], errors='coerce').dt.hour
    df_tiempo['fecha_dt'] = pd.to_datetime(df_tiempo['fecha'], errors='coerce')

    return df_vol, df_tiempo, mapeo

# ── Cargar ────────────────────────────────────────────────
try:
    df_vol, df_tiempo, mapeo = cargar_datos()
    datos_ok = True
except Exception as e:
    st.error(f"Error cargando datos: {e}")
    datos_ok = False

# ── Sidebar ───────────────────────────────────────────────
st.sidebar.image("https://via.placeholder.com/200x60?text=FAVARCIA", width=200)
st.sidebar.title("Navegación")

pagina = st.sidebar.radio(
    "Selecciona una sección:",
    ["📊 Resumen Operación",
     "👥 Dashboard Alistadores",
     "🔍 Perfil Individual",
     "🏆 Ranking"]
)

st.sidebar.markdown("---")
st.sidebar.markdown("**FPM — Favarcia Plan de Mejora**")

if not datos_ok:
    st.stop()

# ── Filtro de fechas en sidebar ───────────────────────────
st.sidebar.markdown("---")
st.sidebar.subheader("Filtro de período")

fecha_min = pd.to_datetime(df_vol['fecha_factura'], errors='coerce').min().date()
fecha_max = pd.to_datetime(df_vol['fecha_factura'], errors='coerce').max().date()

fecha_inicio, fecha_fin = st.sidebar.date_input(
    "Selecciona período:",
    value=(fecha_min, fecha_max),
    min_value=fecha_min,
    max_value=fecha_max,
    format="DD/MM/YYYY"
)

# Aplicar filtro a ambos datasets
mask = (
    (pd.to_datetime(df_vol['fecha_factura'], errors='coerce').dt.date >= fecha_inicio) &
    (pd.to_datetime(df_vol['fecha_factura'], errors='coerce').dt.date <= fecha_fin)
)
df_vol    = df_vol[mask].copy()
df_tiempo = df_tiempo[mask].copy()

st.sidebar.caption(f"Pedidos en período: {len(df_vol):,}")

# ══════════════════════════════════════════════════════════
# PÁGINA 1 — RESUMEN DE LA OPERACIÓN
# ══════════════════════════════════════════════════════════
if pagina == "📊 Resumen Operación":
    st.title("📊 Resumen de la Operación")
    st.markdown("Análisis estadístico del proceso de picking — datos reales de operación")

    # ── KPIs ──
    total_pedidos  = len(df_vol)
    con_tiempo     = len(df_tiempo)
    pct_invisible  = (total_pedidos - con_tiempo) / total_pedidos * 100
    mediana_seg    = df_tiempo['seg_por_linea'].median()
    pct_friccion   = (df_tiempo['seg_por_linea'] > 120).mean() * 100

    # Cpk
    USL    = 120
    media  = df_tiempo['seg_por_linea'].mean()
    sigma  = df_tiempo['seg_por_linea'].std()
    cpk    = (USL - media) / (3 * sigma)

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Pedidos", f"{total_pedidos:,}")
    col2.metric("Trabajo Invisible", f"{pct_invisible:.1f}%",
                help="Pedidos trabajados sin abrir en el WMS")
    col3.metric("Mediana seg/línea", f"{mediana_seg:.0f}s",
                delta=f"{mediana_seg-60:.0f}s vs meta",
                delta_color="inverse")
    col4.metric("Alta Fricción", f"{pct_friccion:.1f}%",
                help="Pedidos con más de 120s/línea")
    col5.metric("Cpk", f"{cpk:.2f}",
                delta="Incapaz" if cpk < 1.0 else "Capaz",
                delta_color="inverse" if cpk < 1.0 else "normal")

    st.markdown("---")

    col_a, col_b = st.columns(2)

    # Distribución de tiempos
    with col_a:
        st.subheader("Distribución de Tiempo por Línea")
        datos_plot = df_tiempo[df_tiempo['seg_por_linea'] < 600]['seg_por_linea']
        fig = px.histogram(datos_plot, nbins=60,
                          labels={'value': 'Segundos por línea',
                                  'count': 'Cantidad de pedidos'},
                          color_discrete_sequence=['steelblue'])
        fig.add_vline(x=60, line_dash="dash", line_color="green",
                     annotation_text="Meta 60s")
        fig.add_vline(x=mediana_seg, line_dash="solid", line_color="black",
                     annotation_text=f"Mediana {mediana_seg:.0f}s")
        fig.update_layout(showlegend=False, height=350)
        st.plotly_chart(fig, use_container_width=True)

    # Fricción por hora
    with col_b:
        st.subheader("Fricción por Hora del Día")
        por_hora = (df_tiempo.groupby('hora')['seg_por_linea']
                    .median().reset_index())
        por_hora.columns = ['hora', 'mediana_seg']
        hora_pico = por_hora.loc[por_hora['mediana_seg'].idxmax(), 'hora']
        por_hora['color'] = por_hora['hora'].apply(
            lambda h: 'tomato' if h == hora_pico else 'steelblue')
        fig2 = px.bar(por_hora, x='hora', y='mediana_seg',
                     color='color',
                     color_discrete_map={'tomato': 'tomato', 'steelblue': 'steelblue'},
                     labels={'hora': 'Hora del día', 'mediana_seg': 'Mediana seg/línea'})
        fig2.add_hline(y=60, line_dash="dash", line_color="green",
                      annotation_text="Meta 60s")
        fig2.update_layout(showlegend=False, height=350)
        st.plotly_chart(fig2, use_container_width=True)

    # Análisis de capacidad
    st.markdown("---")
    st.subheader("Análisis de Capacidad — Cpk")

    col_c, col_d = st.columns([2, 1])
    with col_c:
        x_range = np.linspace(0, 400, 500)
        curva = stats.norm.pdf(x_range, media, sigma)
        fig3 = go.Figure()
        fig3.add_trace(go.Histogram(x=df_tiempo[df_tiempo['seg_por_linea']<400]['seg_por_linea'],
                                    nbinsx=60, name='Distribución real',
                                    histnorm='probability density',
                                    marker_color='steelblue', opacity=0.6))
        fig3.add_trace(go.Scatter(x=x_range, y=curva, name='Curva normal',
                                  line=dict(color='steelblue', width=2)))
        fig3.add_vline(x=USL, line_dash="dash", line_color="red",
                      annotation_text=f"USL={USL}s")
        fig3.add_vline(x=60, line_dash="dot", line_color="green",
                      annotation_text="Target 60s")
        fig3.add_vline(x=media, line_color="black",
                      annotation_text=f"Media {media:.0f}s")
        # Área fuera de USL
        x_fuera = x_range[x_range > USL]
        fig3.add_trace(go.Scatter(
            x=np.concatenate([[USL], x_fuera, [x_fuera[-1]]]),
            y=np.concatenate([[0], stats.norm.pdf(x_fuera, media, sigma), [0]]),
            fill='toself', fillcolor='rgba(255,0,0,0.2)',
            line=dict(color='rgba(255,0,0,0)'),
            name=f'Fuera USL'
        ))
        fig3.update_layout(height=350, xaxis_title='Segundos por línea',
                          yaxis_title='Densidad')
        st.plotly_chart(fig3, use_container_width=True)

    with col_d:
        pct_fuera = (1 - stats.norm.cdf(USL, media, sigma)) * 100
        st.metric("Cp", f"{(USL/6/sigma):.2f}")
        st.metric("Cpk", f"{cpk:.2f}")
        st.metric("Media", f"{media:.1f}s")
        st.metric("σ", f"{sigma:.1f}s")
        st.metric("% fuera de USL", f"{pct_fuera:.1f}%")
        if cpk < 1.0:
            st.error("Proceso INCAPAZ")
        elif cpk < 1.33:
            st.warning("Proceso MARGINAL")
        else:
            st.success("Proceso CAPAZ")

# ══════════════════════════════════════════════════════════
# PÁGINA 2 — DASHBOARD ALISTADORES
# ══════════════════════════════════════════════════════════
elif pagina == "👥 Dashboard Alistadores":
    st.title("👥 Dashboard de Alistadores")

    ROLES_APOYO = ['EM039', 'EM560', 'EM289']

    # Métricas por alistador
    vol = (df_vol.groupby(['picker_id', 'etiqueta'])
           .agg(total_pedidos   = ('picker_id', 'count'),
                total_lineas    = ('cant_lineas', 'sum'))
           .reset_index())

    tiempo_m = (df_tiempo.groupby('picker_id')
                .agg(mediana_seg  = ('seg_por_linea', 'median'),
                     promedio_seg = ('seg_por_linea', 'mean'),
                     pedidos_t    = ('picker_id', 'count'))
                .reset_index())

    # Promedio incluyendo tiempo=0 — como lo calcula el sistema actual
    promedio_total = (df_vol.groupby('picker_id')
                     .agg(promedio_seg_total = ('tiempo_minutos',
                          lambda x: (x * 60 / df_vol.loc[x.index, 'cant_lineas']).mean()))
                     .reset_index())

    resumen = vol.merge(tiempo_m, on='picker_id', how='left')
    resumen = resumen.merge(promedio_total, on='picker_id', how='left')
    resumen['es_apoyo'] = resumen['picker_id'].isin(ROLES_APOYO)
    resumen = resumen[resumen['total_pedidos'] >= 50]

    tab1, tab2, tab3, tab4 = st.tabs([
        "Volumen de pedidos",
        "Tiempo por linea",
        "Volumen vs Tiempo",
        "Tamaño de pedidos"
    ])

    with tab1:
        st.subheader("Total Pedidos por Alistador")
        col1, col2 = st.columns(2)

        orden = resumen.sort_values('total_pedidos', ascending=True)

        with col1:
            st.markdown("**Pedidos con tiempo registrado en WMS**")
            fig = px.bar(orden, x='pedidos_t', y='etiqueta', orientation='h',
                        color='es_apoyo',
                        color_discrete_map={True: 'lightcoral', False: 'steelblue'},
                        labels={'pedidos_t': 'Pedidos con tiempo', 'etiqueta': ''})
            fig.update_layout(showlegend=False, height=max(400, len(orden)*22))
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("**Total pedidos reales (incluyendo tiempo=0)**")
            fig2 = px.bar(orden, x='total_pedidos', y='etiqueta', orientation='h',
                         color='es_apoyo',
                         color_discrete_map={True: 'lightcoral', False: 'steelblue'},
                         labels={'total_pedidos': 'Total pedidos', 'etiqueta': ''})
            fig2.update_layout(showlegend=False, height=max(400, len(orden)*22))
            st.plotly_chart(fig2, use_container_width=True)

    with tab2:
        st.subheader("Tiempo por Línea por Alistador")
        res_t = resumen[resumen['mediana_seg'].notna()].copy()

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Promedio seg/línea** (incluye todos los pedidos)")
            orden_p = res_t.sort_values('promedio_seg_total', ascending=True)
            # Detectar outlier extremo y limitar escala
            escala_max = orden_p['promedio_seg_total'].quantile(0.95) * 1.2
            outlier = orden_p.loc[orden_p['promedio_seg_total'].idxmax()]
            fig = px.bar(orden_p, x='promedio_seg_total', y='etiqueta',
                        orientation='h',
                        labels={'promedio_seg_total': 'Promedio seg/línea', 'etiqueta': ''})
            fig.add_vline(x=60, line_dash="dash", line_color="green",
                         annotation_text="Meta 60s")
            fig.add_vline(x=120, line_dash="dash", line_color="red",
                         annotation_text="Umbral 120s")
            if outlier['promedio_seg_total'] > escala_max:
                fig.update_xaxes(range=[0, escala_max])
                st.caption(f"⚠️ {outlier['etiqueta']}: {outlier['promedio_seg_total']:.0f}s — fuera de escala (pedido olvidado sin cerrar)")
            fig.update_layout(showlegend=False, height=max(400, len(orden_p)*22))
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("**Mediana seg/línea** (robusta a outliers)")
            orden_m = res_t.sort_values('mediana_seg', ascending=True)
            fig2 = px.bar(orden_m, x='mediana_seg', y='etiqueta', orientation='h',
                         labels={'mediana_seg': 'Mediana seg/línea', 'etiqueta': ''})
            fig2.add_vline(x=60, line_dash="dash", line_color="green",
                          annotation_text="Meta 60s")
            fig2.add_vline(x=120, line_dash="dash", line_color="red",
                          annotation_text="Umbral 120s")
            fig2.update_layout(showlegend=False, height=max(400, len(orden_m)*22))
            st.plotly_chart(fig2, use_container_width=True)

    with tab3:
        st.subheader("Volumen vs Tiempo — Ideal: esquina inferior derecha")
        res_s = resumen[resumen['mediana_seg'].notna()].copy()
        fig = px.scatter(res_s, x='total_pedidos', y='mediana_seg',
                        text='etiqueta', color='es_apoyo',
                        color_discrete_map={True: 'lightcoral', False: 'steelblue'},
                        labels={'total_pedidos': 'Total pedidos (volumen real)',
                                'mediana_seg': 'Mediana seg/línea'})
        fig.add_hline(y=60, line_dash="dash", line_color="green",
                     annotation_text="Meta 60s")
        fig.add_hline(y=120, line_dash="dash", line_color="red",
                     annotation_text="Umbral fricción")
        fig.update_traces(textposition='top center', textfont_size=9)
        fig.update_layout(showlegend=False, height=550)
        st.plotly_chart(fig, use_container_width=True)

    with tab4:
        st.subheader("Distribución de Tamaño de Pedidos por Alistador")
        st.markdown("Cajas bajas y compactas = pedidos pequeños | Cajas altas y dispersas = pedidos grandes")

        top15_vol = (resumen.nlargest(15, 'total_pedidos')['picker_id'].tolist())
        df_box_tam = df_vol[df_vol['picker_id'].isin(top15_vol)].copy()
        df_box_tam['etiqueta'] = df_box_tam['picker_id'].map(mapeo).fillna(df_box_tam['picker_id'])
        df_box_tam['es_apoyo'] = df_box_tam['picker_id'].isin(ROLES_APOYO)

        p95 = df_box_tam['cant_lineas'].quantile(0.95)
        df_box_tam = df_box_tam[df_box_tam['cant_lineas'] <= p95]
        mediana_global = df_vol['cant_lineas'].median()

        fig_box = px.box(df_box_tam, x='etiqueta', y='cant_lineas',
                        color='es_apoyo',
                        color_discrete_map={True: 'lightcoral', False: 'steelblue'},
                        labels={'etiqueta': 'Alistador',
                                'cant_lineas': 'Lineas por pedido'})
        fig_box.add_hline(y=mediana_global, line_dash="dash", line_color="green",
                         annotation_text=f"Mediana global: {mediana_global:.0f}")
        fig_box.update_layout(showlegend=False, height=500, xaxis_tickangle=45)
        st.plotly_chart(fig_box, use_container_width=True)
        st.caption("Coral = rol de apoyo | Azul = alistador permanente")
# ══════════════════════════════════════════════════════════
# PÁGINA 3 — PERFIL INDIVIDUAL
# ══════════════════════════════════════════════════════════
elif pagina == "🔍 Perfil Individual":
    st.title("🔍 Perfil Individual de Alistador")

    # Selector
    pickers_disponibles = sorted(df_vol['picker_id'].unique())
    etiquetas_disponibles = [mapeo.get(p, p) for p in pickers_disponibles]
    seleccion = st.selectbox("Selecciona un alistador:", etiquetas_disponibles)
    picker_sel = pickers_disponibles[etiquetas_disponibles.index(seleccion)]

    # Datos del picker
    picker_vol    = df_vol[df_vol['picker_id'] == picker_sel]
    picker_tiempo = df_tiempo[df_tiempo['picker_id'] == picker_sel]

    st.markdown("---")

    # KPIs
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total pedidos", f"{len(picker_vol):,}")
    col2.metric("Con tiempo registrado",
                f"{len(picker_tiempo):,}",
                f"{len(picker_tiempo)/len(picker_vol)*100:.1f}%")
    col3.metric("Líneas totales", f"{picker_vol['cant_lineas'].sum():,}")

    if len(picker_tiempo) > 0:
        mediana_p = picker_tiempo['seg_por_linea'].median()
        col4.metric("Mediana seg/línea", f"{mediana_p:.0f}s",
                   delta=f"{mediana_p-60:.0f}s vs meta",
                   delta_color="inverse")

    st.markdown("---")

    if len(picker_tiempo) > 0:
        col_a, col_b = st.columns(2)

        with col_a:
            st.subheader("Distribución de tiempos")
            datos_p = picker_tiempo[picker_tiempo['seg_por_linea'] < 600]['seg_por_linea']
            fig = px.histogram(datos_p, nbins=40,
                              labels={'value': 'Segundos por línea'},
                              color_discrete_sequence=['steelblue'])
            fig.add_vline(x=60, line_dash="dash", line_color="green",
                         annotation_text="Meta 60s")
            fig.add_vline(x=mediana_p, line_dash="solid", line_color="black",
                         annotation_text=f"Mediana {mediana_p:.0f}s")
            fig.update_layout(showlegend=False, height=300)
            st.plotly_chart(fig, use_container_width=True)

        with col_b:
            st.subheader("Fricción por hora del día")
            por_hora_p = (picker_tiempo.groupby('hora')['seg_por_linea']
                         .agg(['median', 'count']).reset_index())
            por_hora_p.columns = ['hora', 'mediana_seg', 'pedidos']
            fig2 = px.bar(por_hora_p, x='hora', y='mediana_seg',
                         labels={'hora': 'Hora', 'mediana_seg': 'Mediana seg/línea'},
                         color_discrete_sequence=['steelblue'])
            fig2.add_hline(y=60, line_dash="dash", line_color="green")
            fig2.update_layout(height=300)
            st.plotly_chart(fig2, use_container_width=True)

        # Estadísticas detalladas
        st.subheader("Estadísticas detalladas")
        col_e, col_f, col_g = st.columns(3)
        col_e.metric("P25", f"{picker_tiempo['seg_por_linea'].quantile(0.25):.1f}s")
        col_f.metric("P75", f"{picker_tiempo['seg_por_linea'].quantile(0.75):.1f}s")
        col_g.metric("P90", f"{picker_tiempo['seg_por_linea'].quantile(0.90):.1f}s")

        umbral = 120
        friccion = (picker_tiempo['seg_por_linea'] > umbral).mean() * 100
        friccion_op = (df_tiempo['seg_por_linea'] > umbral).mean() * 100
        diff = friccion - friccion_op

        st.markdown(f"**Fricción alta (>{umbral}s):** {friccion:.1f}% "
                   f"({'▲' if diff > 0 else '▼'} {abs(diff):.1f}pts vs operación {friccion_op:.1f}%)")

        # Top pedidos con fricción
        st.subheader("Top 10 pedidos con mayor fricción")
        top_f = (picker_tiempo[picker_tiempo['seg_por_linea'] > umbral]
                 .sort_values('seg_por_linea', ascending=False)
                 [['hora_inicio', 'cant_lineas', 'tiempo_minutos', 'seg_por_linea']]
                 .head(10))
        if len(top_f) > 0:
            st.dataframe(top_f.round(1), use_container_width=True)
        else:
            st.success("Sin pedidos con alta fricción")

    st.markdown("---")

    # ── Tamaño de pedidos ─────────────────────────────────
    st.subheader("Tamaño de pedidos — ¿Pedidos grandes o pequeños?")

    mediana_global = df_vol['cant_lineas'].median()
    mediana_picker = picker_vol['cant_lineas'].median()
    promedio_picker = picker_vol['cant_lineas'].mean()
    diff_med = mediana_picker - mediana_global

    col1, col2, col3 = st.columns(3)
    col1.metric("Mediana líneas/pedido", f"{mediana_picker:.0f}",
                delta=f"{diff_med:+.0f} vs operación ({mediana_global:.0f})",
                delta_color="normal")
    col2.metric("Promedio líneas/pedido", f"{promedio_picker:.1f}")
    col3.metric("Pedido más grande", f"{picker_vol['cant_lineas'].max():.0f} líneas")

    if diff_med < -mediana_global * 0.3:
        st.warning(f"Patrón: pedidos PEQUEÑOS — mediana {mediana_picker:.0f} líneas vs operación {mediana_global:.0f}")
    elif diff_med > mediana_global * 0.3:
        st.info(f"Patrón: pedidos GRANDES — mediana {mediana_picker:.0f} líneas vs operación {mediana_global:.0f}")
    else:
        st.success(f"Patrón: pedidos TÍPICOS — mediana {mediana_picker:.0f} líneas vs operación {mediana_global:.0f}")

    col_c, col_d = st.columns(2)

    with col_c:
        # Histograma de tamaño de pedidos
        fig_tam = px.histogram(
            picker_vol[picker_vol['cant_lineas'] <= picker_vol['cant_lineas'].quantile(0.95)],
            x='cant_lineas', nbins=30,
            labels={'cant_lineas': 'Líneas por pedido', 'count': 'Cantidad'},
            color_discrete_sequence=['steelblue'],
            title='Distribución de tamaño de pedidos'
        )
        fig_tam.add_vline(x=mediana_global, line_dash="dash", line_color="red",
                         annotation_text=f"Mediana operación: {mediana_global:.0f}")
        fig_tam.add_vline(x=mediana_picker, line_dash="solid", line_color="black",
                         annotation_text=f"Mediana picker: {mediana_picker:.0f}")
        fig_tam.update_layout(height=300, showlegend=False)
        st.plotly_chart(fig_tam, use_container_width=True)

    with col_d:
        # % pedidos por categoría de tamaño
        picker_vol2 = picker_vol.copy()
        picker_vol2['categoria'] = pd.cut(
            picker_vol2['cant_lineas'],
            bins=[0, 2, 5, 10, 20, 999],
            labels=['1-2 líneas', '3-5 líneas', '6-10 líneas', '11-20 líneas', '20+ líneas']
        )
        cat_counts = picker_vol2['categoria'].value_counts().sort_index()
        cat_pct = (cat_counts / len(picker_vol2) * 100).reset_index()
        cat_pct.columns = ['categoria', 'pct']

        fig_cat = px.bar(cat_pct, x='categoria', y='pct',
                        labels={'categoria': 'Tamaño', 'pct': '% de pedidos'},
                        color_discrete_sequence=['steelblue'],
                        title='% pedidos por tamaño')
        fig_cat.update_layout(height=300, showlegend=False)
        st.plotly_chart(fig_cat, use_container_width=True)

    st.markdown("---")

    # ── Boxplot comparativo ───────────────────────────────
    st.subheader("Comparación con otros alistadores")

    if len(picker_tiempo) > 0:
        # Top 10 por volumen + el picker seleccionado
        top10_vol = (df_vol.groupby('picker_id').size()
                    .nlargest(10).index.tolist())
        if picker_sel not in top10_vol:
            top10_vol.append(picker_sel)

        df_box = df_tiempo[df_tiempo['picker_id'].isin(top10_vol)].copy()
        df_box = df_box[df_box['seg_por_linea'] < df_box['seg_por_linea'].quantile(0.95)]
        df_box['es_seleccionado'] = df_box['picker_id'] == picker_sel
        df_box['etiqueta_box'] = df_box['picker_id'].map(mapeo).fillna(df_box['picker_id'])

        fig_box = px.box(df_box, x='etiqueta_box', y='seg_por_linea',
                        color='es_seleccionado',
                        color_discrete_map={True: 'tomato', False: 'steelblue'},
                        labels={'etiqueta_box': 'Alistador',
                                'seg_por_linea': 'Segundos por línea'},
                        title='Distribución de tiempos — Alistador seleccionado (rojo) vs top 10')
        fig_box.add_hline(y=60, line_dash="dash", line_color="green",
                         annotation_text="Meta 60s")
        fig_box.update_layout(showlegend=False, height=400,
                              xaxis_tickangle=45)
        st.plotly_chart(fig_box, use_container_width=True)

# ══════════════════════════════════════════════════════════
# PÁGINA 4 — RANKING
# ══════════════════════════════════════════════════════════
elif pagina == "🏆 Ranking":
    st.title("🏆 Ranking Real de Alistadores")
    st.markdown("Excluye roles de apoyo | Mínimo 200 pedidos | Score compuesto 0-100")

    ROLES_APOYO = ['EM039', 'EM560', 'EM289']

    # Mínimo dinámico según el período seleccionado
    dias_periodo = (fecha_fin - fecha_inicio).days
    MIN_PEDIDOS = max(10, int(dias_periodo * 1.5))
    st.caption(f"Mínimo de pedidos para aparecer en ranking: {MIN_PEDIDOS} (basado en {dias_periodo} días)")

    df_rank   = df_vol[~df_vol['picker_id'].isin(ROLES_APOYO)].copy()
    df_rank_t = df_tiempo[~df_tiempo['picker_id'].isin(ROLES_APOYO)].copy()

    vol_r = (df_rank.groupby(['picker_id', 'etiqueta'])
             .agg(total_pedidos = ('picker_id', 'count'),
                  total_lineas  = ('cant_lineas', 'sum'),
                  lineas_mediana= ('cant_lineas', 'median'),
                  pct_con_tiempo= ('tiempo_minutos', lambda x: (x>0).mean()*100))
             .reset_index())

    tiempo_r = (df_rank_t.groupby('picker_id')
                .agg(mediana_seg = ('seg_por_linea', 'median'),
                     cv_tiempo   = ('seg_por_linea', lambda x: x.std()/x.mean()*100))
                .reset_index())

    ranking = vol_r.merge(tiempo_r, on='picker_id', how='left')
    ranking = ranking[ranking['total_pedidos'] >= MIN_PEDIDOS].copy()

    def normalizar(serie, mayor_es_mejor=True):
        mn, mx = serie.min(), serie.max()
        if mx == mn: return pd.Series([50]*len(serie), index=serie.index)
        norm = (serie - mn) / (mx - mn) * 100
        return norm if mayor_es_mejor else 100 - norm

    ranking['score_volumen']      = (normalizar(ranking['total_pedidos'])*0.5 +
                                      normalizar(ranking['total_lineas'])*0.5)
    ranking['score_consistencia'] = normalizar(ranking['cv_tiempo'], False)
    ranking['score_complejidad']  = normalizar(ranking['lineas_mediana'])
    ranking['score_registro']     = normalizar(ranking['pct_con_tiempo'])
    ranking['score_final'] = (ranking['score_volumen']      * 0.35 +
                               ranking['score_consistencia'] * 0.30 +
                               ranking['score_complejidad']  * 0.20 +
                               ranking['score_registro']     * 0.15)
    ranking = ranking.sort_values('score_final', ascending=False)

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("Score Final")
        fig = px.bar(ranking.sort_values('score_final'),
                    x='score_final', y='etiqueta', orientation='h',
                    color='score_final',
                    color_continuous_scale='RdYlGn',
                    labels={'score_final': 'Score (0-100)', 'etiqueta': ''})
        fig.update_layout(showlegend=False, height=500,
                         coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Tabla de Rankings")
        tabla = ranking[['etiqueta', 'total_pedidos', 'total_lineas',
                         'mediana_seg', 'pct_con_tiempo', 'score_final']].copy()
        tabla.columns = ['Alistador', 'Pedidos', 'Líneas',
                         'Mediana s/l', '% Registro', 'Score']
        tabla = tabla.reset_index(drop=True)
        tabla.index += 1
        tabla['Mediana s/l'] = tabla['Mediana s/l'].round(1)
        tabla['% Registro'] = tabla['% Registro'].round(1)
        tabla['Score'] = tabla['Score'].round(1)
        st.dataframe(tabla, use_container_width=True, height=500)

    # Perfil scores top 5
    st.subheader("Perfil de Scores — Top 5")
    top5 = ranking.head(5)
    categorias = ['Volumen', 'Consistencia', 'Complejidad', 'Registro']
    fig2 = go.Figure()
    for _, row in top5.iterrows():
        fig2.add_trace(go.Bar(
            name=row['etiqueta'],
            x=categorias,
            y=[row['score_volumen'], row['score_consistencia'],
               row['score_complejidad'], row['score_registro']]
        ))
    fig2.update_layout(barmode='group', height=350,
                      yaxis_title='Score (0-100)')
    st.plotly_chart(fig2, use_container_width=True)