"""
modulo_osm.py
=============
Módulo reutilizable OSM para GreenCity.
Consulta la API Overpass y renderiza el análisis de verde público en Streamlit.

Uso en dashboard:
    from modulo_osm import cargar_osm, render_osm
    datos = cargar_osm(bbox, poblacion)
    render_osm(datos, m2_hab_satelital)
"""

import requests
import time
import streamlit as st
from shapely.geometry import Polygon
from shapely.ops import unary_union


# ============================================================
# CONSTANTES
# ============================================================

OVERPASS_ENDPOINTS = [
    'https://overpass-api.de/api/interpreter',
    'https://overpass.kumi.systems/api/interpreter',
    'https://maps.mail.ru/osm/tools/overpass/api/interpreter',
]

CATEGORIAS = {
    'Parques':           [('leisure', 'park')],
    'Plazas / jardines': [('leisure', 'garden'), ('place', 'square')],
    'Deportivo':         [('leisure', 'pitch'), ('leisure', 'sports_centre')],
    'Juegos':            [('leisure', 'playground')],
    'Áreas verdes':      [('landuse', 'grass'), ('landuse', 'recreation_ground'),
                          ('landuse', 'meadow')],
    'Naturaleza':        [('natural', 'wood'), ('landuse', 'forest')],
    'Cementerios':       [('landuse', 'cemetery')],
}

COLORES_CAT = {
    'Parques':           '#2e7d32',
    'Plazas / jardines': '#66bb6a',
    'Deportivo':         '#1565c0',
    'Juegos':            '#f57f17',
    'Áreas verdes':      '#558b2f',
    'Naturaleza':        '#1b5e20',
    'Cementerios':       '#78909c',
}


# ============================================================
# CONSULTA OVERPASS
# ============================================================

def _construir_query(bbox):
    sur, oeste, norte, este = bbox
    bbox_str = f"{sur},{oeste},{norte},{este}"
    filtros = []
    for pares in CATEGORIAS.values():
        for key, val in pares:
            filtros.append(f'  way[{key}={val}]({bbox_str});')
            filtros.append(f'  relation[{key}={val}]({bbox_str});')
    return f"[out:json][timeout:60];\n(\n" + "\n".join(filtros) + "\n);\nout body;\n>;\nout skel qt;"


def _consultar_overpass(query):
    for endpoint in OVERPASS_ENDPOINTS:
        try:
            r = requests.post(
                endpoint,
                data={'data': query},
                headers={'User-Agent': 'GreenCityResearch/1.0'},
                timeout=60,
            )
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        time.sleep(0.5)
    return None


# ============================================================
# PROCESAMIENTO
# ============================================================

def _procesar_elementos(data):
    nodos = {
        el['id']: (el['lon'], el['lat'])
        for el in data['elements']
        if el['type'] == 'node'
    }
    geometrias = []
    for el in data['elements']:
        if el['type'] != 'way' or 'nodes' not in el:
            continue
        tags = el.get('tags', {})
        tipo = (tags.get('leisure') or tags.get('landuse') or
                tags.get('natural') or tags.get('place') or '?')
        nombre = tags.get('name', '(sin nombre)')
        cat = 'Otros'
        for cat_nombre, pares in CATEGORIAS.items():
            for key, val in pares:
                if tags.get(key) == val:
                    cat = cat_nombre
                    break
        coords = [nodos[n] for n in el['nodes'] if n in nodos]
        if len(coords) < 3:
            continue
        try:
            poly = Polygon(coords)
            if poly.is_valid and poly.area > 0:
                area_m2 = poly.area * 111320 * 111320 * 0.848
                geometrias.append({
                    'id': el['id'],
                    'geometry': poly,
                    'tags': tags,
                    'tipo': tipo,
                    'categoria': cat,
                    'nombre': nombre,
                    'area_m2': area_m2,
                    'lat': poly.centroid.y,
                    'lon': poly.centroid.x,
                })
        except Exception:
            pass
    return geometrias


def _area_union(geometrias):
    if not geometrias:
        return 0
    try:
        return unary_union([g['geometry'] for g in geometrias]).area * 111320 * 111320 * 0.848
    except Exception:
        return sum(g['area_m2'] for g in geometrias)


# ============================================================
# FUNCIÓN PRINCIPAL (cacheada)
# ============================================================

@st.cache_data(show_spinner=False, ttl=86400)
def cargar_osm(bbox, poblacion):
    """
    Descarga y procesa espacios verdes públicos de OSM.

    Parámetros
    ----------
    bbox       : tuple (sur, oeste, norte, este)
    poblacion  : int

    Retorna
    -------
    dict con métricas y lista de espacios, o None si hay error.
    """
    query = _construir_query(bbox)
    data  = _consultar_overpass(query)

    if not data:
        return None

    geometrias = _procesar_elementos(data)
    if not geometrias:
        return {'elementos': 0, 'area_ha': 0, 'm2_hab': 0,
                'por_categoria': {}, 'espacios': [], 'error': None}

    area_total_m2 = _area_union(geometrias)
    area_ha       = area_total_m2 / 10000
    m2_hab        = area_total_m2 / poblacion

    por_cat = {}
    for g in geometrias:
        cat = g['categoria']
        if cat not in por_cat:
            por_cat[cat] = {'cantidad': 0, 'area_m2': 0}
        por_cat[cat]['cantidad'] += 1
        por_cat[cat]['area_m2']  += g['area_m2']

    top10 = sorted(geometrias, key=lambda x: -x['area_m2'])[:10]

    return {
        'elementos':     len(geometrias),
        'area_ha':       round(area_ha, 1),
        'm2_hab':        round(m2_hab, 1),
        'por_categoria': por_cat,
        'espacios':      geometrias,
        'top10':         top10,
        'error':         None,
    }


# ============================================================
# RENDER EN STREAMLIT
# ============================================================

def render_osm(datos_osm, m2_hab_satelital=None, poblacion=None):
    """
    Renderiza la sección OSM completa en el dashboard.

    Parámetros
    ----------
    datos_osm          : resultado de cargar_osm()
    m2_hab_satelital   : float, m²/hab calculados por WorldCover (para comparar)
    poblacion          : int (para mostrar contexto)
    """
    st.markdown("## 🗺️ Verde Público vs Verde Total")
    st.caption("Fuente: OpenStreetMap · API Overpass · Datos actualizados por la comunidad")

    if datos_osm is None:
        st.error("No se pudo conectar con la API de OpenStreetMap. Verificá tu conexión a internet.")
        _mostrar_ayuda_osm()
        return

    if datos_osm.get('elementos', 0) == 0:
        st.warning("No se encontraron espacios verdes catalogados en OSM para esta área.")
        st.info("Esto puede significar que la comunidad OSM local aún no los digitalizó — "
                "¡es una oportunidad para contribuir!")
        _mostrar_ayuda_osm()
        return

    d = datos_osm

    # ---- Métricas principales ----
    col1, col2, col3, col4 = st.columns(4)

    oms_color = (
        "normal" if d['m2_hab'] >= 9
        else "inverse"
    )

    with col1:
        st.metric("Espacios catalogados", d['elementos'])
    with col2:
        st.metric("Área verde pública", f"{d['area_ha']} ha")
    with col3:
        st.metric(
            "m² público / habitante",
            f"{d['m2_hab']} m²",
            delta="OMS mín: 9 m²",
            delta_color=oms_color
        )
    with col4:
        if m2_hab_satelital:
            diff = round(m2_hab_satelital - d['m2_hab'], 1)
            st.metric(
                "Verde privado estimado",
                f"{diff} m²/hab",
                delta="No accesible al público",
                delta_color="off"
            )

    st.markdown("---")

    # ---- Comparativa satelital vs OSM ----
    if m2_hab_satelital:
        st.markdown("### 📊 Verde total (satélite) vs Verde público (OSM)")
        pct_publico = min((d['m2_hab'] / m2_hab_satelital) * 100, 100) if m2_hab_satelital > 0 else 0

        col_bar, col_txt = st.columns([3, 1])
        with col_bar:
            # Barra comparativa visual
            st.markdown(
                f"""
                <div style='font-size:0.8em;color:var(--text-secondary);margin-bottom:4px'>
                  Verde total detectado por satélite (WorldCover)
                </div>
                <div style='background:#c8e6c9;border-radius:6px;height:22px;width:100%;position:relative'>
                  <div style='width:{pct_publico:.0f}%;background:#2e7d32;height:22px;
                              border-radius:6px;display:flex;align-items:center;padding-left:8px'>
                    <span style='color:white;font-size:0.75em;white-space:nowrap'>
                      {d['m2_hab']:.1f} m²/hab público ({pct_publico:.0f}%)
                    </span>
                  </div>
                </div>
                <div style='font-size:0.75em;color:var(--text-secondary);margin-top:2px'>
                  Restante ({100-pct_publico:.0f}%) = verde privado, baldíos, cultivos
                </div>
                """,
                unsafe_allow_html=True
            )
        with col_txt:
            st.metric("Satelital", f"{m2_hab_satelital:.1f} m²/hab")

        st.markdown("")

    # ---- OMS gauge ----
    st.markdown("### 🎯 Cumplimiento estándar OMS (9-15 m²/hab)")
    m2 = d['m2_hab']
    pct_oms = min((m2 / 15) * 100, 100)
    color_oms = "#4caf50" if m2 >= 15 else "#ff9800" if m2 >= 9 else "#f44336"
    label_oms = "✅ Cumple umbral óptimo" if m2 >= 15 else \
                "✅ Cumple mínimo OMS" if m2 >= 9 else \
                "⚠️ Por debajo del mínimo OMS"

    st.markdown(
        f"""
        <div style='display:flex;align-items:center;gap:12px;margin:8px 0'>
          <div style='flex:1;background:#e0e0e0;border-radius:8px;height:18px'>
            <div style='width:{pct_oms:.0f}%;background:{color_oms};
                        height:18px;border-radius:8px'></div>
          </div>
          <span style='font-size:0.85em;white-space:nowrap'>{label_oms}</span>
        </div>
        <div style='display:flex;justify-content:space-between;
                    font-size:0.75em;color:var(--text-secondary)'>
          <span>0 m²</span><span>9 m² (mínimo)</span><span>15 m² (óptimo)</span>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("---")

    # ---- Tabla por categoría ----
    st.markdown("### 🌿 Distribución por tipo de espacio")

    col_tabla, col_grafico = st.columns([1, 1])

    with col_tabla:
        filas = []
        for cat, datos in sorted(
            d['por_categoria'].items(),
            key=lambda x: -x[1]['area_m2']
        ):
            area_ha = datos['area_m2'] / 10000
            filas.append({
                'Tipo': cat,
                'Espacios': datos['cantidad'],
                'Área (ha)': f"{area_ha:.1f}",
            })
        if filas:
            import pandas as pd
            st.dataframe(
                pd.DataFrame(filas),
                hide_index=True,
                use_container_width=True
            )

    with col_grafico:
        if d['por_categoria']:
            chart_data = {
                cat: datos['area_m2'] / 10000
                for cat, datos in d['por_categoria'].items()
            }
            st.bar_chart(chart_data)

    st.markdown("---")

    # ---- Top 10 ----
    st.markdown("### 🏆 Los 10 espacios verdes más grandes")

    for i, esp in enumerate(d['top10'], 1):
        area_str = (
            f"{esp['area_m2']/10000:.2f} ha"
            if esp['area_m2'] >= 10000
            else f"{esp['area_m2']:.0f} m²"
        )
        color = COLORES_CAT.get(esp['categoria'], '#888')
        st.markdown(
            f"""
            <div style='display:flex;align-items:center;gap:10px;
                        padding:6px 0;border-bottom:1px solid var(--border)'>
              <span style='color:var(--text-secondary);min-width:20px;
                           font-size:0.85em'>#{i}</span>
              <div style='width:10px;height:10px;border-radius:50%;
                          background:{color};flex-shrink:0'></div>
              <span style='flex:1'>{esp['nombre']}</span>
              <span style='color:var(--text-secondary);font-size:0.85em'>
                {esp['tipo']}
              </span>
              <span style='font-weight:500;min-width:70px;text-align:right'>
                {area_str}
              </span>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("---")

    # ---- Mapa Folium con espacios OSM ----
    st.markdown("### 🗺️ Mapa de espacios verdes públicos")
    st.caption("Cada punto es un espacio catalogado en OpenStreetMap · Hacé clic para ver detalles")

    if d.get('espacios'):
        import folium as _folium
        from streamlit_folium import st_folium as _st_folium
        from folium import FeatureGroup as _FG

        lats = [g['lat'] for g in d['espacios']]
        lons = [g['lon'] for g in d['espacios']]
        center = [sum(lats) / len(lats), sum(lons) / len(lons)]

        m_osm = _folium.Map(location=center, zoom_start=14, tiles=None)

        _folium.TileLayer(
            tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}',
            attr='© Google', name='🌍 Híbrido Google', max_zoom=20, show=True,
        ).add_to(m_osm)
        _folium.TileLayer(
            tiles='https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
            attr='© OpenStreetMap contributors', name='🗺️ OpenStreetMap',
            max_zoom=19, show=False,
        ).add_to(m_osm)

        # Grupos por categoría
        grupos = {cat: _FG(name=f"🌿 {cat}", show=True) for cat in COLORES_CAT}

        for g in d['espacios']:
            cat   = g['categoria']
            color = COLORES_CAT.get(cat, '#888888')
            area_str = (
                f"{g['area_m2']/10000:.2f} ha"
                if g['area_m2'] >= 10000
                else f"{g['area_m2']:.0f} m²"
            )
            _folium.CircleMarker(
                location=[g['lat'], g['lon']],
                radius=5, color=color, weight=1.5,
                fill=True, fill_color=color, fill_opacity=0.75,
                tooltip=f"{g['nombre']} — {cat}",
                popup=_folium.Popup(
                    f"<b>{g['nombre']}</b><br>Tipo: {cat}<br>Área: {area_str}",
                    max_width=200,
                ),
            ).add_to(grupos.get(cat, m_osm))

        for grupo in grupos.values():
            grupo.add_to(m_osm)

        # Leyenda
        items = "".join(
            f"<div><span style='color:{c};font-size:14px;'>●</span> {cat}</div>"
            for cat, c in COLORES_CAT.items()
        )
        m_osm.get_root().html.add_child(_folium.Element(
            f"""<div style='position:fixed;bottom:14px;left:10px;z-index:9999;
                background:rgba(255,255,255,0.93);border-radius:8px;
                padding:8px 12px;font-family:Arial,sans-serif;font-size:11px;
                box-shadow:0 2px 6px rgba(0,0,0,0.2);line-height:1.7;'>
              <b>Tipo de espacio</b><br>{items}
            </div>"""
        ))

        _folium.LayerControl(position='topright', collapsed=False).add_to(m_osm)
        _st_folium(m_osm, width="100%", height=480, returned_objects=[])

    st.markdown("")
    st.caption(
        "Datos de OpenStreetMap — colaborativos y actualizados por la comunidad. "
        "Si falta algún espacio verde, podés agregarlo en openstreetmap.org"
    )


def _mostrar_ayuda_osm():
    with st.expander("¿Cómo contribuir a OpenStreetMap?"):
        st.markdown("""
        OpenStreetMap es un mapa colaborativo libre. Si los espacios verdes de tu ciudad
        no aparecen, podés agregarlos vos mismo:

        1. Registrate en [openstreetmap.org](https://www.openstreetmap.org)
        2. Usá el editor iD (web) o JOSM (desktop)
        3. Dibujá el polígono del espacio verde
        4. Agregá las etiquetas: `leisure=park`, `name=Nombre del parque`

        Más info: [wiki.openstreetmap.org/wiki/Argentina](https://wiki.openstreetmap.org/wiki/Argentina)
        """)
