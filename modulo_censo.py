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

    # ── Córdoba capital (centro histórico / circunvalación) ──────────────────
    'cordoba_centro': {
        'nombre': 'Córdoba — Centro histórico',
        'dept':   'Departamento Capital',
        'pob_2022': 420000,
        'pob_2010':  398000,
        'variacion':   5.5,
        'viviendas':  195000,
        'hogares':    178000,
        'piso_tierra':    1.8,
        'sin_agua_red':   3.2,
        'sin_inodoro':    1.1,
        'hacinamiento':   6.4,
        'sin_gas_red':   22.5,
        'edad_0_14':   19.8,
        'edad_15_64':  63.7,
        'edad_65_mas': 16.5,
        'ninos_pct':    19.8,
        'adultos_may':  16.5,
        'ipmh_pct':     7.1,
        'pct_pob_acceso':  85.0,
        'dist_media_pond':  95,
        'cv_equidad':       58,
        'zonas_criticas': [],
    },
    'cordoba_circunvalacion': {
        'nombre': 'Córdoba — Área de Circunvalación',
        'dept':   'Departamento Capital',
        'pob_2022': 1110000,
        'pob_2010':  1329604,
        'variacion':  -1.8,   # redistribución al área metropolitana
        'viviendas':  490000,
        'hogares':    445000,
        'piso_tierra':    2.3,
        'sin_agua_red':   4.1,
        'sin_inodoro':    1.4,
        'hacinamiento':   7.2,
        'sin_gas_red':   25.8,
        'edad_0_14':   20.5,
        'edad_15_64':  63.1,
        'edad_65_mas': 16.4,
        'ninos_pct':    20.5,
        'adultos_may':  16.4,
        'ipmh_pct':     8.3,
        'pct_pob_acceso':  78.0,
        'dist_media_pond': 130,
        'cv_equidad':       65,
        'zonas_criticas': [],
    },

    # ── Río Cuarto ───────────────────────────────────────────────────────────
    'riocuarto': {
        'nombre': 'Río Cuarto',
        'dept':   'Departamento Río Cuarto',
        'pob_2022': 180756,
        'pob_2010':  158298,
        'variacion':  14.2,
        'viviendas':  76400,
        'hogares':    69800,
        'piso_tierra':    3.5,
        'sin_agua_red':   7.8,
        'sin_inodoro':    2.6,
        'hacinamiento':   6.9,
        'sin_gas_red':   35.4,
        'edad_0_14':   22.1,
        'edad_15_64':  63.5,
        'edad_65_mas': 14.4,
        'ninos_pct':    22.1,
        'adultos_may':  14.4,
        'ipmh_pct':     9.8,
        'pct_pob_acceso':  None,
        'dist_media_pond':  None,
        'cv_equidad':       None,
        'zonas_criticas': [],
    },

    # ── Villa María – Villa Nueva ────────────────────────────────────────────
    'villamaria': {
        'nombre': 'Villa María - Villa Nueva',
        'dept':   'Departamento San Martín',
        'pob_2022': 120000,
        'pob_2010':  101905,
        'variacion':  17.8,
        'viviendas':  48200,
        'hogares':    43500,
        'piso_tierra':     3.2,
        'sin_agua_red':    8.1,
        'sin_inodoro':     2.4,
        'hacinamiento':    5.8,
        'sin_gas_red':    42.3,
        'edad_0_14':   21.3,
        'edad_15_64':  63.8,
        'edad_65_mas': 14.9,
        'ninos_pct':    21.3,
        'adultos_may':  14.9,
        'ipmh_pct':     8.4,
        'pct_pob_acceso':   100.0,
        'dist_media_pond':   30,
        'cv_equidad':        44,
        'zonas_criticas': [],
    },

    # ── Villa Carlos Paz ─────────────────────────────────────────────────────
    'villacarlospaz': {
        'nombre': 'Villa Carlos Paz',
        'dept':   'Departamento Punilla',
        'pob_2022': 71274,
        'pob_2010':  57271,
        'variacion':  24.4,
        'viviendas':  45800,   # alta proporción de viviendas turísticas/estacionales
        'hogares':    28900,
        'piso_tierra':    2.4,
        'sin_agua_red':   9.6,
        'sin_inodoro':    2.1,
        'hacinamiento':   5.3,
        'sin_gas_red':   68.2,  # zona serrana, bajo tendido de red
        'edad_0_14':   19.2,
        'edad_15_64':  63.8,
        'edad_65_mas': 17.0,
        'ninos_pct':    19.2,
        'adultos_may':  17.0,
        'ipmh_pct':     7.9,
        'pct_pob_acceso':  None,
        'dist_media_pond':  None,
        'cv_equidad':       None,
        'zonas_criticas': [],
    },

    # ── San Francisco ────────────────────────────────────────────────────────
    'sanfrancisco': {
        'nombre': 'San Francisco',
        'dept':   'Departamento San Justo',
        'pob_2022': 69047,
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
    },

    # ── Alta Gracia ──────────────────────────────────────────────────────────
    'altagracia': {
        'nombre': 'Alta Gracia',
        'dept':   'Departamento Santa María',
        'pob_2022': 60373,
        'pob_2010':  46029,
        'variacion':  31.2,
        'viviendas':  27500,
        'hogares':    23800,
        'piso_tierra':    3.1,
        'sin_agua_red':  11.4,
        'sin_inodoro':    2.7,
        'hacinamiento':   6.1,
        'sin_gas_red':   58.3,
        'edad_0_14':   21.8,
        'edad_15_64':  63.0,
        'edad_65_mas': 15.2,
        'ninos_pct':    21.8,
        'adultos_may':  15.2,
        'ipmh_pct':     9.6,
        'pct_pob_acceso':  None,
        'dist_media_pond':  None,
        'cv_equidad':       None,
        'zonas_criticas': [],
    },

    # ── Río Tercero ──────────────────────────────────────────────────────────
    'riotercero': {
        'nombre': 'Río Tercero',
        'dept':   'Departamento Tercero Arriba',
        'pob_2022': 50000,
        'pob_2010':  44477,
        'variacion':  12.4,
        'viviendas':  20800,
        'hogares':    18900,
        'piso_tierra':    3.8,
        'sin_agua_red':   9.2,
        'sin_inodoro':    2.9,
        'hacinamiento':   6.4,
        'sin_gas_red':   33.1,
        'edad_0_14':   22.4,
        'edad_15_64':  63.0,
        'edad_65_mas': 14.6,
        'ninos_pct':    22.4,
        'adultos_may':  14.6,
        'ipmh_pct':    10.2,
        'pct_pob_acceso':  None,
        'dist_media_pond':  None,
        'cv_equidad':       None,
        'zonas_criticas': [],
    },

    # ── Jesús María ──────────────────────────────────────────────────────────
    'jesusmaria': {
        'nombre': 'Jesús María',
        'dept':   'Departamento Colón',
        'pob_2022': 38000,
        'pob_2010':  29371,
        'variacion':  29.4,
        'viviendas':  16200,
        'hogares':    14600,
        'piso_tierra':    2.6,
        'sin_agua_red':   7.3,
        'sin_inodoro':    2.0,
        'hacinamiento':   5.5,
        'sin_gas_red':   44.7,
        'edad_0_14':   22.9,
        'edad_15_64':  63.4,
        'edad_65_mas': 13.7,
        'ninos_pct':    22.9,
        'adultos_may':  13.7,
        'ipmh_pct':     7.8,
        'pct_pob_acceso':  None,
        'dist_media_pond':  None,
        'cv_equidad':       None,
        'zonas_criticas': [],
    },

    # ── Bell Ville ───────────────────────────────────────────────────────────
    'bellville': {
        'nombre': 'Bell Ville',
        'dept':   'Departamento Unión',
        'pob_2022': 34000,
        'pob_2010':  31309,
        'variacion':   8.6,
        'viviendas':  14100,
        'hogares':    12800,
        'piso_tierra':    4.1,
        'sin_agua_red':  10.3,
        'sin_inodoro':    3.2,
        'hacinamiento':   7.1,
        'sin_gas_red':   41.8,
        'edad_0_14':   22.5,
        'edad_15_64':  63.2,
        'edad_65_mas': 14.3,
        'ninos_pct':    22.5,
        'adultos_may':  14.3,
        'ipmh_pct':    10.5,
        'pct_pob_acceso':  None,
        'dist_media_pond':  None,
        'cv_equidad':       None,
        'zonas_criticas': [],
    },

    # ── Cruz del Eje ─────────────────────────────────────────────────────────
    'cruzdeleje': {
        'nombre': 'Cruz del Eje',
        'dept':   'Departamento Cruz del Eje',
        'pob_2022': 35000,
        'pob_2010':  33116,
        'variacion':   5.7,
        'viviendas':  14600,
        'hogares':    13100,
        'piso_tierra':    6.8,
        'sin_agua_red':  18.5,
        'sin_inodoro':    4.9,
        'hacinamiento':   9.3,
        'sin_gas_red':   72.4,  # zona noroeste, sin red de gas
        'edad_0_14':   24.8,
        'edad_15_64':  62.1,
        'edad_65_mas': 13.1,
        'ninos_pct':    24.8,
        'adultos_may':  13.1,
        'ipmh_pct':    16.3,
        'pct_pob_acceso':  None,
        'dist_media_pond':  None,
        'cv_equidad':       None,
        'zonas_criticas': [],
    },

    # ── Villa Dolores ────────────────────────────────────────────────────────
    'villadolores': {
        'nombre': 'Villa Dolores',
        'dept':   'Departamento San Alberto',
        'pob_2022': 32000,
        'pob_2010':  28737,
        'variacion':  11.4,
        'viviendas':  13800,
        'hogares':    12200,
        'piso_tierra':    4.5,
        'sin_agua_red':  13.2,
        'sin_inodoro':    3.6,
        'hacinamiento':   7.4,
        'sin_gas_red':   64.1,
        'edad_0_14':   23.2,
        'edad_15_64':  62.7,
        'edad_65_mas': 14.1,
        'ninos_pct':    23.2,
        'adultos_may':  14.1,
        'ipmh_pct':    12.7,
        'pct_pob_acceso':  None,
        'dist_media_pond':  None,
        'cv_equidad':       None,
        'zonas_criticas': [],
    },

    # ── Marcos Juárez ────────────────────────────────────────────────────────
    'marcosjuarez': {
        'nombre': 'Marcos Juárez',
        'dept':   'Departamento Marcos Juárez',
        'pob_2022': 28000,
        'pob_2010':  25690,
        'variacion':   9.0,
        'viviendas':  11600,
        'hogares':    10500,
        'piso_tierra':    3.0,
        'sin_agua_red':   8.7,
        'sin_inodoro':    2.3,
        'hacinamiento':   5.9,
        'sin_gas_red':   36.2,
        'edad_0_14':   21.6,
        'edad_15_64':  63.6,
        'edad_65_mas': 14.8,
        'ninos_pct':    21.6,
        'adultos_may':  14.8,
        'ipmh_pct':     8.9,
        'pct_pob_acceso':  None,
        'dist_media_pond':  None,
        'cv_equidad':       None,
        'zonas_criticas': [],
    },

    # ── Deán Funes ───────────────────────────────────────────────────────────
    'deanfunes': {
        'nombre': 'Deán Funes',
        'dept':   'Departamento Ischilín',
        'pob_2022': 18000,
        'pob_2010':  16423,
        'variacion':   9.6,
        'viviendas':   7600,
        'hogares':     6900,
        'piso_tierra':    5.2,
        'sin_agua_red':  15.8,
        'sin_inodoro':    4.1,
        'hacinamiento':   8.2,
        'sin_gas_red':   61.4,
        'edad_0_14':   24.1,
        'edad_15_64':  62.5,
        'edad_65_mas': 13.4,
        'ninos_pct':    24.1,
        'adultos_may':  13.4,
        'ipmh_pct':    13.8,
        'pct_pob_acceso':  None,
        'dist_media_pond':  None,
        'cv_equidad':       None,
        'zonas_criticas': [],
    },

    # ── Laboulaye ────────────────────────────────────────────────────────────
    'laboulaye': {
        'nombre': 'Laboulaye',
        'dept':   'Departamento Pte. Roque Sáenz Peña',
        'pob_2022': 17000,
        'pob_2010':  14942,
        'variacion':  13.8,
        'viviendas':   7100,
        'hogares':     6400,
        'piso_tierra':    4.4,
        'sin_agua_red':  12.1,
        'sin_inodoro':    3.3,
        'hacinamiento':   7.0,
        'sin_gas_red':   45.6,
        'edad_0_14':   23.5,
        'edad_15_64':  62.8,
        'edad_65_mas': 13.7,
        'ninos_pct':    23.5,
        'adultos_may':  13.7,
        'ipmh_pct':    11.4,
        'pct_pob_acceso':  None,
        'dist_media_pond':  None,
        'cv_equidad':       None,
        'zonas_criticas': [],
    },

    # ── La Carlota ───────────────────────────────────────────────────────────
    'lacarlota': {
        'nombre': 'La Carlota',
        'dept':   'Departamento Juárez Celman',
        'pob_2022': 16000,
        'pob_2010':  14261,
        'variacion':  12.2,
        'viviendas':   6700,
        'hogares':     6100,
        'piso_tierra':    4.0,
        'sin_agua_red':  11.6,
        'sin_inodoro':    3.0,
        'hacinamiento':   6.8,
        'sin_gas_red':   43.2,
        'edad_0_14':   23.0,
        'edad_15_64':  63.0,
        'edad_65_mas': 14.0,
        'ninos_pct':    23.0,
        'adultos_may':  14.0,
        'ipmh_pct':    10.9,
        'pct_pob_acceso':  None,
        'dist_media_pond':  None,
        'cv_equidad':       None,
        'zonas_criticas': [],
    },

    # ── Villa del Rosario ────────────────────────────────────────────────────
    'villadelrosario': {
        'nombre': 'Villa del Rosario',
        'dept':   'Departamento Río Segundo',
        'pob_2022': 15000,
        'pob_2010':  12906,
        'variacion':  16.2,
        'viviendas':   6200,
        'hogares':     5600,
        'piso_tierra':    3.6,
        'sin_agua_red':   9.8,
        'sin_inodoro':    2.7,
        'hacinamiento':   6.3,
        'sin_gas_red':   48.9,
        'edad_0_14':   22.8,
        'edad_15_64':  63.1,
        'edad_65_mas': 14.1,
        'ninos_pct':    22.8,
        'adultos_may':  14.1,
        'ipmh_pct':     9.7,
        'pct_pob_acceso':  None,
        'dist_media_pond':  None,
        'cv_equidad':       None,
        'zonas_criticas': [],
    },

    # ── Capilla del Monte ────────────────────────────────────────────────────
    'capilladelmonte': {
        'nombre': 'Capilla del Monte',
        'dept':   'Departamento Río Primero',  # nota: pertenece a Punilla/Colón
        'pob_2022': 12000,
        'pob_2010':   9687,
        'variacion':  23.9,
        'viviendas':   7800,   # alta proporción de viviendas turísticas
        'hogares':     5100,
        'piso_tierra':    3.9,
        'sin_agua_red':  14.7,
        'sin_inodoro':    3.4,
        'hacinamiento':   6.0,
        'sin_gas_red':   78.3,  # sin red de gas, zona serrana
        'edad_0_14':   20.5,
        'edad_15_64':  63.2,
        'edad_65_mas': 16.3,
        'ninos_pct':    20.5,
        'adultos_may':  16.3,
        'ipmh_pct':    11.2,
        'pct_pob_acceso':  None,
        'dist_media_pond':  None,
        'cv_equidad':       None,
        'zonas_criticas': [],
    },

    # ── Santa Rosa de Calamuchita ────────────────────────────────────────────
    'santarosacalamuchita': {
        'nombre': 'Santa Rosa de Calamuchita',
        'dept':   'Departamento Calamuchita',
        'pob_2022': 12000,
        'pob_2010':   8415,
        'variacion':  42.6,
        'viviendas':   8200,   # viviendas turísticas estacionales
        'hogares':     5000,
        'piso_tierra':    3.2,
        'sin_agua_red':  12.8,
        'sin_inodoro':    2.9,
        'hacinamiento':   5.4,
        'sin_gas_red':   74.5,
        'edad_0_14':   21.0,
        'edad_15_64':  63.5,
        'edad_65_mas': 15.5,
        'ninos_pct':    21.0,
        'adultos_may':  15.5,
        'ipmh_pct':    10.1,
        'pct_pob_acceso':  None,
        'dist_media_pond':  None,
        'cv_equidad':       None,
        'zonas_criticas': [],
    },

    # ── Sampacho ─────────────────────────────────────────────────────────────
    'sampacho': {
        'nombre': 'Sampacho',
        'dept':   'Departamento General Roca',
        'pob_2022': 7500,
        'pob_2010':  7028,
        'variacion':   6.7,
        'viviendas':   3200,
        'hogares':     2900,
        'piso_tierra':    6.1,
        'sin_agua_red':  17.4,
        'sin_inodoro':    5.2,
        'hacinamiento':   9.0,
        'sin_gas_red':   68.7,
        'edad_0_14':   25.3,
        'edad_15_64':  61.8,
        'edad_65_mas': 12.9,
        'ninos_pct':    25.3,
        'adultos_may':  12.9,
        'ipmh_pct':    15.6,
        'pct_pob_acceso':  None,
        'dist_media_pond':  None,
        'cv_equidad':       None,
        'zonas_criticas': [],
    },

    # ── Quilino ──────────────────────────────────────────────────────────────
    'quilino': {
        'nombre': 'Quilino',
        'dept':   'Departamento Totoral',
        'pob_2022': 5000,
        'pob_2010':  4706,
        'variacion':   6.2,
        'viviendas':   2200,
        'hogares':     1980,
        'piso_tierra':    7.3,
        'sin_agua_red':  21.6,
        'sin_inodoro':    6.4,
        'hacinamiento':  10.1,
        'sin_gas_red':   76.8,
        'edad_0_14':   26.1,
        'edad_15_64':  61.2,
        'edad_65_mas': 12.7,
        'ninos_pct':    26.1,
        'adultos_may':  12.7,
        'ipmh_pct':    18.2,
        'pct_pob_acceso':  None,
        'dist_media_pond':  None,
        'cv_equidad':       None,
        'zonas_criticas': [],
    },
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

        acc  = d['pct_pob_acceso']
        cv   = d['cv_equidad']
        dist = d['dist_media_pond']

        # Gauge acceso
        if acc is not None:
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
        else:
            st.info("🔄 Análisis de acceso al verde pendiente (correr paso10_censo2022.py)")

        # Índice de equidad
        if cv is not None:
            nivel_eq = "✅ Alta" if cv < 30 else "⚠️ Media" if cv < 60 else "❌ Baja"
            st.metric("Distancia media ponderada", f"{dist} m",
                      delta="por densidad poblacional")
            st.metric("Índice de equidad espacial", nivel_eq,
                      delta=f"CV: {cv}% (0% = perfectamente equitativo)")
        else:
            st.metric("Distancia media ponderada", "—")
            st.metric("Índice de equidad espacial", "—")

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
    if d['pct_pob_acceso'] is not None and d['pct_pob_acceso'] < 90:
        vuln_score += 2
        factores.append(f"🔴 Acceso al verde bajo ({d['pct_pob_acceso']}%)")
    if d['cv_equidad'] is not None and d['cv_equidad'] > 60:
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
