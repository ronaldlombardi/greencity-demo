"""
modulo_masterplan.py — Ciudad Verde AI Agent
=============================================
Masterplan ambiental para Villa María.
- Admin: puede generar con Claude Opus 5.5 y ver historial.
- Usuario: solo puede ver y cargar masterplans guardados.
- El contexto que recibe el modelo se arma en el momento con los datos de la app:
  indicadores, Agenda 2030 / C40, meta municipal 1 árbol por casa,
  Decisiones para Villa María en línea con C40 y huella de eventos.
Registra consumo en PostgreSQL.
"""

import os
import datetime
import requests
import streamlit as st
from modulo_db import registrar_consumo, guardar_masterplan, obtener_masteplans, eliminar_masterplan

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
API_URL           = "https://api.anthropic.com/v1/messages"
MODEL_ID          = "claude-opus-5-5"
MODEL_NOMBRE      = "Claude Opus 5.5"
TIPO_CONSUMO      = "opus55"          # clave de COSTOS en modulo_db.py
PRECIO_INPUT      = 4.00              # USD por millón de tokens — verificar en la facturación
PRECIO_OUTPUT     = 20.00
MAX_TOKENS        = 8000
TIMEOUT_S         = 180

FUENTES_DATOS = ("ESA WorldCover 2020 · Copa Meta/WRI 1 m · Landsat 8/9 · OSM · "
                 "INDEC 2022 · Zonas por barrio (municipio)")

# ── Municipios soportados ─────────────────────────────────
MUNICIPIOS = {
    'villamaria': {
        'nombre':  'Villa María',
        'archivo': 'villa_maria',
        'genera':  True,
    },
    'villanueva': {
        'nombre':  'Villa Nueva',
        'archivo': 'villa_nueva',
        'genera':  False,   # solo historial: no tiene datos auditados para el contexto
    },
}


# ============================================================
# CONTEXTO DINÁMICO — todos los números salen de la app
# ============================================================

def _num(n):
    return f"{int(round(n)):,}".replace(",", ".")


def _dec(x, d=1):
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _texto_seguro(funcion, *args):
    """Llama a una función que lee Postgres; si falla, devuelve texto vacío."""
    try:
        return funcion(*args) or ""
    except Exception as e:
        print(f"[masterplan] Error armando contexto ({funcion.__name__}): {e}")
        return ""


def _contexto_vm():
    """Arma el bloque de datos para el prompt. Devuelve (texto, a) o (None, None)
    si faltan los datos precalculados."""
    from modulo_villamaria import DATOS_VM
    from modulo_agenda2030 import (calcular_agenda2030, TASA_SECUESTRO_NETA, C_A_CO2,
                                   LANCET_FOCALIZADO, ANIO_INICIO, ANIO_META)
    from modulo_barrios import _cargar_resumen
    from modulo_benchmarking import texto_decisiones_para_prompt
    from modulo_huella_eventos import texto_eventos_para_prompt, HUELLA_HAB_TOTAL_T, PARTE_AGRO

    a = calcular_agenda2030()
    if not a:
        return None, None

    cob = DATOS_VM['cobertura']
    acc = DATOS_VM['acceso']
    lst = DATOS_VM['lst']
    osm = DATOS_VM['osm']
    m = a['meta_municipal']
    res = _cargar_resumen()

    # Barrios con menos copa (regla 3-30-300)
    menos_copa = "; ".join(
        f"{b['barrio']} {_dec(b['copa_pct'])} %" for b in a['barrios_copa'][:5]
    )
    # Barrios con mayor déficit de la meta municipal
    mayor_deficit = ""
    if res and res.get('barrios'):
        ordenados = sorted(
            (b for b in res['barrios'] if b.get('meta_1_arbol_por_casa')),
            key=lambda b: b['meta_1_arbol_por_casa']['deficit_arboles'], reverse=True,
        )[:5]
        mayor_deficit = "; ".join(
            f"{b['barrio'].title()} faltan {_num(b['meta_1_arbol_por_casa']['deficit_arboles'])} "
            f"({_dec(b['meta_1_arbol_por_casa']['cumplimiento_pct'])} % cumplido)"
            for b in ordenados
        )

    # Escenario 30 % de copa en toda la ciudad
    copa_30_m2 = a['area_ha'] * 0.30 * 10_000
    co2_30 = copa_30_m2 * TASA_SECUESTRO_NETA / 1000 * C_A_CO2

    # Huella anual de la ciudad (promedio nacional, supuesto)
    huella_total = HUELLA_HAB_TOTAL_T * a['poblacion']
    huella_urbana = huella_total * (1 - PARTE_AGRO)

    decisiones = _texto_seguro(texto_decisiones_para_prompt, "Villa María")
    if not decisiones:
        decisiones = ("DECISIONES DEL MUNICIPIO EN LÍNEA CON C40: el administrador todavía no "
                      "cargó decisiones. Indicalo en el documento y proponé prioridades "
                      "a partir de las brechas medidas.")
    eventos = _texto_seguro(texto_eventos_para_prompt, "Villa María", None)
    if not eventos:
        eventos = "HUELLA DE CARBONO DE EVENTOS: no hay eventos registrados todavía."

    lineas = [
        "DATOS DE LA PLATAFORMA CIUDAD VERDE — VILLA MARÍA (Córdoba, Argentina)",
        "=" * 70,
        "",
        "DATOS GENERALES:",
        f"- Población: {_num(a['poblacion'])} habitantes (INDEC, Censo 2022)",
        f"- Área analizada: {_dec(a['area_ha'] / 100)} km² ({_num(a['area_ha'])} ha), "
        f"{res['ciudad']['n_barrios'] if res else 38} barrios oficiales",
        "- Villa Nueva está en la margen opuesta del Río Ctalamochita y NO está incluida en estos datos.",
        "",
        "COBERTURA DEL SUELO (ESA WorldCover 2020, 10 m):",
        f"- Árboles {_dec(cob.get('arboles') or 0)} % · Arbustos {_dec(cob.get('arbustos') or 0)} % · "
        f"Pastizales {_dec(cob.get('pastizales') or 0)} % · Cultivos {_dec(cob.get('cultivos') or 0)} % · "
        f"Edificado {_dec(cob.get('edificado') or 0)} % · Suelo desnudo {_dec(cob.get('suelo') or 0)} % · "
        f"Agua {_dec(cob.get('agua') or 0)} %",
        "",
        "COPA ARBÓREA (Meta/WRI, 1 m; imagen 2018):",
        f"- Árboles contados: {_num(a['total_arboles'])}",
        f"- Superficie de copa: {_dec(a['copa_ha'])} ha = {_dec(a['copa_pct'])} % del área de los barrios",
        f"- Copa media por árbol: {_dec(a['copa_media_m2'])} m²",
        f"- Barrios con 30 % de copa o más: {a['barrios_30']} de {len(a['barrios_copa'])}",
        f"- Barrios con menos copa: {menos_copa}",
        "",
        "ACCESO A ESPACIOS VERDES:",
        f"- Área edificada con verde a menos de 300 m: {_dec(acc.get('acceso') or 0, 0)} % "
        f"(distancia promedio {_num(acc.get('dist_prom') or 0)} m)",
        f"- Verde satelital por habitante: {_dec(acc.get('m2_hab_sat') or 0)} m²/hab",
        f"- Verde público catalogado en OpenStreetMap: {_dec(osm.get('m2Hab') or 0)} m²/hab "
        f"({_num(osm.get('elementos') or 0)} espacios, {_dec(osm.get('areaHa') or 0)} ha)",
        "",
        f"TEMPERATURA SUPERFICIAL (Landsat 8/9, {lst.get('nImagenes') or '—'} imágenes de verano):",
        f"- Temperatura media: {_dec(lst.get('tMedia') or 0)} °C · Isla de calor ΔT: "
        f"+{_dec(lst.get('deltaUHI') or 0)} °C",
        f"- Diferencia entre zonas con vegetación densa y sin vegetación: {_dec(a['enfriamiento'])} °C",
        "",
        "C40 URBAN NATURE ACCELERATOR (metas a 2030):",
        f"- Meta 1 (30–40 % de superficie verde o permeable): {_dec(a['qtc'])} % → "
        f"{'CUMPLIDA' if a['meta1_cumplida'] else 'NO cumplida'}. "
        f"Sin contar cultivos sería {_dec(a['qtc_sin_cultivos'])} %: si los cultivos se urbanizan, la meta se pierde.",
        f"- Meta 2 (70 % de la población a 15 minutos de verde): aproximación de la app "
        f"{_dec(a['acceso_aprox'], 0)} % (proxy: verde a menos de 300 m del área edificada; "
        f"no es el cálculo oficial de C40).",
        "",
        "REGLA 3-30-300 (Konijnendijk, 2021):",
        f"- Copa actual {_dec(a['copa_pct'])} % frente a la meta de 30 % por barrio",
        f"- Para llevar cada barrio al 30 % faltan {_num(a['falta_30_ha'])} ha de copa ≈ "
        f"{_num(a['arboles_30'])} árboles adultos",
        "",
    ]
    if m:
        lineas += [
            "META MUNICIPAL: 1 ÁRBOL POR CASA (zonas con casas: céntrica, residencial, mixta y ribereña):",
            f"- Lotes estimados: {_num(m['lotes_estimados'])} · árboles en esas zonas: "
            f"{_num(m['arboles_zonas_casas'])}",
            f"- Cumplimiento: {_dec(m['cumplimiento_pct'])} % · déficit: {_num(m['deficit_arboles'])} árboles",
            f"- Ritmo para cumplir en {ANIO_INICIO}–{ANIO_META}: {_num(a['arboles_por_anio_municipal'])} árboles por año",
            f"- Barrios con mayor déficit: {mayor_deficit}" if mayor_deficit else "",
            "",
        ]
    lineas += [
        "CAPTURA DE CO₂ DEL ARBOLADO (Nowak et al. 2013, 0,205 kg C/m² de copa/año, neta):",
        f"- Hoy: {_num(a['co2_meta_t'])} t CO₂/año (equivale a {_num(a['autos_meta'])} autos por año, EPA 4,6 t/auto)",
        f"- Con 30 % de copa en la ciudad: {_num(co2_30)} t CO₂/año",
        f"- Huella anual estimada de la ciudad (promedio nacional INDEC 2022 por habitante, supuesto): "
        f"≈ {_num(huella_total)} t CO₂e en total y ≈ {_num(huella_urbana)} t sin el sector agropecuario. "
        f"El arbolado actual absorbe ≈ {_dec(a['co2_meta_t'] / huella_urbana * 100, 2)} % de la huella urbana.",
        "",
        "SALUD PÚBLICA (Martin et al. 2025, The Lancet Planetary Health, 96 ciudades C40):",
        f"- Cada punto porcentual de verde adicional evitaría ≈ {_dec(a['muertes_punto'])} muertes "
        f"prematuras por año en Villa María (rango {_dec(a['muertes_punto_bajo'])}–{_dec(a['muertes_punto_alto'])})",
        f"- Si el verde se suma en los barrios con menos, el beneficio es {_dec(LANCET_FOCALIZADO[0])} a "
        f"{_dec(LANCET_FOCALIZADO[1])} veces mayor",
        "",
        decisiones,
        "",
        eventos,
        "",
        "MARCO NORMATIVO Y DE REFERENCIA:",
        "- Agenda 2030, ODS 11 (meta 11.7: acceso universal a espacios verdes)",
        "- C40 Urban Nature Accelerator (41 ciudades firmantes, entre ellas Buenos Aires)",
        "- Regla 3-30-300 (IUCN Urban Alliance)",
        "- Acuerdo de París / NDC Argentina",
        "- EU Nature Restoration Law, Art. 8 (referencia internacional)",
        "- Ordenanza 7209 \"Ruralidad Urbana\" de Villa María (2017)",
        "",
        "CORREDOR DEL RÍO CTALAMOCHITA:",
        "- Separa Villa María de Villa Nueva; potencial de parque lineal en ambas márgenes "
        "(la extensión del corredor no está medida en la app: tratarla como dato a relevar).",
    ]
    return "\n".join(l for l in lineas if l is not None), a


def _system_masterplan(nombre_municipio: str) -> str:
    return f"""Sos un experto en planificación urbana ambiental, política pública y desarrollo
sostenible de ciudades intermedias en Argentina y América Latina.

Tu tarea es generar un MASTERPLAN AMBIENTAL 2026–2030 completo, riguroso y accionable para
el Municipio de {nombre_municipio}, Córdoba, Argentina, basado exclusivamente en los datos
provistos por la plataforma Ciudad Verde AI Agent.

El documento se presenta ante autoridades municipales: cada número tiene que poder rastrearse
hasta los datos provistos.

REGLAS DE RIGOR (obligatorias):
- Usá SOLO las cifras del bloque de datos. No inventes cifras, superficies, cantidades ni estudios.
- Si necesitás un dato que no está, escribí "dato a relevar" en lugar de estimarlo.
- Todo valor que propongas vos (plazos, porcentajes, costos, cantidades por etapa) va marcado
  como "(supuesto)". Los montos del presupuesto van marcados como "(supuesto referencial)".
- Las líneas de acción siguen el orden de las DECISIONES DEL MUNICIPIO EN LÍNEA CON C40:
  primero las de prioridad Alta, después Media y después Baja. Si no hay decisiones cargadas,
  decilo en el diagnóstico y ordená las líneas según las brechas medidas.
- Los datos son de Villa María (38 barrios). Mencioná Villa Nueva solo como vecina del corredor
  del río, sin atribuirle cifras.
- Formato de números argentino: punto para miles y coma para decimales (31.665 árboles; 7,5 %).

ESTRUCTURA OBLIGATORIA:

1. RESUMEN EJECUTIVO (3-4 párrafos)
   - Diagnóstico sintético, posicionamiento frente a C40, la regla 3-30-300 y la Agenda 2030
   - Objetivo central del plan

2. DIAGNÓSTICO DE BASE
   - Fortalezas (con datos)
   - Brechas (con datos): copa arbórea, meta 1 árbol por casa, dependencia de los cultivos para la meta 1 de C40
   - Barrios prioritarios y justificación con los datos de copa y déficit

3. VISIÓN 2030
   - Enunciado de visión
   - 3 objetivos estratégicos medibles, anclados en las metas del bloque de datos

4. LÍNEAS DE ACCIÓN (mínimo 5, priorizadas 🔴 Alta, 🟡 Media, 🟢 Baja, según las decisiones del municipio)
   Para cada línea: descripción, justificación con datos, al menos 3 acciones concretas,
   indicador de seguimiento y plazo (supuesto)

5. METAS CUANTIFICABLES 2026–2030
   - Tabla: indicador | valor actual | meta 2030 | responsable

6. IMPACTO PROYECTADO
   - CO₂ capturado al cumplir las metas (usar las cifras del bloque)
   - Enfriamiento: usar solo la diferencia medida entre zonas con y sin vegetación
   - Salud pública con Martin et al. (2025)
   - Huella de los eventos registrados y su compensación

7. MARCO NORMATIVO Y ALINEACIÓN INTERNACIONAL

8. PRESUPUESTO ESTIMADO REFERENCIAL
   - Por línea de acción y total 2026–2030, cada monto marcado "(supuesto referencial)"
   - Fuentes de financiamiento posibles (municipal, provincial, nacional, fondos climáticos)

9. GOBERNANZA Y SEGUIMIENTO
   - Estructura de gestión, monitoreo satelital periódico e indicadores clave

10. CONCLUSIÓN Y PRÓXIMOS 90 DÍAS

FORMATO:
- Títulos de sección con "# ", subtítulos con "## ", listas con "- " y tablas con "|".
- Español formal pero accesible para funcionarios municipales.
- Incorporá el foco indicado por el usuario en las líneas de acción prioritarias.
- Extensión: 3.000 a 4.500 palabras.
"""


def _llamar_modelo(foco: str, nombre_municipio: str, contexto: str) -> tuple[str, int, int]:
    """Llama a Claude Opus 5.5 y devuelve (texto, tok_in, tok_out)."""
    if not ANTHROPIC_API_KEY:
        return "⚠️ ANTHROPIC_API_KEY no configurada.", 0, 0

    prompt_usuario = f"""
{contexto}

FOCO ESPECÍFICO DEL PLAN (indicado por el usuario):
{foco}

Generá el Masterplan Ambiental completo para {nombre_municipio} siguiendo la estructura
y las reglas de rigor indicadas, incorporando el foco específico en las líneas de acción prioritarias.
"""
    headers = {
        "x-api-key":         ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type":      "application/json",
    }
    payload = {
        "model":      MODEL_ID,
        "max_tokens": MAX_TOKENS,
        "system":     _system_masterplan(nombre_municipio),
        "messages":   [{"role": "user", "content": prompt_usuario}],
    }
    try:
        r = requests.post(API_URL, headers=headers, json=payload, timeout=TIMEOUT_S)
        r.raise_for_status()
        data    = r.json()
        texto   = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
        tok_in  = data.get("usage", {}).get("input_tokens",  0)
        tok_out = data.get("usage", {}).get("output_tokens", 0)
        if data.get("stop_reason") == "max_tokens":
            texto += ("\n\n⚠️ El documento se cortó al alcanzar el límite de extensión del modelo. "
                      "Generalo de nuevo o acotá el foco.")
        return texto, tok_in, tok_out
    except requests.exceptions.Timeout:
        return f"⚠️ Tiempo de espera agotado ({TIMEOUT_S}s). Intentá de nuevo.", 0, 0
    except requests.exceptions.HTTPError:
        return f"⚠️ Error de la API ({r.status_code}): {r.text[:300]}", 0, 0
    except Exception as e:
        return f"⚠️ Error: {str(e)}", 0, 0


def _render_historial(ciudad: str):
    """Muestra el historial de masteplans guardados en PostgreSQL, filtrado por ciudad."""
    masteplans_guardados = obtener_masteplans(limit=5, ciudad=ciudad)
    if masteplans_guardados:
        with st.expander(
            f"📂 Masteplans guardados ({len(masteplans_guardados)} recientes)",
            expanded=False,
        ):
            for mp in masteplans_guardados:
                fecha = mp["fecha"]
                fecha_str = (
                    fecha.strftime("%d/%m/%Y %H:%M")
                    if hasattr(fecha, "strftime")
                    else str(fecha)[:16]
                )
                foco_guardado = (mp["foco"] or "")[:120]
                col_mp, col_load = st.columns([5, 1])
                with col_mp:
                    st.markdown(
                        f"<div style='font-family:\"Space Mono\",monospace;font-size:10px;"
                        f"color:rgba(170,176,200,0.7);'>"
                        f"<b style='color:#9060ff;'>#{mp['id']}</b> · {fecha_str} · "
                        f"<span style='color:rgba(200,188,255,0.6)'>"
                        f"{mp['palabras'] or 0:,} palabras</span><br>"
                        f"<span style='font-size:9px;color:rgba(150,160,200,0.5);'>"
                        f"{foco_guardado}…</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                with col_load:
                    if st.button("Cargar", key=f"mp_load_{mp['id']}", use_container_width=True):
                        st.session_state["mp_resultado"]      = mp["texto"]
                        st.session_state["mp_tok_in"]         = mp["tok_input"] or 0
                        st.session_state["mp_tok_out"]        = mp["tok_output"] or 0
                        st.session_state["mp_costo"]          = float(mp.get("costo_usd") or 0)
                        st.session_state["mp_modelo"]         = "Claude"
                        st.session_state["mp_id_guardado"]    = mp["id"]
                        st.session_state["mp_fecha_guardado"] = fecha_str
                        st.rerun()

                confirmando = st.session_state.get("mp_confirmar_borrar") == mp["id"]
                if confirmando:
                    col_conf1, col_conf2 = st.columns(2)
                    with col_conf1:
                        if st.button("✅ Confirmar borrado", key=f"mp_del_confirm_{mp['id']}", use_container_width=True):
                            eliminar_masterplan(mp["id"])
                            st.session_state.pop("mp_confirmar_borrar", None)
                            st.rerun()
                    with col_conf2:
                        if st.button("✕ Cancelar", key=f"mp_del_cancel_{mp['id']}", use_container_width=True):
                            st.session_state.pop("mp_confirmar_borrar", None)
                            st.rerun()
                else:
                    if st.button("🗑️ Borrar", key=f"mp_del_{mp['id']}", use_container_width=True):
                        st.session_state["mp_confirmar_borrar"] = mp["id"]
                        st.rerun()
    return masteplans_guardados




def _focos_sugeridos(a):
    """Cuatro focos con los números actuales de la app."""
    from modulo_villamaria import DATOS_VM
    cob = DATOS_VM['cobertura']
    m = a['meta_municipal'] if a else None
    focos = []
    if m:
        focos.append(("🌳 Meta 1 árbol por casa", (
            f"Cerrar el déficit de {_num(m['deficit_arboles'])} árboles de la meta municipal de 1 árbol "
            f"por casa (hoy {_dec(m['cumplimiento_pct'])} % cumplida), a razón de "
            f"{_num(a['arboles_por_anio_municipal'])} árboles por año entre 2026 y 2030, empezando por "
            f"los barrios con mayor déficit."
        )))
    if a:
        menos = ", ".join(b['barrio'] for b in a['barrios_copa'][:3])
        llegan = ("ningún barrio llega" if a['barrios_30'] == 0 else
                  "1 barrio llega" if a['barrios_30'] == 1 else f"{a['barrios_30']} barrios llegan")
        focos.append(("🌿 Regla 3-30-300", (
            f"Avanzar hacia el 30 % de copa arbórea por barrio de la regla 3-30-300: hoy la ciudad tiene "
            f"{_dec(a['copa_pct'])} % y {llegan} al 30 %. Priorizar los barrios "
            f"con menos copa ({menos}) para sumar sombra, enfriamiento y beneficios en salud."
        )))
    focos.append(("💧 Corredor Ctalamochita", (
        "Desarrollo del corredor verde sobre el Río Ctalamochita como parque lineal y corredor "
        "ecológico de Villa María, con arbolado ribereño nativo, senderos y ciclovías, coordinado "
        "con Villa Nueva en la margen opuesta."
    )))
    if a:
        focos.append(("🌍 Sostener C40", (
            f"Mantener la meta 1 de C40 (hoy {_dec(a['qtc'])} % de cobertura verde, meta 30–40 %), "
            f"asegurando que el verde que aportan cultivos ({_dec(cob.get('cultivos') or 0)} %) y "
            f"pastizales ({_dec(cob.get('pastizales') or 0)} %) no se pierda con la urbanización: sin "
            f"cultivos la ciudad quedaría en {_dec(a['qtc_sin_cultivos'])} %."
        )))
    return focos


def _render_formulario_admin(a):
    """Formulario de generación — solo visible para admin."""
    st.markdown("### ✏️ Foco del plan")
    st.markdown(
        "Indicá el enfoque prioritario para personalizar el Masterplan. Las líneas de acción se "
        "ordenan según las **Decisiones para Villa María en línea con C40** guardadas en Benchmarking C40."
    )

    if "mp_foco_set" in st.session_state:
        st.session_state["mp_foco"] = st.session_state.pop("mp_foco_set")

    foco = st.text_area(
        "Foco y prioridades",
        placeholder=(
            "Ejemplo: Priorizar los barrios con menos copa arbórea y el cierre del déficit de la meta "
            "1 árbol por casa, junto con el corredor verde del Río Ctalamochita."
        ),
        height=120,
        key="mp_foco",
    )

    st.markdown("**Focos sugeridos:**")
    focos = _focos_sugeridos(a)
    cols = st.columns(2)
    for i, (etiqueta, texto_foco) in enumerate(focos):
        with cols[i % 2]:
            if st.button(etiqueta, key=f"mp_sug{i + 1}", use_container_width=True):
                st.session_state["mp_foco_set"] = texto_foco
                st.rerun()

    st.markdown("---")

    col_gen, col_info = st.columns([2, 3])
    with col_gen:
        generar = st.button(
            f"🚀 Generar Masterplan con {MODEL_NOMBRE}",
            key="mp_generar",
            use_container_width=True,
            type="primary",
        )
    with col_info:
        st.markdown(
            "<div style='padding:9px 0;font-family:\"Space Mono\",monospace;"
            "font-size:10px;color:rgba(170,176,200,0.6);'>"
            "⏱️ Tiempo estimado: 1–3 minutos · "
            f"Modelo: {MODEL_NOMBRE} · "
            "Output: 3.000–4.500 palabras</div>",
            unsafe_allow_html=True,
        )

    return generar, foco


def _render_documento(texto, nombre_municipio, archivo_slug, marco_normativo_local):
    """Renderiza el documento Masterplan en pantalla y botones de acción."""
    import html as _html
    import re as _re
    import datetime as _dt

    tok_in   = st.session_state.get("mp_tok_in",  0)
    tok_out  = st.session_state.get("mp_tok_out", 0)
    costo    = st.session_state.get("mp_costo", 0.0)
    modelo   = st.session_state.get("mp_modelo", "Claude")
    mp_id    = st.session_state.get("mp_id_guardado", "")
    mp_fecha = st.session_state.get("mp_fecha_guardado", "")

    if mp_id:
        st.success(f"✅ Masterplan #{mp_id} guardado en base de datos · {mp_fecha}")

    if tok_in > 0:
        mc1, mc2, mc3, mc4 = st.columns(4)
        with mc1: st.metric("Tokens input",     f"{tok_in:,}")
        with mc2: st.metric("Tokens output",    f"{tok_out:,}")
        with mc3: st.metric("Costo generación", f"USD {costo:.4f}")
        with mc4: st.metric("Palabras aprox.",  f"{len(texto.split()):,}")

    st.markdown("---")

    fecha_gen     = _dt.datetime.now().strftime("%d de %B de %Y")
    fecha_gen_pdf = _dt.datetime.now().strftime("%d/%m/%Y")

    def _md_inline(txt):
        txt = _html.escape(txt)
        txt = _re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', txt)
        txt = _re.sub(r'\*(.+?)\*',     r'<em>\1</em>',         txt)
        txt = _re.sub(r'`(.+?)`',       r'<code>\1</code>',     txt)
        return txt

    def _parsear(texto, modo):
        resultado = []
        lineas = texto.split("\n")
        i = 0
        while i < len(lineas):
            linea = lineas[i]
            s     = linea.strip()

            if _re.match(r'^-{3,}$', s) or _re.match(r'^\*{3,}$', s):
                i += 1
                continue

            if not s:
                if resultado and resultado[-1] not in (
                    '<br>', "<div class='mp-report-spacer'></div>"
                ):
                    resultado.append(
                        "<div class='mp-report-spacer'></div>"
                        if modo == 'screen' else '<br>'
                    )
                i += 1
                continue

            if linea.startswith("# "):
                contenido = _md_inline(linea[2:])
                resultado.append(
                    f"<div class='mp-report-h1'>{contenido}</div>"
                    if modo == 'screen' else f"<h2>{contenido}</h2>"
                )
                i += 1
                continue

            if linea.startswith("## ") or linea.startswith("### "):
                contenido = _md_inline(_re.sub(r'^#+\s*', '', linea))
                resultado.append(
                    f"<div class='mp-report-h2'>{contenido}</div>"
                    if modo == 'screen' else f"<h3>{contenido}</h3>"
                )
                i += 1
                continue

            if s.isupper() and 4 < len(s) < 90 and not s.startswith("|"):
                contenido = _md_inline(s)
                resultado.append(
                    f"<div class='mp-report-h1'>{contenido}</div>"
                    if modo == 'screen' else f"<h2>{contenido}</h2>"
                )
                i += 1
                continue

            if linea.startswith("- ") or linea.startswith("• "):
                contenido = _md_inline(linea[2:])
                resultado.append(
                    f"<div class='mp-report-li'>◦ {contenido}</div>"
                    if modo == 'screen' else f"<li>{contenido}</li>"
                )
                i += 1
                continue

            if s.startswith("|"):
                if _re.match(r'^\|[\s\-:|]+\|', s):
                    i += 1
                    continue
                celdas = [c.strip() for c in s.strip("|").split("|")]
                celdas_html = "".join(f"<td>{_md_inline(c)}</td>" for c in celdas)
                resultado.append(
                    f"<div class='mp-report-table'>"
                    f"<table style='width:100%;border-collapse:collapse;'>"
                    f"<tr>{celdas_html}</tr></table></div>"
                    if modo == 'screen'
                    else (
                        "<tr>"
                        + "".join(
                            f"<td style='padding:3px 8px;border-bottom:0.5pt solid #ddd;"
                            f"font-size:9pt;'>{_md_inline(c)}</td>"
                            for c in celdas
                        )
                        + "</tr>"
                    )
                )
                i += 1
                continue

            contenido = _md_inline(s)
            resultado.append(
                f"<div class='mp-report-p'>{contenido}</div>"
                if modo == 'screen' else f"<p>{contenido}</p>"
            )
            i += 1

        return "\n".join(resultado)

    documento_inner = _parsear(texto, 'screen')
    documento_print = _parsear(texto, 'print')

    st.markdown(
        f"""<div class='mp-report cv-printable'>
          <div class='mp-report-header'>
            <div style='display:flex;align-items:center;gap:14px;margin-bottom:12px;'>
              <div style='width:44px;height:44px;border-radius:10px;flex-shrink:0;
                   background:linear-gradient(135deg,#6228b4,#00b4dc);
                   display:flex;align-items:center;justify-content:center;
                   font-family:"Space Mono",monospace;font-size:18px;font-weight:700;color:#fff;'>
                CV</div>
              <div>
                <div style='font-family:"Space Mono",monospace;font-size:10px;
                     letter-spacing:0.12em;color:rgba(160,175,220,0.6);
                     text-transform:uppercase;'>Ciudad Verde AI Agent · {nombre_municipio}, Córdoba</div>
                <div style='font-family:"Space Grotesk",sans-serif;font-size:22px;
                     font-weight:700;color:#fff;margin-top:2px;'>
                     Masterplan Ambiental 2026–2030</div>
              </div>
            </div>
            <div style='display:flex;gap:24px;flex-wrap:wrap;
                 font-family:"Space Mono",monospace;font-size:10px;
                 color:rgba(160,175,220,0.55);letter-spacing:0.06em;'>
              <span>📅 {fecha_gen}</span>
              <span>🤖 {modelo}</span>
              <span>📡 {FUENTES_DATOS}</span>
            </div>
          </div>
          {documento_inner}
          <div style='margin-top:32px;padding-top:12px;
               border-top:0.5px solid rgba(120,140,255,0.15);
               font-family:"Space Mono",monospace;font-size:10px;
               color:rgba(160,175,220,0.4);letter-spacing:0.05em;'>
            Ciudad Verde AI Agent · Marco: C40, ODS 11, Acuerdo de París{marco_normativo_local}
          </div>
        </div>""",
        unsafe_allow_html=True,
    )

    st.markdown("---")

    col_print, col_dl, col_new, _ = st.columns([2, 2, 2, 1])
    with col_print:
        import streamlit.components.v1 as _components
        print_js = f"""
        <script>
        function abrirImpresion() {{
            var w = window.open('', '_blank', 'width=960,height=750,scrollbars=yes');
            w.document.write(`<!DOCTYPE html><html><head>
            <meta charset="utf-8">
            <title>Masterplan Ambiental · {nombre_municipio} 2026-2030</title>
            <style>
              * {{ box-sizing:border-box; margin:0; padding:0; }}
              body {{
                font-family: Georgia, 'Times New Roman', serif;
                font-size: 11pt; color: #111;
                margin: 0; padding: 0; background: #f5f5f5;
              }}
              .page {{
                background: #fff; max-width: 820px; margin: 24px auto;
                padding: 52px 56px 48px 56px;
                box-shadow: 0 2px 16px rgba(0,0,0,0.12);
              }}
              .rp-header {{
                border-bottom: 3px solid #1b5e20;
                padding-bottom: 18px; margin-bottom: 28px;
              }}
              .rp-org {{
                font-family: Arial, sans-serif; font-size: 9pt;
                font-weight: 700; letter-spacing: 0.12em;
                text-transform: uppercase; color: #2e7d32; margin-bottom: 6px;
              }}
              .rp-titulo {{
                font-family: Arial, sans-serif; font-size: 22pt;
                font-weight: 700; color: #1a1a1a; line-height: 1.1; margin-bottom: 6px;
              }}
              .rp-subtitulo {{
                font-family: Arial, sans-serif; font-size: 11pt;
                color: #4a4a4a; margin-bottom: 10px;
              }}
              .rp-meta {{
                display: flex; gap: 24px; flex-wrap: wrap;
                font-family: Arial, sans-serif; font-size: 8.5pt; color: #777;
                border-top: 0.5pt solid #ddd; padding-top: 10px; margin-top: 10px;
              }}
              h2 {{
                font-family: Arial, sans-serif; font-size: 12pt; font-weight: 700;
                color: #1b5e20; text-transform: uppercase; letter-spacing: 0.06em;
                margin: 22px 0 6px 0; padding-bottom: 5px;
                border-bottom: 1pt solid #c8e6c9;
              }}
              h3 {{
                font-family: Arial, sans-serif; font-size: 11pt; font-weight: 700;
                color: #1a3a6e; margin: 16px 0 5px 0;
              }}
              p {{ line-height: 1.65; margin: 5px 0; font-size: 10.5pt; text-align: justify; }}
              li {{ line-height: 1.6; margin: 3px 0 3px 18px; font-size: 10.5pt; }}
              .rp-footer {{
                margin-top: 36px; padding-top: 10px; border-top: 1pt solid #ddd;
                font-family: Arial, sans-serif; font-size: 8pt; color: #999; text-align: center;
              }}
              .btn-print {{
                display: block; margin: 20px auto 0; padding: 10px 28px;
                background: #1b5e20; color: #fff; border: none; border-radius: 6px;
                font-family: Arial, sans-serif; font-size: 13px; cursor: pointer;
              }}
              @media print {{
                body {{ background:#fff; }}
                .page {{ margin:0; box-shadow:none; padding:20mm 22mm; }}
                .btn-print {{ display:none; }}
              }}
            </style>
            </head><body>
            <div class="page">
              <div class="rp-header">
                <div class="rp-org">🌿 Ciudad Verde AI Agent &nbsp;·&nbsp; Municipio de {nombre_municipio} &nbsp;·&nbsp; C&#243;rdoba, Argentina</div>
                <div class="rp-titulo">Masterplan Ambiental<br>{nombre_municipio} 2026&#8211;2030</div>
                <div class="rp-subtitulo">Diagn&#243;stico, objetivos y l&#237;neas de acci&#243;n para la pol&#237;tica p&#250;blica ambiental municipal</div>
                <div class="rp-meta">
                  <span>&#128197; {fecha_gen_pdf}</span>
                  <span>&#129302; {modelo}</span>
                  <span>&#128225; {FUENTES_DATOS}</span>
                </div>
              </div>
              {documento_print}
              <div class="rp-footer">
                Ciudad Verde AI Agent &nbsp;&middot;&nbsp; Marco normativo: C40, ODS 11, Acuerdo de Par&#237;s{marco_normativo_local} &nbsp;&middot;&nbsp; {fecha_gen_pdf}
              </div>
              <button class="btn-print" onclick="window.print()">&#128438; Imprimir / Guardar PDF</button>
            </div>
            </body></html>`);
            w.document.close();
            w.focus();
        }}
        </script>
        <button onclick="abrirImpresion()"
           style="width:100%;background:linear-gradient(135deg,#6228b4,#00b4dc);
                  border:none;border-radius:8px;color:#fff;
                  font-family:'Space Grotesk',sans-serif;font-size:14px;
                  font-weight:600;padding:10px;cursor:pointer;">
           🖨️ Imprimir / Guardar PDF
        </button>"""
        _components.html(print_js, height=50)

    with col_dl:
        st.download_button(
            "⬇️ Descargar .txt",
            data=texto.encode("utf-8"),
            file_name=f"masterplan_{archivo_slug}.txt",
            mime="text/plain",
            key="mp_download",
            use_container_width=True,
        )
    with col_new:
        if st.button("🔄 Nuevo Masterplan", key="mp_nuevo", use_container_width=True):
            for k in ("mp_resultado", "mp_tok_in", "mp_tok_out", "mp_costo", "mp_modelo",
                      "mp_id_guardado", "mp_fecha_guardado"):
                st.session_state.pop(k, None)
            st.rerun()




def render_masterplan(municipio: str = 'villamaria'):
    """Punto de entrada del módulo. Llamar desde modulo_villamaria.py o modulo_villanueva.py.
    municipio: 'villamaria' (default) o 'villanueva'."""

    info_municipio    = MUNICIPIOS.get(municipio, MUNICIPIOS['villamaria'])
    nombre_municipio  = info_municipio['nombre']
    archivo_slug      = info_municipio['archivo']
    marco_normativo_local = ", Ordenanza 7209/2017" if municipio == 'villamaria' else ""

    st.title(f"📄 Masterplan Ambiental · {nombre_municipio}")
    st.markdown("---")

    es_admin = st.session_state.get("cv_admin_auth", False)

    # ── Historial visible para todos (filtrado por ciudad) ────
    _render_historial(ciudad=nombre_municipio)

    st.markdown("---")

    # ── Bloque según rol ──────────────────────────────────────
    if es_admin and not info_municipio.get('genera', False):
        st.info(
            f"🔒 **Generación no habilitada para {nombre_municipio}** — todavía no tiene datos "
            "auditados para armar el contexto del Masterplan. El historial de arriba sigue disponible."
        )
    elif not es_admin:
        st.info(
            "🔒 **Generación restringida** — Solo los administradores pueden generar "
            "nuevos Masteplans. Si necesitás uno actualizado, contactá al administrador "
            "de la plataforma. Podés cargar y visualizar los documentos ya guardados "
            "desde el historial de arriba."
        )
    else:
        st.markdown(
            "<div style='font-family:\"Space Mono\",monospace;font-size:10px;"
            "color:rgba(120,200,120,0.7);letter-spacing:0.08em;margin-bottom:16px;'>"
            f"🔑 MODO ADMINISTRADOR · Generación habilitada · {MODEL_NOMBRE}"
            "</div>",
            unsafe_allow_html=True,
        )

        contexto, a = _contexto_vm()
        if not contexto:
            st.warning(
                "⚠️ Faltan los datos precalculados de Villa María (indicadores, censo arbóreo o zonas). "
                "Sin ellos no se puede generar un Masterplan con cifras trazables."
            )
            st.stop()

        with st.expander("📋 Datos que recibe el modelo", expanded=False):
            st.caption("Este bloque se arma en el momento con los datos de la app. "
                       "El modelo tiene la instrucción de usar solo estas cifras.")
            st.code(contexto, language=None)

        generar, foco = _render_formulario_admin(a)

        if generar:
            foco_final = st.session_state.get("mp_foco", "").strip()
            if not foco_final:
                st.warning("Ingresá un foco para personalizar el Masterplan.")
            else:
                st.session_state["mp_foco_en_proceso"] = foco_final

                orbe_slot = st.empty()
                orbe_slot.markdown(
                    """<div style='display:flex;flex-direction:column;align-items:center;
                        gap:16px;padding:32px 0;'>
                      <div style='position:relative;width:80px;height:80px;'>
                        <div style='position:absolute;inset:0;border-radius:50%;
                             background:radial-gradient(circle at 38% 32%,
                             #d0a0ff 0%,#7030e0 30%,#2010a0 62%,#060318 100%);
                             animation:mp-pulse 2s ease-in-out infinite;
                             box-shadow:0 0 24px rgba(110,45,230,0.6);'></div>
                      </div>
                      <div style='font-family:"Space Mono",monospace;font-size:11px;
                           color:rgba(180,160,255,0.8);letter-spacing:0.06em;'>
                        ● __MODELO__ · GENERANDO MASTERPLAN
                      </div>
                    </div>
                    <style>
                    @keyframes mp-pulse {
                      0%,100%{box-shadow:0 0 24px rgba(110,45,230,.6);transform:scale(1);}
                      50%{box-shadow:0 0 42px rgba(130,60,255,.85);transform:scale(1.06);}
                    }
                    </style>""".replace("__MODELO__", MODEL_NOMBRE.upper()),
                    unsafe_allow_html=True,
                )

                usuario = st.session_state.get("cv_usuario", "admin")
                texto, tok_in, tok_out = _llamar_modelo(foco_final, nombre_municipio, contexto)
                orbe_slot.empty()

                if tok_in > 0:
                    registrar_consumo(
                        usuario=usuario,
                        tipo=TIPO_CONSUMO,
                        pregunta=f"[MASTERPLAN] {foco_final[:200]}",
                        tok_input=tok_in,
                        tok_output=tok_out,
                        modelo=MODEL_ID,
                    )
                    nuevo_id = guardar_masterplan(
                        usuario=usuario,
                        foco=foco_final,
                        texto=texto,
                        tok_input=tok_in,
                        tok_output=tok_out,
                        ciudad=nombre_municipio,
                    )
                    st.session_state["mp_id_guardado"]    = nuevo_id
                    st.session_state["mp_fecha_guardado"] = "recién generado"

                st.session_state["mp_resultado"] = texto
                st.session_state["mp_tok_in"]    = tok_in
                st.session_state["mp_tok_out"]   = tok_out
                st.session_state["mp_costo"]     = (tok_in * PRECIO_INPUT + tok_out * PRECIO_OUTPUT) / 1_000_000
                st.session_state["mp_modelo"]    = MODEL_NOMBRE
                st.rerun()

    # ── Mostrar documento cargado o recién generado ───────────
    if "mp_resultado" in st.session_state:
        _render_documento(
            st.session_state["mp_resultado"],
            nombre_municipio=nombre_municipio,
            archivo_slug=archivo_slug,
            marco_normativo_local=marco_normativo_local,
        )

    st.markdown("---")
    st.caption(
        f"Ciudad Verde AI Agent · Masterplan generado con {MODEL_NOMBRE} · "
        f"Datos: {FUENTES_DATOS} · "
        f"Marco: C40, ODS 11, Acuerdo de París{marco_normativo_local}"
    )
