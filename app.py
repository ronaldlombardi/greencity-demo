"""
app.py — GreenCity AI Agent
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

from modulo_temperatura import cargar_lst, render_temperatura
from modulo_osm         import cargar_osm, render_osm
from modulo_censo       import render_censo
from modulo_ayuda       import ayuda_cobertura, ayuda_accesibilidad, ayuda_temperatura, ayuda_osm, ayuda_censo, ayuda_comparativa, ayuda_diagnostico

# ============================================================
# CONFIGURACIÓN DE PÁGINA
# ============================================================
st.set_page_config(
    page_title="GreenCity AI Agent",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

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
    st.markdown("## 🌿 GreenCity Agent")
    st.markdown("---")

    ciudades_ord = sorted(CIUDADES.keys(), key=lambda k: -CIUDADES[k]['poblacion'])
    ciudad_key = st.selectbox(
        "Ciudad",
        ciudades_ord,
        format_func=lambda k: f"{CIUDADES[k]['emoji']} {CIUDADES[k]['nombre']} ({CIUDADES[k]['poblacion']:,} hab)",
    )
    ciudad = CIUDADES[ciudad_key]
    if not ciudad['lst']['tMedia']:
        st.info("Sin datos GEE — correr paso11_batch_ciudades.py")

    st.markdown("---")

    seccion = st.radio(
        "Sección",
        [f"{e} {n}" for e, n in SECCIONES],
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.caption(f"📍 {ciudad['nombre']}")
    st.caption(f"👥 {ciudad['poblacion']:,} hab · {ciudad['area_km2']} km²")
    st.caption(f"⭐ {ciudad['calificacion']}")

# ============================================================
# CONEXIÓN GEE
# ============================================================
with st.spinner("Conectando con Earth Engine..."):
    conectar_gee()

# ============================================================
# SECCIÓN: INICIO
# ============================================================
if "Inicio" in seccion:
    st.title("🌿 GreenCity AI Agent")
    st.subheader("Diagnóstico inteligente de espacios verdes urbanos")
    st.markdown("---")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Acceso <300m", f"{ciudad['acceso']:.0f}%", "Meta OMS: 100%")
    with col2:
        st.metric("Distancia promedio", f"{ciudad['dist_prom']} m")
    with col3:
        st.metric("Verde público / hab", f"{ciudad['osm']['m2Hab']} m²", "OMS: 9-15 m²")
    with col4:
        st.metric("Isla de calor (ΔT)", f"+{ciudad['lst']['deltaUHI']}°C",
                  "vs zona verde", delta_color="inverse")

    st.markdown("---")
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(f"""
        ### {ciudad['emoji']} {ciudad['nombre']}
        - **Población:** {ciudad['poblacion']:,} hab
        - **Área analizada:** {ciudad['area_km2']} km²
        - **Calificación:** {ciudad['calificacion']}
        - **Arbolado:** {ciudad['cobertura']['Árboles']}%
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

    m = folium.Map(location=[ciudad['lat'], ciudad['lon']],
                   zoom_start=ciudad['zoom'], tiles='CartoDB positron')

    coords_folium = [[c[1], c[0]] for c in ciudad['coords_area']]
    coords_folium.append(coords_folium[0])
    folium.Polygon(
        locations=coords_folium,
        popup=f"{ciudad['nombre']} — {ciudad['area_km2']} km²",
        color="#2e7d32", weight=2, fill=True,
        fill_color="#4caf50", fill_opacity=0.15,
    ).add_to(m)
    folium.CircleMarker(
        [ciudad['lat'], ciudad['lon']], radius=8,
        color="#1b5e20", fill=True, fill_color="#4caf50", fill_opacity=0.9,
        popup=f"{ciudad['nombre']} — {ciudad['poblacion']:,} hab",
    ).add_to(m)
    if ciudad['coords_rio']:
        coords_rio = [[c[1], c[0]] for c in ciudad['coords_rio']]
        folium.PolyLine(
            coords_rio, color="#2196f3", weight=3,
            dash_array="8 8", popup="Río Ctalamochita",
        ).add_to(m)

    st_folium(m, width=900, height=480)

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

    cob = ciudad['cobertura']
    col1, col2 = st.columns([1, 2])
    with col1:
        for nombre, pct in cob.items():
            st.metric(nombre, f"{pct:.1f}%")
    with col2:
        st.bar_chart(cob)

    st.markdown("---")
    arb = cob['Árboles']
    edif = cob['Edificado']
    cult = cob['Cultivos']

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
        st.metric("Acceso <300m", f"{ciudad['acceso']:.0f}%", "Meta OMS: 100%")
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

    if ciudad['acceso'] >= 100:
        st.success("✅ Cumple el estándar OMS: toda la población tiene verde a menos de 300m")
    elif ciudad['acceso'] >= 80:
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
        ("Arbolado urbano",          f"{vm['cobertura']['Árboles']}%",    f"{sf['cobertura']['Árboles']}%",   "bad"),
        ("Acceso <300m",             f"{vm['acceso']:.0f}%",              f"{sf['acceso']:.0f}%",             "good"),
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
    | Arbolado | {vm['cobertura']['Árboles']}% | {sf['cobertura']['Árboles']}% | 🔴 VM tiene 5× más árboles |
    | Verde público/hab | {vm['osm']['m2Hab']} m² | {sf['osm']['m2Hab']} m² | VM tiene 5× más verde público |
    | Isla de calor | +{vm['lst']['deltaUHI']}°C | +{sf['lst']['deltaUHI']}°C | SF tiene 6× mayor UHI |
    | Enfriamiento potencial | {vm['lst']['enfriamiento']}°C | {sf['lst']['enfriamiento']}°C | SF podría ganar {sf['lst']['enfriamiento']}°C con arbolado |
    | Acceso <300m | {vm['acceso']:.0f}% | {sf['acceso']:.0f}% | ✅ Ambas cumplen OMS |
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
        f"GreenCity AI Agent · {ciudad['nombre']} · "
        "Datos: ESA WorldCover 2020 · Landsat 8/9 · OpenStreetMap · INDEC Censo 2022"
    )
