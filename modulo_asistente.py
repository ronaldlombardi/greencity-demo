"""
modulo_asistente.py — Ciudad Verde AI Agent
============================================
Asistente IA con Claude Haiku.
- Sidebar: solo un botón compacto
- Al pulsar: panel horizontal flotante sobre el contenido
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

# ── CSS + HTML del panel flotante horizontal ──────────────
_CSS_PANEL = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600&family=Space+Mono:wght@400;700&display=swap');

/* ── Panel flotante horizontal ── */
#cvAiPanel {
    display: none;
    position: fixed;
    left: 245px;          /* justo después del sidebar */
    bottom: 0;
    right: 0;
    height: 300px;
    z-index: 1000;
    background: rgba(8,12,28,0.97);
    border-top: 0.5px solid rgba(120,140,255,0.30);
    border-left: 0.5px solid rgba(120,140,255,0.20);
    backdrop-filter: blur(20px);
    display: none;
    flex-direction: row;
    gap: 0;
    font-family: 'Space Grotesk', sans-serif;
}
#cvAiPanel.open { display: flex !important; }

/* Columna izquierda: orbe + sugerencias */
#cvAiLeft {
    width: 280px;
    flex-shrink: 0;
    padding: 16px 16px;
    border-right: 0.5px solid rgba(120,140,255,0.16);
    display: flex;
    flex-direction: column;
    gap: 10px;
    overflow-y: auto;
}

/* Cabecera orbe */
.cv-panel-header {
    display: flex; align-items: center; gap: 10px;
    padding-bottom: 10px;
    border-bottom: 0.5px solid rgba(120,140,255,0.14);
}
.cv-panel-orb {
    width: 34px; height: 34px; flex-shrink: 0;
    border-radius: 50%;
    background: radial-gradient(circle at 35% 35%, #a060ff, #3010a0 60%, #050810);
    box-shadow: 0 0 16px rgba(100,40,200,0.5);
    animation: cv-orb-idle 3s ease-in-out infinite;
}
@keyframes cv-orb-idle {
    0%,100%{box-shadow:0 0 16px rgba(100,40,200,0.4);transform:scale(1);}
    50%{box-shadow:0 0 28px rgba(100,40,200,0.7);transform:scale(1.05);}
}
.cv-panel-orb.processing {
    animation: cv-orb-proc 0.8s ease-in-out infinite !important;
}
@keyframes cv-orb-proc {
    0%,100%{box-shadow:0 0 32px rgba(0,180,220,0.7);transform:scale(1);}
    50%{box-shadow:0 0 56px rgba(0,180,220,0.9);transform:scale(1.10);}
}
.cv-panel-name {
    font-family:'Space Mono',monospace;font-size:11px;
    font-weight:700;color:#c0b0f0;letter-spacing:0.05em;
}
.cv-panel-status {
    font-family:'Space Mono',monospace;font-size:8px;
    color:rgba(64,220,144,0.75);letter-spacing:0.07em;margin-top:2px;
}
.cv-panel-status.proc { color:rgba(0,180,220,0.85) !important; }

/* Sugerencias */
.cv-sugs-lbl {
    font-family:'Space Mono',monospace;font-size:8px;
    letter-spacing:0.12em;text-transform:uppercase;
    color:rgba(160,175,210,0.45);margin-bottom:2px;
}
.cv-sug-chip {
    display:block;width:100%;text-align:left;
    padding:6px 10px;
    background:rgba(99,40,180,0.12);
    border:0.5px solid rgba(120,80,200,0.25);
    border-radius:6px;
    font-family:'Space Grotesk',sans-serif;
    font-size:11px;color:#c8d0f0;
    cursor:pointer;transition:all 0.18s;
    margin-bottom:4px;
}
.cv-sug-chip:hover {
    background:rgba(99,40,180,0.26);
    border-color:rgba(144,96,255,0.45);
    color:#e8e0ff;
}

/* Columna central: input + respuesta */
#cvAiCenter {
    flex: 1;
    padding: 16px 18px;
    display: flex;
    flex-direction: column;
    gap: 10px;
    overflow-y: auto;
}

.cv-input-row {
    display: flex; gap: 8px; align-items: flex-end;
    flex-shrink: 0;
}
.cv-ai-textarea {
    flex: 1;
    padding: 9px 12px;
    background: rgba(8,12,28,0.85);
    border: 0.5px solid rgba(120,140,255,0.28);
    border-radius: 7px;
    font-family: 'Space Grotesk', sans-serif;
    font-size: 13px; color: #fff;
    outline: none; resize: none;
    height: 60px;
    transition: border-color 0.2s;
}
.cv-ai-textarea:focus { border-color: #9060ff; }
.cv-ai-textarea::placeholder { color: rgba(170,176,200,0.4); }

.cv-send-btn {
    padding: 9px 18px;
    background: linear-gradient(135deg, #6228b4, #00b4dc);
    border: none; border-radius: 7px;
    font-family: 'Space Grotesk', sans-serif;
    font-size: 12px; font-weight: 600; color: #fff;
    cursor: pointer; white-space: nowrap;
    transition: opacity 0.2s;
    align-self: flex-end;
}
.cv-send-btn:hover { opacity: 0.88; }
.cv-send-btn:disabled { opacity: 0.4; cursor: not-allowed; }

/* Respuesta */
.cv-resp-box {
    flex: 1;
    background: rgba(10,14,32,0.6);
    border: 0.5px solid rgba(120,140,255,0.18);
    border-radius: 8px;
    padding: 12px 14px;
    overflow-y: auto;
}
.cv-resp-lbl {
    font-family:'Space Mono',monospace;font-size:8px;
    font-weight:700;letter-spacing:0.12em;text-transform:uppercase;
    color:#00b4dc;margin-bottom:8px;
}
.cv-resp-body {
    font-family:'Space Grotesk',sans-serif;
    font-size:12px;color:#dde3f5;line-height:1.7;
}
.cv-resp-dots {
    display:flex;gap:6px;align-items:center;
    padding:4px 0;
}
.cv-resp-dot {
    width:5px;height:5px;border-radius:50%;background:#00b4dc;
    animation:cv-dot 1s ease-in-out infinite;
}
.cv-resp-dot:nth-child(2){animation-delay:0.2s;}
.cv-resp-dot:nth-child(3){animation-delay:0.4s;}
@keyframes cv-dot{0%,100%{opacity:1;transform:scale(1);}50%{opacity:0.3;transform:scale(0.6);}}

/* Botón cerrar panel */
#cvCloseBtn {
    position:absolute;top:10px;right:14px;
    background:transparent;border:none;
    font-family:'Space Mono',monospace;font-size:11px;
    color:rgba(170,176,200,0.5);cursor:pointer;
    transition:color 0.2s;z-index:10;
    padding:4px 8px;
}
#cvCloseBtn:hover{color:#fff;}

/* Arco de procesamiento en orbe */
.cv-panel-orb-wrap {
    position:relative;width:34px;height:34px;flex-shrink:0;
}
.cv-proc-arc {
    display:none;
    position:absolute;inset:-6px;border-radius:50%;
    border:1.5px solid transparent;
    border-top-color:rgba(0,180,220,0.8);
    animation:cv-arc-spin 1.2s linear infinite;
}
.cv-proc-arc.active { display:block; }
@keyframes cv-arc-spin{to{transform:rotate(360deg);}}
</style>

<!-- Panel flotante horizontal -->
<div id="cvAiPanel">
  <button id="cvCloseBtn" onclick="cvClosePanel()">✕ cerrar</button>

  <!-- Columna izquierda -->
  <div id="cvAiLeft">
    <div class="cv-panel-header">
      <div class="cv-panel-orb-wrap">
        <div class="cv-panel-orb" id="cvOrb"></div>
        <div class="cv-proc-arc" id="cvArc"></div>
      </div>
      <div>
        <div class="cv-panel-name">Asistente IA</div>
        <div class="cv-panel-status" id="cvStatus">● CLAUDE HAIKU · EN LÍNEA</div>
      </div>
    </div>
    <div class="cv-sugs-lbl">Preguntas frecuentes</div>
    <div id="cvSugs"></div>
  </div>

  <!-- Columna central -->
  <div id="cvAiCenter">
    <div class="cv-input-row">
      <textarea class="cv-ai-textarea" id="cvPregunta"
        placeholder="Preguntá sobre indicadores, fuentes de datos, metodología…"
        onkeydown="if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();cvEnviar();}">
      </textarea>
      <button class="cv-send-btn" id="cvSendBtn" onclick="cvEnviar()">
        Consultar →
      </button>
    </div>
    <div class="cv-resp-box" id="cvRespBox">
      <div class="cv-resp-lbl">// Asistente Ciudad Verde</div>
      <div class="cv-resp-body" id="cvRespBody" style="color:rgba(170,176,200,0.45);">
        Hacé una pregunta o elegí una sugerencia para comenzar.
      </div>
    </div>
  </div>
</div>

<script>
(function(){
  // Sugerencias
  const sugs = %SUGERENCIAS%;
  const cont = document.getElementById('cvSugs');
  if(cont){
    sugs.forEach(s=>{
      const b=document.createElement('button');
      b.className='cv-sug-chip';
      b.textContent=s;
      b.onclick=()=>{ document.getElementById('cvPregunta').value=s; cvEnviar(); };
      cont.appendChild(b);
    });
  }

  window.cvOpenPanel = function(){
    document.getElementById('cvAiPanel').classList.add('open');
  };
  window.cvClosePanel = function(){
    document.getElementById('cvAiPanel').classList.remove('open');
  };

  window.cvEnviar = async function(){
    const ta  = document.getElementById('cvPregunta');
    const btn = document.getElementById('cvSendBtn');
    const body= document.getElementById('cvRespBody');
    const orb = document.getElementById('cvOrb');
    const arc = document.getElementById('cvArc');
    const st  = document.getElementById('cvStatus');
    const pregunta = ta.value.trim();
    if(!pregunta) return;

    // Estado procesando
    btn.disabled = true;
    orb.classList.add('processing');
    arc.classList.add('active');
    st.textContent  = '● PROCESANDO…';
    st.classList.add('proc');
    body.innerHTML = '<div class="cv-resp-dots"><div class="cv-resp-dot"></div><div class="cv-resp-dot"></div><div class="cv-resp-dot"></div></div>';

    try {
      const resp = await fetch('https://api.anthropic.com/v1/messages', {
        method: 'POST',
        headers: {
          'content-type':      'application/json',
          'x-api-key':         '%API_KEY%',
          'anthropic-version': '2023-06-01',
          'anthropic-dangerous-direct-browser-calls': 'true'
        },
        body: JSON.stringify({
          model: 'claude-haiku-4-5-20251001',
          max_tokens: 800,
          system: %SYSTEM_JSON%,
          messages: [{ role: 'user', content: pregunta }]
        })
      });
      const data = await resp.json();
      const texto = (data.content && data.content[0] && data.content[0].text)
        ? data.content[0].text
        : 'Sin respuesta del modelo.';
      const html = texto
        .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
        .replace(/\n\n/g,'</p><p style="margin-top:8px">').replace(/\n/g,'<br>');
      document.getElementById('cvRespBox').querySelector('.cv-resp-lbl').textContent = '// Respuesta';
      body.innerHTML = '<p>' + html + '</p>';
      ta.value = '';
    } catch(e) {
      body.innerHTML = '<span style="color:#e24b4a;">Error: ' + e.message + '</span>';
    } finally {
      btn.disabled = false;
      orb.classList.remove('processing');
      arc.classList.remove('active');
      st.textContent = '● CLAUDE HAIKU · EN LÍNEA';
      st.classList.remove('proc');
    }
  };
})();
</script>
"""


def _consultar_haiku(pregunta: str) -> str:
    """Fallback Python por si el JS falla (no debería usarse en producción)."""
    if not ANTHROPIC_API_KEY:
        return "⚠️ API key no configurada."
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
        return r.json()["content"][0]["text"]
    except Exception as e:
        return f"⚠️ Error: {str(e)}"


def render_asistente_panel():
    """
    Inyecta el panel flotante horizontal en el área principal.
    Llamar UNA VEZ al inicio del contenido principal (fuera del sidebar).
    """
    import json as _json
    if "cv_panel_injected" not in st.session_state:
        # Inyectar panel con sugerencias y API key reemplazadas
        html = _CSS_PANEL
        html = html.replace("%SUGERENCIAS%", _json.dumps(SUGERENCIAS, ensure_ascii=False))
        html = html.replace("%API_KEY%", ANTHROPIC_API_KEY)
        html = html.replace("%SYSTEM_JSON%", _json.dumps(SYSTEM_PROMPT, ensure_ascii=False))
        st.markdown(html, unsafe_allow_html=True)
        st.session_state["cv_panel_injected"] = True


def render_asistente_sidebar():
    """
    Botón compacto en el sidebar que abre el panel flotante.
    """
    st.markdown("---")
    st.markdown(
        """
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
          <div style="width:22px;height:22px;border-radius:50%;flex-shrink:0;
               background:radial-gradient(circle at 35% 35%,#a060ff,#3010a0 60%,#050810);
               box-shadow:0 0 12px rgba(100,40,200,0.5);
               animation:orb-mini 3s ease-in-out infinite;">
          </div>
          <div style="font-family:'Space Mono',monospace;font-size:9px;
               color:rgba(64,220,144,0.7);letter-spacing:0.06em;">
            ● HAIKU · EN LÍNEA
          </div>
        </div>
        <style>
        @keyframes orb-mini{0%,100%{box-shadow:0 0 12px rgba(100,40,200,0.4);}
        50%{box-shadow:0 0 22px rgba(100,40,200,0.7);}}
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """<button onclick="cvOpenPanel()"
          style="width:100%;padding:9px 14px;
          background:linear-gradient(135deg,rgba(99,40,180,0.35),rgba(0,180,220,0.25));
          border:0.5px solid rgba(120,140,255,0.35);border-radius:7px;
          font-family:'Space Grotesk',sans-serif;font-size:12px;font-weight:600;
          color:#c8d4f8;cursor:pointer;letter-spacing:0.03em;
          transition:all 0.2s;text-align:center;">
          🤖 Asistente IA
        </button>""",
        unsafe_allow_html=True,
    )
