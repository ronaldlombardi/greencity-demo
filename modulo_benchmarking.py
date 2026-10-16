"""
modulo_benchmarking.py — Ciudad Verde AI Agent
==============================================
Benchmarking C40 · Villa María.

- Tabla de las ciudades firmantes del C40 Urban Nature Accelerator, con sus
  planes, números y fuentes (data/benchmarking_c40.json, sin consultas en vivo).
- Estado de Villa María medido con las metas C40 (datos de la propia app).
- Decisiones para Villa María en línea con C40: las edita solo el administrador,
  se guardan en PostgreSQL (cv_decisiones_c40) y el Masterplan las usa en su prompt.

Uso:
    from modulo_benchmarking import render_benchmarking_c40
    render_benchmarking_c40()
"""

import os
import json

import pandas as pd
import streamlit as st

from modulo_db import guardar_decision, obtener_decisiones, DB_URL

RUTA_BENCHMARKING = os.path.join(os.path.dirname(__file__), 'data', 'benchmarking_c40.json')
CIUDAD = "Villa María"

PRIORIDADES = ["Sin definir", "Alta", "Media", "Baja", "No aplica"]
COLOR_PRIORIDAD = {"Alta": "#c62828", "Media": "#f57c00", "Baja": "#2e7d32", "No aplica": "#757575"}

# Clases de ESA WorldCover que el estudio de las 96 ciudades C40 cuenta como verde
# para la meta 1 (el agua queda afuera). Claves según indicadores_villamaria.json.
CLASES_VERDE_C40 = ['arboles', 'arbustos', 'pastizales', 'cultivos', 'humedal', 'manglar', 'musgo']


# ============================================================
# CARGA DE DATOS
# ============================================================

@st.cache_data(show_spinner=False)
def _cargar_benchmarking():
    if not os.path.exists(RUTA_BENCHMARKING):
        return None
    with open(RUTA_BENCHMARKING, encoding='utf-8') as f:
        return json.load(f)


# ============================================================
# HELPERS
# ============================================================

def _num(n):
    """Entero con separador de miles argentino."""
    return f"{int(round(n)):,}".replace(",", ".")


def _dec(x, d=1):
    """Decimal con coma."""
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


def _titulos_fuentes(claves, fuentes):
    return " · ".join(fuentes[k]['titulo'] for k in claves if k in fuentes)


# ============================================================
# BLOQUES DE PANTALLA
# ============================================================

def _render_contexto(datos):
    st.markdown("### 🎯 Las metas C40 a 2030")
    m = datos['metas_c40']
    c1, c2 = st.columns(2)
    with c1:
        st.info(f"**Meta 1 · Cobertura verde**\n\n{m['meta_1']}")
    with c2:
        st.info(f"**Meta 2 · Acceso equitativo**\n\n{m['meta_2']}")
    st.markdown("**Avance de las ciudades firmantes**")
    for linea in datos['avance_global']:
        st.markdown(f"- {linea}")
    st.caption(datos['nota'])


def _render_tabla(datos):
    st.markdown("### 🌍 Ciudades firmantes")
    ciudades = datos['ciudades']
    fuentes = datos['fuentes']

    regiones = sorted({c['region'] for c in ciudades})
    col_f, col_b = st.columns([2, 2])
    with col_f:
        elegidas = st.multiselect("Región", regiones, default=regiones, key="bench_regiones")
    with col_b:
        buscar = st.text_input("Buscar (ciudad, plan o acción)", key="bench_buscar").strip().lower()

    filas = []
    for c in ciudades:
        if c['region'] not in elegidas:
            continue
        texto = " ".join([c['ciudad'], c['pais'], c['plan'], c['numeros'], c['acciones']]).lower()
        if buscar and buscar not in texto:
            continue
        filas.append({
            'Ciudad': c['ciudad'],
            'País': c['pais'],
            'Región': c['region'],
            'Meta C40 informada': c['meta'],
            'Plan o programa': c['plan'],
            'Números clave': c['numeros'],
            'Acciones destacadas': c['acciones'],
            'Fuentes': _titulos_fuentes(c['fuentes'], fuentes),
        })

    st.caption(f"{len(filas)} de {len(ciudades)} ciudades")
    if filas:
        st.dataframe(
            pd.DataFrame(filas), hide_index=True, use_container_width=True, height=460,
            column_config={
                'Plan o programa': st.column_config.TextColumn(width="medium"),
                'Números clave': st.column_config.TextColumn(width="large"),
                'Acciones destacadas': st.column_config.TextColumn(width="large"),
            },
        )

    # Detalle completo de una ciudad (la tabla recorta textos largos)
    nombres = [f['Ciudad'] for f in filas]
    if nombres:
        elegida = st.selectbox("Ver el detalle de una ciudad", nombres, key="bench_detalle")
        c = next(x for x in ciudades if x['ciudad'] == elegida)
        enlaces = " · ".join(
            f"[{fuentes[k]['titulo']}]({fuentes[k]['url']})" for k in c['fuentes'] if k in fuentes
        )
        st.markdown(
            f"**{c['ciudad']}** ({c['pais']}) · Meta C40: {c['meta']}\n\n"
            f"- **Plan o programa:** {c['plan']}\n"
            f"- **Números clave:** {c['numeros']}\n"
            f"- **Acciones destacadas:** {c['acciones']}\n"
            f"- **Fuentes:** {enlaces}"
        )


def _render_fuentes(datos):
    with st.expander("📚 Fuentes", expanded=False):
        for f in datos['fuentes'].values():
            st.markdown(f"- [{f['titulo']}]({f['url']})")


def _render_estado_vm():
    """Villa María medida con las mismas metas, desde los datos de la propia app."""
    from modulo_villamaria import DATOS_VM
    from modulo_barrios import _cargar_resumen

    st.markdown(f"### 🏙️ Estado de {CIUDAD} frente a las metas C40")

    if DATOS_VM.get('datos_preliminares'):
        st.warning("Faltan los indicadores calculados de Villa María (`data/indicadores_villamaria.json`).")
        return

    cob = DATOS_VM['cobertura']
    acc = DATOS_VM['acceso']
    lst = DATOS_VM['lst']
    res = _cargar_resumen()

    qtc = sum(cob.get(k) or 0 for k in CLASES_VERDE_C40)
    acceso = acc.get('acceso') or 0
    enf = lst.get('enfriamiento') or 0

    c1, c2, c3 = st.columns(3)
    with c1:
        color = "#2e7d32" if qtc >= 30 else "#f57c00"
        _card("Meta 1 · Cobertura verde", f"{_dec(qtc)} %",
              f"Meta C40: 30 %–40 % · {'cumplida' if qtc >= 30 else 'no cumplida'}", color)
    with c2:
        color = "#2e7d32" if acceso >= 70 else "#f57c00"
        _card("Meta 2 · Acceso (aproximación)", f"{_dec(acceso, 0)} %",
              "Área edificada a menos de 300 m de verde", color)
    with c3:
        _card("Enfriamiento medido", f"{_dec(enf, 2)} °C",
              "Verde denso vs. suelo/asfalto (Landsat 8/9)", "#1e88e5")

    if res:
        m = res['ciudad']['meta_1_arbol_por_casa']
        c4, c5, c6 = st.columns(3)
        with c4:
            _card("Árboles detectados", _num(res['ciudad']['total_arboles']),
                  "Meta/WRI Canopy Height · imagen 2018", "#2e7d32")
        with c5:
            _card("Meta municipal 1 árbol por casa", f"{_dec(m['cumplimiento_pct'])} %",
                  f"{_num(m['lotes_estimados'])} lotes estimados", "#f57c00")
        with c6:
            _card("Déficit", f"{_num(m['deficit_arboles'])} árboles",
                  "para llegar a 1 árbol por casa", "#c62828")

    st.caption(
        "**Cómo se mide.** Meta 1: suma de las clases de ESA WorldCover que el estudio de las 96 "
        "ciudades C40 cuenta como verde (árboles, arbustos, pastizales, cultivos y humedales; el agua "
        "queda afuera), sobre el área de análisis de los indicadores. "
        "Meta 2: C40 pide el 70 % de la población a 15 minutos caminando (~1.000 m) de un espacio "
        "verde o azul público; el valor mostrado es una aproximación con el área edificada a menos de "
        "300 m de cualquier verde satelital, incluidos espacios privados."
    )


def _render_decisiones(datos):
    st.markdown(f"### 📋 Decisiones para {CIUDAD} en línea con C40")
    st.caption(
        "Líneas de acción tomadas de las ciudades firmantes. Las prioridades que se guardan acá "
        "las usa el Masterplan para generar las estrategias."
    )

    if not DB_URL:
        st.warning("La base de datos no está configurada: las decisiones no se pueden guardar ni leer.")
        return

    if st.session_state.pop("dec_c40_guardadas", False):
        st.success("✅ Decisiones guardadas.")

    lineas = datos['lineas_accion']
    guardadas = obtener_decisiones(CIUDAD)
    es_admin = st.session_state.get("cv_admin_auth", False)

    if es_admin:
        st.markdown(
            "<div style='font-family:\"Space Mono\",monospace;font-size:10px;"
            "color:rgba(120,200,120,0.7);letter-spacing:0.08em;margin-bottom:8px;'>"
            "🔑 MODO ADMINISTRADOR · Edición habilitada</div>",
            unsafe_allow_html=True,
        )
        with st.form("form_decisiones_c40"):
            valores = {}
            for ln in lineas:
                previa = guardadas.get(ln['id'], {})
                st.markdown(f"**{ln['titulo']}** · _{ln['referencia']}_")
                st.caption(ln['descripcion'])
                c1, c2 = st.columns([1, 3])
                with c1:
                    prioridad = st.selectbox(
                        "Prioridad", PRIORIDADES,
                        index=PRIORIDADES.index(previa.get('prioridad', 'Sin definir'))
                        if previa.get('prioridad') in PRIORIDADES else 0,
                        key=f"dec_prio_{ln['id']}", label_visibility="collapsed",
                    )
                with c2:
                    nota = st.text_input(
                        "Nota", value=previa.get('nota') or "",
                        key=f"dec_nota_{ln['id']}", label_visibility="collapsed",
                        placeholder="Nota (opcional)",
                    )
                valores[ln['id']] = (prioridad, nota)
            guardar = st.form_submit_button("💾 Guardar decisiones", use_container_width=True)

        if guardar:
            usuario = st.session_state.get("cv_usuario", "admin")
            errores = 0
            for id_linea, (prioridad, nota) in valores.items():
                previa = guardadas.get(id_linea, {})
                sin_cambios = (previa.get('prioridad', 'Sin definir') == prioridad
                               and (previa.get('nota') or "") == nota)
                if sin_cambios:
                    continue
                if not guardar_decision(CIUDAD, id_linea, prioridad, nota, usuario):
                    errores += 1
            if errores:
                st.error(f"No se pudieron guardar {errores} decisiones. Revisá la conexión a la base de datos.")
            else:
                st.session_state["dec_c40_guardadas"] = True
                st.rerun()
    else:
        st.info("🔒 Solo el administrador puede modificar las decisiones. Abajo se ve lo decidido.")

    _render_resumen_decisiones(lineas, guardadas)


def _render_resumen_decisiones(lineas, guardadas):
    st.markdown("#### Resumen de lo decidido")
    por_id = {ln['id']: ln for ln in lineas}
    hay = False
    for prioridad in ["Alta", "Media", "Baja", "No aplica"]:
        items = [(por_id[i], d) for i, d in guardadas.items()
                 if d.get('prioridad') == prioridad and i in por_id]
        if not items:
            continue
        hay = True
        color = COLOR_PRIORIDAD[prioridad]
        st.markdown(f"<div style='font-weight:700;color:{color};margin-top:8px'>Prioridad {prioridad}</div>",
                    unsafe_allow_html=True)
        for ln, d in items:
            nota = f" — {d['nota']}" if d.get('nota') else ""
            st.markdown(f"- **{ln['titulo']}** ({ln['referencia']}){nota}")
    if not hay:
        st.caption("Todavía no hay decisiones guardadas.")
    else:
        fechas = [d['fecha'] for d in guardadas.values() if d.get('fecha')]
        if fechas:
            ultima = max(fechas)
            ultima_txt = ultima.strftime("%d/%m/%Y %H:%M") if hasattr(ultima, "strftime") else str(ultima)[:16]
            st.caption(f"Última modificación: {ultima_txt}")


# ============================================================
# TEXTO PARA EL PROMPT DEL MASTERPLAN
# ============================================================

def texto_decisiones_para_prompt(ciudad: str = CIUDAD) -> str:
    """Devuelve las decisiones C40 guardadas como texto para el prompt del Masterplan.
    Incluye solo las prioridades Alta, Media y Baja, con su ciudad de referencia y nota."""
    datos = _cargar_benchmarking()
    if not datos:
        return ""
    por_id = {ln['id']: ln for ln in datos['lineas_accion']}
    guardadas = obtener_decisiones(ciudad)
    lineas = []
    for prioridad in ["Alta", "Media", "Baja"]:
        for id_linea, d in guardadas.items():
            if d.get('prioridad') != prioridad or id_linea not in por_id:
                continue
            ln = por_id[id_linea]
            nota = f" Nota del municipio: {d['nota']}" if d.get('nota') else ""
            lineas.append(f"- [{prioridad}] {ln['titulo']}: {ln['descripcion']} "
                          f"(referencia C40: {ln['referencia']}).{nota}")
    if not lineas:
        return ""
    return ("DECISIONES DEL MUNICIPIO EN LÍNEA CON C40 (priorizadas por el administrador):\n"
            + "\n".join(lineas))


# ============================================================
# RENDER
# ============================================================

def render_benchmarking_c40():
    """Punto de entrada. Llamar desde render_modulo_villamaria()."""
    st.title("🌐 Benchmarking C40")
    st.caption("Ciudades del C40 Urban Nature Accelerator y Villa María medida con las mismas metas")

    datos = _cargar_benchmarking()
    if not datos:
        st.warning("Falta data/benchmarking_c40.json.")
        return

    _render_contexto(datos)
    st.markdown("---")
    _render_tabla(datos)
    _render_fuentes(datos)
    st.markdown("---")
    _render_estado_vm()
    st.markdown("---")
    _render_decisiones(datos)
    st.markdown("---")
    st.caption(
        f"Ciudad Verde AI Agent · Benchmarking C40 · Datos de ciudades actualizados al "
        f"{datos['actualizado']} · Fuentes: informes C40 Urban Nature Accelerator 2023 y 2025 y "
        "fuentes oficiales de cada ciudad"
    )
