"""
modulo_asistente.py — Ciudad Verde AI Agent
============================================
Asistente IA con Claude Haiku.
Panel compacto en la parte inferior del sidebar.
Orbe animada al procesar estilo ANCLA SCIENCE.
"""

import os
import requests
import streamlit as st

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
API_URL           = "https://api.anthropic.com/v1/messages"
MODEL             = "claude-haiku-4-5-20251001"

SYSTEM_PROMPT = """Sos el asistente de Ciudad Verde AI Agent, plataforma de análisis ambiental
de espacios verdes urbanos en la Provincia de Córdoba, Argentina.

Datos reales de Villa María en el sistema:
- Cobertura arbórea: 8.2% (ESA WorldCover 2020, 10m resolución)
- Pastizales: 14.2% | Cultivos urbanos: 23.9% | Edificado: 50.6% | Agua: 1.3%
- Acceso verde <300m: 100% del área edificada (cumple OMS)
- Distancia promedio al verde: 48 metros
- Verde público por habitante (OSM): 65.4 m²/hab (OMS mínimo: 9 m²/hab ✅)
- Verde satelital/hab: 93.2 m²/hab
- Temperatura superficial media: 39.97°C (Landsat 8/9, 13 imágenes)
- Isla de calor ΔT: +0.17°C (muy baja)
- Enfriamiento potencial del verde: 1.67°C/ha
- Zona más caliente: Noroeste VM centro-norte (40.76°C)
- CO₂ capturado: ~556 ton CO₂/año (USDA Forest Service, Nowak 2013)
- Población Villa María: ~97.000 hab | Villa Nueva: ~23.000 hab
- Área analizada: 49.6 km² (conglomerado VM + VN)
- Calificación general: A - Excelente (7/7 puntos)
- Río Ctalamochita: corredor ecológico natural entre VM y VN

Fuentes de datos:
- ESA WorldCover 2020: cobertura del suelo a 10m
- Landsat 8/9 (Google Earth Engine): temperatura superficial e índices vegetación
- OpenStreetMap / API Overpass: espacios verdes públicos catalogados
- INDEC Censo 2022: datos poblacionales
- USDA Forest Service / Nowak et al. 2013: metodología captura CO₂

Marcos internacionales:
- OMS: mínimo 9 m²/hab, acceso <300m a 0.5 ha
- ODS 11 Agenda 2030: ciudades sostenibles
- C40 Urban Nature Declaration 2030: 30% verde (QTC), 70% acceso (ESD)
- Acuerdo de París / NDC Argentina: sumideros de carbono
- EU Nature Restoration Law Art.8: ciudades >20.000 hab
- Ordenanza 7209 Ruralidad Urbana Villa María (2017)

Instrucciones:
- Respondé en español, claro y preciso
- Máximo 4 párrafos
- Usá datos reales del sistema cuando apliquen
- Texto plano, sin markdown con ** ni ##
- Orientado a funcionarios municipales
"""

SUGERENCIAS = [
    "¿Qué es el NDVI?",
    "¿Qué es la isla de calor ΔT?",
    "¿De dónde vienen los datos de temperatura?",
    "¿Cómo se calcula el CO₂?",
    "¿Qué es ESA WorldCover?",
    "¿Por qué se incluye Villa Nueva?",
    "¿Qué es el estándar C40?",
    "¿Qué es la Ordenanza 7209?",
]

# CSS del orbe procesando + panel compacto
_CSS_ASISTENTE = """
<style>
/* ── Panel asistente compacto ── */
.cv-ai-compact {
    background: rgba(8,12,28,0.75);
    border: 0.5px solid rgba(120,140,255,0.22);
    border-radius: 10px;
    padding: 12px 14px;
    margin-top: 6px;
}
.cv-ai-header {
    display: flex; align-items: center; gap: 9px;
    margin-bottom: 10px;
    padding-bottom: 9px;
    border-bottom: 0.5px solid rgba(120,140,255,0.14);
}
.cv-ai-orb-mini {
    width: 28px; height: 28px; flex-shrink: 0;
    border-radius: 50%;
    background: radial-gradient(circle at 35% 35%, #a060ff, #3010a0 60%, #050810);
    box-shadow: 0 0 14px rgba(100,40,200,0.45);
    animation: orb-mini 3s ease-in-out infinite;
}
@keyframes orb-mini {
    0%,100%{box-shadow:0 0 14px rgba(100,40,200,0.4);transform:scale(1);}
    50%{box-shadow:0 0 26px rgba(100,40,200,0.65);transform:scale(1.05);}
}
.cv-ai-header-info { flex:1; }
.cv-ai-header-name {
    font-family:'Space Mono',monospace;font-size:11px;
    font-weight:700;color:#c0b0f0;letter-spacing:0.05em;
}
.cv-ai-header-status {
    font-family:'Space Mono',monospace;font-size:8px;
    color:rgba(64,220,144,0.7);letter-spacing:0.06em;margin-top:1px;
}

/* Sugerencias en chips horizontales — scroll */
.cv-ai-chips {
    font-family:'Space Mono',monospace;font-size:8px;
    letter-spacing:0.10em;text-transform:uppercase;
    color:rgba(160,175,210,0.45);margin-bottom:5px;
}

/* ── Overlay orbe procesando ── */
.cv-orbe-overlay {
    display: none;
    position: fixed; inset: 0; z-index: 9999;
    background: rgba(5,8,16,0.94);
    flex-direction: column;
    align-items: center; justify-content: center;
    gap: 24px;
}
.cv-orbe-overlay.active { display: flex; }

.cv-orbe-wrap {
    position: relative;
    display: flex; align-items: center; justify-content: center;
    width: 220px; height: 220px;
}
.cv-arc {
    position: absolute; border-radius: 50%;
    border: 1px solid transparent;
    animation: cv-arc-spin linear infinite;
}
.cv-arc:nth-child(1){
    width:170px;height:170px;
    border-top-color:rgba(120,80,255,0.75);
    border-right-color:rgba(120,80,255,0.25);
    animation-duration:2.8s;
}
.cv-arc:nth-child(2){
    width:190px;height:190px;
    border-bottom-color:rgba(0,180,220,0.65);
    border-left-color:rgba(0,180,220,0.2);
    animation-duration:4.2s;animation-direction:reverse;
}
.cv-arc:nth-child(3){
    width:210px;height:210px;
    border-top-color:rgba(160,100,255,0.35);
    animation-duration:6.5s;
}
@keyframes cv-arc-spin { to{ transform:rotate(360deg); } }

.cv-sphere {
    width:120px;height:120px;border-radius:50%;
    background:radial-gradient(circle at 38% 32%,#d0a0ff 0%,#7030e0 30%,#2010a0 62%,#060318 100%);
    position:relative;z-index:2;
    animation:cv-sphere-pulse 2.2s ease-in-out infinite;
}
.cv-sphere::before {
    content:'';position:absolute;inset:-14px;border-radius:50%;
    background:radial-gradient(circle,rgba(130,60,255,0.22) 0%,transparent 68%);
    animation:cv-sphere-pulse 2.2s ease-in-out infinite;
}
@keyframes cv-sphere-pulse {
    0%,100%{transform:scale(1);filter:brightness(1);}
    50%{transform:scale(1.04);filter:brightness(1.12);}
}

.cv-orbe-label {
    font-family:'Space Mono',monospace;font-size:11px;
    letter-spacing:0.12em;text-transform:uppercase;
    color:rgba(180,160,255,0.7);text-align:center;
}
.cv-orbe-dots {
    display:flex;gap:8px;align-items:center;margin-top:4px;
}
.cv-orbe-dot {
    width:5px;height:5px;border-radius:50%;
    background:#00b4dc;
    animation:cv-dot-pulse 1s ease-in-out infinite;
}
.cv-orbe-dot:nth-child(2){animation-delay:0.2s;}
.cv-orbe-dot:nth-child(3){animation-delay:0.4s;}
@keyframes cv-dot-pulse{0%,100%{opacity:1;transform:scale(1);}50%{opacity:0.3;transform:scale(0.7);}}

/* Respuesta */
.cv-ai-respuesta {
    background:rgba(10,14,32,0.65);
    border:0.5px solid rgba(120,140,255,0.20);
    border-radius:8px;padding:12px 14px;margin-top:8px;
}
.cv-ai-respuesta-lbl {
    font-family:'Space Mono',monospace;font-size:8px;
    font-weight:700;letter-spacing:0.12em;text-transform:uppercase;
    color:#00b4dc;margin-bottom:8px;
}
.cv-ai-respuesta-body {
    font-family:'Space Grotesk',sans-serif;
    font-size:12px;color:#dde3f5;line-height:1.7;
}
</style>

<!-- Overlay orbe procesando -->
<div class="cv-orbe-overlay" id="cvOrbeOverlay">
  <div class="cv-orbe-wrap">
    <div class="cv-arc"></div>
    <div class="cv-arc"></div>
    <div class="cv-arc"></div>
    <div class="cv-sphere"></div>
  </div>
  <div>
    <div class="cv-orbe-label">Procesando consulta</div>
    <div class="cv-orbe-dots">
      <div class="cv-orbe-dot"></div>
      <div class="cv-orbe-dot"></div>
      <div class="cv-orbe-dot"></div>
    </div>
  </div>
</div>

<script>
function cvShowOrbe(){ document.getElementById('cvOrbeOverlay').classList.add('active'); }
function cvHideOrbe(){ document.getElementById('cvOrbeOverlay').classList.remove('active'); }
</script>
"""


def _consultar_haiku(pregunta: str) -> str:
    if not ANTHROPIC_API_KEY:
        return "⚠️ API key de Anthropic no configurada. Agregá ANTHROPIC_API_KEY en Railway → Variables."
    headers = {
        "x-api-key":         ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type":      "application/json",
    }
    payload = {
        "model":    MODEL,
        "max_tokens": 800,
        "system":   SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": pregunta}],
    }
    try:
        resp = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()["content"][0]["text"]
    except requests.exceptions.Timeout:
        return "⚠️ Tiempo de espera agotado. Intentá de nuevo."
    except requests.exceptions.RequestException as e:
        return f"⚠️ Error de conexión: {str(e)}"
    except (KeyError, IndexError):
        return "⚠️ Respuesta inesperada del modelo."


def render_asistente_sidebar():
    """Panel compacto del asistente en la parte inferior del sidebar."""

    # Inyectar CSS + overlay (una sola vez por sesión)
    if "cv_ai_css_injected" not in st.session_state:
        st.markdown(_CSS_ASISTENTE, unsafe_allow_html=True)
        st.session_state["cv_ai_css_injected"] = True

    st.markdown("---")

    # Header compacto con orbe mini
    st.markdown(
        """<div class="cv-ai-compact">
          <div class="cv-ai-header">
            <div class="cv-ai-orb-mini"></div>
            <div class="cv-ai-header-info">
              <div class="cv-ai-header-name">Asistente IA</div>
              <div class="cv-ai-header-status">● CLAUDE HAIKU · EN LÍNEA</div>
            </div>
          </div>
          <div class="cv-ai-chips">Preguntas frecuentes</div>
        </div>""",
        unsafe_allow_html=True,
    )

    # Sugerencias como botones — 2 columnas compactas
    cols = st.columns(2)
    for i, sug in enumerate(SUGERENCIAS):
        with cols[i % 2]:
            if st.button(
                sug, key=f"sug_{i}",
                use_container_width=True,
            ):
                st.session_state["ai_pregunta_disparar"] = sug

    # Input libre
    pregunta_input = st.text_input(
        "Pregunta libre",
        placeholder="Preguntá sobre datos, metodología…",
        key="ai_input_libre",
        label_visibility="collapsed",
    )

    col_btn, col_clear = st.columns([3, 1])
    with col_btn:
        enviar = st.button("Consultar →", key="ai_enviar", use_container_width=True, type="primary")
    with col_clear:
        if st.button("✕", key="ai_limpiar", use_container_width=True):
            st.session_state.pop("ai_respuesta", None)
            st.session_state.pop("ai_pregunta_disparar", None)
            st.rerun()

    # Resolver pregunta final
    pregunta_final = None
    if enviar and pregunta_input.strip():
        pregunta_final = pregunta_input.strip()
    elif "ai_pregunta_disparar" in st.session_state:
        pregunta_final = st.session_state.pop("ai_pregunta_disparar")

    # Consultar Haiku con spinner de Streamlit + orbe JS
    if pregunta_final:
        st.markdown(
            "<script>if(typeof cvShowOrbe==='function')cvShowOrbe();</script>",
            unsafe_allow_html=True,
        )
        with st.spinner(""):
            respuesta = _consultar_haiku(pregunta_final)
        st.session_state["ai_respuesta"] = respuesta
        st.markdown(
            "<script>if(typeof cvHideOrbe==='function')cvHideOrbe();</script>",
            unsafe_allow_html=True,
        )
        st.rerun()

    # Mostrar respuesta
    if "ai_respuesta" in st.session_state:
        cuerpo = st.session_state["ai_respuesta"].replace("\n", "<br>")
        st.markdown(
            f"""<div class="cv-ai-respuesta">
              <div class="cv-ai-respuesta-lbl">// Respuesta</div>
              <div class="cv-ai-respuesta-body">{cuerpo}</div>
            </div>""",
            unsafe_allow_html=True,
        )
