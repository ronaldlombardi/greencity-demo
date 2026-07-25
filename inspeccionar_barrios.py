"""
inspeccionar_barrios.py
========================
Script de UNA SOLA VEZ para ver la estructura del shapefile de Barrios
antes de integrarlo al Censo Arbóreo.
"""

import geopandas as gpd
import os

RUTA_SHP = os.path.join(os.path.dirname(__file__), 'data', 'barrios_raw')

def main():
    # Busca el .shp dentro de la carpeta
    archivos = [f for f in os.listdir(RUTA_SHP) if f.endswith('.shp')]
    if not archivos:
        print("No se encontró ningún archivo .shp en data/barrios_raw/")
        return

    ruta_completa = os.path.join(RUTA_SHP, archivos[0])
    print(f"Leyendo: {ruta_completa}\n")

    gdf = gpd.read_file(ruta_completa)

    print(f"Cantidad de polígonos: {len(gdf)}")
    print(f"Sistema de coordenadas (CRS) original: {gdf.crs}")
    print(f"\nColumnas disponibles: {list(gdf.columns)}")
    print(f"\nPrimeras 5 filas:")
    print(gdf.head())


if __name__ == '__main__':
    main()