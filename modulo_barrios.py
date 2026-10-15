"""
modulo_barrios.py — Ciudad Verde AI Agent
=========================================
Diagnóstico por barrio · Villa María.
Meta municipal: 1 árbol por casa.

Lee únicamente archivos precalculados (no usa GEE en producción):
  data/zonas_villamaria_resumen.json  -> totales por ciudad, tipo, barrio y zona
  data/zonas_villamaria.geojson       -> polígonos de las zonas (para el mapa)
  data/barrios_villamaria.geojson     -> contornos de los 38 barrios (opcional)

Ambos archivos de zonas se generan con consolidar_zonas.py.

Uso:
    from modulo_barrios import render_diagnostico_barrios
    render_diagnostico_barrios()
"""

import os
import json

import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium


# ============================================================
# CONFIGURACIÓN
# ============================================================

_DATA = os.path.join(os.path.dirname(__file__), 'data')
RUTA_RESUMEN = os.path.join(_DATA, 'zonas_villamaria_resumen.json')
RUTA_ZONAS = os.path.join(_DATA, 'zonas_villamaria.geojson')
RUTA_BARRIOS = os.path.join(_DATA, 'barrios_villamaria.geojson')

FECHA_IMAGEN = "16/03/2018 (≈92% de la ciudad) y 09/10/2019 (franja oeste)"

COLOR_TIPO = {
    'urbana_centrica':    '#e53935',
    'urbana_residencial': '#fb8c00',
    'urbana_mixta':       '#fdd835',
    'riberena':           '#1e88e5',
    'bosque_autoctono':   '#2e7d32',
    'industrial':         '#8e24aa',
}

NOTA_EXCESO = ("El conteo satelital incluye árboles de patios y, en barrios ribereños, "
               "vegetación de la ribera dentro de la zona; por eso puede superar el 100%.")


# ============================================================
# CARGA DE DATOS
# ============================================================

@st.cache_data(show_spinner=False)
def _cargar_resumen():
    if not os.path.exists(RUTA_RESUMEN):
        return None
    with open(RUTA_RESUMEN, encoding='utf-8') as f:
        return json.load(f)


@st.cache_data(show_spinner=False)
def _cargar_geojson(ruta):
    if not os.path.exists(ruta):
        return None
    with open(ruta, encoding='utf-8') as f:
        return json.load(f)


# ============================================================
# HELPERS
# ============================================================

def _num(n):
    """Entero con separador de miles argentino."""
    return f"{int(n):,}".replace(",", ".")


def _dec(x, d=1):
    """Decimal con coma."""
    return f"{x:.{d}f}".replace(".", ",")


def _txt_meta(pct):
    if pct is None:
        return "Sin zona de casas"
    if pct >= 100:
        return "Meta alcanzada"
    return f"{_dec(pct)} %"


def _color_meta(pct):
    if pct is None:
        return "#9e9e9e"
    if pct >= 100:
        return "#2e7d32"
    if pct >= 60:
        return "#f57c00"
    return "#c62828"


def _card(titulo, valor, detalle, color):
    st.markdown(
        f"""<div style='border-left:4px solid {color};background:{color}11;
            padding:14px 16px;border-radius:0 10px 10px 0;margin-bottom:8px'>
          <div style='font-size:0.88em;color:#fff;margin-bottom:2px;font-weight:500'>{titulo}</div>
          <div style='font-size:1.7em;font-weight:700;color:{color}'>{valor}</div>
          <div style='font-size:0.84em;color:#ccc;margin-top:2px'>{detalle}</div>
        </div>""",
        unsafe_allow_html=True,
    )


# ============================================================
# BLOQUES DE PANTALLA
# ============================================================

def _render_aviso(res):
    st.info(
        f"🛰️ **Imagen satelital:** Meta/WRI Canopy Height · {FECHA_IMAGEN}. "
        "Las plantaciones posteriores no están incluidas.\n\n"
        f"🏠 **Lotes:** {res['metodo_lotes']['estado']}. "
        "Cuando la Municipalidad aporte el catastro, la meta se recalcula con el número real de viviendas."
    )


def _render_ciudad(res):
    c = res['ciudad']
    m = c['meta_1_arbol_por_casa']
    st.markdown("### 🌍 Villa María")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        _card("Árboles detectados", _num(c['total_arboles']),
              f"{c['n_barrios']} barrios · {c['n_zonas']} zonas", "#2e7d32")
    with c2:
        _card("Lotes estimados", _num(m['lotes_estimados']),
              "zonas con casas · estimación provisoria", "#1e88e5")
    with c3:
        _card("Cumplimiento de la meta", _txt_meta(m['cumplimiento_pct']),
              f"{_num(m['arboles_zonas_casas'])} árboles en zonas de casas",
              _color_meta(m['cumplimiento_pct']))
    with c4:
        _card("Déficit", f"{_num(m['deficit_arboles'])} árboles",
              "para llegar a 1 árbol por casa", "#c62828")


def _render_mapa(res):
    st.markdown("### 🗺️ Zonas por barrio")
    zonas = _cargar_geojson(RUTA_ZONAS)
    if not zonas:
        st.warning("Falta data/zonas_villamaria.geojson — correr consolidar_zonas.py.")
        return

    m = folium.Map(location=[-32.41, -63.245], zoom_start=13, tiles=None)
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='© Esri', name='🛰️ Satélite', max_zoom=19,
    ).add_to(m)
    folium.TileLayer(
        tiles='https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
        attr='© OpenStreetMap contributors', name='🗺️ OpenStreetMap', max_zoom=19,
    ).add_to(m)

    barrios = _cargar_geojson(RUTA_BARRIOS)
    if barrios:
        folium.GeoJson(
            barrios, name='Barrios',
            style_function=lambda f: {'color': '#ffffff', 'weight': 1.2, 'fill': False, 'dashArray': '4 3'},
        ).add_to(m)

    folium.GeoJson(
        zonas, name='Zonas',
        style_function=lambda f: {
            'color': COLOR_TIPO.get(f['properties'].get('tipo'), '#9e9e9e'),
            'weight': 2,
            'fillColor': COLOR_TIPO.get(f['properties'].get('tipo'), '#9e9e9e'),
            'fillOpacity': 0.30,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=['barrio', 'tipo_nombre', 'n_arboles', 'lotes_estimados', 'cumplimiento_pct'],
            aliases=['Barrio', 'Tipo de zona', 'Árboles', 'Lotes estimados', 'Cumplimiento %'],
            localize=True,
        ),
    ).add_to(m)

    folium.LayerControl(position='topright', collapsed=False).add_to(m)
    st_folium(m, width="100%", height=520, returned_objects=[], key="mapa_barrios_vm")

    leyenda = " ".join(
        f"<span style='margin-right:14px'><span style='display:inline-block;width:11px;height:11px;"
        f"background:{color};border-radius:2px;margin-right:5px'></span>{t['tipo_nombre']}</span>"
        for t in res['por_tipo']
        for tipo, color in COLOR_TIPO.items() if tipo == t['tipo']
    )
    st.markdown(f"<div style='font-size:0.82em;margin-top:4px'>{leyenda}</div>", unsafe_allow_html=True)
    st.caption("Fuera de las zonas quedan plazas, parques y espacios sin casas (no cuentan para la meta).")


def _render_barrio(res):
    st.markdown("### 🏘️ Detalle por barrio")
    barrios = sorted(res['barrios'], key=lambda b: b['barrio'])
    nombres = [b['barrio'] for b in barrios]
    elegido = st.selectbox("Barrio", nombres, key="sel_barrio_vm")
    b = next(x for x in barrios if x['barrio'] == elegido)
    m = b['meta_1_arbol_por_casa']

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        _card("Árboles en el barrio", _num(b['total_arboles']),
              f"{_num(b['arboles_sin_zona'])} fuera de zonas (plazas, parques)", "#2e7d32")
    with c2:
        _card("Lotes estimados", _num(m['lotes_estimados']),
              f"{b['n_zonas']} zona(s) dibujada(s)", "#1e88e5")
    with c3:
        _card("Cumplimiento de la meta", _txt_meta(m['cumplimiento_pct']),
              f"{_num(m['arboles_zonas_casas'])} árboles en zonas de casas",
              _color_meta(m['cumplimiento_pct']))
    with c4:
        _card("Déficit", f"{_num(m['deficit_arboles'])} árboles",
              "suma de faltantes por zona", "#c62828")

    if m['cumplimiento_pct'] is not None and m['cumplimiento_pct'] >= 100:
        st.caption(f"ℹ️ {NOTA_EXCESO}")

    filas = []
    for z in b['zonas']:
        filas.append({
            'Zona': z['zona_id'],
            'Tipo': z['tipo_nombre'] + (" · forestación incipiente" if z.get('forestacion_incipiente') else ""),
            'LCZ': z.get('lcz', ''),
            'Superficie (ha)': z['area_ha'],
            'Árboles': z['n_arboles'],
            'Árb/ha': z['arboles_ha'],
            'Lotes estimados': z['lotes_estimados'],
            'Meta': _txt_meta(z['cumplimiento_pct']),
            'Déficit': z['deficit_arboles'],
        })
    if filas:
        st.dataframe(pd.DataFrame(filas), hide_index=True, use_container_width=True)


def _render_ranking(res):
    st.markdown("### 📋 Prioridades de forestación")
    st.caption("Barrios ordenados de menor a mayor cumplimiento de la meta 1 árbol por casa.")
    filas = []
    for b in res['barrios']:
        m = b['meta_1_arbol_por_casa']
        filas.append({
            'Barrio': b['barrio'],
            '_orden': m['cumplimiento_pct'] if m['cumplimiento_pct'] is not None else 999,
            'Cumplimiento': _txt_meta(m['cumplimiento_pct']),
            'Árboles en zonas de casas': m['arboles_zonas_casas'],
            'Lotes estimados': m['lotes_estimados'],
            'Déficit (árboles)': m['deficit_arboles'],
        })
    df = pd.DataFrame(filas).sort_values('_orden').drop(columns='_orden')
    df.insert(0, '#', range(1, len(df) + 1))
    st.dataframe(df, hide_index=True, use_container_width=True, height=420)
    st.caption(f"ℹ️ {NOTA_EXCESO}")


def _render_metodologia(res):
    ml = res['metodo_lotes']
    with st.expander("📐 Metodología y fuentes"):
        st.markdown(
            f"""
**Árboles** — {res['fuente_puntos']}. Imagen: {FECHA_IMAGEN}.
Cada árbol es una cima de copa detectada; se asigna a la zona que la contiene.
{res['metodo']}.

**Zonas** — delimitadas manualmente barrio por barrio sobre la imagen satelital.
Tipos basados en las Zonas Climáticas Locales (Stewart y Oke, 2012).

**Lotes estimados** — {ml['estado']}.
- Cuadra eje a eje: {_dec(ml['cuadra_eje_m'], 0)} m · ancho de calle: {_dec(ml['ancho_calle_m'], 0)} m · frente de lote: {_dec(ml['frente_lote_m'], 0)} m
- Lotes por manzana: {_dec(ml['lotes_por_manzana'])} · lotes por hectárea: {_dec(ml['lotes_por_ha'], 2)}
- Fórmula: {ml['formula']}
"""
        )
        fac = pd.DataFrame(
            [{'Tipo de zona': t['tipo_nombre'], 'Factor de ocupación': ml['factor_ocupacion'].get(t['tipo'], 0)}
             for t in res['por_tipo']]
        )
        st.dataframe(fac, hide_index=True, use_container_width=True)
        st.markdown("**Fuentes de las constantes**")
        for fuente in ml['fuentes']:
            st.markdown(f"- {fuente}")
        st.caption(f"Generado: {res['generado']}")


# ============================================================
# RENDER
# ============================================================

def render_diagnostico_barrios():
    """Punto de entrada. Llamar desde render_modulo_villamaria()."""
    st.title("🏘️ Diagnóstico por barrio · Villa María")

    res = _cargar_resumen()
    if not res:
        st.warning("Falta data/zonas_villamaria_resumen.json — correr consolidar_zonas.py.")
        return

    _render_aviso(res)
    _render_ciudad(res)
    st.markdown("---")
    _render_mapa(res)
    st.markdown("---")
    _render_barrio(res)
    st.markdown("---")
    _render_ranking(res)
    st.markdown("---")
    _render_metodologia(res)