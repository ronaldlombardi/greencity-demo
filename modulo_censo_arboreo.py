"""
modulo_censo_arboreo.py — Ciudad Verde AI Agent
================================================
Censo Arbóreo — Villa María.
Objetivo municipal: 1 árbol por vivienda.

Este módulo se construye paso a paso:
  1. Estructura de pantalla ✅
  2. Numerador aproximado — Canopy Height (GEE, 1m):
       - Área/altura de copa para toda la ciudad (agregado, confiable) ✅
       - Conteo aproximado de "manchones" de copa en zona piloto chica ✅
         (NO correr sobre la ciudad completa: riesgo de timeout en GEE)
  3. Denominador — Catastro IDECOR (parcelas edificadas por manzana)
  4. Cruce numerador/denominador → ratio árboles/vivienda por zona

Uso en dashboard:
    from modulo_censo_arboreo import render_censo_arboreo
    render_censo_arboreo()
"""

import ee
import streamlit as st
import folium
from streamlit_folium import st_folium


# ============================================================
# CONFIGURACIÓN
# ============================================================

CANOPY_ASSET = 'projects/meta-forest-monitoring-okw37/assets/CanopyHeight'
ALTURA_MIN_ARBOL = 2  # metros — umbral para distinguir árbol de pasto/arbusto bajo

# Bbox de Villa María + Villa Nueva (mismo usado en modulo_villamaria.py)
COORDS_VM = [
    [-63.280, -32.390], [-63.200, -32.390],
    [-63.200, -32.440], [-63.280, -32.440], [-63.280, -32.390]
]

# ⚠️ ZONA PILOTO DE PRUEBA — coordenadas aproximadas, A AJUSTAR
# con el municipio a un barrio real una vez validado el método.
# Tamaño intencionalmente chico (~0.5 km²) para que connectedComponents no de timeout.
COORDS_PILOTO = [
    [-63.245, -32.405], [-63.238, -32.405],
    [-63.238, -32.412], [-63.245, -32.412], [-63.245, -32.405]
]


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
# GEE — CONTEO PILOTO (ZONA CHICA)
# ============================================================

@st.cache_data(show_spinner=False, ttl=86400)
def cargar_canopy_conteo_piloto(coords_area=COORDS_PILOTO):
    """
    Conteo aproximado de individuos arbóreos ('manchones' de copa contigua)
    en una zona piloto chica. Es un PROXY, no un inventario exacto:
    copas que se tocan entre sí se cuentan como un solo manchón.

    NO ejecutar con coords_area = COORDS_VM (ciudad completa):
    connectedComponents a 1m sobre ~80 km² es demasiado pesado para GEE.
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
        'n_manchones': int(n_manchones) if n_manchones is not None else None,
        'area_copa_ha': round(area_m2 / 10000, 3),
        'area_piloto_ha': round(area_piloto_ha, 2),
    }


# ============================================================
# ESTADO DE FUENTES
# ============================================================

FUENTES = [
    {
        'nombre': 'Canopy Height (GEE, 1m)',
        'rol': 'Numerador — estimación de copas/cobertura arbórea',
        'estado': 'en_progreso',
        'detalle': 'Dataset global de altura de dosel a 1m (Meta/WRI). Ya conectado: área/altura '
                    'agregada para toda la ciudad + conteo aproximado de manchones en zona piloto. '
                    'Error medio ~2.8m en altura — es una aproximación, no un inventario exacto.',
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
    'pendiente': '#9e9e9e',
    'en_progreso': '#f57c00',
    'conectada': '#2e7d32',
    'descartada_por_ahora': '#616161',
}

_LABEL_ESTADO = {
    'pendiente': '⏳ Pendiente',
    'en_progreso': '🔧 En progreso',
    'conectada': '✅ Conectada',
    'descartada_por_ahora': '⛔ Descartada por ahora',
}


# ============================================================
# RENDER
# ============================================================

def render_censo_arboreo():
    """Punto de entrada. Llamar desde render_modulo_villamaria()."""

    st.title("🌳 Censo Arbóreo · Villa María")
    st.caption("Objetivo municipal: 1 árbol por vivienda")
    st.markdown("---")

    st.info(
        "📍 Pantalla en construcción. Numerador (copa arbórea) conectado vía Canopy Height. "
        "Falta el denominador (viviendas edificadas, vía IDECOR) para calcular el ratio final."
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
            st.metric("Altura media de copa", f"{datos_ciudad['altura_media_m']} m"
                       if datos_ciudad['altura_media_m'] else "N/D")
        with c3:
            st.metric("Altura máxima detectada", f"{datos_ciudad['altura_max_m']} m"
                       if datos_ciudad['altura_max_m'] else "N/D")

        st.caption(
            "⚠️ Esto es superficie de copa, NO cantidad de árboles — varios árboles con copas "
            "que se tocan se ven como una sola mancha verde a esta escala."
        )
    except Exception as e:
        st.warning("No se pudo calcular la cobertura de copa para toda la ciudad.")
        st.caption(f"Detalle técnico: {e}")

    st.markdown("---")

    # ---- Zona piloto: conteo aproximado ----
    st.markdown("### 🧪 Conteo piloto — zona de prueba chica")
    st.caption(
        "Zona de ~0.5 km² usada para validar el método de conteo antes de pensar en escalarlo. "
        "Coordenadas de prueba — a ajustar con el municipio a un barrio real."
    )

    try:
        with st.spinner("Contando manchones de copa en la zona piloto..."):
            datos_piloto = cargar_canopy_conteo_piloto()

        c4, c5, c6 = st.columns(3)
        with c4:
            st.metric("Manchones detectados", datos_piloto['n_manchones'] or "N/D")
        with c5:
            st.metric("Área de copa en la zona", f"{datos_piloto['area_copa_ha']} ha")
        with c6:
            st.metric("Área total de la zona piloto", f"{datos_piloto['area_piloto_ha']} ha")

        st.warning(
            "⚠️ **'Manchones' ≠ 'árboles'.** Es un proxy: copas contiguas (ej. una hilera de árboles "
            "muy juntos) se cuentan como un solo manchón. Antes de usar este número para decisiones, "
            "hay que validarlo a ojo contra la imagen satelital de esta misma zona."
        )

        # Mapa de la zona piloto
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