"""
modulo_censo_arboreo.py — Ciudad Verde AI Agent
================================================
Plan de Forestación — Villa María.
Objetivo municipal: 1 árbol por casa.

Página de ACCIÓN (la situación por barrio está en modulo_barrios.py →
"Diagnóstico por barrio"):
  1. Cobertura de copa de la ciudad — Canopy Height (GEE, 1 m) ✅
  2. Base satelital — conteo por cimas (radio 2 m), imagen 16/03/2018,
     precalculado con consolidar_zonas.py ✅
  3. Calculadora — base satelital en zonas de casas + plantaciones
     desde marzo de 2018 cargadas por barrio → cumplimiento actualizado
     de la meta contra los lotes estimados ✅
  4. Denominador — lotes estimados (provisorio) → catastro municipal (pendiente)
  5. Margen de error validado — conteo automático vs conteo manual (pendiente)

Uso en dashboard:
    from modulo_censo_arboreo import render_censo_arboreo
    render_censo_arboreo()
"""

import os
import json

import ee
import pandas as pd
import streamlit as st


# ============================================================
# CONFIGURACIÓN
# ============================================================

CANOPY_ASSET = 'projects/meta-forest-monitoring-okw37/assets/CanopyHeight'
ALTURA_MIN_ARBOL = 2

RUTA_BARRIOS = os.path.join(os.path.dirname(__file__), 'data', 'barrios_villamaria.geojson')
RUTA_RESUMEN = os.path.join(os.path.dirname(__file__), 'data', 'zonas_villamaria_resumen.json')

FECHA_IMAGEN = "16/03/2018 (≈92% de la ciudad) y 09/10/2019 (franja oeste)"
CORTE_PLANTACIONES = "marzo de 2018"


# ============================================================
# GEE — COBERTURA AGREGADA, ACOTADA A LOS BARRIOS REALES
# ============================================================

@st.cache_data(show_spinner=False, ttl=86400)
def cargar_canopy_ciudad():
    """
    Área cubierta por copas y altura media/máxima, acotado a la unión
    real de los 38 barrios de Villa María (ya no un bbox que incluye
    Villa Nueva). Requiere data/barrios_villamaria.geojson.
    """
    if not os.path.exists(RUTA_BARRIOS):
        return None

    with open(RUTA_BARRIOS, encoding='utf-8') as f:
        barrios_geojson = json.load(f)

    fc = ee.FeatureCollection(barrios_geojson)
    area = fc.geometry()

    canopy = ee.ImageCollection(CANOPY_ASSET).mosaic().rename('altura').clip(area)
    mask_arbol = canopy.gte(ALTURA_MIN_ARBOL)
    altura_arbol = canopy.updateMask(mask_arbol)

    area_stats = mask_arbol.multiply(ee.Image.pixelArea()).reduceRegion(
        reducer=ee.Reducer.sum(), geometry=area, scale=1,
        maxPixels=1e10, bestEffort=True, tileScale=8,
    ).getInfo()
    area_m2 = list(area_stats.values())[0] if area_stats else 0

    stats_altura = altura_arbol.reduceRegion(
        reducer=ee.Reducer.mean().combine(ee.Reducer.max(), sharedInputs=True),
        geometry=area, scale=1, maxPixels=1e10, bestEffort=True, tileScale=8,
    ).getInfo()

    return {
        'area_copa_ha': round(area_m2 / 10000, 1) if area_m2 else 0,
        'altura_media_m': round(stats_altura.get('altura_mean'), 1) if stats_altura.get('altura_mean') else None,
        'altura_max_m': round(stats_altura.get('altura_max'), 1) if stats_altura.get('altura_max') else None,
    }


# ============================================================
# BASE SATELITAL — LEE EL RESUMEN PRECALCULADO
# ============================================================

@st.cache_data(show_spinner=False, ttl=3600)
def _cargar_resumen():
    if not os.path.exists(RUTA_RESUMEN):
        return None
    with open(RUTA_RESUMEN, encoding='utf-8') as f:
        return json.load(f)


def _num(n):
    """Entero con separador de miles argentino."""
    return f"{int(n):,}".replace(",", ".")


def _pct(x):
    return f"{x:.1f}".replace(".", ",") + " %"


# ============================================================
# ESTADO DE FUENTES
# ============================================================

FUENTES = [
    {
        'nombre': 'Canopy Height (Meta/WRI, 1 m)',
        'rol': 'Numerador — conteo de árboles',
        'estado': 'conectada',
        'detalle': f'Dataset global de altura de dosel a 1 m. Imagen sobre Villa María: {FECHA_IMAGEN}. '
                   'Conteo por detección de cimas (radio 2 m, umbral 2 m), precalculado localmente. '
                   'Falta el margen de error empírico (ver validación).',
    },
    {
        'nombre': 'Barrios (Municipalidad de Villa María)',
        'rol': 'Unidad de agregación — 38 barrios reales',
        'estado': 'conectada',
        'detalle': 'Fuente: datos.villamaria.gob.ar, dataset "Barrios" (2021), shapefile oficial.',
    },
    {
        'nombre': 'Zonas por barrio (tipos de zona, base LCZ)',
        'rol': 'Dónde están las casas — 82 zonas en los 38 barrios',
        'estado': 'conectada',
        'detalle': 'Delimitadas manualmente barrio por barrio sobre la imagen satelital. '
                   'Tipos basados en las Zonas Climáticas Locales (Stewart y Oke, 2012).',
    },
    {
        'nombre': 'Catastro municipal / IDECOR',
        'rol': 'Denominador — viviendas reales por barrio',
        'estado': 'en_progreso',
        'detalle': 'Hoy se usa una estimación provisoria de lotes (cuadra de 130 m eje a eje, '
                   'calle de 19 m, frente de 10 m, factor de ocupación por tipo de zona). '
                   'Se reemplaza por el número real de viviendas cuando la Municipalidad aporte el catastro.',
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

    st.title("🌳 Plan de Forestación · Villa María")

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

    # ---- Ciudad completa: área y altura de copa (acotado a barrios reales) ----
    st.markdown("### 🌍 Cobertura de copa arbórea — ciudad completa")
    st.caption(f"Fuente: Canopy Height (Meta/WRI, 1m) · umbral de altura: {ALTURA_MIN_ARBOL}m · "
               "área acotada a los 38 barrios oficiales (excluye Villa Nueva)")

    try:
        with st.spinner("Calculando cobertura de copa en Villa María..."):
            datos_ciudad = cargar_canopy_ciudad()

        if datos_ciudad:
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Área cubierta por copas", f"{datos_ciudad['area_copa_ha']} ha")
            with c2:
                st.metric("Altura media de copa",
                          f"{datos_ciudad['altura_media_m']} m" if datos_ciudad['altura_media_m'] else "N/D")
            with c3:
                st.metric("Altura máxima detectada",
                          f"{datos_ciudad['altura_max_m']} m" if datos_ciudad['altura_max_m'] else "N/D")
        else:
            st.info("Falta data/barrios_villamaria.geojson — correr convertir_barrios.py primero.")
    except Exception as e:
        st.warning("No se pudo calcular la cobertura de copa para toda la ciudad.")
        st.caption(f"Detalle técnico: {e}")

    st.markdown("---")

    res = _cargar_resumen()
    if not res:
        st.info("Falta data/zonas_villamaria_resumen.json — correr `python consolidar_zonas.py` localmente.")
        return

    ciudad = res['ciudad']
    meta = ciudad['meta_1_arbol_por_casa']

    # ---- Base satelital ----
    st.markdown("### 🛰️ Base satelital")
    st.caption(f"Imagen: {FECHA_IMAGEN} · conteo por cimas de copa · precalculado (consolidar_zonas.py)")

    b1, b2, b3 = st.columns(3)
    with b1:
        st.metric("🌳 Árboles detectados", _num(ciudad['total_arboles']))
    with b2:
        st.metric("En zonas de casas", _num(meta['arboles_zonas_casas']))
    with b3:
        st.metric("Lotes estimados (provisorio)", _num(meta['lotes_estimados']))

    st.info(
        "📍 La situación barrio por barrio —mapa de zonas, cumplimiento de la meta y ranking de "
        "prioridades— está en la sección **🏘️ Diagnóstico por barrio**."
    )

    st.markdown("---")

    # ---- Calculadora: satelital + plantaciones desde marzo de 2018 ----
    st.markdown(f"### 🧮 Calculadora de forestación — satelital + plantado desde {CORTE_PLANTACIONES}")
    st.caption(
        f"La imagen satelital es de {FECHA_IMAGEN}: no puede ver plantaciones posteriores, ni "
        f"árboles jóvenes que todavía no alcanzaron los {ALTURA_MIN_ARBOL} m de altura. Cargá acá, por "
        f"barrio, los árboles plantados y registrados por la Municipalidad **desde {CORTE_PLANTACIONES}** "
        "en zonas de casas — así se suman sin repetir los que el satélite ya cuenta."
    )

    barrios = sorted(res['barrios'], key=lambda b: b['barrio'])
    nombres = [b['barrio'] for b in barrios]

    if ('plantaciones_input_2018' not in st.session_state
            or list(st.session_state['plantaciones_input_2018']['Barrio']) != nombres):
        st.session_state['plantaciones_input_2018'] = pd.DataFrame({
            'Barrio': nombres,
            'Árboles en zonas de casas (satélite)': [b['meta_1_arbol_por_casa']['arboles_zonas_casas'] for b in barrios],
            'Lotes estimados': [b['meta_1_arbol_por_casa']['lotes_estimados'] for b in barrios],
            f'Plantados desde {CORTE_PLANTACIONES} (cargar)': [0] * len(nombres),
        })

    col_plant = f'Plantados desde {CORTE_PLANTACIONES} (cargar)'
    editado = st.data_editor(
        st.session_state['plantaciones_input_2018'],
        column_config={
            'Barrio': st.column_config.TextColumn(disabled=True),
            'Árboles en zonas de casas (satélite)': st.column_config.NumberColumn(disabled=True),
            'Lotes estimados': st.column_config.NumberColumn(disabled=True),
            col_plant: st.column_config.NumberColumn(min_value=0, step=1),
        },
        hide_index=True,
        use_container_width=True,
        key='editor_plantaciones_2018',
    )
    st.session_state['plantaciones_input_2018'] = editado

    calc = editado.copy()
    calc[col_plant] = calc[col_plant].fillna(0).astype(int)
    calc['Total'] = calc['Árboles en zonas de casas (satélite)'] + calc[col_plant]
    calc['Faltan'] = (calc['Lotes estimados'] - calc['Total']).clip(lower=0)

    total_sat = int(calc['Árboles en zonas de casas (satélite)'].sum())
    total_plant = int(calc[col_plant].sum())
    total = int(calc['Total'].sum())
    lotes = int(calc['Lotes estimados'].sum())
    faltan = int(calc['Faltan'].sum())
    cumpl = total / lotes * 100 if lotes else 0

    cc1, cc2, cc3, cc4 = st.columns(4)
    with cc1:
        st.metric("Base satelital (zonas de casas)", _num(total_sat))
    with cc2:
        st.metric(f"Plantados desde {CORTE_PLANTACIONES}", _num(total_plant))
    with cc3:
        st.metric("Cumplimiento actualizado", _pct(min(cumpl, 100)) if cumpl < 100 else "Meta alcanzada",
                  delta=f"+{_pct(total_plant / lotes * 100)}" if lotes and total_plant else None)
    with cc4:
        st.metric("Faltan para la meta", f"{_num(faltan)} árboles")

    st.info(
        "ℹ️ Es una **aproximación de trabajo**, no un censo validado: la base satelital tiene su propio "
        "margen de error, los lotes son una estimación provisoria hasta contar con el catastro, y el "
        f"resultado depende de que lo cargado no incluya árboles plantados antes de {CORTE_PLANTACIONES}. "
        "Los faltantes se suman barrio por barrio (el excedente de un barrio no compensa a otro). "
        "**No se guarda entre sesiones.**"
    )

    st.markdown("---")

    # ---- Validación del método ----
    st.markdown("### 🧪 Validación del método — pendiente")
    st.warning(
        "⏳ **Margen de error: pendiente de calcular.** Próximo paso: elegir junto con la Municipalidad "
        "una muestra de manzanas, contar los árboles a mano sobre la imagen satelital y compararlos con el "
        "conteo automático, para reportar un % de error real y auditable — no una cifra genérica."
    )

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
        "Ciudad Verde AI Agent · Villa María · Plan de Forestación · "
        "Canopy Height (Meta/WRI) + Barrios y zonas + lotes estimados (provisorio)"
    )