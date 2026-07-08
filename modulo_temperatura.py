"""
modulo_temperatura.py
=====================
Módulo reutilizable de Temperatura Superficial (LST) para GreenCity.
Integra datos de Landsat 8/9 con WorldCover para análisis de isla de calor.

Uso en dashboard:
    from modulo_temperatura import cargar_lst, render_temperatura
    render_temperatura(ciudad_key, area_ee, worldcover)
"""

import ee
import streamlit as st


# ============================================================
# CÁLCULO LST
# ============================================================

def _calcular_lst(imagen):
    """LST en °C desde Landsat 8/9 Collection 2 Level 2."""
    ndvi = imagen.normalizedDifference(['SR_B5', 'SR_B4']).rename('NDVI')
    pv   = ndvi.subtract(0.2).divide(0.3).pow(2).clamp(0, 1)
    em   = pv.multiply(0.004).add(0.986).rename('emissividad')
    tb   = imagen.select('ST_B10').multiply(0.00341802).add(149.0)
    lst_k = tb.divide(
        tb.divide(14388).multiply(ee.Image(10.895).log()).add(1).multiply(em.log()).add(1)
    )
    lst_c = lst_k.subtract(273.15).rename('LST_celsius')
    return imagen.addBands([ndvi, em, lst_c])


def _media(img, area):
    r = img.reduceRegion(
        reducer=ee.Reducer.mean(), geometry=area, scale=30, maxPixels=1e9
    ).getInfo()
    v = list(r.values())[0]
    return round(v, 1) if v is not None else None


def _percentil(img, area, p):
    r = img.reduceRegion(
        reducer=ee.Reducer.percentile([p]), geometry=area, scale=30, maxPixels=1e9
    ).getInfo()
    v = list(r.values())[0]
    return round(v, 1) if v is not None else None


# ============================================================
# FUNCIÓN PRINCIPAL DE CARGA (cacheada)
# ============================================================

@st.cache_data(show_spinner=False, ttl=3600)
def cargar_lst(coords_area, fecha_inicio='2023-12-01', fecha_fin='2024-03-01'):
    """
    Calcula métricas de temperatura superficial para el área dada.

    Parámetros
    ----------
    coords_area   : list  – coordenadas [lon, lat] del polígono
    fecha_inicio  : str   – 'YYYY-MM-DD'
    fecha_fin     : str   – 'YYYY-MM-DD'

    Retorna
    -------
    dict con todas las métricas, o None si no hay imágenes disponibles.
    """
    area = ee.Geometry.Polygon([coords_area])

    coleccion = (
        ee.ImageCollection('LANDSAT/LC08/C02/T1_L2')
        .merge(ee.ImageCollection('LANDSAT/LC09/C02/T1_L2'))
        .filterDate(fecha_inicio, fecha_fin)
        .filterBounds(area)
        .filter(ee.Filter.lt('CLOUD_COVER', 20))
        .map(_calcular_lst)
    )

    n_imagenes = coleccion.size().getInfo()
    if n_imagenes == 0:
        return None

    lst_med  = coleccion.select('LST_celsius').median().clip(area)
    ndvi_med = coleccion.select('NDVI').median().clip(area)
    wc       = ee.Image('ESA/WorldCover/v100/2020').clip(area)

    mask_urb   = wc.eq(50)
    mask_verde = wc.eq(10).Or(wc.eq(30))

    t_total  = _media(lst_med, area)
    t_urbano = _media(lst_med.updateMask(mask_urb), area)
    t_verde  = _media(lst_med.updateMask(mask_verde), area)
    t_p95    = _percentil(lst_med, area, 95)
    t_p5     = _percentil(lst_med, area, 5)

    delta_uhi = round(t_urbano - t_verde, 1) if (t_urbano and t_verde) else None

    # Correlación NDVI
    t_ndvi_alto = _media(lst_med.updateMask(ndvi_med.gt(0.4)), area)
    t_ndvi_bajo = _media(lst_med.updateMask(ndvi_med.lt(0.2)), area)
    enfriamiento = round(t_ndvi_bajo - t_ndvi_alto, 1) if (t_ndvi_alto and t_ndvi_bajo) else None

    return {
        'n_imagenes': n_imagenes,
        'periodo': f"{fecha_inicio} → {fecha_fin}",
        't_media': t_total,
        't_urbano': t_urbano,
        't_verde': t_verde,
        't_p95': t_p95,
        't_p5': t_p5,
        'delta_uhi': delta_uhi,
        't_ndvi_alto': t_ndvi_alto,
        't_ndvi_bajo': t_ndvi_bajo,
        'enfriamiento_verde': enfriamiento,
    }


# ============================================================
# RENDER EN STREAMLIT
# ============================================================

def render_temperatura(datos_lst):
    """
    Renderiza la sección completa de temperatura en el dashboard.
    Llamar con el resultado de cargar_lst().
    """
    if datos_lst is None:
        st.warning("No se encontraron imágenes Landsat para el período seleccionado.")
        st.info("Intentá ampliar el rango de fechas o reducir el filtro de nubosidad.")
        return

    d = datos_lst

    st.markdown("## 🌡️ Temperatura Superficial (LST)")
    st.caption(
        f"Fuente: Landsat 8/9 (USGS) · {d['n_imagenes']} imágenes · Período: {d['periodo']}"
    )

    # --- Métricas principales ---
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Temp. media", f"{d['t_media']}°C" if d['t_media'] else "N/D")

    with col2:
        delta_str = None
        delta_color = "off"
        if d['delta_uhi'] is not None:
            delta_str = f"+{d['delta_uhi']}°C vs verde"
            delta_color = "inverse" if d['delta_uhi'] > 2 else "normal"
        st.metric(
            "Zona urbana",
            f"{d['t_urbano']}°C" if d['t_urbano'] else "N/D",
            delta=delta_str,
            delta_color=delta_color
        )

    with col3:
        st.metric("Zona verde", f"{d['t_verde']}°C" if d['t_verde'] else "N/D")

    with col4:
        st.metric("Punto más caliente (P95)", f"{d['t_p95']}°C" if d['t_p95'] else "N/D")

    st.markdown("---")

    # --- Isla de calor ---
    col_a, col_b = st.columns([1, 2])

    with col_a:
        st.markdown("### 🏙️ Isla de Calor Urbano")
        if d['delta_uhi'] is not None:
            uhi = d['delta_uhi']
            if uhi > 3:
                nivel = "🔴 ALTO"
                desc = f"El asfalto y el hormigón elevan la temperatura **{uhi}°C** sobre las zonas verdes."
            elif uhi > 1.5:
                nivel = "🟡 MODERADO"
                desc = f"Diferencia de **{uhi}°C** entre zonas urbanas y verdes."
            else:
                nivel = "🟢 BAJO"
                desc = f"Solo **{uhi}°C** de diferencia. La vegetación distribuye bien el calor."

            st.markdown(f"**Intensidad:** {nivel}")
            st.markdown(desc)

            # Barra visual
            max_uhi = 6.0
            pct = min(uhi / max_uhi, 1.0)
            color = "#ef5350" if uhi > 3 else "#ff9800" if uhi > 1.5 else "#4caf50"
            st.markdown(
                f"""
                <div style='background:#e0e0e0;border-radius:6px;height:14px;margin-top:8px'>
                  <div style='width:{pct*100:.0f}%;background:{color};height:14px;border-radius:6px'></div>
                </div>
                <p style='font-size:0.75em;color:#888;margin-top:4px'>
                  0°C &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
                  {uhi}°C &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 6°C+
                </p>
                """,
                unsafe_allow_html=True
            )
        else:
            st.info("No se pudo calcular el diferencial UHI.")

    with col_b:
        st.markdown("### 🌿 Efecto enfriador de la vegetación")
        if d['enfriamiento_verde'] is not None:
            enf = d['enfriamiento_verde']
            st.markdown(
                f"""
                Las zonas con **NDVI alto (>0.4)** — parques, arbolado denso — 
                tienen una temperatura superficial **{enf}°C menor** que las zonas 
                de suelo desnudo o asfalto (NDVI <0.2).
                
                | Cobertura | Temperatura media |
                |-----------|:-----------------:|
                | Verde denso (NDVI > 0.4) | **{d['t_ndvi_alto']}°C** |
                | Suelo/asfalto (NDVI < 0.2) | **{d['t_ndvi_bajo']}°C** |
                | Diferencia | **{enf}°C** |
                """
            )
            if enf > 4:
                st.success(f"✅ Cada hectárea de arbolado puede reducir hasta {enf}°C la temperatura local.")
            else:
                st.info(f"💡 Con más forestación, el enfriamiento podría superar los 5°C en verano.")
        else:
            st.info("Datos de correlación NDVI-LST no disponibles.")

    st.markdown("---")

    # --- Interpretación para municipios ---
    st.markdown("### 📝 Interpretación para planificación urbana")

    if d['t_p95'] and d['t_media']:
        diff_max = round(d['t_p95'] - d['t_media'], 1)
        st.markdown(
            f"""
            Los puntos más calientes de la ciudad alcanzan **{d['t_p95']}°C**, 
            es decir **{diff_max}°C por encima** del promedio general. 
            Estos son los candidatos prioritarios para intervención verde.
            
            **Acciones recomendadas:**
            - 🌳 Forestar los sectores con LST > {round(d['t_media'] + 2, 0):.0f}°C
            - 💧 Incorporar superficies permeables y agua en zonas críticas
            - 🏫 Priorizar escuelas y centros de salud en zonas de alta temperatura
            """
        )

    st.caption(
        "Metodología: LST calculada con corrección de emisividad por NDVI (Sobrino et al.). "
        "Los valores corresponden a medianas de temperatura superficial en período estival."
    )
