"""
exportar_indicadores_villamaria.py
===================================
Script local — NO forma parte de la app Streamlit.
Calcula los indicadores ambientales reales de Villa María (cobertura de
suelo, accesibilidad a verde, temperatura superficial LST, verde público
OSM) usando el límite geográfico real de la ciudad (38 barrios oficiales,
data/barrios_villamaria.geojson) y guarda el resultado en
data/indicadores_villamaria.json.

Uso:
    python exportar_indicadores_villamaria.py

Requiere: credenciales de Earth Engine autenticadas localmente (mismas
que usa exportar_censo_json.py), y data/barrios_villamaria.geojson
ya generado.
"""

import ee
import json
import os
import datetime

from modulo_temperatura import cargar_lst
from modulo_osm import cargar_osm

RUTA_BARRIOS = os.path.join(os.path.dirname(__file__), 'data', 'barrios_villamaria.geojson')
SALIDA_JSON = os.path.join(os.path.dirname(__file__), 'data', 'indicadores_villamaria.json')

POBLACION_VM = 96061  # INDEC, Censo Nacional 2022, resultados definitivos (actualización 15/01/2024)

# Clases ESA WorldCover -> claves de DATOS_VM['cobertura']
CLASES_WC = {
    10: 'arboles',
    20: 'arbustos',
    30: 'pastizales',
    40: 'cultivos',
    50: 'edificado',
    60: 'suelo',
    80: 'agua',
}

# Categorías OSM con uso público explícito — mismo criterio que Villa Nueva,
# para que ambas ciudades sean comparables entre sí.
CATS_PUBLICO_EXPLICITO = {'Parques', 'Deportivo', 'Plazas / jardines', 'Cementerios'}
CATS_COMPLEMENTARIO = {'Naturaleza', 'Áreas verdes', 'Otros'}


# ============================================================
# CONEXIÓN GEE — misma lógica que exportar_censo_json.py
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


def _cargar_barrios():
    with open(RUTA_BARRIOS, encoding='utf-8') as f:
        return json.load(f)


def _bbox_desde_geojson(barrios_geojson):
    """(sur, oeste, norte, este) recorriendo las coordenadas del geojson."""
    lats, lons = [], []
    for feat in barrios_geojson['features']:
        geom = feat['geometry']
        anillos = [geom['coordinates'][0]] if geom['type'] == 'Polygon' \
            else [poly[0] for poly in geom['coordinates']]
        for anillo in anillos:
            for lon, lat in anillo:
                lons.append(lon)
                lats.append(lat)
    return (min(lats), min(lons), max(lats), max(lons))


def _hull_coords(barrios_geojson):
    """Envolvente convexa de la unión de los 38 barrios (anillo simple para LST)."""
    fc = ee.FeatureCollection(barrios_geojson)
    hull = fc.geometry().convexHull(maxError=10)
    coords = hull.coordinates().getInfo()
    return coords[0]


# ============================================================
# COBERTURA DE SUELO (ESA WorldCover 2020)
# ============================================================

def _calcular_cobertura(barrios_geojson):
    fc = ee.FeatureCollection(barrios_geojson)
    area = fc.geometry()
    wc = ee.Image('ESA/WorldCover/v100/2020').clip(area)

    area_total_m2 = area.area(1).getInfo()

    pct = {}
    for codigo, clave in CLASES_WC.items():
        mask = wc.eq(codigo)
        r = mask.multiply(ee.Image.pixelArea()).reduceRegion(
            reducer=ee.Reducer.sum(), geometry=area, scale=10,
            maxPixels=1e10, bestEffort=True, tileScale=8,
        ).getInfo()
        m2 = list(r.values())[0] if r else 0
        pct[clave] = round((m2 or 0) / area_total_m2 * 100, 1)

    return pct, area_total_m2


# ============================================================
# ACCESIBILIDAD A ESPACIOS VERDES
# ============================================================

def _calcular_accesibilidad(barrios_geojson, poblacion):
    """Distancia de cada píxel edificado al verde más cercano — mismo
    método usado en exportar_indicadores_villanueva.py."""
    fc = ee.FeatureCollection(barrios_geojson)
    area = fc.geometry()
    wc = ee.Image('ESA/WorldCover/v100/2020').clip(area)

    verde = wc.eq(10).Or(wc.eq(20)).Or(wc.eq(30)).selfMask()
    edif = wc.eq(50).selfMask()
    dist = verde.fastDistanceTransform(1000).sqrt().multiply(10)
    dist_edif = dist.updateMask(edif)

    def _suma(img):
        r = img.reduceRegion(
            reducer=ee.Reducer.sum(), geometry=area, scale=10,
            maxPixels=1e10, bestEffort=True, tileScale=8,
        ).getInfo()
        return (list(r.values())[0] if r else 0) or 0

    def _media(img):
        r = img.reduceRegion(
            reducer=ee.Reducer.mean(), geometry=area, scale=10,
            maxPixels=1e10, bestEffort=True, tileScale=8,
        ).getInfo()
        return list(r.values())[0] if r else None

    t_edif = _suma(edif)
    r_100 = _suma(dist_edif.lt(100))
    r_300 = _suma(dist_edif.lt(300))
    r_500 = _suma(dist_edif.lt(500))
    dist_prom = _media(dist_edif)

    verde_m2 = verde.multiply(ee.Image.pixelArea()).reduceRegion(
        reducer=ee.Reducer.sum(), geometry=area, scale=10,
        maxPixels=1e10, bestEffort=True, tileScale=8,
    ).getInfo()
    verde_m2 = (list(verde_m2.values())[0] if verde_m2 else 0) or 0

    if not t_edif:
        return {
            'acceso': None, 'dist_prom': None, 'm2_hab_sat': round(verde_m2 / poblacion, 1),
            'r_0_100': None, 'r_100_300': None, 'r_300_500': None, 'r_500_mas': None,
        }

    return {
        'acceso': round((r_300 / t_edif) * 100, 1),
        'dist_prom': round(dist_prom, 0) if dist_prom is not None else None,
        'm2_hab_sat': round(verde_m2 / poblacion, 1),
        'r_0_100': round((r_100 / t_edif) * 100, 1),
        'r_100_300': round(((r_300 - r_100) / t_edif) * 100, 1),
        'r_300_500': round(((r_500 - r_300) / t_edif) * 100, 1),
        'r_500_mas': round(((t_edif - r_500) / t_edif) * 100, 1),
    }


# ============================================================
# VERDE PÚBLICO (OSM / Overpass)
# ============================================================

def _resumen_osm(lista, poblacion):
    area_m2 = sum(e['area_m2'] for e in lista)
    por_cat = {}
    for e in lista:
        cat = e['categoria']
        if cat not in por_cat:
            por_cat[cat] = {'cantidad': 0, 'area_m2': 0}
        por_cat[cat]['cantidad'] += 1
        por_cat[cat]['area_m2'] += e['area_m2']
    return {
        'elementos': len(lista),
        'area_ha': round(area_m2 / 10000, 1),
        'm2_hab': round(area_m2 / poblacion, 1),
        'por_categoria': por_cat,
    }


def _clasificar_osm(osm, poblacion):
    """Separa 'público explícito' (headline, comparable OMS) de
    'complementario' (cobertura verde no necesariamente accesible) —
    mismo criterio que Villa Nueva, para que ambas ciudades sean
    comparables entre sí."""
    if not osm or not osm.get('espacios'):
        return osm

    espacios = osm['espacios']
    publico = [e for e in espacios if e['categoria'] in CATS_PUBLICO_EXPLICITO]
    complementario = [e for e in espacios if e['categoria'] in CATS_COMPLEMENTARIO]

    resumen_publico = _resumen_osm(publico, poblacion)
    resumen_complementario = _resumen_osm(complementario, poblacion)
    area_total_m2 = sum(e['area_m2'] for e in espacios)

    return {
        'elementos': resumen_publico['elementos'],
        'area_ha': resumen_publico['area_ha'],
        'm2_hab': resumen_publico['m2_hab'],
        'por_categoria': resumen_publico['por_categoria'],
        'complementario': resumen_complementario,
        'total_combinado_ha': round(area_total_m2 / 10000, 1),
        'total_combinado_m2_hab': round(area_total_m2 / poblacion, 1),
        'espacios': espacios,
        'top10': sorted(publico, key=lambda x: -x['area_m2'])[:10],
        'error': None,
    }


# ============================================================
# MAIN
# ============================================================

def main():
    print("Inicializando Earth Engine (cuenta de servicio)...")
    _conectar_gee()

    barrios_geojson = _cargar_barrios()

    print("\nCalculando cobertura de suelo (ESA WorldCover 2020)...")
    cobertura, area_total_m2 = _calcular_cobertura(barrios_geojson)
    print(f"  -> {cobertura}")

    print("\nCalculando accesibilidad a espacios verdes...")
    acceso = _calcular_accesibilidad(barrios_geojson, POBLACION_VM)
    print(f"  -> {acceso}")

    print("\nCalculando envolvente convexa para LST...")
    coords_hull = _hull_coords(barrios_geojson)

    print("Calculando temperatura superficial (Landsat 8/9)...")
    lst = cargar_lst(coords_hull)
    if lst:
        print(f"  -> {lst['n_imagenes']} imágenes, T media {lst['t_media']}°C")
    else:
        print("  -> Sin imágenes Landsat disponibles para el período.")

    print("\nCalculando verde público (OSM / Overpass)...")
    bbox = _bbox_desde_geojson(barrios_geojson)
    osm_bruto = cargar_osm(bbox, POBLACION_VM)
    osm = _clasificar_osm(osm_bruto, POBLACION_VM)
    if osm:
        print(f"  -> {osm['elementos']} elementos, {osm['area_ha']} ha, {osm['m2_hab']} m²/hab")
    else:
        print("  -> No se pudo consultar la API Overpass.")

    salida = {
        'fecha_calculo': datetime.datetime.now().isoformat(),
        'fuente_limite': '38 barrios oficiales — data/barrios_villamaria.geojson',
        'area_ciudad_km2': round(area_total_m2 / 1e6, 1),
        'poblacion': POBLACION_VM,
        'cobertura': cobertura,
        'acceso': acceso,
        'lst': lst,
        'osm': osm,
    }

    os.makedirs(os.path.dirname(SALIDA_JSON), exist_ok=True)
    with open(SALIDA_JSON, 'w', encoding='utf-8') as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)

    print(f"\nGuardado en: {SALIDA_JSON}")


if __name__ == '__main__':
    main()