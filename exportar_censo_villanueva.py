"""
exportar_censo_villanueva.py
=============================
Script local — NO forma parte de la app Streamlit.
Corre el censo arbóreo completo POR ZONA OFICIAL (32 zonas del
Código Urbano Rural 2025, fuente: IDECOR / Municipalidad de Villa
Nueva) contra Earth Engine y guarda el resultado en
data/censo_arboreo_villanueva.json.

Uso:
    python exportar_censo_villanueva.py

Requiere: tener las credenciales de Earth Engine ya autenticadas
localmente (las mismas que usa la app para conectar_gee()),
y haber corrido antes convertir_zonificacion_vn.py (genera
data/zonificacion_villanueva.geojson).
"""

import ee
import json
import os
import datetime

# ============================================================
# CONFIGURACIÓN — debe coincidir con modulo_censo_arboreo_villanueva.py
# ============================================================

CANOPY_ASSET = 'projects/meta-forest-monitoring-okw37/assets/CanopyHeight'
ALTURA_MIN_ARBOL = 2

RUTA_ZONAS = os.path.join(os.path.dirname(__file__), 'data', 'zonificacion_villanueva.geojson')
SALIDA_JSON = os.path.join(os.path.dirname(__file__), 'data', 'censo_arboreo_villanueva.json')


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
# PROCESAMIENTO POR ZONA
# ============================================================

def _procesar_zona(geometry_geojson):
    """Conteo + área de copa para UNA zona (geometría GeoJSON real)."""
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

        area_zona_m2 = area.area(1).getInfo()

        n = conteo.get('labels') if conteo else 0
        area_copa_m2 = list(area_stats.values())[0] if area_stats else 0

        return {
            'n_arboles': int(n or 0),
            'area_copa_ha': round(area_copa_m2 / 10000, 3),
            'area_zona_ha': round(area_zona_m2 / 10000, 2),
            'error': None,
        }
    except Exception as e:
        return {'n_arboles': None, 'area_copa_ha': None, 'area_zona_ha': None, 'error': str(e)}


def main():
    print("Inicializando Earth Engine (cuenta de servicio)...")
    _conectar_gee()

    with open(RUTA_ZONAS, encoding='utf-8') as f:
        zonas_geojson = json.load(f)

    features = zonas_geojson['features']
    total = len(features)
    print(f"Zonas a procesar: {total}\n")

    resultados = []
    for i, feat in enumerate(features):
        props = feat['properties']
        desig = props.get('desig', '')
        nombre = props.get('name') or desig

        r = _procesar_zona(feat['geometry'])
        r['desig'] = desig
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
        print(f"[{i+1}/{total}] {desig} ({nombre}) -> {estado}")

    validos = [r for r in resultados if r['n_arboles'] is not None]
    fallidos = [r for r in resultados if r['n_arboles'] is None]

    # Unión de todas las zonas para el agregado "ciudad completa"
    print("\nCalculando cobertura agregada de Villa Nueva (unión de zonas)...")
    fc = ee.FeatureCollection(zonas_geojson)
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
        'metodo': 'por_zona_normativa',
        'fuente_zonas': 'IDECOR / Municipalidad de Villa Nueva — Código Urbano Rural 2025',
        'altura_min_arbol_m': ALTURA_MIN_ARBOL,
        'total_arboles': sum(r['n_arboles'] for r in validos),
        'total_area_copa_ha': round(sum(r['area_copa_ha'] for r in validos), 1),
        'zonas_procesadas': len(validos),
        'zonas_totales': total,
        'ciudad_area_copa_ha': round(area_copa_ciudad_m2 / 10000, 1) if area_copa_ciudad_m2 else 0,
        'ciudad_altura_media_m': round(stats_altura_ciudad.get('altura_mean'), 1)
            if stats_altura_ciudad.get('altura_mean') else None,
        'ciudad_altura_max_m': round(stats_altura_ciudad.get('altura_max'), 1)
            if stats_altura_ciudad.get('altura_max') else None,
        'zonas': resultados,
    }

    os.makedirs(os.path.dirname(SALIDA_JSON), exist_ok=True)
    with open(SALIDA_JSON, 'w', encoding='utf-8') as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)

    print(f"\nListo. {len(validos)}/{total} zonas OK, {len(fallidos)} con error.")
    print(f"Total árboles: {salida['total_arboles']:,}")
    print(f"Guardado en: {SALIDA_JSON}")


if __name__ == '__main__':
    main()