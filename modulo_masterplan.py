"""
modulo_masterplan.py — Ciudad Verde AI Agent
=============================================
Masterplan Ejecutivo "Villa María, Ciudad Verde 2030".

- Opus completa una estructura fija (herramienta forzada → JSON), no un texto libre:
  no se corta y, si llega incompleta, no se guarda.
- La app arma el documento diseñado (portada, tarjetas, programas, hoja de ruta y
  gráficos SVG) en pantalla y para imprimir / guardar en PDF.
- Los números de las tarjetas y gráficos los calcula la app con sus datos, no el modelo.
- Admin genera; cualquier usuario ve y carga los guardados. Solo admin borra.
"""

import os
import json
import html
import datetime
import requests
import streamlit as st
import streamlit.components.v1 as components
from modulo_db import registrar_consumo, guardar_masterplan, obtener_masteplans, eliminar_masterplan

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
API_URL           = "https://api.anthropic.com/v1/messages"
MODEL_ID          = "claude-opus-5-5"
MODEL_NOMBRE      = "Claude Opus 5.5"
TIPO_CONSUMO      = "opus55"          # clave de COSTOS en modulo_db.py
PRECIO_INPUT      = 4.00              # USD por millón de tokens — verificar en la facturación
PRECIO_OUTPUT     = 20.00
MAX_TOKENS        = 16000
TIMEOUT_S         = 420

TITULO_PLAN  = "Villa María, Ciudad Verde 2030"
GESTION      = "Gestión Eduardo Accastello"
FUENTES_DATOS = ("ESA WorldCover 2020 · Copa Meta/WRI 1 m · Landsat 8/9 · OSM · "
                 "INDEC 2022 · Zonas por barrio (municipio)")

# ── Municipios soportados ─────────────────────────────────
MUNICIPIOS = {
    'villamaria': {'nombre': 'Villa María', 'archivo': 'villa_maria', 'genera': True},
    'villanueva': {'nombre': 'Villa Nueva', 'archivo': 'villa_nueva', 'genera': False},
}


# ============================================================
# CONTEXTO DINÁMICO — todos los números salen de la app
# ============================================================

def _num(n):
    return f"{int(round(n)):,}".replace(",", ".")


def _dec(x, d=1):
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _texto_seguro(funcion, *args):
    """Llama a una función que lee Postgres; si falla, devuelve texto vacío."""
    try:
        return funcion(*args) or ""
    except Exception as e:
        print(f"[masterplan] Error armando contexto ({funcion.__name__}): {e}")
        return ""


def _contexto_vm():
    """Arma el bloque de datos para el prompt. Devuelve (texto, a) o (None, None)
    si faltan los datos precalculados."""
    from modulo_villamaria import DATOS_VM
    from modulo_agenda2030 import (calcular_agenda2030, TASA_SECUESTRO_NETA, C_A_CO2,
                                   LANCET_FOCALIZADO, ANIO_INICIO, ANIO_META)
    from modulo_barrios import _cargar_resumen
    from modulo_benchmarking import texto_decisiones_para_prompt
    from modulo_huella_eventos import texto_eventos_para_prompt, HUELLA_HAB_TOTAL_T, PARTE_AGRO
    from modulo_bonos_verdes import texto_financiamiento_para_prompt
    a = calcular_agenda2030()
    if not a:
        return None, None

    cob = DATOS_VM['cobertura']
    acc = DATOS_VM['acceso']
    lst = DATOS_VM['lst']
    osm = DATOS_VM['osm']
    m = a['meta_municipal']
    res = _cargar_resumen()

    # Barrios con menos copa (regla 3-30-300)
    menos_copa = "; ".join(
        f"{b['barrio']} {_dec(b['copa_pct'])} %" for b in a['barrios_copa'][:5]
    )
    # Barrios con mayor déficit de la meta municipal
    mayor_deficit = ""
    if res and res.get('barrios'):
        ordenados = sorted(
            (b for b in res['barrios'] if b.get('meta_1_arbol_por_casa')),
            key=lambda b: b['meta_1_arbol_por_casa']['deficit_arboles'], reverse=True,
        )[:5]
        mayor_deficit = "; ".join(
            f"{b['barrio'].title()} faltan {_num(b['meta_1_arbol_por_casa']['deficit_arboles'])} "
            f"({_dec(b['meta_1_arbol_por_casa']['cumplimiento_pct'])} % cumplido)"
            for b in ordenados
        )

    # Escenario 30 % de copa en toda la ciudad
    copa_30_m2 = a['area_ha'] * 0.30 * 10_000
    co2_30 = copa_30_m2 * TASA_SECUESTRO_NETA / 1000 * C_A_CO2

    # Huella anual de la ciudad (promedio nacional, supuesto)
    huella_total = HUELLA_HAB_TOTAL_T * a['poblacion']
    huella_urbana = huella_total * (1 - PARTE_AGRO)

    decisiones = _texto_seguro(texto_decisiones_para_prompt, "Villa María")
    if not decisiones:
        decisiones = ("DECISIONES DEL MUNICIPIO EN LÍNEA CON C40: el administrador todavía no "
                      "cargó decisiones. Indicalo en el documento y proponé prioridades "
                      "a partir de las brechas medidas.")
    eventos = _texto_seguro(texto_eventos_para_prompt, "Villa María", None)
    if not eventos:
        eventos = "HUELLA DE CARBONO DE EVENTOS: no hay eventos registrados todavía."
    financiamiento = _texto_seguro(texto_financiamiento_para_prompt)
    if not financiamiento:
        financiamiento = ("FUENTES DE FINANCIAMIENTO: no se pudo leer el catálogo. "
                          "Dejá el campo 'financiamiento' vacío en todos los programas.")

    lineas = [
        "DATOS DE LA PLATAFORMA CIUDAD VERDE — VILLA MARÍA (Córdoba, Argentina)",
        "=" * 70,
        "",
        "DATOS GENERALES:",
        f"- Población: {_num(a['poblacion'])} habitantes (INDEC, Censo 2022)",
        f"- Área analizada: {_dec(a['area_ha'] / 100)} km² ({_num(a['area_ha'])} ha), "
        f"{res['ciudad']['n_barrios'] if res else 38} barrios oficiales",
        "- Villa Nueva está en la margen opuesta del Río Ctalamochita y NO está incluida en estos datos.",
        "",
        "COBERTURA DEL SUELO (ESA WorldCover 2020, 10 m):",
        f"- Árboles {_dec(cob.get('arboles') or 0)} % · Arbustos {_dec(cob.get('arbustos') or 0)} % · "
        f"Pastizales {_dec(cob.get('pastizales') or 0)} % · Cultivos {_dec(cob.get('cultivos') or 0)} % · "
        f"Edificado {_dec(cob.get('edificado') or 0)} % · Suelo desnudo {_dec(cob.get('suelo') or 0)} % · "
        f"Agua {_dec(cob.get('agua') or 0)} %",
        "",
        "COPA ARBÓREA (Meta/WRI, 1 m; imagen 2018):",
        f"- Árboles contados: {_num(a['total_arboles'])}",
        f"- Superficie de copa: {_dec(a['copa_ha'])} ha = {_dec(a['copa_pct'])} % del área de los barrios",
        f"- Copa media por árbol: {_dec(a['copa_media_m2'])} m²",
        f"- Barrios con 30 % de copa o más: {a['barrios_30']} de {len(a['barrios_copa'])}",
        f"- Barrios con menos copa: {menos_copa}",
        "",
        "ACCESO A ESPACIOS VERDES:",
        f"- Área edificada con verde a menos de 300 m: {_dec(acc.get('acceso') or 0, 0)} % "
        f"(distancia promedio {_num(acc.get('dist_prom') or 0)} m)",
        f"- Verde satelital por habitante: {_dec(acc.get('m2_hab_sat') or 0)} m²/hab",
        f"- Verde público catalogado en OpenStreetMap: {_dec(osm.get('m2Hab') or 0)} m²/hab "
        f"({_num(osm.get('elementos') or 0)} espacios, {_dec(osm.get('areaHa') or 0)} ha)",
        "",
        f"TEMPERATURA SUPERFICIAL (Landsat 8/9, {lst.get('nImagenes') or '—'} imágenes de verano):",
        f"- Temperatura media: {_dec(lst.get('tMedia') or 0)} °C · Isla de calor ΔT: "
        f"+{_dec(lst.get('deltaUHI') or 0)} °C",
        f"- Diferencia entre zonas con vegetación densa y sin vegetación: {_dec(a['enfriamiento'])} °C",
        "",
        "C40 URBAN NATURE ACCELERATOR (metas a 2030):",
        f"- Meta 1 (30–40 % de superficie verde o permeable): {_dec(a['qtc'])} % → "
        f"{'CUMPLIDA' if a['meta1_cumplida'] else 'NO cumplida'}. "
        f"Sin contar cultivos sería {_dec(a['qtc_sin_cultivos'])} %: si los cultivos se urbanizan, la meta se pierde.",
        f"- Meta 2 (70 % de la población a 15 minutos de verde): aproximación de la app "
        f"{_dec(a['acceso_aprox'], 0)} % (proxy: verde a menos de 300 m del área edificada; "
        f"no es el cálculo oficial de C40).",
        "",
        "REGLA 3-30-300 (Konijnendijk, 2021):",
        f"- Copa actual {_dec(a['copa_pct'])} % frente a la meta de 30 % por barrio",
        f"- Para llevar cada barrio al 30 % faltan {_num(a['falta_30_ha'])} ha de copa ≈ "
        f"{_num(a['arboles_30'])} árboles adultos",
        "",
    ]
    if m:
        lineas += [
            "META MUNICIPAL: 1 ÁRBOL POR CASA (zonas con casas: céntrica, residencial, mixta y ribereña):",
            f"- Lotes estimados: {_num(m['lotes_estimados'])} · árboles en esas zonas: "
            f"{_num(m['arboles_zonas_casas'])}",
            f"- Cumplimiento: {_dec(m['cumplimiento_pct'])} % · déficit: {_num(m['deficit_arboles'])} árboles",
            f"- Ritmo para cumplir en {ANIO_INICIO}–{ANIO_META}: {_num(a['arboles_por_anio_municipal'])} árboles por año",
            f"- Barrios con mayor déficit: {mayor_deficit}" if mayor_deficit else "",
            "",
        ]
    lineas += [
        "CAPTURA DE CO₂ DEL ARBOLADO (Nowak et al. 2013, 0,205 kg C/m² de copa/año, neta):",
        f"- Hoy: {_num(a['co2_meta_t'])} t CO₂/año (equivale a {_num(a['autos_meta'])} autos por año, EPA 4,6 t/auto)",
        f"- Con 30 % de copa en la ciudad: {_num(co2_30)} t CO₂/año",
        f"- Huella anual estimada de la ciudad (promedio nacional INDEC 2022 por habitante, supuesto): "
        f"≈ {_num(huella_total)} t CO₂e en total y ≈ {_num(huella_urbana)} t sin el sector agropecuario. "
        f"El arbolado actual absorbe ≈ {_dec(a['co2_meta_t'] / huella_urbana * 100, 2)} % de la huella urbana.",
        "",
        "SALUD PÚBLICA (Martin et al. 2025, The Lancet Planetary Health, 96 ciudades C40):",
        f"- Cada punto porcentual de verde adicional evitaría ≈ {_dec(a['muertes_punto'])} muertes "
        f"prematuras por año en Villa María (rango {_dec(a['muertes_punto_bajo'])}–{_dec(a['muertes_punto_alto'])})",
        f"- Si el verde se suma en los barrios con menos, el beneficio es {_dec(LANCET_FOCALIZADO[0])} a "
        f"{_dec(LANCET_FOCALIZADO[1])} veces mayor",
        "",
        decisiones,
        "",
        eventos,
        "",
        financiamiento,
        "",
        "MARCO NORMATIVO Y DE REFERENCIA:",
        "- Agenda 2030, ODS 11 (meta 11.7: acceso universal a espacios verdes)",
        "- C40 Urban Nature Accelerator (41 ciudades firmantes, entre ellas Buenos Aires)",
        "- Regla 3-30-300 (IUCN Urban Alliance)",
        "- Acuerdo de París / NDC Argentina",
        "- EU Nature Restoration Law, Art. 8 (referencia internacional)",
        "- Ordenanza 7209 \"Ruralidad Urbana\" de Villa María (2017)",
        "",
        "CORREDOR DEL RÍO CTALAMOCHITA:",
        "- Separa Villa María de Villa Nueva; potencial de parque lineal en ambas márgenes "
        "(la extensión del corredor no está medida en la app: tratarla como dato a relevar).",
    ]
    return "\n".join(l for l in lineas if l is not None), a


def _datos_documento(a):
    """Foto de los números que usa el documento (tarjetas y gráficos).
    Se guarda junto al Masterplan para que siempre muestre las cifras con que se generó."""
    from modulo_villamaria import DATOS_VM
    from modulo_agenda2030 import TASA_SECUESTRO_NETA, C_A_CO2, ANIO_INICIO, ANIO_META, LANCET_FOCALIZADO
    from modulo_huella_eventos import _captura_por_arbol_kg

    acc = DATOS_VM['acceso']
    m = a['meta_municipal']
    captura_kg, _ = _captura_por_arbol_kg()

    logros, oportunidades = [], []
    (logros if a['meta1_cumplida'] else oportunidades).append({
        'titulo': 'Meta 1 de C40', 'valor': f"{_dec(a['qtc'])} %",
        'detalle': 'de superficie verde · meta C40 30–40 %'})
    logros.append({'titulo': 'Acceso al verde', 'valor': f"{_dec(acc.get('acceso') or 0, 0)} %",
                   'detalle': 'del área edificada a menos de 300 m de un espacio verde'})
    logros.append({'titulo': 'Árboles medidos', 'valor': _num(a['total_arboles']),
                   'detalle': 'contados uno por uno con imagen de 1 m de resolución'})
    logros.append({'titulo': 'CO₂ capturado', 'valor': f"{_num(a['co2_meta_t'])} t/año",
                   'detalle': f"equivale a {_num(a['autos_meta'])} autos fuera de circulación"})
    oportunidades.append({'titulo': 'Copa arbórea', 'valor': f"{_dec(a['copa_pct'])} % → 30 %",
                          'detalle': 'regla 3-30-300: más sombra en cada barrio'})
    if m:
        oportunidades.append({'titulo': '1 árbol por casa', 'valor': f"{_dec(m['cumplimiento_pct'])} % → 100 %",
                              'detalle': f"{_num(m['deficit_arboles'])} árboles para 2030 · "
                                         f"{_num(a['arboles_por_anio_municipal'])} por año"})

    # Árboles nuevos acumulados para la meta municipal (ritmo lineal)
    anios = list(range(ANIO_INICIO + 1, ANIO_META + 1))
    arboles = {}
    if m and anios:
        paso = m['deficit_arboles'] / len(anios)
        arboles = {'anios': anios, 'acumulado': [paso * (i + 1) for i in range(len(anios))],
                   'por_anio': paso, 'total': m['deficit_arboles']}

    # Captura de CO₂ en tres escenarios (árboles adultos)
    co2 = [{'etiqueta': 'Hoy', 'valor': a['co2_meta_t']}]
    if m and captura_kg:
        co2.append({'etiqueta': '1 árbol por casa', 'valor': a['co2_meta_t'] + m['deficit_arboles'] * captura_kg / 1000})
    co2.append({'etiqueta': '30 % de copa', 'valor': a['area_ha'] * 0.30 * 10_000 * TASA_SECUESTRO_NETA / 1000 * C_A_CO2})

    return {
        'fecha': datetime.date.today().isoformat(),
        'logros': logros,
        'oportunidades': oportunidades,
        'copa_barrios': [{'barrio': b['barrio'], 'pct': b['copa_pct']} for b in a['barrios_copa']],
        'arboles': arboles,
        'co2': co2,
        'enfriamiento': a['enfriamiento'],
        'muertes_punto': a['muertes_punto'],
        'muertes_rango': [a['muertes_punto_bajo'], a['muertes_punto_alto']],
        'focalizado': list(LANCET_FOCALIZADO),
        'anio_inicio': ANIO_INICIO,
        'anio_meta': ANIO_META,
    }


# ============================================================
# MODELO — estructura fija vía herramienta forzada
# ============================================================

_TXT = {"type": "string"}
_ANIO = {"type": "integer", "minimum": 2026, "maximum": 2030}

ESQUEMA = {
    "type": "object",
    "properties": {
        "lema": {"type": "string", "description": "Frase de visión para la portada, máximo 15 palabras."},
        "resumen_ejecutivo": {"type": "string", "description": "Máximo 110 palabras, tono de oportunidad."},
        "lectura_hoy": {"type": "string", "description": "Máximo 70 palabras: qué logró la ciudad y qué oportunidad abre."},
        "vision": {"type": "string", "description": "Máximo 50 palabras."},
        "objetivos": {
            "type": "array", "minItems": 3, "maxItems": 3,
            "items": {"type": "object", "properties": {
                "titulo": _TXT, "meta_2030": _TXT, "indicador": _TXT},
                "required": ["titulo", "meta_2030", "indicador"]},
        },
        "programas": {
            "type": "array", "minItems": 4, "maxItems": 6,
            "items": {"type": "object", "properties": {
                "nombre": {"type": "string", "description": "Nombre propio, corto y comunicable."},
                "emoji": _TXT,
                "prioridad": {"type": "string", "enum": ["Alta", "Media", "Baja"]},
                "objetivo": {"type": "string", "description": "Una oración."},
                "por_que": {"type": "string", "description": "Máximo 40 palabras, con un dato del bloque."},
                "barrios_inicio": {"type": "array", "items": _TXT, "maxItems": 5},
                "acciones": {"type": "array", "items": _TXT, "minItems": 3, "maxItems": 5},
                "primera_accion_visible": _TXT,
                "indicador": _TXT,
                "meta_2030": _TXT,
                "inicio": _ANIO,
                "fin": _ANIO,
                "hitos": {"type": "array", "maxItems": 4, "items": {"type": "object", "properties": {
                    "anio": _ANIO, "texto": _TXT}, "required": ["anio", "texto"]}},
            }, "required": ["nombre", "emoji", "prioridad", "objetivo", "por_que", "barrios_inicio",
                            "acciones", "primera_accion_visible", "indicador", "meta_2030",
                            "inicio", "fin", "hitos"]},
        },
        "impacto": {"type": "object", "properties": {
            "arbolado": _TXT, "clima": _TXT, "salud": _TXT, "eventos": _TXT},
            "required": ["arbolado", "clima", "salud", "eventos"]},
        "gobernanza": {"type": "object", "properties": {
            "conduccion": _TXT, "seguimiento": _TXT,
            "indicadores": {"type": "array", "items": _TXT, "minItems": 3, "maxItems": 6}},
            "required": ["conduccion", "seguimiento", "indicadores"]},
        "primeros_90_dias": {
            "type": "array", "minItems": 5, "maxItems": 8,
            "items": {"type": "object", "properties": {"plazo": _TXT, "accion": _TXT},
                      "required": ["plazo", "accion"]},
        },
        "cierre": {"type": "string", "description": "Máximo 60 palabras."},
    },
    "required": ["lema", "resumen_ejecutivo", "lectura_hoy", "vision", "objetivos", "programas",
                 "impacto", "gobernanza", "primeros_90_dias", "cierre"],
}


def _system_masterplan() -> str:
    return f"""Sos el equipo de planificación estratégica que prepara el Masterplan
"{TITULO_PLAN}" para presentar al Intendente de Villa María (Córdoba, Argentina).

TONO:
- Ejecutivo, claro y de liderazgo. Frases cortas. Nada de jerga técnica innecesaria.
- Primero los logros de la ciudad; las brechas se presentan como oportunidades y metas.
- Villa María como ciudad intermedia que lidera en naturaleza urbana.

REGLAS (obligatorias):
- Usá SOLO las cifras del bloque de datos. No inventes cifras, estudios ni superficies.
- NO menciones montos, costos, inversión ni presupuesto en ningún campo.
- El financiamiento va SOLO en el campo "financiamiento" de cada programa: 1 o 2 fuentes
  elegidas por id de FUENTES DE FINANCIAMIENTO, priorizando las que no generan deuda y
  las de mayor avance de requisitos. En "por_que" usá el uso previsto o el requisito pendiente;
  no inventes montos ni plazos de la fuente.
- No incluyas citas ni frases atribuidas al Intendente ni a otras personas reales.
- Los programas siguen el orden de las DECISIONES DEL MUNICIPIO EN LÍNEA CON C40
  (Alta, después Media, después Baja). Si no hay decisiones, ordenalos según las brechas medidas.
- Incluí al menos un programa para la meta 1 árbol por casa y uno para los barrios con menos copa.
- En "barrios_inicio" usá solo nombres de barrios que aparecen en el bloque de datos.
- Los años van de 2026 a 2030.
- Si proponés una cantidad o plazo que no está en los datos, agregá "(supuesto)".
- Los datos son de Villa María; Villa Nueva solo como vecina del corredor del río.
- Formato de números argentino: 31.665 árboles; 10,7 %.
- Respetá los largos máximos de cada campo.

Respondé únicamente llamando a la herramienta entregar_masterplan."""


def _llamar_modelo(foco: str, contexto: str):
    """Devuelve (doc, error, tok_in, tok_out). doc es None si hubo error o vino incompleto."""
    if not ANTHROPIC_API_KEY:
        return None, "ANTHROPIC_API_KEY no configurada.", 0, 0

    prompt_usuario = f"""{contexto}

FOCO DEL PLAN (indicado por el administrador):
{foco}

Prepará el Masterplan Ejecutivo incorporando el foco en los programas prioritarios."""
    headers = {
        "x-api-key":         ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type":      "application/json",
    }
    payload = {
        "model":       MODEL_ID,
        "max_tokens":  MAX_TOKENS,
        "system":      _system_masterplan(),
        "messages":    [{"role": "user", "content": prompt_usuario}],
        "tools":       [{"name": "entregar_masterplan",
                         "description": "Entrega el Masterplan Ejecutivo completo con la estructura fija.",
                         "input_schema": ESQUEMA}],
        "tool_choice": {"type": "auto"},
    }
    try:
        r = requests.post(API_URL, headers=headers, json=payload, timeout=TIMEOUT_S)
        r.raise_for_status()
        data    = r.json()
        tok_in  = data.get("usage", {}).get("input_tokens",  0)
        tok_out = data.get("usage", {}).get("output_tokens", 0)
        if data.get("stop_reason") == "max_tokens":
            return None, "La respuesta llegó incompleta y no se guardó. Generalo de nuevo.", tok_in, tok_out
        doc = next((b.get("input") for b in data.get("content", []) if b.get("type") == "tool_use"), None)
        error = _validar(doc)
        if error:
            return None, error, tok_in, tok_out
        return doc, None, tok_in, tok_out
    except requests.exceptions.Timeout:
        return None, f"Tiempo de espera agotado ({TIMEOUT_S} s). Intentá de nuevo.", 0, 0
    except requests.exceptions.HTTPError:
        return None, f"Error de la API ({r.status_code}): {r.text[:300]}", 0, 0
    except Exception as e:
        return None, f"Error: {e}", 0, 0


def _validar(doc):
    """Chequea que la estructura esté completa. Devuelve el error o None."""
    if not isinstance(doc, dict):
        return "El modelo no devolvió la estructura del Masterplan. Generalo de nuevo."
    faltan = [k for k in ESQUEMA["required"] if not doc.get(k)]
    if faltan:
        return f"La respuesta llegó sin: {', '.join(faltan)}. No se guardó; generalo de nuevo."
    for p in doc["programas"]:
        p["inicio"] = min(max(int(p.get("inicio") or 2026), 2026), 2030)
        p["fin"] = min(max(int(p.get("fin") or 2030), p["inicio"]), 2030)
    return None


# ============================================================
# GRÁFICOS SVG (sirven en pantalla y en el PDF)
# ============================================================

# Paleta de reporte ejecutivo: tinta azul marino, un solo azul de datos y grises.
TINTA      = "#14213d"   # títulos y énfasis
TEXTO      = "#2b2f36"   # cuerpo
SECUNDARIO = "#5c6470"   # notas, ejes
LINEA      = "#d9dde3"   # filetes y grilla
FONDO_SUAVE = "#f4f6f9"
DATO       = "#2f5d9e"   # serie principal
DATO_SUAVE = "#a9bdd8"   # contexto / valores anteriores
ACENTO     = "#c8962e"   # un único acento (hitos, meta)
COLOR_PRIORIDAD = {"Alta": TINTA, "Media": DATO, "Baja": DATO_SUAVE}
_e = html.escape


def _svg_copa_barrios(items, meta=30.0, destacados=()):
    ancho, izq, fila = 760, 190, 19
    area = ancho - izq - 60
    tope = max(meta, max((i['pct'] for i in items), default=0)) * 1.1
    alto = len(items) * fila + 40
    x_meta = izq + meta / tope * area
    dest = {d.strip().lower() for d in destacados}
    partes = [f"<svg viewBox='0 0 {ancho} {alto}' width='100%' role='img' "
              f"aria-label='Copa arbórea por barrio frente a la meta de 30 %'>"]
    for k, it in enumerate(items):
        y = 10 + k * fila
        w = max(2, it['pct'] / tope * area)
        marcado = it['barrio'].strip().lower() in dest
        color = DATO if marcado else DATO_SUAVE
        peso = " font-weight='700'" if marcado else ""
        partes.append(
            f"<g><title>{_e(it['barrio'])}: {_dec(it['pct'])} % de copa</title>"
            f"<text x='{izq - 8}' y='{y + 13}' text-anchor='end' class='sv-lbl'{peso}>{_e(it['barrio'])}</text>"
            f"<rect x='{izq}' y='{y + 3}' width='{w:.1f}' height='{fila - 7}' rx='2' fill='{color}'/>"
            f"<text x='{izq + w + 6:.1f}' y='{y + 13}' class='sv-val'>{_dec(it['pct'])} %</text></g>")
    partes.append(
        f"<line x1='{x_meta:.1f}' y1='4' x2='{x_meta:.1f}' y2='{alto - 22}' stroke='{TINTA}' "
        f"stroke-width='1.25' stroke-dasharray='4 4'/>"
        f"<text x='{x_meta:.1f}' y='{alto - 6}' text-anchor='middle' class='sv-meta'>Meta 30 %</text></svg>")
    return "".join(partes)


def _svg_columnas(etiquetas, valores, textos):
    """Columnas: la última (el destino) en azul, las anteriores en azul suave."""
    ancho, alto, base, techo = 360, 228, 196, 28
    n = len(valores)
    paso = ancho / n
    tope = max(valores) * 1.08 if valores else 1
    partes = [f"<svg viewBox='0 0 {ancho} {alto}' width='100%' role='img'>"]
    for k, (et, v, t) in enumerate(zip(etiquetas, valores, textos)):
        h = (base - techo) * v / tope
        x = k * paso + paso * 0.22
        w = paso * 0.56
        color = DATO if k == n - 1 else DATO_SUAVE
        partes.append(
            f"<g><title>{_e(et)}: {_e(t)}</title>"
            f"<rect x='{x:.1f}' y='{base - h:.1f}' width='{w:.1f}' height='{h:.1f}' rx='2' fill='{color}'/>"
            f"<text x='{x + w / 2:.1f}' y='{base - h - 7:.1f}' text-anchor='middle' class='sv-val-b'>{_e(t)}</text>"
            f"<text x='{x + w / 2:.1f}' y='{base + 20}' text-anchor='middle' class='sv-lbl'>{_e(et)}</text></g>")
    partes.append(f"<line x1='0' y1='{base}' x2='{ancho}' y2='{base}' stroke='{LINEA}'/></svg>")
    return "".join(partes)


def _svg_hoja_ruta(programas, ini=2026, fin=2030):
    anios = list(range(ini, fin + 1))
    ancho, izq, fila = 760, 250, 38
    col = (ancho - izq - 10) / len(anios)
    alto = 34 + len(programas) * fila
    partes = [f"<svg viewBox='0 0 {ancho} {alto}' width='100%' role='img' aria-label='Hoja de ruta'>"]
    for k, a in enumerate(anios):
        x = izq + k * col
        partes.append(
            f"<line x1='{x:.1f}' y1='26' x2='{x:.1f}' y2='{alto}' stroke='{LINEA}'/>"
            f"<text x='{x + col / 2:.1f}' y='18' text-anchor='middle' class='sv-anio'>{a}</text>")
    for k, p in enumerate(programas):
        y = 30 + k * fila
        x1 = izq + (p['inicio'] - ini) * col + 4
        x2 = izq + (p['fin'] - ini + 1) * col - 6
        color = COLOR_PRIORIDAD.get(p.get('prioridad'), DATO)
        partes.append(
            f"<text x='{izq - 12}' y='{y + 19}' text-anchor='end' class='sv-prog'>"
            f"{k + 1:02d}  {_e(p['nombre'][:34])}</text>"
            f"<rect x='{x1:.1f}' y='{y + 8}' width='{x2 - x1:.1f}' height='16' rx='2' fill='{color}'/>")
        for h in p.get('hitos') or []:
            try:
                ha = min(max(int(h['anio']), ini), fin)
            except (TypeError, ValueError, KeyError):
                continue
            cx = izq + (ha - ini) * col + col / 2
            partes.append(f"<rect x='{cx - 5:.1f}' y='{y + 11:.1f}' width='10' height='10' fill='{ACENTO}' "
                          f"stroke='#ffffff' stroke-width='2' transform='rotate(45 {cx:.1f} {y + 16:.1f})'>"
                          f"<title>{h['anio']}: {_e(str(h.get('texto', '')))}</title></rect>")
    partes.append("</svg>")
    return "".join(partes)


# ============================================================
# DOCUMENTO HTML — plantilla de reporte ejecutivo
# ============================================================

_CSS_DOC = """
@import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,500;8..60,600;8..60,700&family=Inter:wght@400;500;600;700&display=swap');
:root { --tinta:#14213d; --texto:#2b2f36; --sec:#5c6470; --linea:#d9dde3; --suave:#f4f6f9; --dato:#2f5d9e; --acento:#c8962e; }
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Inter', Arial, sans-serif; color: var(--texto); background: #e6e8ec; font-size: 14px; line-height: 1.6; }
.doc { max-width: 880px; margin: 0 auto; background: #fff; }
.serif, h1, h2, .vision, .kpi-v, .big { font-family: 'Source Serif 4', Georgia, serif; }
.pag { padding: 48px 64px 40px; }
.cab { display: flex; justify-content: space-between; font-size: 10.5px; letter-spacing: .08em; text-transform: uppercase; color: var(--sec); border-bottom: 1px solid var(--linea); padding-bottom: 8px; margin-bottom: 30px; }
.sec-n { font-size: 11px; font-weight: 700; letter-spacing: .14em; color: var(--acento); text-transform: uppercase; }
h2 { font-size: 27px; font-weight: 600; color: var(--tinta); line-height: 1.2; margin: 4px 0 8px; }
.bajada { font-size: 15px; color: var(--sec); max-width: 640px; margin-bottom: 26px; }
p { margin-bottom: 10px; }
h3 { font-size: 13px; font-weight: 600; color: var(--tinta); margin-bottom: 8px; }
/* Portada */
.portada { min-height: 1000px; display: flex; flex-direction: column; padding: 0; }
.portada .franja { height: 10px; background: var(--tinta); }
.portada .cuerpo { flex: 1; padding: 120px 64px 40px; display: flex; flex-direction: column; }
.portada .tipo { font-size: 11.5px; font-weight: 600; letter-spacing: .18em; text-transform: uppercase; color: var(--acento); }
.portada h1 { font-size: 52px; font-weight: 600; color: var(--tinta); line-height: 1.08; margin: 18px 0 22px; max-width: 780px; }
.portada .filete { width: 64px; height: 3px; background: var(--acento); margin-bottom: 22px; }
.portada .lema { font-size: 19px; color: var(--sec); max-width: 560px; font-family: 'Source Serif 4', Georgia, serif; font-style: italic; }
.portada .pie { margin-top: auto; display: flex; justify-content: space-between; align-items: flex-end; border-top: 1px solid var(--linea); padding-top: 18px; }
.portada .gestion { font-size: 15px; font-weight: 600; color: var(--tinta); }
.portada .muni { font-size: 12.5px; color: var(--sec); }
.portada .fecha { font-size: 12px; color: var(--sec); text-align: right; }
/* Resumen */
.resumen { font-family: 'Source Serif 4', Georgia, serif; font-size: 18px; line-height: 1.6; color: var(--tinta); border-left: 3px solid var(--acento); padding-left: 22px; }
/* KPIs */
.grid { display: grid; gap: 0; }
.g2 { grid-template-columns: repeat(2, 1fr); }
.g3 { grid-template-columns: repeat(3, 1fr); }
.kpis { border-top: 2px solid var(--tinta); margin-bottom: 28px; }
.kpi { padding: 16px 18px 16px 0; border-bottom: 1px solid var(--linea); }
.kpi + .kpi { padding-left: 18px; border-left: 1px solid var(--linea); }
.g2 .kpi:nth-child(odd) { padding-left: 0; border-left: none; }
.kpi-t { font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: .08em; color: var(--sec); }
.kpi-v { font-size: 34px; font-weight: 600; color: var(--tinta); line-height: 1.15; margin: 6px 0 4px; }
.kpi-d { font-size: 12.5px; color: var(--sec); }
.rotulo { display: flex; align-items: center; gap: 10px; font-size: 11px; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; color: var(--tinta); margin-bottom: 0; padding-bottom: 8px; }
.rotulo .t { display: inline-block; padding: 2px 8px; border: 1px solid var(--tinta); border-radius: 2px; font-size: 10px; }
.rotulo .t.op { border-color: var(--acento); color: #8a6417; }
/* Visión y objetivos */
.vision { font-size: 24px; line-height: 1.4; color: var(--tinta); font-weight: 500; margin: 6px 0 30px; max-width: 700px; }
.obj { border-top: 2px solid var(--tinta); padding: 14px 18px 14px 0; }
.obj + .obj { padding-left: 18px; }
.obj .n { font-family: 'Source Serif 4', Georgia, serif; font-size: 30px; color: var(--acento); line-height: 1; }
.obj b { display: block; font-size: 15px; color: var(--tinta); margin: 8px 0 6px; }
.obj .m { font-size: 13.5px; margin-bottom: 8px; }
.obj .i { font-size: 12px; color: var(--sec); border-top: 1px solid var(--linea); padding-top: 6px; }
/* Programas */
.prog { display: grid; grid-template-columns: 56px 1fr; gap: 0 18px; border-top: 1px solid var(--linea); padding: 22px 0; break-inside: avoid; }
.prog:first-of-type { border-top: 2px solid var(--tinta); }
.prog .pn { font-family: 'Source Serif 4', Georgia, serif; font-size: 34px; color: var(--dato); line-height: 1; }
.prog-h { display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap; margin-bottom: 6px; }
.prog-n { font-family: 'Source Serif 4', Georgia, serif; font-size: 21px; font-weight: 600; color: var(--tinta); }
.chip { font-size: 10.5px; font-weight: 600; letter-spacing: .06em; text-transform: uppercase; padding: 2px 8px; border-radius: 2px; color: #fff; }
.chip.Media { background: var(--dato); } .chip.Alta { background: var(--tinta); } .chip.Baja { background: #a9bdd8; color: var(--tinta); }
.per { font-size: 12px; color: var(--sec); }
.prog .obj-p { font-size: 15px; font-weight: 500; color: var(--tinta); margin-bottom: 4px; }
.prog .pq { color: var(--sec); font-size: 13.5px; margin-bottom: 10px; }
.prog .dos { display: grid; grid-template-columns: 1.3fr 1fr; gap: 22px; }
.prog ul { margin: 0 0 0 16px; font-size: 13.5px; }
.prog li { margin-bottom: 3px; }
.ficha { font-size: 12.5px; }
.ficha div { padding: 6px 0; border-bottom: 1px solid var(--linea); }
.ficha div:first-child { border-top: 1px solid var(--linea); }
.ficha b { display: block; font-size: 10.5px; letter-spacing: .08em; text-transform: uppercase; color: var(--sec); font-weight: 600; }
.visible { margin-top: 12px; font-size: 13.5px; padding: 9px 12px; background: var(--suave); border-left: 3px solid var(--acento); }
.visible b { color: var(--tinta); }
.hitos { font-size: 12px; color: var(--sec); margin-top: 8px; }
/* Gráficos */
.graf { padding: 6px 0 18px; break-inside: avoid; }
.graf h3 { border-top: 2px solid var(--tinta); padding-top: 10px; }
.graf .nota, .fuente { font-size: 11.5px; color: var(--sec); margin-top: 4px; }
.g2.gap { gap: 0 32px; }
.sv-lbl { font-size: 11.5px; fill: #2b2f36; font-family: 'Inter', Arial; }
.sv-val { font-size: 11px; fill: #5c6470; font-family: 'Inter', Arial; }
.sv-val-b { font-size: 13px; font-weight: 600; fill: #14213d; font-family: 'Inter', Arial; }
.sv-meta { font-size: 11px; font-weight: 600; fill: #14213d; font-family: 'Inter', Arial; }
.sv-anio { font-size: 12px; font-weight: 600; fill: #5c6470; font-family: 'Inter', Arial; }
.sv-prog { font-size: 12.5px; fill: #14213d; font-family: 'Inter', Arial; font-weight: 500; }
.leyenda { font-size: 11.5px; color: var(--sec); margin-top: 8px; }
.leyenda i { display: inline-block; width: 18px; height: 9px; border-radius: 1px; margin: 0 5px 0 14px; vertical-align: middle; }
.leyenda i.h { width: 9px; height: 9px; background: var(--acento); transform: rotate(45deg); }
.imp { border-top: 2px solid var(--tinta); padding: 12px 0; }
.imp .big { font-size: 32px; font-weight: 600; color: var(--tinta); line-height: 1.15; }
.imp .kpi-d { margin-bottom: 8px; }
/* Gobernanza / 90 días */
.tabla { width: 100%; border-collapse: collapse; font-size: 13.5px; }
.tabla th { text-align: left; font-size: 10.5px; letter-spacing: .08em; text-transform: uppercase; color: var(--sec); font-weight: 600; border-bottom: 2px solid var(--tinta); padding: 8px 10px 8px 0; }
.tabla td { border-bottom: 1px solid var(--linea); padding: 10px 10px 10px 0; vertical-align: top; }
.tabla td.pl { width: 130px; font-weight: 600; color: var(--tinta); white-space: nowrap; }
.tabla td.ck { width: 28px; } .tabla td.ck span { display: inline-block; width: 13px; height: 13px; border: 1.5px solid var(--tinta); }
.ind { list-style: none; columns: 2; column-gap: 32px; font-size: 13.5px; }
.ind li { padding: 7px 0; border-bottom: 1px solid var(--linea); break-inside: avoid; }
.cierre { background: var(--tinta); color: #fff; padding: 44px 64px; }
.cierre p { font-family: 'Source Serif 4', Georgia, serif; font-size: 20px; line-height: 1.5; margin: 0; }
.cierre .firma { font-family: 'Inter', Arial; font-size: 12px; letter-spacing: .1em; text-transform: uppercase; color: #c9cfdb; margin-top: 18px; }
.fuentes { font-size: 10.5px; color: var(--sec); padding: 16px 64px 26px; }
.imprimir { position: fixed; top: 14px; right: 14px; z-index: 9; background: #fff; color: var(--tinta); border: 1px solid var(--tinta); border-radius: 3px; padding: 8px 14px; font: 600 12px 'Inter', Arial; cursor: pointer; }
.imprimir:hover { background: var(--tinta); color: #fff; }
h2, .sec-n, .bajada, h3, .rotulo { break-after: avoid; page-break-after: avoid; }
@media (max-width: 680px) {
  .g2, .g3, .prog .dos { grid-template-columns: 1fr; }
  .kpi + .kpi, .obj + .obj { padding-left: 0; border-left: none; }
  .pag, .portada .cuerpo, .cierre { padding-left: 22px; padding-right: 22px; }
  .portada h1 { font-size: 36px; } .prog { grid-template-columns: 1fr; } .ind { columns: 1; }
}
@page { size: A4; margin: 14mm 0; }
@page :first { margin: 0; }
@media print {
  body { background: #fff; font-size: 12.5px; }
  .doc { max-width: none; }
  .imprimir { display: none; }
  .portada { min-height: 100vh; break-after: page; }
  .salto { break-before: page; }
  .portada .franja, .cierre, .chip, .visible, .leyenda i { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
}
"""


def _html_documento(doc, nombre_municipio="Villa María"):
    d = doc.get('_datos') or {}
    fecha = d.get('fecha') or datetime.date.today().isoformat()
    try:
        fecha_dt = datetime.date.fromisoformat(fecha)
        meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
                 "septiembre", "octubre", "noviembre", "diciembre"]
        fecha_txt = f"{meses[fecha_dt.month - 1].capitalize()} de {fecha_dt.year}"
        fecha_corta = fecha_dt.strftime("%d/%m/%Y")
    except ValueError:
        fecha_txt = fecha_corta = fecha
    ini, fin = d.get('anio_inicio', 2026), d.get('anio_meta', 2030)
    cab = (f"<div class='cab'><span>{_e(TITULO_PLAN)}</span>"
           f"<span>Masterplan Ambiental {ini}–{fin}</span></div>")

    def kpis(items):
        return "".join(
            f"<div class='kpi'><div class='kpi-t'>{_e(k['titulo'])}</div>"
            f"<div class='kpi-v'>{_e(k['valor'])}</div><div class='kpi-d'>{_e(k['detalle'])}</div></div>"
            for k in items)

    objetivos = "".join(
        f"<div class='obj'><div class='n'>{k + 1:02d}</div><b>{_e(o['titulo'])}</b>"
        f"<div class='m'>{_e(o['meta_2030'])}</div><div class='i'>Indicador: {_e(o['indicador'])}</div></div>"
        for k, o in enumerate(doc['objetivos']))

    programas, barrios_destacados = [], []
    for k, p in enumerate(doc['programas']):
        prioridad = p.get('prioridad', 'Media')
        barrios_destacados += p.get('barrios_inicio') or []
        barrios = ", ".join(_e(b) for b in p.get('barrios_inicio') or [])
        acciones = "".join(f"<li>{_e(a)}</li>" for a in p.get('acciones') or [])
        hitos = " · ".join(f"<b>{h.get('anio')}</b> {_e(str(h.get('texto', '')))}" for h in p.get('hitos') or [])
        programas.append(f"""
        <div class='prog'>
          <div class='pn'>{k + 1:02d}</div>
          <div>
            <div class='prog-h'><span class='prog-n'>{_e(p['nombre'])}</span>
              <span class='chip {_e(prioridad)}'>Prioridad {_e(prioridad)}</span>
              <span class='per'>{p['inicio']}–{p['fin']}</span></div>
            <div class='obj-p'>{_e(p['objetivo'])}</div>
            <div class='pq'>{_e(p['por_que'])}</div>
            <div class='dos'>
              <ul>{acciones}</ul>
              <div class='ficha'>
                <div><b>Meta 2030</b>{_e(p['meta_2030'])}</div>
                <div><b>Indicador</b>{_e(p['indicador'])}</div>
                {f"<div><b>Barrios de inicio</b>{barrios}</div>" if barrios else ""}
              </div>
            </div>
            <div class='visible'><b>Primera acción visible:</b> {_e(p['primera_accion_visible'])}</div>
            {f"<div class='hitos'>Hitos: {hitos}</div>" if hitos else ""}
          </div>
        </div>""")

    graf_arboles = ""
    arb = d.get('arboles') or {}
    if arb.get('anios'):
        graf_arboles = f"""<div class='graf'><h3>Árboles nuevos acumulados · meta 1 árbol por casa</h3>
          {_svg_columnas([str(a) for a in arb['anios']], arb['acumulado'], [_num(v) for v in arb['acumulado']])}
          <div class='nota'>Ritmo de {_num(arb['por_anio'])} árboles por año.</div></div>"""
    co2 = d.get('co2') or []
    graf_co2 = ""
    if co2:
        graf_co2 = f"""<div class='graf'><h3>Captura de CO₂ del arbolado · t por año</h3>
          {_svg_columnas([c['etiqueta'] for c in co2], [c['valor'] for c in co2], [_num(c['valor']) for c in co2])}
          <div class='nota'>Con los árboles en tamaño adulto (15 a 20 años).</div></div>"""
    graf_copa = ""
    if d.get('copa_barrios'):
        graf_copa = f"""<div class='graf'><h3>Copa arbórea por barrio frente a la meta de la regla 3-30-300</h3>
          {_svg_copa_barrios(d['copa_barrios'], destacados=barrios_destacados)}
          <div class='nota'>En azul intenso, los barrios donde arrancan los programas.</div></div>"""

    imp = doc['impacto']
    eventos = imp.get('eventos') or ""
    rango = d.get('muertes_rango') or [0, 0]
    foc = d.get('focalizado') or [1.4, 1.7]

    dias = "".join(
        f"<tr><td class='ck'><span></span></td><td class='pl'>{_e(x['plazo'])}</td><td>{_e(x['accion'])}</td></tr>"
        for x in doc['primeros_90_dias'])
    indicadores = "".join(f"<li>{_e(i)}</li>" for i in doc['gobernanza'].get('indicadores') or [])

    return f"""<!DOCTYPE html><html lang='es'><head><meta charset='utf-8'>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<title>{_e(TITULO_PLAN)}</title><style>{_CSS_DOC}</style></head><body>
<button class='imprimir' onclick='window.print()'>Imprimir / Guardar PDF</button>
<div class='doc'>

<section class='portada'>
  <div class='franja'></div>
  <div class='cuerpo'>
    <div class='tipo'>Masterplan Ambiental {ini}–{fin}</div>
    <h1>{_e(TITULO_PLAN)}</h1>
    <div class='filete'></div>
    <div class='lema'>{_e(doc['lema'])}</div>
    <div class='pie'>
      <div><div class='gestion'>{_e(GESTION)}</div><div class='muni'>{_e(nombre_municipio)} · Córdoba, Argentina</div></div>
      <div class='fecha'>{fecha_txt}<br>Ciudad Verde AI Agent</div>
    </div>
  </div>
</section>

<section class='pag salto'>
  {cab}
  <div class='sec-n'>Resumen ejecutivo</div>
  <h2>En síntesis</h2>
  <p class='resumen'>{_e(doc['resumen_ejecutivo'])}</p>
</section>

<section class='pag'>
  <div class='sec-n'>01 · Punto de partida</div>
  <h2>Villa María hoy</h2>
  <div class='bajada'>{_e(doc['lectura_hoy'])}</div>
  <div class='rotulo'><span class='t'>Logros</span> Lo que la ciudad ya alcanzó</div>
  <div class='grid g2 kpis'>{kpis(d.get('logros') or [])}</div>
  <div class='rotulo'><span class='t op'>Oportunidades</span> Hacia 2030</div>
  <div class='grid g2 kpis'>{kpis(d.get('oportunidades') or [])}</div>
</section>

<section class='pag salto'>
  {cab}
  <div class='sec-n'>02 · Visión</div>
  <h2>Visión 2030</h2>
  <div class='vision'>{_e(doc['vision'])}</div>
  <div class='grid g3'>{objetivos}</div>
</section>

<section class='pag'>
  <div class='sec-n'>03 · Programas</div>
  <h2>Programas del Masterplan</h2>
  <div class='bajada'>Ordenados según las decisiones del municipio en línea con C40.</div>
  {''.join(programas)}
</section>

<section class='pag salto'>
  {cab}
  <div class='sec-n'>04 · Hoja de ruta</div>
  <h2>Hoja de ruta {ini}–{fin}</h2>
  <div class='graf'>{_svg_hoja_ruta(doc['programas'], ini, fin)}
    <div class='leyenda'>Prioridad<i style='background:{TINTA}'></i>Alta<i style='background:{DATO}'></i>Media
      <i style='background:{DATO_SUAVE}'></i>Baja<i class='h'></i>Hito</div></div>
</section>

<section class='pag'>
  <div class='sec-n'>05 · Impacto</div>
  <h2>Impacto esperado</h2>
  <div class='bajada'>{_e(imp['arbolado'])}</div>
  <div class='grid g2 gap'>{graf_arboles}{graf_co2}</div>
  {graf_copa}
  <div class='grid g2 gap'>
    <div class='imp'><h3>Clima urbano</h3><div class='big'>{_dec(d.get('enfriamiento') or 0)} °C</div>
      <div class='kpi-d'>más fresco donde hay vegetación densa (Landsat 8/9)</div><p>{_e(imp['clima'])}</p></div>
    <div class='imp'><h3>Salud pública</h3><div class='big'>≈ {_dec(d.get('muertes_punto') or 0)} vidas por año</div>
      <div class='kpi-d'>por cada punto de verde adicional (rango {_dec(rango[0])}–{_dec(rango[1])}); entre
        {_dec(foc[0])} y {_dec(foc[1])} veces más si se suma donde menos hay · Martin et al. 2025</div>
      <p>{_e(imp['salud'])}</p></div>
  </div>
  {f"<div class='imp'><h3>Eventos de la ciudad</h3><p>{_e(eventos)}</p></div>" if eventos else ""}
</section>

<section class='pag salto'>
  {cab}
  <div class='sec-n'>06 · Gobernanza</div>
  <h2>Gobernanza y seguimiento</h2>
  <div class='grid g2 gap'>
    <div class='imp'><h3>Conducción</h3><p>{_e(doc['gobernanza']['conduccion'])}</p></div>
    <div class='imp'><h3>Seguimiento</h3><p>{_e(doc['gobernanza']['seguimiento'])}</p></div>
  </div>
  <h3 style='margin-top:18px'>Indicadores clave</h3>
  <ul class='ind'>{indicadores}</ul>
</section>

<section class='pag'>
  <div class='sec-n'>07 · Acción inmediata</div>
  <h2>Primeros 90 días</h2>
  <table class='tabla'><thead><tr><th></th><th>Plazo</th><th>Acción</th></tr></thead><tbody>{dias}</tbody></table>
</section>

<section class='cierre'><p>{_e(doc['cierre'])}</p>
  <div class='firma'>{_e(GESTION)} · {_e(TITULO_PLAN)}</div></section>
<div class='fuentes'>Fuentes de datos: {_e(FUENTES_DATOS)}. Marco: C40 Urban Nature Accelerator, regla 3-30-300,
  Agenda 2030 (ODS 11), Acuerdo de París, Ordenanza 7209/2017. Cifras calculadas por Ciudad Verde AI Agent al {fecha_corta}.</div>
</div></body></html>"""


def _alto_estimado(doc):
    d = doc.get('_datos') or {}
    return int(1.3 * (3300 + 330 * len(doc.get('programas') or []) + 19 * len(d.get('copa_barrios') or [])
               + 40 * len(doc.get('primeros_90_dias') or [])))


# ============================================================
# PANTALLA
# ============================================================

def _render_historial(ciudad: str, es_admin: bool):
    """Historial de masterplans guardados en PostgreSQL, filtrado por ciudad."""
    guardados = obtener_masteplans(limit=10, ciudad=ciudad)
    if not guardados:
        return
    with st.expander(f"📂 Masterplans guardados ({len(guardados)})", expanded=False):
        for mp in guardados:
            fecha = mp["fecha"]
            fecha_str = fecha.strftime("%d/%m/%Y %H:%M") if hasattr(fecha, "strftime") else str(fecha)[:16]
            col_mp, col_load = st.columns([5, 1])
            with col_mp:
                st.markdown(f"**#{mp['id']}** · {fecha_str}  \n"
                            f"<span style='font-size:0.8em;opacity:0.7'>{_e((mp['foco'] or '')[:120])}…</span>",
                            unsafe_allow_html=True)
            with col_load:
                if st.button("Cargar", key=f"mp_load_{mp['id']}", use_container_width=True):
                    st.session_state["mp_resultado"]      = mp["texto"]
                    st.session_state["mp_tok_in"]         = mp["tok_input"] or 0
                    st.session_state["mp_tok_out"]        = mp["tok_output"] or 0
                    st.session_state["mp_costo"]          = float(mp.get("costo_usd") or 0)
                    st.session_state["mp_id_guardado"]    = mp["id"]
                    st.session_state["mp_fecha_guardado"] = fecha_str
                    st.rerun()
            if not es_admin:
                continue
            if st.session_state.get("mp_confirmar_borrar") == mp["id"]:
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("✅ Confirmar borrado", key=f"mp_del_confirm_{mp['id']}", use_container_width=True):
                        eliminar_masterplan(mp["id"])
                        st.session_state.pop("mp_confirmar_borrar", None)
                        if st.session_state.get("mp_id_guardado") == mp["id"]:
                            for k in ("mp_resultado", "mp_id_guardado", "mp_fecha_guardado"):
                                st.session_state.pop(k, None)
                        st.rerun()
                with c2:
                    if st.button("✕ Cancelar", key=f"mp_del_cancel_{mp['id']}", use_container_width=True):
                        st.session_state.pop("mp_confirmar_borrar", None)
                        st.rerun()
            elif st.button("🗑️ Borrar", key=f"mp_del_{mp['id']}", use_container_width=True):
                st.session_state["mp_confirmar_borrar"] = mp["id"]
                st.rerun()


def _focos_sugeridos(a):
    """Cuatro focos con los números actuales de la app."""
    from modulo_villamaria import DATOS_VM
    cob = DATOS_VM['cobertura']
    m = a['meta_municipal']
    focos = []
    if m:
        focos.append(("🌳 Meta 1 árbol por casa", (
            f"Cerrar el déficit de {_num(m['deficit_arboles'])} árboles de la meta municipal de 1 árbol "
            f"por casa (hoy {_dec(m['cumplimiento_pct'])} % cumplida), a razón de "
            f"{_num(a['arboles_por_anio_municipal'])} árboles por año hasta 2030, empezando por "
            f"los barrios con mayor déficit."
        )))
    menos = ", ".join(b['barrio'] for b in a['barrios_copa'][:3])
    llegan = ("ningún barrio llega" if a['barrios_30'] == 0 else
              "1 barrio llega" if a['barrios_30'] == 1 else f"{a['barrios_30']} barrios llegan")
    focos.append(("🌿 Regla 3-30-300", (
        f"Avanzar hacia el 30 % de copa arbórea por barrio de la regla 3-30-300: hoy la ciudad tiene "
        f"{_dec(a['copa_pct'])} % y {llegan} al 30 %. Priorizar los barrios con menos copa ({menos}) "
        f"para sumar sombra, frescura y salud."
    )))
    focos.append(("💧 Corredor Ctalamochita", (
        "Desarrollo del corredor verde sobre el Río Ctalamochita como parque lineal y corredor "
        "ecológico de Villa María, con arbolado ribereño nativo, senderos y ciclovías, coordinado "
        "con Villa Nueva en la margen opuesta."
    )))
    focos.append(("🌍 Liderazgo C40", (
        f"Consolidar a Villa María como ciudad intermedia líder en naturaleza urbana: sostener la meta 1 "
        f"de C40 (hoy {_dec(a['qtc'])} %, meta 30–40 %) cuidando el verde que aportan cultivos "
        f"({_dec(cob.get('cultivos') or 0)} %) y pastizales ({_dec(cob.get('pastizales') or 0)} %) a "
        f"medida que la ciudad crece, y sumar copa arbórea donde más falta."
    )))
    return focos


def _render_formulario_admin(a):
    """Formulario de generación — solo admin."""
    st.markdown("### ✏️ Foco del plan")
    st.markdown("Los programas se ordenan según las **Decisiones para Villa María en línea con C40** "
                "guardadas en Benchmarking C40.")

    if "mp_foco_set" in st.session_state:
        st.session_state["mp_foco"] = st.session_state.pop("mp_foco_set")

    st.text_area(
        "Foco y prioridades",
        placeholder="Ejemplo: 1 árbol por casa en los barrios con mayor déficit y corredor verde del Ctalamochita.",
        height=110,
        key="mp_foco",
    )
    st.markdown("**Focos sugeridos:**")
    cols = st.columns(2)
    for i, (etiqueta, texto_foco) in enumerate(_focos_sugeridos(a)):
        with cols[i % 2]:
            if st.button(etiqueta, key=f"mp_sug{i + 1}", use_container_width=True):
                st.session_state["mp_foco_set"] = texto_foco
                st.rerun()

    st.markdown("---")
    col_gen, col_info = st.columns([2, 3])
    with col_gen:
        generar = st.button(f"🚀 Generar Masterplan con {MODEL_NOMBRE}", key="mp_generar",
                            use_container_width=True, type="primary")
    with col_info:
        st.caption(f"⏱️ 2–5 minutos · {MODEL_NOMBRE} · Reporte ejecutivo con gráficos")
    return generar


def _render_documento(texto_guardado, nombre_municipio, archivo_slug, es_admin):
    try:
        doc = json.loads(texto_guardado)
        assert isinstance(doc, dict) and doc.get('programas')
    except Exception:
        st.info("Este Masterplan tiene el formato anterior (texto).")
        st.markdown(texto_guardado)
        return

    mp_id = st.session_state.get("mp_id_guardado")
    if mp_id:
        st.success(f"✅ Masterplan #{mp_id} · {st.session_state.get('mp_fecha_guardado', '')}")

    if es_admin and st.session_state.get("mp_tok_in"):
        c1, c2, c3 = st.columns(3)
        c1.metric("Tokens input", f"{st.session_state['mp_tok_in']:,}".replace(",", "."))
        c2.metric("Tokens output", f"{st.session_state.get('mp_tok_out', 0):,}".replace(",", "."))
        c3.metric("Costo generación", f"USD {st.session_state.get('mp_costo', 0.0):.3f}")

    html_doc = _html_documento(doc, nombre_municipio)
    col_a, col_b, _ = st.columns([2, 2, 3])
    with col_a:
        st.download_button("⬇️ Descargar documento (HTML)", data=html_doc.encode("utf-8"),
                           file_name=f"masterplan_{archivo_slug}.html", mime="text/html",
                           key="mp_download", use_container_width=True)
    with col_b:
        if st.button("🔄 Cerrar documento", key="mp_nuevo", use_container_width=True):
            for k in ("mp_resultado", "mp_tok_in", "mp_tok_out", "mp_costo",
                      "mp_id_guardado", "mp_fecha_guardado"):
                st.session_state.pop(k, None)
            st.rerun()
    st.caption("Para el PDF usá el botón 🖨️ dentro del documento, o abrí el HTML descargado y imprimilo.")
    components.html(html_doc, height=min(_alto_estimado(doc), 9000), scrolling=True)


_ORBE = """<div style='display:flex;flex-direction:column;align-items:center;gap:16px;padding:32px 0;'>
  <div style='width:80px;height:80px;border-radius:50%;
       background:radial-gradient(circle at 38% 32%,#c8e6c9 0%,#43a047 35%,#1b5e20 70%,#08210f 100%);
       animation:mp-pulse 2s ease-in-out infinite;box-shadow:0 0 24px rgba(67,160,71,0.6);'></div>
  <div style='font-family:"Space Mono",monospace;font-size:11px;color:rgba(165,214,167,0.9);letter-spacing:0.06em;'>
    ● __MODELO__ · PREPARANDO EL MASTERPLAN EJECUTIVO</div>
</div>
<style>@keyframes mp-pulse{0%,100%{transform:scale(1);}50%{transform:scale(1.07);}}</style>"""


def render_masterplan(municipio: str = 'villamaria'):
    """Punto de entrada. Llamar desde modulo_villamaria.py o modulo_villanueva.py."""
    info = MUNICIPIOS.get(municipio, MUNICIPIOS['villamaria'])
    nombre_municipio, archivo_slug = info['nombre'], info['archivo']

    st.title(f"📄 Masterplan · {nombre_municipio}")
    st.caption(f"{TITULO_PLAN} · {GESTION}" if municipio == 'villamaria' else "Historial")
    st.markdown("---")

    es_admin = st.session_state.get("cv_admin_auth", False)
    _render_historial(nombre_municipio, es_admin)

    if es_admin and not info.get('genera', False):
        st.info(f"🔒 **Generación no habilitada para {nombre_municipio}**: todavía no tiene datos auditados. "
                "El historial sigue disponible.")
    elif not es_admin:
        if "mp_resultado" not in st.session_state:
            st.info("🔒 Solo los administradores generan Masterplans. Podés abrir los guardados desde el historial.")
    else:
        contexto, a = _contexto_vm()
        if not contexto:
            st.warning("⚠️ Faltan los datos precalculados de Villa María (indicadores, censo arbóreo o zonas).")
            st.stop()

        with st.expander("📋 Datos que recibe el modelo", expanded=False):
            st.caption("Se arma en el momento con los datos de la app. El modelo solo puede usar estas cifras; "
                       "las tarjetas y gráficos del documento los calcula la app.")
            st.code(contexto, language=None)

        if _render_formulario_admin(a):
            foco = st.session_state.get("mp_foco", "").strip()
            if not foco:
                st.warning("Ingresá un foco o elegí uno sugerido.")
            else:
                orbe = st.empty()
                orbe.markdown(_ORBE.replace("__MODELO__", MODEL_NOMBRE.upper()), unsafe_allow_html=True)
                doc, error, tok_in, tok_out = _llamar_modelo(foco, contexto)
                orbe.empty()
                usuario = st.session_state.get("cv_usuario", "admin")
                if tok_in > 0:
                    registrar_consumo(usuario=usuario, tipo=TIPO_CONSUMO,
                                      pregunta=f"[MASTERPLAN] {foco[:200]}",
                                      tok_input=tok_in, tok_output=tok_out, modelo=MODEL_ID)
                if error:
                    st.error(f"⚠️ {error}")
                else:
                    doc['_datos'] = _datos_documento(a)
                    texto = json.dumps(doc, ensure_ascii=False)
                    nuevo_id = guardar_masterplan(usuario=usuario, foco=foco, texto=texto,
                                                  tok_input=tok_in, tok_output=tok_out,
                                                  ciudad=nombre_municipio)
                    st.session_state["mp_resultado"]      = texto
                    st.session_state["mp_tok_in"]         = tok_in
                    st.session_state["mp_tok_out"]        = tok_out
                    st.session_state["mp_costo"]          = (tok_in * PRECIO_INPUT + tok_out * PRECIO_OUTPUT) / 1_000_000
                    st.session_state["mp_id_guardado"]    = nuevo_id
                    st.session_state["mp_fecha_guardado"] = "recién generado"
                    st.rerun()

    if "mp_resultado" in st.session_state:
        st.markdown("---")
        _render_documento(st.session_state["mp_resultado"], nombre_municipio, archivo_slug, es_admin)
