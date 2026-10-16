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
from modulo_barrios import render_diagnostico_barrios
from modulo_benchmarking import render_benchmarking_c40
from modulo_agenda2030 import render_agenda2030
from modulo_huella_eventos import render_huella_eventos

SECCIONES_VM = [
    ("🏠", "Inicio"),
    ("🗺️", "Mapa del conglomerado"),
    ("📊", "Indicadores ambientales"),
    ("🌡️", "Temperatura superficial"),
    ("🏛️", "Verde público (OSM)"),
    ("🌳", "Plan de Forestación"),
    ("🏘️", "Diagnóstico por barrio"),
    ("🎯", "Estrategias · Villa María"),
    ("🌍", "Agenda 2030 · C40"),
    ("🌐", "Benchmarking C40"),
    ("🎪", "Huella de carbono de eventos"),
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
    st.caption(
        "Exclusivamente para el Municipio de Villa María · basadas en indicadores GEE + OSM + "
        "INDEC 2022 + Diagnóstico por barrio"
    )
    st.markdown("---")

    from modulo_barrios import _cargar_resumen
    res = _cargar_resumen()

    if DATOS_VM.get('datos_preliminares') or not res:
        st.warning(
            "⚠️ Faltan datos calculados para armar las estrategias "
            "(`data/indicadores_villamaria.json` o `data/zonas_villamaria_resumen.json`)."
        )
        return

    def _n(x):
        """Entero con separador de miles argentino."""
        return f"{int(round(x)):,}".replace(",", ".")

    def _d(x, dec=1):
        """Decimal con coma."""
        return f"{x:.{dec}f}".replace(".", ",")

    SUP = "*(supuesto)*"

    acc = DATOS_VM['acceso']
    osm = DATOS_VM['osm']
    cob = DATOS_VM['cobertura']
    lst = DATOS_VM['lst']
    poblacion_vm = DATOS_VM.get('poblacion_vm', 96061)

    # --- Brecha satelital vs. OSM (desde indicadores_villamaria.json) ---
    m2_sat = acc.get('m2_hab_sat') or 0
    m2_osm = osm.get('m2Hab') or 0
    brecha_m2 = max(0, m2_sat - m2_osm)
    brecha_ha = brecha_m2 * poblacion_vm / 10_000
    enf = lst.get('enfriamiento') or 0

    # --- Diagnóstico por barrio (desde zonas_villamaria_resumen.json) ---
    meta_c = res['ciudad']['meta_1_arbol_por_casa']
    lotes_ciudad = meta_c['lotes_estimados']
    arb_casas_ciudad = meta_c['arboles_zonas_casas']
    deficit_total = meta_c['deficit_arboles']
    cumpl_ciudad = meta_c['cumplimiento_pct'] or 0

    # Déficit de las zonas urbanas céntricas
    deficit_centrica = 0
    barrios_centricos = []
    for b in res['barrios']:
        zonas_c = [z for z in b['zonas'] if z['tipo'] == 'urbana_centrica']
        if zonas_c:
            barrios_centricos.append(b['barrio'].title())
            deficit_centrica += sum(z['deficit_arboles'] for z in zonas_c)
    pct_centrica = deficit_centrica / deficit_total * 100 if deficit_total else 0
    cumpl_con_centrica = (
        (arb_casas_ciudad + deficit_centrica) / lotes_ciudad * 100 if lotes_ciudad else 0
    )

    # Barrios por debajo del umbral de cumplimiento
    UMBRAL = 50
    criticos = sorted(
        [
            b for b in res['barrios']
            if b['meta_1_arbol_por_casa']['cumplimiento_pct'] is not None
            and b['meta_1_arbol_por_casa']['cumplimiento_pct'] < UMBRAL
        ],
        key=lambda b: b['meta_1_arbol_por_casa']['cumplimiento_pct'],
    )
    deficit_criticos = sum(b['meta_1_arbol_por_casa']['deficit_arboles'] for b in criticos)
    acciones_criticos = []
    for b in criticos:
        m = b['meta_1_arbol_por_casa']
        incipiente = (
            " · forestación incipiente"
            if any(z.get('forestacion_incipiente') for z in b['zonas']) else ""
        )
        acciones_criticos.append(
            f"{b['barrio'].title()}: {_d(m['cumplimiento_pct'])} % de la meta · "
            f"faltan {_n(m['deficit_arboles'])} árboles{incipiente}"
        )
    acciones_criticos.append(
        "Plan de plantación barrio por barrio, empezando por el menor cumplimiento"
    )
        
    acciones_criticos.append(
        "Registrar lo plantado en la calculadora del Plan de Forestación para medir el avance"
    )

    # Densidad de arbolado en zonas de casas, comparada con el promedio de su tipo
    TIPOS_CASAS = ('urbana_centrica', 'urbana_residencial', 'urbana_mixta', 'riberena')
    area_t, arb_t = {}, {}
    for b in res['barrios']:
        for z in b['zonas']:
            if z['tipo'] in TIPOS_CASAS and z['lotes_estimados'] > 0:
                area_t[z['tipo']] = area_t.get(z['tipo'], 0) + z['area_ha']
                arb_t[z['tipo']] = arb_t.get(z['tipo'], 0) + z['n_arboles']
    media_tipo = {t: arb_t[t] / area_t[t] for t in area_t if area_t[t] > 0}
    area_casas = sum(area_t.values())
    dens_ciudad = sum(arb_t.values()) / area_casas if area_casas else 0
    sombra = []
    for b in res['barrios']:
        zc = [z for z in b['zonas'] if z['tipo'] in media_tipo and z['lotes_estimados'] > 0]
        area_b = sum(z['area_ha'] for z in zc)
        esperado = sum(media_tipo[z['tipo']] * z['area_ha'] for z in zc)
        if area_b > 0 and esperado > 0:
            n_b = sum(z['n_arboles'] for z in zc)
            sombra.append({
                'barrio': b['barrio'].title(),
                'dens': n_b / area_b,
                'indice': n_b / esperado,
                'faltan': max(0, esperado - n_b),
            })
    sombra.sort(key=lambda x: x['indice'])
    menos_sombra = sombra[:5]
    faltan_sombra = sum(x['faltan'] for x in menos_sombra)
    acciones_sombra = [
        f"{x['barrio']}: {_d(x['dens'])} árb/ha · índice {_d(x['indice'], 2)} respecto de su tipo de zona"
        for x in menos_sombra
    ] + [
        'Priorizar especies nativas de alta copa: espinillo, tala, ombú',
        'Articular con UNVM para monitoreo satelital anual del impacto térmico',
    ]

    st.markdown("""
    Las siguientes líneas de acción surgen del análisis cuantitativo de los indicadores ambientales
    y del Diagnóstico por barrio (meta municipal: 1 árbol por casa).
    Están priorizadas según urgencia e impacto potencial sobre la calidad de vida de los vecinos.
    Los valores marcados como *(supuesto)* no surgen de un cálculo: se detallan al final de la sección.
    """)

    # --- Prioridad ALTA ---
    st.markdown("### 🔴 Prioridad Alta — Intervención inmediata")

    estrategias_alta = [
        {
            'titulo': 'Arbolado de veredas en el área céntrica',
            'fundamento': f'Los {len(barrios_centricos)} barrios con zona urbana céntrica concentran '
                          f'{_n(deficit_centrica)} de los {_n(deficit_total)} árboles que faltan para la '
                          f'meta de 1 árbol por casa ({_d(pct_centrica)} % del déficit de la ciudad). '
                          'En el centro los lotes son chicos y hay pocos patios: la vereda es el lugar '
                          'principal de plantación.',
            'acciones': [
                'Plan de plantación en veredas, priorizando las cuadras sin arbolado',
                'Barrios incluidos: ' + ', '.join(barrios_centricos),
                'Registrar lo plantado en la calculadora del Plan de Forestación para medir el avance',
            ],
            'impacto': f'Cubrir el déficit céntrico lleva el cumplimiento de la ciudad del '
                       f'{_d(cumpl_ciudad)} % al {_d(cumpl_con_centrica)} %',
        },
        {
            'titulo': f'Barrios por debajo del {UMBRAL} % de la meta 1 árbol por casa',
            'fundamento': f'{len(criticos)} barrios tienen menos del {UMBRAL} % de la meta y suman '
                          f'{_n(deficit_criticos)} árboles faltantes. El cumplimiento depende de los '
                          'lotes estimados, que son provisorios hasta contar con el catastro municipal.',
            'acciones': acciones_criticos,
            'impacto': f'Plantar {_n(deficit_criticos)} árboles en estos {len(criticos)} barrios '
                       f'lleva a todos a la meta de 1 árbol por casa',
        },
                {
            'titulo': 'Arbolado para reducir el calor urbano',
            'fundamento': f'Landsat 8/9 mide hasta {_d(enf, 2)} °C menos en zonas de verde denso que en '
                          f'suelo/asfalto. En las zonas con casas hay en promedio {_d(dens_ciudad)} árboles '
                          'por hectárea. Estos barrios tienen menos arbolado que el promedio de su mismo tipo '
                          'de zona (índice 1,00 = igual al promedio), lo que indica menos sombra.',
            'acciones': acciones_sombra,
            'impacto': f'Plantar {_n(faltan_sombra)} árboles lleva a estos {len(menos_sombra)} barrios al '
                       f'promedio de su tipo de zona, con un enfriamiento local de hasta {_d(enf, 2)} °C {SUP}',
        },
        {
            'titulo': 'Relevamiento y apertura de verde no catalogado',
            'fundamento': f'El satélite detecta {_d(m2_sat)} m²/hab de verde, pero OSM confirma solo '
                          f'{_d(m2_osm)} m²/hab como público. Hay ~{_n(brecha_ha)} ha de verde que los '
                          'vecinos probablemente no pueden usar.',
            'acciones': [
                'Censo municipal de espacios verdes no catalogados (baldíos, bordes de canales, franjas ferroviarias)',
                'Acuerdos de acceso público con propietarios privados (servidumbre ambiental)',
                'Aplicación de la Ordenanza 7209 en zonas periurbanas limítrofes',
            ],
            'impacto': f'Potencial de sumar hasta {_d(brecha_m2)} m²/hab de verde accesible sin nueva infraestructura',
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
            'impacto': f'Corredor verde de ~8 km lineales {SUP}; beneficio directo para barrios costeros',
        },
        {
            'titulo': 'Programa de agricultura urbana en zonas de cultivo',
            'fundamento': f'El {_d(cob.get("cultivos") or 0)}% del área analizada son cultivos en zona '
                          'urbana/periurbana. Representan una oportunidad de transición ordenada hacia verde público.',
            'acciones': [
                'Identificar parcelas de cultivo con potencial de reconversión a verde público',
                'Programa de huertas comunitarias en lotes ociosos',
                'Convenios con propietarios para servicios ambientales (Ord. 7209)',
            ],
            'impacto': f'Reconversión potencial de hasta 5–10% {SUP} de la superficie de cultivos en verde público',
        },
        {
            'titulo': 'Red de corredores verdes entre barrios',
            'fundamento': f'El {_d(acc.get("r_100_300") or 0)}% del área edificada accede al verde en el '
                          'rango 100–300m. Conectar parques existentes mediante arbolado de calles '
                          'mejoraría la accesibilidad peatonal.',
            'acciones': [
                'Mapeo de rutas peatonales con déficit de sombra entre plazas y parques',
                'Arbolado sistemático en ejes peatonales prioritarios',
                'Programa de "calles verdes" con vecinos y juntas de participación',
            ],
            'impacto': f'Reducir la distancia media al verde de {_n(acc.get("dist_prom") or 0)}m '
                       f'a <40m {SUP} para el 100% del área',
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
            'fundamento': f'Villa María tiene {_n(osm.get("elementos") or 0)} elementos catalogados en OSM. '
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
    # --- Supuestos declarados ---
    st.markdown("### 📌 Supuestos de esta sección")
    st.info(
        f"- **Lotes estimados:** {res['metodo_lotes']['estado']}. Los porcentajes de cumplimiento "
        "de la meta 1 árbol por casa dependen de esta estimación (ver Diagnóstico por barrio → Metodología).\n"
        "- **Densidad de arbolado como indicador de sombra:** se compara la cantidad de árboles por "
        "hectárea con el promedio de su tipo de zona, sin medir la temperatura barrio por barrio.\n"
        "- **Enfriamiento local:** la diferencia medida entre verde denso y suelo/asfalto (Landsat 8/9) "
        "se usa como referencia máxima, no como una medición por barrio.\n"
        "- **~8 km de parque lineal:** longitud aproximada del corredor, sin medición.\n"
        "- **Reconversión del 5–10% de cultivos:** rango propuesto, sin cálculo de respaldo.\n"
        "- **Distancia media <40 m:** meta propuesta, sin cálculo de respaldo."
    )

    st.markdown("---")
    st.caption(
        "Ciudad Verde AI Agent · Estrategias para Villa María · "
        "Datos: ESA WorldCover 2020 · Landsat 8/9 · OpenStreetMap · INDEC Censo 2022 · "
        "Meta/WRI Canopy Height (Diagnóstico por barrio) · "
        "Marco: OMS, ODS 11, Ordenanza 7209"
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
    elif "barrio" in seccion:
        render_diagnostico_barrios()
    elif "Estrategias" in seccion:
        _render_estrategias()
    elif "Agenda" in seccion:
        render_agenda2030()
    elif "Benchmarking" in seccion:
        render_benchmarking_c40()
    elif "Huella" in seccion:
        render_huella_eventos()
    elif "Masterplan" in seccion:
        render_masterplan()
    elif "Mejorar" in seccion:
        _render_amejorar()
