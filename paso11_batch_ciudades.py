"""
paso11_batch_ciudades.py
========================
Analiza TODAS las ciudades del JSON con GEE en una sola corrida.
Genera resultados_ciudades.json con cobertura, accesibilidad y LST.

Correr con:
    python paso11_batch_ciudades.py

Tiempo estimado: 3-5 minutos para las 21 ciudades.
"""

import ee
import os
import json
import time

ruta = os.path.join(os.path.dirname(__file__), 'service_account.json')
credenciales = ee.ServiceAccountCredentials(email=None, key_file=ruta)
ee.Initialize(credentials=credenciales, project='my-project-1697-1767615452939')
print("Conectado a Earth Engine.\n")

# Cargar configuración de ciudades
with open(os.path.join(os.path.dirname(__file__), 'datos_ciudades.json'), encoding='utf-8') as f:
    CIUDADES = json.load(f)

# ============================================================
# FUNCIONES DE ANÁLISIS
# ============================================================

def analizar_cobertura(area):
    wc    = ee.Image('ESA/WorldCover/v100/2020').clip(area)
    total = ee.Image.constant(1).reduceRegion(ee.Reducer.sum(), area, 10, maxPixels=1e9)
    total_v = list(total.getInfo().values())[0] or 1

    def pct(clase):
        r = wc.eq(clase).reduceRegion(ee.Reducer.sum(), area, 10, maxPixels=1e9).getInfo()
        v = list(r.values())[0] or 0
        return round(v / total_v * 100, 1)

    return {
        'arboles':    pct(10),
        'arbustos':   pct(20),
        'pastizales': pct(30),
        'cultivos':   pct(40),
        'edificado':  pct(50),
        'suelo':      pct(60),
        'agua':       pct(80),
    }


def analizar_accesibilidad(area):
    wc    = ee.Image('ESA/WorldCover/v100/2020').clip(area)
    verde = wc.eq(10).Or(wc.eq(20)).Or(wc.eq(30)).selfMask()
    edif  = wc.eq(50).selfMask()
    dist  = verde.fastDistanceTransform(1000).sqrt().multiply(10)
    dist_edif = dist.updateMask(edif)

    def suma(img):
        r = img.reduceRegion(ee.Reducer.sum(), area, 10, maxPixels=1e9).getInfo()
        return list(r.values())[0] or 0
    def media(img):
        r = img.reduceRegion(ee.Reducer.mean(), area, 10, maxPixels=1e9).getInfo()
        return list(r.values())[0]

    total_edif = suma(edif) or 1
    cerc       = suma(dist_edif.lt(300))
    dist_prom  = media(dist_edif)

    # Rangos
    r0   = suma(dist_edif.lt(100))
    r100 = suma(dist_edif.gte(100).And(dist_edif.lt(300)).updateMask(edif))
    r300 = suma(dist_edif.gte(300).And(dist_edif.lt(500)).updateMask(edif))
    r500 = suma(dist_edif.gte(500).updateMask(edif))

    return {
        'acceso':     round(cerc / total_edif * 100, 1),
        'dist_prom':  round(dist_prom, 0) if dist_prom else None,
        'm2_hab_sat': None,  # se calcula después con pop
        'r_0_100':    round(r0 / total_edif * 100, 1),
        'r_100_300':  round(r100 / total_edif * 100, 1),
        'r_300_500':  round(r300 / total_edif * 100, 1),
        'r_500_mas':  round(r500 / total_edif * 100, 1),
        'total_edif_pix': total_edif,
    }


def analizar_lst(area, fecha_inicio='2023-12-01', fecha_fin='2024-03-01'):
    def lst_fn(img):
        ndvi = img.normalizedDifference(['SR_B5','SR_B4']).rename('NDVI')
        pv   = ndvi.subtract(0.2).divide(0.3).pow(2).clamp(0,1)
        em   = pv.multiply(0.004).add(0.986)
        tb   = img.select('ST_B10').multiply(0.00341802).add(149.0)
        lst_k = tb.divide(tb.divide(14388).multiply(ee.Image(10.895).log()).add(1).multiply(em.log()).add(1))
        return img.addBands(lst_k.subtract(273.15).rename('LST'))

    def add_ndvi(img):
        return img.addBands(
            img.normalizedDifference(['SR_B5','SR_B4']).rename('NDVI')
        )

    col_base = (ee.ImageCollection('LANDSAT/LC08/C02/T1_L2')
                .merge(ee.ImageCollection('LANDSAT/LC09/C02/T1_L2'))
                .filterDate(fecha_inicio, fecha_fin)
                .filterBounds(area)
                .filter(ee.Filter.lt('CLOUD_COVER', 20)))

    col      = col_base.map(lst_fn)
    col_ndvi = col_base.map(add_ndvi)

    n = col.size().getInfo()
    if n == 0:
        return None

    lst_med  = col.select('LST').median().clip(area)
    ndvi_med = col_ndvi.select('NDVI').median().clip(area)
    wc       = ee.Image('ESA/WorldCover/v100/2020').clip(area)
    m_urb    = wc.eq(50)
    m_vrd    = wc.eq(10).Or(wc.eq(30))

    def media(img):
        r = img.reduceRegion(ee.Reducer.mean(), area, 30, maxPixels=1e9).getInfo()
        v = list(r.values())[0]
        return round(v, 2) if v else None
    def p95(img):
        r = img.reduceRegion(ee.Reducer.percentile([95]), area, 30, maxPixels=1e9).getInfo()
        v = list(r.values())[0]
        return round(v, 2) if v else None

    t_med  = media(lst_med)
    t_urb  = media(lst_med.updateMask(m_urb))
    t_vrd  = media(lst_med.updateMask(m_vrd))
    t_p95  = p95(lst_med)
    t_nalto = media(lst_med.updateMask(ndvi_med.gt(0.4))) if ndvi_med else None
    t_nbajo = media(lst_med.updateMask(ndvi_med.lt(0.2))) if ndvi_med else None

    return {
        'imagenes':    n,
        'tMedia':      t_med,
        'tUrbano':     t_urb,
        'tVerde':      t_vrd,
        'tP95':        t_p95,
        'tP5':         None,
        'deltaUHI':    round(t_urb - t_vrd, 2) if (t_urb and t_vrd) else None,
        'tNdviAlto':   t_nalto,
        'tNdviBajo':   t_nbajo,
        'enfriamiento': round(t_nbajo - t_nalto, 2) if (t_nalto and t_nbajo) else None,
        'zonas':       [],
    }


# ============================================================
# BATCH
# ============================================================

resultados = {}
errores    = []

total = len(CIUDADES)
for i, (key, ciudad) in enumerate(CIUDADES.items(), 1):
    print(f"\n[{i}/{total}] {ciudad['nombre']}...")
    t0 = time.time()

    try:
        area = ee.Geometry.Polygon([ciudad['coords_area']])

        print(f"  → Cobertura...", end=' ')
        cob = analizar_cobertura(area)
        print(f"OK (arbolado: {cob['arboles']}%)")

        print(f"  → Accesibilidad...", end=' ')
        acc = analizar_accesibilidad(area)
        pob = ciudad['poblacion']
        verde_m2 = (cob['arboles'] + cob['arbustos'] + cob['pastizales']) / 100 * ciudad['area_km2'] * 1e6
        acc['m2_hab_sat'] = round(verde_m2 / pob, 1)
        print(f"OK (acceso: {acc['acceso']}%, dist: {acc['dist_prom']}m)")

        print(f"  → Temperatura LST...", end=' ')
        lst = analizar_lst(area)
        if lst:
            print(f"OK ({lst['imagenes']} imgs, media: {lst['tMedia']}°C, UHI: {lst['deltaUHI']}°C)")
        else:
            print("Sin imágenes disponibles")

        resultados[key] = {
            'nombre':    ciudad['nombre'],
            'dept':      ciudad.get('dept', ''),
            'poblacion': ciudad['poblacion'],
            'area_km2':  ciudad['area_km2'],
            'cobertura': cob,
            'acceso':    acc,
            'lst':       lst,
        }

        elapsed = round(time.time() - t0, 1)
        print(f"  ✅ {elapsed}s")

    except Exception as e:
        print(f"  ❌ Error: {e}")
        errores.append({'ciudad': key, 'error': str(e)})
        continue

# ============================================================
# GUARDAR
# ============================================================

out = os.path.join(os.path.dirname(__file__), 'resultados_ciudades.json')
with open(out, 'w', encoding='utf-8') as f:
    json.dump(resultados, f, ensure_ascii=False, indent=2)

print(f"\n{'='*55}")
print(f"  Procesadas: {len(resultados)}/{total} ciudades")
if errores:
    print(f"  Errores: {len(errores)}")
    for e in errores:
        print(f"    - {e['ciudad']}: {e['error']}")
print(f"  Guardado en: resultados_ciudades.json")
print(f"{'='*55}")

# Resumen rápido
if resultados:
    print(f"\n  RANKING ARBOLADO (de mayor a menor):")
    ranking = sorted(resultados.items(), key=lambda x: -x[1]['cobertura']['arboles'])
    for k, r in ranking:
        arb = r['cobertura']['arboles']
        uhi = r['lst']['deltaUHI'] if r['lst'] else '-'
        print(f"  {r['nombre']:<35} arbolado: {arb:>5}%  UHI: {uhi}°C")
