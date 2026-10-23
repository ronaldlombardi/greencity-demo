"""
modulo_bonos_verdes.py — Ciudad Verde AI Agent
===============================================
Bonos Verdes y Financiamiento del Masterplan.

Lee data/fuentes_financiamiento.json (catálogo verificado con fuentes).
Pestañas:
  1. Catálogo de fuentes  — todas las vías, viables hoy o no
  2. Marco legal y fuentes — Ley 25.917, BCRA, CNV y referencias
"""

import os
import json
import streamlit as st

_RUTA_CATALOGO = os.path.join(os.path.dirname(__file__), "data", "fuentes_financiamiento.json")

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


def render_bonos_verdes():
    """Punto de entrada del módulo."""
    st.title("💚 Bonos Verdes y Financiamiento")
    st.caption("Opciones para financiar y ejecutar el Masterplan de Villa María")

    try:
        catalogo = cargar_catalogo()
    except Exception as e:
        st.error(f"No se pudo leer el catálogo de fuentes: {e}")
        return

    tab_cat, tab_legal = st.tabs(["📚 Catálogo de fuentes", "⚖️ Marco legal y fuentes"])
    with tab_cat:
        _render_catalogo(catalogo)
    with tab_legal:
        _render_marco_legal(catalogo)
