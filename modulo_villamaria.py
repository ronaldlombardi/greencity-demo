"""
modulo_villamaria.py — Ciudad Verde AI Agent
=============================================
Módulo específico para el conglomerado Villa María / Villa Nueva.
- Análisis ambiental: VM + VN como ecosistema compartido (río Ctalamochita)
- Estrategias y políticas públicas: exclusivamente Villa María
"""

import streamlit as st
import folium
from streamlit_folium import st_folium
from folium import FeatureGroup

# ============================================================
# DATOS DEL CONGLOMERADO
# ============================================================

DATOS_VM = {
    'cobertura': {
        'arboles': 8.2, 'arbustos': 0, 'pastizales': 14.2,
        'cultivos': 23.9, 'edificado': 50.6, 'suelo': 1.6, 'agua': 1.3
    },
    'acceso': {
        'acceso': 100.0, 'dist_prom': 48, 'm2_hab_sat': 93.2,
        'r_0_100': 91.1, 'r_100_300': 8.9, 'r_300_500': 0.0, 'r_500_mas': 0.0
    },
    'lst': {
        'tMedia': 39.97, 'tUrbano': 39.51, 'tVerde': 39.34,
        'tP95': 44.56, 'tP5': 37.07, 'deltaUHI': 0.17,
        'tNdviAlto': 38.21, 'tNdviBajo': 39.88, 'enfriamiento': 1.67,
        'zonas': [
            {'nombre': 'Noroeste (VM centro-N)', 'temp': 40.76},
            {'nombre': 'Noreste (VN norte)',      'temp': 39.85},
            {'nombre': 'Suroeste (VM sur)',        'temp': 39.73},
            {'nombre': 'Sureste (VN sur)',         'temp': 39.55},
        ]
    },
    'osm': {'elementos': 1027, 'areaHa': 784.7, 'm2Hab': 65.4},
    'calificacion': 'A - Excelente',
    'puntaje': 7,
    'poblacion_vm': 97000,
    'poblacion_vn': 23000,
    'area_vm_km2': 36.0,
    'area_vn_km2': 13.6,
}

ZONAS = {
    'Noroeste': {
        'label': 'Noroeste — VM centro-norte',
        'municipio': 'Villa María',
        'acceso_pct': 88.3, 'dist_prom': 62, 'ha_edif': 18.4,
        'temp': 40.76, 'color_muni': '#1565c0',
    },
    'Noreste': {
        'label': 'Noreste — VN norte',
        'municipio': 'Villa Nueva',
        'acceso_pct': 96.1, 'dist_prom': 41, 'ha_edif': 12.1,
        'temp': 39.85, 'color_muni': '#6a1b9a',
    },
    'Suroeste': {
        'label': 'Suroeste — VM sur',
        'municipio': 'Villa María',
        'acceso_pct': 100.0, 'dist_prom': 38, 'ha_edif': 21.7,
        'temp': 39.73, 'color_muni': '#1565c0',
    },
    'Sureste': {
        'label': 'Sureste — VN sur',
        'municipio': 'Villa Nueva',
        'acceso_pct': 100.0, 'dist_prom': 35, 'ha_edif': 9.8,
        'temp': 39.55, 'color_muni': '#6a1b9a',
    },
}

SECCIONES_VM = [
    ("🏠", "Inicio"),
    ("🗺️", "Mapa del conglomerado"),
    ("📊", "Indicadores ambientales"),
    ("🌡️", "Temperatura superficial"),
    ("🏛️", "Verde público (OSM)"),
    ("📋", "Diagnóstico por zonas"),
    ("🎯", "Estrategias · Villa María"),
]

# ============================================================
# HELPERS VISUALES
# ============================================================

def _semaforo(valor, umbral_ok, umbral_warn, invert=False):
    """Devuelve color semáforo según umbrales."""
    if invert:
        if valor <= umbral_ok:   return "#2e7d32"
        if valor <= umbral_warn: return "#f57c00"
        return "#c62828"
    else:
        if valor >= umbral_ok:   return "#2e7d32"
        if valor >= umbral_warn: return "#f57c00"
        return "#c62828"

def _badge(texto, color):
    return (
        f"<span style='background:{color}22;border:1.5px solid {color};"
        f"color:{color};border-radius:6px;padding:2px 10px;"
        f"font-size:0.82em;font-weight:600'>{texto}</span>"
    )

def _card_indicador(titulo, valor, unidad, referencia, color):
    st.markdown(
        f"""<div style='border-left:4px solid {color};background:{color}11;
            padding:14px 16px;border-radius:0 10px 10px 0;margin-bottom:8px'>
          <div style='font-size:0.78em;color:#555;margin-bottom:2px'>{titulo}</div>
          <div style='font-size:1.7em;font-weight:700;color:{color}'>{valor}<span style='font-size:0.55em;font-weight:400;margin-left:4px'>{unidad}</span></div>
          <div style='font-size:0.75em;color:#777;margin-top:2px'>{referencia}</div>
        </div>""",
        unsafe_allow_html=True
    )

# ============================================================
# MAPA DE ALTA CALIDAD
# ============================================================

def _mapa_conglomerado(zoom=14):
    """Mapa Folium con capas de alta calidad centrado en el conglomerado."""
    m = folium.Map(
        location=[-32.415, -63.242],
        zoom_start=zoom,
        tiles=None,
        prefer_canvas=True,
    )

    # --- Capas base de alta calidad ---
    folium.TileLayer(
        tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}',
        attr='© Google',
        name='🌍 Híbrido Google (por defecto)',
        max_zoom=20,
        show=True,
    ).add_to(m)

    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='© Esri — DigitalGlobe, GeoEye, USDA FSA, USGS',
        name='🛰️ Satélite Esri',
        max_zoom=20,
        show=False,
    ).add_to(m)

    folium.TileLayer(
        tiles='https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
        attr='© OpenStreetMap contributors',
        name='🗺️ OpenStreetMap',
        max_zoom=19,
        show=False,
    ).add_to(m)

    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}',
        attr='© Esri',
        name='🗻 Topográfico',
        max_zoom=19,
        show=False,
    ).add_to(m)

    # --- Grupo: Río Ctalamochita ---
    grupo_rio = FeatureGroup(name='💧 Río Ctalamochita', show=True)
    folium.PolyLine(
        locations=[[-32.390, -63.258], [-32.398, -63.252],
                   [-32.408, -63.248], [-32.418, -63.245],
                   [-32.430, -63.244], [-32.440, -63.242]],
        color='#1565c0', weight=4, opacity=0.75,
        tooltip='Río Ctalamochita — corredor ecológico',
        popup=folium.Popup(
            "<b>💧 Río Ctalamochita</b><br>"
            "Corredor ecológico natural que divide<br>"
            "Villa María (oeste) y Villa Nueva (este).<br>"
            "<i>Potencial: parque lineal con ciclovías</i>",
            max_width=240,
        ),
    ).add_to(grupo_rio)
    grupo_rio.add_to(m)

    # --- Grupo: Villa María ---
    grupo_vm = FeatureGroup(name='🔵 Villa María', show=True)
    folium.Polygon(
        locations=[[-32.390, -63.280], [-32.390, -63.248],
                   [-32.440, -63.248], [-32.440, -63.280]],
        tooltip='Villa María — área de análisis',
        popup=folium.Popup(
            "<b>🔵 Villa María</b><br>"
            "Municipio: Villa María<br>"
            "Población: ~97.000 hab<br>"
            "Área: 36 km²<br>"
            "Calificación: A - Excelente",
            max_width=220,
        ),
        color='#1565c0', weight=2.5,
        fill=True, fill_color='#1565c0', fill_opacity=0.08,
    ).add_to(grupo_vm)
    folium.Marker(
        location=[-32.415, -63.265],
        tooltip='Villa María',
        popup=folium.Popup(
            "<b>🔵 Villa María</b><br>Cap. Depto. General San Martín<br>~97.000 hab",
            max_width=200,
        ),
        icon=folium.Icon(color='blue', icon='home', prefix='fa'),
    ).add_to(grupo_vm)
    grupo_vm.add_to(m)

    # --- Grupo: Villa Nueva ---
    grupo_vn = FeatureGroup(name='🟣 Villa Nueva', show=True)
    folium.Polygon(
        locations=[[-32.390, -63.248], [-32.390, -63.200],
                   [-32.440, -63.200], [-32.440, -63.248]],
        tooltip='Villa Nueva — contexto ecosistémico',
        popup=folium.Popup(
            "<b>🟣 Villa Nueva</b><br>"
            "Municipio: Villa Nueva<br>"
            "Población: ~23.000 hab<br>"
            "Área: 13.6 km²<br>"
            "<i>Incluida por continuidad ecológica<br>con el río Ctalamochita</i>",
            max_width=240,
        ),
        color='#6a1b9a', weight=2.5, dash_array='6 4',
        fill=True, fill_color='#6a1b9a', fill_opacity=0.06,
    ).add_to(grupo_vn)
    folium.Marker(
        location=[-32.415, -63.222],
        tooltip='Villa Nueva',
        popup=folium.Popup(
            "<b>🟣 Villa Nueva</b><br>~23.000 hab<br>"
            "<i>Contexto ecosistémico</i>",
            max_width=200,
        ),
        icon=folium.Icon(color='purple', icon='home', prefix='fa'),
    ).add_to(grupo_vn)
    grupo_vn.add_to(m)

    # --- Grupo: Zonas de análisis ---
    grupo_zonas = FeatureGroup(name='📍 Zonas de análisis', show=True)
    zonas_coords = {
        'Noroeste': {'center': [-32.402, -63.265], 'bounds': [[-32.390, -63.280], [-32.390, -63.248], [-32.415, -63.248], [-32.415, -63.280]]},
        'Noreste':  {'center': [-32.402, -63.222], 'bounds': [[-32.390, -63.248], [-32.390, -63.200], [-32.415, -63.200], [-32.415, -63.248]]},
        'Suroeste': {'center': [-32.428, -63.265], 'bounds': [[-32.415, -63.280], [-32.415, -63.248], [-32.440, -63.248], [-32.440, -63.280]]},
        'Sureste':  {'center': [-32.428, -63.222], 'bounds': [[-32.415, -63.248], [-32.415, -63.200], [-32.440, -63.200], [-32.440, -63.248]]},
    }

    for nom, z in ZONAS.items():
        coords = zonas_coords[nom]
        acc = z['acceso_pct']
        color_z = '#2e7d32' if acc >= 98 else '#f57c00' if acc >= 85 else '#c62828'
        folium.CircleMarker(
            location=coords['center'],
            radius=14,
            color=color_z, weight=2,
            fill=True, fill_color=color_z, fill_opacity=0.55,
            tooltip=f"{nom} — Acceso: {acc}%",
            popup=folium.Popup(
                f"<b>{z['label']}</b><br>"
                f"Municipio: {z['municipio']}<br>"
                f"Acceso <300m: <b>{acc}%</b><br>"
                f"Dist. prom.: {z['dist_prom']} m<br>"
                f"Temp. sup.: {z['temp']}°C",
                max_width=220,
            ),
        ).add_to(grupo_zonas)
    grupo_zonas.add_to(m)

    folium.LayerControl(position='topright', collapsed=False).add_to(m)
    return m


# ============================================================
# SECCIONES
# ============================================================

def _render_inicio():
    st.title("🏙️ Villa María — Análisis Ambiental")
    st.markdown(
        "Análisis del **conglomerado urbano Villa María – Villa Nueva** como unidad ecosistémica, "
        "articulado por el río Ctalamochita. Los datos ambientales incluyen ambas márgenes del río; "
        "las estrategias de política pública corresponden exclusivamente al municipio de **Villa María**."
    )
    st.markdown("---")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Acceso <300m", "100%", "✅ Meta OMS cumplida")
    with col2:
        st.metric("Verde público/hab", "65.4 m²", "OMS: mín. 9 m²")
    with col3:
        st.metric("Arbolado urbano", "8.2%", "Referencia: >15%")
    with col4:
        st.metric("Isla de calor ΔT", "+0.17°C", "Muy baja ✅", delta_color="inverse")

    st.markdown("---")
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("""
        ### 🔵 Villa María
        - **Población:** ~97.000 hab
        - **Área analizada:** 36 km²
        - **Depto.:** General San Martín
        - **Calificación:** A - Excelente
        - **Normativa clave:** Ordenanza 7209 — Ruralidad Urbana
        """)
    with col_b:
        st.markdown("""
        ### 🟣 Villa Nueva _(contexto ecosistémico)_
        - **Población:** ~23.000 hab
        - **Área analizada:** 13.6 km²
        - **Relación:** comparte corredor verde del Ctalamochita
        - **Nota:** las políticas públicas de esta plataforma
          corresponden al municipio de Villa María
        """)
    st.markdown("---")
    col_t, col_d = st.columns(2)
    with col_t:
        st.markdown("""
        ### 🛰️ Fuentes de datos
        - Google Earth Engine · Landsat 8/9
        - ESA WorldCover 2020 (resolución 10m)
        - OpenStreetMap — API Overpass
        - INDEC Censo 2022
        """)
    with col_d:
        st.markdown("""
        ### 📚 Marco de referencia
        - OMS: mínimo 9 m²/hab de verde público
        - ODS 11: ciudades y comunidades sostenibles
        - CONICET — investigación periurbano VM (UNVM)
        - Ordenanza 7209 "Ruralidad Urbana" (2017)
        """)
    st.info("👈 Usá el menú lateral para navegar entre las secciones del análisis.")


def _render_mapa():
    st.title("🗺️ Mapa del conglomerado")
    st.caption("Villa María · Villa Nueva · Río Ctalamochita — conglomerado urbano")
    st.markdown("---")

    st.markdown("""
    El mapa muestra el conglomerado como unidad de análisis ambiental. El **río Ctalamochita**
    actúa como corredor ecológico natural entre Villa María (oeste, 🔵) y Villa Nueva (este, 🟣).
    Las zonas de color indican el nivel de accesibilidad a espacios verdes.
    """)

    col_ley1, col_ley2, col_ley3 = st.columns(3)
    with col_ley1:
        st.markdown("🟢 **Acceso >98%** — excelente")
    with col_ley2:
        st.markdown("🟠 **Acceso 85–98%** — mejorable")
    with col_ley3:
        st.markdown("🔴 **Acceso <85%** — crítico")

    m = _mapa_conglomerado(zoom=14)
    st_folium(m, width="100%", height=560, returned_objects=[])

    st.markdown("---")
    st.markdown("""
    **Sobre el área de Villa Nueva:** su inclusión en el análisis responde a que comparte el
    ecosistema del Ctalamochita con Villa María. Las zonas Noreste y Sureste corresponden
    geográficamente a Villa Nueva y se incluyen como contexto ambiental del conglomerado.
    """)


def _render_indicadores():
    st.title("📊 Indicadores ambientales")
    st.caption("Conglomerado Villa María – Villa Nueva · Datos: ESA WorldCover 2020 + Landsat 8/9 + OSM")
    st.markdown("---")

    d = DATOS_VM
    acc = d['acceso']
    cob = d['cobertura']
    osm = d['osm']

    st.markdown("### Accesibilidad a espacios verdes")
    c1, c2, c3 = st.columns(3)
    with c1:
        color = _semaforo(acc['acceso'], 100, 80)
        _card_indicador("Acceso a <300 metros", f"{acc['acceso']:.0f}", "%", "OMS: meta 100%", color)
    with c2:
        color = _semaforo(acc['dist_prom'], 150, 300, invert=True)
        _card_indicador("Distancia promedio al verde", acc['dist_prom'], "m", "Referencia OMS: <300m", color)
    with c3:
        color = _semaforo(acc['m2_hab_sat'], 15, 9)
        _card_indicador("Verde detectado / habitante", acc['m2_hab_sat'], "m²/hab", "OMS mínimo: 9 m²/hab", color)

    st.markdown("---")
    st.markdown("### Verde público accesible (OpenStreetMap)")
    c4, c5, c6 = st.columns(3)
    with c4:
        color = _semaforo(osm['m2Hab'], 15, 9)
        _card_indicador("Verde público / habitante", osm['m2Hab'], "m²/hab", "OMS mínimo: 9 m²/hab ✅", color)
    with c5:
        _card_indicador("Área verde pública total", osm['areaHa'], "ha", "Catalogada en OSM", "#2e7d32")
    with c6:
        _card_indicador("Espacios catalogados", osm['elementos'], "", "Plazas, parques, arbolado", "#2e7d32")

    st.markdown("---")
    st.markdown("### Cobertura del suelo")
    c7, c8, c9, c10 = st.columns(4)
    with c7:
        color = _semaforo(cob['arboles'], 15, 8)
        _card_indicador("Arbolado urbano", cob['arboles'], "%", "Referencia ideal: >15%", color)
    with c8:
        _card_indicador("Pastizales", cob['pastizales'], "%", "Verde no arbolado", "#f57c00")
    with c9:
        _card_indicador("Cultivos en área urbana", cob['cultivos'], "%", "Potencial de reconversión", "#f57c00")
    with c10:
        _card_indicador("Suelo edificado", cob['edificado'], "%", "Impermeabilización", "#1565c0")

    st.markdown("---")
    st.markdown("### Distribución de accesibilidad por distancia")
    import pandas as pd
    df_dist = pd.DataFrame({
        'Rango': ['0–100 m', '100–300 m', '300–500 m', '>500 m'],
        '% área edificada': [acc['r_0_100'], acc['r_100_300'], acc['r_300_500'], acc['r_500_mas']]
    }).set_index('Rango')
    st.bar_chart(df_dist)
    st.caption("El 91.1% del área edificada tiene un espacio verde a menos de 100 metros.")


def _render_temperatura():
    st.title("🌡️ Temperatura superficial")
    st.caption("Conglomerado Villa María – Villa Nueva · Fuente: Landsat 8/9 · 13 imágenes analizadas")
    st.markdown("---")

    lst = DATOS_VM['lst']

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        _card_indicador("Temperatura media", lst['tMedia'], "°C", "Promedio área urbana", "#f57c00")
    with c2:
        color_uhi = _semaforo(lst['deltaUHI'], 0.5, 1.0, invert=True)
        _card_indicador("Isla de calor ΔT", f"+{lst['deltaUHI']}", "°C", "Urbano vs verde · muy baja ✅", "#2e7d32")
    with c3:
        _card_indicador("Verde denso (NDVI>0.4)", lst['tNdviAlto'], "°C", "Zonas con vegetación densa", "#2e7d32")
    with c4:
        _card_indicador("Suelo/asfalto (NDVI<0.2)", lst['tNdviBajo'], "°C", "Zonas sin vegetación", "#c62828")

    st.markdown("---")
    st.markdown("### Temperatura por zona del conglomerado")
    cols = st.columns(4)
    zonas_lst = lst['zonas']
    for i, z in enumerate(zonas_lst):
        with cols[i]:
            diff = z['temp'] - lst['tMedia']
            color = "#c62828" if diff > 0.5 else "#2196f3" if diff < -0.2 else "#555"
            municipio = "Villa María" if "VM" in z['nombre'] else "Villa Nueva"
            badge_color = "#1565c0" if municipio == "Villa María" else "#6a1b9a"
            st.markdown(
                f"""<div style='border:1.5px solid {color};border-radius:10px;
                    padding:14px;text-align:center;background:{color}09'>
                  <div style='font-size:0.72em;color:#555'>{z['nombre']}</div>
                  <div style='font-size:1.6em;font-weight:700;color:{color}'>{z['temp']}°C</div>
                  <div style='font-size:0.78em;color:{color}'>{'+' if diff>0 else ''}{diff:.2f}°C vs media</div>
                  <div style='margin-top:6px'><span style='background:{badge_color}22;border:1px solid {badge_color};
                    color:{badge_color};border-radius:5px;padding:1px 7px;font-size:0.7em'>{municipio}</span></div>
                </div>""",
                unsafe_allow_html=True
            )

    st.markdown("---")
    st.markdown("### Potencial de enfriamiento por arbolado")
    enf = lst['enfriamiento']
    st.markdown(f"""
    | Cobertura | Temperatura |
    |-----------|:-----------:|
    | 🌳 Vegetación densa (NDVI >0.4) | **{lst['tNdviAlto']}°C** |
    | 🏗️ Suelo / asfalto (NDVI <0.2) | **{lst['tNdviBajo']}°C** |
    | ❄️ Diferencia de enfriamiento | **{enf}°C menos** |
    """)
    st.info(
        f"💡 Cada hectárea de arbolado puede reducir hasta **{enf}°C** la temperatura local. "
        "La zona Noroeste de Villa María (+0.79°C sobre la media) es la de mayor prioridad de intervención."
    )


def _render_osm():
    st.title("🏛️ Verde público — OpenStreetMap")
    st.caption("Conglomerado Villa María – Villa Nueva · Fuente: OSM API Overpass")
    st.markdown("---")

    osm = DATOS_VM['osm']
    acc = DATOS_VM['acceso']

    st.markdown("""
    **¿Por qué OSM además del satélite?**
    El satélite detecta todo el verde visible (patios, baldíos, cultivos).
    OSM solo cataloga lo que la comunidad confirmó como **espacio de uso público**.
    La brecha entre ambos revela el verde que los vecinos *no pueden* usar.
    """)

    c1, c2, c3 = st.columns(3)
    with c1:
        _card_indicador("Verde público / habitante", osm['m2Hab'], "m²/hab", "OMS mínimo: 9 m²/hab ✅", "#2e7d32")
    with c2:
        _card_indicador("Área pública total", osm['areaHa'], "ha", "Catalogada como pública en OSM", "#2e7d32")
    with c3:
        _card_indicador("Espacios catalogados", osm['elementos'], "", "Plazas · parques · arbolado", "#2e7d32")

    diff = acc['m2_hab_sat'] - osm['m2Hab']
    st.warning(
        f"⚠️ **Brecha satelital vs. público:** el satélite detecta **{acc['m2_hab_sat']} m²/hab** "
        f"pero OSM confirma solo **{osm['m2Hab']} m²/hab** como accesible. "
        f"**{diff:.1f} m²/hab** ({diff * 97000 / 10000:.0f} ha estimadas) es verde que los vecinos probablemente no pueden usar."
    )

    st.markdown("---")
    st.markdown("### 💡 Oportunidad de política pública")
    st.markdown(f"""
    De las ~{acc['m2_hab_sat'] * 97000 / 10000:.0f} ha de verde satelital,
    solo **{osm['areaHa']} ha** están catalogadas como acceso público.
    Las **{diff * 97000 / 10000:.0f} ha restantes** representan una oportunidad concreta para:
    - Relevar y gestionar acuerdos de acceso público (baldíos, bordes de canales, franjas ferroviarias)
    - Incorporar espacios privados mediante convenios de servidumbre ambiental
    - Aplicar la Ordenanza 7209 de Ruralidad Urbana en el periurbano
    """)


def _render_diagnostico_zonas():
    st.title("📋 Diagnóstico por zonas")
    st.caption("Conglomerado Villa María – Villa Nueva · 4 zonas de análisis")
    st.markdown("---")

    lst_media = DATOS_VM['lst']['tMedia']

    cols = st.columns(4)
    zonas_orden = ['Noroeste', 'Noreste', 'Suroeste', 'Sureste']

    for i, nom in enumerate(zonas_orden):
        z = ZONAS[nom]
        with cols[i]:
            acc = z['acceso_pct']
            temp_diff = z['temp'] - lst_media
            color_acc = '#2e7d32' if acc >= 98 else '#f57c00' if acc >= 85 else '#c62828'
            color_t = '#c62828' if temp_diff > 0.3 else '#2196f3' if temp_diff < -0.1 else '#555'
            badge_color = '#1565c0' if z['municipio'] == 'Villa María' else '#6a1b9a'

            st.markdown(
                f"""<div style='border:1.5px solid #ddd;border-radius:12px;padding:16px;'>
                  <div style='font-size:0.78em;font-weight:600;color:{badge_color};margin-bottom:4px'>
                    {z['municipio']}
                  </div>
                  <div style='font-size:1em;font-weight:700;margin-bottom:10px'>{z['label']}</div>
                  <div style='font-size:0.82em;color:#333;margin-bottom:4px'>
                    <span style='color:{color_acc};font-weight:700'>●</span>
                    Acceso <300m: <b>{acc}%</b>
                  </div>
                  <div style='font-size:0.82em;color:#333;margin-bottom:4px'>
                    📏 Dist. media: <b>{z['dist_prom']} m</b>
                  </div>
                  <div style='font-size:0.82em;color:#333;margin-bottom:4px'>
                    🏗️ Área edificada: <b>{z['ha_edif']} ha</b>
                  </div>
                  <div style='font-size:0.82em;color:{color_t};margin-bottom:4px'>
                    🌡️ Temp: <b>{z['temp']}°C</b>
                    ({'+' if temp_diff > 0 else ''}{temp_diff:.2f}°C)
                  </div>
                </div>""",
                unsafe_allow_html=True
            )

    st.markdown("---")
    st.markdown("### Resumen comparativo")
    import pandas as pd
    df = pd.DataFrame([
        {
            'Zona': ZONAS[n]['label'],
            'Municipio': ZONAS[n]['municipio'],
            'Acceso <300m (%)': ZONAS[n]['acceso_pct'],
            'Dist. media (m)': ZONAS[n]['dist_prom'],
            'Temp. sup. (°C)': ZONAS[n]['temp'],
            'Área edif. (ha)': ZONAS[n]['ha_edif'],
        }
        for n in zonas_orden
    ]).set_index('Zona')
    st.dataframe(df, use_container_width=True)


def _render_estrategias():
    st.title("🎯 Estrategias de política pública")
    st.caption("Exclusivamente para el Municipio de Villa María · basadas en indicadores GEE + OSM + INDEC 2022")
    st.markdown("---")

    st.markdown("""
    Las siguientes líneas de acción surgen del análisis cuantitativo de los indicadores ambientales.
    Están priorizadas según urgencia e impacto potencial sobre la calidad de vida de los vecinos.
    """)

    # --- Prioridad ALTA ---
    st.markdown("### 🔴 Prioridad Alta — Intervención inmediata")

    estrategias_alta = [
        {
            'titulo': 'Forestación urgente en zona Noroeste (VM centro-norte)',
            'fundamento': 'Es la zona más caliente del conglomerado: 40.76°C, +0.79°C sobre la media. '
                          'El déficit de sombra en el centro-norte de Villa María genera un punto crítico '
                          'de estrés térmico para los vecinos.',
            'acciones': [
                'Plan de 500 árboles en avenidas y espacios públicos del centro-norte en 18 meses',
                'Priorizar especies nativas de alta copa: espinillo, tala, ombú',
                'Articular con UNVM para monitoreo satelital anual del impacto térmico',
            ],
            'impacto': 'Reducción estimada de hasta 1.67°C en temperatura local con cobertura del 15%',
        },
        {
            'titulo': 'Relevamiento y apertura de verde no catalogado',
            'fundamento': f'El satélite detecta 93.2 m²/hab de verde, pero OSM confirma solo 65.4 m²/hab '
                          f'como público. Hay ~{(93.2-65.4)*97000/10000:.0f} ha de verde que los vecinos '
                          f'probablemente no pueden usar.',
            'acciones': [
                'Censo municipal de espacios verdes no catalogados (baldíos, bordes de canales, franjas ferroviarias)',
                'Acuerdos de acceso público con propietarios privados (servidumbre ambiental)',
                'Aplicación de la Ordenanza 7209 en zonas periurbanas limítrofes',
            ],
            'impacto': 'Potencial de sumar hasta 27.8 m²/hab de verde accesible sin nueva infraestructura',
        },
    ]

    for e in estrategias_alta:
        with st.expander(f"🔴 {e['titulo']}", expanded=True):
            st.markdown(f"**Fundamento técnico:** {e['fundamento']}")
            st.markdown("**Acciones concretas:**")
            for a in e['acciones']:
                st.markdown(f"- {a}")
            st.success(f"📈 Impacto esperado: {e['impacto']}")

    st.markdown("---")
    # --- Prioridad MEDIA ---
    st.markdown("### 🟡 Prioridad Media — Planificación 2025–2027")

    estrategias_media = [
        {
            'titulo': 'Parque lineal sobre el Río Ctalamochita',
            'fundamento': 'El Ctalamochita es el principal corredor ecológico del conglomerado. '
                          'Actualmente subutilizado como espacio público de calidad.',
            'acciones': [
                'Ciclovía bidireccional en ambas márgenes (coordinar con Villa Nueva)',
                'Senderos peatonales con arbolado nativo en margen oeste (Villa María)',
                'Áreas de picnic y recreación en puntos estratégicos del recorrido',
                'Señalización ambiental sobre el ecosistema ribereño',
            ],
            'impacto': 'Corredor verde de ~8 km lineales; beneficio directo para barrios costeros',
        },
        {
            'titulo': 'Programa de agricultura urbana en zonas de cultivo',
            'fundamento': 'El 23.9% del área analizada son cultivos en zona urbana/periurbana. '
                          'Representan una oportunidad de transición ordenada hacia verde público.',
            'acciones': [
                'Identificar parcelas de cultivo con potencial de reconversión a verde público',
                'Programa de huertas comunitarias en lotes ociosos',
                'Convenios con propietarios para servicios ambientales (Ord. 7209)',
            ],
            'impacto': 'Reconversión potencial de hasta 5–10% de la superficie de cultivos en verde público',
        },
        {
            'titulo': 'Red de corredores verdes entre barrios',
            'fundamento': 'El 8.9% del área edificada accede al verde en el rango 100–300m. '
                          'Conectar parques existentes mediante arbolado de calles mejoraría la accesibilidad peatonal.',
            'acciones': [
                'Mapeo de rutas peatonales con déficit de sombra entre plazas y parques',
                'Arbolado sistemático en ejes peatonales prioritarios',
                'Programa de "calles verdes" con vecinos y juntas de participación',
            ],
            'impacto': 'Reducir la distancia media al verde de 48m a <40m para el 100% del área',
        },
    ]

    for e in estrategias_media:
        with st.expander(f"🟡 {e['titulo']}", expanded=False):
            st.markdown(f"**Fundamento técnico:** {e['fundamento']}")
            st.markdown("**Acciones concretas:**")
            for a in e['acciones']:
                st.markdown(f"- {a}")
            st.info(f"📈 Impacto esperado: {e['impacto']}")

    st.markdown("---")
    # --- Prioridad BAJA ---
    st.markdown("### 🟢 Prioridad Sostenida — Monitoreo y mejora continua")

    estrategias_baja = [
        {
            'titulo': 'Sistema de monitoreo ambiental con GEE',
            'fundamento': 'Villa María ya tiene indicadores de base sólidos. '
                          'El valor ahora está en medir el impacto de cada intervención.',
            'acciones': [
                'Actualización anual de indicadores LST, NDVI y cobertura satelital',
                'Dashboard público con evolución histórica de la calidad ambiental',
                'Articulación con CONICET/UNVM para validación científica de los datos',
            ],
            'impacto': 'Evidencia para rendición de cuentas y ajuste de políticas en tiempo real',
        },
        {
            'titulo': 'Fortalecimiento del catálogo OSM de espacios verdes',
            'fundamento': 'Villa María tiene 1.027 elementos catalogados en OSM. '
                          'Mantenerlo actualizado es crítico para la planificación.',
            'acciones': [
                'Mapathon municipal anual con participación ciudadana',
                'Articulación con escuelas para relevamiento colaborativo de espacios verdes',
                'Vinculación del catálogo OSM con el sistema de gestión municipal',
            ],
            'impacto': 'Base de datos pública y actualizada para decisiones de política ambiental',
        },
    ]

    for e in estrategias_baja:
        with st.expander(f"🟢 {e['titulo']}", expanded=False):
            st.markdown(f"**Fundamento técnico:** {e['fundamento']}")
            st.markdown("**Acciones concretas:**")
            for a in e['acciones']:
                st.markdown(f"- {a}")
            st.success(f"📈 Impacto esperado: {e['impacto']}")

    st.markdown("---")
    st.caption(
        "Ciudad Verde AI Agent · Estrategias para Villa María · "
        "Datos: ESA WorldCover 2020 · Landsat 8/9 · OpenStreetMap · INDEC Censo 2022 · "
        "Marco: OMS, ODS 11, Ordenanza 7209"
    )


# ============================================================
# RENDER PRINCIPAL — punto de entrada desde app.py
# ============================================================

def render_modulo_villamaria():
    """Punto de entrada. Llamar desde app.py cuando el módulo activo es Villa María."""

    with st.sidebar:
        st.markdown("---")
        st.markdown("### 🏙️ Villa María")
        seccion = st.radio(
            "Sección",
            [f"{e} {n}" for e, n in SECCIONES_VM],
            label_visibility="collapsed",
            key="seccion_vm",
        )
        st.markdown("---")
        st.caption("🔵 Villa María · 97.000 hab")
        st.caption("🟣 Villa Nueva · contexto ecosistémico")
        st.caption("💧 Río Ctalamochita · corredor verde")

    if "Inicio" in seccion:
        _render_inicio()
    elif "Mapa" in seccion:
        _render_mapa()
    elif "Indicadores" in seccion:
        _render_indicadores()
    elif "Temperatura" in seccion:
        _render_temperatura()
    elif "OSM" in seccion:
        _render_osm()
    elif "Diagnóstico" in seccion:
        _render_diagnostico_zonas()
    elif "Estrategias" in seccion:
        _render_estrategias()
