"""
modulo_asistente.py — Ciudad Verde AI Agent
============================================
Asistente IA con Claude Haiku integrado en el sidebar.
Responde preguntas sobre indicadores, fuentes de datos,
metodologías y contexto ambiental de Villa María.
"""

import os
import json
import requests
import streamlit as st

# ── Configuración ──────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
API_URL           = "https://api.anthropic.com/v1/messages"
MODEL             = "claude-haiku-4-5-20251001"

SYSTEM_PROMPT = """Sos el asistente de Ciudad Verde AI Agent, una plataforma de análisis ambiental
de espacios verdes urbanos en la Provincia de Córdoba, Argentina.

Contexto de Villa María — datos reales del sistema:
- Cobertura arbórea: 8.2% del área urbana (fuente: ESA WorldCover 2020, 10m resolución)
- Pastizales: 14.2% | Cultivos urbanos: 23.9% | Edificado: 50.6% | Agua: 1.3%
- Acceso a verde <300m: 100% del área edificada (cumple meta OMS)
- Distancia promedio al verde: 48 metros
- Verde público por habitante (OSM): 65.4 m²/hab (OMS mínimo: 9 m²/hab ✅)
- Verde satelital por habitante: 93.2 m²/hab
- Temperatura superficial media: 39.97°C (Landsat 8/9, 13 imágenes)
- Isla de calor ΔT: +0.17°C (muy baja, referencia internacional)
- Enfriamiento potencial del verde: 1.67°C por hectárea arbolada
- Zona más caliente: Noroeste VM centro-norte (40.76°C)
- Captura de CO₂ estimada: ~556 toneladas CO₂/año (metodología USDA Forest Service)
- Población Villa María: ~97.000 hab | Villa Nueva: ~23.000 hab
- Área analizada: 49.6 km² (conglomerado VM + VN)
- Calificación general: A - Excelente (7/7 puntos)

Fuentes de datos utilizadas:
- ESA WorldCover 2020: clasificación de cobertura del suelo a 10m de resolución
- Landsat 8/9 (Google Earth Engine): temperatura superficial (LST) e índices de vegetación
- OpenStreetMap / API Overpass: espacios verdes de uso público catalogados
- INDEC Censo 2022: datos poblacionales
- Río Ctalamochita: corredor ecológico natural entre Villa María y Villa Nueva

Marcos de referencia internacionales:
- OMS: mínimo 9 m²/hab de verde público y acceso a 0.5 ha dentro de 300m
- ODS 11 (Agenda 2030): ciudades y comunidades sostenibles
- C40 Urban Nature Declaration 2030: 30% superficie verde (QTC) y 70% acceso (ESD)
- Acuerdo de París / NDC Argentina: sumideros de carbono urbanos
- EU Nature Restoration Law Art. 8: estándar europeo para ciudades >20.000 hab
- Ordenanza 7209 "Ruralidad Urbana" Villa María (2017): marco normativo local

Normativa local relevante:
- Ordenanza 7209 de Ruralidad Urbana (2017): reconoce servicios ambientales del periurbano
- Investigación CONICET/UNVM activa sobre periurbano de Villa María

Metodología de captura de CO₂:
- Densidad de secuestro neto: 0.205 kg C/m²/año de cobertura arbórea (Nowak et al. 2013, USDA)
- Factor de conversión C → CO₂: 3.667
- Equivalencia: 1 auto promedio emite ~2.1 tCO₂/año (EPA)

Instrucciones de respuesta:
- Respondé en español, de forma clara y precisa
- Usá los datos reales del sistema cuando sean relevantes
- Explicá los conceptos técnicos de forma accesible para funcionarios municipales
- Sé conciso: máximo 4-5 párrafos
- Cuando cites datos, mencioná la fuente (ESA WorldCover, Landsat, OSM, INDEC, etc.)
- Si te preguntan algo fuera del ámbito ambiental/urbano de Ciudad Verde, redirigí amablemente
- No uses markdown con ** o ## en las respuestas — texto plano con saltos de línea
"""

SUGERENCIAS = [
    "¿Qué es el NDVI y por qué importa?",
    "¿De dónde vienen los datos de temperatura?",
    "¿Qué significa isla de calor ΔT?",
    "¿Cómo se calcula la captura de CO₂?",
    "¿Qué es ESA WorldCover?",
    "¿Por qué se incluye Villa Nueva en el análisis?",
    "¿Qué es el estándar C40 Urban Nature?",
    "¿Cómo se mide el acceso <300m a verde?",
    "¿Qué significa la calificación A - Excelente?",
    "¿Qué es la Ordenanza 7209?",
]


# ── Llamada a la API ───────────────────────────────────────

def _consultar_haiku(pregunta: str) -> str:
    """Llama a Claude Haiku y devuelve la respuesta como texto."""
    if not ANTHROPIC_API_KEY:
        return "⚠️ API key de Anthropic no configurada. Agregá ANTHROPIC_API_KEY en las variables de entorno de Railway."

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
        resp = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data["content"][0]["text"]
    except requests.exceptions.Timeout:
        return "⚠️ Tiempo de espera agotado. Intentá de nuevo."
    except requests.exceptions.RequestException as e:
        return f"⚠️ Error de conexión: {str(e)}"
    except (KeyError, IndexError):
        return "⚠️ Respuesta inesperada del modelo."


# ── Panel visual ───────────────────────────────────────────

def render_asistente_sidebar():
    """
    Renderiza el panel del asistente IA en el sidebar de Streamlit.
    Llamar desde app.py dentro del bloque `with st.sidebar:`.
    """
    st.markdown("---")

    # Orbe + estado
    st.markdown(
        """
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">
          <div style="width:32px;height:32px;flex-shrink:0;border-radius:50%;
               background:radial-gradient(circle at 35% 35%,#a060ff,#3010a0 60%,#050810);
               animation:orb-pulse 3s ease-in-out infinite;
               box-shadow:0 0 18px rgba(100,40,200,0.4);">
          </div>
          <div style="flex:1;">
            <div style="font-family:'Space Mono',monospace;font-size:11px;
                 font-weight:700;color:#c0b0f0;letter-spacing:0.05em;">
              Asistente IA
            </div>
            <div style="font-family:'Space Mono',monospace;font-size:9px;
                 color:rgba(64,220,144,0.7);margin-top:2px;letter-spacing:0.06em;">
              ● CLAUDE HAIKU · EN LÍNEA
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Sugerencias clickeables
    st.markdown(
        "<div style='font-family:\"Space Mono\",monospace;font-size:8px;"
        "letter-spacing:0.12em;text-transform:uppercase;"
        "color:rgba(160,175,210,0.5);margin-bottom:6px;'>Preguntas frecuentes</div>",
        unsafe_allow_html=True,
    )

    # Mostrar sugerencias en dos columnas
    col_a, col_b = st.columns(2)
    sugerencias_visibles = SUGERENCIAS[:6]
    for i, sug in enumerate(sugerencias_visibles):
        col = col_a if i % 2 == 0 else col_b
        with col:
            if st.button(sug, key=f"sug_{i}", use_container_width=True):
                st.session_state["ai_pregunta"] = sug
                st.session_state["ai_disparar"] = True

    st.markdown("<div style='margin-top:6px;'></div>", unsafe_allow_html=True)

    # Input de pregunta
    pregunta_input = st.text_area(
        "Tu pregunta",
        value=st.session_state.get("ai_pregunta", ""),
        placeholder="Preguntá sobre indicadores, fuentes de datos, metodologías…",
        height=80,
        key="ai_input",
        label_visibility="collapsed",
    )

    # Botón enviar
    enviar = st.button(
        "Consultar →",
        key="ai_enviar",
        use_container_width=True,
        type="primary",
    )

    # Disparar consulta por sugerencia o botón
    disparar = enviar or st.session_state.pop("ai_disparar", False)
    pregunta_final = st.session_state.get("ai_pregunta", "") if not enviar else pregunta_input

    if disparar and pregunta_final.strip():
        with st.spinner("Consultando…"):
            respuesta = _consultar_haiku(pregunta_final.strip())
        st.session_state["ai_respuesta"] = respuesta
        st.session_state["ai_pregunta"] = ""

    # Mostrar respuesta
    if "ai_respuesta" in st.session_state and st.session_state["ai_respuesta"]:
        st.markdown(
            f"""
            <div style="background:rgba(10,14,32,0.65);border:0.5px solid rgba(120,140,255,0.22);
                 border-radius:8px;padding:14px 16px;margin-top:8px;">
              <div style="font-family:'Space Mono',monospace;font-size:8px;font-weight:700;
                   letter-spacing:0.12em;text-transform:uppercase;
                   color:#00b4dc;margin-bottom:10px;">// Respuesta</div>
              <div style="font-size:12px;color:#dde3f5;line-height:1.7;
                   font-family:'Space Grotesk',sans-serif;">
                {st.session_state["ai_respuesta"].replace(chr(10), "<br>")}
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Nueva pregunta", key="ai_limpiar"):
            del st.session_state["ai_respuesta"]
            st.rerun()
