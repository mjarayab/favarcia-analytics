import pandas as pd

df = pd.read_excel('data/raw/FPM_Datos.xlsx')

print(f"Total filas raw: {len(df):,}")
print(f"Pedidos EM564 raw: {len(df[df['ALISTADOR'] == 'EM564']):,}")
print(f"Pedidos EM047 raw: {len(df[df['ALISTADOR'] == 'EM047']):,}")
print(f"\nRango de fechas:")
print(f"  Desde: {df['FECHA PEDIDO'].min()}")
print(f"  Hasta: {df['FECHA PEDIDO'].max()}")
print(f"\nFilas sin alistador: {df['ALISTADOR'].isna().sum():,}")
print(f"Filas con tiempo 0: {(df['TIEMPO ALISTO (MINUTOS)'] == 0).sum():,}")
print(f"Filas con tiempo nulo: {df['TIEMPO ALISTO (MINUTOS)'].isna().sum():,}")

import pandas as pd

df = pd.read_excel('data/raw/FPM_Datos.xlsx')

for picker in ['EM564', 'EM047']:
    sub = df[df['ALISTADOR'] == picker]
    con_tiempo = (sub['TIEMPO ALISTO (MINUTOS)'] > 0).sum()
    sin_tiempo = (sub['TIEMPO ALISTO (MINUTOS)'] == 0).sum()
    nulos = sub['TIEMPO ALISTO (MINUTOS)'].isna().sum()
    print(f"\n{picker}:")
    print(f"  Total pedidos:      {len(sub):,}")
    print(f"  Con tiempo > 0:     {con_tiempo:,} ({con_tiempo/len(sub)*100:.1f}%)")
    print(f"  Tiempo = 0:         {sin_tiempo:,} ({sin_tiempo/len(sub)*100:.1f}%)")
    print(f"  Tiempo nulo:        {nulos:,}")