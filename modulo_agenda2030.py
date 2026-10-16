"""
modulo_agenda2030.py — Ciudad Verde AI Agent
============================================
Agenda 2030 · C40 · Villa María.

- calcular_agenda2030(): todos los números de la sección en un solo lugar.
  La usan esta sección, el Masterplan y el Benchmarking C40.
- render_agenda2030(): la pantalla.

Lee solo datos precalculados:
  data/indicadores_villamaria.json      (vía DATOS_VM de modulo_villamaria)
  data/censo_arboreo_villamaria.json    (copa Meta/WRI a 1 m)
  data/zonas_villamaria_resumen.json    (meta municipal 1 árbol por casa)

Uso:
    from modulo_agenda2030 import render_agenda2030, calcular_agenda2030
"""

import os
import json

import pandas as pd
import streamlit as st

RUTA_CENSO = os.path.join(os.path.dirname(__file__), 'data', 'censo_arboreo_villamaria.json')

# ============================================================
# CONSTANTES CON FUENTE
# ============================================================

# Clases de ESA WorldCover que el estudio de las 96 ciudades C40 cuenta como
# verde para la meta 1 (el agua queda afuera).
CLASES_VERDE_C40 = ['arboles', 'arbustos', 'pastizales', 'cultivos', 'humedal', 'manglar', 'musgo']

META_C40_VERDE_PCT = 30.0         # C40 Urban Nature Accelerator, meta 1 (30–40 %)
META_C40_ACCESO_PCT = 70.0        # C40 Urban Nature Accelerator, meta 2
META_COPA_3_30_300 = 30.0         # Konijnendijk (2021), regla 3-30-300

TASA_SECUESTRO_NETA = 0.205       # kg C/m² de copa/año — Nowak et al. (2013)
C_A_CO2 = 44 / 12                 # conversión de carbono a CO₂
CO2_AUTO_T = 4.6                  # t CO₂/año de un vehículo típico — EPA

LANCET_MEDIANA = 1.77             # muertes evitadas /100.000 hab por punto de verde — Martin et al. (2025)
LANCET_RANGO = (0.65, 3.52)
LANCET_FOCALIZADO = (1.4, 1.7)    # multiplicador si el verde se suma donde menos hay

ANIO_INICIO = 2026
ANIO_META = 2030

FUENTES = [
    ("C40 Urban Nature Accelerator", "https://www.c40.org/accelerators/urban-nature/"),
    ("Tracking Progress Toward Urban Nature Targets — 96 C40 cities (GeoHealth, 2024)",
     "https://pmc.ncbi.nlm.nih.gov/articles/PMC10897363"),
    ("Konijnendijk (2021) — La regla 3-30-300 (IUCN Urban Alliance)",
     "https://iucnurbanalliance.org/promoting-health-and-wellbeing-through-urban-forests-introducing-the-3-30-300-rule/"),
    ("Nowak et al. (2013) — Carbon storage and sequestration by trees in urban and community areas",
     "https://research.fs.usda.gov/treesearch/46254"),
    ("EPA — Greenhouse Gas Emissions from a Typical Passenger Vehicle",
     "https://www.epa.gov/greenvehicles/greenhouse-gas-emissions-typical-passenger-vehicle"),
    ("Martin et al. (2025) — Health impact assessment of urban nature targets in the 96 C40 cities, "
     "Lancet Planetary Health 9(4)", "https://hsrc.himmelfarb.gwu.edu/gwhpubs/7114"),
    ("Barboza et al. (2021) — Green space and mortality in European cities (ISGlobal)",
     "https://www.isglobal.org/en/-/isglobal-presenta-el-ranking-de-las-ciudades-europeas-con-mayor-mortalidad-atribuible-a-la-falta-de-espacios-verdes"),
]


# ============================================================
# CARGA Y CÁLCULO
# ============================================================

@st.cache_data(show_spinner=False)
def _cargar_censo():
    if not os.path.exists(RUTA_CENSO):
        return None
    with open(RUTA_CENSO, encoding='utf-8') as f:
        return json.load(f)


def _co2_t(area_copa_m2):
    """t CO₂/año capturadas por una superficie de copa (Nowak 2013, tasa neta)."""
    return area_copa_m2 * TASA_SECUESTRO_NETA / 1000 * C_A_CO2


def calcular_agenda2030():
    """Devuelve todos los indicadores de la sección como diccionario,
    o None si faltan los datos precalculados."""
    from modulo_villamaria import DATOS_VM
    from modulo_barrios import _cargar_resumen

    censo = _cargar_censo()
    if DATOS_VM.get('datos_preliminares') or not censo or not DATOS_VM.get('area_vm_km2'):
        return None

    cob = DATOS_VM['cobertura']
    acc = DATOS_VM['acceso']
    lst = DATOS_VM['lst']
    poblacion = DATOS_VM.get('poblacion_vm', 96061)
    area_ha = DATOS_VM['area_vm_km2'] * 100

    # --- Meta 1 C40 (definición del estudio de las 96 ciudades) ---
    qtc = sum(cob.get(k) or 0 for k in CLASES_VERDE_C40)
    qtc_sin_cultivos = qtc - (cob.get('cultivos') or 0)

    # --- Copa arbórea (Meta/WRI, 1 m) ---
    copa_ha = censo['ciudad_area_copa_ha']
    total_arboles = censo['total_arboles']
    area_barrios_ha = sum(b['area_barrio_ha'] for b in censo['barrios'] if b.get('area_barrio_ha'))
    copa_pct = copa_ha / area_barrios_ha * 100 if area_barrios_ha else 0
    copa_media_m2 = copa_ha * 10_000 / total_arboles if total_arboles else 0

    barrios = []
    for b in censo['barrios']:
        if not b.get('area_barrio_ha'):
            continue
        falta_ha = max(0, META_COPA_3_30_300 / 100 * b['area_barrio_ha'] - b['area_copa_ha'])
        barrios.append({
            'barrio': b['nombre'].title(),
            'area_ha': b['area_barrio_ha'],
            'copa_ha': b['area_copa_ha'],
            'copa_pct': b['area_copa_ha'] / b['area_barrio_ha'] * 100,
            'falta_ha': falta_ha,
            'arboles_30': falta_ha * 10_000 / copa_media_m2 if copa_media_m2 else 0,
        })
    barrios.sort(key=lambda x: x['copa_pct'])
    falta_30_ha = sum(b['falta_ha'] for b in barrios)

    # --- CO₂ ---
    copa_wc_ha = area_ha * (cob.get('arboles') or 0) / 100
    co2_meta = _co2_t(copa_ha * 10_000)
    co2_wc = _co2_t(copa_wc_ha * 10_000)

    # --- Salud (Martin et al. 2025) ---
    factor_pob = poblacion / 100_000

    # --- Meta municipal 1 árbol por casa ---
    res = _cargar_resumen()
    meta_m = res['ciudad']['meta_1_arbol_por_casa'] if res else None
    anios = ANIO_META - ANIO_INICIO

    return {
        'area_ha': area_ha,
        'poblacion': poblacion,
        'qtc': qtc,
        'qtc_sin_cultivos': qtc_sin_cultivos,
        'meta1_cumplida': qtc >= META_C40_VERDE_PCT,
        'acceso_aprox': acc.get('acceso') or 0,
        'meta2_cumplida_aprox': (acc.get('acceso') or 0) >= META_C40_ACCESO_PCT,
        'copa_ha': copa_ha,
        'copa_pct': copa_pct,
        'copa_media_m2': copa_media_m2,
        'total_arboles': total_arboles,
        'barrios_copa': barrios,
        'barrios_30': sum(1 for b in barrios if b['copa_pct'] >= META_COPA_3_30_300),
        'falta_30_ha': falta_30_ha,
        'arboles_30': falta_30_ha * 10_000 / copa_media_m2 if copa_media_m2 else 0,
        'copa_wc_ha': copa_wc_ha,
        'arbolado_wc_pct': cob.get('arboles') or 0,
        'co2_meta_t': co2_meta,
        'co2_wc_t': co2_wc,
        'autos_meta': co2_meta / CO2_AUTO_T,
        'autos_wc': co2_wc / CO2_AUTO_T,
        'muertes_punto': LANCET_MEDIANA * factor_pob,
        'muertes_punto_bajo': LANCET_RANGO[0] * factor_pob,
        'muertes_punto_alto': LANCET_RANGO[1] * factor_pob,
        'enfriamiento': lst.get('enfriamiento') or 0,
        'anios': anios,
        'meta_municipal': meta_m,
        'arboles_por_anio_municipal': (meta_m['deficit_arboles'] / anios) if (meta_m and anios) else None,
    }


# ============================================================
# HELPERS VISUALES
# ============================================================

def _num(n):
    return f"{int(round(n)):,}".replace(",", ".")


def _dec(x, d=1):
    return f"{x:.{d}f}".replace(".", ",")


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


def _tarjeta_meta(titulo, valor_txt, subtitulo, avance_pct, meta_txt, estado_txt, color):
    st.markdown(
        f"""<div style='border:2.5px solid {color};border-radius:14px;padding:22px;text-align:center;background:{color}0d'>
          <div style='font-size:0.88em;color:#fff;font-weight:600;margin-bottom:4px'>{titulo}</div>
          <div style='font-size:2.6em;font-weight:800;color:{color}'>{valor_txt}</div>
          <div style='font-size:0.9em;color:#ddd'>{subtitulo}</div>
          <div style='margin:10px 0'>
            <div style='background:rgba(255,255,255,0.15);border-radius:8px;height:12px;overflow:hidden'>
              <div style='background:{color};width:{min(avance_pct, 100):.0f}%;height:100%;border-radius:8px'></div>
            </div>
            <div style='font-size:0.84em;color:#ccc;margin-top:4px'>{meta_txt}</div>
          </div>
          <div style='font-size:0.88em;color:{color};font-weight:600'>{estado_txt}</div>
        </div>""",
        unsafe_allow_html=True,
    )


# ============================================================
# BLOQUES DE PANTALLA
# ============================================================

def _render_metas_c40(a):
    st.markdown("## 🎯 Metas C40 a 2030")
    c1, c2 = st.columns(2)
    with c1:
        color = "#2e7d32" if a['meta1_cumplida'] else "#f57c00"
        _tarjeta_meta(
            "META 1 · Cobertura verde", f"{_dec(a['qtc'])} %", "de la superficie de los 38 barrios es verde",
            a['qtc'] / META_C40_VERDE_PCT * 100,
            f"{_dec(a['qtc'])} % de {_dec(META_C40_VERDE_PCT, 0)} % (meta C40: 30 %–40 %)",
            "✅ META CUMPLIDA" if a['meta1_cumplida']
            else f"⚠️ Faltan {_dec(META_C40_VERDE_PCT - a['qtc'])} puntos", color,
        )
    with c2:
        color = "#2e7d32" if a['meta2_cumplida_aprox'] else "#f57c00"
        _tarjeta_meta(
            "META 2 · Acceso equitativo (aproximación)", f"{_dec(a['acceso_aprox'], 0)} %",
            "del área edificada a menos de 300 m de verde",
            a['acceso_aprox'] / META_C40_ACCESO_PCT * 100,
            f"{_dec(a['acceso_aprox'], 0)} % frente a {_dec(META_C40_ACCESO_PCT, 0)} % de la meta C40",
            "✅ Cumplida según la aproximación" if a['meta2_cumplida_aprox']
            else "⚠️ No cumplida según la aproximación", color,
        )
    st.caption(
        f"**Meta 1:** suma de árboles, arbustos, pastizales y cultivos de ESA WorldCover 2020 (definición del "
        f"estudio de las 96 ciudades C40; el agua queda afuera) sobre los {_dec(a['area_ha'] / 100)} km² de los "
        f"38 barrios. Sin contar cultivos sería {_dec(a['qtc_sin_cultivos'])} %: la meta se cumple en buena parte "
        f"por el verde agrícola periurbano. **Meta 2:** C40 pide que el 70 % de la población tenga un espacio "
        f"verde o azul público a 15 minutos caminando (~1.000 m, espacios de 0,5 ha o más). El valor mostrado es "
        f"una aproximación: área edificada a menos de 300 m de cualquier verde satelital, incluidos espacios "
        f"privados. El cálculo con la definición C40 está pendiente."
    )


def _render_3_30_300(a):
    st.markdown("## 🌳 Regla 3-30-300")
    st.markdown(
        "Estándar de arbolado urbano propuesto por Konijnendijk (2021): **3** árboles visibles desde cada "
        "casa, **30 %** de copa arbórea en cada barrio y **300 m** hasta un espacio verde de al menos 1 ha."
    )
    c1, c2, c3 = st.columns(3)
    with c1:
        _card("30 · Copa de la ciudad", f"{_dec(a['copa_pct'])} %",
              f"{_dec(a['copa_ha'])} ha de copa · meta 30 %", "#c62828" if a['copa_pct'] < 15 else "#f57c00")
    with c2:
        _card("Barrios que llegan al 30 %", f"{a['barrios_30']} de {len(a['barrios_copa'])}",
              "copa Meta/WRI a 1 m de resolución", "#c62828" if a['barrios_30'] == 0 else "#f57c00")
    with c3:
        _card("Para llevar cada barrio al 30 %", f"{_num(a['falta_30_ha'])} ha de copa",
              f"≈ {_num(a['arboles_30'])} árboles adultos", "#1e88e5")

    filas = [{
        'Barrio': b['barrio'],
        'Superficie (ha)': round(b['area_ha'], 1),
        'Copa (ha)': round(b['copa_ha'], 1),
        'Copa (%)': round(b['copa_pct'], 1),
        'Copa faltante para 30 % (ha)': round(b['falta_ha'], 1),
        'Árboles adultos necesarios': int(round(b['arboles_30'])),
    } for b in a['barrios_copa']]
    st.dataframe(pd.DataFrame(filas), hide_index=True, use_container_width=True, height=380)
    st.caption(
        f"**30:** copa = superficie con árboles de 2 m o más (Meta/WRI Canopy Height, imagen 2018) sobre la "
        f"superficie total de cada barrio. Los árboles necesarios suponen que cada árbol nuevo llega a la copa "
        f"media medida en la ciudad ({_dec(a['copa_media_m2'])} m² = {_dec(a['copa_ha'])} ha ÷ "
        f"{_num(a['total_arboles'])} árboles) *(supuesto)*. **300:** pendiente, se calcula junto con la meta 2 "
        f"de C40. **3:** no se puede medir con imágenes satelitales."
    )


def _render_co2(a):
    st.markdown("## 🌿 Captura de CO₂ del arbolado")
    st.markdown(
        f"Nowak et al. (2013), con datos de campo de ciudades de EE.UU., estiman una captura **neta** de "
        f"**{_dec(TASA_SECUESTRO_NETA, 3)} kg de carbono por m² de copa por año** (descontada la "
        f"mortalidad de árboles). Se aplica a la copa medida con dos fuentes."
    )
    c1, c2 = st.columns(2)
    with c1:
        _card("Copa Meta/WRI · 1 m (principal)", f"{_num(a['co2_meta_t'])} t CO₂/año",
              f"{_dec(a['copa_ha'])} ha de copa · equivale a {_num(a['autos_meta'])} autos por año", "#2e7d32")
    with c2:
        _card("ESA WorldCover · 10 m", f"{_num(a['co2_wc_t'])} t CO₂/año",
              f"{_dec(a['copa_wc_ha'])} ha ({_dec(a['arbolado_wc_pct'])} %) · equivale a "
              f"{_num(a['autos_wc'])} autos por año", "#1e88e5")
    st.caption(
        "La diferencia entre fuentes se debe a la resolución: a 10 m se pierden árboles aislados de vereda. "
        f"Equivalencia en autos: {_dec(CO2_AUTO_T)} t CO₂ por vehículo típico por año (EPA)."
    )

    st.markdown("### 🧮 ¿Cuánto CO₂ capturaría la ciudad con más copa?")
    col_sl, col_res = st.columns([1, 2])
    with col_sl:
        objetivo = st.slider(
            "Copa objetivo (%)", min_value=int(a['copa_pct']) + 1, max_value=40,
            value=int(META_COPA_3_30_300), step=1, key="ag_copa_objetivo",
            help="30 % es la meta de la regla 3-30-300",
        )
    copa_obj_ha = a['area_ha'] * objetivo / 100
    co2_obj = _co2_t(copa_obj_ha * 10_000)
    arboles_obj = max(0, copa_obj_ha - a['copa_ha']) * 10_000 / a['copa_media_m2'] if a['copa_media_m2'] else 0
    with col_res:
        st.markdown(
            f"""<div style='background:rgba(46,125,50,0.12);border:1.5px solid #81c784;border-radius:12px;padding:20px'>
              <div style='font-size:1em;font-weight:700;color:#81c784;margin-bottom:12px'>
                🌿 Con {objetivo} % de copa en la ciudad:</div>
              <table style='width:100%;font-size:0.88em;border-collapse:collapse'>
                <tr><td style='padding:4px 0;color:#ccc'>Superficie de copa</td>
                    <td style='font-weight:700;color:#66bb6a;text-align:right'>{_num(copa_obj_ha)} ha</td></tr>
                <tr><td style='padding:4px 0;color:#ccc'>CO₂ capturado por año</td>
                    <td style='font-weight:700;color:#66bb6a;text-align:right'>{_num(co2_obj)} t</td></tr>
                <tr><td style='padding:4px 0;color:#ccc'>Incremento frente a hoy</td>
                    <td style='font-weight:700;color:#64b5f6;text-align:right'>+{_num(co2_obj - a['co2_meta_t'])} t/año</td></tr>
                <tr><td style='padding:4px 0;color:#ccc'>Árboles adultos necesarios</td>
                    <td style='font-weight:700;color:#66bb6a;text-align:right'>≈ {_num(arboles_obj)}</td></tr>
              </table>
            </div>""",
            unsafe_allow_html=True,
        )
    st.caption("Los árboles plantados alcanzan su copa adulta en 15 a 20 años; la captura crece en ese plazo.")


def _render_salud(a):
    st.markdown("## ❤️ Impacto en salud pública")
    st.markdown(
        f"Martin et al. (2025), en *The Lancet Planetary Health*, estimaron para las 96 ciudades C40 que cada "
        f"punto porcentual de verde adicional evita una mediana de **{_dec(LANCET_MEDIANA, 2)} muertes "
        f"prematuras por año cada 100.000 habitantes** (rango {_dec(LANCET_RANGO[0], 2)}–"
        f"{_dec(LANCET_RANGO[1], 2)} según la ciudad), si el verde se suma de forma pareja. Si se suma donde "
        f"menos hay, el beneficio es entre {_dec(LANCET_FOCALIZADO[0])} y {_dec(LANCET_FOCALIZADO[1])} veces mayor."
    )
    c1, c2 = st.columns(2)
    with c1:
        _card("Muertes evitadas por cada punto de verde", f"{_dec(a['muertes_punto'])} por año",
              f"Rango {_dec(a['muertes_punto_bajo'])}–{_dec(a['muertes_punto_alto'])} · "
              f"{_num(a['poblacion'])} habitantes (INDEC 2022)", "#c62828")
    with c2:
        _card("Con verde focalizado en los barrios con menos",
              f"{_dec(a['muertes_punto'] * LANCET_FOCALIZADO[0])}–{_dec(a['muertes_punto'] * LANCET_FOCALIZADO[1])} por año",
              "por cada punto de verde, según el mismo estudio", "#6a1b9a")
    st.markdown(
        """<div style='background:rgba(233,30,99,0.12);border:1.5px solid #e91e63;border-radius:10px;padding:16px;font-size:0.9em'>
          <b>📖 Referencia:</b> Barboza et al. (2021) estimaron que <b>42.968 muertes anuales</b> podrían
          evitarse en 978 ciudades europeas si se cumpliera la recomendación de la OMS de acceso al verde.
          Según la aproximación de acceso de esta app, Villa María tiene verde cerca del área edificada; lo
          pendiente es <b>más copa arbórea en cada barrio</b>, que aporta sombra, enfriamiento y calidad del aire.
        </div>""",
        unsafe_allow_html=True,
    )
    st.caption("Las estimaciones son lineales y se aplican a la población de Villa María como referencia.")


def _render_hoja_ruta(a):
    st.markdown(f"## 🗓️ Hoja de ruta {ANIO_INICIO}–{ANIO_META}")
    m = a['meta_municipal']
    filas = []
    if m:
        filas.append({
            'Meta': 'Municipal: 1 árbol por casa',
            'Hoy': f"{_dec(m['cumplimiento_pct'])} %",
            f'Meta {ANIO_META}': '100 %',
            'Brecha': f"{_num(m['deficit_arboles'])} árboles",
            'Por año': f"{_num(a['arboles_por_anio_municipal'])} árboles",
        })
    filas.append({
        'Meta': 'Regla 3-30-300: 30 % de copa por barrio',
        'Hoy': f"{_dec(a['copa_pct'])} %",
        f'Meta {ANIO_META}': '30 % en cada barrio',
        'Brecha': f"≈ {_num(a['arboles_30'])} árboles adultos",
        'Por año': f"≈ {_num(a['arboles_30'] / a['anios'])} árboles" if a['anios'] else "—",
    })
    filas.append({
        'Meta': 'C40 meta 1: 30 % de cobertura verde',
        'Hoy': f"{_dec(a['qtc'])} %",
        f'Meta {ANIO_META}': '30 %–40 %',
        'Brecha': 'Cumplida: mantener' if a['meta1_cumplida'] else f"{_dec(META_C40_VERDE_PCT - a['qtc'])} puntos",
        'Por año': '—',
    })
    filas.append({
        'Meta': 'C40 meta 2: 70 % con acceso (aproximación)',
        'Hoy': f"{_dec(a['acceso_aprox'], 0)} %",
        f'Meta {ANIO_META}': '70 %',
        'Brecha': 'Cumplida según la aproximación' if a['meta2_cumplida_aprox'] else 'Pendiente',
        'Por año': '—',
    })
    st.dataframe(pd.DataFrame(filas), hide_index=True, use_container_width=True)
    if m:
        st.success(
            f"🎯 **Síntesis para política pública:** Villa María cumple la meta de cobertura verde de C40, pero "
            f"tiene {_dec(a['copa_pct'])} % de copa arbórea y ningún barrio llega al 30 % de la regla 3-30-300. "
            f"Para la meta municipal de 1 árbol por casa faltan {_num(m['deficit_arboles'])} árboles: unos "
            f"**{_num(a['arboles_por_anio_municipal'])} por año** durante {a['anios']} años "
            f"({ANIO_INICIO}–{ANIO_META}), priorizando los barrios con menos arbolado."
        )


def _render_marco(a):
    st.markdown("## 📋 Marco normativo y estándares de referencia")
    marcos = [
        ("🌍", "Agenda 2030 — ODS 11",
         "Meta 11.7: acceso universal a espacios verdes seguros e inclusivos. Según la aproximación de esta "
         "app, el área edificada de Villa María tiene verde a menos de 300 m."),
        ("🏙️", "C40 Urban Nature Accelerator",
         "Lanzado en 2021 con 31 ciudades; hoy 41 firmantes, entre ellas Buenos Aires. Metas a 2030: 30 %–40 % "
         "de superficie verde o permeable y 70 % de la población a 15 minutos de un espacio verde o azul."),
        ("🌳", "Regla 3-30-300 (Konijnendijk, 2021)",
         "3 árboles visibles desde cada casa, 30 % de copa en cada barrio y 300 m hasta un espacio verde de "
         f"al menos 1 ha. Villa María: {_dec(a['copa_pct'])} % de copa."),
        ("🌡️", "Acuerdo de París — NDC Argentina",
         f"El arbolado urbano es un sumidero de carbono cuantificable: ≈ {_num(a['co2_meta_t'])} t CO₂ por "
         "año en Villa María (Meta/WRI)."),
        ("🇪🇺", "EU Nature Restoration Law — Art. 8",
         "Referencia europea que pide no perder superficie verde ni copa arbórea urbana y aumentarlas "
         "después de 2030."),
        ("🏥", "OMS — Espacios verdes urbanos",
         f"Mínimo de 9 m² de verde público por habitante. Villa María: "
         f"{_dec(a.get('m2_osm') or 0)} m²/hab (OpenStreetMap)." if a.get('m2_osm') else
         "Mínimo de 9 m² de verde público por habitante y acceso a verde a menos de 300 m."),
        ("🌿", "Ordenanza 7209 — Ruralidad Urbana (2017)",
         "Marco local que reconoce los servicios ambientales del periurbano y regula el territorio "
         "rural-urbano de Villa María."),
    ]
    for icono, titulo, descripcion in marcos:
        st.markdown(
            f"""<div style='display:flex;gap:14px;align-items:flex-start;
                padding:12px 16px;border-radius:10px;background:rgba(255,255,255,0.05);
                border:1px solid rgba(255,255,255,0.12);margin-bottom:8px'>
              <div style='font-size:1.6em;line-height:1'>{icono}</div>
              <div>
                <div style='font-weight:700;font-size:0.92em;color:#81c784'>{titulo}</div>
                <div style='font-size:0.83em;color:#ccc;margin-top:3px'>{descripcion}</div>
              </div>
            </div>""",
            unsafe_allow_html=True,
        )


def _render_fuentes():
    with st.expander("📚 Fuentes", expanded=False):
        for titulo, url in FUENTES:
            st.markdown(f"- [{titulo}]({url})")


# ============================================================
# RENDER
# ============================================================

def render_agenda2030():
    """Punto de entrada. Llamar desde render_modulo_villamaria()."""
    from modulo_villamaria import DATOS_VM

    st.title("🌍 Agenda 2030 · Estándares C40")
    st.caption("Villa María medida con los estándares internacionales de naturaleza urbana")
    st.markdown("---")

    a = calcular_agenda2030()
    if not a:
        st.warning(
            "Faltan datos precalculados (`data/indicadores_villamaria.json` o "
            "`data/censo_arboreo_villamaria.json`). Esta sección no se muestra sin datos reales."
        )
        return
    a['m2_osm'] = DATOS_VM['osm'].get('m2Hab')

    _render_metas_c40(a)
    st.markdown("---")
    _render_3_30_300(a)
    st.markdown("---")
    _render_co2(a)
    st.markdown("---")
    _render_salud(a)
    st.markdown("---")
    _render_hoja_ruta(a)
    st.markdown("---")
    _render_marco(a)
    _render_fuentes()
    st.markdown("---")
    st.caption(
        "Ciudad Verde AI Agent · Agenda 2030 · Villa María · Datos: ESA WorldCover 2020 · "
        "Meta/WRI Canopy Height · Landsat 8/9 · OpenStreetMap · INDEC Censo 2022 · Diagnóstico por barrio"
    )
