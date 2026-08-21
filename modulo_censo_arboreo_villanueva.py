"""
modulo_censo_arboreo_villanueva.py — Ciudad Verde AI Agent
============================================================
Censo Arbóreo — Villa Nueva.
Objetivo municipal: 1 árbol por vivienda.

Mismo método que Villa María (Canopy Height GEE, umbral 2m), pero
usando las 32 zonas oficiales de zonificación (Código Urbano Rural
2025, IDECOR / Municipalidad de Villa Nueva) como unidad de
agregación en vez de barrios.

Datos precalculados localmente — ver exportar_censo_villanueva.py.

Uso en dashboard:
    from modulo_censo_arboreo_villanueva import render_censo_arboreo_villanueva
    render_censo_arboreo_villanueva()
"""

import os
import json
import streamlit as st
import folium
from streamlit_folium import st_folium


# ============================================================
# CONFIGURACIÓN
# ============================================================

RUTA_ZONAS = os.path.join(os.path.dirname(__file__), 'data', 'zonificacion_villanueva.geojson')
RUTA_CENSO_JSON = os.path.join(os.path.dirname(__file__), 'data', 'censo_arboreo_villanueva.json')


# ============================================================
# CARGA DE DATOS PRECALCULADOS
# ============================================================

@st.cache_data(show_spinner=False, ttl=3600)
def _cargar_censo_json():
    if not os.path.exists(RUTA_CENSO_JSON):
        return None
    with open(RUTA_CENSO_JSON, encoding='utf-8') as f:
        return json.load(f)


@st.cache_data(show_spinner=False, ttl=3600)
def _cargar_zonas_geojson():
    if not os.path.exists(RUTA_ZONAS):
        return None
    with open(RUTA_ZONAS, encoding='utf-8') as f:
        return json.load(f)


def _color_densidad(densidad_ha):
    """Color según densidad de árboles/ha (para el mapa y el ranking)."""
    if densidad_ha is None:
        return '#555555'
    if densidad_ha >= 40:
        return '#1b5e20'
    if densidad_ha >= 20:
        return '#4caf50'
    if densidad_ha >= 8:
        return '#aed581'
    if densidad_ha > 0:
        return '#fff59d'
    return '#e0e0e0'


# ============================================================
# ESTADO DE FUENTES
# ============================================================

_COLOR_ESTADO = {
    'conectada':    '#4caf50',
    'en_progreso':  '#ff9800',
    'pendiente':    '#9e9e9e',
}
_LABEL_ESTADO = {
    'conectada':    '✅ Conectada',
    'en_progreso':  '🔶 En progreso',
    'pendiente':    '⏳ Pendiente',
}

FUENTES = [
    {
        'nombre': 'Canopy Height (GEE, 1m)',
        'rol': 'Numerador — conteo y cobertura de árboles',
        'estado': 'conectada',
        'detalle': 'Dataset global de altura de dosel a 1m (Meta/WRI). Censo completo por '
                    'zona normativa, precalculado local. Método ya validado en Villa María '
                    '(mismo umbral de 2m).',
    },
    {
        'nombre': 'Zonificación oficial (IDECOR / Municipalidad de Villa Nueva)',
        'rol': 'Unidad de agregación — 32 zonas del Código Urbano Rural 2025',
        'estado': 'conectada',
        'detalle': 'Fuente: WFS público IDECOR, capa villa_nva_cod_urb_rur. Reemplaza a los '
                    'barrios con nombre (que no existen para Villa Nueva) por la zonificación '
                    'normativa oficial.',
    },
    {
        'nombre': 'Catastro IDECOR (WFS/WMS)',
        'rol': 'Denominador — parcelas edificadas por zona',
        'estado': 'pendiente',
        'detalle': 'Distingue parcelas baldío/edificado/PH. Da el número real de viviendas '
                    'por zona para calcular el ratio árboles/vivienda. Requiere consulta '
                    'a idecor@cba.gov.ar para descarga sin filtro por WFS.',
    },
    {
        'nombre': 'OpenStreetMap (natural=tree)',
        'rol': 'Complementaria — árboles individuales cargados por la comunidad',
        'estado': 'pendiente',
        'detalle': 'Puede sumar detalle puntual en el futuro, no reemplaza el censo por Canopy Height.',
    },
]


# ============================================================
# RENDER PRINCIPAL
# ============================================================

def render_censo_arboreo_villanueva():
    st.title("🌳 Censo Arbóreo — Villa Nueva")
    st.caption("Objetivo municipal: 1 árbol por vivienda")

    censo = _cargar_censo_json()
    zonas_geo = _cargar_zonas_geojson()

    if not censo:
        st.info(
            "Censo completo aún no calculado. Correr "
            "`python exportar_censo_villanueva.py` localmente para generarlo."
        )
        return

    st.caption(f"Último cálculo: {censo['fecha_calculo'][:16].replace('T', ' ')}")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("🌳 Árboles contados", f"{censo['total_arboles']:,}".replace(",", "."))
    with c2:
        st.metric("Área total de copa", f"{censo['total_area_copa_ha']} ha")
    with c3:
        st.metric("Zonas procesadas", f"{censo['zonas_procesadas']}/{censo['zonas_totales']}")

    c4, c5 = st.columns(2)
    with c4:
        st.metric("Altura media de copa (ciudad)",
                   f"{censo['ciudad_altura_media_m']} m" if censo.get('ciudad_altura_media_m') else "N/D")
    with c5:
        st.metric("Altura máxima detectada",
                   f"{censo['ciudad_altura_max_m']} m" if censo.get('ciudad_altura_max_m') else "N/D")

    # Calcular densidad por zona (árboles/ha)
    validos = [z for z in censo['zonas'] if z['n_arboles'] is not None and z.get('area_zona_ha')]
    for z in validos:
        z['densidad_arboles_ha'] = round(z['n_arboles'] / z['area_zona_ha'], 1) if z['area_zona_ha'] else 0

    st.markdown("---")

    # ---- Ranking top 5 / bottom 5 ----
    if validos:
        ordenados = sorted(validos, key=lambda z: -z['densidad_arboles_ha'])
        top5 = ordenados[:5]
        bottom5 = ordenados[-5:][::-1]

        st.markdown("#### 🏆 Ranking de zonas — densidad arbórea (árboles/ha)")
        col_top, col_bottom = st.columns(2)

        with col_top:
            st.markdown("**🟢 Las 5 con mayor densidad**")
            for i, z in enumerate(top5, 1):
                st.markdown(
                    f"<div style='display:flex;justify-content:space-between;padding:6px 0;"
                    f"border-bottom:1px solid rgba(255,255,255,0.08)'>"
                    f"<span>#{i} {z['nombre']} ({z['desig']})</span>"
                    f"<span style='font-weight:700;color:#4caf50'>{z['densidad_arboles_ha']} árb/ha</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

        with col_bottom:
            st.markdown("**🟡 Las 5 con menor densidad**")
            for i, z in enumerate(bottom5, 1):
                st.markdown(
                    f"<div style='display:flex;justify-content:space-between;padding:6px 0;"
                    f"border-bottom:1px solid rgba(255,255,255,0.08)'>"
                    f"<span>#{i} {z['nombre']} ({z['desig']})</span>"
                    f"<span style='font-weight:700;color:#f57c00'>{z['densidad_arboles_ha']} árb/ha</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

        st.caption(
            "💡 Las zonas con menor densidad son las primeras candidatas para planes de "
            "forestación dirigidos al objetivo '1 árbol por casa'."
        )

    st.markdown("---")

    # ---- Mapa por zona (polígonos reales, coloreados por densidad) ----
    st.markdown("#### 🗺️ Mapa por zona — densidad arbórea")

    if zonas_geo:
        censo_por_desig = {z['desig']: z for z in censo['zonas']}

        lat_centro = sum(z['centro'][0] for z in censo['zonas']) / len(censo['zonas'])
        lon_centro = sum(z['centro'][1] for z in censo['zonas']) / len(censo['zonas'])

        m_censo = folium.Map(location=[lat_centro, lon_centro], zoom_start=13, tiles=None)
        folium.TileLayer(
            tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}',
            attr='© Google', name='🌍 Satelital', max_zoom=20, show=True,
        ).add_to(m_censo)

        for feat in zonas_geo['features']:
            desig = feat['properties'].get('desig', '')
            stats = censo_por_desig.get(desig, {})
            densidad = None
            if stats.get('n_arboles') is not None and stats.get('area_zona_ha'):
                densidad = round(stats['n_arboles'] / stats['area_zona_ha'], 1)
            color = _color_densidad(densidad)

            nombre = stats.get('nombre', desig)
            tooltip = f"{nombre} ({desig})"
            if stats.get('n_arboles') is not None:
                tooltip += f" — {stats['n_arboles']} árboles ({densidad} árb/ha)"
            else:
                tooltip += " — sin datos"

            folium.GeoJson(
                feat,
                style_function=lambda x, c=color: {
                    'fillColor': c, 'color': '#ffffff', 'weight': 1,
                    'fillOpacity': 0.55,
                },
                tooltip=tooltip,
            ).add_to(m_censo)

        st_folium(m_censo, width="100%", height=520, returned_objects=[], key="mapa_censo_vn")
        st.caption(
            "🟢 Alta densidad (≥40 árb/ha) · 🟩 Media (20-39) · 🟡 Baja (8-19) · "
            "⚪ Muy baja (1-7) · ⚫ Sin datos/error"
        )
    else:
        st.info("Falta data/zonificacion_villanueva.geojson para dibujar el mapa por zona.")

    st.markdown("---")

    # ---- Estado de fuentes ----
    st.markdown("### Fuentes de datos — estado actual")

    for f in FUENTES:
        color = _COLOR_ESTADO[f['estado']]
        st.markdown(
            f"""<div style='border-left:4px solid {color};background:{color}11;
                padding:14px 16px;border-radius:0 10px 10px 0;margin-bottom:10px'>
              <div style='display:flex;justify-content:space-between;align-items:center'>
                <span style='font-size:1em;font-weight:600;color:#fff'>{f['nombre']}</span>
                <span style='font-size:0.82em;font-weight:600;color:{color}'>{_LABEL_ESTADO[f['estado']]}</span>
              </div>
              <div style='font-size:0.85em;color:#ccc;margin-top:2px'>{f['rol']}</div>
              <div style='font-size:0.82em;color:#aaa;margin-top:6px'>{f['detalle']}</div>
            </div>""",
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.caption(
        "Ciudad Verde AI Agent · Villa Nueva · Censo Arbóreo · "
        "Canopy Height (GEE) + Zonificación oficial (IDECOR) + Catastro IDECOR (pendiente)"
    )