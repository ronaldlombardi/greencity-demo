"""
modulo_censo_arboreo.py — Ciudad Verde AI Agent
================================================
Censo Arbóreo — Villa María.
Objetivo municipal: 1 árbol por vivienda.

Este módulo se construye paso a paso:
  1. Estructura de pantalla ✅
  2. Numerador — Canopy Height (GEE, 1m):
       - Área/altura de copa ciudad completa (agregado) ✅
       - Conteo piloto en zona chica (validación de método) ✅
       - Censo completo por celdas 300x300m — PRECALCULADO LOCAL ✅
         (ver exportar_censo_json.py — corre aparte, no en Streamlit)
  3. Denominador — Catastro IDECOR (parcelas edificadas por manzana)
  4. Cruce numerador/denominador → ratio árboles/vivienda por zona
  5. Margen de error validado — comparar conteo automático vs conteo
     manual en muestra de manzanas (pendiente, próximo paso)

Uso en dashboard:
    from modulo_censo_arboreo import render_censo_arboreo
    render_censo_arboreo()
"""

import os
import json
import ee
import streamlit as st
import folium
from streamlit_folium import st_folium


# ============================================================
# CONFIGURACIÓN
# ============================================================

CANOPY_ASSET = 'projects/meta-forest-monitoring-okw37/assets/CanopyHeight'
ALTURA_MIN_ARBOL = 2  # metros — umbral para distinguir árbol de pasto/arbusto bajo
TAMANO_CELDA_M = 300  # debe coincidir con exportar_censo_json.py

# Bbox de Villa María + Villa Nueva (mismo usado en modulo_villamaria.py)
COORDS_VM = [
    [-63.280, -32.390], [-63.200, -32.390],
    [-63.200, -32.440], [-63.280, -32.440], [-63.280, -32.390]
]

# ⚠️ ZONA PILOTO DE PRUEBA — coordenadas aproximadas, A AJUSTAR
# con el municipio a un barrio real una vez validado el método.
COORDS_PILOTO = [
    [-63.245, -32.405], [-63.238, -32.405],
    [-63.238, -32.412], [-63.245, -32.412], [-63.245, -32.405]
]

# Archivo generado por exportar_censo_json.py (script local, corre aparte)
RUTA_CENSO_JSON = os.path.join(os.path.dirname(__file__), 'data', 'censo_arboreo_villamaria.json')


# ============================================================
# GEE — ÁREA/ALTURA DE COPA (CIUDAD COMPLETA, AGREGADO)
# ============================================================

@st.cache_data(show_spinner=False, ttl=86400)
def cargar_canopy_ciudad(coords_area=COORDS_VM):
    """
    Área cubierta por copas y altura media/máxima para toda el área urbana.
    Cálculo agregado (reduceRegion) — liviano, sin riesgo de timeout.
    """
    area = ee.Geometry.Polygon([coords_area])
    canopy = ee.ImageCollection(CANOPY_ASSET).mosaic().rename('altura').clip(area)
    mask_arbol = canopy.gte(ALTURA_MIN_ARBOL)
    altura_arbol = canopy.updateMask(mask_arbol)

    area_stats = mask_arbol.multiply(ee.Image.pixelArea()).reduceRegion(
        reducer=ee.Reducer.sum(), geometry=area, scale=1,
        maxPixels=1e10, bestEffort=True, tileScale=4,
    ).getInfo()
    area_m2 = list(area_stats.values())[0] if area_stats else 0

    stats_altura = altura_arbol.reduceRegion(
        reducer=ee.Reducer.mean().combine(ee.Reducer.max(), sharedInputs=True),
        geometry=area, scale=1, maxPixels=1e10, bestEffort=True, tileScale=4,
    ).getInfo()

    return {
        'area_copa_ha': round(area_m2 / 10000, 1) if area_m2 else 0,
        'altura_media_m': round(stats_altura.get('altura_mean'), 1) if stats_altura.get('altura_mean') else None,
        'altura_max_m': round(stats_altura.get('altura_max'), 1) if stats_altura.get('altura_max') else None,
        'umbral_altura_m': ALTURA_MIN_ARBOL,
    }


# ============================================================
# GEE — CONTEO PILOTO (ZONA CHICA, VALIDACIÓN DE MÉTODO)
# ============================================================

@st.cache_data(show_spinner=False, ttl=86400)
def cargar_canopy_conteo_piloto(coords_area=COORDS_PILOTO):
    """
    Conteo de árboles ('manchones' de copa contigua) en zona piloto chica.
    Sirve para validar el método antes de confiar en el censo completo.
    """
    area = ee.Geometry.Polygon([coords_area])
    canopy = ee.ImageCollection(CANOPY_ASSET).mosaic().rename('altura').clip(area)
    mask_arbol = canopy.gte(ALTURA_MIN_ARBOL).selfMask()

    conectados = mask_arbol.connectedComponents(
        connectedness=ee.Kernel.plus(1), maxSize=256
    )
    conteo = conectados.select('labels').reduceRegion(
        reducer=ee.Reducer.countDistinctNonNull(),
        geometry=area, scale=1, maxPixels=1e9, bestEffort=True, tileScale=4,
    ).getInfo()

    area_stats = mask_arbol.multiply(ee.Image.pixelArea()).reduceRegion(
        reducer=ee.Reducer.sum(), geometry=area, scale=1,
        maxPixels=1e9, bestEffort=True, tileScale=4,
    ).getInfo()
    area_m2 = list(area_stats.values())[0] if area_stats else 0

    area_piloto_ha = area.area().divide(10000).getInfo()
    n_manchones = conteo.get('labels') if conteo else None

    return {
        'n_arboles': int(n_manchones) if n_manchones is not None else None,
        'area_copa_ha': round(area_m2 / 10000, 3),
        'area_piloto_ha': round(area_piloto_ha, 2),
    }


# ============================================================
# CENSO COMPLETO — LEE EL JSON PRECALCULADO (exportar_censo_json.py)
# ============================================================

@st.cache_data(show_spinner=False, ttl=3600)
def _cargar_censo_json():
    """Lee el censo completo precalculado localmente. None si aún no existe."""
    if not os.path.exists(RUTA_CENSO_JSON):
        return None
    with open(RUTA_CENSO_JSON, encoding='utf-8') as f:
        return json.load(f)


def _color_densidad(n_arboles):
    """Color según densidad de árboles en la celda (para el mapa)."""
    if n_arboles is None:
        return '#555555'
    if n_arboles >= 60:
        return '#1b5e20'
    if n_arboles >= 30:
        return '#4caf50'
    if n_arboles >= 10:
        return '#aed581'
    if n_arboles > 0:
        return '#fff59d'
    return '#e0e0e0'


# ============================================================
# ESTADO DE FUENTES
# ============================================================

FUENTES = [
    {
        'nombre': 'Canopy Height (GEE, 1m)',
        'rol': 'Numerador — conteo y cobertura de árboles',
        'estado': 'en_progreso',
        'detalle': 'Dataset global de altura de dosel a 1m (Meta/WRI). Conectado: agregado ciudad, '
                    'piloto de validación y censo completo (precalculado local, ver '
                    'exportar_censo_json.py). Falta el margen de error empírico (próximo paso).',
    },
    {
        'nombre': 'Catastro IDECOR (WFS/WMS)',
        'rol': 'Denominador — parcelas edificadas por manzana',
        'estado': 'pendiente',
        'detalle': 'Distingue parcelas baldío/edificado/PH. Da el número real de viviendas '
                    'por manzana para calcular el ratio árboles/vivienda. Requiere consulta '
                    'a idecor@cba.gov.ar para descarga sin filtro por WFS.',
    },
    {
        'nombre': 'OpenStreetMap (natural=tree)',
        'rol': 'Complementaria — árboles individuales cargados por la comunidad',
        'estado': 'descartada_por_ahora',
        'detalle': 'Cobertura comunitaria en Argentina es prácticamente nula para este tag. '
                    'Se deja documentada por si en el futuro se completa.',
    },
]

_COLOR_ESTADO = {
    'pendiente': '#9e9e9e', 'en_progreso': '#f57c00',
    'conectada': '#2e7d32', 'descartada_por_ahora': '#616161',
}
_LABEL_ESTADO = {
    'pendiente': '⏳ Pendiente', 'en_progreso': '🔧 En progreso',
    'conectada': '✅ Conectada', 'descartada_por_ahora': '⛔ Descartada por ahora',
}


# ============================================================
# RENDER
# ============================================================

def render_censo_arboreo():
    """Punto de entrada. Llamar desde render_modulo_villamaria()."""

    st.title("🌳 Censo Arbóreo · Villa María")

    # ---- Banner de objetivo ----
    st.markdown(
        """<div style='background:linear-gradient(135deg,#1b5e20,#2e7d32);
            border-radius:12px;padding:18px 22px;margin-bottom:18px;text-align:center'>
          <div style='font-size:0.8em;letter-spacing:0.12em;text-transform:uppercase;color:#c8e6c9'>
            Objetivo municipal
          </div>
          <div style='font-size:1.7em;font-weight:700;color:#fff;margin-top:4px'>
            🌳 1 árbol por casa
          </div>
        </div>""",
        unsafe_allow_html=True,
    )

    # ---- Ciudad completa: área y altura de copa ----
    st.markdown("### 🌍 Cobertura de copa arbórea — ciudad completa")
    st.caption(f"Fuente: Canopy Height (Meta/WRI, 1m) · umbral de altura: {ALTURA_MIN_ARBOL}m")

    try:
        with st.spinner("Calculando cobertura de copa en Villa María + Villa Nueva..."):
            datos_ciudad = cargar_canopy_ciudad()

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Área cubierta por copas", f"{datos_ciudad['area_copa_ha']} ha")
        with c2:
            st.metric("Altura media de copa",
                      f"{datos_ciudad['altura_media_m']} m" if datos_ciudad['altura_media_m'] else "N/D")
        with c3:
            st.metric("Altura máxima detectada",
                      f"{datos_ciudad['altura_max_m']} m" if datos_ciudad['altura_max_m'] else "N/D")

        st.caption(
            "⚠️ Esto es superficie de copa, NO cantidad de árboles — varios árboles con copas "
            "que se tocan se ven como una sola mancha verde a esta escala."
        )
    except Exception as e:
        st.warning("No se pudo calcular la cobertura de copa para toda la ciudad.")
        st.caption(f"Detalle técnico: {e}")

    st.markdown("---")

    # ---- Censo completo (precalculado, lee JSON local) ----
    st.markdown("### 🌳 Censo Arbóreo Completo — árboles individuales")
    st.caption(
        f"Celdas de {TAMANO_CELDA_M}x{TAMANO_CELDA_M}m sobre toda el área urbana. "
        "Precalculado localmente — ver exportar_censo_json.py."
    )

    censo = _cargar_censo_json()

    if censo:
        st.caption(f"Último cálculo: {censo['fecha_calculo'][:16].replace('T', ' ')}")

        c4, c5, c6 = st.columns(3)
        with c4:
            st.metric("🌳 Árboles contados", f"{censo['total_arboles']:,}".replace(",", "."))
        with c5:
            st.metric("Área total de copa", f"{censo['total_area_copa_ha']} ha")
        with c6:
            st.metric("Celdas procesadas", f"{censo['celdas_procesadas']}/{censo['celdas_totales']}")

        st.markdown("#### Mapa de densidad — árboles por celda")
        centro_mapa = [
            (COORDS_VM[0][1] + COORDS_VM[2][1]) / 2,
            (COORDS_VM[0][0] + COORDS_VM[1][0]) / 2,
        ]
        m_censo = folium.Map(location=centro_mapa, zoom_start=13, tiles=None)
        folium.TileLayer(
            tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}',
            attr='© Google', name='🌍 Satelital', max_zoom=20, show=True,
        ).add_to(m_censo)

        for r in censo['celdas']:
            color = _color_densidad(r['n_arboles'])
            tooltip = f"{r['n_arboles']} árboles" if r['n_arboles'] is not None else "Sin datos"
            folium.CircleMarker(
                location=r['centro'], radius=6, color=color, weight=1,
                fill=True, fill_color=color, fill_opacity=0.85,
                tooltip=tooltip,
            ).add_to(m_censo)

        st_folium(m_censo, width="100%", height=480, returned_objects=[])
        st.caption(
            "🟢 Alta densidad (≥60 árboles/celda) · 🟩 Media (30-59) · 🟡 Baja (10-29) · "
            "⚪ Muy baja (1-9) · ⚫ Sin datos/error"
        )
    else:
        st.info(
            "Censo completo aún no calculado. Correr `python exportar_censo_json.py` "
            "localmente para generarlo (tarda 10-25 min, corre una sola vez)."
        )

    st.markdown("---")

    # ---- Validación pendiente / zona piloto ----
    st.markdown("### 🧪 Validación del método — zona piloto")
    st.caption(
        "Referencia usada para validar el conteo antes de confiar en el censo completo. "
        "Coordenadas de prueba — a ajustar con el municipio a un barrio real."
    )

    try:
        with st.spinner("Contando árboles en la zona piloto..."):
            datos_piloto = cargar_canopy_conteo_piloto()

        c7, c8, c9 = st.columns(3)
        with c7:
            st.metric("Árboles contados (piloto)", datos_piloto['n_arboles'] or "N/D")
        with c8:
            st.metric("Área de copa en la zona", f"{datos_piloto['area_copa_ha']} ha")
        with c9:
            st.metric("Área total de la zona piloto", f"{datos_piloto['area_piloto_ha']} ha")

        st.warning(
            "⏳ **Margen de error: pendiente de calcular.** Próximo paso: comparar este conteo "
            "automático contra un conteo manual sobre imagen satelital de esta misma zona, "
            "para reportar un % de error real y auditable — no una cifra genérica."
        )

        centro = [
            sum(p[1] for p in COORDS_PILOTO) / len(COORDS_PILOTO),
            sum(p[0] for p in COORDS_PILOTO) / len(COORDS_PILOTO),
        ]
        m_piloto = folium.Map(location=centro, zoom_start=17, tiles=None)
        folium.TileLayer(
            tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}',
            attr='© Google', name='🌍 Satelital', max_zoom=20, show=True,
        ).add_to(m_piloto)
        folium.Polygon(
            locations=[[p[1], p[0]] for p in COORDS_PILOTO],
            color='#f57c00', weight=2, fill=True, fill_opacity=0.08,
            tooltip="Zona piloto de conteo",
        ).add_to(m_piloto)
        st_folium(m_piloto, width="100%", height=380, returned_objects=[])

    except Exception as e:
        st.warning("No se pudo calcular el conteo en la zona piloto (posible timeout de GEE).")
        st.caption(f"Detalle técnico: {e}")

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
        "Ciudad Verde AI Agent · Villa María · Censo Arbóreo · "
        "En desarrollo — Canopy Height (GEE) + Catastro IDECOR"
    )