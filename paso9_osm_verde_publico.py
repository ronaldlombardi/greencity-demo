"""
paso9_osm_verde_publico.py
==========================
Análisis de espacios verdes PÚBLICOS usando OpenStreetMap (API Overpass).

Diferencia clave respecto a WorldCover:
  WorldCover detecta TODO el verde (incluyendo patios privados, baldíos, cultivos).
  OSM identifica sólo los espacios CATALOGADOS como públicos: parques, plazas,
  jardines, canchas, arbolado de calles, etc.

Ejecutar:
    python paso9_osm_verde_publico.py

Dependencias:
    pip install requests shapely
"""

import requests
import json
import time
from shapely.geometry import Polygon, shape
from shapely.ops import unary_union

# ============================================================
# CONFIGURACIÓN
# ============================================================

CIUDADES = {
    'villamaria': {
        'nombre': 'Villa María - Villa Nueva',
        'poblacion': 120000,
        # bbox: sur, oeste, norte, este
        'bbox': (-32.44, -63.28, -32.39, -63.20),
    },
    'sanfrancisco': {
        'nombre': 'San Francisco',
        'poblacion': 62000,
        'bbox': (-31.450, -62.105, -31.405, -62.055),
    }
}

# Categorías OSM a consultar
# Ref: https://wiki.openstreetmap.org/wiki/Key:leisure
CATEGORIAS = {
    'Parques':           [('leisure', 'park')],
    'Plazas':            [('leisure', 'garden'), ('place', 'square')],
    'Canchas/Deportivo': [('leisure', 'pitch'), ('leisure', 'sports_centre'),
                          ('leisure', 'stadium')],
    'Juegos infantiles': [('leisure', 'playground')],
    'Áreas verdes':      [('landuse', 'grass'), ('landuse', 'meadow'),
                          ('landuse', 'recreation_ground')],
    'Naturaleza':        [('natural', 'wood'), ('natural', 'scrub'),
                          ('landuse', 'forest')],
    'Cementerios':       [('landuse', 'cemetery')],
}

OVERPASS_ENDPOINTS = [
    'https://overpass-api.de/api/interpreter',
    'https://overpass.kumi.systems/api/interpreter',
    'https://maps.mail.ru/osm/tools/overpass/api/interpreter',
]

# ============================================================
# CONSULTA OVERPASS
# ============================================================

def construir_query(bbox, categorias):
    """Genera la query Overpass QL para todas las categorías."""
    sur, oeste, norte, este = bbox
    bbox_str = f"{sur},{oeste},{norte},{este}"

    filtros = []
    for cat, pares in categorias.items():
        for key, val in pares:
            filtros.append(f'  way[{key}={val}]({bbox_str});')
            filtros.append(f'  relation[{key}={val}]({bbox_str});')

    return f"""
[out:json][timeout:60];
(
{chr(10).join(filtros)}
);
out body;
>;
out skel qt;
""".strip()


def consultar_overpass(query, verbose=True):
    """Envía query a Overpass con fallback entre endpoints."""
    for endpoint in OVERPASS_ENDPOINTS:
        try:
            if verbose:
                print(f"  Consultando {endpoint.split('/')[2]}...", end=' ')
            resp = requests.post(
                endpoint,
                data={'data': query},
                headers={'User-Agent': 'GreenCityResearch/1.0 (educacion)'},
                timeout=60
            )
            if resp.status_code == 200:
                data = resp.json()
                if verbose:
                    print(f"OK ({len(data['elements'])} elementos)")
                return data
            else:
                if verbose:
                    print(f"Error {resp.status_code}")
        except Exception as e:
            if verbose:
                print(f"Fallo ({e})")
        time.sleep(1)
    return None


# ============================================================
# PROCESAMIENTO GEOMÉTRICO
# ============================================================

def elementos_a_geometrias(data):
    """
    Convierte la respuesta Overpass en polígonos Shapely.
    Devuelve lista de dicts con {geometry, tags, tipo, nombre, area_m2}.
    """
    # Índice de nodos por ID
    nodos = {
        el['id']: (el['lon'], el['lat'])
        for el in data['elements']
        if el['type'] == 'node'
    }

    geometrias = []

    for el in data['elements']:
        if el['type'] not in ('way', 'relation'):
            continue
        tags = el.get('tags', {})
        nombre = tags.get('name', '(sin nombre)')
        tipo = (
            tags.get('leisure') or
            tags.get('landuse') or
            tags.get('natural') or
            tags.get('place') or
            'desconocido'
        )

        # Determinar categoría
        cat = 'Otros'
        for cat_nombre, pares in CATEGORIAS.items():
            for key, val in pares:
                if tags.get(key) == val:
                    cat = cat_nombre
                    break

        # Construir polígono desde nodos del way
        if el['type'] == 'way' and 'nodes' in el:
            coords = [nodos[nid] for nid in el['nodes'] if nid in nodos]
            if len(coords) >= 3:
                try:
                    poly = Polygon(coords)
                    if poly.is_valid and poly.area > 0:
                        # Convertir grados a m² aprox. (latitud ~32°S)
                        area_m2 = poly.area * 111320 * 111320 * 0.848
                        geometrias.append({
                            'id': el['id'],
                            'geometry': poly,
                            'tags': tags,
                            'tipo': tipo,
                            'categoria': cat,
                            'nombre': nombre,
                            'area_m2': area_m2,
                        })
                except Exception:
                    pass

    return geometrias


def calcular_area_total(geometrias):
    """Unión de polígonos para evitar doble conteo de superposiciones."""
    if not geometrias:
        return 0
    try:
        union = unary_union([g['geometry'] for g in geometrias])
        # Conversión grados² → m²
        return union.area * 111320 * 111320 * 0.848
    except Exception:
        return sum(g['area_m2'] for g in geometrias)


# ============================================================
# ANÁLISIS PRINCIPAL
# ============================================================

def analizar_ciudad(ciudad_key):
    ciudad = CIUDADES[ciudad_key]
    print(f"\n{'='*58}")
    print(f"  {ciudad['nombre']}")
    print(f"{'='*58}")

    query = construir_query(ciudad['bbox'], CATEGORIAS)
    data  = consultar_overpass(query)

    if not data or not data.get('elements'):
        print("  ❌ No se obtuvieron datos de OSM.")
        return None

    geometrias = elementos_a_geometrias(data)
    print(f"\n  Elementos procesados: {len(geometrias)}")

    if not geometrias:
        print("  ⚠️  No se pudieron construir geometrías.")
        return None

    # ---- Por categoría ----
    print(f"\n  {'CATEGORÍA':<25} {'Elementos':>9} {'Área (ha)':>10}")
    print(f"  {'-'*46}")

    por_categoria = {}
    for g in geometrias:
        cat = g['categoria']
        if cat not in por_categoria:
            por_categoria[cat] = []
        por_categoria[cat].append(g)

    for cat, items in sorted(por_categoria.items(), key=lambda x: -len(x[1])):
        area_ha = sum(i['area_m2'] for i in items) / 10000
        print(f"  {cat:<25} {len(items):>9} {area_ha:>9.1f} ha")

    # ---- Totales ----
    area_total_m2 = calcular_area_total(geometrias)
    area_total_ha = area_total_m2 / 10000
    pob = ciudad['poblacion']
    m2_hab = area_total_m2 / pob

    print(f"\n  {'TOTAL (sin doble conteo)':<25} {len(geometrias):>9} {area_total_ha:>9.1f} ha")

    print(f"\n  INDICADORES OMS")
    print(f"  {'m² verde público / habitante':35} {m2_hab:.1f} m²/hab")
    print(f"  {'Referencia OMS mínima':35} 9 m²/hab")
    print(f"  {'Referencia OMS óptima':35} 15 m²/hab")

    if m2_hab >= 15:
        print(f"  ✅ Por encima del umbral óptimo OMS")
    elif m2_hab >= 9:
        print(f"  ✅ Dentro del rango recomendado OMS")
    elif m2_hab >= 5:
        print(f"  ⚠️  Por debajo del mínimo OMS")
    else:
        print(f"  ❌ Muy por debajo del mínimo OMS")

    # ---- Top espacios por área ----
    top = sorted(geometrias, key=lambda x: -x['area_m2'])[:10]
    print(f"\n  TOP 10 ESPACIOS VERDES PÚBLICOS (por superficie)")
    print(f"  {'Nombre':<30} {'Tipo':<18} {'Área':>8}")
    print(f"  {'-'*58}")
    for g in top:
        area_str = (
            f"{g['area_m2']/10000:.2f} ha"
            if g['area_m2'] >= 10000
            else f"{g['area_m2']:.0f} m²"
        )
        nombre_corto = g['nombre'][:28]
        print(f"  {nombre_corto:<30} {g['tipo']:<18} {area_str:>8}")

    return {
        'ciudad': ciudad['nombre'],
        'elementos': len(geometrias),
        'area_total_ha': area_total_ha,
        'm2_hab': m2_hab,
        'por_categoria': {k: len(v) for k, v in por_categoria.items()},
        'top10': top,
    }


# ============================================================
# COMPARATIVA WORLDCOVER vs OSM
# ============================================================

def comparativa_worldcover_osm(resultado_wc_ha, resultado_osm_ha, poblacion, ciudad):
    """
    Imprime la diferencia entre verde total (WorldCover) y verde público (OSM).
    resultado_wc_ha: hectáreas de verde total del WorldCover
    resultado_osm_ha: hectáreas de verde público de OSM
    """
    print(f"\n  COMPARATIVA WORLDCOVER vs OSM — {ciudad}")
    print(f"  {'Verde total detectado (WorldCover)':40} {resultado_wc_ha:.0f} ha")
    print(f"  {'Verde público catalogado (OSM)':40} {resultado_osm_ha:.1f} ha")

    if resultado_wc_ha > 0:
        pct_publico = (resultado_osm_ha / resultado_wc_ha) * 100
        print(f"  {'% del verde total que es público':40} {pct_publico:.1f}%")
        print(f"  {'Verde privado/no catalogado':40} {resultado_wc_ha - resultado_osm_ha:.0f} ha")

    m2_sat = (resultado_wc_ha * 10000) / poblacion
    m2_osm = (resultado_osm_ha * 10000) / poblacion
    print(f"\n  m²/hab satelital (WorldCover): {m2_sat:.1f}")
    print(f"  m²/hab público  (OSM):         {m2_osm:.1f}")
    print(f"  ⚠️  La diferencia ({m2_sat - m2_osm:.1f} m²/hab) es verde que")
    print(f"      los vecinos posiblemente NO pueden acceder libremente.")


# ============================================================
# EJECUCIÓN
# ============================================================

if __name__ == '__main__':
    resultados = {}

    for key in CIUDADES:
        try:
            r = analizar_ciudad(key)
            if r:
                resultados[key] = r
        except Exception as e:
            print(f"\n  ❌ Error procesando {key}: {e}")

    # Comparativa final entre ciudades
    if len(resultados) == 2:
        vm = resultados['villamaria']
        sf = resultados['sanfrancisco']

        print(f"\n{'='*58}")
        print("  COMPARATIVA ENTRE CIUDADES")
        print(f"{'='*58}")
        print(f"  {'Indicador':<35} {'Villa María':>12} {'San Francisco':>10}")
        print(f"  {'-'*58}")

        indicadores = [
            ('Espacios catalogados (OSM)', 'elementos'),
            ('Área verde pública (ha)',     'area_total_ha'),
            ('m² verde público / hab',      'm2_hab'),
        ]
        for label, key in indicadores:
            vv = vm.get(key, '-')
            sv = sf.get(key, '-')
            if isinstance(vv, float):
                vv = f"{vv:.1f}"
                sv = f"{sv:.1f}"
            print(f"  {label:<35} {str(vv):>12} {str(sv):>10}")

        print(f"\n  Referencia OMS: 9 m²/hab mínimo, 15 m²/hab óptimo")

    # Ejemplo de comparativa con WorldCover
    # (usar los valores reales de tu paso5_worldcover.py)
    print(f"\n{'='*58}")
    print("  EJEMPLO DE COMPARATIVA WorldCover vs OSM")
    print(f"{'='*58}")
    if 'villamaria' in resultados:
        comparativa_worldcover_osm(
            resultado_wc_ha=1120,   # ← reemplazar con valor real de paso5
            resultado_osm_ha=resultados['villamaria']['area_total_ha'],
            poblacion=120000,
            ciudad="Villa María - Villa Nueva"
        )

    print(f"\n{'='*58}")
    print("  Módulo OSM completado.")
    print(f"{'='*58}\n")
