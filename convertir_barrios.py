"""
convertir_barrios.py
=====================
Script de UNA SOLA VEZ: convierte el shapefile de Barrios (EPSG:22174,
encoding con problemas de tildes) a un GeoJSON limpio en EPSG:4326
(lat/lon), listo para usar en el Censo Arbóreo.

Uso:
    python convertir_barrios.py
"""

import geopandas as gpd
import os

RUTA_SHP_DIR = os.path.join(os.path.dirname(__file__), 'data', 'barrios_raw')
RUTA_SALIDA = os.path.join(os.path.dirname(__file__), 'data', 'barrios_villamaria.geojson')


def _arreglar_mojibake(texto):
    """
    Revierte texto UTF-8 que fue mal decodificado como cp1252
    (ej. 'PEÃ‘A' -> 'PEÑA'). Si el texto ya está bien, lo deja igual.
    """
    if not isinstance(texto, str):
        return texto
    try:
        return texto.encode('cp1252').decode('utf-8')
    except (UnicodeDecodeError, UnicodeEncodeError):
        return texto


def main():
    archivos = [f for f in os.listdir(RUTA_SHP_DIR) if f.endswith('.shp')]
    if not archivos:
        print("No se encontró ningún archivo .shp en data/barrios_raw/")
        return

    ruta_shp = os.path.join(RUTA_SHP_DIR, archivos[0])
    gdf = gpd.read_file(ruta_shp)

    print("Antes de corregir:")
    print(gdf['NOMBRE'].head(10).tolist())

    # Arreglar el mojibake ANTES de reproyectar/limpiar
    gdf['NOMBRE'] = gdf['NOMBRE'].apply(_arreglar_mojibake)

    # Reproyectar de EPSG:22174 (metros) a EPSG:4326 (lat/lon)
    gdf = gdf.to_crs(epsg=4326)

    # Limpiar nombres: mayúsculas consistentes, sin espacios extra
    gdf['NOMBRE'] = gdf['NOMBRE'].str.strip().str.upper()

    print("\nDespués de reproyectar y limpiar:")
    print(gdf[['NOMBRE']].head(10).to_string())
    print(f"\nCRS final: {gdf.crs}")

    # Guardar como GeoJSON estándar
    gdf[['NOMBRE', 'geometry']].to_file(RUTA_SALIDA, driver='GeoJSON')
    print(f"\nGuardado en: {RUTA_SALIDA}")
    print(f"Total de barrios: {len(gdf)}")


if __name__ == '__main__':
    main()