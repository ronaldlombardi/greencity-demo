"""
modulo_asistente.py — Ciudad Verde AI Agent
============================================
Panel de Ayuda contextual persistente — sin llamadas a modelos de IA.
- Botón en sidebar togglea el panel (no se cierra con st.rerun)
- Buscador por texto libre sobre toda la base de conocimiento
- Navegación por categorías (secciones de la app)
- Contenido estático definido en ayuda_contenido.py
"""

import streamlit as st
from ayuda_contenido import AYUDA, CATEGORIAS_ORDEN, buscar, por_categoria

# ── CSS del panel ─────────────────────────────────────────
_CSS_PANEL = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600&family=Space+Mono:wght@400;700&display=swap');

.cv-ayuda-panel {
    background: rgba(6,10,24,0.97);
    border: 0.5px solid rgba(0,180,220,0.28);
    border-radius: 14px;
    padding: 24px 28px;
    margin-bottom: 24px;
    font-family: 'Space Grotesk', sans-serif;
}
.cv-ayuda-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-bottom: 14px;
    border-bottom: 0.5px solid rgba(120,140,255,0.18);
    margin-bottom: 18px;
}
.cv-ayuda-titulo {
    font-family: 'Space Mono', monospace;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.08em;
    color: #c8d8f8;
}
.cv-ayuda-sub {
    font-family: 'Space Mono', monospace;
    font-size: 10px;
    color: rgba(0,180,220,0.65);
    letter-spacing: 0.07em;
    margin-top: 3px;
}
.cv-ayuda-card {
    background: rgba(10,18,42,0.75);
    border: 0.5px solid rgba(0,180,220,0.18);
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 12px;
}
.cv-ayuda-card-cat {
    font-family: 'Space Mono', monospace;
    font-size: 10px;
    letter-spacing: 0.10em;
    text-transform: uppercase;
    color: rgba(0,180,220,0.65);
    margin-bottom: 6px;
}
.cv-ayuda-card-titulo {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 16px;
    font-weight: 600;
    color: #e8eeff;
    margin-bottom: 10px;
}
.cv-ayuda-card-texto {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 14px;
    color: #b8cce0;
    line-height: 1.75;
    white-space: pre-line;
}
.cv-ayuda-label {
    font-family: 'Space Mono', monospace;
    font-size: 9px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: rgba(160,175,210,0.5);
    margin-bottom: 7px;
    margin-top: 14px;
}
.cv-ayuda-resultado-info {
    font-family: 'Space Mono', monospace;
    font-size: 10px;
    color: rgba(0,180,220,0.65);
    letter-spacing: 0.08em;
    margin-bottom: 14px;
}
.cv-ayuda-vacio {
    background: rgba(10,18,38,0.5);
    border: 0.5px solid rgba(120,140,255,0.14);
    border-radius: 10px;
    padding: 36px 22px;
    text-align: center;
}
.cv-ayuda-vacio-titulo {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 15px;
    font-weight: 600;
    color: #c0d0f0;
    margin: 10px 0 8px 0;
}
.cv-ayuda-vacio-sub {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 13px;
    color: rgba(170,185,220,0.6);
    line-height: 1.6;
}
.cv-ayuda-rapidos-titulo {
    font-family: 'Space Mono', monospace;
    font-size: 9px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: rgba(160,175,210,0.45);
    margin: 18px 0 10px 0;
}
</style>
"""


def _render_entrada(entrada: dict):
    """Renderiza una entrada de ayuda como card."""
    st.markdown(
        f"""<div class="cv-ayuda-card">
          <div class="cv-ayuda-card-cat">{entrada['categoria']}</div>
          <div class="cv-ayuda-card-titulo">{entrada['titulo']}</div>
          <div class="cv-ayuda-card-texto">{entrada['texto']}</div>
        </div>""",
        unsafe_allow_html=True,
    )


def _render_panel_ayuda():
    """Contenido completo del panel de ayuda — persistente en el área principal."""
    st.markdown(_CSS_PANEL, unsafe_allow_html=True)

    # ── Header con botón cerrar ───────────────────────────
    col_titulo, col_cerrar = st.columns([8, 1])
    with col_titulo:
        st.markdown(
            """<div class="cv-ayuda-header">
              <div>
                <div class="cv-ayuda-titulo">❓ Ayuda — Base de conocimiento · Ciudad Verde AI Agent</div>
                <div class="cv-ayuda-sub">Glosario de indicadores, fuentes y marcos normativos de la plataforma</div>
              </div>
            </div>""",
            unsafe_allow_html=True,
        )
    with col_cerrar:
        if st.button("✕ Cerrar", key="ayuda_cerrar_top", use_container_width=True):
            st.session_state["cv_ayuda_abierta"] = False
            st.rerun()

    # ── Layout: nav izquierda | contenido derecha ─────────
    col_nav, col_cont = st.columns([1, 2], gap="large")

    with col_nav:
        st.markdown('<div class="cv-ayuda-label">Buscar</div>', unsafe_allow_html=True)
        query = st.text_input(
            "Buscar término",
            placeholder="ej: NDVI, isla de calor, OMS...",
            label_visibility="collapsed",
            key="ayuda_query",
        )

        st.markdown('<div class="cv-ayuda-label">Categorías</div>', unsafe_allow_html=True)

        for cat in CATEGORIAS_ORDEN:
            n = len(por_categoria(cat))
            activa = st.session_state.get("ayuda_cat_activa") == cat
            btn_label = f"{'▶ ' if activa else ''}{cat}  ({n})"
            if st.button(btn_label, key=f"ayuda_cat_{cat}", use_container_width=True):
                st.session_state["ayuda_cat_activa"] = cat
                st.rerun()

        if query or st.session_state.get("ayuda_cat_activa"):
            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
            if st.button("✕ Limpiar filtro", key="ayuda_limpiar", use_container_width=True):
                st.session_state.pop("ayuda_cat_activa", None)
                st.rerun()

    with col_cont:
        # ── Modo búsqueda ──────────────────────────────────
        if query and query.strip():
            resultados = buscar(query)
            st.markdown(
                f'<div class="cv-ayuda-resultado-info">// {len(resultados)} resultado(s) para «{query}»</div>',
                unsafe_allow_html=True,
            )
            if resultados:
                for entrada in resultados:
                    _render_entrada(entrada)
            else:
                st.markdown(
                    '<div style="font-family:\'Space Grotesk\',sans-serif;font-size:14px;'
                    'color:rgba(180,190,220,0.5);padding:28px 0;text-align:center;">'
                    'No se encontraron resultados. Probá con otro término.</div>',
                    unsafe_allow_html=True,
                )

        # ── Modo categoría ─────────────────────────────────
        elif st.session_state.get("ayuda_cat_activa"):
            cat = st.session_state["ayuda_cat_activa"]
            entradas = por_categoria(cat)
            st.markdown(
                f'<div class="cv-ayuda-resultado-info">// {cat} — {len(entradas)} artículo(s)</div>',
                unsafe_allow_html=True,
            )
            for entrada in entradas:
                _render_entrada(entrada)

        # ── Estado inicial ─────────────────────────────────
        else:
            st.markdown(
                '<div class="cv-ayuda-vacio">'
                '<div style="font-size:2em;">📖</div>'
                '<div class="cv-ayuda-vacio-titulo">Glosario de Ciudad Verde</div>'
                '<div class="cv-ayuda-vacio-sub">Usá el buscador o seleccioná una categoría<br>'
                'para explorar los conceptos de la plataforma.</div>'
                '</div>',
                unsafe_allow_html=True,
            )

            st.markdown('<div class="cv-ayuda-rapidos-titulo">Más consultados</div>', unsafe_allow_html=True)

            rapidos = [
                "ESA WorldCover 2020",
                "NDVI — Índice de Vegetación",
                "Isla de calor urbano (UHI / ΔT)",
                "OMS — Estándares de verde urbano",
                "C40 — Urban Nature Declaration 2030",
                "Sistema de calificación A-F",
            ]
            col_r1, col_r2 = st.columns(2)
            for i, titulo in enumerate(rapidos):
                col = col_r1 if i % 2 == 0 else col_r2
                with col:
                    if st.button(titulo, key=f"ayuda_rapido_{i}", use_container_width=True):
                        entrada = next((e for e in AYUDA if e["titulo"] == titulo), None)
                        if entrada:
                            st.session_state["ayuda_entrada_rapida"] = entrada
                            st.rerun()

            if "ayuda_entrada_rapida" in st.session_state:
                st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
                _render_entrada(st.session_state.pop("ayuda_entrada_rapida"))

    st.markdown(
        "<div style='height:0.5px;background:rgba(0,180,220,0.14);margin:20px 0 0 0;'></div>",
        unsafe_allow_html=True,
    )


def render_asistente_sidebar():
    """Botón toggle en el sidebar — abre/cierra el panel persistente."""
    st.markdown("---")
    abierta = st.session_state.get("cv_ayuda_abierta", False)
    label   = "✕  Cerrar ayuda" if abierta else "❓  Ayuda"
    if st.button(label, key="cv_toggle_ayuda", use_container_width=True):
        st.session_state["cv_ayuda_abierta"] = not abierta
        st.rerun()


def render_asistente_panel():
    """Renderiza el panel en el área principal si está abierto."""
    if st.session_state.get("cv_ayuda_abierta", False):
        _render_panel_ayuda()
