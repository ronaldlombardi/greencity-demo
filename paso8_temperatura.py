import ee
import os

# ============================================================
# PASO 8: TEMPERATURA SUPERFICIAL (LST) - Isla de Calor Urbano
# Fuente: Landsat 8/9 (USGS) - Banda TIRS B10
# Resolución: 30m | Fórmula: Jiménez-Muñoz et al.
# ============================================================

ruta = os.path.join(os.path.dirname(__file__), 'service_account.json')
credenciales = ee.ServiceAccountCredentials(email=None, key_file=ruta)
ee.Initialize(credentials=credenciales, project='my-project-1697-1767615452939')
print("Conectado a Earth Engine.\n")

# ============================================================
# CONFIGURACIÓN
# ============================================================

CIUDADES = {
    'villamaria': {
        'nombre': 'Villa María - Villa Nueva',
        'coords': [[-63.28, -32.39], [-63.20, -32.39], [-63.20, -32.44], [-63.28, -32.44]],
    },
    'sanfrancisco': {
        'nombre': 'San Francisco',
        'coords': [[-62.105, -31.405], [-62.055, -31.405], [-62.055, -31.450], [-62.105, -31.450]],
    }
}

# Período de análisis: verano austral (diciembre-febrero)
FECHA_INICIO = '2023-12-01'
FECHA_FIN    = '2024-03-01'

# ============================================================
# FUNCIÓN PRINCIPAL: calcular LST desde Landsat 8/9
# ============================================================

def calcular_lst(imagen):
    """
    Convierte la banda térmica B10 de Landsat 8/9 a temperatura en °C.
    Método: corrección por emisividad usando NDVI (Sobrino et al.)
    """
    # NDVI para emisividad
    ndvi = imagen.normalizedDifference(['SR_B5', 'SR_B4']).rename('NDVI')

    # Emisividad (método NDVI threshold)
    pv   = ndvi.subtract(0.2).divide(0.3).pow(2).clamp(0, 1)   # Proporción de vegetación
    em   = pv.multiply(0.004).add(0.986).rename('emissividad')   # Emisividad

    # Temperatura de brillo en Kelvin (escala Landsat Collection 2)
    tb = imagen.select('ST_B10').multiply(0.00341802).add(149.0).rename('TB_kelvin')

    # Corrección por emisividad → LST en Kelvin
    lst_k = tb.divide(
        tb.divide(14388).multiply(ee.Image(10.895).log()).add(1).multiply(em.log()).add(1)
    ).rename('LST_kelvin')

    # Convertir a Celsius
    lst_c = lst_k.subtract(273.15).rename('LST_celsius')

    return imagen.addBands([ndvi, em, lst_c])


def analizar_ciudad(ciudad_key):
    ciudad = CIUDADES[ciudad_key]
    area   = ee.Geometry.Polygon([ciudad['coords']])

    print(f"\n{'='*55}")
    print(f"  {ciudad['nombre']}")
    print(f"{'='*55}")

    # Colección Landsat 8/9 - Surface Temperature producto C2 L2
    coleccion = (
        ee.ImageCollection('LANDSAT/LC08/C02/T1_L2')
        .merge(ee.ImageCollection('LANDSAT/LC09/C02/T1_L2'))
        .filterDate(FECHA_INICIO, FECHA_FIN)
        .filterBounds(area)
        .filter(ee.Filter.lt('CLOUD_COVER', 20))
        .map(calcular_lst)
    )

    cantidad = coleccion.size().getInfo()
    print(f"  Imágenes disponibles (nubosidad <20%): {cantidad}")

    if cantidad == 0:
        print("  ⚠️  Sin imágenes. Probá ampliar el rango de fechas.")
        return None

    # Mediana de LST para el período
    lst_mediana = coleccion.select('LST_celsius').median().clip(area)

    # WorldCover para separar urbano de vegetado
    worldcover    = ee.Image('ESA/WorldCover/v100/2020').clip(area)
    mask_urbano   = worldcover.eq(50)     # Zona edificada
    mask_verde    = worldcover.eq(10).Or(worldcover.eq(30))  # Árboles + pastizales

    # LST por tipo de cobertura
    lst_urbano = lst_mediana.updateMask(mask_urbano)
    lst_verde  = lst_mediana.updateMask(mask_verde)

    def media(img, area):
        r = img.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=area,
            scale=30,
            maxPixels=1e9
        ).getInfo()
        v = list(r.values())[0]
        return round(v, 2) if v is not None else None

    def percentil(img, area, p):
        r = img.reduceRegion(
            reducer=ee.Reducer.percentile([p]),
            geometry=area,
            scale=30,
            maxPixels=1e9
        ).getInfo()
        v = list(r.values())[0]
        return round(v, 2) if v is not None else None

    t_media_total  = media(lst_mediana, area)
    t_media_urbano = media(lst_urbano, area)
    t_media_verde  = media(lst_verde, area)
    t_max          = percentil(lst_mediana, area, 95)
    t_min          = percentil(lst_mediana, area, 5)

    # Diferencial isla de calor (urbano vs verde)
    delta_uhi = None
    if t_media_urbano and t_media_verde:
        delta_uhi = round(t_media_urbano - t_media_verde, 2)

    print(f"\n  TEMPERATURA SUPERFICIAL (verano {FECHA_INICIO[:4]}-{FECHA_FIN[:4]})")
    print(f"  {'Temperatura media general':35} {t_media_total}°C")
    print(f"  {'Temperatura media zona urbana':35} {t_media_urbano}°C")
    print(f"  {'Temperatura media zona verde':35} {t_media_verde}°C")
    print(f"  {'Percentil 95 (puntos más calientes)':35} {t_max}°C")
    print(f"  {'Percentil 5 (puntos más frescos)':35} {t_min}°C")

    if delta_uhi is not None:
        signo = '+' if delta_uhi > 0 else ''
        print(f"\n  ISLA DE CALOR URBANO (UHI)")
        print(f"  Diferencia urbano - verde: {signo}{delta_uhi}°C")
        if delta_uhi > 3:
            print("  ⚠️  Efecto isla de calor ALTO (>3°C)")
        elif delta_uhi > 1.5:
            print("  ⚠️  Efecto isla de calor MODERADO (1.5-3°C)")
        else:
            print("  ✅  Efecto isla de calor BAJO (<1.5°C)")

    # Análisis por zonas (4 cuadrantes) — solo para Villa María
    if ciudad_key == 'villamaria':
        print(f"\n  TEMPERATURA POR ZONAS")
        zonas = {
            'Noroeste (VM centro-N)': ee.Geometry.Polygon([[-63.28,-32.39],[-63.24,-32.39],[-63.24,-32.415],[-63.28,-32.415]]),
            'Noreste  (VN norte)   ': ee.Geometry.Polygon([[-63.24,-32.39],[-63.20,-32.39],[-63.20,-32.415],[-63.24,-32.415]]),
            'Suroeste (VM sur)     ': ee.Geometry.Polygon([[-63.28,-32.415],[-63.24,-32.415],[-63.24,-32.44],[-63.28,-32.44]]),
            'Sureste  (VN sur)     ': ee.Geometry.Polygon([[-63.24,-32.415],[-63.20,-32.415],[-63.20,-32.44],[-63.24,-32.44]]),
        }
        for nombre, geom in zonas.items():
            t = media(lst_mediana.clip(geom), geom)
            marca = ' 🔴' if t and t > (t_media_total + 1.5) else (' ✅' if t and t < (t_media_total - 1) else '')
            print(f"    {nombre}: {t}°C{marca}")

    # Correlación NDVI - Temperatura
    print(f"\n  CORRELACIÓN NDVI ↔ LST")
    ndvi_mediano = coleccion.select('NDVI').median().clip(area)

    # Zonas de alto verde (NDVI > 0.4)
    mask_alto_ndvi = ndvi_mediano.gt(0.4)
    t_alto_ndvi    = media(lst_mediana.updateMask(mask_alto_ndvi), area)
    t_bajo_ndvi    = media(lst_mediana.updateMask(ndvi_mediano.lt(0.2)), area)

    print(f"    LST donde NDVI > 0.4 (verde denso): {t_alto_ndvi}°C")
    print(f"    LST donde NDVI < 0.2 (suelo/asfalto): {t_bajo_ndvi}°C")
    if t_alto_ndvi and t_bajo_ndvi:
        diff = round(t_bajo_ndvi - t_alto_ndvi, 2)
        print(f"    Enfriamiento por vegetación densa:  {diff}°C menos")

    return {
        'ciudad': ciudad['nombre'],
        't_media': t_media_total,
        't_urbano': t_media_urbano,
        't_verde': t_media_verde,
        't_max_p95': t_max,
        't_min_p5': t_min,
        'delta_uhi': delta_uhi,
        't_alto_ndvi': t_alto_ndvi,
        't_bajo_ndvi': t_bajo_ndvi,
    }


# ============================================================
# EJECUCIÓN
# ============================================================

resultados = {}

for key in CIUDADES:
    try:
        r = analizar_ciudad(key)
        if r:
            resultados[key] = r
    except Exception as e:
        print(f"\n  ❌ Error en {key}: {e}")

# Comparativa final
if len(resultados) == 2:
    vm = resultados.get('villamaria', {})
    sf = resultados.get('sanfrancisco', {})

    print(f"\n{'='*55}")
    print("  COMPARATIVA: Villa María vs San Francisco")
    print(f"{'='*55}")
    print(f"  {'Indicador':<30} {'Villa María':>12} {'San Francisco':>13}")
    print(f"  {'-'*55}")

    indicadores = [
        ('Temp. media general (°C)', 't_media'),
        ('Temp. zona urbana (°C)',   't_urbano'),
        ('Temp. zona verde (°C)',    't_verde'),
        ('Isla de calor ΔT (°C)',    'delta_uhi'),
        ('Máx P95 (°C)',             't_max_p95'),
    ]

    for label, key in indicadores:
        vv = vm.get(key, '-')
        sv = sf.get(key, '-')
        print(f"  {label:<30} {str(vv):>12} {str(sv):>13}")

    print(f"\n  Nota: Valores más altos de ΔT = mayor isla de calor.")
    print(f"  San Francisco (arbolado 1.6%) debería mostrar ΔT mayor que")
    print(f"  Villa María (arbolado 8.2%) — confirmando el impacto del verde.")

print(f"\n{'='*55}")
print("  Módulo LST completado.")
print(f"{'='*55}")
