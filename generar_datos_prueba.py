"""
=============================================================
FAVARCIA — GENERADOR DE DATOS SINTÉTICOS PARA PRUEBAS
=============================================================
Propósito: Generar un archivo Excel realista que simule el
           reporte de alistadores a nivel de pedido individual.

Los parámetros están calibrados con datos REALES observados:
- Enero 2026: 4,924 pedidos en media quincena
- Febrero 2026: 8,814 pedidos en mes completo
- Efectividad: 97.4% (tasa de error 2.6%)
- Alistadores activos: ~38 personas (códigos EM###)
- Meta: 60 segundos por línea

HIPÓTESIS INCORPORADA EN LOS DATOS:
Los tiempos siguen distribución BIMODAL:
  - 70% de líneas: "limpias" → 15-45 seg/línea (cajón con producto)
  - 30% de líneas: "con fricción" → 90-300 seg/línea (cajón vacío, búsqueda)

Esto es lo que el análisis principal debe DETECTAR y DEMOSTRAR.
=============================================================
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import os

# Rutas ancladas al directorio del script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ── MODO DE OPERACIÓN ─────────────────────────────────────
# "demo"  → guarda en data/sample/ (va a GitHub, uso público)
# "real"  → guarda en data/raw/    (excluido por .gitignore)
#
MODO = "demo"   # ← CAMBIAR A "real" si quieres regenerar con parámetros distintos
# ──────────────────────────────────────────────────────────

if MODO == "demo":
    DATA_DIR = os.path.join(BASE_DIR, "data", "sample")
else:
    DATA_DIR = os.path.join(BASE_DIR, "data", "raw")

os.makedirs(DATA_DIR, exist_ok=True)

print(f"📁 MODO: {MODO.upper()}")
print(f"   Destino: {DATA_DIR}")

# Semilla aleatoria — garantiza que los mismos datos se generen
# cada vez que corras el script (reproducibilidad)
np.random.seed(42)
random.seed(42)


# ─────────────────────────────────────────────
# BLOQUE 1: DEFINIR LOS ALISTADORES
# ─────────────────────────────────────────────
# Basado en los códigos reales visibles en las fotos del tablero.
# Cada alistador tiene un perfil que afecta sus tiempos simulados.
# Esto refleja que hay alistadores nuevos, medios y expertos.

ALISTADORES = [
    # (codigo,  experiencia,  volumen_relativo)
    # experiencia: 'experto', 'medio', 'nuevo'
    # volumen_relativo: peso para asignar pedidos (más peso = más pedidos)
    ("EM039", "experto",  10),   # Top performer en fotos: 415 pedidos/quincena
    ("EM047", "experto",  10),   # Top performer: 346 pedidos/quincena
    ("EM128", "experto",   9),   # 216 pedidos/quincena
    ("EM196", "experto",   9),   # 179 pedidos/quincena
    ("EM239", "experto",  10),   # 393 pedidos/quincena
    ("EM304", "experto",  10),   # 392 pedidos/quincena (el del "pico de errores")
    ("EM452", "experto",  10),   # Top en febrero: 728 pedidos
    ("EM564", "experto",  10),   # Top en febrero: 1,004 pedidos
    ("EM575", "experto",   9),
    ("EM476", "experto",   9),
    ("EM113", "medio",     7),
    ("EM286", "medio",     6),
    ("EM289", "medio",     6),
    ("EM311", "medio",     6),
    ("EM386", "medio",     6),
    ("EM426", "medio",     5),
    ("EM459", "medio",     5),
    ("EM494", "medio",     5),
    ("EM560", "medio",     5),
    ("EM599", "medio",     4),
    ("EM024", "nuevo",     3),
    ("EM046", "nuevo",     2),   # El que tenía 5:00 min/línea en fotos
    ("EM130", "nuevo",     3),
    ("EM177", "nuevo",     2),
    ("EM210", "nuevo",     3),
    ("EM221", "nuevo",     3),
    ("EM285", "nuevo",     2),
    ("EM288", "nuevo",     2),
    ("EM307", "nuevo",     2),
    ("EM337", "nuevo",     2),   # El que tenía 4:00 min/línea en fotos
]

# Parámetros de tiempo según nivel de experiencia
# Estos definen la distribución de tiempos "limpios" para cada perfil
PERFIL_TIEMPOS = {
    "experto": {
        "media_limpio": 28,    # segundos por línea cuando el cajón tiene producto
        "std_limpio": 8,
        "pct_friccion": 0.22,  # 22% de sus pedidos tienen fricción (conocen bodega)
    },
    "medio": {
        "media_limpio": 38,
        "std_limpio": 12,
        "pct_friccion": 0.32,  # 32% de fricción
    },
    "nuevo": {
        "media_limpio": 55,
        "std_limpio": 18,
        "pct_friccion": 0.45,  # 45% de fricción (no conocen la bodega)
    },
}

# Tiempo de fricción — igual para todos los perfiles
# (el cajón vacío tarda lo mismo en resolverse sin importar quién lo encuentre)
FRICCION_MEDIA = 180    # segundos por línea cuando hay que buscar caja
FRICCION_STD   = 70


# ─────────────────────────────────────────────
# BLOQUE 2: FUNCIONES AUXILIARES
# ─────────────────────────────────────────────

def generar_lineas_pedido():
    """
    Genera cantidad de líneas por pedido.
    Distribución log-normal: mayoría de pedidos pequeños,
    algunos grandes — refleja realidad de distribuidoras.
    """
    # np.random.lognormal genera valores siempre positivos
    # con cola larga hacia la derecha (pedidos grandes son raros)
    lineas = int(np.random.lognormal(mean=2.0, sigma=0.8))
    return max(1, min(lineas, 80))  # Entre 1 y 80 líneas


def generar_unidades_por_linea():
    """La mayoría de líneas son 1-3 unidades, algunas son bultos grandes."""
    return max(1, int(np.random.lognormal(mean=1.2, sigma=0.9)))


def generar_tiempo_pedido(picker_id, cant_lineas, hora_del_dia):
    """
    Genera el tiempo total de un pedido en segundos.
    
    Incorpora tres factores reales:
    1. Perfil del alistador (experto/medio/nuevo)
    2. Bimodalidad: líneas limpias vs líneas con fricción
    3. Efecto hora del día: más fricción después de las 2pm
       (cajones más vacíos por el volumen acumulado del día)
    """
    
    # Encontrar el perfil del alistador
    perfil_nombre = next(
        (a[1] for a in ALISTADORES if a[0] == picker_id), "medio"
    )
    perfil = PERFIL_TIEMPOS[perfil_nombre]
    
    # Factor hora del día:
    # Después de las 14:00 (2pm) los cajones están más vacíos
    # → más probabilidad de fricción
    if hora_del_dia >= 14:
        factor_hora = 1.0 + (hora_del_dia - 14) * 0.08  # +8% por cada hora después de 2pm
    else:
        factor_hora = 1.0
    
    pct_friccion_ajustado = min(0.8, perfil["pct_friccion"] * factor_hora)
    
    # Calcular tiempo línea por línea
    tiempo_total = 0
    
    for _ in range(cant_lineas):
        # Decidir si esta línea tiene fricción o no
        tiene_friccion = np.random.random() < pct_friccion_ajustado
        
        if tiene_friccion:
            # Línea con fricción: cajón vacío, hay que buscar caja
            seg = np.random.normal(FRICCION_MEDIA, FRICCION_STD)
        else:
            # Línea limpia: cajón con producto
            seg = np.random.normal(perfil["media_limpio"], perfil["std_limpio"])
        
        # Los tiempos no pueden ser negativos
        tiempo_total += max(5, seg)
    
    # Agregar tiempo base de overhead por pedido
    # (caminar al área, tomar carretilla, ir a chequeo)
    overhead = np.random.normal(45, 15)
    tiempo_total += max(20, overhead)
    
    return round(tiempo_total, 1)


def tiempo_a_string(segundos_totales):
    """
    Convierte segundos a formato hh:mm:ss.xx
    igual al formato del reporte real de Favarcia.
    Ejemplo: 3925.5 → '1:05:25.50'
    """
    horas = int(segundos_totales // 3600)
    minutos = int((segundos_totales % 3600) // 60)
    segundos = segundos_totales % 60
    return f"{horas}:{minutos:02d}:{segundos:05.2f}"


def generar_errores(cant_lineas, picker_id, tiempo_seg, cant_lineas_total):
    """
    Genera cantidad de errores por pedido.
    
    Lógica realista:
    - Tasa base: ~2.6% de pedidos tienen al menos 1 error
    - Pedidos más grandes tienen más probabilidad de error
    - Alistadores nuevos tienen más errores
    - Pedidos con mucha fricción (tiempo alto) tienen más errores
      (el estrés y la búsqueda de cajas aumenta descuidos)
    """
    perfil_nombre = next(
        (a[1] for a in ALISTADORES if a[0] == picker_id), "medio"
    )
    
    # Tasa de error base según experiencia
    tasa_base = {"experto": 0.018, "medio": 0.028, "nuevo": 0.045}[perfil_nombre]
    
    # Factor por tamaño de pedido
    factor_tamaño = 1 + (cant_lineas / 20) * 0.3
    
    # Factor por fricción: si el tiempo/línea es muy alto, más probabilidad de error
    seg_por_linea = tiempo_seg / max(cant_lineas, 1)
    factor_friccion = 1 + max(0, (seg_por_linea - 60) / 100)
    
    prob_error = min(0.15, tasa_base * factor_tamaño * factor_friccion)
    
    if np.random.random() < prob_error:
        return np.random.choice([1, 1, 1, 2, 3], p=[0.6, 0.2, 0.1, 0.07, 0.03])
    return 0


# ─────────────────────────────────────────────
# BLOQUE 3: GENERADOR PRINCIPAL
# ─────────────────────────────────────────────

def generar_dataset(
    fecha_inicio="2026-01-16",
    fecha_fin="2026-02-28",
    pedidos_por_dia=450,
    incluir_sabados=True
):
    """
    Genera el dataset completo simulando la operación de Favarcia.
    
    Parámetros:
        fecha_inicio: primer día del período
        fecha_fin: último día del período
        pedidos_por_dia: promedio de pedidos diarios
        incluir_sabados: Favarcia trabaja algunos sábados
    
    Retorna:
        DataFrame con todos los pedidos simulados
    """
    
    print("🔄 Generando datos sintéticos de Favarcia...")
    print(f"   Período: {fecha_inicio} → {fecha_fin}")
    print(f"   Pedidos/día promedio: {pedidos_por_dia}")
    
    # Preparar lista de pickers con sus pesos de volumen
    picker_ids = [a[0] for a in ALISTADORES]
    picker_pesos = [a[2] for a in ALISTADORES]
    # Normalizar pesos para que sumen 1
    pesos_norm = [p / sum(picker_pesos) for p in picker_pesos]
    
    registros = []
    
    fecha_actual = datetime.strptime(fecha_inicio, "%Y-%m-%d")
    fecha_limite = datetime.strptime(fecha_fin, "%Y-%m-%d")
    
    while fecha_actual <= fecha_limite:
        
        # Saltar domingos siempre
        if fecha_actual.weekday() == 6:
            fecha_actual += timedelta(days=1)
            continue
        
        # Sábados: menos pedidos y no siempre
        es_sabado = fecha_actual.weekday() == 5
        if es_sabado:
            if not incluir_sabados or np.random.random() > 0.6:
                fecha_actual += timedelta(days=1)
                continue
            pedidos_hoy = int(pedidos_por_dia * 0.3)
        else:
            # Variación diaria ±15% — los días no son todos iguales
            variacion = np.random.normal(1.0, 0.15)
            pedidos_hoy = max(200, int(pedidos_por_dia * variacion))
        
        # Distribuir pedidos a lo largo del día
        # La operación empieza a las 6am, pico entre 10am-3pm
        # Distribución de horas: ponderada hacia el horario de trabajo
        horas_disponibles = list(range(6, 17))  # 6am a 5pm
        # Más pedidos en horas centrales del día
        pesos_hora = [1, 2, 3, 4, 5, 5, 4, 4, 3, 2, 1]
        pesos_hora_norm = [p / sum(pesos_hora) for p in pesos_hora]
        
        for _ in range(pedidos_hoy):
            
            # Asignar alistador según su volumen relativo
            picker_id = np.random.choice(picker_ids, p=pesos_norm)
            
            # Hora de inicio del pedido
            hora = np.random.choice(horas_disponibles, p=pesos_hora_norm)
            minuto = np.random.randint(0, 60)
            segundo = np.random.randint(0, 60)
            hora_inicio = fecha_actual.replace(hour=hora, minute=minuto, second=segundo)
            
            # Características del pedido
            cant_lineas = generar_lineas_pedido()
            cant_unidades = sum(generar_unidades_por_linea() for _ in range(cant_lineas))
            
            # Tiempo de procesamiento (la métrica clave)
            tiempo_seg = generar_tiempo_pedido(picker_id, cant_lineas, hora)
            hora_fin = hora_inicio + timedelta(seconds=tiempo_seg)
            
            # Errores
            cant_errores = generar_errores(cant_lineas, picker_id, tiempo_seg, cant_lineas)
            error_en_bodega = cant_errores > 0 and np.random.random() < 0.90
            error_al_cliente = cant_errores > 0 and not error_en_bodega
            
            registros.append({
                "fecha":            fecha_actual.strftime("%Y-%m-%d"),
                "picker_id":        picker_id,
                "hora_inicio":      hora_inicio.strftime("%H:%M:%S"),
                "hora_fin":         hora_fin.strftime("%H:%M:%S"),
                "cant_lineas":      cant_lineas,
                "cant_unidades":    cant_unidades,
                "tiempo":           tiempo_a_string(tiempo_seg),   # formato original Favarcia
                "tiempo_segundos":  round(tiempo_seg, 1),          # columna extra para facilitar análisis
                "seg_por_linea":    round(tiempo_seg / cant_lineas, 2),
                "cant_errores":     cant_errores,
                "error_bodega":     1 if error_en_bodega else 0,
                "error_cliente":    1 if error_al_cliente else 0,
            })
        
        fecha_actual += timedelta(days=1)
    
    df = pd.DataFrame(registros)
    
    # ── Resumen de validación ──────────────────────────────
    # Compara con los datos reales del tablero para verificar
    # que los sintéticos son realistas
    print(f"\n✅ Dataset generado: {len(df):,} pedidos")
    print(f"\n📊 VALIDACIÓN vs datos reales del tablero:")
    
    # Enero (segunda quincena)
    ene = df[df['fecha'] >= '2026-01-16']
    ene = ene[ene['fecha'] <= '2026-01-31']
    tasa_error_ene = ene['cant_errores'].gt(0).mean() * 100
    print(f"\n   Enero 2a quincena:")
    print(f"   Pedidos generados: {len(ene):,}  (real: 4,924)")
    print(f"   Tasa error: {tasa_error_ene:.1f}%  (real: 2.6%)")
    
    # Febrero
    feb = df[df['fecha'] >= '2026-02-01']
    tasa_error_feb = feb['cant_errores'].gt(0).mean() * 100
    print(f"\n   Febrero:")
    print(f"   Pedidos generados: {len(feb):,}  (real: 8,814)")
    print(f"   Tasa error: {tasa_error_feb:.1f}%  (real: 2.6%)")
    
    # Estadísticas de tiempo
    print(f"\n   Tiempo por línea (seg):")
    print(f"   Promedio: {df['seg_por_linea'].mean():.1f}s  (meta: 60s)")
    print(f"   Mediana:  {df['seg_por_linea'].median():.1f}s")
    print(f"   P90:      {df['seg_por_linea'].quantile(0.90):.1f}s")
    print(f"   Máximo:   {df['seg_por_linea'].max():.1f}s")
    
    return df


# ─────────────────────────────────────────────
# BLOQUE 4: EXPORTAR A EXCEL
# ─────────────────────────────────────────────

def exportar_excel(df, nombre_archivo="datos_prueba_favarcia.xlsx"):
    """
    Exporta el dataset a Excel con dos hojas:
    - Hoja 1: datos completos (todos los pedidos)
    - Hoja 2: resumen agregado por alistador (como el reporte real del WMS)
    
    Así podemos probar el análisis con ambos formatos.
    """
    
    # ExcelWriter permite escribir múltiples hojas en un solo archivo
    with pd.ExcelWriter(nombre_archivo, engine='openpyxl') as writer:
        
        # ── Hoja 1: Detalle por pedido ──
        df.to_excel(writer, sheet_name='Detalle_Pedidos', index=False)
        
        # ── Hoja 2: Resumen por alistador (como el tablero real) ──
        resumen = df.groupby('picker_id').agg(
            cant_pedidos    = ('picker_id', 'count'),
            cant_lineas     = ('cant_lineas', 'sum'),
            cant_unidades   = ('cant_unidades', 'sum'),
            tiempo_total_min= ('tiempo_segundos', lambda x: round(x.sum() / 60, 1)),
            seg_por_linea   = ('seg_por_linea', 'mean'),
            total_errores   = ('cant_errores', 'sum'),
            pct_error       = ('cant_errores', lambda x: round(x.gt(0).mean() * 100, 1)),
        ).reset_index()
        
        resumen['seg_por_linea'] = resumen['seg_por_linea'].round(2)
        resumen = resumen.sort_values('cant_pedidos', ascending=False)
        
        resumen.to_excel(writer, sheet_name='Resumen_Alistadores', index=False)
        
        print(f"\n✅ Archivo Excel generado: {nombre_archivo}")
        print(f"   Hoja 1 'Detalle_Pedidos': {len(df):,} filas")
        print(f"   Hoja 2 'Resumen_Alistadores': {len(resumen)} alistadores")
        print(f"\n💡 Usa este archivo para probar favarcia_picking_analysis.py")
        print(f"   Cambia ARCHIVO = '{nombre_archivo}' en el script principal")


# ─────────────────────────────────────────────
# BLOQUE 5: PUNTO DE ENTRADA
# ─────────────────────────────────────────────

if __name__ == "__main__":
    
    print("="*55)
    print("FAVARCIA — GENERADOR DE DATOS SINTÉTICOS")
    print("="*55)
    print("Datos calibrados con observaciones reales:")
    print("  Ene 2026: 4,924 pedidos | 97.4% efectividad")
    print("  Feb 2026: 8,814 pedidos | 97.4% efectividad")
    print("  Hipótesis: distribución bimodal de tiempos")
    print("="*55)
    
    # Generar datos para enero 2a quincena + febrero completo
    df = generar_dataset(
        fecha_inicio="2026-01-16",
        fecha_fin="2026-02-28",
        pedidos_por_dia=450,
        incluir_sabados=True
    )
    
    # Exportar a Excel
    exportar_excel(df, os.path.join(DATA_DIR, "datos_prueba_favarcia.xlsx"))
    
    print("\n🚀 Próximo paso:")
    print("   Abre favarcia_picking_analysis.py")
    print("   Cambia: ARCHIVO = 'datos_prueba_favarcia.xlsx'")
    print("   Corre el análisis y verifica que todo funciona")
    print("   Cuando lleguen los datos reales de IT, solo cambia esa línea.")