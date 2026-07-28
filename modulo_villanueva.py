"""
modulo_villanueva.py — Ciudad Verde AI Agent
=============================================
Módulo específico para Villa Nueva (Córdoba, Argentina).
- Análisis ambiental propio de Villa Nueva.
- Estrategias y políticas públicas: exclusivamente Villa Nueva.
- Zonificación oficial: Código Urbano Rural 2025 (IDECOR / Municipalidad
  de Villa Nueva), 32 zonas normativas agrupadas en 6 macro-categorías
  para lectura rápida (ver ZONAS_VN). El detalle completo por zona
  oficial se usa en el mapa interactivo (data/zonificacion_villanueva.geojson).
"""

import os
import json
import streamlit as st
import folium
from streamlit_folium import st_folium
from folium import FeatureGroup

RUTA_ZONIFICACION = os.path.join(os.path.dirname(__file__), 'data', 'zonificacion_villanueva.geojson')

# ============================================================
# DATOS DE VILLA NUEVA
# ============================================================
# ⚠️ VALORES PRELIMINARES — cobertura, acceso, temperatura y OSM
# todavía no fueron calculados con GEE/Landsat/OSM para Villa Nueva
# en particular. Son estimaciones ilustrativas para poder construir
# y validar la interfaz. Se reemplazan por cálculo real en el
# siguiente paso del plan (ver conversación de proyecto).

DATOS_VN = {
    'cobertura': {
        'arboles': 15.0, 'arbustos': 0, 'pastizales': 18.0,
        'cultivos': 20.0, 'edificado': 38.0, 'suelo': 1.5, 'agua': 7.5
    },
    'acceso': {
        'acceso': 100.0, 'dist_prom': 40, 'm2_hab_sat': 95.0,
        'r_0_100': 92.0, 'r_100_300': 8.0, 'r_300_500': 0.0, 'r_500_mas': 0.0
    },
    'lst': {
        'tMedia': 39.55, 'tUrbano': 39.30, 'tVerde': 38.20,
        'tP95': 44.00, 'tP5': 36.80, 'deltaUHI': 0.10,
        'tNdviAlto': 38.00, 'tNdviBajo': 39.60, 'enfriamiento': 1.70,
    },
    'osm': {'elementos': None, 'areaHa': None, 'm2Hab': None},
    'calificacion': 'Por calcular',
    'puntaje': None,
    'poblacion_vn': 23000,
    'area_vn_km2': 13.6,
    'datos_preliminares': True,
}

# ============================================================
# ZONIFICACIÓN — macro-categorías agrupando las 32 zonas oficiales
# del Código Urbano Rural 2025 (campo 'desig' en el geojson fuente)
# ============================================================

ZONAS_VN = {
    'Centro': {
        'label': 'Centro',
        'zonas_oficiales': ['ZCen', 'ZCenA', 'ZCenR'],
        'color': '#c62828',
    },
    'Residencial': {
        'label': 'Residencial',
        'zonas_oficiales': ['ZR1', 'ZR2A', 'ZR2B', 'ZR2C', 'ZR2D', 'ZR2E', 'ZR2F'],
        'color': '#f9a825',
    },
    'ComercialMixta': {
        'label': 'Comercial / Mixta',
        'zonas_oficiales': ['ZComR1', 'ZComR2', 'ZComR3', 'ZComI1', 'ZComI2',
                             'ZComRecre4', 'ZComServ5'],
        'color': '#6a1b9a',
    },
    'IndustrialEspecial': {
        'label': 'Industrial / Especial',
        'zonas_oficiales': ['ZIAE', 'ZE'],
        'color': '#455a64',
    },
    'VerdeRecreativa': {
        'label': 'Verde / Recreativa',
        'zonas_oficiales': ['ZParque', 'ZPCons', 'AVP', 'ZVP', 'RNA'],
        'color': '#2e7d32',
    },
    'ProductivaRural': {
        'label': 'Productiva / Rural',
        'zonas_oficiales': ['ZRurI', 'ZRurE', 'ZUrbProd1', 'ZUrbProd2',
                             'ZProdUrb1', 'ZDUrb1', 'ZDUrb2', 'ZCir'],
        'color': '#8d6e63',
    },
}

# Índice inverso: código oficial ('ZR2A', 'ZCen', ...) -> clave de macro-zona
_DESIG_A_MACRO = {}
for _clave, _z in ZONAS_VN.items():
    for _desig in _z['zonas_oficiales']:
        _DESIG_A_MACRO[_desig] = _clave


def _macro_de(desig):
    """Devuelve la clave de macro-zona (y su color) para un código oficial dado."""
    clave = _DESIG_A_MACRO.get(desig)
    if clave is None:
        return None, '#757575'  # gris — código no contemplado en el agrupamiento
    return clave, ZONAS_VN[clave]['color']


SECCIONES_VN = [
    ("🏠", "Inicio"),
    ("🗺️", "Mapa de zonificación"),
    ("📊", "Indicadores ambientales"),
    ("🌡️", "Temperatura superficial"),
    ("🏛️", "Verde público (OSM)"),
    ("🌳", "Censo Arbóreo"),
    ("📋", "Diagnóstico por zonas"),
    ("🎯", "Estrategias · Villa Nueva"),
    ("🌍", "Agenda 2030 · C40"),
    ("📄", "Masterplan · Opus 4.7"),
    ("🤝", "A Mejorar juntos"),
]


# ============================================================
# HELPERS VISUALES (mismo patrón que modulo_villamaria.py)
# ============================================================

def _semaforo(valor, umbral_ok, umbral_warn, invert=False):
    """Devuelve color semáforo según umbrales. Gris si valor es None."""
    if valor is None:
        return "#757575"
    if invert:
        if valor <= umbral_ok:   return "#2e7d32"
        if valor <= umbral_warn: return "#f57c00"
        return "#c62828"
    else:
        if valor >= umbral_ok:   return "#2e7d32"
        if valor >= umbral_warn: return "#f57c00"
        return "#c62828"


def _card_indicador(titulo, valor, unidad, referencia, color):
    valor_mostrar = "N/D" if valor is None else valor
    st.markdown(
        f"""<div style='border-left:4px solid {color};background:{color}11;
            padding:14px 16px;border-radius:0 10px 10px 0;margin-bottom:8px'>
          <div style='font-size:0.88em;color:#fff;margin-bottom:2px;font-weight:500'>{titulo}</div>
          <div style='font-size:1.7em;font-weight:700;color:{color}'>{valor_mostrar}<span style='font-size:0.55em;font-weight:400;margin-left:4px'>{unidad}</span></div>
          <div style='font-size:0.84em;color:#ccc;margin-top:2px'>{referencia}</div>
        </div>""",
        unsafe_allow_html=True
    )


# ============================================================
# SECCIÓN: INICIO
# ============================================================

def _render_inicio():
    st.markdown("## 🏠 Villa Nueva — Ciudad Verde AI Agent")

    if DATOS_VN.get('datos_preliminares'):
        st.warning(
            "⚠️ **Datos preliminares.** Los indicadores ambientales de esta "
            "sección todavía no fueron calculados específicamente para Villa "
            "Nueva (GEE / Landsat / OSM). Los valores mostrados son "
            "ilustrativos, a fin de validar la estructura de la plataforma. "
            "La zonificación (32 zonas oficiales, Código Urbano Rural 2025) "
            "sí es un dato real y validado."
        )

    st.markdown(
        "Plataforma de monitoreo ambiental para la ciudad de Villa Nueva "
        "(Departamento General San Martín, Córdoba), basada en la "
        "zonificación oficial del **Código Urbano Rural 2025** "
        "(Municipalidad de Villa Nueva / IDECOR) cruzada con datos "
        "satelitales de cobertura, temperatura superficial y espacios verdes."
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Población (INDEC)", f"{DATOS_VN['poblacion_vn']:,}".replace(",", "."))
    with c2:
        st.metric("Área", f"{DATOS_VN['area_vn_km2']} km²")
    with c3:
        st.metric("Zonas oficiales", "32")

    st.markdown("---")
    st.markdown("### Zonificación — macro-categorías")
    st.caption(
        "Las 32 zonas oficiales del Código Urbano Rural 2025 agrupadas en "
        "6 categorías para lectura rápida. El detalle completo (usos "
        "permitidos, alturas, retiros) está disponible en el mapa."
    )

    cols = st.columns(3)
    for i, (clave, zona) in enumerate(ZONAS_VN.items()):
        with cols[i % 3]:
            st.markdown(
                f"""<div style='border-left:4px solid {zona['color']};
                    background:{zona['color']}15;padding:10px 14px;
                    border-radius:0 8px 8px 0;margin-bottom:10px'>
                  <div style='font-weight:600;color:#fff'>{zona['label']}</div>
                  <div style='font-size:0.8em;color:#aaa;margin-top:4px'>
                    {len(zona['zonas_oficiales'])} zonas oficiales</div>
                </div>""",
                unsafe_allow_html=True,
            )

    st.markdown("---")
    st.caption(
        "Ciudad Verde AI Agent · Villa Nueva · Fuente zonificación: "
        "Código Urbano Rural 2025, Municipalidad de Villa Nueva / IDECOR"
    )


# ============================================================
# SECCIÓN: MAPA DE ZONIFICACIÓN
# ============================================================

@st.cache_data(show_spinner=False, ttl=86400)
def _cargar_zonificacion():
    if not os.path.exists(RUTA_ZONIFICACION):
        return None
    with open(RUTA_ZONIFICACION, encoding='utf-8') as f:
        return json.load(f)


def _render_mapa():
    st.markdown("## 🗺️ Mapa de zonificación — Villa Nueva")
    st.caption(
        "32 zonas oficiales del Código Urbano Rural 2025 "
        "(Municipalidad de Villa Nueva / IDECOR), coloreadas por macro-categoría."
    )

    geo = _cargar_zonificacion()
    if not geo:
        st.info(
            "Falta data/zonificacion_villanueva.geojson — correr "
            "convertir_zonificacion_vn.py primero."
        )
        return

    centro_lat = sum(
        f['geometry']['coordinates'][0][0][1]
        if f['geometry']['type'] == 'Polygon'
        else f['geometry']['coordinates'][0][0][0][1]
        for f in geo['features']
    ) / len(geo['features'])
    centro_lon = sum(
        f['geometry']['coordinates'][0][0][0]
        if f['geometry']['type'] == 'Polygon'
        else f['geometry']['coordinates'][0][0][0][0]
        for f in geo['features']
    ) / len(geo['features'])

    m = folium.Map(location=[centro_lat, centro_lon], zoom_start=13, tiles=None, prefer_canvas=True)
    folium.TileLayer(
        tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}',
        attr='© Google', name='🌍 Satelital', max_zoom=20, show=True,
    ).add_to(m)
    folium.TileLayer(
        tiles='https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
        attr='© OpenStreetMap contributors', name='🗺️ OpenStreetMap', max_zoom=19, show=False,
    ).add_to(m)

    grupos = {clave: FeatureGroup(name=f"{z['label']}", show=True) for clave, z in ZONAS_VN.items()}
    grupo_otras = FeatureGroup(name='Sin categorizar', show=True)

    for feat in geo['features']:
        props = feat['properties']
        desig = props.get('desig', '')
        nombre = props.get('name', desig)
        clave_macro, color = _macro_de(desig)

        popup_html = (
            f"<b>{desig}</b> — {nombre}<br>"
            f"<i>{ZONAS_VN[clave_macro]['label'] if clave_macro else 'Sin categorizar'}</i><br><br>"
            f"<b>FOS:</b> {props.get('fos', 'N/D')} · "
            f"<b>FOT:</b> {props.get('fot', 'N/D')}<br>"
            f"<b>Uso permitido:</b> {(props.get('u_perm') or 'N/D')[:200]}"
        )

        capa = folium.GeoJson(
            feat,
            style_function=lambda x, c=color: {
                'fillColor': c, 'color': '#ffffff', 'weight': 1, 'fillOpacity': 0.5,
            },
            tooltip=f"{desig} — {nombre}",
            popup=folium.Popup(popup_html, max_width=280),
        )
        capa.add_to(grupos.get(clave_macro, grupo_otras))

    for grupo in grupos.values():
        grupo.add_to(m)
    grupo_otras.add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)

    st_folium(m, width="100%", height=560, returned_objects=[])

    # Leyenda fuera del iframe (dentro nunca renderiza bien en modo oscuro)
    st.markdown("#### Referencias")
    cols = st.columns(3)
    for i, (clave, z) in enumerate(ZONAS_VN.items()):
        with cols[i % 3]:
            st.markdown(
                f"<span style='display:inline-block;width:12px;height:12px;"
                f"background:{z['color']};border-radius:3px;margin-right:6px'></span>"
                f"{z['label']}",
                unsafe_allow_html=True,
            )

    st.caption(
        "Fuente: Código Urbano Rural 2025, Municipalidad de Villa Nueva / IDECOR "
        "(WFS geoserver, capa villa_nva_cod_urb_rur)."
    )


# ============================================================
# SECCIÓN: INDICADORES AMBIENTALES
# ============================================================

def _render_indicadores():
    st.title("📊 Indicadores ambientales")
    st.caption("Villa Nueva · Datos: ESA WorldCover 2020 + Landsat 8/9 + OSM")

    if DATOS_VN.get('datos_preliminares'):
        st.warning(
            "⚠️ **Datos preliminares** — valores ilustrativos, cálculo real "
            "por zona pendiente (ver Mapa de zonificación para las 32 zonas "
            "oficiales confirmadas)."
        )

    st.markdown("---")

    d = DATOS_VN
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
    st.caption("Pendiente de cálculo — requiere consulta a la API Overpass para el ejido de Villa Nueva.")
    c4, c5, c6 = st.columns(3)
    with c4:
        _card_indicador("Verde público / habitante", osm['m2Hab'], "m²/hab", "OMS mínimo: 9 m²/hab", "#757575")
    with c5:
        _card_indicador("Área verde pública total", osm['areaHa'], "ha", "Catalogada en OSM", "#757575")
    with c6:
        _card_indicador("Espacios catalogados", osm['elementos'], "", "Plazas, parques, arbolado", "#757575")

    st.markdown("---")
    st.markdown("### Cobertura del suelo")
    c7, c8, c9, c10 = st.columns(4)
    with c7:
        color = _semaforo(cob['arboles'], 15, 8)
        _card_indicador("Arbolado urbano", cob['arboles'], "%", "Meta municipal: 15%", color)
    with c8:
        _card_indicador("Pastizales", cob['pastizales'], "%", "", "#8bc34a")
    with c9:
        _card_indicador("Cultivos urbanos", cob['cultivos'], "%", "Oportunidad de reconversión", "#cddc39")
    with c10:
        _card_indicador("Suelo edificado", cob['edificado'], "%", "", "#9e9e9e")

    st.markdown("---")
    st.caption(
        "Ciudad Verde AI Agent · Villa Nueva · Fuente: ESA WorldCover 2020, "
        "Landsat 8/9, OpenStreetMap — valores preliminares sujetos a cálculo real."
    )


# ============================================================
# SECCIÓN: TEMPERATURA SUPERFICIAL
# ============================================================

def _render_temperatura():
    st.title("🌡️ Temperatura superficial")
    st.caption("Villa Nueva · Datos: Landsat 8/9 — banda térmica")

    if DATOS_VN.get('datos_preliminares'):
        st.warning(
            "⚠️ **Datos preliminares** — no se corrió aún el análisis de "
            "temperatura superficial (LST) específico para Villa Nueva. "
            "Los valores de referencia usados abajo son estimativos, "
            "tomados como punto de partida del conglomerado VM+VN."
        )

    d = DATOS_VN['lst']
    c1, c2, c3 = st.columns(3)
    with c1:
        _card_indicador("Temperatura media", d['tMedia'], "°C", "Superficie terrestre (LST)", "#f57c00")
    with c2:
        color = _semaforo(d['deltaUHI'], 0.3, 1.0, invert=True)
        _card_indicador("Isla de calor (ΔT)", d['deltaUHI'], "°C", "Diferencia urbano vs. verde", color)
    with c3:
        _card_indicador("Enfriamiento por arbolado", d['enfriamiento'], "°C/ha", "Efecto de la cobertura arbórea", "#2e7d32")

    st.markdown("---")
    c4, c5 = st.columns(2)
    with c4:
        _card_indicador("Verde denso (NDVI alto)", d['tNdviAlto'], "°C", "Zonas con NDVI > 0.4", "#2e7d32")
    with c5:
        _card_indicador("Suelo/asfalto (NDVI bajo)", d['tNdviBajo'], "°C", "Zonas con NDVI < 0.2", "#c62828")

    st.markdown("---")
    st.info(
        "👉 Próximo paso: correr el análisis LST específico de Villa Nueva "
        "(13 imágenes Landsat, mismo método usado en el conglomerado VM+VN) "
        "y cruzarlo con las 32 zonas oficiales de zonificación para "
        "identificar puntos calientes por tipo de uso de suelo."
    )


# ============================================================
# SECCIÓN: VERDE PÚBLICO (OSM)
# ============================================================

def _render_osm():
    st.title("🏛️ Verde público (OpenStreetMap)")
    st.caption("Villa Nueva · Espacios verdes catalogados por la comunidad OSM")

    st.warning(
        "⚠️ **Pendiente de cálculo.** Todavía no se corrió la consulta a la "
        "API Overpass de OpenStreetMap acotada al ejido de Villa Nueva. "
        "Esta sección va a mostrar plazas, parques y arbolado catalogado, "
        "igual que en el módulo de Villa María."
    )

    st.markdown("---")
    st.markdown("### Lo que ya sabemos por zonificación oficial")
    st.caption(
        "Aunque no tenemos el conteo OSM todavía, la zonificación del "
        "Código Urbano Rural 2025 ya identifica formalmente las áreas "
        "verdes/recreativas de la ciudad:"
    )

    verdes = ZONAS_VN['VerdeRecreativa']['zonas_oficiales']
    st.markdown(
        f"- **Zona Parque Hipólito Yrigoyen** (`ZParque`) — parque urbano lineal sobre el Río Tercero\n"
        f"- **Área Verde Protegida** (`AVP`) y **Zonas Verdes Periurbanas** (`ZVP`)\n"
        f"- **Reserva Natural Autóctona** (`RNA`)\n"
        f"- **Zona Pericentral Consolidada** (`ZPCons`)\n\n"
        f"Total: {len(verdes)} categorías oficiales de suelo verde/recreativo "
        f"(ver detalle y geometría real en el Mapa de zonificación)."
    )


# ============================================================
# SECCIÓN: CENSO ARBÓREO
# ============================================================

def _render_censo_vn():
    st.title("🌳 Censo Arbóreo — Villa Nueva")
    st.caption("Objetivo municipal: 1 árbol por vivienda")

    st.info(
        "🚧 **En construcción.** El Censo Arbóreo de Villa Nueva sigue el "
        "mismo método que Villa María (Canopy Height GEE + conteo por "
        "unidad territorial), pero usando las **32 zonas oficiales de "
        "zonificación** (`data/zonificacion_villanueva.geojson`) como "
        "unidad de agregación en vez de barrios.\n\n"
        "**Falta correr:** un script `exportar_censo_villanueva.py` "
        "(mismo patrón que `exportar_censo_json.py` de Villa María) que "
        "calcule el conteo de árboles por zona vía Earth Engine y guarde "
        "el resultado en `data/censo_arboreo_villanueva.json`.\n\n"
        "Este es el próximo paso pendiente de ejecutar localmente."
    )


# ============================================================
# SECCIÓN: DIAGNÓSTICO POR ZONAS
# ============================================================

def _render_diagnostico():
    st.title("📋 Diagnóstico por zonas")
    st.caption("Villa Nueva · Resumen por macro-categoría de zonificación")

    if DATOS_VN.get('datos_preliminares'):
        st.warning("⚠️ Indicadores ambientales por zona: pendientes de cálculo real. Mostrando estructura.")

    geo = _cargar_zonificacion()
    conteo_por_macro = {clave: 0 for clave in ZONAS_VN}
    if geo:
        for feat in geo['features']:
            clave_macro, _ = _macro_de(feat['properties'].get('desig', ''))
            if clave_macro:
                conteo_por_macro[clave_macro] += 1

    cols = st.columns(3)
    for i, (clave, z) in enumerate(ZONAS_VN.items()):
        with cols[i % 3]:
            n_zonas = conteo_por_macro.get(clave, 0)
            st.markdown(
                f"<div style='border:2px solid {z['color']};border-radius:10px;"
                f"padding:14px 12px;margin-bottom:12px;height:100%;'>"
                f"<div style='font-size:1em;font-weight:700;margin-bottom:8px;'>{z['label']}</div>"
                f"<div style='font-size:0.85em;margin-bottom:4px;'>"
                f"<span style='color:{z['color']};font-weight:700;'>●</span> "
                f"{n_zonas} zonas oficiales</div>"
                f"<div style='font-size:0.78em;color:#aaa;'>"
                f"Códigos: {', '.join(z['zonas_oficiales'][:4])}"
                f"{'...' if len(z['zonas_oficiales']) > 4 else ''}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

    st.markdown("---")
    st.caption(
        "El detalle de indicadores ambientales por macro-zona (temperatura, "
        "cobertura, acceso a verde) se completa cuando esté disponible el "
        "cálculo real por zona (ver banners de 'datos preliminares')."
    )


# ============================================================
# SECCIÓN: ESTRATEGIAS · VILLA NUEVA
# ============================================================

def _render_estrategias_vn():
    st.title("🎯 Estrategias · Villa Nueva")
    st.caption("Basadas en la zonificación oficial — Código Urbano Rural 2025")

    geo = _cargar_zonificacion()
    if not geo:
        st.info("Falta data/zonificacion_villanueva.geojson para mostrar estrategias por zona.")
        return

    st.markdown(
        "Cada macro-zona tiene usos permitidos, condicionados y no conformes "
        "definidos por ordenanza. Estas son las líneas de acción ambiental "
        "sugeridas por macro-categoría, a partir de esa normativa real:"
    )
    st.markdown("---")

    estrategias_sugeridas = {
        'Centro': "Arbolado en veredas y espacios públicos, dado el alto FOS/FOT y baja proporción de suelo absorbente.",
        'Residencial': "Meta '1 árbol por casa' — mayor potencial de impacto por cantidad de lotes con retiro de frente.",
        'ComercialMixta': "Incentivar cubiertas verdes y arbolado en estacionamientos de grandes superficies.",
        'IndustrialEspecial': "Franjas de forestación perimetral como mitigación de impacto (ZIAE junto a zona residencial).",
        'VerdeRecreativa': "Conservación y ampliación — ya es la base del corredor ecológico del Río Tercero.",
        'ProductivaRural': "Corredores de vegetación nativa entre parcelas productivas, uso condicionado a bajo impacto.",
    }

    for clave, z in ZONAS_VN.items():
        with st.expander(f"{z['label']} — {len(z['zonas_oficiales'])} zonas"):
            st.markdown(f"**Estrategia sugerida:** {estrategias_sugeridas.get(clave, 'A definir.')}")
            st.caption(f"Códigos oficiales: {', '.join(z['zonas_oficiales'])}")

    st.markdown("---")
    st.caption(
        "Fuente normativa: Código Urbano Rural 2025, Municipalidad de Villa "
        "Nueva. Estrategias sugeridas a validar con la Municipalidad."
    )


# ============================================================
# SECCIÓN: AGENDA 2030 · C40
# ============================================================

def _render_agenda2030_vn():
    st.title("🌍 Agenda 2030 · C40")
    st.caption("Villa Nueva frente a los Objetivos de Desarrollo Sostenible")

    st.markdown("""
    ### ODS relevantes para el diagnóstico ambiental de Villa Nueva
    - **ODS 11** — Ciudades y comunidades sostenibles: acceso a espacios verdes, planificación urbana inclusiva.
    - **ODS 13** — Acción por el clima: mitigación de islas de calor, captura de CO₂ por arbolado.
    - **ODS 15** — Vida de ecosistemas terrestres: conservación del corredor del Río Tercero (Parque Yrigoyen, Reserva Natural).
    """)

    st.markdown("---")
    st.info(
        "👉 El seguimiento cuantitativo de KPIs 2030 (igual que en el módulo "
        "de Villa María) se activa cuando estén disponibles los indicadores "
        "ambientales reales calculados por zona."
    )


# ============================================================
# SECCIÓN: MASTERPLAN
# ============================================================

def _render_masterplan_vn():
    st.title("📄 Masterplan · Villa Nueva")

    st.info(
        "🚧 **En construcción.** El Masterplan de Villa Nueva va a reusar "
        "`modulo_masterplan.py` (mismo modelo, Claude Sonnet 4.6, admin-only), "
        "pero necesita que ese módulo acepte el municipio destinatario como "
        "parámetro — hoy está redactado exclusivamente para Villa María.\n\n"
        "Este ajuste queda pendiente como paso posterior del plan, una vez "
        "resuelto el tema de facturación de Anthropic que está bloqueando "
        "el Masterplan de Villa María también."
    )


# ============================================================
# SECCIÓN: A MEJORAR JUNTOS
# ============================================================

def _render_mejorar_juntos_vn():
    st.title("🤝 A Mejorar juntos — Villa Nueva")
    st.markdown(
        "Este espacio está pensado para que la Municipalidad de Villa Nueva "
        "y la comunidad puedan sugerir mejoras, señalar datos faltantes o "
        "reportar inconsistencias en el análisis ambiental de la ciudad."
    )
    st.caption(
        "Funcionalidad de contacto/feedback pendiente de definir en conjunto "
        "con el municipio — mismo criterio que la sección equivalente de "
        "Villa María."
    )


# ============================================================
# RENDER PRINCIPAL (se completa con el resto de las secciones)
# ============================================================

def render_villanueva():
    st.sidebar.markdown("### 🏙️ Villa Nueva")
    seccion = st.sidebar.radio(
        "Sección",
        [f"{icono} {nombre}" for icono, nombre in SECCIONES_VN],
        key="seccion_villanueva",
    )

    if "Inicio" in seccion:
        _render_inicio()
    elif "Mapa de zonificación" in seccion:
        _render_mapa()
    elif "Indicadores ambientales" in seccion:
        _render_indicadores()
    elif "Temperatura superficial" in seccion:
        _render_temperatura()
    elif "Verde público" in seccion:
        _render_osm()
    elif "Censo Arbóreo" in seccion:
        _render_censo_vn()
    elif "Diagnóstico por zonas" in seccion:
        _render_diagnostico()
    elif "Estrategias" in seccion:
        _render_estrategias_vn()
    elif "Agenda 2030" in seccion:
        _render_agenda2030_vn()
    elif "Masterplan" in seccion:
        _render_masterplan_vn()
    elif "A Mejorar juntos" in seccion:
        _render_mejorar_juntos_vn()
