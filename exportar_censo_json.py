"""
exportar_censo_json.py
=======================
Script local — NO forma parte de la app Streamlit.
Corre el censo arbóreo completo POR BARRIO REAL (38 barrios,
fuente: datos.villamaria.gob.ar) contra Earth Engine y guarda
el resultado en data/censo_arboreo_villamaria.json.

Uso:
    python exportar_censo_json.py

Requiere: tener las credenciales de Earth Engine ya autenticadas
localmente (las mismas que usa la app para conectar_gee()),
y haber corrido antes convertir_barrios.py (genera
data/barrios_villamaria.geojson).
"""

import ee
import json
import os
import datetime

# ============================================================
# CONFIGURACIÓN — debe coincidir con modulo_censo_arboreo.py
# ============================================================

CANOPY_ASSET = 'projects/meta-forest-monitoring-okw37/assets/CanopyHeight'
ALTURA_MIN_ARBOL = 2

RUTA_BARRIOS = os.path.join(os.path.dirname(__file__), 'data', 'barrios_villamaria.geojson')
SALIDA_JSON = os.path.join(os.path.dirname(__file__), 'data', 'censo_arboreo_villamaria.json')


# ============================================================
# CONEXIÓN GEE — misma lógica que app.py
# ============================================================

def _conectar_gee():
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


# ============================================================
# PROCESAMIENTO POR BARRIO
# ============================================================

def _procesar_barrio(geometry_geojson):
    """Conteo + área de copa para UN barrio (geometría GeoJSON real)."""
    try:
        area = ee.Geometry(geometry_geojson)
        canopy = ee.ImageCollection(CANOPY_ASSET).mosaic().rename('altura').clip(area)
        mask_arbol = canopy.gte(ALTURA_MIN_ARBOL).selfMask()

        conectados = mask_arbol.connectedComponents(
            connectedness=ee.Kernel.plus(1), maxSize=256
        )
        conteo = conectados.select('labels').reduceRegion(
            reducer=ee.Reducer.countDistinctNonNull(),
            geometry=area, scale=1, maxPixels=1e9, bestEffort=True, tileScale=8,
        ).getInfo()

        area_stats = mask_arbol.multiply(ee.Image.pixelArea()).reduceRegion(
            reducer=ee.Reducer.sum(), geometry=area, scale=1,
            maxPixels=1e9, bestEffort=True, tileScale=8,
        ).getInfo()

        area_barrio_m2 = area.area(1).getInfo()

        n = conteo.get('labels') if conteo else 0
        area_copa_m2 = list(area_stats.values())[0] if area_stats else 0

        return {
            'n_arboles': int(n or 0),
            'area_copa_ha': round(area_copa_m2 / 10000, 3),
            'area_barrio_ha': round(area_barrio_m2 / 10000, 2),
            'error': None,
        }
    except Exception as e:
        return {'n_arboles': None, 'area_copa_ha': None, 'area_barrio_ha': None, 'error': str(e)}


def main():
    print("Inicializando Earth Engine (cuenta de servicio)...")
    _conectar_gee()

    with open(RUTA_BARRIOS, encoding='utf-8') as f:
        barrios_geojson = json.load(f)

    features = barrios_geojson['features']
    total = len(features)
    print(f"Barrios a procesar: {total}\n")

    resultados = []
    for i, feat in enumerate(features):
        nombre = feat['properties']['NOMBRE']
        r = _procesar_barrio(feat['geometry'])
        r['nombre'] = nombre
        # Centro aproximado (para ubicar el marcador/tooltip en el mapa)
        coords_ring = feat['geometry']['coordinates'][0]
        if feat['geometry']['type'] == 'MultiPolygon':
            coords_ring = feat['geometry']['coordinates'][0][0]
        lons = [c[0] for c in coords_ring]
        lats = [c[1] for c in coords_ring]
        r['centro'] = [sum(lats) / len(lats), sum(lons) / len(lons)]

        resultados.append(r)
        estado = "OK" if r['n_arboles'] is not None else f"ERROR: {r['error']}"
        print(f"[{i+1}/{total}] {nombre} -> {estado}")

    validos = [r for r in resultados if r['n_arboles'] is not None]
    fallidos = [r for r in resultados if r['n_arboles'] is None]

    # Unión de todos los barrios para el agregado "ciudad completa"
    print("\nCalculando cobertura agregada de la ciudad (unión de barrios)...")
    fc = ee.FeatureCollection(barrios_geojson)
    area_ciudad = fc.geometry()
    canopy = ee.ImageCollection(CANOPY_ASSET).mosaic().rename('altura').clip(area_ciudad)
    mask_arbol = canopy.gte(ALTURA_MIN_ARBOL)
    altura_arbol = canopy.updateMask(mask_arbol)

    area_stats_ciudad = mask_arbol.multiply(ee.Image.pixelArea()).reduceRegion(
        reducer=ee.Reducer.sum(), geometry=area_ciudad, scale=1,
        maxPixels=1e10, bestEffort=True, tileScale=8,
    ).getInfo()
    stats_altura_ciudad = altura_arbol.reduceRegion(
        reducer=ee.Reducer.mean().combine(ee.Reducer.max(), sharedInputs=True),
        geometry=area_ciudad, scale=1, maxPixels=1e10, bestEffort=True, tileScale=8,
    ).getInfo()
    area_copa_ciudad_m2 = list(area_stats_ciudad.values())[0] if area_stats_ciudad else 0

    salida = {
        'fecha_calculo': datetime.datetime.now().isoformat(),
        'metodo': 'por_barrio_real',
        'fuente_barrios': 'datos.villamaria.gob.ar — Barrios 2021',
        'altura_min_arbol_m': ALTURA_MIN_ARBOL,
        'total_arboles': sum(r['n_arboles'] for r in validos),
        'total_area_copa_ha': round(sum(r['area_copa_ha'] for r in validos), 1),
        'barrios_procesados': len(validos),
        'barrios_totales': total,
        'ciudad_area_copa_ha': round(area_copa_ciudad_m2 / 10000, 1) if area_copa_ciudad_m2 else 0,
        'ciudad_altura_media_m': round(stats_altura_ciudad.get('altura_mean'), 1)
            if stats_altura_ciudad.get('altura_mean') else None,
        'ciudad_altura_max_m': round(stats_altura_ciudad.get('altura_max'), 1)
            if stats_altura_ciudad.get('altura_max') else None,
        'barrios': resultados,
    }

    os.makedirs(os.path.dirname(SALIDA_JSON), exist_ok=True)
    with open(SALIDA_JSON, 'w', encoding='utf-8') as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)

    print(f"\nListo. {len(validos)}/{total} barrios OK, {len(fallidos)} con error.")
    print(f"Total árboles: {salida['total_arboles']:,}")
    print(f"Guardado en: {SALIDA_JSON}")


if __name__ == '__main__':
    main()
