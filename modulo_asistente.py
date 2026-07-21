"""
modulo_asistente.py — Ciudad Verde AI Agent
============================================
Panel de Ayuda contextual — sin llamadas a modelos de IA.
- Buscador por texto libre sobre toda la base de conocimiento
- Navegación por categorías (secciones de la app)
- Contenido estático definido en ayuda_contenido.py
"""

import streamlit as st
from ayuda_contenido import AYUDA, CATEGORIAS_ORDEN, buscar, por_categoria

# CSS del dialog
_CSS_DIALOG = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600&family=Space+Mono:wght@400;700&display=swap');

div[data-testid="stDialog"] > div {
    background: rgba(5,8,16,0.98) !important;
    border: 0.5px solid rgba(120,140,255,0.30) !important;
    border-radius: 14px !important;
    box-shadow: 0 8px 60px rgba(0,0,0,0.7) !important;
    max-width: 860px !important;
    width: 92vw !important;
}

div[data-testid="stDialog"] .stMarkdown p,
div[data-testid="stDialog"] .stMarkdown li {
    font-family: 'Space Grotesk', sans-serif !important;
    color: #dde3f5 !important;
    font-size: 13px !important;
    line-height: 1.7 !important;
}

div[data-testid="stDialog"] .stTextInput > div > div > input {
    background: rgba(8,12,28,0.90) !important;
    border: 0.5px solid rgba(120,140,255,0.35) !important;
    border-radius: 8px !important;
    color: #fff !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: 13px !important;
}
div[data-testid="stDialog"] .stTextInput > div > div > input:focus {
    border-color: #00b4dc !important;
    box-shadow: 0 0 0 1px rgba(0,180,220,0.3) !important;
}

div[data-testid="stDialog"] .stButton > button {
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: 11px !important;
    font-weight: 500 !important;
    border-radius: 7px !important;
    transition: all 0.2s !important;
    text-align: left !important;
    background: rgba(0,140,180,0.10) !important;
    border: 0.5px solid rgba(0,180,220,0.22) !important;
    color: #c0d8ec !important;
    padding: 5px 10px !important;
}
div[data-testid="stDialog"] .stButton > button:hover {
    background: rgba(0,140,180,0.24) !important;
    border-color: rgba(0,180,220,0.45) !important;
    color: #e0f0ff !important;
}
</style>
"""

# ── Helpers de render ─────────────────────────────────────

def _render_entrada(entrada: dict):
    """Renderiza una entrada de ayuda como card."""
    st.markdown(
        f"""<div style="
            background:rgba(10,18,38,0.72);
            border:0.5px solid rgba(0,180,220,0.18);
            border-radius:10px;
            padding:14px 18px;
            margin-bottom:10px;">
          <div style="
              font-family:'Space Mono',monospace;
              font-size:8px;letter-spacing:0.12em;
              text-transform:uppercase;
              color:rgba(0,180,220,0.6);
              margin-bottom:5px;">
            {entrada['categoria']}
          </div>
          <div style="
              font-family:'Space Grotesk',sans-serif;
              font-size:14px;font-weight:600;
              color:#e8eeff;margin-bottom:8px;">
            {entrada['titulo']}
          </div>
          <div style="
              font-family:'Space Grotesk',sans-serif;
              font-size:12.5px;color:#b8c8e0;
              line-height:1.72;
              white-space:pre-line;">
            {entrada['texto']}
          </div>
        </div>""",
        unsafe_allow_html=True,
    )


def _label_cat(cat: str) -> str:
    """Devuelve la etiqueta corta de categoría (sin emoji para selectbox)."""
    return cat


@st.dialog("❓ Ayuda — Ciudad Verde", width="large")
def _dialog_ayuda():
    """Panel de ayuda contextual."""
    st.markdown(_CSS_DIALOG, unsafe_allow_html=True)

    # ── Header ────────────────────────────────────────────
    st.markdown(
        """<div style="padding-bottom:12px;border-bottom:0.5px solid rgba(120,140,255,0.16);
                       margin-bottom:14px;">
          <div style="font-family:'Space Mono',monospace;font-size:11px;font-weight:700;
               letter-spacing:0.08em;color:#c0d0f0;">
            Base de conocimiento · Ciudad Verde AI Agent
          </div>
          <div style="font-family:'Space Mono',monospace;font-size:9px;
               color:rgba(0,180,220,0.65);letter-spacing:0.07em;margin-top:3px;">
            Glosario de indicadores, fuentes y marcos normativos de la plataforma
          </div>
        </div>""",
        unsafe_allow_html=True,
    )

    # ── Layout: categorías izquierda | contenido derecha ──
    col_nav, col_cont = st.columns([1, 2], gap="medium")

    with col_nav:
        # Buscador
        st.markdown(
            "<div style='font-family:\"Space Mono\",monospace;font-size:8px;"
            "letter-spacing:0.12em;text-transform:uppercase;"
            "color:rgba(160,175,210,0.5);margin-bottom:6px;'>Buscar</div>",
            unsafe_allow_html=True,
        )
        query = st.text_input(
            "Buscar término",
            placeholder="ej: NDVI, isla de calor, OMS...",
            label_visibility="collapsed",
            key="ayuda_query",
        )

        st.markdown(
            "<div style='font-family:\"Space Mono\",monospace;font-size:8px;"
            "letter-spacing:0.12em;text-transform:uppercase;"
            "color:rgba(160,175,210,0.5);margin:12px 0 6px 0;'>Categorías</div>",
            unsafe_allow_html=True,
        )

        # Botones de categoría
        for cat in CATEGORIAS_ORDEN:
            n = len(por_categoria(cat))
            if st.button(
                f"{cat}  ({n})",
                key=f"ayuda_cat_{cat}",
                use_container_width=True,
            ):
                st.session_state["ayuda_cat_activa"] = cat
                st.rerun()

        # Botón limpiar
        if query or st.session_state.get("ayuda_cat_activa"):
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            if st.button("✕ Limpiar filtro", key="ayuda_limpiar", use_container_width=True):
                st.session_state.pop("ayuda_cat_activa", None)
                st.rerun()

    with col_cont:
        # ── Modo búsqueda ──────────────────────────────────
        if query and query.strip():
            resultados = buscar(query)
            st.markdown(
                f"<div style='font-family:\"Space Mono\",monospace;font-size:9px;"
                f"color:rgba(0,180,220,0.65);letter-spacing:0.08em;margin-bottom:12px;'>"
                f"// {len(resultados)} resultado(s) para «{query}»</div>",
                unsafe_allow_html=True,
            )
            if resultados:
                for entrada in resultados:
                    _render_entrada(entrada)
            else:
                st.markdown(
                    "<div style='font-family:\"Space Grotesk\",sans-serif;font-size:13px;"
                    "color:rgba(180,190,220,0.5);padding:24px 0;text-align:center;'>"
                    "No se encontraron resultados. Probá con otro término.</div>",
                    unsafe_allow_html=True,
                )

        # ── Modo categoría ─────────────────────────────────
        elif st.session_state.get("ayuda_cat_activa"):
            cat = st.session_state["ayuda_cat_activa"]
            entradas = por_categoria(cat)
            st.markdown(
                f"<div style='font-family:\"Space Mono\",monospace;font-size:9px;"
                f"color:rgba(0,180,220,0.65);letter-spacing:0.08em;margin-bottom:12px;'>"
                f"// {cat} — {len(entradas)} artículo(s)</div>",
                unsafe_allow_html=True,
            )
            for entrada in entradas:
                _render_entrada(entrada)

        # ── Estado inicial ─────────────────────────────────
        else:
            st.markdown(
                """<div style="
                    background:rgba(10,18,38,0.5);
                    border:0.5px solid rgba(120,140,255,0.14);
                    border-radius:10px;padding:28px 22px;text-align:center;">
                  <div style="font-size:1.8em;margin-bottom:10px;">📖</div>
                  <div style="font-family:'Space Grotesk',sans-serif;font-size:13px;
                       font-weight:600;color:#c0d0f0;margin-bottom:6px;">
                    Glosario de Ciudad Verde
                  </div>
                  <div style="font-family:'Space Grotesk',sans-serif;font-size:12px;
                       color:rgba(170,185,220,0.6);line-height:1.6;">
                    Usá el buscador o seleccioná una categoría<br>
                    para explorar los conceptos de la plataforma.
                  </div>
                </div>""",
                unsafe_allow_html=True,
            )

            # Accesos rápidos
            st.markdown(
                "<div style='font-family:\"Space Mono\",monospace;font-size:8px;"
                "letter-spacing:0.12em;text-transform:uppercase;"
                "color:rgba(160,175,210,0.45);margin:16px 0 8px 0;'>Más consultados</div>",
                unsafe_allow_html=True,
            )
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
                        # Buscar por título exacto
                        entrada = next((e for e in AYUDA if e["titulo"] == titulo), None)
                        if entrada:
                            st.session_state["ayuda_entrada_rapida"] = entrada
                            st.rerun()

            # Mostrar entrada rápida si fue seleccionada
            if "ayuda_entrada_rapida" in st.session_state:
                st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
                _render_entrada(st.session_state.pop("ayuda_entrada_rapida"))


def render_asistente_sidebar():
    """Botón compacto en el sidebar que abre el panel de ayuda."""
    st.markdown("---")
    st.markdown(
        """<div style="display:flex;align-items:center;gap:8px;margin-bottom:7px;">
          <div style="font-family:'Space Mono',monospace;font-size:8px;
               color:rgba(0,180,220,0.70);letter-spacing:0.07em;">
            ● AYUDA · DOCUMENTACIÓN
          </div>
        </div>""",
        unsafe_allow_html=True,
    )
    if st.button("❓  Ayuda", key="cv_open_ayuda", use_container_width=True):
        _dialog_ayuda()


def render_asistente_panel():
    """Compatibilidad con app.py — no inyecta nada."""
    pass
