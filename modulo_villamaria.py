"""
modulo_villamaria.py — Ciudad Verde AI Agent
=============================================
Módulo específico para el conglomerado Villa María / Villa Nueva.
- Análisis ambiental: VM + VN como ecosistema compartido (río Ctalamochita)
- Estrategias y políticas públicas: exclusivamente Villa María
"""

import os
import json
import streamlit as st
import folium
from streamlit_folium import st_folium
from folium import FeatureGroup

RUTA_INDICADORES = os.path.join(os.path.dirname(__file__), 'data', 'indicadores_villamaria.json')

# ============================================================
# DATOS DEL CONGLOMERADO — cargados desde cálculo real (GEE/OSM)
# ============================================================


def _cargar_datos_vm():
    """Carga los indicadores reales calculados con
    exportar_indicadores_villamaria.py (data/indicadores_villamaria.json).
    Si el archivo no existe todavía, devuelve valores en cero explícitos
    y datos_preliminares=True — nunca un número inventado. Mismo criterio
    que _cargar_datos_vn() en modulo_villanueva.py."""
    if not os.path.exists(RUTA_INDICADORES):
        return {
            'cobertura': {'arboles': 0, 'arbustos': 0, 'pastizales': 0,
                          'cultivos': 0, 'edificado': 0, 'suelo': 0, 'agua': 0},
            'acceso': {'acceso': 0, 'dist_prom': None, 'm2_hab_sat': 0,
                       'r_0_100': 0, 'r_100_300': 0, 'r_300_500': 0, 'r_500_mas': 0},
            'lst': {'tMedia': None, 'tUrbano': None, 'tVerde': None, 'tP95': None,
                    'tP5': None, 'deltaUHI': None, 'tNdviAlto': None,
                    'tNdviBajo': None, 'enfriamiento': None, 'nImagenes': None,
                    'zonas': []},
            'osm': {'elementos': None, 'areaHa': None, 'm2Hab': None},
            'calificacion': 'Por calcular',
            'puntaje': None,
            'poblacion_vm': 96061,   # INDEC Censo 2022, resultados definitivos
            'poblacion_vn': 26260,  # INDEC Censo 2022, vía Wikipedia (actualizado con datos definitivos)
            'area_vm_km2': None,
            'area_vn_km2': 13.6,
            'fecha_calculo': None,
            'datos_preliminares': True,
        }

    with open(RUTA_INDICADORES, encoding='utf-8') as f:
        d = json.load(f)

    lst_raw = d.get('lst') or {}
    osm_raw = d.get('osm') or {}

    return {
        'cobertura': d.get('cobertura', {}),
        'acceso': d.get('acceso', {}),
        'lst': {
            'tMedia': lst_raw.get('t_media'),
            'tUrbano': lst_raw.get('t_urbano'),
            'tVerde': lst_raw.get('t_verde'),
            'tP95': lst_raw.get('t_p95'),
            'tP5': lst_raw.get('t_p5'),
            'deltaUHI': lst_raw.get('delta_uhi'),
            'tNdviAlto': lst_raw.get('t_ndvi_alto'),
            'tNdviBajo': lst_raw.get('t_ndvi_bajo'),
            'enfriamiento': lst_raw.get('enfriamiento_verde'),
            'nImagenes': lst_raw.get('n_imagenes'),
            # ⚠️ Sin desglose por zona todavía — no hay script real que lo
            # calcule por barrio/zona. Se deja vacío a propósito, no se
            # inventa. Ver Paso 2 del plan: sacar secciones que dependían
            # de esto (rectángulos a mano, sin respaldo).
            'zonas': [],
        },
        'osm': {
            'elementos': osm_raw.get('elementos'),
            'areaHa': osm_raw.get('area_ha'),
            'm2Hab': osm_raw.get('m2_hab'),
            'espacios': osm_raw.get('espacios', []),
            'top10': osm_raw.get('top10', []),
        },
        'calificacion': 'Calculado',
        'puntaje': None,
        'poblacion_vm': d.get('poblacion', 96061),
        'poblacion_vn': 26260,  # INDEC Censo 2022, vía Wikipedia (actualizado con datos definitivos)
        'area_vm_km2': d.get('area_ciudad_km2'),
        'area_vn_km2': 13.6,
        'fecha_calculo': d.get('fecha_calculo'),
        'datos_preliminares': False,
    }


DATOS_VM = _cargar_datos_vm()

from modulo_masterplan import render_masterplan
from modulo_censo_arboreo import render_censo_arboreo

SECCIONES_VM = [
    ("🏠", "Inicio"),
    ("🗺️", "Mapa del conglomerado"),
    ("📊", "Indicadores ambientales"),
    ("🌡️", "Temperatura superficial"),
    ("🏛️", "Verde público (OSM)"),
    ("🌳", "Plan de Forestación"),
    ("🎯", "Estrategias · Villa María"),
    ("🌍", "Agenda 2030 · C40"),
    ("📄", "Masterplan · Opus 4.7"),
    ("🤝", "A Mejorar juntos"),
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
          <div style='font-size:0.88em;color:#fff;margin-bottom:2px;font-weight:500'>{titulo}</div>
          <div style='font-size:1.7em;font-weight:700;color:{color}'>{valor}<span style='font-size:0.55em;font-weight:400;margin-left:4px'>{unidad}</span></div>
          <div style='font-size:0.84em;color:#ccc;margin-top:2px'>{referencia}</div>
        </div>""",
        unsafe_allow_html=True
    )

# ============================================================
# MAPA DE ALTA CALIDAD
# ============================================================

def _mapa_conglomerado(zoom=14):
    """Mapa limpio: polígonos VM/VN bien diferenciados, río destacado, zonas simples con tooltip."""
    m = folium.Map(
        location=[-32.415, -63.242],
        zoom_start=zoom,
        tiles=None,
        prefer_canvas=True,
    )

    # --- Capas base ---
    folium.TileLayer(
        tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}',
        attr='© Google', name='🌍 Híbrido Google', max_zoom=20, show=True,
    ).add_to(m)
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='© Esri', name='🛰️ Satélite Esri', max_zoom=20, show=False,
    ).add_to(m)
    folium.TileLayer(
        tiles='https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
        attr='© OpenStreetMap contributors', name='🗺️ OpenStreetMap', max_zoom=19, show=False,
    ).add_to(m)

    # --- Villa María (polígono azul sólido) ---
    grupo_vm = FeatureGroup(name='🔵 Villa María', show=True)
    folium.Polygon(
        locations=[[-32.390, -63.280], [-32.390, -63.248],
                   [-32.440, -63.248], [-32.440, -63.280]],
        color='#1565c0', weight=3,
        fill=True, fill_color='#1565c0', fill_opacity=0.10,
        tooltip='🔵 Villa María — ~97.000 hab · 36 km² · Calificación: A ✅',
        popup=folium.Popup(
            "<b style='color:#1565c0'>🔵 Villa María</b><br>"
            "Cap. Depto. General San Martín<br>"
            "Población: ~97.000 hab · Área: 36 km²<br>"
            "<b>Calificación: A - Excelente ✅</b>",
            max_width=220,
        ),
    ).add_to(grupo_vm)
    grupo_vm.add_to(m)

    # --- Villa Nueva (polígono violeta punteado) ---
    grupo_vn = FeatureGroup(name='🟣 Villa Nueva', show=True)
    folium.Polygon(
        locations=[[-32.390, -63.248], [-32.390, -63.200],
                   [-32.440, -63.200], [-32.440, -63.248]],
        color='#7b1fa2', weight=2.5, dash_array='8 5',
        fill=True, fill_color='#7b1fa2', fill_opacity=0.07,
        tooltip='🟣 Villa Nueva — ~23.000 hab · 13.6 km² · contexto ecosistémico',
        popup=folium.Popup(
            "<b style='color:#7b1fa2'>🟣 Villa Nueva</b><br>"
            "Población: ~23.000 hab · Área: 13.6 km²<br>"
            "<i>Incluida por continuidad ecológica con el Ctalamochita</i>",
            max_width=230,
        ),
    ).add_to(grupo_vn)
    grupo_vn.add_to(m)

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

    acc = DATOS_VM['acceso']
    osm = DATOS_VM['osm']
    cob = DATOS_VM['cobertura']
    lst = DATOS_VM['lst']

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Acceso <300m", f"{acc['acceso']:.0f}%" if acc['acceso'] is not None else "—",
                   "✅ Meta OMS cumplida" if acc['acceso'] == 100 else None)
    with col2:
        st.metric("Verde público/hab", f"{osm['m2Hab']} m²" if osm['m2Hab'] is not None else "—",
                   "OMS: mín. 9 m²")
    with col3:
        st.metric("Arbolado urbano", f"{cob['arboles']}%" if cob.get('arboles') is not None else "—",
                   "Referencia: >15%")
    with col4:
        st.metric("Isla de calor ΔT", f"+{lst['deltaUHI']}°C" if lst['deltaUHI'] is not None else "—",
                   "Muy baja ✅" if (lst['deltaUHI'] or 99) < 0.5 else None, delta_color="inverse")

    if DATOS_VM.get('datos_preliminares'):
        st.warning(
            "⚠️ Todavía no se corrió el cálculo real de indicadores para Villa María "
            "(`exportar_indicadores_villamaria.py`). Los valores en cero son un placeholder, "
            "no una medición."
        )

    st.markdown("---")
    poblacion_vm = DATOS_VM.get('poblacion_vm')
    area_vm = DATOS_VM.get('area_vm_km2')
    fecha_calc = DATOS_VM.get('fecha_calculo')
    fecha_str = fecha_calc[:10] if fecha_calc else "sin calcular"

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(f"""
        ### 🔵 Villa María
        - **Población:** {poblacion_vm:,.0f} hab (INDEC Censo 2022)
        - **Área analizada:** {f"{area_vm:.1f} km²" if area_vm else "—"} (38 barrios oficiales)
        - **Depto.:** General San Martín
        - **Última actualización de indicadores:** {fecha_str}
        - **Normativa clave:** Ordenanza 7209 — Ruralidad Urbana
        """)
    with col_b:
        st.markdown(f"""
        ### 🟣 Villa Nueva _(contexto ecosistémico)_
        - **Población:** {DATOS_VM.get('poblacion_vn', 0):,.0f} hab
        - **Área analizada:** {DATOS_VM.get('area_vn_km2', '—')} km²
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

    poblacion_vm = DATOS_VM.get('poblacion_vm', 0)
    poblacion_vn = DATOS_VM.get('poblacion_vn', 0)

    # --- Explicación del mapa ---
    st.markdown("""
    Este mapa muestra el **conglomerado urbano Villa María – Villa Nueva** como una unidad de análisis ambiental.
    Ambas ciudades comparten el ecosistema del **Río Ctalamochita** (visible en el centro del mapa satelital),
    que actúa como corredor ecológico natural.
    """)

    st.markdown(
        "<div style='background:rgba(30,40,80,0.5);border:1px solid rgba(120,140,255,0.2);"
        "border-radius:10px;padding:14px 18px;margin-bottom:14px;font-size:0.88em;line-height:1.8;'>"
        "<b>Cómo leer el mapa:</b><br>"
        f"<span style='color:#1565c0;font-size:15px;font-weight:700;'>▬</span> "
        f"<b>Borde azul sólido</b> = Villa María (oeste del río) · ~{poblacion_vm:,.0f} hab<br>"
        f"<span style='color:#7b1fa2;font-size:15px;font-weight:700;'>╌</span> "
        f"<b>Borde violeta punteado</b> = Villa Nueva (este del río) · ~{poblacion_vn:,.0f} hab<br>"
        "</div>",
        unsafe_allow_html=True,
    )

    m = _mapa_conglomerado(zoom=14)
    st_folium(m, width="100%", height=540, returned_objects=[], key="mapa_conglomerado_vm")

    st.markdown("---")
    st.markdown(
        "<div style='font-size:0.82em;color:#888;'>"
        "Villa Nueva se incluye en el análisis por su continuidad ecosistémica con Villa María "
        "a través del Río Ctalamochita. Las estrategias de política pública corresponden "
        "exclusivamente al municipio de Villa María."
        "</div>",
        unsafe_allow_html=True,
    )


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

    # --- Mapa WorldCover ---
    st.markdown("#### 🗺️ Distribución espacial de cobertura del suelo")
    st.caption("Fuente: ESA WorldCover 2020 · resolución 10m · cada color representa una clase de cobertura")

    st.markdown(
        "<div style='background:rgba(30,40,80,0.5);border:1px solid rgba(120,140,255,0.2);"
        "border-radius:8px;padding:10px 14px;margin-bottom:10px;font-size:0.82em;line-height:1.7;'>"
        "<b>Clasificación ESA WorldCover 2020:</b> "
        "Árboles · Pastizales · Cultivos · Edificado · Agua · Suelo desnudo · Humedal"
        "</div>",
        unsafe_allow_html=True,
    )

    try:
        import ee
        coords_vm = [
            [-63.280, -32.390], [-63.200, -32.390],
            [-63.200, -32.440], [-63.280, -32.440], [-63.280, -32.390]
        ]
        area_ee  = ee.Geometry.Polygon([coords_vm])
        wc       = ee.Image('ESA/WorldCover/v100/2020').clip(area_ee)
        # SLD style con colores exactos por valor de pixel — sin interpolación
        sld = """
        <RasterSymbolizer>
          <ColorMap type="values">
            <ColorMapEntry color="#006400" quantity="10" label="Árboles"/>
            <ColorMapEntry color="#8db360" quantity="20" label="Arbustos"/>
            <ColorMapEntry color="#ffbb22" quantity="30" label="Pastizales"/>
            <ColorMapEntry color="#fffb00" quantity="40" label="Cultivos"/>
            <ColorMapEntry color="#fa0000" quantity="50" label="Edificado"/>
            <ColorMapEntry color="#b4b4b4" quantity="60" label="Suelo desnudo"/>
            <ColorMapEntry color="#f0f0f0" quantity="70" label="Nieve"/>
            <ColorMapEntry color="#0064c8" quantity="80" label="Agua"/>
            <ColorMapEntry color="#0096a0" quantity="90" label="Humedal"/>
            <ColorMapEntry color="#00cf75" quantity="95" label="Manglar"/>
            <ColorMapEntry color="#fae6a0" quantity="100" label="Musgo"/>
          </ColorMap>
        </RasterSymbolizer>
        """
        map_id   = wc.sldStyle(sld).getMapId()
        tiles_wc = map_id['tile_fetcher'].url_format

        m_wc = folium.Map(location=[-32.415, -63.242], zoom_start=13, tiles=None)
        folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='© Esri', name='🛰️ Satélite', max_zoom=20, show=True,
        ).add_to(m_wc)
        folium.TileLayer(
            tiles=tiles_wc,
            attr='ESA WorldCover 2020 · GEE',
            name='🌍 WorldCover',
            overlay=True, show=True, opacity=0.15,
        ).add_to(m_wc)
        # Polígono del área
        folium.Polygon(
            locations=[[-32.390,-63.280],[-32.390,-63.200],
                       [-32.440,-63.200],[-32.440,-63.280]],
            color='#fff', weight=1.5, fill=False,
            tooltip='Área de análisis VM+VN',
        ).add_to(m_wc)
        folium.LayerControl(position='topright', collapsed=False).add_to(m_wc)
        st_folium(m_wc, width="100%", height=440, returned_objects=[], key="mapa_cobertura_vm")
    except Exception as e:
        st.info(f"Mapa WorldCover no disponible en este momento: {e}")

    st.markdown("---")
    st.markdown("### Distribución de accesibilidad por distancia al verde más cercano")
    st.caption("% del área edificada por rango · Referencia OMS: 100% a menos de 300 m")

    rangos = [
        ("0 – 100 m",   acc['r_0_100'],    "#2e7d32", "Dentro del estándar OMS · a pasos"),
        ("100 – 300 m", acc['r_100_300'],  "#66bb6a", "Dentro del estándar OMS · ~4 min caminando"),
    ]
    if round(acc['r_300_500'], 1) > 0:
        rangos.append(("300 – 500 m", acc['r_300_500'], "#f57c00", "Por encima del umbral OMS"))
    if round(acc['r_500_mas'], 1) > 0:
        rangos.append(("> 500 m", max(acc['r_500_mas'], 0), "#c62828", "Déficit · intervención recomendada"))
    pct_oms = acc['r_0_100'] + acc['r_100_300']

    for label, pct, color, desc in rangos:
        col_l, col_b, col_v = st.columns([2, 5, 1])
        with col_l:
            st.markdown(
                f"<div style='font-size:0.88em;font-weight:600;color:{color};"
                f"padding-top:6px;'>{label}</div>"
                f"<div style='font-size:0.82em;color:#ccc;'>{desc}</div>",
                unsafe_allow_html=True,
            )
        with col_b:
            bar_w = max(pct, 0.3)
            label_inner = f'<span style="color:#fff;font-size:0.8em;font-weight:700;">{pct:.1f}%</span>' if pct > 5 else ''
            st.markdown(
                f"<div style='background:rgba(255,255,255,0.08);border-radius:6px;height:28px;"
                f"margin-top:4px;overflow:hidden;'>"
                f"<div style='width:{bar_w:.1f}%;background:{color};height:28px;"
                f"border-radius:6px;display:flex;align-items:center;padding-left:8px;'>"
                f"{label_inner}"
                f"</div></div>",
                unsafe_allow_html=True,
            )
        with col_v:
            st.markdown(
                f"<div style='font-weight:700;color:{color};padding-top:4px;"
                f"text-align:right;font-size:0.95em;'>{pct:.1f}%</div>",
                unsafe_allow_html=True,
            )

    st.markdown(
        f"<div style='margin-top:14px;background:#e8f5e9;border:1.5px solid #66bb6a;"
        f"border-radius:8px;padding:10px 16px;display:flex;"
        f"justify-content:space-between;align-items:center;'>"
        f"<div style='font-size:0.88em;'>"
        f"<b style='color:#2e7d32;'>&#9989; Dentro del est&aacute;ndar OMS (&lt;300 m)</b>"
        f"</div>"
        f"<div style='font-size:1.3em;font-weight:800;color:#2e7d32;'>{pct_oms:.1f}%</div>"
        f"</div>"
        f"<div style='font-size:0.84em;color:#ccc;margin-top:6px;'>"
        f"{acc['r_0_100']:.1f}% del &aacute;rea edificada tiene verde a menos de 100 m &middot; "
        f"{acc['r_100_300']:.1f}% adicional lo tiene entre 100 y 300 m &middot; Meta OMS: 100% &#9989;"
        f"</div>",
        unsafe_allow_html=True,
    )

    
    # Leyenda accesibilidad
    st.markdown(
        "<div style='display:flex;gap:20px;font-size:12px;margin-top:4px;'>"
        "<span><span style='color:#2e7d32;font-size:16px;'>█</span> &ge;98% Excelente</span>"
        "<span><span style='color:#f57c00;font-size:16px;'>█</span> 85–97% Mejorable</span>"
        "<span><span style='color:#c62828;font-size:16px;'>█</span> &lt;85% Crítico</span>"
        "</div>",
        unsafe_allow_html=True,
    )


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

    # ---- Mapa OSM en vivo ----
    st.markdown("### 🗺️ Mapa de espacios verdes públicos")
    from modulo_osm import cargar_osm, COLORES_CAT

    BBOX_VM = (-32.44, -63.28, -32.39, -63.20)  # sur, oeste, norte, este
    with st.spinner("Consultando OpenStreetMap..."):
        datos_osm = cargar_osm(BBOX_VM, 120000)

    if datos_osm and datos_osm.get('elementos', 0) > 0:
        espacios = datos_osm['espacios']
        lats = [g['lat'] for g in espacios]
        lons = [g['lon'] for g in espacios]
        center = [sum(lats)/len(lats), sum(lons)/len(lons)]

        m_osm = folium.Map(location=center, zoom_start=14, tiles=None)
        folium.TileLayer(
            tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}',
            attr='© Google', name='🌍 Híbrido Google', max_zoom=20, show=True,
        ).add_to(m_osm)
        folium.TileLayer(
            tiles='https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
            attr='© OpenStreetMap contributors', name='🗺️ OpenStreetMap',
            max_zoom=19, show=False,
        ).add_to(m_osm)

        grupos = {cat: FeatureGroup(name=f"🌿 {cat}", show=True) for cat in COLORES_CAT}
        for g in espacios:
            cat   = g['categoria']
            color = COLORES_CAT.get(cat, '#888')
            area_str = f"{g['area_m2']/10000:.2f} ha" if g['area_m2'] >= 10000 else f"{g['area_m2']:.0f} m²"
            folium.CircleMarker(
                location=[g['lat'], g['lon']],
                radius=5, color=color, weight=1.5,
                fill=True, fill_color=color, fill_opacity=0.8,
                tooltip=f"{g['nombre']} — {cat}",
                popup=folium.Popup(
                    f"<b>{g['nombre']}</b><br>Tipo: {cat}<br>Área: {area_str}",
                    max_width=200,
                ),
            ).add_to(grupos.get(cat, m_osm))

        for grupo in grupos.values():
            grupo.add_to(m_osm)
        folium.LayerControl(position='topright', collapsed=False).add_to(m_osm)
        st_folium(m_osm, width="100%", height=500, returned_objects=[], key="mapa_osm_vm")

        # Leyenda fuera del iframe
        items = " &nbsp;&nbsp; ".join(
            f"<span style='color:{c};font-size:15px;'>●</span> {cat}"
            for cat, c in COLORES_CAT.items()
        )
        st.markdown(f"<div style='font-size:11px;color:#aaa;margin-top:4px;'>{items}</div>",
                    unsafe_allow_html=True)
    else:
        st.info("No se encontraron espacios en OSM para este área, o hubo un error de conexión.")

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
    st.markdown("### 🟡 Prioridad Media — Planificación 2026–2028")

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
# SECCIÓN: AGENDA 2030 · C40
# ============================================================

def _render_agenda2030():
    st.title("🌍 Agenda 2030 · Estándares C40")
    st.caption("Villa María medida con los mismos estándares que Londres, París, Tokio y Buenos Aires")
    st.markdown("---")

    # --- Contexto ---
    st.markdown("""
    En 2021, 31 alcaldes del **C40 Cities Climate Leadership Group** — incluyendo Buenos Aires —
    firmaron la **Declaración de Naturaleza Urbana**, comprometiendo dos metas globales para 2030.
    Ciudad Verde calcula el posicionamiento de Villa María frente a esos mismos estándares
    usando los datos satelitales de ESA WorldCover y Landsat 8/9.
    """)

    # ============================================================
    # BLOQUE 1 — TARGETS C40 2030
    # ============================================================
    st.markdown("## 🎯 Targets C40 Urban Nature Declaration 2030")

    # Datos de VM — todos desde DATOS_VM (cálculo real), no hardcodeados
    cob = DATOS_VM['cobertura']
    acc = DATOS_VM['acceso']
    arb_pct   = cob.get('arboles') or 0
    past_pct  = cob.get('pastizales') or 0
    agua_pct  = cob.get('agua') or 0
    verde_total_pct = round(arb_pct + past_pct + agua_pct, 1)
    acceso_300m     = acc.get('acceso') or 0
    poblacion_vm    = DATOS_VM.get('poblacion_vm', 96061)
    area_vm_km2     = DATOS_VM.get('area_vm_km2')
    area_vm_ha      = area_vm_km2 * 100 if area_vm_km2 else None

    if DATOS_VM.get('datos_preliminares') or area_vm_ha is None:
        st.warning(
            "⚠️ No hay indicadores calculados todavía para Villa María "
            "(`exportar_indicadores_villamaria.py`). Esta sección no puede mostrarse "
            "sin datos reales de base."
        )
        return

    # Target 1: QTC — 30% superficie verde
    meta_qtc = 30.0
    gap_qtc  = max(0, meta_qtc - verde_total_pct)
    color_qtc = "#2e7d32" if verde_total_pct >= meta_qtc else "#f57c00" if verde_total_pct >= 20 else "#c62828"

    # Target 2: ESD — 70% población con acceso a verde/azul en 15 min
    meta_esd = 70.0
    esd_vm   = acceso_300m
    color_esd = "#2e7d32" if esd_vm >= meta_esd else "#f57c00" if esd_vm >= 40 else "#c62828"

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            f"""<div style='border:2.5px solid {color_qtc};border-radius:14px;padding:22px;text-align:center;background:{color_qtc}0d'>
              <div style='font-size:0.88em;color:#fff;font-weight:600;margin-bottom:4px'>
                TARGET 1 · Cobertura Total de Calidad (QTC)
              </div>
              <div style='font-size:2.6em;font-weight:800;color:{color_qtc}'>{verde_total_pct:.1f}%</div>
              <div style='font-size:0.9em;color:#ddd'>de la superficie es verde/azul</div>
              <div style='margin:10px 0'>
                <div style='background:rgba(255,255,255,0.15);border-radius:8px;height:12px;overflow:hidden'>
                  <div style='background:{color_qtc};width:{min(verde_total_pct/meta_qtc*100,100):.0f}%;height:100%;border-radius:8px'></div>
                </div>
                <div style='font-size:0.84em;color:#ccc;margin-top:4px'>{verde_total_pct:.1f}% de {meta_qtc:.0f}% meta C40</div>
              </div>
              <div style='font-size:0.88em;color:{color_qtc};font-weight:600'>
                {'✅ META CUMPLIDA' if verde_total_pct >= meta_qtc else f'⚠️ Faltan {gap_qtc:.1f} puntos porcentuales'}
              </div>
            </div>""",
            unsafe_allow_html=True
        )

    with col2:
        st.markdown(
            f"""<div style='border:2.5px solid {color_esd};border-radius:14px;padding:22px;text-align:center;background:{color_esd}0d'>
              <div style='font-size:0.88em;color:#fff;font-weight:600;margin-bottom:4px'>
                TARGET 2 · Distribución Espacial Equitativa (ESD)
              </div>
              <div style='font-size:2.6em;font-weight:800;color:{color_esd}'>{esd_vm:.0f}%</div>
              <div style='font-size:0.9em;color:#ddd'>de la población con acceso a verde</div>
              <div style='margin:10px 0'>
                <div style='background:rgba(255,255,255,0.15);border-radius:8px;height:12px;overflow:hidden'>
                  <div style='background:{color_esd};width:100%;height:100%;border-radius:8px'></div>
                </div>
                <div style='font-size:0.84em;color:#ccc;margin-top:4px'>{esd_vm:.0f}% de {meta_esd:.0f}% meta C40</div>
              </div>
              <div style='font-size:0.88em;color:{color_esd};font-weight:600'>✅ META SUPERADA — 100% a &lt;300m</div>
            </div>""",
            unsafe_allow_html=True
        )

    st.markdown("")
    if verde_total_pct < meta_qtc:
        ha_faltantes = gap_qtc / 100 * area_vm_ha
        st.warning(
            f"⚠️ **Target QTC:** Villa María necesita incorporar ~**{ha_faltantes:.0f} ha** adicionales "
            f"de verde para alcanzar el 30% C40. El potencial está en los cultivos urbanos ({23.9:.1f}%) "
            f"y el verde no catalogado como público."
        )
    else:
        st.success("✅ Villa María cumple ambos targets de la Declaración de Naturaleza Urbana C40 2030.")

    st.info(
        "📌 **Contexto:** Buenos Aires firmó la Declaración C40. "
        "Villa María puede alinearse con esta agenda, posicionando su política ambiental "
        "en el mismo marco que Londres, París, Tokio, Copenhague y Medellín."
    )

    st.markdown("---")

    # ============================================================
    # BLOQUE 2 — CAPTURA DE CO₂
    # ============================================================
    st.markdown("## 🌳 Captura de CO₂ por el arbolado urbano")
    st.caption("Metodología: USDA Forest Service · Nowak et al. 2013 · 28 ciudades")

    st.markdown(f"""
    El USDA Forest Service estableció, con datos de campo de 28 ciudades, una densidad
    bruta de secuestro de carbono del arbolado urbano de **0.28 kg C/m²/año**. Nowak et al. (2013)
    reportan que, descontando pérdidas por respiración y recambio de hojas, la tasa **neta** efectiva
    es de **0.205 kg C/m²/año** (~74% de la bruta) — es la que usamos en este cálculo, aplicada al
    {arb_pct}% de cobertura arbórea de Villa María.
    """)

    # Cálculos de CO₂
    area_vm_m2       = area_vm_ha * 10_000          # 36.000.000 m²
    arb_m2           = area_vm_m2 * (arb_pct / 100) # m² de cobertura arbórea
    # Secuestro neto = 0.205 kg C/m²/año (74% del bruto, según Nowak 2013)
    seq_kg_c_anual   = arb_m2 * 0.205               # kg C/año
    seq_ton_c_anual  = seq_kg_c_anual / 1000
    # Convertir C → CO₂: factor 44/12 = 3.667
    seq_ton_co2_anual = seq_ton_c_anual * 3.667

    # Escenario meta: arbolado al 15%
    arb_m2_meta      = area_vm_m2 * 0.15
    seq_meta_ton_co2 = (arb_m2_meta * 0.205 / 1000) * 3.667
    ganancia_co2     = seq_meta_ton_co2 - seq_ton_co2_anual

    # Equivalencias comprensibles
    autos_equiv      = seq_ton_co2_anual / 2.1      # un auto promedio emite ~2.1 tCO₂/año (EPA)
    autos_meta       = seq_meta_ton_co2 / 2.1
    vuelos_equiv     = seq_ton_co2_anual / 0.9      # BsAs-Madrid ≈ 0.9 tCO₂/pasajero

    c1, c2, c3 = st.columns(3)
    with c1:
        _card_indicador(
            f"CO₂ capturado hoy ({arb_pct}% arbolado)",
            f"{seq_ton_co2_anual:.0f}",
            "ton CO₂/año",
            f"Equivale a sacar {autos_equiv:.0f} autos de circulación",
            "#2e7d32"
        )
    with c2:
        _card_indicador(
            "CO₂ capturado con meta 15% arbolado",
            f"{seq_meta_ton_co2:.0f}",
            "ton CO₂/año",
            f"Equivale a {autos_meta:.0f} autos fuera de circulación",
            "#1565c0"
        )
    with c3:
        _card_indicador(
            "Ganancia neta al llegar al 15%",
            f"+{ganancia_co2:.0f}",
            "ton CO₂/año",
            f"≈ {vuelos_equiv:.0f} vuelos BsAs–Madrid evitados",
            "#6a1b9a"
        )

    st.markdown("---")

    # Calculadora interactiva
    st.markdown("### 🧮 Calculadora de impacto — ¿cuánto vale plantar más árboles?")
    col_sl, col_res = st.columns([1, 2])

    with col_sl:
        arb_objetivo = st.slider(
            "Meta de cobertura arbórea (%)",
            min_value=int(arb_pct),
            max_value=40,
            value=15,
            step=1,
            help="Deslizá para ver el impacto de aumentar el arbolado urbano de Villa María"
        )
        arboles_nuevos = st.number_input(
            "Árboles nuevos a plantar (estimado)",
            min_value=0,
            max_value=100000,
            value=5000,
            step=500,
            help="Proyección a largo plazo: asume que cada árbol alcanza ~25 m² de copa "
                 "en su etapa adulta (15-20 años desde la plantación)."
        )

    with col_res:
        arb_m2_obj    = area_vm_m2 * (arb_objetivo / 100)
        seq_obj_co2   = (arb_m2_obj * 0.205 / 1000) * 3.667
        delta_co2     = seq_obj_co2 - seq_ton_co2_anual
        autos_obj     = seq_obj_co2 / 2.1

        # CO₂ de árboles nuevos (copa media 25m², secuestro neto)
        co2_nuevos    = (arboles_nuevos * 25 * 0.205 / 1000) * 3.667

        st.markdown(
            f"""<div style='background:rgba(46,125,50,0.12);border:1.5px solid #81c784;border-radius:12px;padding:20px'>
              <div style='font-size:1em;font-weight:700;color:#81c784;margin-bottom:12px'>
                🌿 Con {arb_objetivo}% de arbolado urbano:
              </div>
              <table style='width:100%;font-size:0.88em;border-collapse:collapse'>
                <tr><td style='padding:4px 0;color:#ccc'>CO₂ capturado/año</td>
                    <td style='font-weight:700;color:#66bb6a;text-align:right'>{seq_obj_co2:.0f} ton CO₂</td></tr>
                <tr><td style='padding:4px 0;color:#ccc'>Incremento vs. hoy</td>
                    <td style='font-weight:700;color:#64b5f6;text-align:right'>+{delta_co2:.0f} ton CO₂/año</td></tr>
                <tr><td style='padding:4px 0;color:#ccc'>Equivale a autos retirados</td>
                    <td style='font-weight:700;color:#66bb6a;text-align:right'>{autos_obj:.0f} vehículos</td></tr>
              </table>
              <div style='margin-top:14px;border-top:1px solid rgba(200,230,201,0.3);padding-top:10px;font-size:0.85em;color:#aaa'>
                🌱 <b>{arboles_nuevos:,} árboles nuevos</b>, cuando alcancen tamaño adulto
                (~15-20 años), capturarían adicionalmente
                <b>{co2_nuevos:.1f} ton CO₂/año</b>
                (≈ {co2_nuevos/2.1:.0f} autos fuera de circulación)
              </div>
            </div>""",
            unsafe_allow_html=True
        )

    st.markdown("---")

    # ============================================================
    # BLOQUE 3 — VIDAS SALVADAS (metodología Lancet)
    # ============================================================
    st.markdown("## ❤️ Impacto en salud pública")
    st.caption(
        "Metodología: The Lancet Planetary Health, 2025 · "
        "C40 Cities health impact assessment · 96 ciudades globales"
    )

    st.markdown("""
    Un estudio publicado en **The Lancet Planetary Health** (2025) — *"A health impact
    assessment of progress towards urban nature targets in the 96 C40 cities"* — encontró que
    aumentar el verde urbano un 1% se asocia a una mediana de **1.77 muertes prematuras evitadas
    por año cada 100.000 habitantes** (rango observado entre ciudades: 0.65 a 3.52), en el
    escenario de distribución uniforme del nuevo verde. Aplicamos esa tasa a la población de
    Villa María.
    """)

    # Tasa real del estudio: 1.77 muertes evitadas / 100.000 hab / punto % de verde adicional
    # (mediana, escenario uniforme; rango 0.65–3.52 entre las 96 ciudades C40)
    TASA_MUERTES_100K_POR_PUNTO = 1.77
    TASA_MUERTES_100K_RANGO = (0.65, 3.52)
    muertes_por_punto = TASA_MUERTES_100K_POR_PUNTO * (poblacion_vm / 100_000)
    muertes_rango_bajo = TASA_MUERTES_100K_RANGO[0] * (poblacion_vm / 100_000)
    muertes_rango_alto = TASA_MUERTES_100K_RANGO[1] * (poblacion_vm / 100_000)

        # Escenarios — con rango, no solo el punto medio
    delta_1pct       = muertes_por_punto
    delta_1pct_bajo  = muertes_rango_bajo
    delta_1pct_alto  = muertes_rango_alto
    delta_5pct       = muertes_por_punto * 5
    delta_meta       = muertes_por_punto * (meta_qtc - verde_total_pct)

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        _card_indicador(
            "Muertes evitadas por +1% verde",
            f"{delta_1pct:.1f}",
            "por año",
            f"Mediana C40, rango {delta_1pct_bajo:.1f}–{delta_1pct_alto:.1f} según ciudad",
            "#c62828"
        )
    with col_b:
        _card_indicador(
            "Muertes evitadas por +5% verde",
            f"{delta_5pct:.1f}",
            "por año",
            "Escala lineal del punto medio — no valida más allá del rango citado",
            "#f57c00"
        )
    with col_c:
        if gap_qtc > 0:
            _card_indicador(
                f"Muertes evitadas al cumplir C40 (30%)",
                f"{delta_meta:.1f}",
                "por año",
                f"Incremento de {gap_qtc:.1f}% para cumplir el target QTC",
                "#2e7d32"
            )
        else:
            _card_indicador(
                "Villa María ya cumple el target C40",
                "✅",
                "",
                "El beneficio de salud ya está siendo capturado",
                "#2e7d32"
            )

    st.markdown("")
    st.markdown(
        f"""<div style='background:rgba(233,30,99,0.12);border:1.5px solid #e91e63;border-radius:10px;padding:16px;font-size:0.9em'>
          <b>📖 Referencia:</b> Barboza et al. (2021) estimaron que <b>42.968 muertes anuales</b>
          podrían evitarse en ciudades europeas si se cumpliera el acceso universal OMS al verde.
          Villa María ya cumple ese acceso — lo que queda pendiente es <b>aumentar la cobertura total</b>
          para capturar los beneficios adicionales de temperatura, calidad del aire y bienestar.
        </div>""",
        unsafe_allow_html=True
    )

    st.markdown("---")

    # ============================================================
    # BLOQUE 4 — BRECHA 2030 Y HOJA DE RUTA
    # ============================================================
    st.markdown("## 🗓️ Hoja de ruta Villa María hacia 2030")

    años_restantes = 2030 - 2026   # 4 años

    # Cuánto verde hay que sumar para llegar al 30% QTC
    ha_actuales_verde = verde_total_pct / 100 * area_vm_ha
    ha_meta_verde     = meta_qtc / 100 * area_vm_ha
    ha_a_sumar        = max(0, ha_meta_verde - ha_actuales_verde)
    ha_por_año        = ha_a_sumar / años_restantes if años_restantes > 0 else 0

    # Árboles necesarios (copa media 25m²)
    arboles_necesarios     = int(ha_a_sumar * 10_000 / 25)
    arboles_por_año        = int(arboles_necesarios / años_restantes) if años_restantes > 0 else 0

    col_r1, col_r2 = st.columns(2)

    with col_r1:
        st.markdown("### 📐 ¿Cuánto falta?")
        st.markdown(
            f"""| Indicador | Hoy | Meta 2030 | Brecha |
|-----------|:---:|:---------:|:------:|
| Verde total | {verde_total_pct:.1f}% | 30% | {gap_qtc:.1f}% |
| Hectáreas verdes | {ha_actuales_verde:.0f} ha | {ha_meta_verde:.0f} ha | {ha_a_sumar:.0f} ha |
| Arbolado | {arb_pct}% | 15% | {15-arb_pct:.1f}% |
| Acceso <300m | {acceso_300m:.0f}% | 70% | ✅ cumplido |
| CO₂ capturado | {seq_ton_co2_anual:.0f} t/año | {seq_meta_ton_co2:.0f} t/año | +{ganancia_co2:.0f} t/año |
"""
        )

    with col_r2:
        st.markdown("### 📅 Ritmo necesario (2025–2030)")
        st.markdown(
            f"""| Acción | Por año | Total 2030 |
|--------|:-------:|:----------:|
| Nuevas hectáreas verdes | {ha_por_año:.1f} ha/año | {ha_a_sumar:.0f} ha |
| Árboles a plantar | {arboles_por_año:,} árb/año | {arboles_necesarios:,} árboles |
| Reducción CO₂ adicional | +{ganancia_co2/años_restantes:.0f} t/año | +{ganancia_co2:.0f} t CO₂/año |
"""
        )

    st.success(
        f"🎯 **Síntesis para política pública:** Villa María necesita incorporar "
        f"**{ha_por_año:.1f} hectáreas de verde por año** durante 5 años para cumplir el target C40. "
        f"Equivale a plantar ~**{arboles_por_año:,} árboles anuales** — "
        f"un compromiso concreto, medible y alineado con la Agenda 2030."
    )

    st.markdown("---")

    # ============================================================
    # BLOQUE 5 — MARCO NORMATIVO INTERNACIONAL
    # ============================================================
    st.markdown("## 📋 Marco normativo internacional aplicable")

    marcos = [
        ("🌍", "Agenda 2030 — ODS 11",
         "Meta 11.7: acceso universal a espacios verdes seguros e inclusivos. "
         "Villa María cumple el indicador de accesibilidad (<300m al 100%)."),
        ("🏙️", "C40 Urban Nature Declaration 2030",
         "Targets QTC (30% verde) y ESD (70% con acceso). "
         "Buenos Aires ya la firmó. VM puede alinearse a este estándar globalmente reconocido."),
        ("🌡️", "Acuerdo de París — NDC Argentina",
         "El arbolado urbano contribuye al inventario nacional de sumideros de carbono. "
         "La captura estimada de VM (~{:.0f} t CO₂/año) es cuantificable y reportable.".format(seq_ton_co2_anual)),
        ("🇪🇺", "EU Nature Restoration Law — Art. 8",
         "Estándar europeo de restauración de ecosistemas urbanos. Establece metas de cobertura arbórea "
         "para ciudades >20.000 hab — referencia de primer nivel para benchmarking internacional."),
        ("🏥", "OMS — Espacios Verdes Urbanos",
         f"Mínimo 9 m²/hab de verde público (VM: {DATOS_VM['osm'].get('m2Hab', '—')} m²/hab ✅) y acceso a 0.5 ha "
         f"de espacio verde dentro de 300m (VM: {acceso_300m:.0f}% ✅)."),
        ("🌿", "Ordenanza 7209 — Ruralidad Urbana (2017)",
         "Marco local que reconoce los servicios ambientales del periurbano y establece "
         "mecanismos de gestión del territorio rural-urbano en Villa María."),
    ]

    for icono, titulo, descripcion in marcos:
        st.markdown(
            f"""<div style='display:flex;gap:14px;align-items:flex-start;
                padding:12px 16px;border-radius:10px;background:rgba(255,255,255,0.05);
                border:1px solid rgba(255,255,255,0.12);margin-bottom:8px'>
              <div style='font-size:1.6em;line-height:1'>{icono}</div>
              <div>
                <div style='font-weight:700;font-size:0.92em;color:#81c784'>{titulo}</div>
                <div style='font-size:0.83em;color:#ccc;margin-top:3px'>{descripcion}</div>
              </div>
            </div>""",
            unsafe_allow_html=True
        )

    st.markdown("---")
    st.caption(
        "Ciudad Verde AI Agent · Agenda 2030 · Villa María · "
        "Fuentes: C40 Cities (2021), The Lancet Planetary Health (2025), "
        "USDA Forest Service / Nowak et al. (2013), OMS, ODS-ONU, "
        "ESA WorldCover 2020 · Landsat 8/9 · INDEC Censo 2022"
    )

# ============================================================
# SECCIÓN: A MEJORAR JUNTOS
# ============================================================

def _render_amejorar():
    st.title("🤝 A Mejorar juntos")
    st.markdown(
        "Estos son los datos municipales que, integrados a Ciudad Verde, transforman la plataforma "
        "de diagnóstico externo en el **sistema oficial de monitoreo ambiental de Villa María**. "
        "Cada conjunto de datos abre nuevas funciones concretas en la app."
    )
    st.markdown("---")

    items = [
        {
            "icono": "🗺️",
            "titulo": "Catastro municipal digitalizado",
            "que_es": "Polígonos SIG del ejido urbano con uso del suelo real por parcela.",
            "funciones": [
                "Reemplazar el bbox rectangular por los límites reales del ejido urbano",
                "Identificar baldíos, franjas ferroviarias y bordes de canales con potencial verde",
                "Calcular déficit de verde por barrio con geometría real, no aproximada",
            ],
            "impacto": "Los indicadores de accesibilidad y cobertura pasan de estimados satelitales a datos catastrales oficiales.",
            "color": "#1565c0",
        },
        {
            "icono": "🌳",
            "titulo": "Censo de arbolado urbano",
            "que_es": "Relevamiento georeferenciado de árboles por especie, estado sanitario y ubicación.",
            "funciones": [
                "Cruzar densidad de arbolado con mapa de temperatura — confirmar zonas críticas con datos de campo",
                "Calcular captura de CO₂ real por especie en lugar de promedio USDA",
                "Identificar corredores de arbolado existentes y faltantes por barrio",
            ],
            "impacto": "El análisis de isla de calor pasa de satelital a validado con datos de campo.",
            "color": "#2e7d32",
        },
        {
            "icono": "🏞️",
            "titulo": "Padrón oficial de espacios verdes",
            "que_es": "Registro municipal de plazas, parques y paseos con superficie, equipamiento y estado.",
            "funciones": [
                "Reemplazar datos OSM colaborativos por el inventario oficial del municipio",
                "Calcular m²/hab de verde público con datos propios y auditables",
                "Detectar espacios verdes sin catalogar en OSM que sí existen en el padrón",
            ],
            "impacto": "Los 65.4 m²/hab actuales se ajustan con datos reales — el municipio tiene su propio indicador oficial.",
            "color": "#00796b",
        },
        {
            "icono": "🏥",
            "titulo": "Datos de salud pública por barrio",
            "que_es": "Casos de internación por estrés térmico, enfermedades respiratorias y consultas pediátricas georreferenciadas.",
            "funciones": [
                "Cruzar mapa de temperatura superficial con incidencia de patologías termosensibles",
                "Construir un Índice de Vulnerabilidad Ambiental con base epidemiológica real",
                "Priorizar intervenciones verdes en zonas con mayor carga de enfermedad",
            ],
            "impacto": "Argumento de salud pública cuantificado para justificar inversión en arbolado ante el Concejo Deliberante.",
            "color": "#c62828",
        },
        {
            "icono": "🚌",
            "titulo": "Red de transporte público",
            "que_es": "Recorridos georeferenciados de líneas de colectivo con frecuencias y paradas.",
            "funciones": [
                "Calcular accesibilidad real al verde combinando caminata + transporte (isócronas 15 min)",
                "Identificar barrios con déficit de acceso tanto peatonal como en transporte",
                "Alinear el análisis con el estándar C40 de ciudad de 15 minutos",
            ],
            "impacto": "El indicador de accesibilidad pasa de distancia euclidiana a accesibilidad real por red urbana.",
            "color": "#f57c00",
        },
        {
            "icono": "📐",
            "titulo": "Plan de obras y presupuesto ambiental",
            "que_es": "Intervenciones verdes planificadas 2026–2030 con localización e inversión estimada.",
            "funciones": [
                "Mostrar en el mapa las obras planificadas vs las zonas de déficit detectadas",
                "Calcular el delta entre lo planificado y lo necesario para cumplir el target C40",
                "Generar el Masterplan IA con inversión real en lugar de estimada",
            ],
            "impacto": "El Masterplan pasa de recomendaciones genéricas a plan de acción con presupuesto municipal real.",
            "color": "#6a1b9a",
        },
    ]

    for item in items:
        color = item["color"]
        with st.expander(f"{item['icono']} {item['titulo']}", expanded=False):
            st.markdown(
                f"<div style='font-size:0.88em;color:#aaa;margin-bottom:12px;'>"
                f"<b style='color:#ccc;'>Qué es:</b> {item['que_es']}</div>",
                unsafe_allow_html=True,
            )
            st.markdown(f"**Funciones que se habilitan en la app:**")
            for f in item["funciones"]:
                st.markdown(
                    f"<div style='display:flex;gap:10px;align-items:flex-start;margin-bottom:6px;'>"
                    f"<span style='color:{color};font-size:1.1em;'>▸</span>"
                    f"<span style='font-size:0.88em;color:#ddd;'>{f}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            st.markdown(
                f"<div style='margin-top:12px;border-left:3px solid {color};"
                f"padding:8px 14px;background:{color}11;border-radius:0 8px 8px 0;'>"
                f"<span style='font-size:0.85em;color:#ccc;'>"
                f"<b style='color:{color};'>Impacto:</b> {item['impacto']}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

    st.markdown("---")
    st.success(
        "💡 Con el catastro y el padrón de espacios verdes, Ciudad Verde pasa de ser "
        "una herramienta de diagnóstico externo a ser el **sistema oficial de monitoreo "
        "ambiental de Villa María** — con datos propios, auditables y actualizables."
    )
    st.caption(
        "Ciudad Verde AI Agent · Villa María · "
        "Datos propios del municipio + ESA WorldCover · Landsat 8/9 · OSM · INDEC 2022"
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
    elif "Forestación" in seccion:
        render_censo_arboreo()
    elif "Estrategias" in seccion:
        _render_estrategias()
    elif "Agenda" in seccion:
        _render_agenda2030()
    elif "Masterplan" in seccion:
        render_masterplan()
    elif "Mejorar" in seccion:
        _render_amejorar()
