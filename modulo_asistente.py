"""
modulo_asistente.py — Ciudad Verde AI Agent
============================================
Asistente IA con Claude Haiku.
- Sidebar: botón compacto + indicador de estado
- Panel: st.dialog nativo de Streamlit (funciona siempre)
- Llamada a Haiku via Python puro (sin CORS)
- Registra consumo en PostgreSQL
"""

import os
import requests
import streamlit as st
from modulo_db import registrar_consumo

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
API_URL           = "https://api.anthropic.com/v1/messages"
MODEL             = "claude-haiku-4-5-20251001"

SYSTEM_PROMPT = """Sos el asistente de Ciudad Verde AI Agent, plataforma de análisis ambiental
de espacios verdes urbanos en la Provincia de Córdoba, Argentina.

Datos reales de Villa María:
- Cobertura arbórea: 8.2% (ESA WorldCover 2020, 10m)
- Pastizales: 14.2% | Cultivos urbanos: 23.9% | Edificado: 50.6% | Agua: 1.3%
- Acceso verde <300m: 100% del área edificada (cumple OMS)
- Distancia promedio al verde: 48 metros
- Verde público/hab (OSM): 65.4 m²/hab (OMS mínimo: 9 m²/hab ✅)
- Verde satelital/hab: 93.2 m²/hab
- Temperatura superficial media: 39.97°C (Landsat 8/9, 13 imágenes)
- Isla de calor ΔT: +0.17°C (muy baja)
- Enfriamiento potencial: 1.67°C/ha arbolada
- Zona más caliente: Noroeste VM centro-norte (40.76°C)
- CO₂ capturado: ~556 ton CO₂/año (USDA Forest Service, Nowak 2013)
- Población Villa María: ~97.000 hab | Villa Nueva: ~23.000 hab
- Área analizada: 49.6 km² (conglomerado VM + VN)
- Calificación: A - Excelente (7/7 puntos)
- Río Ctalamochita: corredor ecológico entre VM y VN

Fuentes: ESA WorldCover 2020 · Landsat 8/9 (GEE) · OpenStreetMap · INDEC Censo 2022
         USDA Forest Service / Nowak et al. 2013

Marcos: OMS · ODS 11 · C40 Urban Nature 2030 · Acuerdo de París · Ordenanza 7209/2017

Respondé en español, claro y conciso, máximo 4 párrafos.
Texto plano sin ** ni ##. Orientado a funcionarios municipales."""

SUGERENCIAS = [
    "¿Qué es el NDVI?",
    "¿Qué es la isla de calor ΔT?",
    "¿De dónde vienen los datos de temperatura?",
    "¿Cómo se calcula la captura de CO₂?",
    "¿Qué es ESA WorldCover?",
    "¿Por qué se incluye Villa Nueva?",
    "¿Qué es el estándar C40?",
    "¿Qué es la Ordenanza 7209?",
]

# CSS del dialog estilo dark tech
_CSS_DIALOG = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600&family=Space+Mono:wght@400;700&display=swap');

/* Dialog overlay oscuro */
div[data-testid="stDialog"] > div {
    background: rgba(5,8,16,0.98) !important;
    border: 0.5px solid rgba(120,140,255,0.30) !important;
    border-radius: 14px !important;
    box-shadow: 0 8px 60px rgba(0,0,0,0.7) !important;
    max-width: 820px !important;
    width: 90vw !important;
}

/* Contenido del dialog */
div[data-testid="stDialog"] .stMarkdown p {
    font-family: 'Space Grotesk', sans-serif !important;
    color: #dde3f5 !important;
    font-size: 13px !important;
    line-height: 1.7 !important;
}

/* Input dentro del dialog */
div[data-testid="stDialog"] .stTextInput > div > div > input {
    background: rgba(8,12,28,0.90) !important;
    border: 0.5px solid rgba(120,140,255,0.30) !important;
    border-radius: 8px !important;
    color: #fff !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: 13px !important;
}
div[data-testid="stDialog"] .stTextInput > div > div > input:focus {
    border-color: #9060ff !important;
    box-shadow: 0 0 0 1px rgba(144,96,255,0.3) !important;
}

/* Botones dentro del dialog */
div[data-testid="stDialog"] .stButton > button {
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    border-radius: 7px !important;
    transition: all 0.2s !important;
}

/* Chips de sugerencias */
div[data-testid="stDialog"] .stButton > button[kind="secondary"] {
    background: rgba(99,40,180,0.12) !important;
    border: 0.5px solid rgba(120,80,200,0.25) !important;
    color: #c0ccec !important;
    font-size: 11px !important;
    padding: 5px 10px !important;
    text-align: left !important;
}
div[data-testid="stDialog"] .stButton > button[kind="secondary"]:hover {
    background: rgba(99,40,180,0.26) !important;
    border-color: rgba(144,96,255,0.42) !important;
    color: #e0d8ff !important;
}
</style>
"""


def _consultar_haiku(pregunta: str) -> str:
    """Llama a Claude Haiku via Python. Registra consumo en Postgres."""
    if not ANTHROPIC_API_KEY:
        return "⚠️ ANTHROPIC_API_KEY no configurada en Railway → Variables."
    headers = {
        "x-api-key":         ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type":      "application/json",
    }
    payload = {
        "model":      MODEL,
        "max_tokens": 800,
        "system":     SYSTEM_PROMPT,
        "messages":   [{"role": "user", "content": pregunta}],
    }
    try:
        r = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        r.raise_for_status()
        data    = r.json()
        texto   = data["content"][0]["text"]
        tok_in  = data.get("usage", {}).get("input_tokens",  0)
        tok_out = data.get("usage", {}).get("output_tokens", 0)
        registrar_consumo(
            usuario=st.session_state.get("cv_usuario", "usuarioverde"),
            tipo="haiku",
            pregunta=pregunta,
            tok_input=tok_in,
            tok_output=tok_out,
            modelo=MODEL,
        )
        return texto
    except requests.exceptions.Timeout:
        return "⚠️ Tiempo de espera agotado. Intentá de nuevo."
    except Exception as e:
        return f"⚠️ Error: {str(e)}"


@st.dialog("🤖 Asistente IA — Ciudad Verde", width="large")
def _dialog_asistente():
    """Contenido del dialog del asistente."""
    st.markdown(_CSS_DIALOG, unsafe_allow_html=True)

    # Header con orbe
    col_orb, col_info, col_close = st.columns([1, 6, 1])
    with col_orb:
        st.markdown(
            """<div style="width:36px;height:36px;border-radius:50%;margin-top:4px;
               background:radial-gradient(circle at 35% 35%,#a060ff,#3010a0 60%,#050810);
               box-shadow:0 0 18px rgba(100,40,200,0.6);
               animation:orb-d 3s ease-in-out infinite;">
            </div>
            <style>@keyframes orb-d{
              0%,100%{box-shadow:0 0 18px rgba(100,40,200,0.5);}
              50%{box-shadow:0 0 32px rgba(100,40,200,0.8);}
            }</style>""",
            unsafe_allow_html=True,
        )
    with col_info:
        st.markdown(
            """<div style="padding-top:2px;">
              <div style="font-family:'Space Mono',monospace;font-size:12px;
                   font-weight:700;color:#c0b0f0;letter-spacing:0.05em;">
                Asistente Ciudad Verde</div>
              <div style="font-family:'Space Mono',monospace;font-size:9px;
                   color:rgba(64,220,144,0.75);letter-spacing:0.07em;margin-top:2px;">
                ● CLAUDE HAIKU · EN LÍNEA · Preguntá sobre datos, indicadores y metodología
              </div>
            </div>""",
            unsafe_allow_html=True,
        )

    st.markdown(
        "<div style='height:0.5px;background:rgba(120,140,255,0.18);margin:10px 0 14px 0;'></div>",
        unsafe_allow_html=True,
    )

    # Layout: sugerencias izquierda | respuesta derecha
    col_sug, col_resp = st.columns([1, 2])

    with col_sug:
        st.markdown(
            "<div style='font-family:\"Space Mono\",monospace;font-size:8px;"
            "letter-spacing:0.12em;text-transform:uppercase;"
            "color:rgba(160,175,210,0.45);margin-bottom:8px;'>Preguntas frecuentes</div>",
            unsafe_allow_html=True,
        )
        for i, sug in enumerate(SUGERENCIAS):
            if st.button(sug, key=f"dlg_sug_{i}", use_container_width=True):
                with st.spinner("Consultando…"):
                    st.session_state["cv_ai_resp"] = _consultar_haiku(sug)
                st.rerun()

    with col_resp:
        # Caja de respuesta
        if "cv_ai_resp" in st.session_state:
            resp = st.session_state["cv_ai_resp"]
            st.markdown(
                f"""<div style="background:rgba(10,14,32,0.7);
                    border:0.5px solid rgba(120,140,255,0.20);
                    border-radius:10px;padding:14px 16px;min-height:140px;
                    max-height:220px;overflow-y:auto;">
                  <div style="font-family:'Space Mono',monospace;font-size:8px;
                       font-weight:700;letter-spacing:0.12em;text-transform:uppercase;
                       color:#00b4dc;margin-bottom:10px;">// Respuesta</div>
                  <div style="font-family:'Space Grotesk',sans-serif;
                       font-size:13px;color:#dde3f5;line-height:1.72;">
                    {resp.replace(chr(10), "<br>")}
                  </div>
                </div>""",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """<div style="background:rgba(10,14,32,0.5);
                    border:0.5px solid rgba(120,140,255,0.14);
                    border-radius:10px;padding:14px 16px;min-height:140px;
                    display:flex;align-items:center;justify-content:center;">
                  <div style="font-family:'Space Mono',monospace;font-size:10px;
                       color:rgba(170,176,200,0.35);text-align:center;">
                    Elegí una sugerencia o escribí tu pregunta
                  </div>
                </div>""",
                unsafe_allow_html=True,
            )

        # Input de pregunta libre
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        pregunta = st.text_input(
            "Pregunta libre",
            placeholder="Escribí tu pregunta sobre los datos o metodología…",
            label_visibility="collapsed",
            key="dlg_pregunta",
        )
        col_btn, col_clr = st.columns([3, 1])
        with col_btn:
            if st.button("Consultar →", key="dlg_enviar",
                         use_container_width=True, type="primary"):
                if pregunta.strip():
                    with st.spinner("Consultando…"):
                        st.session_state["cv_ai_resp"] = _consultar_haiku(pregunta.strip())
                    st.rerun()
        with col_clr:
            if st.button("Limpiar", key="dlg_limpiar", use_container_width=True):
                st.session_state.pop("cv_ai_resp", None)
                st.rerun()


def render_asistente_sidebar():
    """Botón compacto en el sidebar que abre el dialog."""
    st.markdown("---")
    st.markdown(
        """<div style="display:flex;align-items:center;gap:8px;margin-bottom:7px;">
          <div style="width:20px;height:20px;border-radius:50%;flex-shrink:0;
               background:radial-gradient(circle at 35% 35%,#a060ff,#3010a0 60%,#050810);
               box-shadow:0 0 10px rgba(100,40,200,0.6);">
          </div>
          <div style="font-family:'Space Mono',monospace;font-size:8px;
               color:rgba(64,220,144,0.75);letter-spacing:0.07em;">
            ● HAIKU · EN LÍNEA
          </div>
        </div>""",
        unsafe_allow_html=True,
    )
    if st.button("🤖  Asistente IA", key="cv_open_ai", use_container_width=True):
        _dialog_asistente()


def render_asistente_panel():
    """Compatibilidad — ya no inyecta nada, el dialog se abre desde el sidebar."""
    pass
