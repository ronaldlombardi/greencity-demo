"""
modulo_censo.py
===============
Módulo de análisis socioespacial para GreenCity.
Cruza datos del Censo 2022 (INDEC) con acceso a verde (GEE).

Uso en dashboard:
    from modulo_censo import render_censo
    render_censo(ciudad_key)
"""

import json
import os
import streamlit as st


# ============================================================
# DATOS CENSO 2022 (INDEC — resultados definitivos)
# Fuente: censo.gob.ar → datos_definitivos_cordoba
# ============================================================

CENSO_DATA = {
    'villamaria': {
        'nombre': 'Villa María - Villa Nueva',
        'dept':   'Departamento San Martín',
        'pob_2022': 120000,
        'pob_2010':  101905,
        'variacion':  17.8,
        'viviendas':  48200,
        'hogares':    43500,
        # Condiciones habitacionales (proxy NBI)
        'piso_tierra':     3.2,
        'sin_agua_red':    8.1,
        'sin_inodoro':     2.4,
        'hacinamiento':    5.8,
        'sin_gas_red':    42.3,
        # Pirámide etaria estimada (% por grupo)
        'edad_0_14':   21.3,
        'edad_15_64':  63.8,
        'edad_65_mas': 14.9,
        # Grupos vulnerables que más necesitan verde cercano
        'ninos_pct':    21.3,
        'adultos_may':  14.9,
        # Índice de privación material (IPMH — proxy)
        'ipmh_pct':     8.4,
        # Resultado análisis verde (paso10_censo2022.py)
        'pct_pob_acceso':   100.0,
        'dist_media_pond':   30,
        'cv_equidad':        44,
        'zonas_criticas': [],  # sin zonas críticas detectadas
    },
    'sanfrancisco': {
        'nombre': 'San Francisco',
        'dept':   'Departamento San Justo',
        'pob_2022': 62000,
        'pob_2010':  59659,
        'variacion':   3.9,
        'viviendas':  26800,
        'hogares':    24100,
        'piso_tierra':    2.1,
        'sin_agua_red':   5.4,
        'sin_inodoro':    1.8,
        'hacinamiento':   4.2,
        'sin_gas_red':   38.7,
        'edad_0_14':  20.1,
        'edad_15_64': 64.5,
        'edad_65_mas': 15.4,
        'ninos_pct':   20.1,
        'adultos_may': 15.4,
        'ipmh_pct':    6.2,
        'pct_pob_acceso':  100.0,
        'dist_media_pond':  33,
        'cv_equidad':       37,
        'zonas_criticas': [],
    }
}


# ============================================================
# RENDER EN STREAMLIT
# ============================================================

def render_censo(ciudad_key):
    """Renderiza la sección censal completa en el dashboard."""

    d = CENSO_DATA.get(ciudad_key)
    if not d:
        st.error(f"Ciudad no encontrada: {ciudad_key}")
        return

    # Intentar cargar datos actualizados del archivo JSON (si corrió paso10)
    json_path = os.path.join(os.path.dirname(__file__), 'datos_censo_verde.json')
    if os.path.exists(json_path):
        try:
            with open(json_path) as f:
                datos_json = json.load(f)
            if ciudad_key in datos_json:
                dj = datos_json[ciudad_key]
                d['pct_pob_acceso']   = dj.get('pct_pob_acceso',   d['pct_pob_acceso'])
                d['dist_media_pond']  = dj.get('dist_media_pond',  d['dist_media_pond'])
                d['cv_equidad']       = dj.get('cv_equidad',       d['cv_equidad'])
                d['zonas_criticas']   = dj.get('zonas_criticas',   d['zonas_criticas'])
                st.caption("✅ Datos actualizados desde paso10_censo2022.py")
        except Exception:
            pass

    st.markdown("## 👥 Análisis Socioespacial — Censo 2022")
    st.caption(f"Fuente: INDEC Censo 2022 (resultados definitivos) · {d['dept']}")

    # ---- Métricas demográficas ----
    st.markdown("### 📊 Demografía")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        delta_pob = f"+{d['variacion']}% vs 2010"
        st.metric("Población 2022", f"{d['pob_2022']:,}", delta=delta_pob)
    with c2:
        st.metric("Viviendas", f"{d['viviendas']:,}")
    with c3:
        st.metric("Niños/as (0-14)", f"{d['ninos_pct']}%",
                  delta="Mayor necesidad de plazas")
    with c4:
        st.metric("Adultos mayores (65+)", f"{d['edad_65_mas']}%",
                  delta="Necesitan verde accesible")

    st.markdown("---")

    # ---- Condiciones habitacionales (proxy NBI) ----
    col_hab, col_verde = st.columns(2)

    with col_hab:
        st.markdown("### 🏠 Condiciones habitacionales")
        st.caption("Indicadores de vulnerabilidad (Censo 2022, nivel departamental)")

        indicadores = [
            ("Piso de tierra",          d['piso_tierra'],    5,  10),
            ("Sin agua de red interna", d['sin_agua_red'],   10, 20),
            ("Sin inodoro con descarga",d['sin_inodoro'],    3,   8),
            ("Hacinamiento",            d['hacinamiento'],   7,  15),
            ("Sin gas de red",          d['sin_gas_red'],    40, 60),
        ]

        for label, val, umbral_warn, umbral_bad in indicadores:
            color = (
                "#f44336" if val > umbral_bad
                else "#ff9800" if val > umbral_warn
                else "#4caf50"
            )
            icono = "🔴" if val > umbral_bad else "🟡" if val > umbral_warn else "🟢"
            st.markdown(
                f"""
                <div style='margin:6px 0'>
                  <div style='display:flex;justify-content:space-between;
                              font-size:0.85em;margin-bottom:2px'>
                    <span>{icono} {label}</span>
                    <span style='font-weight:600'>{val}%</span>
                  </div>
                  <div style='background:#e0e0e0;border-radius:4px;height:8px'>
                    <div style='width:{min(val*3,100):.0f}%;background:{color};
                                height:8px;border-radius:4px'></div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True
            )

        ipmh = d['ipmh_pct']
        nivel_ipmh = "🟢 Bajo" if ipmh < 8 else "🟡 Medio" if ipmh < 15 else "🔴 Alto"
        st.markdown(f"\n**IPMH estimado:** {ipmh}% de hogares con privación material → {nivel_ipmh}")

    with col_verde:
        st.markdown("### 🌿 Verde y equidad espacial")

        acc = d['pct_pob_acceso']
        cv  = d['cv_equidad']

        # Gauge acceso
        color_acc = "#4caf50" if acc >= 95 else "#ff9800" if acc >= 80 else "#f44336"
        st.markdown(
            f"""
            <div style='margin-bottom:14px'>
              <div style='display:flex;justify-content:space-between;font-size:0.85em'>
                <span>Población con buen acceso a verde</span>
                <span style='font-weight:700;color:{color_acc}'>{acc}%</span>
              </div>
              <div style='background:#e0e0e0;border-radius:6px;height:14px;margin-top:4px'>
                <div style='width:{acc}%;background:{color_acc};height:14px;border-radius:6px'></div>
              </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # Índice de equidad
        nivel_eq = "✅ Alta" if cv < 30 else "⚠️ Media" if cv < 60 else "❌ Baja"
        st.metric("Distancia media ponderada", f"{d['dist_media_pond']} m",
                  delta="por densidad poblacional")
        st.metric("Índice de equidad espacial", nivel_eq,
                  delta=f"CV: {cv}% (0% = perfectamente equitativo)")

        # Grupos más vulnerables
        st.markdown("**Grupos prioritarios:**")
        pob = d['pob_2022']
        ninos     = round(pob * d['ninos_pct'] / 100)
        adultos_m = round(pob * d['edad_65_mas'] / 100)
        ipmh_n    = round(pob * d['ipmh_pct'] / 100)
        st.markdown(
            f"""
            | Grupo | Población estimada |
            |-------|:-----------------:|
            | Niños/as (0-14) | ~{ninos:,} |
            | Adultos mayores (65+) | ~{adultos_m:,} |
            | Hogares con privación (IPMH) | ~{ipmh_n:,} |
            """
        )

    st.markdown("---")

    # ---- Cruce vulnerabilidad + verde ----
    st.markdown("### 🎯 Índice de Vulnerabilidad Ambiental")

    vuln_score = 0
    factores   = []

    if d['piso_tierra'] > 5:
        vuln_score += 1
        factores.append(f"🔴 Piso de tierra elevado ({d['piso_tierra']}%)")
    if d['sin_agua_red'] > 10:
        vuln_score += 1
        factores.append(f"🔴 Sin agua de red ({d['sin_agua_red']}%)")
    if d['hacinamiento'] > 7:
        vuln_score += 1
        factores.append(f"🔴 Hacinamiento elevado ({d['hacinamiento']}%)")
    if d['pct_pob_acceso'] < 90:
        vuln_score += 2
        factores.append(f"🔴 Acceso al verde bajo ({d['pct_pob_acceso']}%)")
    if d['cv_equidad'] > 60:
        vuln_score += 2
        factores.append(f"🔴 Distribución del verde muy desigual (CV={d['cv_equidad']}%)")
    if d['edad_65_mas'] > 18:
        vuln_score += 1
        factores.append(f"🟡 Alta proporción de adultos mayores ({d['edad_65_mas']}%)")

    nivel_vuln = (
        ("🟢 BAJA",   "#4caf50") if vuln_score <= 1
        else ("🟡 MEDIA",  "#ff9800") if vuln_score <= 3
        else ("🔴 ALTA",   "#f44336")
    )

    col_v1, col_v2 = st.columns([1, 2])
    with col_v1:
        st.markdown(
            f"""
            <div style='background:{nivel_vuln[1]}22;border:2px solid {nivel_vuln[1]};
                        border-radius:10px;padding:20px;text-align:center'>
              <div style='font-size:2em;font-weight:700;color:{nivel_vuln[1]}'>
                {nivel_vuln[0]}
              </div>
              <div style='font-size:0.85em;color:#555;margin-top:6px'>
                Score: {vuln_score}/8
              </div>
              <div style='font-size:0.8em;color:#555;margin-top:4px'>
                Índice de Vulnerabilidad<br>Ambiental Urbana
              </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col_v2:
        if factores:
            st.markdown("**Factores detectados:**")
            for f in factores:
                st.markdown(f"- {f}")
        else:
            st.success("✅ No se detectaron factores de vulnerabilidad significativos.")

        st.markdown(
            """
            > El **Índice de Vulnerabilidad Ambiental** combina condiciones
            > habitacionales del Censo 2022 con el acceso espacial al verde.
            > Identifica dónde es más urgente intervenir.
            """
        )

    st.markdown("---")

    # ---- Zonas prioritarias ----
    if d.get('zonas_criticas'):
        st.markdown("### 📍 Zonas prioritarias para intervención")
        st.caption("Sectores con menor acceso al verde y mayor densidad poblacional estimada")

        for i, z in enumerate(d['zonas_criticas'], 1):
            color_z = "#f44336" if z['pct_acceso'] < 80 else "#ff9800"
            st.markdown(
                f"""
                <div style='border-left:4px solid {color_z};padding:10px 14px;
                            margin:8px 0;background:{color_z}11;border-radius:0 8px 8px 0'>
                  <strong>Zona {i}</strong> — Coordenadas: {z['lat']:.4f}, {z['lon']:.4f}<br>
                  <span style='font-size:0.85em'>
                    Acceso al verde: <b>{z['pct_acceso']}%</b> ·
                    Distancia media: <b>{z['dist_m']} m</b> ·
                    Población estimada: <b>~{z['pob']:,} hab</b>
                  </span>
                </div>
                """,
                unsafe_allow_html=True
            )

        st.info(
            "💡 Para mayor precisión ejecutar `paso10_censo2022.py` con el shapefile "
            "de radios censales descargado de geoestadistica.indec.gob.ar"
        )

        st.info(
            "💡 **¿Por qué la distancia media es tan baja (~30m)?** "
            "El satélite detecta todo el verde visible: pastizales, baldíos y patios privados. "
            "Físicamente hay vegetación cerca, pero no necesariamente accesible al público. "
            "El módulo OSM es el complemento clave: muestra cuánto de ese verde es realmente público."
        )

    st.caption(
        "Fuentes: INDEC Censo 2022 — resultados definitivos (censo.gob.ar) · "
        "Condiciones habitacionales por departamento · "
        "Acceso al verde: GEE/WorldCover · "
        "Nota: datos demográficos a nivel municipal, condiciones habitacionales a nivel departamental."
    )
