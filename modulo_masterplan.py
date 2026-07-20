"""
modulo_masterplan.py — Ciudad Verde AI Agent
=============================================
Generador de Masterplan ambiental para Villa María.
Usa Claude Opus 4.7 con contexto completo de la plataforma.
Registra consumo en PostgreSQL.
"""

import os
import requests
import streamlit as st
from modulo_db import registrar_consumo, guardar_masterplan, obtener_masteplans

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
API_URL           = "https://api.anthropic.com/v1/messages"
MODEL_OPUS        = "claude-opus-4-7"

# ── Overlay orbe procesando — estilo ANCLA SCIENCE ────────
_ORBE_HTML = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Space+Grotesk:wght@400;600&display=swap');

#cvOrbeOverlay {
    display: none;
    position: fixed;
    inset: 0;
    z-index: 9999;
    background: rgba(5,8,16,0.97);
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 28px;
}
#cvOrbeOverlay.active { display: flex; }

/* Canvas neuro de fondo */
#cvNeuroCanvas {
    position: absolute;
    inset: 0;
    z-index: 0;
    opacity: 0.6;
}

/* Contenido sobre canvas */
.cv-orbe-content {
    position: relative;
    z-index: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 24px;
}

/* Orbe con arcos */
.cv-orbe-wrap {
    position: relative;
    width: 240px; height: 240px;
    display: flex; align-items: center; justify-content: center;
}
.cv-o-arc {
    position: absolute; border-radius: 50%;
    border: 1px solid transparent;
    animation: cv-arc-spin linear infinite;
}
.cv-o-arc:nth-child(1){
    width:190px;height:190px;
    border-top-color:rgba(120,80,255,0.75);
    border-right-color:rgba(120,80,255,0.28);
    animation-duration:2.8s;
}
.cv-o-arc:nth-child(2){
    width:212px;height:212px;
    border-bottom-color:rgba(0,180,220,0.65);
    border-left-color:rgba(0,180,220,0.2);
    animation-duration:4.2s;
    animation-direction:reverse;
}
.cv-o-arc:nth-child(3){
    width:234px;height:234px;
    border-top-color:rgba(160,100,255,0.4);
    animation-duration:6.5s;
}
@keyframes cv-arc-spin { to { transform: rotate(360deg); } }

.cv-o-sphere {
    width: 140px; height: 140px;
    border-radius: 50%;
    background: radial-gradient(circle at 38% 32%,
        #d0a0ff 0%, #7030e0 30%, #2010a0 62%, #060318 100%);
    position: relative; z-index: 2;
    animation: cv-sphere-pulse 2.2s ease-in-out infinite;
    box-shadow: 0 0 36px rgba(110,45,230,0.5), 0 0 70px rgba(90,30,190,0.25);
}
.cv-o-sphere::before {
    content: '';
    position: absolute; inset: -14px; border-radius: 50%;
    background: radial-gradient(circle, rgba(130,60,255,0.22) 0%, transparent 68%);
    animation: cv-halo 2.2s ease-in-out infinite;
}
.cv-o-sphere::after {
    content: '';
    position: absolute; inset: 12px; border-radius: 50%;
    border: 1px solid rgba(200,160,255,0.22);
}
@keyframes cv-sphere-pulse {
    0%,100%{box-shadow:0 0 36px rgba(110,45,230,.5),0 0 70px rgba(90,30,190,.25);transform:scale(1);}
    50%{box-shadow:0 0 55px rgba(130,60,255,.7),0 0 100px rgba(110,45,220,.35);transform:scale(1.04);}
}
@keyframes cv-halo {
    0%,100%{opacity:.55;transform:scale(1);}
    50%{opacity:1;transform:scale(1.1);}
}

/* Badge modelo */
.cv-o-badge {
    display: flex; align-items: center; gap: 7px;
    background: rgba(12,16,36,0.8);
    border: 0.5px solid rgba(120,100,255,0.32);
    border-radius: 20px;
    padding: 5px 14px;
    font-family: 'Space Mono', monospace;
    font-size: 10px; color: rgba(180,160,255,0.8);
    letter-spacing: 0.05em;
}
.cv-o-bdot {
    width: 5px; height: 5px; border-radius: 50%;
    background: #a060ff;
    animation: cv-pdot 1.2s ease-in-out infinite;
}
@keyframes cv-pdot { 0%,100%{opacity:1;}50%{opacity:0.3;} }

/* Fase animada */
.cv-o-phase {
    font-family: 'Space Mono', monospace;
    font-size: 13px; color: rgba(200,188,255,0.85);
    letter-spacing: 0.02em;
    min-height: 20px; text-align: center;
}
.cv-o-cursor {
    display: inline-block;
    width: 7px; height: 13px;
    background: #9060ff;
    margin-left: 3px;
    animation: cv-blink 0.75s step-end infinite;
    vertical-align: middle;
}
@keyframes cv-blink { 0%,100%{opacity:1;}50%{opacity:0;} }

/* Progress bar */
.cv-o-prog {
    display: flex; align-items: center; gap: 10px;
    font-family: 'Space Mono', monospace;
    font-size: 9px; color: rgba(130,115,195,0.55);
    letter-spacing: 0.06em;
}
.cv-o-bar {
    width: 200px; height: 2px;
    background: rgba(80,60,160,0.22);
    border-radius: 2px; overflow: hidden;
}
.cv-o-fill {
    height: 100%;
    background: linear-gradient(90deg, #6228b4, #a060ff, #00b4dc);
    border-radius: 2px;
    width: 0%;
    transition: width 0.4s ease;
}
</style>

<!-- Overlay orbe -->
<div id="cvOrbeOverlay">
  <canvas id="cvNeuroCanvas"></canvas>
  <div class="cv-orbe-content">
    <div class="cv-orbe-wrap">
      <div class="cv-o-arc"></div>
      <div class="cv-o-arc"></div>
      <div class="cv-o-arc"></div>
      <div class="cv-o-sphere"></div>
    </div>
    <div class="cv-o-badge">
      <div class="cv-o-bdot"></div>
      Claude Opus 4.7 · generando Masterplan
    </div>
    <div class="cv-o-phase" id="cvOPhase">
      Iniciando análisis<span class="cv-o-cursor"></span>
    </div>
    <div class="cv-o-prog">
      <span id="cvOTok">0 tokens</span>
      <div class="cv-o-bar"><div class="cv-o-fill" id="cvOFill"></div></div>
      <span id="cvOPct">0%</span>
    </div>
  </div>
</div>

<script>
(function(){
  // ── Fases animadas ──
  const FASES = [
    'Analizando datos ambientales de Villa María',
    'Procesando indicadores de cobertura verde',
    'Evaluando métricas de temperatura superficial',
    'Calculando captura de CO₂ y equivalencias',
    'Comparando con estándares C40 y OMS',
    'Alineando con Agenda 2030 y ODS 11',
    'Identificando brechas y oportunidades',
    'Diseñando líneas de acción prioritarias',
    'Estimando presupuesto y gobernanza',
    'Estructurando el Masterplan ejecutivo',
    'Redactando recomendaciones para Villa María',
    'Finalizando documento de política pública',
  ];

  let orbeTimer = null, orbePhaseIdx = 0, orbeProgress = 0, orbeProgressTimer = null;
  let neuroNodes = [], neuroCtx, neuroW, neuroH, speedMult = 1;

  // ── Canvas neuro ──
  function initNeuro(){
    const c = document.getElementById('cvNeuroCanvas');
    if(!c) return;
    neuroW = c.width  = window.innerWidth;
    neuroH = c.height = window.innerHeight;
    neuroCtx = c.getContext('2d');
    neuroNodes = [];
    for(let i=0;i<35;i++) neuroNodes.push({
      x:Math.random()*neuroW, y:Math.random()*neuroH,
      vx:(Math.random()-.5)*.4, vy:(Math.random()-.5)*.4,
      r:Math.random()*2+1.2, o:Math.random()*.5+.2,
      p:Math.random()*Math.PI*2
    });
    drawNeuro();
  }

  function drawNeuro(){
    if(!neuroCtx) return;
    neuroCtx.clearRect(0,0,neuroW,neuroH);
    for(const n of neuroNodes){
      n.x += n.vx*speedMult; n.y += n.vy*speedMult;
      if(n.x<0||n.x>neuroW) n.vx*=-1;
      if(n.y<0||n.y>neuroH) n.vy*=-1;
      n.p += .025*speedMult;
    }
    for(let i=0;i<neuroNodes.length;i++){
      for(let j=i+1;j<neuroNodes.length;j++){
        const dx=neuroNodes[j].x-neuroNodes[i].x, dy=neuroNodes[j].y-neuroNodes[i].y;
        const d=Math.sqrt(dx*dx+dy*dy);
        if(d<140){
          neuroCtx.beginPath();
          neuroCtx.moveTo(neuroNodes[i].x,neuroNodes[i].y);
          neuroCtx.lineTo(neuroNodes[j].x,neuroNodes[j].y);
          neuroCtx.strokeStyle=`rgba(120,90,255,${Math.min((1-d/140)*.20,.28)})`;
          neuroCtx.lineWidth=.5;
          neuroCtx.stroke();
        }
      }
    }
    for(const n of neuroNodes){
      const p=Math.sin(n.p)*.3+.7;
      neuroCtx.beginPath();
      neuroCtx.arc(n.x,n.y,n.r*p,0,Math.PI*2);
      neuroCtx.fillStyle=`rgba(140,100,255,${n.o*p})`;
      neuroCtx.fill();
    }
    requestAnimationFrame(drawNeuro);
  }

  window.cvMostrarOrbe = function(){
    const ov = document.getElementById('cvOrbeOverlay');
    if(!ov) return;
    ov.classList.add('active');
    speedMult = 3;
    initNeuro();
    orbePhaseIdx = 0;
    const ph = document.getElementById('cvOPhase');
    if(ph) ph.innerHTML = FASES[0] + '<span class="cv-o-cursor"></span>';
    orbeTimer = setInterval(()=>{
      orbePhaseIdx = (orbePhaseIdx+1) % FASES.length;
      if(ph) ph.innerHTML = FASES[orbePhaseIdx] + '<span class="cv-o-cursor"></span>';
    }, 1400);
    // Barra de progreso simulada (0→85% en ~55s, luego espera)
    orbeProgress = 0;
    const fill = document.getElementById('cvOFill');
    const pct  = document.getElementById('cvOPct');
    const tok  = document.getElementById('cvOTok');
    orbeProgressTimer = setInterval(()=>{
      if(orbeProgress < 85){
        orbeProgress += 0.28;
        if(fill) fill.style.width = orbeProgress.toFixed(1)+'%';
        if(pct)  pct.textContent  = Math.round(orbeProgress)+'%';
        if(tok)  tok.textContent  = Math.round(orbeProgress * 40).toLocaleString()+' tokens';
      }
    }, 150);
  };

  window.cvOcultarOrbe = function(tokFinal){
    clearInterval(orbeTimer);
    clearInterval(orbeProgressTimer);
    speedMult = 1;
    const fill = document.getElementById('cvOFill');
    const pct  = document.getElementById('cvOPct');
    const tok  = document.getElementById('cvOTok');
    if(fill) fill.style.width = '100%';
    if(pct)  pct.textContent  = '100%';
    if(tok && tokFinal) tok.textContent = tokFinal.toLocaleString()+' tokens';
    setTimeout(()=>{
      const ov = document.getElementById('cvOrbeOverlay');
      if(ov) ov.classList.remove('active');
    }, 600);
  };
})();
</script>
"""

# ── Contexto completo de Villa María ──────────────────────
CONTEXTO_VM = """
DATOS REALES DEL SISTEMA — VILLA MARÍA / VILLA NUEVA (Córdoba, Argentina)
==========================================================================

COBERTURA DEL SUELO (ESA WorldCover 2020, resolución 10m):
- Arbolado urbano:    8.2%  del área analizada
- Pastizales:        14.2%
- Cultivos urbanos:  23.9%  (oportunidad de reconversión)
- Suelo edificado:   50.6%
- Agua (río):         1.3%
- Área total analizada: 49.6 km² (conglomerado VM + VN)

ACCESIBILIDAD A ESPACIOS VERDES:
- Acceso a verde <300m:    100% del área edificada ✅ (meta OMS cumplida)
- Distancia promedio:       48 metros al espacio verde más cercano
- Verde satelital/hab:      93.2 m²/hab
- Verde público/hab (OSM):  65.4 m²/hab ✅ (OMS mínimo: 9 m²/hab)
- Distribución: 91.1% a <100m | 8.9% entre 100–300m

TEMPERATURA SUPERFICIAL (Landsat 8/9, 13 imágenes):
- Temperatura media:         39.97°C
- Isla de calor ΔT:         +0.17°C (muy baja — referencia excelente)
- Verde denso (NDVI >0.4):   38.21°C
- Suelo/asfalto (NDVI <0.2): 39.88°C
- Enfriamiento por arbolado:  1.67°C por hectárea
- Zona más caliente: Noroeste VM centro-norte (40.76°C, +0.79°C sobre media)
- Zona más fresca:  Sureste VN sur (39.55°C)

CAPTURA DE CO₂ (metodología USDA Forest Service, Nowak et al. 2013):
- Densidad secuestro neto:   0.205 kg C/m²/año de cobertura arbórea
- CO₂ capturado actual:      ~556 toneladas CO₂/año
- Equivalente a:             ~265 autos fuera de circulación
- Con meta 15% arbolado:     ~1.017 toneladas CO₂/año (+461 t adicionales)

VERDE PÚBLICO — OPENSTREETMAP:
- Espacios catalogados:    1.027 elementos
- Área pública total:      784.7 ha
- Verde público/hab:        65.4 m²/hab
- Brecha satelital/público: 27.8 m²/hab (~270 ha no accesibles al público)

DATOS POBLACIONALES (INDEC Censo 2022):
- Población Villa María:   ~97.000 hab (cabecera Depto. General San Martín)
- Población Villa Nueva:   ~23.000 hab
- Total conglomerado:     ~120.000 hab

CALIFICACIÓN GENERAL: A - Excelente (7/7 puntos)

ANÁLISIS POR ZONAS:
- Noroeste (VM centro-norte): Acceso 88.3% | Temp 40.76°C | 18.4 ha edif. ⚠️ PRIORITARIA
- Noreste  (VN norte):        Acceso 96.1% | Temp 39.85°C | 12.1 ha edif.
- Suroeste (VM sur):          Acceso 100%  | Temp 39.73°C | 21.7 ha edif. ✅
- Sureste  (VN sur):          Acceso 100%  | Temp 39.55°C |  9.8 ha edif. ✅

TARGETS C40 URBAN NATURE DECLARATION 2030:
- QTC (30% superficie verde): VM tiene 23.7% → faltan 6.3 puntos porcentuales (~227 ha)
- ESD (70% acceso verde/azul): VM tiene 100% → ✅ CUMPLIDO Y SUPERADO
- Ritmo necesario: 45.4 ha/año de verde adicional hasta 2030
- Árboles necesarios: ~1.816 árboles/año (copa media 25m²)

MARCO NORMATIVO:
- OMS: 9 m²/hab mínimo (VM: 65.4 m²/hab ✅)
- ODS 11 — Agenda 2030: ciudades sostenibles
- C40 Urban Nature Declaration 2030 (Buenos Aires firmante)
- Acuerdo de París / NDC Argentina: sumideros de carbono urbanos
- EU Nature Restoration Law Art.8 (referencia internacional)
- Ordenanza 7209 "Ruralidad Urbana" Villa María (2017)
- Investigación CONICET/UNVM activa sobre periurbano VM

CORREDOR ECOLÓGICO:
- Río Ctalamochita: divide VM (oeste) y VN (este)
- Potencial: parque lineal con ciclovías en ambas márgenes
- ~8 km de corredor verde posible
"""

SYSTEM_MASTERPLAN = """Sos un experto en planificación urbana ambiental, política pública y desarrollo
sostenible de ciudades intermedias en Argentina y América Latina.

Tu tarea es generar un MASTERPLAN AMBIENTAL completo, riguroso y accionable para
el Municipio de Villa María, Córdoba, Argentina, basado exclusivamente en los datos
reales provistos por la plataforma Ciudad Verde AI Agent.

El Masterplan debe ser un documento ejecutivo de alta calidad, listo para ser
presentado ante autoridades municipales y organismos provinciales o nacionales.

ESTRUCTURA OBLIGATORIA DEL MASTERPLAN:

1. RESUMEN EJECUTIVO (3-4 párrafos)
   - Diagnóstico sintético del estado ambiental actual
   - Posicionamiento internacional (C40, OMS, ODS)
   - Objetivo central del plan

2. DIAGNÓSTICO DE BASE
   - Fortalezas del sistema verde actual (con datos específicos)
   - Brechas y oportunidades (con datos específicos)
   - Zona prioritaria de intervención y justificación técnica

3. VISIÓN 2030
   - Enunciado de visión para Villa María como ciudad verde líder en ciudades intermedias de Argentina
   - 3 objetivos estratégicos medibles

4. LÍNEAS DE ACCIÓN (mínimo 5, priorizadas 🔴🟡🟢)
   Para cada línea:
   - Nombre y descripción
   - Justificación con datos del sistema
   - Acciones concretas (mínimo 3 por línea)
   - Indicador de seguimiento
   - Plazo estimado

5. METAS CUANTIFICABLES 2025–2030
   - Tabla con indicador, valor actual, meta 2030, responsable

6. IMPACTO PROYECTADO
   - Captura de CO₂ adicional al cumplir metas
   - Reducción de temperatura proyectada
   - Mejora en salud pública (metodología Lancet)
   - Equivalencias comprensibles (autos, vuelos, vidas)

7. MARCO NORMATIVO Y ALINEACIÓN INTERNACIONAL
   - Normativa local aplicable
   - Alineación con Agenda 2030, C40, Acuerdo de París

8. PRESUPUESTO ESTIMADO REFERENCIAL
   - Por línea de acción
   - Total estimado por año y para el período 2025–2030
   - Fuentes de financiamiento posibles (municipal, provincial, fondos climáticos)

9. GOBERNANZA Y SEGUIMIENTO
   - Estructura de gestión propuesta
   - Frecuencia de monitoreo con datos satelitales
   - Indicadores clave de desempeño (KPIs)

10. CONCLUSIÓN
    - Síntesis del compromiso climático de Villa María
    - Próximos pasos inmediatos (primeros 90 días)

INSTRUCCIONES:
- Usá los datos reales del sistema en cada sección donde apliquen
- Sé específico: no generalices, anclá cada afirmación en los datos provistos
- Escribí en español formal pero accesible para funcionarios municipales
- Usá el foco adicional que te provea el usuario para personalizar el plan
- Formato: texto estructurado con títulos claros, no uses markdown excesivo
- Extensión: documento completo y sustancioso (2.000-3.500 palabras)
"""


def _llamar_opus(foco: str, usuario: str) -> tuple[str, int, int]:
    """Llama a Claude Opus 4.7 y devuelve (texto, tok_in, tok_out)."""
    if not ANTHROPIC_API_KEY:
        return "⚠️ ANTHROPIC_API_KEY no configurada.", 0, 0

    prompt_usuario = f"""
{CONTEXTO_VM}

FOCO ESPECÍFICO DEL PLAN (indicado por el usuario):
{foco}

Generá el Masterplan Ambiental completo para Villa María siguiendo la estructura
indicada, incorporando el foco específico en las líneas de acción prioritarias.
"""
    headers = {
        "x-api-key":         ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type":      "application/json",
    }
    payload = {
        "model":      MODEL_OPUS,
        "max_tokens": 4096,
        "system":     SYSTEM_MASTERPLAN,
        "messages":   [{"role": "user", "content": prompt_usuario}],
    }
    try:
        r = requests.post(API_URL, headers=headers, json=payload, timeout=120)
        r.raise_for_status()
        data     = r.json()
        texto    = data["content"][0]["text"]
        tok_in   = data.get("usage", {}).get("input_tokens",  0)
        tok_out  = data.get("usage", {}).get("output_tokens", 0)
        return texto, tok_in, tok_out
    except requests.exceptions.Timeout:
        return "⚠️ Tiempo de espera agotado (120s). Intentá de nuevo.", 0, 0
    except Exception as e:
        return f"⚠️ Error: {str(e)}", 0, 0


def render_masterplan():
    """Sección completa del Masterplan. Llamar desde modulo_villamaria.py."""

    # Inyectar overlay orbe una sola vez
    if "cv_orbe_injected" not in st.session_state:
        st.markdown(_ORBE_HTML, unsafe_allow_html=True)
        st.session_state["cv_orbe_injected"] = True

    st.title("📄 Masterplan Ambiental · Villa María")
    st.caption(
        "Generado por Claude Opus 4.7 · contexto: Ciudad Verde AI Agent · "
        "datos reales ESA WorldCover + Landsat 8/9 + OSM + INDEC 2022"
    )
    st.markdown("---")

    # Intro
    st.markdown("""
    El Masterplan es un documento ejecutivo completo generado por **Claude Opus 4.7**
    — el modelo de mayor capacidad de Anthropic — utilizando como contexto todos los
    datos ambientales reales de Villa María que provee esta plataforma.

    El resultado es un plan de política pública accionable, con metas cuantificables,
    presupuesto referencial y alineación con estándares internacionales (C40, ODS, Acuerdo de París).
    """)

    # Estimación de costo
    st.info(
        "💡 **Nota:** la generación del Masterplan consume Claude Opus 4.7 "
        "(~2.000–4.000 tokens de output). Costo estimado por generación: USD 0.10–0.25."
    )

    st.markdown("---")
    st.markdown("### ✏️ Foco del plan")
    st.markdown(
        "Indicá el enfoque prioritario para personalizar el Masterplan. "
        "Por ejemplo: *forestación del centro-norte*, *parque lineal del Ctalamochita*, "
        "*cumplimiento del target C40 2030*, *reducción de isla de calor*, etc."
    )

    # Aplicar foco sugerido si viene de un botón
    if "mp_foco_set" in st.session_state:
        st.session_state["mp_foco"] = st.session_state.pop("mp_foco_set")

    foco = st.text_area(
        "Foco y prioridades",
        placeholder="Ejemplo: Priorizar la forestación de la zona Noroeste (VM centro-norte) "
                    "que es la más caliente (+0.79°C), junto con el desarrollo del parque lineal "
                    "sobre el Río Ctalamochita como corredor verde y recreativo.",
        height=120,
        key="mp_foco",
    )

    # Focos sugeridos
    st.markdown("**Focos sugeridos:**")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🌳 Forestación urbana", key="mp_sug1", use_container_width=True):
            st.session_state["mp_foco_set"] = (
                "Forestación masiva del área urbana con foco en la zona Noroeste "
                "(la más caliente), incremento del arbolado del 8.2% al 15%, "
                "uso de especies nativas y corredores verdes entre barrios."
            )
            st.rerun()
    with col2:
        if st.button("💧 Parque Ctalamochita", key="mp_sug2", use_container_width=True):
            st.session_state["mp_foco_set"] = (
                "Desarrollo del parque lineal sobre el Río Ctalamochita como "
                "corredor ecológico y recreativo principal del conglomerado VM-VN, "
                "con ciclovías, senderos, arbolado ribereño y áreas de picnic."
            )
            st.rerun()
    with col3:
        if st.button("🌍 Cumplimiento C40 2030", key="mp_sug3", use_container_width=True):
            st.session_state["mp_foco_set"] = (
                "Cumplimiento del target C40 Urban Nature Declaration 2030: "
                "alcanzar el 30% de cobertura verde (QTC) incorporando 227 ha adicionales "
                "a ritmo de 45.4 ha/año, con énfasis en verde público accesible y captura de CO₂."
            )
            st.rerun()

    st.markdown("---")

    # Botón generar
    col_gen, col_info = st.columns([2, 3])
    with col_gen:
        generar = st.button(
            "🚀 Generar Masterplan con Opus 4.7",
            key="mp_generar",
            use_container_width=True,
            type="primary",
        )
    with col_info:
        st.markdown(
            "<div style='padding:9px 0;font-family:\"Space Mono\",monospace;"
            "font-size:10px;color:rgba(170,176,200,0.6);'>"
            "⏱️ Tiempo estimado: 30–60 segundos · "
            "Modelo: Claude Opus 4.7 · "
            "Output: 2.000–3.500 palabras</div>",
            unsafe_allow_html=True,
        )

    # ── Historial guardado en PostgreSQL ──────────────────────────────────────
    masteplans_guardados = obtener_masteplans(limit=5)
    if masteplans_guardados:
        with st.expander(f"📂 Masteplans guardados ({len(masteplans_guardados)} recientes)", expanded=False):
            for mp in masteplans_guardados:
                fecha = mp["fecha"]
                fecha_str = fecha.strftime("%d/%m/%Y %H:%M") if hasattr(fecha, "strftime") else str(fecha)[:16]
                foco_guardado = (mp["foco"] or "")[:120]
                col_mp, col_load = st.columns([5, 1])
                with col_mp:
                    st.markdown(
                        f"<div style='font-family:\"Space Mono\",monospace;font-size:10px;"
                        f"color:rgba(170,176,200,0.7);'>"
                        f"<b style='color:#9060ff;'>#{mp['id']}</b> · {fecha_str} · "
                        f"<span style='color:rgba(200,188,255,0.6)'>{mp['palabras'] or 0:,} palabras</span><br>"
                        f"<span style='font-size:9px;color:rgba(150,160,200,0.5);'>{foco_guardado}…</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                with col_load:
                    if st.button("Cargar", key=f"mp_load_{mp['id']}", use_container_width=True):
                        st.session_state["mp_resultado"]    = mp["texto"]
                        st.session_state["mp_tok_in"]       = mp["tok_input"] or 0
                        st.session_state["mp_tok_out"]      = mp["tok_output"] or 0
                        st.session_state["mp_id_guardado"]  = mp["id"]
                        st.session_state["mp_fecha_guardado"] = fecha_str
                        st.rerun()

    st.markdown("---")

    # ── Generar ───────────────────────────────────────────────────────────────
    if generar:
        foco_final = st.session_state.get("mp_foco", "").strip()
        if not foco_final:
            st.warning("Ingresá un foco para personalizar el Masterplan.")
        else:
            st.session_state["mp_foco_en_proceso"] = foco_final
            st.markdown(
                "<script>if(typeof cvMostrarOrbe==='function')cvMostrarOrbe();</script>",
                unsafe_allow_html=True,
            )
            with st.spinner("Claude Opus 4.7 generando el Masterplan…"):
                usuario = st.session_state.get("cv_usuario", "usuarioverde")
                texto, tok_in, tok_out = _llamar_opus(foco_final, usuario)

            st.markdown(
                f"<script>if(typeof cvOcultarOrbe==='function')cvOcultarOrbe({tok_in+tok_out});</script>",
                unsafe_allow_html=True,
            )

            if tok_in > 0:
                # Registrar consumo
                registrar_consumo(
                    usuario=usuario,
                    tipo="opus",
                    pregunta=f"[MASTERPLAN] {foco_final[:200]}",
                    tok_input=tok_in,
                    tok_output=tok_out,
                    modelo=MODEL_OPUS,
                )
                # Guardar Masterplan en PostgreSQL
                nuevo_id = guardar_masterplan(
                    usuario=usuario,
                    foco=foco_final,
                    texto=texto,
                    tok_input=tok_in,
                    tok_output=tok_out,
                )
                st.session_state["mp_id_guardado"]    = nuevo_id
                st.session_state["mp_fecha_guardado"] = "recién generado"

            st.session_state["mp_resultado"] = texto
            st.session_state["mp_tok_in"]    = tok_in
            st.session_state["mp_tok_out"]   = tok_out
            st.rerun()

    # ── Mostrar resultado ─────────────────────────────────────────────────────
    if "mp_resultado" in st.session_state:
        texto   = st.session_state["mp_resultado"]
        tok_in  = st.session_state.get("mp_tok_in",  0)
        tok_out = st.session_state.get("mp_tok_out", 0)
        costo   = (tok_in * 15.0 + tok_out * 75.0) / 1_000_000
        mp_id   = st.session_state.get("mp_id_guardado", "")
        mp_fecha = st.session_state.get("mp_fecha_guardado", "")

        # Badge guardado
        if mp_id:
            st.success(f"✅ Masterplan #{mp_id} guardado en base de datos · {mp_fecha}")

        # Métricas
        mc1, mc2, mc3, mc4 = st.columns(4)
        with mc1: st.metric("Tokens input",      f"{tok_in:,}")
        with mc2: st.metric("Tokens output",     f"{tok_out:,}")
        with mc3: st.metric("Costo generación",  f"USD {costo:.4f}")
        with mc4: st.metric("Palabras aprox.",   f"{len(texto.split()):,}")

        st.markdown("---")

        # ── CSS de impresión + documento ──────────────────────────────────────
        import html as _html
        texto_escaped = _html.escape(texto)

        # Construir HTML del documento para pantalla Y para window.print()
        lineas_html = []
        for linea in texto.split("\n"):
            if linea.strip() == "":
                lineas_html.append("<div class='mp-spacer'></div>")
            elif linea.startswith("# ") or (linea.isupper() and len(linea) < 80):
                lineas_html.append(
                    f"<div class='mp-h1'>{_html.escape(linea.lstrip('# '))}</div>"
                )
            elif linea.startswith("## ") or (linea.endswith(":") and len(linea) < 60):
                lineas_html.append(
                    f"<div class='mp-h2'>{_html.escape(linea.lstrip('# '))}</div>"
                )
            elif linea.startswith("- ") or linea.startswith("• "):
                lineas_html.append(
                    f"<div class='mp-li'>◦ {_html.escape(linea[2:])}</div>"
                )
            elif linea.startswith("|"):
                lineas_html.append(
                    f"<div class='mp-table-row'>{_html.escape(linea)}</div>"
                )
            else:
                lineas_html.append(
                    f"<div class='mp-p'>{_html.escape(linea)}</div>"
                )

        documento_inner = "\n".join(lineas_html)
        import datetime as _dt
        fecha_gen = _dt.datetime.now().strftime("%d de %B de %Y")

        st.markdown(f"""
<style>
/* ── Estilos pantalla ── */
.mp-doc {{
    background:rgba(10,14,32,0.6);
    border:0.5px solid rgba(120,140,255,0.20);
    border-radius:12px;
    padding:28px 32px;
    font-family:'Space Grotesk',sans-serif;
    font-size:14px;color:#dde3f5;line-height:1.8;
}}
.mp-h1 {{
    font-family:'Space Mono',monospace;font-size:13px;font-weight:700;
    letter-spacing:0.06em;color:#9060ff;
    margin:18px 0 8px 0;
    border-bottom:0.5px solid rgba(120,140,255,0.2);padding-bottom:6px;
}}
.mp-h2 {{
    font-family:'Space Mono',monospace;font-size:11px;font-weight:700;
    letter-spacing:0.08em;color:#00b4dc;margin:14px 0 6px 0;
}}
.mp-li  {{ padding-left:16px;margin:3px 0;color:#dde3f5; }}
.mp-p   {{ margin:4px 0;color:#dde3f5; }}
.mp-table-row {{ font-family:'Space Mono',monospace;font-size:11px;
    color:rgba(200,210,240,0.75);margin:2px 0; }}
.mp-spacer {{ height:8px; }}

/* ── Estilos de impresión ── */
@media print {{
    body {{ background:#fff !important; color:#111 !important; }}
    /* Ocultar TODO Streamlit excepto el documento */
    header, footer, [data-testid="stSidebar"],
    [data-testid="stToolbar"], [data-testid="stDecoration"],
    .stButton, .stMetric, .stDownloadButton,
    [data-testid="stHeader"], #cv-print-btn-row,
    .element-container:not(.cv-printable) {{ display:none !important; }}

    .mp-doc {{
        background:#fff !important;border:none !important;
        border-radius:0 !important;padding:0 !important;
        color:#111 !important;
    }}
    .mp-h1 {{
        color:#2e4a1e !important;font-size:14pt !important;
        border-bottom:1px solid #ccc !important;
    }}
    .mp-h2  {{ color:#1a3a6e !important;font-size:11pt !important; }}
    .mp-li  {{ color:#111 !important; }}
    .mp-p   {{ color:#222 !important; }}
    .mp-table-row {{ color:#333 !important; }}

    /* Header de impresión */
    #cv-print-header {{ display:block !important; }}
    /* Footer de impresión */
    #cv-print-footer {{ display:block !important; }}
}}

#cv-print-header {{
    display:none;
    font-family:'Arial',sans-serif;
    border-bottom:2px solid #2e4a1e;
    padding-bottom:14px;margin-bottom:24px;
}}
#cv-print-header .ph-logo {{
    font-size:9pt;font-weight:700;letter-spacing:0.12em;
    color:#2e4a1e;text-transform:uppercase;
}}
#cv-print-header .ph-titulo {{
    font-size:18pt;font-weight:700;color:#1a1a1a;margin:6px 0 2px 0;
}}
#cv-print-header .ph-sub {{
    font-size:9pt;color:#555;
}}
#cv-print-footer {{
    display:none;
    font-family:'Arial',sans-serif;font-size:8pt;color:#888;
    border-top:1px solid #ddd;padding-top:10px;margin-top:32px;
    text-align:center;
}}
</style>

<div class="mp-doc cv-printable" id="cv-masterplan-doc">

  <!-- Header solo visible en impresión -->
  <div id="cv-print-header">
    <div class="ph-logo">🌿 Ciudad Verde AI Agent · Municipio de Villa María · Córdoba, Argentina</div>
    <div class="ph-titulo">Masterplan Ambiental 2025–2030</div>
    <div class="ph-sub">
      Generado con Claude Opus 4.7 · {fecha_gen} · 
      Datos: ESA WorldCover 2020 · Landsat 8/9 · OpenStreetMap · INDEC Censo 2022
    </div>
  </div>

  {documento_inner}

  <!-- Footer solo visible en impresión -->
  <div id="cv-print-footer">
    Ciudad Verde AI Agent · Datos: ESA WorldCover 2020 · Landsat 8/9 · OSM · INDEC 2022 ·
    Marco: C40, ODS 11, Acuerdo de París, Ordenanza 7209/2017 ·
    Generado el {fecha_gen}
  </div>

</div>
""", unsafe_allow_html=True)

        st.markdown("---")

        # ── Botones de acción ─────────────────────────────────────────────────
        col_print, col_dl, col_new, _ = st.columns([2, 2, 2, 1])
        with col_print:
            st.markdown(
                """<button onclick="window.print()"
                   style="width:100%;background:linear-gradient(135deg,#6228b4,#00b4dc);
                          border:none;border-radius:8px;color:#fff;
                          font-family:'Space Grotesk',sans-serif;font-size:14px;
                          font-weight:600;padding:10px;cursor:pointer;
                          transition:opacity 0.2s;"
                   onmouseover="this.style.opacity=0.85"
                   onmouseout="this.style.opacity=1">
                   🖨️ Imprimir / Guardar PDF
                </button>""",
                unsafe_allow_html=True,
            )
        with col_dl:
            st.download_button(
                "⬇️ Descargar .txt",
                data=texto.encode("utf-8"),
                file_name="masterplan_villa_maria.txt",
                mime="text/plain",
                key="mp_download",
                use_container_width=True,
            )
        with col_new:
            if st.button("🔄 Generar nuevo", key="mp_nuevo", use_container_width=True):
                for k in ("mp_resultado", "mp_tok_in", "mp_tok_out",
                          "mp_id_guardado", "mp_fecha_guardado"):
                    st.session_state.pop(k, None)
                st.rerun()

    st.markdown("---")
    st.caption(
        "Ciudad Verde AI Agent · Masterplan generado con Claude Opus 4.7 · "
        "Datos: ESA WorldCover 2020 · Landsat 8/9 · OSM · INDEC 2022 · "
        "Marco: C40, ODS 11, Acuerdo de París, Ordenanza 7209"
    )
