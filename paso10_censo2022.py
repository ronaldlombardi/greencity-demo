"""
paso10_censo2022.py
===================
Análisis socioespacial: Censo 2022 + Acceso a verde (GEE)
Versión optimizada: procesa TODO en una sola llamada GEE con reduceRegions()
"""

import ee
import os
import json

ruta = os.path.join(os.path.dirname(__file__), 'service_account.json')
credenciales = ee.ServiceAccountCredentials(email=None, key_file=ruta)
ee.Initialize(credentials=credenciales, project='my-project-1697-1767615452939')
print("Conectado a Earth Engine.\n")

# ============================================================
# CONFIGURACIÓN
# ============================================================

CIUDADES = {
    'villamaria': {
        'nombre':    'Villa María - Villa Nueva',
        'coords':    [[-63.28,-32.39],[-63.20,-32.39],[-63.20,-32.44],[-63.28,-32.44]],
        'poblacion': 120000,
        'censo': {
            'pob_2010': 101905, 'variacion_pct': 17.8,
            'viviendas': 48200, 'hogares': 43500,
            'piso_tierra': 3.2, 'sin_agua_red': 8.1,
            'sin_inodoro': 2.4, 'hacinamiento': 5.8,
            'sin_gas_red': 42.3, 'ipmh_pct': 8.4,
            'edad_0_14': 21.3, 'edad_65_mas': 14.9,
        }
    },
    'sanfrancisco': {
        'nombre':    'San Francisco',
        'coords':    [[-62.105,-31.405],[-62.055,-31.405],[-62.055,-31.450],[-62.105,-31.450]],
        'poblacion': 62000,
        'censo': {
            'pob_2010': 59659, 'variacion_pct': 3.9,
            'viviendas': 26800, 'hogares': 24100,
            'piso_tierra': 2.1, 'sin_agua_red': 5.4,
            'sin_inodoro': 1.8, 'hacinamiento': 4.2,
            'sin_gas_red': 38.7, 'ipmh_pct': 6.2,
            'edad_0_14': 20.1, 'edad_65_mas': 15.4,
        }
    }
}

PASO_GRADOS = 0.004  # ~450m a latitud ~32°S


# ============================================================
# CONSTRUCCIÓN DE GRILLA EN GEE (FeatureCollection)
# ============================================================

def crear_grilla_ee(coords, paso=PASO_GRADOS):
    """Crea la grilla como FeatureCollection de GEE — sin loop de consultas."""
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    lon_min, lon_max = min(lons), max(lons)
    lat_min, lat_max = min(lats), max(lats)

    features = []
    i = 0
    lon = lon_min
    while lon < lon_max:
        lat = lat_min
        while lat < lat_max:
            geom = ee.Geometry.Rectangle([lon, lat, lon + paso, lat + paso])
            feat = ee.Feature(geom, {
                'celda_id': i,
                'centroid_lon': round(lon + paso/2, 5),
                'centroid_lat': round(lat + paso/2, 5),
            })
            features.append(feat)
            i += 1
            lat += paso
        lon += paso

    print(f"  Grilla creada: {len(features)} celdas")
    return ee.FeatureCollection(features), len(features)


# ============================================================
# ANÁLISIS GEE — UNA SOLA LLAMADA con reduceRegions()
# ============================================================

def analizar_ciudad_gee(ciudad_key):
    ciudad = CIUDADES[ciudad_key]
    coords = ciudad['coords']
    area   = ee.Geometry.Polygon([coords])

    print(f"\n{'='*55}")
    print(f"  {ciudad['nombre']}")
    print(f"{'='*55}")

    # Capas base
    wc        = ee.Image('ESA/WorldCover/v100/2020').clip(area)
    verde     = wc.eq(10).Or(wc.eq(20)).Or(wc.eq(30)).selfMask()
    edif      = wc.eq(50)
    dist      = verde.fastDistanceTransform(1000).sqrt().multiply(10)
    dist_edif = dist.updateMask(edif.selfMask())

    # Imagen multicapa para reducir en una sola llamada
    img = ee.Image.cat([
        edif.rename('edif'),
        dist_edif.rename('dist_verde'),
        dist_edif.lt(300).rename('acceso_300'),
        ee.Image.constant(1).rename('total'),
    ])

    # Grilla como FeatureCollection
    grilla, n_celdas = crear_grilla_ee(coords)

    print(f"  Consultando GEE con reduceRegions() — una sola llamada...")
    resultado = img.reduceRegions(
        collection=grilla,
        reducer=ee.Reducer.sum().combine(
            ee.Reducer.mean(), sharedInputs=True
        ),
        scale=30,
        tileScale=4,
    )

    print(f"  Descargando resultados...")
    features = resultado.getInfo()['features']
    print(f"  Recibidas {len(features)} celdas ✅")

    # Procesar resultados
    celdas = []
    for f in features:
        p = f['properties']
        edif_sum   = p.get('edif_sum', 0) or 0
        total_sum  = p.get('total_sum', 1) or 1
        acc_sum    = p.get('acceso_300_sum', 0) or 0
        dist_mean  = p.get('dist_verde_mean')

        pct_edif   = (edif_sum / total_sum * 100) if total_sum > 0 else 0
        pct_acceso = (acc_sum / edif_sum * 100) if edif_sum > 0 else 100

        if pct_edif < 3:  # ignorar celdas sin edificación
            continue

        celdas.append({
            'celda_id':      p.get('celda_id', 0),
            'centroid_lon':  p.get('centroid_lon', 0),
            'centroid_lat':  p.get('centroid_lat', 0),
            'pct_edificado': round(pct_edif, 1),
            'dist_prom_m':   round(dist_mean, 0) if dist_mean else None,
            'pct_acceso':    round(pct_acceso, 1),
        })

    print(f"  Celdas con edificación: {len(celdas)}")
    return celdas


# ============================================================
# MÉTRICAS Y EQUIDAD
# ============================================================

def calcular_metricas(celdas, poblacion_total):
    urbanas = [c for c in celdas if c['dist_prom_m'] is not None]
    if not urbanas:
        return None

    # Población proporcional al % edificado
    total_edif = sum(c['pct_edificado'] for c in urbanas)
    for c in urbanas:
        c['pob'] = round(poblacion_total * c['pct_edificado'] / total_edif)

    pob_buen_acceso = sum(c['pob'] for c in urbanas if c['pct_acceso'] >= 80)
    pob_sin_acceso  = sum(c['pob'] for c in urbanas if c['pct_acceso'] < 80)

    # Distancia media ponderada por población
    dists = [c['dist_prom_m'] for c in urbanas]
    pobs  = [c['pob'] for c in urbanas]
    media_pond = sum(d*p for d,p in zip(dists,pobs)) / sum(pobs)
    var_pond   = sum(p*(d-media_pond)**2 for d,p in zip(dists,pobs)) / sum(pobs)
    cv         = (var_pond**0.5) / media_pond * 100

    # Zonas críticas
    criticas = sorted(
        [c for c in urbanas if c['pct_acceso'] < 90],
        key=lambda x: -x['pob']
    )

    return {
        'n_celdas':         len(urbanas),
        'pob_buen_acceso':  pob_buen_acceso,
        'pob_sin_acceso':   pob_sin_acceso,
        'pct_pob_acceso':   round(pob_buen_acceso / poblacion_total * 100, 1),
        'dist_media_pond':  round(media_pond, 0),
        'cv_equidad':       round(cv, 1),
        'n_criticas':       len(criticas),
        'zonas_criticas':   criticas[:5],
    }


def imprimir(ciudad_key, metricas):
    d = CIUDADES[ciudad_key]
    m = metricas
    c = d['censo']

    print(f"\n  RESULTADOS — {d['nombre']}")
    print(f"  {'Celdas urbanas':30} {m['n_celdas']}")
    print(f"  {'Pob. con buen acceso (>80%)':30} {m['pob_buen_acceso']:,}")
    print(f"  {'Pob. con acceso limitado':30} {m['pob_sin_acceso']:,}")
    print(f"  {'% con buen acceso':30} {m['pct_pob_acceso']}%")
    print(f"  {'Distancia media (pond. pob.)':30} {m['dist_media_pond']} m")
    print(f"  {'Coef. variación (equidad)':30} {m['cv_equidad']}%")

    nivel_eq = "✅ Alta" if m['cv_equidad'] < 30 else "⚠️ Media" if m['cv_equidad'] < 60 else "❌ Baja"
    print(f"  {'Equidad espacial':30} {nivel_eq}")

    # Vulnerabilidad combinada
    score = 0
    if c['piso_tierra'] > 5:       score += 1
    if c['sin_agua_red'] > 10:     score += 1
    if c['hacinamiento'] > 7:      score += 1
    if m['pct_pob_acceso'] < 90:   score += 2
    if m['cv_equidad'] > 60:       score += 2
    nivel_v = "🟢 BAJO" if score<=1 else "🟡 MEDIO" if score<=3 else "🔴 ALTO"
    print(f"\n  Índice Vulnerabilidad Ambiental: {score}/7 → {nivel_v}")

    if m['zonas_criticas']:
        print(f"\n  TOP ZONAS PRIORITARIAS:")
        for i, z in enumerate(m['zonas_criticas'], 1):
            print(f"  {i}. ({z['centroid_lat']:.4f}, {z['centroid_lon']:.4f})"
                  f" | acceso {z['pct_acceso']}% | dist {z['dist_prom_m']}m"
                  f" | ~{z['pob']:,} hab")


# ============================================================
# EJECUCIÓN
# ============================================================

salida = {}

for key in CIUDADES:
    try:
        celdas   = analizar_ciudad_gee(key)
        metricas = calcular_metricas(celdas, CIUDADES[key]['poblacion'])
        if metricas:
            imprimir(key, metricas)
            salida[key] = {
                'pct_pob_acceso':  metricas['pct_pob_acceso'],
                'dist_media_pond': metricas['dist_media_pond'],
                'cv_equidad':      metricas['cv_equidad'],
                'n_criticas':      metricas['n_criticas'],
                'zonas_criticas': [
                    {'lat': z['centroid_lat'], 'lon': z['centroid_lon'],
                     'pct_acceso': z['pct_acceso'], 'dist_m': z['dist_prom_m'],
                     'pob': z['pob']}
                    for z in metricas['zonas_criticas']
                ],
                'censo': CIUDADES[key]['censo'],
            }
    except Exception as e:
        print(f"\n❌ Error en {key}: {e}")

# Guardar JSON para el dashboard
if salida:
    out = os.path.join(os.path.dirname(__file__), 'datos_censo_verde.json')
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Guardado: datos_censo_verde.json")

print("\nListo.")
