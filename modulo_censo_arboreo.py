"""
modulo_censo_arboreo.py — Ciudad Verde AI Agent
================================================
Plan de Forestación — Villa María.
Objetivo municipal: 1 árbol por vivienda.

Este módulo se construye paso a paso:
  1. Estructura de pantalla ✅
  2. Numerador — Canopy Height (GEE, 1m):
       - Cobertura agregada ciudad, acotada a los 38 barrios reales
         (fuente: datos.villamaria.gob.ar) — ya NO incluye Villa Nueva ✅
       - Conteo piloto en zona chica (validación de método) ✅
       - Censo completo POR BARRIO REAL — precalculado local ✅
         (ver convertir_barrios.py + exportar_censo_json.py)
  3. Calculadora — satelital (base) + plantaciones desde 2021 cargadas
     a mano por barrio, para aproximar el total actual sin duplicar lo
     que el satélite ya cuenta ✅
  4. Denominador — Catastro IDECOR (parcelas edificadas por manzana)
  5. Cruce numerador/denominador → ratio árboles/vivienda por barrio
  6. Margen de error validado — comparar conteo automático vs conteo
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
ALTURA_MIN_ARBOL = 2

# ⚠️ ZONA PILOTO DE PRUEBA — coordenadas aproximadas, A AJUSTAR
# con el municipio a un barrio real una vez validado el método.
COORDS_PILOTO = [
    [-63.245, -32.405], [-63.238, -32.405],
    [-63.238, -32.412], [-63.245, -32.412], [-63.245, -32.405]
]

RUTA_BARRIOS = os.path.join(os.path.dirname(__file__), 'data', 'barrios_villamaria.geojson')
RUTA_CENSO_JSON = os.path.join(os.path.dirname(__file__), 'data', 'censo_arboreo_villamaria.json')


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
# GEE — CONTEO PILOTO (ZONA CHICA, VALIDACIÓN DE MÉTODO)
# ============================================================

@st.cache_data(show_spinner=False, ttl=86400)
def cargar_canopy_conteo_piloto(coords_area=COORDS_PILOTO):
    """Conteo de árboles en zona piloto chica — validación del método."""
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
# CENSO COMPLETO POR BARRIO — LEE EL JSON PRECALCULADO
# ============================================================

@st.cache_data(show_spinner=False, ttl=3600)
def _cargar_censo_json():
    if not os.path.exists(RUTA_CENSO_JSON):
        return None
    with open(RUTA_CENSO_JSON, encoding='utf-8') as f:
        return json.load(f)


@st.cache_data(show_spinner=False, ttl=3600)
def _cargar_barrios_geojson():
    if not os.path.exists(RUTA_BARRIOS):
        return None
    with open(RUTA_BARRIOS, encoding='utf-8') as f:
        return json.load(f)


def _color_densidad(densidad_ha):
    """Color según densidad de árboles/ha (para el mapa y el ranking)."""
    if densidad_ha is None:
        return '#555555'
    if densidad_ha >= 40:
        return '#1b5e20'
    if densidad_ha >= 20:
        return '#4caf50'
    if densidad_ha >= 8:
        return '#aed581'
    if densidad_ha > 0:
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
        'detalle': 'Dataset global de altura de dosel a 1m (Meta/WRI). Conectado: agregado ciudad '
                    '(acotado a barrios reales), piloto de validación y censo completo por barrio '
                    '(precalculado local). Falta el margen de error empírico (próximo paso).',
    },
    {
        'nombre': 'Barrios (Municipalidad de Villa María)',
        'rol': 'Unidad de agregación — 38 barrios reales',
        'estado': 'conectada',
        'detalle': 'Fuente: datos.villamaria.gob.ar, dataset "Barrios" (2021), shapefile oficial. '
                    'Reemplaza la grilla arbitraria y el bbox que incluía Villa Nueva.',
    },
    {
        'nombre': 'Catastro IDECOR (WFS/WMS)',
        'rol': 'Denominador — parcelas edificadas por barrio',
        'estado': 'pendiente',
        'detalle': 'Distingue parcelas baldío/edificado/PH. Da el número real de viviendas '
                    'por barrio para calcular el ratio árboles/vivienda. Requiere consulta '
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

    # ---- Censo completo por barrio (precalculado, lee JSON local) ----
    st.markdown("### 🌳 Base satelital por barrio")
    st.caption(
        "38 barrios oficiales (fuente: datos.villamaria.gob.ar). "
        "Precalculado localmente — ver exportar_censo_json.py."
    )

    censo = _cargar_censo_json()
    barrios_geo = _cargar_barrios_geojson()

    if censo:
        st.caption(f"Último cálculo: {censo['fecha_calculo'][:16].replace('T', ' ')}")

        c4, c5, c6 = st.columns(3)
        with c4:
            st.metric("🌳 Árboles contados", f"{censo['total_arboles']:,}".replace(",", "."))
        with c5:
            st.metric("Área total de copa", f"{censo['total_area_copa_ha']} ha")
        with c6:
            st.metric("Barrios procesados", f"{censo['barrios_procesados']}/{censo['barrios_totales']}")

        # Calcular densidad por barrio (árboles/ha)
        validos = [b for b in censo['barrios'] if b['n_arboles'] is not None and b.get('area_barrio_ha')]
        for b in validos:
            b['densidad_arboles_ha'] = round(b['n_arboles'] / b['area_barrio_ha'], 1) if b['area_barrio_ha'] else 0

        # ---- Ranking top 5 / bottom 5 ----
        if validos:
            ordenados = sorted(validos, key=lambda b: -b['densidad_arboles_ha'])
            top5 = ordenados[:5]
            bottom5 = ordenados[-5:][::-1]

            st.markdown("#### 🏆 Ranking de barrios — densidad arbórea (árboles/ha)")
            col_top, col_bottom = st.columns(2)

            with col_top:
                st.markdown("**🟢 Los 5 con mayor densidad**")
                for i, b in enumerate(top5, 1):
                    st.markdown(
                        f"<div style='display:flex;justify-content:space-between;padding:6px 0;"
                        f"border-bottom:1px solid rgba(255,255,255,0.08)'>"
                        f"<span>#{i} {b['nombre'].title()}</span>"
                        f"<span style='font-weight:700;color:#4caf50'>{b['densidad_arboles_ha']} árb/ha</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

            with col_bottom:
                st.markdown("**🟡 Los 5 con menor densidad**")
                for i, b in enumerate(bottom5, 1):
                    st.markdown(
                        f"<div style='display:flex;justify-content:space-between;padding:6px 0;"
                        f"border-bottom:1px solid rgba(255,255,255,0.08)'>"
                        f"<span>#{i} {b['nombre'].title()}</span>"
                        f"<span style='font-weight:700;color:#f57c00'>{b['densidad_arboles_ha']} árb/ha</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

            st.caption(
                "💡 Los barrios con menor densidad son los primeros candidatos para planes de "
                "forestación dirigidos al objetivo '1 árbol por casa'."
            )

        st.markdown("---")

        # ---- Calculadora: satelital + plantaciones recientes cargadas a mano ----
        st.markdown("### 🧮 Calculadora de forestación — satelital + plantado reciente")
        st.caption(
            "El satélite (Meta/WRI Canopy Height) usa fotos de entre 2009 y 2020 — no puede ver "
            "plantaciones posteriores a esa fecha, ni árboles jóvenes que todavía no alcanzaron los "
            f"{ALTURA_MIN_ARBOL}m de altura mínima. Cargá acá, por barrio, los árboles plantados y "
            "registrados por la Municipalidad **desde 2021 en adelante** — así se suman sin repetir "
            "los que el satélite ya cuenta."
        )

        import pandas as pd

        barrios_nombres = [b['nombre'] for b in censo['barrios']]
        base_por_barrio = {b['nombre']: b['n_arboles'] or 0 for b in censo['barrios']}

        if ('plantaciones_input' not in st.session_state
                or set(st.session_state['plantaciones_input']['Barrio']) != set(barrios_nombres)):
            st.session_state['plantaciones_input'] = pd.DataFrame({
                'Barrio': barrios_nombres,
                'Árboles satelitales (base)': [base_por_barrio[n] for n in barrios_nombres],
                'Plantados desde 2021 (cargar)': [0] * len(barrios_nombres),
            })

        editado = st.data_editor(
            st.session_state['plantaciones_input'],
            column_config={
                'Barrio': st.column_config.TextColumn(disabled=True),
                'Árboles satelitales (base)': st.column_config.NumberColumn(disabled=True),
                'Plantados desde 2021 (cargar)': st.column_config.NumberColumn(min_value=0, step=1),
            },
            hide_index=True,
            use_container_width=True,
            key='editor_plantaciones_forestacion',
        )
        st.session_state['plantaciones_input'] = editado

        editado = editado.copy()
        editado['Total estimado'] = (
            editado['Árboles satelitales (base)'] + editado['Plantados desde 2021 (cargar)']
        )

        total_satelital = int(editado['Árboles satelitales (base)'].sum())
        total_plantado = int(editado['Plantados desde 2021 (cargar)'].sum())
        total_estimado = int(editado['Total estimado'].sum())

        cc1, cc2, cc3 = st.columns(3)
        with cc1:
            st.metric("Base satelital (2009–2020)", f"{total_satelital:,}".replace(",", "."))
        with cc2:
            st.metric("Plantados desde 2021 (cargado)", f"{total_plantado:,}".replace(",", "."))
        with cc3:
            st.metric("Total estimado hoy", f"{total_estimado:,}".replace(",", "."))

        st.info(
            "ℹ️ Este total es una **aproximación**, no un censo validado: la base satelital tiene "
            "su propio margen de error (ver la sección de validación más abajo) y el resultado "
            "depende de que lo cargado sea preciso y no incluya árboles plantados antes de 2021 "
            "(que ya podrían estar en la base satelital). **No se guarda entre sesiones** — es una "
            "calculadora de trabajo, no un registro oficial."
        )

        st.markdown("---")

        # ---- Mapa por barrio (polígonos reales, coloreados por densidad) ----
        st.markdown("#### 🗺️ Mapa por barrio — densidad arbórea")

        if barrios_geo:
            censo_por_nombre = {b['nombre']: b for b in censo['barrios']}

            lat_centro = sum(b['centro'][0] for b in censo['barrios']) / len(censo['barrios'])
            lon_centro = sum(b['centro'][1] for b in censo['barrios']) / len(censo['barrios'])

            m_censo = folium.Map(location=[lat_centro, lon_centro], zoom_start=13, tiles=None)
            folium.TileLayer(
                tiles='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}',
                attr='© Google', name='🌍 Satelital', max_zoom=20, show=True,
            ).add_to(m_censo)

            for feat in barrios_geo['features']:
                nombre = feat['properties']['NOMBRE']
                stats = censo_por_nombre.get(nombre, {})
                densidad = None
                if stats.get('n_arboles') is not None and stats.get('area_barrio_ha'):
                    densidad = round(stats['n_arboles'] / stats['area_barrio_ha'], 1)
                color = _color_densidad(densidad)

                tooltip = f"{nombre.title()}"
                if stats.get('n_arboles') is not None:
                    tooltip += f" — {stats['n_arboles']} árboles ({densidad} árb/ha)"
                else:
                    tooltip += " — sin datos"

                folium.GeoJson(
                    feat,
                    style_function=lambda x, c=color: {
                        'fillColor': c, 'color': '#ffffff', 'weight': 1,
                        'fillOpacity': 0.55,
                    },
                    tooltip=tooltip,
                ).add_to(m_censo)

                st_folium(m_censo, width="100%", height=520, returned_objects=[], key="mapa_censo_vm")

            # --- Fix: bug conocido de Streamlit (issue #7376) donde el iframe
            # del mapa a veces queda con altura 0 tras un cambio de sección.
            # Se acota solo a este mapa buscando el último iframe insertado.
            import streamlit.components.v1 as components
            components.html(
                """
                <script>
                (function() {
                    let intentos = 0;
                    const maxIntentos = 20;
                    const intervalo = setInterval(function() {
                        intentos++;
                        const parentDoc = window.parent.document;
                        const iframes = parentDoc.querySelectorAll(
                            'iframe[title="streamlit_folium.st_folium"]'
                        );
                        if (iframes.length > 0) {
                            const mapa = iframes[iframes.length - 1];
                            if (mapa.getAttribute('height') === '0' ||
                                mapa.style.height === '0px') {
                                mapa.style.height = '520px';
                                mapa.setAttribute('height', '520');
                            }
                        }
                        if (intentos >= maxIntentos) {
                            clearInterval(intervalo);
                        }
                    }, 200);
                })();
                </script>
                """,
                height=0,
            )
            st.caption(
                "🟢 Alta densidad (≥40 árb/ha) · 🟩 Media (20-39) · 🟡 Baja (8-19) · "
                "⚪ Muy baja (1-7) · ⚫ Sin datos/error"
            )
        else:
            st.info("Falta data/barrios_villamaria.geojson para dibujar el mapa por barrio.")

    else:
        st.info(
            "Censo completo aún no calculado. Correr `python convertir_barrios.py` y luego "
            "`python exportar_censo_json.py` localmente para generarlo."
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
        "Ciudad Verde AI Agent · Villa María · Plan de Forestación · "
        "En desarrollo — Canopy Height (GEE) + Barrios (Municipalidad) + Catastro IDECOR"
    )
