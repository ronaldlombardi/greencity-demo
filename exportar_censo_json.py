"""
exportar_censo_json.py
=======================
Script local — NO forma parte de la app Streamlit.
Corre el censo arbóreo completo (grilla 300x300m) contra Earth Engine
y guarda el resultado en data/censo_arboreo_villamaria.json.

Uso:
    python exportar_censo_json.py

Requiere: tener las credenciales de Earth Engine ya autenticadas
localmente (las mismas que usa la app para conectar_gee()).
"""

import ee
import json
import math
import os
import datetime

# ============================================================
# CONFIGURACIÓN — debe coincidir con modulo_censo_arboreo.py
# ============================================================

CANOPY_ASSET = 'projects/meta-forest-monitoring-okw37/assets/CanopyHeight'
ALTURA_MIN_ARBOL = 2
TAMANO_CELDA_M = 300

COORDS_VM = [
    [-63.280, -32.390], [-63.200, -32.390],
    [-63.200, -32.440], [-63.280, -32.440], [-63.280, -32.390]
]

SALIDA_JSON = os.path.join(os.path.dirname(__file__), 'data', 'censo_arboreo_villamaria.json')


# ============================================================
# GRILLA
# ============================================================

def _generar_grilla(coords_bbox, tamano_m=TAMANO_CELDA_M):
    lons = [p[0] for p in coords_bbox]
    lats = [p[1] for p in coords_bbox]
    lon_min, lon_max = min(lons), max(lons)
    lat_min, lat_max = min(lats), max(lats)
    lat_media = (lat_min + lat_max) / 2

    m_por_grado_lat = 111320
    m_por_grado_lon = 111320 * math.cos(math.radians(lat_media))
    paso_lat = tamano_m / m_por_grado_lat
    paso_lon = tamano_m / m_por_grado_lon

    celdas = []
    lat, fila = lat_min, 0
    while lat < lat_max:
        lon, col = lon_min, 0
        lat2 = min(lat + paso_lat, lat_max)
        while lon < lon_max:
            lon2 = min(lon + paso_lon, lon_max)
            celdas.append({
                'id': f"f{fila}_c{col}",
                'coords': [[lon, lat], [lon2, lat], [lon2, lat2], [lon, lat2], [lon, lat]],
                'centro': [(lat + lat2) / 2, (lon + lon2) / 2],
            })
            lon += paso_lon
            col += 1
        lat += paso_lat
        fila += 1
    return celdas


def _procesar_celda(coords_celda):
    try:
        area = ee.Geometry.Polygon([coords_celda])
        canopy = ee.ImageCollection(CANOPY_ASSET).mosaic().rename('altura').clip(area)
        mask_arbol = canopy.gte(ALTURA_MIN_ARBOL).selfMask()

        conectados = mask_arbol.connectedComponents(
            connectedness=ee.Kernel.plus(1), maxSize=256
        )
        conteo = conectados.select('labels').reduceRegion(
            reducer=ee.Reducer.countDistinctNonNull(),
            geometry=area, scale=1, maxPixels=1e8, bestEffort=True, tileScale=4,
        ).getInfo()

        area_stats = mask_arbol.multiply(ee.Image.pixelArea()).reduceRegion(
            reducer=ee.Reducer.sum(), geometry=area, scale=1,
            maxPixels=1e8, bestEffort=True, tileScale=4,
        ).getInfo()

        n = conteo.get('labels') if conteo else 0
        area_m2 = list(area_stats.values())[0] if area_stats else 0
        return {'n_arboles': int(n or 0), 'area_copa_ha': round(area_m2 / 10000, 3), 'error': None}
    except Exception as e:
        return {'n_arboles': None, 'area_copa_ha': None, 'error': str(e)}


def _conectar_gee():
    """Misma lógica de conexión que usa app.py — cuenta de servicio, no auth de usuario."""
    import json as _json
    gee_env = os.environ.get('GEE_SERVICE_ACCOUNT_JSON')
    if gee_env:
        info = _json.loads(gee_env)
        cred = ee.ServiceAccountCredentials(
            email=info['client_email'],
            key_data=_json.dumps(info),
        )
    else:
        ruta = os.path.join(os.path.dirname(__file__), 'service_account.json')
        cred = ee.ServiceAccountCredentials(email=None, key_file=ruta)
    ee.Initialize(credentials=cred, project='my-project-1697-1767615452939')


def main():
    print("Inicializando Earth Engine (cuenta de servicio)...")
    _conectar_gee()

    celdas = _generar_grilla(COORDS_VM)
    total = len(celdas)
    print(f"Grilla generada: {total} celdas de {TAMANO_CELDA_M}x{TAMANO_CELDA_M}m")

    resultados = []
    for i, c in enumerate(celdas):
        r = _procesar_celda(c['coords'])
        r['id'] = c['id']
        r['centro'] = c['centro']
        resultados.append(r)
        estado = "OK" if r['n_arboles'] is not None else f"ERROR: {r['error']}"
        print(f"[{i+1}/{total}] {c['id']} -> {estado}")

    validas = [r for r in resultados if r['n_arboles'] is not None]
    fallidas = [r for r in resultados if r['n_arboles'] is None]

    salida = {
        'fecha_calculo': datetime.datetime.now().isoformat(),
        'tamano_celda_m': TAMANO_CELDA_M,
        'altura_min_arbol_m': ALTURA_MIN_ARBOL,
        'total_arboles': sum(r['n_arboles'] for r in validas),
        'total_area_copa_ha': round(sum(r['area_copa_ha'] for r in validas), 1),
        'celdas_procesadas': len(validas),
        'celdas_totales': total,
        'celdas': resultados,
    }

    os.makedirs(os.path.dirname(SALIDA_JSON), exist_ok=True)
    with open(SALIDA_JSON, 'w', encoding='utf-8') as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)

    print(f"\nListo. {len(validas)}/{total} celdas OK, {len(fallidas)} con error.")
    print(f"Total árboles: {salida['total_arboles']:,}")
    print(f"Guardado en: {SALIDA_JSON}")


if __name__ == '__main__':
    main()