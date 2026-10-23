"""
modulo_bonos_verdes.py — Ciudad Verde AI Agent
===============================================
Bonos Verdes y Financiamiento del Masterplan.

Lee data/fuentes_financiamiento.json (catálogo verificado con fuentes).
Pestañas:
  1. Catálogo de fuentes      — todas las vías, viables hoy o no
  2. Elegibilidad Villa María — requisitos de plataforma (indicadores reales)
                                y del municipio (cargados por el admin en PostgreSQL)
  3. Marco legal y fuentes    — Ley 25.917, BCRA, CNV y referencias
"""

import os
import json
import streamlit as st
from modulo_db import guardar_requisito, obtener_requisitos

_RUTA_CATALOGO = os.path.join(os.path.dirname(__file__), "data", "fuentes_financiamiento.json")
_RUTA_INDICADORES = os.path.join(os.path.dirname(__file__), "data", "indicadores_villamaria.json")
_CIUDAD = "Villa María"

# Estados de un requisito en la pestaña de elegibilidad
_ESTADOS_REQ = {
    "cumple":  ("Cumple",    "#2e7d32", 1.0),
    "parcial": ("Parcial",   "#f57c00", 0.5),
    "falta":   ("Falta",     "#c62828", 0.0),
    "sin_dato": ("Sin cargar", "#9e9e9e", 0.0),
}

# Colores por estado (misma paleta de semáforo que el resto de la app)
_COLOR_ESTADO = {
    "viable_hoy":       "#2e7d32",
    "requiere_gestion": "#f57c00",
    "traba_temporal":   "#9e9e9e",
}
_ICONO_CATEGORIA = {
    "directa":       "🏛️",
    "provincia":     "🗺️",
    "nacion":        "🇦🇷",
    "internacional": "🌍",
    "mercado":       "🌳",
}


@st.cache_data(show_spinner=False)
def cargar_catalogo() -> dict:
    """Carga el catálogo de fuentes de financiamiento."""
    with open(_RUTA_CATALOGO, encoding="utf-8") as f:
        return json.load(f)


def _badge(texto: str, color: str) -> str:
    return (
        f"<span style='display:inline-block;background:{color}22;border:1px solid {color}88;"
        f"color:{color};border-radius:6px;padding:2px 8px;font-size:0.78em;"
        f"font-weight:600;margin-right:6px;'>{texto}</span>"
    )


def _render_fuente(fuente: dict, catalogo: dict):
    """Ficha de una fuente de financiamiento."""
    estado_txt = catalogo["estados"].get(fuente["estado"], fuente["estado"])
    cat_txt    = catalogo["categorias"].get(fuente["categoria"], fuente["categoria"])
    color      = _COLOR_ESTADO.get(fuente["estado"], "#9e9e9e")
    icono      = _ICONO_CATEGORIA.get(fuente["categoria"], "•")

    with st.expander(f"{icono} {fuente['nombre']}"):
        st.markdown(
            _badge(estado_txt, color)
            + _badge("Genera deuda" if fuente["es_deuda"] else "No genera deuda",
                     "#c62828" if fuente["es_deuda"] else "#2e7d32")
            + _badge(cat_txt, "#00b4dc"),
            unsafe_allow_html=True,
        )
        st.markdown(fuente["descripcion"])

        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**Autorización requerida**  \n{fuente['autorizacion']}")
            st.markdown(f"**Montos y plazos**  \n{fuente['montos_plazos']}")
        with c2:
            st.markdown(f"**Precedente**  \n{fuente['precedente']}")
            st.markdown("**Usos en el Masterplan**  \n" + " · ".join(fuente["usos_masterplan"]))

        st.markdown("**Requisitos**")
        for r in fuente["requisitos"]:
            quien = "📊 Plataforma" if r["evalua"] == "plataforma" else "🏛️ Municipio"
            st.markdown(f"- {r['texto']} — *{quien}*")

        st.markdown("**Fuentes**")
        for ref in fuente["referencias"]:
            st.markdown(f"- [{ref['titulo']}]({ref['url']})")


def _render_catalogo(catalogo: dict):
    st.caption(
        f"{len(catalogo['fuentes'])} fuentes · verificado el {catalogo['fecha_verificacion']} · "
        "incluye vías que hoy no son viables"
    )

    c1, c2, c3 = st.columns([2, 2, 1])
    with c1:
        cats = st.multiselect(
            "Categoría",
            options=list(catalogo["categorias"].keys()),
            format_func=lambda k: catalogo["categorias"][k],
            key="bv_filtro_categoria",
        )
    with c2:
        estados = st.multiselect(
            "Estado",
            options=list(catalogo["estados"].keys()),
            format_func=lambda k: catalogo["estados"][k],
            key="bv_filtro_estado",
        )
    with c3:
        sin_deuda = st.checkbox("Solo sin deuda", key="bv_filtro_sin_deuda")

    fuentes = [
        f for f in catalogo["fuentes"]
        if (not cats or f["categoria"] in cats)
        and (not estados or f["estado"] in estados)
        and (not sin_deuda or not f["es_deuda"])
    ]

    if not fuentes:
        st.info("Ninguna fuente coincide con los filtros.")
        return

    for cat_key, cat_txt in catalogo["categorias"].items():
        grupo = [f for f in fuentes if f["categoria"] == cat_key]
        if not grupo:
            continue
        st.markdown(f"#### {_ICONO_CATEGORIA.get(cat_key, '')} {cat_txt}")
        for f in grupo:
            _render_fuente(f, catalogo)


def _render_marco_legal(catalogo: dict):
    st.info(
        "Toda deuda municipal requiere autorización nacional (Ley 25.917). "
        "El BCRA interviene solo si la deuda es en moneda extranjera. "
        "Las vías sin endeudamiento son las únicas de gestión directa."
    )
    for m in catalogo["marco_legal"]:
        st.markdown(f"**{m['titulo']}**  \n{m['descripcion']}  \n[Ver fuente]({m['url']})")
    st.caption(catalogo["nota"])


# ============================================================
# ELEGIBILIDAD VILLA MARÍA
# ============================================================

@st.cache_data(show_spinner=False)
def _cargar_indicadores() -> dict:
    """Indicadores reales de Villa María (exportar_indicadores_villamaria.py)."""
    if not os.path.exists(_RUTA_INDICADORES):
        return {}
    with open(_RUTA_INDICADORES, encoding="utf-8") as f:
        return json.load(f)


def _valor_indicador(indicadores: dict, ruta: str):
    """Busca un valor por ruta con puntos, ej. 'cobertura.arboles'. None si no existe."""
    v = indicadores
    for clave in (ruta or "").split("."):
        if not isinstance(v, dict):
            return None
        v = v.get(clave)
    return v


def _evaluar_requisito(req: dict, indicadores: dict, cargados: dict) -> dict:
    """Devuelve estado, valor y fuente de un requisito.
    Plataforma: cumple si el dato real existe. Municipio: lo que cargó el admin."""
    if req["evalua"] == "plataforma":
        v = _valor_indicador(indicadores, req.get("indicador"))
        if v is None:
            return {"estado": "falta", "valor": "Sin dato calculado", "fuente": ""}
        fecha = (indicadores.get("fecha_calculo") or "")[:10]
        valor = f"{v:,}".replace(",", ".") if isinstance(v, int) else str(v).replace(".", ",")
        return {
            "estado": "cumple",
            "valor": f"{valor} {req.get('unidad') or ''}".strip(),
            "fuente": f"Ciudad Verde · indicadores_villamaria.json ({fecha})",
        }
    fila = cargados.get(req["id"])
    if not fila:
        return {"estado": "sin_dato", "valor": "", "fuente": ""}
    return {
        "estado": fila.get("estado") or "sin_dato",
        "valor": fila.get("valor") or "",
        "fuente": fila.get("fuente") or "",
        "usuario": fila.get("usuario"),
        "fecha": fila.get("fecha"),
    }


def _form_requisito_admin(req: dict, actual: dict):
    """Formulario del admin para cargar un requisito del municipio."""
    opciones = ["cumple", "parcial", "falta"]
    estado_actual = actual["estado"] if actual["estado"] in opciones else "falta"
    with st.form(key=f"bv_form_{req['id']}"):
        estado = st.selectbox(
            "Estado", opciones, index=opciones.index(estado_actual),
            format_func=lambda k: _ESTADOS_REQ[k][0], key=f"bv_estado_{req['id']}",
        )
        valor = st.text_input("Valor o detalle", value=actual.get("valor", ""),
                              key=f"bv_valor_{req['id']}")
        fuente = st.text_input("Fuente que lo respalda (documento, norma, enlace)",
                               value=actual.get("fuente", ""), key=f"bv_fuente_{req['id']}")
        if st.form_submit_button("Guardar"):
            if not fuente.strip():
                st.warning("Indicá la fuente que respalda el dato.")
            else:
                usuario = st.session_state.get("cv_usuario", "admin")
                if guardar_requisito(_CIUDAD, req["id"], estado, valor, fuente, usuario):
                    st.rerun()
                else:
                    st.error("No se pudo guardar. Revisá la conexión a la base.")


def _render_elegibilidad(catalogo: dict):
    es_admin = bool(st.session_state.get("cv_admin_auth"))
    indicadores = _cargar_indicadores()
    cargados = obtener_requisitos(_CIUDAD)

    st.caption(
        "📊 Requisitos de plataforma: se cumplen cuando existe el dato real calculado. "
        "🏛️ Requisitos del municipio: los carga el administrador con la fuente que los respalda."
    )
    if es_admin:
        st.info("🔐 Modo administrador: podés cargar los requisitos del municipio.")

    # Evaluar todas las fuentes y ordenar de más cerca a más lejos de ser viables
    evaluadas = []
    for f in catalogo["fuentes"]:
        evals = [(r, _evaluar_requisito(r, indicadores, cargados)) for r in f["requisitos"]]
        puntos = sum(_ESTADOS_REQ[e["estado"]][2] for _, e in evals)
        n_cumple = sum(1 for _, e in evals if e["estado"] == "cumple")
        avance = puntos / len(evals) if evals else 0
        evaluadas.append((f, evals, n_cumple, avance))
    evaluadas.sort(key=lambda x: x[3], reverse=True)

    for f, evals, n_cumple, avance in evaluadas:
        color = "#2e7d32" if avance >= 0.99 else "#f57c00" if avance >= 0.5 else "#c62828"
        icono = _ICONO_CATEGORIA.get(f["categoria"], "•")
        with st.expander(f"{icono} {f['nombre']} — {n_cumple} de {len(evals)} requisitos cumplidos"):
            st.markdown(
                _badge(f"Avance {avance * 100:.0f} %", color)
                + _badge(catalogo["estados"].get(f["estado"], f["estado"]),
                         _COLOR_ESTADO.get(f["estado"], "#9e9e9e")),
                unsafe_allow_html=True,
            )
            for r, e in evals:
                txt, col, _ = _ESTADOS_REQ[e["estado"]]
                quien = "📊 Plataforma" if r["evalua"] == "plataforma" else "🏛️ Municipio"
                detalle = f" · {e['valor']}" if e.get("valor") else ""
                st.markdown(
                    _badge(txt, col) + f"**{r['texto']}** — *{quien}*{detalle}",
                    unsafe_allow_html=True,
                )
                if e.get("fuente"):
                    st.caption(f"Fuente: {e['fuente']}")
                if es_admin and r["evalua"] == "municipio":
                    _form_requisito_admin(r, e)


def render_bonos_verdes():
    """Punto de entrada del módulo."""
    st.title("💚 Bonos Verdes y Financiamiento")
    st.caption("Opciones para financiar y ejecutar el Masterplan de Villa María")

    try:
        catalogo = cargar_catalogo()
    except Exception as e:
        st.error(f"No se pudo leer el catálogo de fuentes: {e}")
        return

    tab_cat, tab_eleg, tab_legal = st.tabs(
        ["📚 Catálogo de fuentes", "✅ Elegibilidad Villa María", "⚖️ Marco legal y fuentes"]
    )
    with tab_cat:
        _render_catalogo(catalogo)
    with tab_eleg:
        _render_elegibilidad(catalogo)
    with tab_legal:
        _render_marco_legal(catalogo)
