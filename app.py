"""
app.py — Ciudad Verde AI Agent
============================
App Streamlit unificada multi-ciudad.
Reemplaza: demo.py, demo_sanfrancisco.py, dashboard.py, demo_v2.py

Correr con:
    streamlit run app.py
"""

import ee
import os
import json
import streamlit as st
import folium
from streamlit_folium import st_folium

from modulo_temperatura  import cargar_lst, render_temperatura
from modulo_osm          import cargar_osm, render_osm
from modulo_censo        import render_censo
from modulo_ayuda        import ayuda_cobertura, ayuda_accesibilidad, ayuda_temperatura, ayuda_osm, ayuda_censo, ayuda_comparativa, ayuda_diagnostico
from modulo_villamaria   import render_modulo_villamaria
from modulo_asistente    import render_asistente_sidebar

# ── Inyección de estilos ──────────────────────────────────
def _inyectar_css():
    css_path = os.path.join(os.path.dirname(__file__), 'assets', 'style.css')
    if os.path.exists(css_path):
        with open(css_path, encoding='utf-8') as f:
            css = f.read()
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

_inyectar_css()

# ============================================================
# CONFIGURACIÓN DE PÁGINA
# ============================================================
st.set_page_config(
    page_title="Ciudad Verde AI Agent",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# LOGIN
# ============================================================
_LOGIN_USER = os.environ.get("APP_USERNAME", "admin")
_LOGIN_PASS = os.environ.get("APP_PASSWORD", "greencity")

def _render_login():
    # CSS completo de login dark — se aplica solo en esta pantalla
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=Space+Mono:wght@400;700&display=swap');

    /* Fondo oscuro global en login */
    .stApp { background: #050810 !important; }

    /* Gradientes ambientales */
    .stApp::before {
        content:'';position:fixed;top:-200px;left:-200px;
        width:600px;height:600px;
        background:radial-gradient(circle,rgba(99,40,180,0.18) 0%,transparent 70%);
        pointer-events:none;z-index:0;
    }
    .stApp::after {
        content:'';position:fixed;bottom:-150px;right:-150px;
        width:500px;height:500px;
        background:radial-gradient(circle,rgba(0,180,220,0.12) 0%,transparent 70%);
        pointer-events:none;z-index:0;
    }

    /* Ocultar sidebar y header en login */
    [data-testid="stSidebar"] { display:none !important; }
    [data-testid="stHeader"]  { display:none !important; }
    #MainMenu, footer         { display:none !important; }

    /* Centrar contenido */
    .block-container {
        max-width: 420px !important;
        margin: 0 auto !important;
        padding-top: 12vh !important;
        background: transparent !important;
    }

    /* Box de login */
    .cv-login-box {
        background: rgba(10,14,32,0.82);
        border: 0.5px solid rgba(120,140,255,0.28);
        border-radius: 16px;
        padding: 36px 32px 28px 32px;
        backdrop-filter: blur(20px);
        margin-bottom: 20px;
        position: relative;
        overflow: hidden;
    }
    .cv-login-box::before {
        content:'';display:block;height:1px;
        background:linear-gradient(90deg,transparent,rgba(120,100,255,0.5),transparent);
        margin-bottom:24px;
    }
    .cv-login-logo {
        text-align:center;margin-bottom:24px;
    }
    .cv-login-mark {
        width:48px;height:48px;
        background:linear-gradient(135deg,#6228b4,#00b4dc);
        border-radius:10px;
        display:inline-flex;align-items:center;justify-content:center;
        font-family:'Space Mono',monospace;font-size:20px;font-weight:700;color:#fff;
        margin-bottom:12px;
        box-shadow:0 0 24px rgba(99,40,180,0.4);
    }
    .cv-login-name {
        font-family:'Space Mono',monospace;font-size:15px;
        font-weight:700;letter-spacing:0.10em;color:#d0d8f8;
        display:block;
    }
    .cv-login-sub {
        font-family:'Space Mono',monospace;font-size:9px;
        letter-spacing:0.14em;color:rgba(170,176,200,0.55);
        text-transform:uppercase;margin-top:4px;display:block;
    }

    /* Labels de inputs */
    .stTextInput label {
        font-family:'Space Mono',monospace !important;
        font-size:9px !important;font-weight:600 !important;
        letter-spacing:0.14em !important;text-transform:uppercase !important;
        color:rgba(170,176,200,0.7) !important;
    }

    /* Inputs */
    .stTextInput > div > div > input {
        background:rgba(8,12,28,0.85) !important;
        border:0.5px solid rgba(120,140,255,0.26) !important;
        border-radius:8px !important;
        color:#fff !important;
        font-family:'Space Grotesk',sans-serif !important;
        font-size:13px !important;
        padding:10px 14px !important;
    }
    .stTextInput > div > div > input:focus {
        border-color:#9060ff !important;
        box-shadow:0 0 0 1px rgba(144,96,255,0.3) !important;
    }
    .stTextInput > div > div > input::placeholder {
        color:rgba(170,176,200,0.4) !important;
    }

    /* Botón Ingresar */
    .stButton > button {
        background:linear-gradient(135deg,#6228b4,#00b4dc) !important;
        border:none !important;border-radius:8px !important;
        font-family:'Space Grotesk',sans-serif !important;
        font-size:14px !important;font-weight:600 !important;
        color:#fff !important;letter-spacing:0.04em !important;
        padding:11px !important;
        transition:opacity 0.2s !important;
        margin-top:6px !important;
    }
    .stButton > button:hover { opacity:0.88 !important; }

    /* Error */
    .stAlert { border-radius:8px !important; }
    </style>

    <div class="cv-login-box">
        <div class="cv-login-logo">
            <div class="cv-login-mark">CV</div>
            <span class="cv-login-name">CIUDAD VERDE</span>
            <span class="cv-login-sub">AI Agent · Córdoba, Argentina</span>
        </div>
        <div style="height:0.5px;background:rgba(120,140,255,0.14);margin-bottom:20px;"></div>
    </div>
    """, unsafe_allow_html=True)

    with st.container():
        usuario   = st.text_input("Usuario",    key="login_user",   placeholder="Tu usuario")
        contrasena = st.text_input("Contraseña", key="login_pass",  placeholder="Tu contraseña", type="password")
        if st.button("Ingresar →", use_container_width=True, type="primary"):
            if usuario == _LOGIN_USER and contrasena == _LOGIN_PASS:
                st.session_state["autenticado"] = True
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos.")

if not st.session_state.get("autenticado"):
    _render_login()
    st.stop()

# ============================================================
# CIUDADES — carga dinámica desde JSON
# ============================================================

def _cargar_ciudades():
    """
    Fusiona datos_ciudades.json (geometría/config) con
    resultados_ciudades.json (datos GEE calculados, si existe).
    """
    base_path = os.path.dirname(__file__)

    with open(os.path.join(base_path, 'datos_ciudades.json'), encoding='utf-8') as f:
        config = json.load(f)

    # Resultados GEE (generados por paso11_batch_ciudades.py)
    res_path = os.path.join(base_path, 'resultados_ciudades.json')
    resultados = {}
    if os.path.exists(res_path):
        with open(res_path, encoding='utf-8') as f:
            resultados = json.load(f)

    # Datos por defecto para ciudades sin resultados aún
    def_cobertura = {'arboles':0,'arbustos':0,'pastizales':0,'cultivos':0,'edificado':0,'suelo':0,'agua':0}
    def_acceso    = {'acceso':0,'dist_prom':None,'m2_hab_sat':0,'r_0_100':0,'r_100_300':0,'r_300_500':0,'r_500_mas':0}
    def_lst       = {'imagenes':0,'tMedia':None,'tUrbano':None,'tVerde':None,'tP95':None,'tP5':None,
                     'deltaUHI':None,'tNdviAlto':None,'tNdviBajo':None,'enfriamiento':None,'zonas':[]}
    def_osm       = {'elementos':0,'areaHa':0,'m2Hab':0}

    # Valores conocidos para VM y SF (ya calculados)
    conocidos = {
        'villamaria': {
            'cobertura': {'arboles':8.2,'arbustos':0,'pastizales':14.2,'cultivos':23.9,'edificado':50.6,'suelo':1.6,'agua':1.3},
            'acceso': {'acceso':100.0,'dist_prom':48,'m2_hab_sat':93.2,'r_0_100':91.1,'r_100_300':8.9,'r_300_500':0.0,'r_500_mas':0.0},
            'lst': {'imagenes':13,'tMedia':39.97,'tUrbano':39.51,'tVerde':39.34,'tP95':44.56,'tP5':37.07,
                    'deltaUHI':0.17,'tNdviAlto':38.21,'tNdviBajo':39.88,'enfriamiento':1.67,
                    'zonas':[{'nombre':'Noroeste (VM centro-N)','temp':40.76},{'nombre':'Noreste (VN norte)','temp':39.85},
                             {'nombre':'Suroeste (VM sur)','temp':39.73},{'nombre':'Sureste (VN sur)','temp':39.55}]},
            'osm': {'elementos':1027,'areaHa':784.7,'m2Hab':65.4},
            'calificacion': 'A - Excelente', 'puntaje': 7,
            'fortalezas': ['Accesibilidad universal (100% a <300m)','Buena cobertura arbórea (8.2%)','Corredor ecológico: río Ctalamochita','Verde público: 65.4 m²/hab (OSM)'],
            'debilidades': ['27.9 m²/hab de verde no accesible al público','Zona Noroeste más caliente (+0.8°C)','Cultivos en área urbana (23.9%)'],
            'recomendaciones': [('🔴','Forestar zona Noroeste','40.76°C en VM centro-norte. Intervención prioritaria.'),
                                ('🟡','Publicitar 335 ha de verde sin catalogar','Relevar y abrir donde sea posible.'),
                                ('🟡','Parque lineal río Ctalamochita','Ciclovías y senderos en ambas márgenes.'),
                                ('🟢','Monitoreo LST anual','Medir impacto de cada intervención.')],
        },
        'sanfrancisco': {
            'cobertura': {'arboles':1.6,'arbustos':0,'pastizales':16.4,'cultivos':24.3,'edificado':56.8,'suelo':0.9,'agua':0.0},
            'acceso': {'acceso':100.0,'dist_prom':50,'m2_hab_sat':68.8,'r_0_100':91.0,'r_100_300':9.0,'r_300_500':0.0,'r_500_mas':0.0},
            'lst': {'imagenes':6,'tMedia':39.87,'tUrbano':40.2,'tVerde':39.19,'tP95':42.34,'tP5':36.65,
                    'deltaUHI':1.01,'tNdviAlto':36.41,'tNdviBajo':40.36,'enfriamiento':3.95,'zonas':[]},
            'osm': {'elementos':87,'areaHa':81.6,'m2Hab':13.2},
            'calificacion': 'B - Muy Bueno', 'puntaje': 6,
            'fortalezas': ['Accesibilidad universal (100% a <300m)','Verde público: 13.2 m²/hab (OMS ✅)','Ciudad compacta','Trazado en damero'],
            'debilidades': ['Arbolado crítico: 1.6%','Isla de calor 6× mayor que VM','Verde mayormente canchas'],
            'recomendaciones': [('🔴','Forestación masiva urgente','Triplicar cobertura arbórea en 5 años.'),
                                ('🔴','Reducir isla de calor (ΔT 1.01°C)','Foco en avenidas y espacios sin sombra.'),
                                ('🟡','Bordes arbolados en canchas','Sumar sombra sin quitar superficie de juego.'),
                                ('🟢','Monitoreo LST anual','Medir impacto de cada árbol plantado.')],
        }
    }

    ciudades = {}
    for key, cfg in config.items():
        # Prioridad: datos conocidos > resultados GEE > defaults
        if key in conocidos:
            datos = conocidos[key]
        elif key in resultados:
            r = resultados[key]
            datos = {
                'cobertura': r.get('cobertura', def_cobertura),
                'acceso':    r.get('acceso', def_acceso),
                'lst':       r.get('lst') or def_lst,
                'osm':       def_osm,
                'calificacion': 'Pendiente', 'puntaje': 0,
                'fortalezas': [], 'debilidades': [],
                'recomendaciones': [],
            }
        else:
            datos = {
                'cobertura': def_cobertura, 'acceso': def_acceso,
                'lst': def_lst, 'osm': def_osm,
                'calificacion': 'Sin datos', 'puntaje': 0,
                'fortalezas': [], 'debilidades': [], 'recomendaciones': [],
            }

        ciudades[key] = {**cfg, **datos}

    # Aliases de acceso directo para compatibilidad con el resto de la app
    for key, c in ciudades.items():
        c['acceso_pct']  = c['acceso']['acceso']
        c['dist_prom']   = c['acceso']['dist_prom']
        c['m2_hab_sat']  = c['acceso']['m2_hab_sat'] or 0
        c['r_0_100']     = c['acceso']['r_0_100']
        c['r_100_300']   = c['acceso']['r_100_300']
        c['r_300_500']   = c['acceso']['r_300_500']
        c['r_500_mas']   = c['acceso']['r_500_mas']
        # cobertura con clave minúscula
        cob = c['cobertura']
        c['arb_pct']     = cob.get('arboles', 0)
        c['past_pct']    = cob.get('pastizales', 0)
        c['cult_pct']    = cob.get('cultivos', 0)
        c['edif_pct']    = cob.get('edificado', 0)
        c['agua_pct']    = cob.get('agua', 0)
    return ciudades

CIUDADES = _cargar_ciudades()

SECCIONES = [
    ("🏠", "Inicio"),
    ("📍", "Área de estudio"),
    ("🌾", "Cobertura del suelo"),
    ("📏", "Accesibilidad"),
    ("🌡️", "Temperatura superficial"),
    ("🏛️", "Verde público (OSM)"),
    ("👥", "Censo 2022"),
    ("📊", "Comparativa"),
    ("📝", "Diagnóstico"),
]

# ============================================================
# GEE
# ============================================================
@st.cache_resource
def conectar_gee():
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
    return True

@st.cache_data(show_spinner=False)
def cargar_worldcover(ciudad_key):
    c = CIUDADES[ciudad_key]
    area = ee.Geometry.Polygon([c["coords_area"]])
    wc   = ee.Image('ESA/WorldCover/v100/2020').clip(area)
    verde = wc.eq(10).Or(wc.eq(20)).Or(wc.eq(30)).selfMask()
    edif  = wc.eq(50).selfMask()
    dist  = verde.fastDistanceTransform(1000).sqrt().multiply(10)
    dist_edif = dist.updateMask(edif)

    def suma(img): return list(img.reduceRegion(ee.Reducer.sum(), area, 10, maxPixels=1e9).getInfo().values())[0]
    def media(img): return list(img.reduceRegion(ee.Reducer.mean(), area, 10, maxPixels=1e9).getInfo().values())[0]

    total  = suma(ee.Image.constant(1))
    t_edif = suma(edif)
    cerc   = suma(dist_edif.lt(300))

    zonas_data = {}
    if ciudad_key == "villamaria":
        zonas = {
            "Noroeste": ee.Geometry.Polygon([[-63.28,-32.39],[-63.24,-32.39],[-63.24,-32.415],[-63.28,-32.415]]),
            "Noreste":  ee.Geometry.Polygon([[-63.24,-32.39],[-63.20,-32.39],[-63.20,-32.415],[-63.24,-32.415]]),
            "Suroeste": ee.Geometry.Polygon([[-63.28,-32.415],[-63.24,-32.415],[-63.24,-32.44],[-63.28,-32.44]]),
            "Sureste":  ee.Geometry.Polygon([[-63.24,-32.415],[-63.20,-32.415],[-63.20,-32.44],[-63.24,-32.44]]),
        }
        for nom, geom in zonas.items():
            g  = geom.intersection(area)
            te = suma(edif.clip(g)) or 1
            ce = suma(dist_edif.lt(300).clip(g)) or 0
            pm = media(dist_edif.clip(g)) or 0
            zonas_data[nom] = {
                "acceso_pct": round(ce/te*100, 1),
                "dist_prom":  round(pm, 0),
                "ha_edif":    round(te*100/1e6, 1),
            }

    return {
        "pct_acceso": (cerc/t_edif)*100,
        "dist_prom":  media(dist_edif),
        "zonas":      zonas_data,
        "total_ha":   t_edif*100/1e6,
    }

# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown("<style>div[data-testid='stSelectbox'] > div { cursor: pointer !important; }</style>", unsafe_allow_html=True)

    # ── Topbar Ciudad Verde ──
    st.markdown(
        """
        <div style="display:flex;align-items:center;gap:10px;padding:4px 0 14px 0;
             border-bottom:0.5px solid rgba(120,140,255,0.14);margin-bottom:14px;">
          <div style="width:26px;height:26px;background:linear-gradient(135deg,#6228b4,#00b4dc);
               border-radius:6px;display:flex;align-items:center;justify-content:center;
               font-family:'Space Mono',monospace;font-size:12px;font-weight:700;color:#fff;
               flex-shrink:0;">CV</div>
          <div>
            <div style="font-family:'Space Mono',monospace;font-size:11px;font-weight:700;
                 letter-spacing:0.10em;color:#c8d0f0;">CIUDAD VERDE</div>
            <div style="font-family:'Space Mono',monospace;font-size:8px;
                 color:rgba(170,176,200,0.55);letter-spacing:0.08em;margin-top:1px;">
                 AI AGENT · CÓRDOBA ARG</div>
          </div>
          <div style="margin-left:auto;display:flex;align-items:center;gap:5px;
               font-family:'Space Mono',monospace;font-size:8px;
               color:rgba(64,220,144,0.7);letter-spacing:0.05em;">
            <div style="width:5px;height:5px;border-radius:50%;background:#40dc90;
                 animation:cv-pulse 2s ease-in-out infinite;"></div>
            ACTIVO
          </div>
        </div>
        <style>
        @keyframes cv-pulse{0%,100%{opacity:1}50%{opacity:0.3}}
        </style>
        """,
        unsafe_allow_html=True,
    )

    # ── Selector de módulo principal ──
    st.markdown(
        "<div style='font-family:\"Space Mono\",monospace;font-size:8px;"
        "letter-spacing:0.14em;text-transform:uppercase;"
        "color:rgba(160,175,210,0.5);margin-bottom:6px;'>Módulo</div>",
        unsafe_allow_html=True,
    )
    modulo = st.radio(
        "Módulo",
        ["🏙️ Villa María", "🌍 Provincia de Córdoba"],
        label_visibility="collapsed",
        key="modulo_principal",
    )
    st.markdown("---")

    if modulo == "🌍 Provincia de Córdoba":
        # Excluir Villa María y Villa Nueva del selector provincial
        ciudades_prov = {
            k: v for k, v in CIUDADES.items()
            if k not in ('villamaria',)
        }
        ciudades_ord = sorted(ciudades_prov.keys(), key=lambda k: -ciudades_prov[k]['poblacion'])
        ciudad_key = st.selectbox(
            "Ciudad",
            ciudades_ord,
            format_func=lambda k: f"{CIUDADES[k]['emoji']} {CIUDADES[k]['nombre']} ({CIUDADES[k]['poblacion']:,} hab)",
        )
        ciudad = CIUDADES[ciudad_key]

        cal = ciudad.get('calificacion', 'Sin datos')
        if cal not in ('Sin datos', 'Pendiente'):
            st.success(f"✅ Datos completos · {cal}")
        elif cal == 'Pendiente':
            st.warning("⏳ Datos parciales — análisis GEE disponible")
        else:
            st.info("🔄 Sin análisis previo — datos se calcularán en vivo")

        st.markdown("---")
        seccion = st.radio(
            "Sección",
            [f"{e} {n}" for e, n in SECCIONES],
            label_visibility="collapsed",
            key="seccion_provincia",
        )
        st.markdown("---")
        st.caption(f"📍 {ciudad['nombre']}")
        st.caption(f"👥 {ciudad['poblacion']:,} hab · {ciudad['area_km2']} km²")
        st.caption(f"⭐ {ciudad['calificacion']}")
    else:
        # Módulo Villa María — el sidebar lo completa render_modulo_villamaria()
        ciudad_key = 'villamaria'
        ciudad = CIUDADES[ciudad_key]
        seccion = None

    # ── Asistente IA — siempre visible al fondo del sidebar ──
    render_asistente_sidebar()

# ============================================================
# CONEXIÓN GEE
# ============================================================
with st.spinner("Conectando con Earth Engine..."):
    conectar_gee()

# ============================================================
# MÓDULO VILLA MARÍA — delegar completamente
# ============================================================
if modulo == "🏙️ Villa María":
    render_modulo_villamaria()
    st.stop()

# ============================================================
# SECCIÓN: INICIO — Módulo Provincia de Córdoba
# ============================================================
if "Inicio" in seccion:
    st.title("🌿 Ciudad Verde AI Agent")
    st.subheader("Diagnóstico inteligente de espacios verdes — Provincia de Córdoba")
    st.markdown("---")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Acceso <300m", f"{ciudad['acceso_pct']:.0f}%", "Meta OMS: 100%")
    with col2:
        st.metric("Distancia promedio", f"{ciudad['dist_prom']} m")
    with col3:
        st.metric("Verde público / hab", f"{ciudad['osm']['m2Hab']} m²", "OMS: 9-15 m²")
    with col4:
        st.metric("Isla de calor (ΔT)", f"+{ciudad['lst']['deltaUHI'] or 0}°C",
                  "vs zona verde", delta_color="inverse")

    st.markdown("---")
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(f"""
        ### {ciudad['emoji']} {ciudad['nombre']}
        - **Población:** {ciudad['poblacion']:,} hab
        - **Área analizada:** {ciudad['area_km2']} km²
        - **Calificación:** {ciudad['calificacion']}
        - **Arbolado:** {ciudad['arb_pct']}%
        """)
    with col_b:
        st.markdown("""
        ### 🛰️ Tecnología
        - Google Earth Engine + Landsat 8/9
        - ESA WorldCover 2020 (10m)
        - OpenStreetMap (API Overpass)
        - INDEC Censo 2022
        - Streamlit · Folium
        """)

    st.info("👈 Usá el menú lateral para navegar entre secciones y ciudades.")

# ============================================================
# SECCIÓN: ÁREA DE ESTUDIO
# ============================================================
elif "Área" in seccion:
    st.title(f"📍 Área de estudio · {ciudad['nombre']}")
    st.markdown("---")

    # --- Mapa con capas seleccionables ---
    m = folium.Map(
        location=[ciudad['lat'], ciudad['lon']],
        zoom_start=ciudad['zoom'],
        tiles=None,
    )

    # Capas base
    folium.TileLayer(
        tiles='https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
        attr='© OpenStreetMap contributors',
        name='🗺️ OpenStreetMap',
        max_zoom=19,
    ).add_to(m)
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='© Esri — Esri, DigitalGlobe, GeoEye, i-cubed, USDA FSA, USGS, AEX, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, GIS User Community',
        name='🛰️ Satélite',
        max_zoom=19,
    ).add_to(m)
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}',
        attr='© Esri — Esri, DeLorme, NAVTEQ, TomTom, Intermap, iPC, USGS, FAO, NPS, NRCAN, GeoBase, Kadaster NL, Ordnance Survey, Esri Japan, METI, Esri China, and the GIS User Community',
        name='🗻 Topográfico',
        max_zoom=19,
    ).add_to(m)
    folium.TileLayer(
        tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}',
        attr='© Google',
        name='🌍 Híbrido Google',
        max_zoom=20,
    ).add_to(m)

    # Grupo: Área de estudio (ciudad seleccionada)
    from folium import FeatureGroup
    grupo_area = FeatureGroup(name='📐 Área de estudio', show=True)
    coords_folium = [[c[1], c[0]] for c in ciudad['coords_area']]
    coords_folium.append(coords_folium[0])
    folium.Polygon(
        locations=coords_folium,
        popup=folium.Popup(
            f"<b>{ciudad['nombre']}</b><br>{ciudad['area_km2']} km² · {ciudad['poblacion']:,} hab",
            max_width=220,
        ),
        tooltip=f"{ciudad['nombre']} — área de análisis",
        color="#2e7d32", weight=2.5, fill=True,
        fill_color="#4caf50", fill_opacity=0.18,
    ).add_to(grupo_area)
    folium.CircleMarker(
        [ciudad['lat'], ciudad['lon']], radius=9,
        color="#1b5e20", weight=2,
        fill=True, fill_color="#4caf50", fill_opacity=0.95,
        tooltip=ciudad['nombre'],
        popup=folium.Popup(
            f"<b>{ciudad['nombre']}</b><br>"
            f"👥 {ciudad['poblacion']:,} hab · {ciudad['area_km2']} km²<br>"
            f"⭐ {ciudad.get('calificacion','—')}",
            max_width=220,
        ),
    ).add_to(grupo_area)
    if ciudad.get('coords_rio'):
        coords_rio = [[c[1], c[0]] for c in ciudad['coords_rio']]
        folium.PolyLine(
            coords_rio, color="#1565c0", weight=3,
            dash_array="6 4",
            tooltip="Curso de agua",
        ).add_to(grupo_area)
    grupo_area.add_to(m)

    # Grupo: Todas las ciudades del proyecto (capa opcional)
    _cal_color = {
        'A - Excelente': '#1b5e20', 'B - Muy Bueno': '#2196f3',
        'B': '#2196f3', 'A': '#1b5e20',
        'Pendiente': '#ff9800', 'Sin datos': '#9e9e9e',
    }
    grupo_todas = FeatureGroup(name='🏙️ Todas las ciudades', show=True)
    for k, c in CIUDADES.items():
        if k == ciudad_key:
            continue
        cal_c = c.get('calificacion', 'Sin datos')
        color_c = _cal_color.get(cal_c, '#9e9e9e')
        folium.CircleMarker(
            [c['lat'], c['lon']], radius=6,
            color=color_c, weight=1.5,
            fill=True, fill_color=color_c, fill_opacity=0.7,
            tooltip=c['nombre'],
            popup=folium.Popup(
                f"<b>{c['emoji']} {c['nombre']}</b><br>"
                f"Depto. {c.get('dept','—')}<br>"
                f"👥 {c['poblacion']:,} hab<br>"
                f"⭐ {cal_c}",
                max_width=200,
            ),
        ).add_to(grupo_todas)
    grupo_todas.add_to(m)

    folium.LayerControl(position='topright', collapsed=False).add_to(m)

    st_folium(m, width="100%", height=520, returned_objects=[])

    # Leyenda de colores de calificación
    st.markdown(
        "<div style='display:flex;gap:18px;margin-top:4px;font-size:0.82em'>"
        "<span>🟢 A · Excelente</span>"
        "<span>🔵 B · Muy Bueno</span>"
        "<span>🟠 Pendiente</span>"
        "<span>⚫ Sin datos</span>"
        "</div>",
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)
    with c1: st.metric("Superficie", f"{ciudad['area_km2']} km²")
    with c2: st.metric("Población", f"{ciudad['poblacion']:,} hab")
    with c3: st.metric("Densidad", f"~{ciudad['poblacion']//int(ciudad['area_km2']):,} hab/km²")

# ============================================================
# SECCIÓN: COBERTURA DEL SUELO
# ============================================================
elif "Cobertura" in seccion:
    st.title(f"🌾 Cobertura del suelo · {ciudad['nombre']}")
    st.caption("Fuente: ESA WorldCover 2020 · resolución 10m")
    ayuda_cobertura()
    st.markdown("---")

    cob_display = {'Árboles': ciudad['arb_pct'], 'Pastizales': ciudad['past_pct'], 'Cultivos': ciudad['cult_pct'], 'Edificado': ciudad['edif_pct'], 'Agua': ciudad['agua_pct']}
    col1, col2 = st.columns([1, 2])
    with col1:
        for nombre, pct in cob_display.items():
            st.metric(nombre, f"{pct:.1f}%")
    with col2:
        st.bar_chart(cob_display)

    st.markdown("---")

    # --- Mapa de distribución de cobertura ---
    st.markdown("#### 🗺️ Distribución espacial de cobertura")
    st.caption("Paleta WorldCover: verde = arbolado · amarillo = pastizal · naranja = cultivos · gris = edificado · azul = agua")

    m_cob = folium.Map(
        location=[ciudad['lat'], ciudad['lon']],
        zoom_start=ciudad['zoom'],
        tiles=None,
    )

    # Capa base satélite por defecto (para ver contraste)
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='© Esri',
        name='🛰️ Satélite',
        max_zoom=19,
    ).add_to(m_cob)
    folium.TileLayer(
        tiles='https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
        attr='© OpenStreetMap contributors',
        name='🗺️ OpenStreetMap',
        max_zoom=19,
    ).add_to(m_cob)

    # Overlay WorldCover via GEE XYZ tiles (si GEE conectado)
    try:
        area_ee = ee.Geometry.Polygon([ciudad['coords_area']])
        wc = ee.Image('ESA/WorldCover/v100/2020').clip(area_ee)
        palette = ['006400','ffbb22','ffff4c','f096ff','fa0000',
                   'b4b4b4','f0f0f0','0064c8','0096a0','00cf75','fae6a0']
        vis = {'min': 10, 'max': 110, 'palette': palette}
        map_id = wc.getMapId(vis)
        tiles_url = map_id['tile_fetcher'].url_format
        from folium import FeatureGroup
        grupo_wc = FeatureGroup(name='🌍 WorldCover (cobertura)', show=True)
        folium.TileLayer(
            tiles=tiles_url,
            attr='ESA WorldCover 2020 · Google Earth Engine',
            name='🌍 WorldCover',
            overlay=True,
            opacity=0.75,
        ).add_to(grupo_wc)
        grupo_wc.add_to(m_cob)
    except Exception:
        # Si GEE no está disponible, mostrar polígono del área con colores simbólicos
        pass

    # Polígono del área de estudio siempre visible
    coords_cob = [[c[1], c[0]] for c in ciudad['coords_area']]
    coords_cob.append(coords_cob[0])
    folium.Polygon(
        locations=coords_cob,
        tooltip="Área de análisis",
        color="#2e7d32", weight=2, fill=False,
    ).add_to(m_cob)

    # Leyenda de cobertura con datos reales de la ciudad
    leyenda_html = f"""
    <div style="position:fixed;bottom:20px;left:20px;z-index:9999;
                background:white;padding:10px 14px;border-radius:8px;
                box-shadow:0 2px 8px rgba(0,0,0,0.25);font-size:0.82em;line-height:1.7">
        <b>Cobertura · {ciudad['nombre']}</b><br>
        <span style="color:#006400">█</span> Árboles &nbsp;<b>{ciudad['arb_pct']:.1f}%</b><br>
        <span style="color:#ffbb22">█</span> Pastizales &nbsp;<b>{ciudad['past_pct']:.1f}%</b><br>
        <span style="color:#e65100">█</span> Cultivos &nbsp;<b>{ciudad['cult_pct']:.1f}%</b><br>
        <span style="color:#757575">█</span> Edificado &nbsp;<b>{ciudad['edif_pct']:.1f}%</b><br>
        <span style="color:#1565c0">█</span> Agua &nbsp;<b>{ciudad['agua_pct']:.1f}%</b>
    </div>"""
    m_cob.get_root().html.add_child(folium.Element(leyenda_html))

    folium.LayerControl(position='topright', collapsed=False).add_to(m_cob)
    st_folium(m_cob, width="100%", height=460, returned_objects=[])

    st.markdown("---")
    arb = ciudad['arb_pct']
    edif = ciudad['edif_pct']
    cult = ciudad['cult_pct']

    if arb < 3:
        st.error(f"⚠️ Cobertura arbórea crítica: {arb}% — muy por debajo del promedio urbano recomendado (10-15%)")
    elif arb < 8:
        st.warning(f"⚠️ Cobertura arbórea baja: {arb}% — hay margen de mejora significativo")
    else:
        st.success(f"✅ Buena cobertura arbórea: {arb}%")

    if cult > 15:
        st.info(f"💡 {cult:.1f}% de cultivos dentro del área urbana — oportunidad de planificación verde ante futuras urbanizaciones")

# ============================================================
# SECCIÓN: ACCESIBILIDAD
# ============================================================
elif "Accesibilidad" in seccion:
    st.title(f"📏 Accesibilidad a espacios verdes · {ciudad['nombre']}")
    st.caption("Fuente: ESA WorldCover + Google Earth Engine · cálculo de distancia euclidiana")
    ayuda_accesibilidad()
    st.markdown("---")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Acceso <300m", f"{ciudad['acceso_pct']:.0f}%", "Meta OMS: 100%")
    with c2:
        st.metric("Distancia promedio", f"{ciudad['dist_prom']} m")
    with c3:
        m2 = ciudad['m2_hab_sat']
        st.metric("m² verde/hab (sat.)", f"{m2:.0f} m²", "OMS: 9-15 m²")

    st.markdown("---")
    st.markdown("#### Distribución por distancia al verde más cercano")

    rangos = [
        ("0 – 100 m",   ciudad['r_0_100'],   "#1b5e20"),
        ("100 – 300 m", ciudad['r_100_300'],  "#66bb6a"),
        ("300 – 500 m", ciudad['r_300_500'],  "#ffcc80"),
        ("Más de 500 m",ciudad['r_500_mas'],  "#ef9a9a"),
    ]
    for label, pct, color in rangos:
        col_l, col_b, col_v = st.columns([2, 5, 1])
        with col_l: st.markdown(f"<small>{label}</small>", unsafe_allow_html=True)
        with col_b:
            st.markdown(
                f"""<div style='background:#e8f5e9;border-radius:6px;height:18px;margin-top:4px'>
                <div style='width:{max(pct,0.5):.1f}%;background:{color};height:18px;border-radius:6px'></div>
                </div>""", unsafe_allow_html=True)
        with col_v: st.markdown(f"**{pct:.1f}%**")

    if ciudad['acceso_pct'] >= 100:
        st.success("✅ Cumple el estándar OMS: toda la población tiene verde a menos de 300m")
    elif ciudad['acceso_pct'] >= 80:
        st.warning("⚠️ Buena cobertura pero hay sectores sin acceso cercano")
    else:
        st.error("❌ Cobertura insuficiente — muchos vecinos sin verde accesible")

    st.caption("Nota: incluye todo tipo de verde satelital, no solo espacios públicos. Ver sección OSM para verde público real.")

    with st.expander("🔍 Detalle por zonas (solo Villa María)"):
        if ciudad_key == "villamaria":
            with st.spinner("Cargando datos por zonas..."):
                datos_wc = cargar_worldcover(ciudad_key)
            if datos_wc['zonas']:
                cols = st.columns(4)
                for i, (nom, z) in enumerate(datos_wc['zonas'].items()):
                    with cols[i]:
                        color = "green" if z['acceso_pct'] >= 95 else "orange"
                        st.markdown(f"**{nom}**")
                        st.markdown(f"Acceso: :{color}[{z['acceso_pct']}%]")
                        st.metric("Dist. media", f"{z['dist_prom']} m")
                        st.caption(f"{z['ha_edif']} ha edificadas")
        else:
            st.info("Análisis por zonas disponible solo para Villa María.")

# ============================================================
# SECCIÓN: TEMPERATURA
# ============================================================
elif "Temperatura" in seccion:
    st.title(f"🌡️ Temperatura superficial · {ciudad['nombre']}")
    st.markdown("---")

    lst = ciudad['lst']

    ayuda_temperatura()
    st.warning(
        "⚠️ **LST ≠ temperatura del aire.** Mide el calor emitido por suelo y asfalto. "
        "En verano puede superar 40°C mientras el termómetro marca 32°C. "
        "Lo relevante es la **diferencia entre zonas** (isla de calor UHI)."
    )

    st.markdown("---")
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("Temp. media (LST)", f"{lst['tMedia']}°C", f"{lst['imagenes']} imágenes")
    with c2:
        delta = f"+{lst['deltaUHI']}°C vs verde"
        st.metric("Zona urbana", f"{lst['tUrbano']}°C", delta, delta_color="inverse")
    with c3: st.metric("Zona verde", f"{lst['tVerde']}°C")
    with c4: st.metric("Punto más caliente (P95)", f"{lst['tP95']}°C")

    st.markdown("---")
    col_uhi, col_enf = st.columns(2)

    with col_uhi:
        st.markdown("### 🏙️ Isla de calor urbano")
        uhi = lst['deltaUHI']
        color = "#f44336" if uhi > 3 else "#ff9800" if uhi > 1.5 else "#4caf50"
        nivel = "🔴 ALTO" if uhi > 3 else "🟡 MODERADO" if uhi > 1.5 else "🟢 BAJO"
        pct   = min(uhi/6*100, 100)
        st.markdown(f"**Intensidad:** {nivel} — **ΔT = +{uhi}°C**")
        st.markdown(
            f"""<div style='background:#e0e0e0;border-radius:6px;height:14px;margin:8px 0'>
            <div style='width:{pct:.0f}%;background:{color};height:14px;border-radius:6px'></div>
            </div><div style='display:flex;justify-content:space-between;font-size:0.75em;color:#888'>
            <span>0°C</span><span>1.5°C</span><span>3°C</span><span>6°C+</span></div>""",
            unsafe_allow_html=True
        )
        if lst['zonas']:
            st.markdown("**Por zonas:**")
            for z in lst['zonas']:
                diff = z['temp'] - lst['tMedia']
                color_z = "#f44336" if diff > 0.5 else "#2196f3" if diff < -0.5 else "#888"
                st.markdown(
                    f"<div style='display:flex;justify-content:space-between;font-size:0.85em'>"
                    f"<span>{z['nombre']}</span>"
                    f"<span style='color:{color_z};font-weight:600'>{z['temp']}°C "
                    f"({'+' if diff>0 else ''}{diff:.2f}°C)</span></div>",
                    unsafe_allow_html=True
                )

    with col_enf:
        st.markdown("### 🌿 Efecto enfriador de la vegetación")
        enf = lst['enfriamiento']
        st.markdown(f"""
        | Cobertura | Temperatura |
        |-----------|:-----------:|
        | 🌳 Verde denso (NDVI >0.4) | **{lst['tNdviAlto']}°C** |
        | 🏗️ Suelo/asfalto (NDVI <0.2) | **{lst['tNdviBajo']}°C** |
        | ❄️ Enfriamiento | **{enf}°C menos** |
        """)
        if enf > 3:
            st.success(f"✅ Alto potencial: cada ha de arbolado puede reducir hasta {enf}°C la temperatura local.")
        else:
            st.info(f"💡 Con más forestación el enfriamiento podría superar los 3°C en verano.")

# ============================================================
# SECCIÓN: VERDE PÚBLICO (OSM)
# ============================================================
elif "OSM" in seccion:
    st.title(f"🏛️ Verde público · {ciudad['nombre']}")
    st.caption("Fuente: OpenStreetMap · API Overpass · datos colaborativos")
    st.markdown("---")

    ayuda_osm()
    st.markdown("""
    **¿Por qué OSM además del satélite?**
    El satélite detecta todo el verde (patios privados, baldíos, cultivos).
    OSM solo cataloga lo que la comunidad confirmó como **espacio de uso público**.
    """)

    osm_cache = ciudad['osm']
    c1, c2, c3 = st.columns(3)
    with c1: st.metric("Espacios catalogados", osm_cache['elementos'])
    with c2: st.metric("Área pública total", f"{osm_cache['areaHa']} ha")
    with c3:
        m2 = osm_cache['m2Hab']
        oms = "✅ OMS" if m2 >= 9 else "⚠️ bajo OMS"
        st.metric("m² público / hab", f"{m2} m²", oms)

    diff = ciudad['m2_hab_sat'] - osm_cache['m2Hab']
    st.warning(
        f"⚠️ **Brecha satelital vs público:** el satélite detecta {ciudad['m2_hab_sat']} m²/hab "
        f"pero OSM solo confirma {osm_cache['m2Hab']} m²/hab como accesible. "
        f"**{diff:.1f} m²/hab** es verde que los vecinos probablemente no pueden usar."
    )

    st.markdown("---")
    with st.spinner("Consultando OpenStreetMap..."):
        datos_osm = cargar_osm(ciudad['bbox_osm'], ciudad['poblacion'])

    render_osm(datos_osm, m2_hab_satelital=ciudad['m2_hab_sat'], poblacion=ciudad['poblacion'])

# ============================================================
# SECCIÓN: CENSO 2022
# ============================================================
elif "Censo" in seccion:
    st.title(f"👥 Censo 2022 · {ciudad['nombre']}")
    ayuda_censo()
    st.markdown("---")
    render_censo(ciudad_key)

# ============================================================
# SECCIÓN: COMPARATIVA
# ============================================================
elif "Comparativa" in seccion:
    st.title("📊 Comparativa entre ciudades")
    ayuda_comparativa()
    st.markdown("---")

    vm = CIUDADES['villamaria']
    sf = CIUDADES['sanfrancisco']

    st.markdown("### Indicadores principales")
    col1, col2 = st.columns(2)

    indicadores = [
        ("Arbolado urbano",          f"{vm['arb_pct']}%",                 f"{sf['arb_pct']}%",                "bad"),
        ("Acceso <300m",             f"{vm['acceso_pct']:.0f}%",          f"{sf['acceso_pct']:.0f}%",         "good"),
        ("Distancia promedio",       f"{vm['dist_prom']} m",              f"{sf['dist_prom']} m",             "normal"),
        ("m² verde público/hab",     f"{vm['osm']['m2Hab']} m²",         f"{sf['osm']['m2Hab']} m²",         "normal"),
        ("Isla de calor ΔT",         f"+{vm['lst']['deltaUHI']}°C",      f"+{sf['lst']['deltaUHI']}°C",      "inverse"),
        ("Enfriamiento por verde",   f"-{vm['lst']['enfriamiento']}°C",   f"-{sf['lst']['enfriamiento']}°C",  "normal"),
        ("Calificación",             vm['calificacion'],                  sf['calificacion'],                 "normal"),
    ]

    with col1:
        st.markdown(f"### 🏙️ {vm['nombre']}")
        for label, val_vm, _, _ in indicadores:
            st.metric(label, val_vm)

    with col2:
        st.markdown(f"### 🏘️ {sf['nombre']}")
        for label, val_vm, val_sf, dc in indicadores:
            # Calcular delta numérico donde aplique
            st.metric(label, val_sf)

    st.markdown("---")
    st.markdown("### 🔑 Diferencias clave")
    st.markdown(f"""
    | Indicador | {vm['nombre']} | {sf['nombre']} | Diferencia |
    |-----------|:---:|:---:|:---:|
    | Arbolado | {vm['arb_pct']}% | {sf['arb_pct']}% | 🔴 VM tiene 5× más árboles |
    | Verde público/hab | {vm['osm']['m2Hab']} m² | {sf['osm']['m2Hab']} m² | VM tiene 5× más verde público |
    | Isla de calor | +{vm['lst']['deltaUHI']}°C | +{sf['lst']['deltaUHI']}°C | SF tiene 6× mayor UHI |
    | Enfriamiento potencial | {vm['lst']['enfriamiento']}°C | {sf['lst']['enfriamiento']}°C | SF podría ganar {sf['lst']['enfriamiento']}°C con arbolado |
    | Acceso <300m | {vm['acceso_pct']:.0f}% | {sf['acceso_pct']:.0f}% | ✅ Ambas cumplen OMS |
    """)

    st.info(
        "💡 **Conclusión:** Villa María tiene mejor infraestructura verde. San Francisco tiene igual "
        "accesibilidad pero urgente necesidad de arbolado — su potencial de enfriamiento (3.95°C) "
        "es el argumento más fuerte para un plan de forestación municipal."
    )

# ============================================================
# SECCIÓN: DIAGNÓSTICO
# ============================================================
elif "Diagnóstico" in seccion:
    st.title(f"📝 Diagnóstico · {ciudad['nombre']}")
    ayuda_diagnostico()
    st.markdown("---")

    # Calificación
    col_cal, col_txt = st.columns([1, 3])
    with col_cal:
        color_cal = "#2e7d32" if ciudad['puntaje'] >= 6 else "#ff9800" if ciudad['puntaje'] >= 4 else "#f44336"
        st.markdown(
            f"""<div style='background:{color_cal}22;border:3px solid {color_cal};
                border-radius:12px;padding:20px;text-align:center'>
              <div style='font-size:2.5em;font-weight:700;color:{color_cal}'>{ciudad['calificacion']}</div>
              <div style='color:#555;margin-top:6px'>{ciudad['puntaje']}/7 puntos</div>
            </div>""",
            unsafe_allow_html=True
        )
    with col_txt:
        col_f, col_d = st.columns(2)
        with col_f:
            st.markdown("### ✅ Fortalezas")
            for f in ciudad['fortalezas']:
                st.markdown(f"- {f}")
        with col_d:
            st.markdown("### ⚠️ Debilidades")
            for d in ciudad['debilidades']:
                st.markdown(f"- {d}")

    st.markdown("---")
    st.markdown("### 💡 Recomendaciones")
    for icono, titulo, texto in ciudad['recomendaciones']:
        color = "#f44336" if icono == "🔴" else "#ff9800" if icono == "🟡" else "#4caf50"
        st.markdown(
            f"""<div style='border-left:4px solid {color};padding:12px 16px;
                margin:8px 0;background:{color}11;border-radius:0 8px 8px 0'>
              <strong>{icono} {titulo}</strong><br>
              <span style='font-size:0.9em'>{texto}</span>
            </div>""",
            unsafe_allow_html=True
        )

    st.markdown("---")
    st.caption(
        f"Ciudad Verde AI Agent · {ciudad['nombre']} · "
        "Datos: ESA WorldCover 2020 · Landsat 8/9 · OpenStreetMap · INDEC Censo 2022"
    )
