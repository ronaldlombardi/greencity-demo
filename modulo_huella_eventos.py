"""
modulo_huella_eventos.py — Ciudad Verde AI Agent
================================================
Huella de carbono de eventos · Villa María.

La Municipalidad estima antes de cada evento cuánto CO₂e genera, por fuente,
y simula acciones de mitigación. Los eventos se guardan en PostgreSQL
(cv_eventos_huella) y el Masterplan usa el registro para el plan de mitigación.

Datos: data/huella_eventos.json (factores con fuente, supuestos y plantillas).
Compensación en árboles: copa media medida en Villa María (censo Meta/WRI).

Uso:
    from modulo_huella_eventos import render_huella_eventos
    render_huella_eventos()
"""

import os
import json
import copy
import datetime

import pandas as pd
import streamlit as st

from modulo_db import guardar_evento_huella, obtener_eventos_huella, eliminar_evento_huella, DB_URL
from modulo_agenda2030 import _cargar_censo, calcular_agenda2030, TASA_SECUESTRO_NETA, C_A_CO2

RUTA_HUELLA = os.path.join(os.path.dirname(__file__), 'data', 'huella_eventos.json')
CIUDAD = "Villa María"
ORIGENES = ['local', 'region', 'provincia', 'otras']
NOMBRE_ORIGEN = {'local': 'Local', 'region': 'Región (hasta ~100 km)',
                 'provincia': 'Resto de la provincia', 'otras': 'Otras provincias'}
NOMBRE_FUENTE = {
    'transporte': 'Traslado del público', 'alojamiento': 'Alojamiento', 'electricidad': 'Electricidad de red',
    'generadores': 'Grupos electrógenos', 'residuos': 'Residuos', 'comida': 'Comida',
    'produccion': 'Artistas y producción',
}


# ============================================================
# CARGA DE DATOS
# ============================================================

@st.cache_data(show_spinner=False)
def _cargar_huella():
    if not os.path.exists(RUTA_HUELLA):
        return None
    with open(RUTA_HUELLA, encoding='utf-8') as f:
        return json.load(f)


def _captura_por_arbol_kg():
    """kg de CO₂ que captura por año un árbol adulto de Villa María
    (copa media medida en el censo × tasa neta de Nowak 2013)."""
    censo = _cargar_censo()
    if not censo or not censo.get('total_arboles'):
        return None, None
    copa_media_m2 = censo['ciudad_area_copa_ha'] * 10_000 / censo['total_arboles']
    return copa_media_m2 * TASA_SECUESTRO_NETA * C_A_CO2, copa_media_m2


# ============================================================
# CÁLCULO
# ============================================================

def parametros_desde_plantilla(datos, plantilla):
    """Arma el diccionario de parámetros de un evento a partir de una plantilla."""
    sup = datos['supuestos_generales']
    perfil = datos['perfiles_procedencia'][plantilla['perfil']]
    return {
        'nombre': plantilla['nombre'],
        'plantilla': plantilla['id'],
        'lugar': plantilla.get('lugar', ''),
        'sectores': copy.deepcopy(plantilla['sectores']),
        'procedencia': {o: perfil[o] for o in ORIGENES},
        'electricidad_kwh_dia': plantilla['electricidad_kwh_dia'],
        'generador_litros_dia': plantilla['generador_litros_dia'],
        'residuos_kg_asistencia': plantilla['residuos_kg_asistencia'],
        'comida': copy.deepcopy(plantilla['comida']),
        'produccion': copy.deepcopy(plantilla['produccion']),
        'supuestos': copy.deepcopy(sup),
        'fuente_asistencia': plantilla.get('fuente_asistencia', ''),
    }


def calcular_huella(p, factores):
    """Devuelve kg de CO₂e por fuente y totales para los parámetros p."""
    f = {k: v['valor'] for k, v in factores.items()}
    sup = p['supuestos']
    asistencias = sum(s['asistentes_dia'] * s['dias'] for s in p['sectores'])
    dias_evento = max([s['dias'] for s in p['sectores']] or [0])

    # Traslado del público
    factor_modo = {
        'auto': f['auto_km'] / sup['personas_por_auto'],
        'moto': f['moto_km'] / sup['personas_por_moto'],
        'colectivo': f['colectivo_pkm'],
        'omnibus': f['omnibus_pkm'],
        'a_pie': 0.0,
    }
    transporte = 0.0
    transporte_origen = {}
    for o in ORIGENES:
        estadia = sup['estadia_noches'] if o in ('provincia', 'otras') else 1
        viajes = asistencias * p['procedencia'][o] / max(estadia, 1)
        km = 2 * sup['distancia_ida_km'][o]
        e = sum(viajes * share * km * factor_modo.get(modo, 0)
                for modo, share in sup['modos_por_origen'][o].items())
        transporte_origen[o] = e
        transporte += e

    # Alojamiento
    noches_hab = sum(asistencias * p['procedencia'][o] * sup['porcentaje_se_aloja'].get(o, 0)
                     for o in ('provincia', 'otras')) / sup['personas_por_habitacion']
    alojamiento = noches_hab * f['hotel_noche']

    electricidad = p['electricidad_kwh_dia'] * dias_evento * f['electricidad_kwh']
    generadores = p['generador_litros_dia'] * dias_evento * f['gasoil_litro']
    residuos_kg = asistencias * p['residuos_kg_asistencia']
    residuos = residuos_kg * p.get('fraccion_a_relleno', 1.0) * f['residuo_kg']

    c = p['comida']
    comida = asistencias * c['pct_consume'] * (
        c['carne_vacuna_kg'] * f['carne_vacuna_kg'] + c['cerdo_kg'] * f['cerdo_kg']
        + c['pollo_kg'] * f['pollo_kg'] + c['pan_kg'] * f['pan_kg'])

    pr = p['produccion']
    produccion = (pr['personas_avion'] * pr['km_avion_ida'] * 2 * f['avion_pkm']
                  + pr['litros_camiones'] * f['gasoil_litro'])

    por_fuente = {
        'transporte': transporte, 'alojamiento': alojamiento, 'electricidad': electricidad,
        'generadores': generadores, 'residuos': residuos, 'comida': comida, 'produccion': produccion,
    }
    total = sum(por_fuente.values())
    return {
        'por_fuente_kg': por_fuente,
        'transporte_origen_kg': transporte_origen,
        'total_kg': total,
        'asistencias': asistencias,
        'dias_evento': dias_evento,
        'kg_por_asistencia': total / asistencias if asistencias else 0,
        'noches_habitacion': noches_hab,
        'residuos_kg': residuos_kg,
    }


def aplicar_acciones(p, acciones):
    """Devuelve una copia de los parámetros con las acciones de mitigación aplicadas."""
    q = copy.deepcopy(p)
    for a in acciones:
        ef = a['efecto']
        if ef['tipo'] == 'auto_a_colectivo':
            # Colectivos especiales con ocupación completa: se usa el factor de ómnibus.
            for o in ('local', 'region'):
                modos = q['supuestos']['modos_por_origen'][o]
                mover = modos.get('auto', 0) * ef['fraccion']
                modos['auto'] = modos.get('auto', 0) - mover
                modos['omnibus'] = modos.get('omnibus', 0) + mover
        elif ef['tipo'] == 'vacuna_a_pollo':
            mover = q['comida']['carne_vacuna_kg'] * ef['fraccion']
            q['comida']['carne_vacuna_kg'] -= mover
            q['comida']['pollo_kg'] += mover
        elif ef['tipo'] == 'residuos_desviados':
            q['fraccion_a_relleno'] = q.get('fraccion_a_relleno', 1.0) * (1 - ef['fraccion'])
        elif ef['tipo'] == 'residuos_reducidos':
            q['residuos_kg_asistencia'] *= (1 - ef['fraccion'])
        elif ef['tipo'] == 'generador_a_red':
            q['electricidad_kwh_dia'] += q['generador_litros_dia'] * ef['kwh_por_litro']
            q['generador_litros_dia'] = 0
    return q


# ============================================================
# HELPERS VISUALES
# ============================================================

def _num(n):
    return f"{int(round(n)):,}".replace(",", ".")


def _dec(x, d=1):
    return f"{x:.{d}f}".replace(".", ",")


def _card(titulo, valor, detalle, color):
    st.markdown(
        f"""<div style='border-left:4px solid {color};background:{color}11;
            padding:14px 16px;border-radius:0 10px 10px 0;margin-bottom:8px'>
          <div style='font-size:0.88em;color:#fff;margin-bottom:2px;font-weight:500'>{titulo}</div>
          <div style='font-size:1.7em;font-weight:700;color:{color}'>{valor}</div>
          <div style='font-size:0.84em;color:#ccc;margin-top:2px'>{detalle}</div>
        </div>""",
        unsafe_allow_html=True,
    )


# ============================================================
# FORMULARIO DEL EVENTO
# ============================================================

def _formulario(datos, base, k):
    """Muestra los campos editables y devuelve los parámetros resultantes.
    k: sufijo de las claves de los widgets (cambia con la plantilla)."""
    p = copy.deepcopy(base)

    c1, c2, c3 = st.columns([2, 1, 2])
    with c1:
        p['nombre'] = st.text_input("Nombre del evento", value=base['nombre'], key=f"he_nombre_{k}")
    with c2:
        p['fecha_evento'] = st.date_input("Fecha de inicio", value=datetime.date.today(),
                                          key=f"he_fecha_{k}", format="DD/MM/YYYY")
    with c3:
        p['lugar'] = st.text_input("Lugar", value=base.get('lugar', ''), key=f"he_lugar_{k}")

    st.markdown("**👥 Asistencia por sector**")
    df = pd.DataFrame([{'Sector': s['nombre'], 'Asistentes por día': s['asistentes_dia'], 'Días': s['dias']}
                       for s in base['sectores']])
    editado = st.data_editor(
        df, num_rows="dynamic", hide_index=True, use_container_width=True, key=f"he_sectores_{k}",
        column_config={
            'Asistentes por día': st.column_config.NumberColumn(min_value=0, step=100),
            'Días': st.column_config.NumberColumn(min_value=1, step=1),
        },
    )
    p['sectores'] = [
        {'nombre': str(r['Sector'] or 'Sector'), 'asistentes_dia': int(r['Asistentes por día'] or 0),
         'dias': int(r['Días'] or 1)}
        for _, r in editado.iterrows() if pd.notna(r['Asistentes por día'])
    ]
    if base.get('fuente_asistencia'):
        st.caption(f"Asistencia: {base['fuente_asistencia']}")

    st.markdown("**🧭 Procedencia del público (%)**")
    cols = st.columns(4)
    for col, o in zip(cols, ORIGENES):
        with col:
            p['procedencia'][o] = st.number_input(
                NOMBRE_ORIGEN[o], min_value=0, max_value=100, step=5,
                value=int(round(base['procedencia'][o] * 100)), key=f"he_proc_{o}_{k}") / 100
    suma = sum(p['procedencia'].values())
    if abs(suma - 1) > 0.001:
        st.warning(f"La procedencia suma {_dec(suma * 100, 0)} %; tiene que sumar 100 %.")

    st.markdown("**⚡ Energía y residuos**")
    c1, c2, c3 = st.columns(3)
    with c1:
        p['electricidad_kwh_dia'] = st.number_input(
            "Electricidad de red (kWh por día)", min_value=0, step=100,
            value=int(base['electricidad_kwh_dia']), key=f"he_kwh_{k}")
    with c2:
        p['generador_litros_dia'] = st.number_input(
            "Gasoil de generadores (litros por día)", min_value=0, step=50,
            value=int(base['generador_litros_dia']), key=f"he_gen_{k}")
    with c3:
        p['residuos_kg_asistencia'] = st.number_input(
            "Residuos (kg por asistencia)", min_value=0.0, step=0.1, format="%.2f",
            value=float(base['residuos_kg_asistencia']), key=f"he_res_{k}")

    st.markdown("**🍽️ Comida (por persona que consume)**")
    c1, c2, c3, c4, c5 = st.columns(5)
    com = base['comida']
    with c1:
        p['comida']['pct_consume'] = st.number_input(
            "% que consume", min_value=0, max_value=100, step=5,
            value=int(round(com['pct_consume'] * 100)), key=f"he_pct_{k}") / 100
    with c2:
        p['comida']['carne_vacuna_kg'] = st.number_input(
            "Carne vacuna (kg)", min_value=0.0, step=0.01, format="%.2f",
            value=float(com['carne_vacuna_kg']), key=f"he_vac_{k}")
    with c3:
        p['comida']['cerdo_kg'] = st.number_input(
            "Cerdo (kg)", min_value=0.0, step=0.01, format="%.2f",
            value=float(com['cerdo_kg']), key=f"he_cerdo_{k}")
    with c4:
        p['comida']['pollo_kg'] = st.number_input(
            "Pollo (kg)", min_value=0.0, step=0.01, format="%.2f",
            value=float(com['pollo_kg']), key=f"he_pollo_{k}")
    with c5:
        p['comida']['pan_kg'] = st.number_input(
            "Pan (kg)", min_value=0.0, step=0.01, format="%.2f",
            value=float(com['pan_kg']), key=f"he_pan_{k}")

    st.markdown("**🎤 Artistas y producción**")
    c1, c2, c3 = st.columns(3)
    pr = base['produccion']
    with c1:
        p['produccion']['personas_avion'] = st.number_input(
            "Personas que viajan en avión", min_value=0, step=5,
            value=int(pr['personas_avion']), key=f"he_avion_{k}")
    with c2:
        p['produccion']['km_avion_ida'] = st.number_input(
            "Distancia del vuelo, ida (km)", min_value=0, step=50,
            value=int(pr['km_avion_ida']), key=f"he_kmavion_{k}")
    with c3:
        p['produccion']['litros_camiones'] = st.number_input(
            "Gasoil de camiones de producción (litros)", min_value=0, step=100,
            value=int(pr['litros_camiones']), key=f"he_cam_{k}")

    with st.expander("⚙️ Supuestos de traslado y alojamiento", expanded=False):
        sup = p['supuestos']
        c1, c2, c3 = st.columns(3)
        with c1:
            sup['personas_por_auto'] = st.number_input(
                "Personas por auto", min_value=1.0, max_value=5.0, step=0.1,
                value=float(base['supuestos']['personas_por_auto']), key=f"he_ocup_{k}")
        with c2:
            sup['estadia_noches'] = st.number_input(
                "Estadía de visitantes (noches)", min_value=1, max_value=10, step=1,
                value=int(base['supuestos']['estadia_noches']), key=f"he_estadia_{k}")
        with c3:
            sup['personas_por_habitacion'] = st.number_input(
                "Personas por habitación", min_value=1, max_value=6, step=1,
                value=int(base['supuestos']['personas_por_habitacion']), key=f"he_hab_{k}")
        st.markdown("Distancia de ida por origen (km)")
        cols = st.columns(4)
        for col, o in zip(cols, ORIGENES):
            with col:
                sup['distancia_ida_km'][o] = st.number_input(
                    NOMBRE_ORIGEN[o], min_value=0, step=10,
                    value=int(base['supuestos']['distancia_ida_km'][o]), key=f"he_dist_{o}_{k}")
        st.markdown("Medio de transporte por origen")
        st.dataframe(
            pd.DataFrame([{'Origen': NOMBRE_ORIGEN[o],
                           **{m.replace('_', ' ').capitalize(): f"{_dec(v * 100, 0)} %" for m, v in modos.items()}}
                          for o, modos in sup['modos_por_origen'].items()]).fillna("—"),
            hide_index=True, use_container_width=True,
        )
        st.caption(
            f"Se alojan en la ciudad: {_dec(sup['porcentaje_se_aloja']['provincia'] * 100, 0)} % de quienes "
            f"vienen del resto de la provincia y {_dec(sup['porcentaje_se_aloja']['otras'] * 100, 0)} % de "
            "quienes vienen de otras provincias. Todos estos valores son supuestos."
        )
    return p


# ============================================================
# RESULTADOS
# ============================================================

def _render_resultado(r, captura_kg, titulo="Resultado"):
    total_t = r['total_kg'] / 1000
    arboles = r['total_kg'] / captura_kg if captura_kg else None
    st.markdown(f"### 📊 {titulo}")
    c1, c2, c3 = st.columns(3)
    with c1:
        _card("Huella total", f"{_num(total_t)} t CO₂e",
              f"{_num(r['asistencias'])} asistencias en {r['dias_evento']} día(s)", "#c62828")
    with c2:
        _card("Por asistencia", f"{_dec(r['kg_por_asistencia'])} kg CO₂e",
              "promedio por persona por día", "#f57c00")
    with c3:
        _card("Árboles para compensar", _num(arboles) if arboles else "—",
              "captura de un año de árboles adultos de Villa María", "#2e7d32")

    filas = [{'Fuente': NOMBRE_FUENTE[k], 't CO₂e': round(v / 1000, 1),
              '%': round(v / r['total_kg'] * 100, 1) if r['total_kg'] else 0}
             for k, v in sorted(r['por_fuente_kg'].items(), key=lambda x: -x[1])]
    df = pd.DataFrame(filas)
    c1, c2 = st.columns([3, 2])
    with c1:
        st.bar_chart(df.set_index('Fuente')['t CO₂e'], height=300)
    with c2:
        st.dataframe(df, hide_index=True, use_container_width=True)


def _render_mitigacion(datos, p, base_res, captura_kg):
    st.markdown("### 🌱 Plan de mitigación")
    acciones = datos['acciones_mitigacion']
    elegidas_ids = st.multiselect(
        "Acciones a simular", [a['id'] for a in acciones],
        format_func=lambda i: next(a['titulo'] for a in acciones if a['id'] == i),
        key="he_acciones",
    )
    elegidas = [a for a in acciones if a['id'] in elegidas_ids]
    for a in elegidas:
        st.caption(f"• **{a['titulo']}:** {a['descripcion']}")
    if not elegidas:
        st.caption("Elegí una o más acciones para ver cuánto reducen la huella.")
        return base_res, []

    # Ahorro de cada acción por separado (las acciones se combinan en el total)
    filas = []
    for a in elegidas:
        r_a = calcular_huella(aplicar_acciones(p, [a]), datos['factores'])
        filas.append({'Acción': a['titulo'], 'Ahorro (t CO₂e)': round((base_res['total_kg'] - r_a['total_kg']) / 1000, 1)})
    mit = calcular_huella(aplicar_acciones(p, elegidas), datos['factores'])
    ahorro_kg = base_res['total_kg'] - mit['total_kg']

    c1, c2, c3 = st.columns(3)
    with c1:
        _card("Huella con mitigación", f"{_num(mit['total_kg'] / 1000)} t CO₂e",
              f"antes: {_num(base_res['total_kg'] / 1000)} t", "#1e88e5")
    with c2:
        _card("Reducción", f"{_num(ahorro_kg / 1000)} t CO₂e",
              f"{_dec(ahorro_kg / base_res['total_kg'] * 100 if base_res['total_kg'] else 0)} % menos", "#2e7d32")
    with c3:
        _card("Árboles para compensar el resto", _num(mit['total_kg'] / captura_kg) if captura_kg else "—",
              "captura de un año", "#2e7d32")
    st.dataframe(pd.DataFrame(filas), hide_index=True, use_container_width=True)
    st.caption("El ahorro de cada acción se calcula por separado; aplicadas juntas, el total puede ser algo menor que la suma.")
    return mit, elegidas_ids


def _render_guardar(p, res, mit, acciones_ids):
    if not st.session_state.get("cv_admin_auth", False):
        st.info("🔒 Cualquier usuario puede simular. Solo el administrador puede guardar eventos en el registro.")
        return
    if not DB_URL:
        st.warning("La base de datos no está configurada: el evento no se puede guardar.")
        return
    if abs(sum(p['procedencia'].values()) - 1) > 0.001:
        st.warning("Corregí la procedencia (tiene que sumar 100 %) antes de guardar.")
        return
    if st.button("💾 Guardar evento en el registro", key="he_guardar", use_container_width=True):
        params = {k: v for k, v in p.items() if k != 'fecha_evento'}
        resultado = {
            'por_fuente_kg': res['por_fuente_kg'], 'transporte_origen_kg': res['transporte_origen_kg'],
            'asistencias': res['asistencias'], 'dias_evento': res['dias_evento'],
            'total_mitigado_kg': mit['total_kg'], 'por_fuente_mitigado_kg': mit['por_fuente_kg'],
        }
        nuevo = guardar_evento_huella(
            CIUDAD, p['nombre'], p['fecha_evento'], p.get('plantilla'), params, resultado,
            acciones_ids, res['total_kg'] / 1000, mit['total_kg'] / 1000,
            st.session_state.get("cv_usuario", "admin"),
        )
        if nuevo:
            st.session_state["he_guardado"] = nuevo
            st.rerun()
        else:
            st.error("No se pudo guardar el evento. Revisá la conexión a la base de datos.")


# Huella por habitante de Argentina: INDEC, Cuenta de emisiones al aire (2022):
# 401,2 MtCO₂e / 46.044.703 habitantes (Censo 2022). Sectores urbanos: se descuenta
# agricultura, ganadería y uso del suelo (39 % del inventario nacional, INGEI 2018).
HUELLA_HAB_TOTAL_T = 401.2e6 / 46_044_703
PARTE_AGRO = 0.39
META_COPA_PCT = 30.0


def _tiempo(dias):
    """Texto legible para un plazo expresado en días."""
    if dias >= 10:
        return f"{_num(dias)} días"
    if dias >= 1:
        return f"{_dec(dias, 1)} días"
    horas = dias * 24
    return f"{_num(horas)} horas" if horas >= 1 else "menos de 1 hora"


def _render_balance(res, mit, captura_kg):
    """¿Puede Villa María absorber el evento con sus propios árboles? Tres escenarios."""
    a = calcular_agenda2030()
    if not a or not captura_kg:
        return
    st.markdown("### ⚖️ ¿Puede Villa María absorber este evento con sus árboles?")

    captura_hoy = a['co2_meta_t']
    deficit = a['meta_municipal']['deficit_arboles'] if a.get('meta_municipal') else 0
    captura_meta = captura_hoy + deficit * captura_kg / 1000
    copa_30_m2 = a['area_ha'] * META_COPA_PCT / 100 * 10_000
    captura_30 = max(captura_hoy, copa_30_m2 * TASA_SECUESTRO_NETA / 1000 * C_A_CO2)

    huella = res['total_kg'] / 1000
    huella_mit = mit['total_kg'] / 1000
    hay_mit = huella_mit < huella - 0.001

    escenarios = [
        ("Hoy", f"{_num(a['total_arboles'])} árboles · {_dec(a['copa_pct'])} % de copa", captura_hoy),
        ("Meta municipal: 1 árbol por casa", f"+{_num(deficit)} árboles", captura_meta),
        ("Camino C40 / regla 3-30-300", f"{_dec(META_COPA_PCT, 0)} % de copa", captura_30),
    ]
    ref = huella_mit if hay_mit else huella
    evento_chico = ref <= captura_hoy   # el arbolado actual ya lo absorbe en menos de un año
    cols = st.columns(3)
    for col, (titulo, detalle, captura) in zip(cols, escenarios):
        pct = captura / ref * 100 if ref else 0
        if evento_chico:
            dias = ref / captura * 365 if captura else 0
            valor = _tiempo(dias)
            estado, color = "✅ para absorberlo", "#2e7d32"
        else:
            valor = f"{_dec(pct, 0)} %"
            color = "#2e7d32" if pct >= 100 else "#f57c00"
            estado = "✅ autosuficiente" if pct >= 100 else "absorbe en un año"
        with col:
            _card(titulo, valor, f"{estado} · captura {_num(captura)} t CO₂/año · {detalle}", color)

    filas = [{
        'Escenario': t,
        'Captura anual (t CO₂)': round(c),
        'Cubre del evento (%)': round(c / huella * 100) if huella else 0,
        **({'Cubre del evento con mitigación (%)': round(c / huella_mit * 100) if huella_mit else 0} if hay_mit else {}),
    } for t, _, c in escenarios]
    st.dataframe(pd.DataFrame(filas), hide_index=True, use_container_width=True)

    ref_txt = "con mitigación" if hay_mit else "sin mitigación"
    pct_hoy = captura_hoy / ref * 100 if ref else 0
    if evento_chico:
        dias_hoy = ref / captura_hoy * 365 if captura_hoy else 0
        mensaje = (f"Los árboles de Villa María absorben la huella de este evento ({ref_txt}) en "
                   f"{_tiempo(dias_hoy)}.")
    elif captura_meta >= ref:
        mensaje = (f"Hoy los árboles de Villa María absorben el {_dec(pct_hoy, 0)} % de la huella de este evento "
                   f"({ref_txt}). Con la meta de 1 árbol por casa, la ciudad lo absorbería con sus propios árboles.")
    elif captura_30 >= ref:
        mensaje = (f"Hoy los árboles de Villa María absorben el {_dec(pct_hoy, 0)} % de la huella de este evento "
                   f"({ref_txt}). Con 30 % de copa, la ciudad lo absorbería con sus propios árboles.")
    else:
        mensaje = (f"Hoy los árboles de Villa María absorben el {_dec(pct_hoy, 0)} % de la huella de este evento "
                   f"({ref_txt}). Cada árbol que se planta acerca a la ciudad a absorberlo con sus propios árboles.")
    st.success(f"🌳 {mensaje}")

    poblacion = a['poblacion']
    huella_ciudad_urbana = poblacion * HUELLA_HAB_TOTAL_T * (1 - PARTE_AGRO)
    huella_ciudad_total = poblacion * HUELLA_HAB_TOTAL_T
    st.caption(
        "Captura = copa × 0,205 kg C/m² por año × 44/12 (Nowak et al. 2013); los árboles nuevos suman la copa media "
        "medida en la ciudad. Un árbol recién plantado tarda 15 a 20 años en llegar a esa captura. "
        "'Autosuficiente' significa que el arbolado captura en un año al menos lo que emite el evento. "
        f"Es un balance del evento, no de toda la ciudad: la huella estimada de Villa María es de ≈ "
        f"{_num(huella_ciudad_urbana / 1000)} mil t CO₂e por año en sectores urbanos (≈ "
        f"{_num(huella_ciudad_total / 1000)} mil t con todos los sectores), con el promedio nacional por habitante "
        "(INDEC, Cuenta de emisiones al aire 2022; Censo 2022)."
    )


def _render_registro(captura_kg):
    st.markdown("### 📅 Registro anual de eventos")
    if not DB_URL:
        st.caption("La base de datos no está configurada.")
        return
    hoy = datetime.date.today()
    anio = st.selectbox("Año", list(range(hoy.year - 1, hoy.year + 3)), index=1, key="he_anio")
    eventos = obtener_eventos_huella(CIUDAD, anio)
    if not eventos:
        st.caption(f"No hay eventos guardados para {anio}.")
        return

    filas = []
    for e in eventos:
        res = e.get('resultado') or {}
        filas.append({
            'Fecha': e['fecha_evento'].strftime("%d/%m/%Y") if e.get('fecha_evento') else "—",
            'Evento': e['nombre'],
            'Asistencias': res.get('asistencias', 0),
            't CO₂e': float(e['total_t'] or 0),
            't CO₂e con mitigación': float(e['total_mitigado_t'] or 0),
            'Acciones': len(e.get('acciones') or []),
        })
    df = pd.DataFrame(filas)
    st.dataframe(df, hide_index=True, use_container_width=True)

    total = df['t CO₂e'].sum()
    total_mit = df['t CO₂e con mitigación'].sum()
    c1, c2, c3 = st.columns(3)
    with c1:
        _card(f"Huella de los eventos {anio}", f"{_num(total)} t CO₂e", f"{len(eventos)} eventos", "#c62828")
    with c2:
        _card("Con las mitigaciones previstas", f"{_num(total_mit)} t CO₂e",
              f"{_dec((total - total_mit) / total * 100 if total else 0)} % menos", "#1e88e5")
    with c3:
        _card("Árboles para compensar el año", _num(total_mit * 1000 / captura_kg) if captura_kg else "—",
              "con las mitigaciones previstas", "#2e7d32")

    if st.session_state.get("cv_admin_auth", False):
        with st.expander("🗑️ Borrar un evento del registro", expanded=False):
            opciones = {f"#{e['id']} · {e['nombre']}": e['id'] for e in eventos}
            elegido = st.selectbox("Evento", list(opciones), key="he_borrar_sel")
            if st.button("Borrar definitivamente", key="he_borrar_btn"):
                if eliminar_evento_huella(opciones[elegido]):
                    st.rerun()
                else:
                    st.error("No se pudo borrar el evento.")


def _render_fuentes(datos, captura_kg, copa_media_m2):
    with st.expander("📚 Método, factores y fuentes", expanded=False):
        st.markdown(datos['metodo'])
        fuentes = datos['fuentes']
        filas = [{'Factor': v['nombre'], 'Valor': v['valor'], 'Unidad': v['unidad'],
                  'Fuente': fuentes[v['fuente']]['titulo']} for v in datos['factores'].values()]
        st.dataframe(pd.DataFrame(filas), hide_index=True, use_container_width=True)
        if captura_kg:
            st.markdown(
                f"**Compensación en árboles:** un árbol adulto de Villa María captura ≈ {_dec(captura_kg)} kg de "
                f"CO₂ por año (copa media medida de {_dec(copa_media_m2)} m² × {_dec(TASA_SECUESTRO_NETA, 3)} kg C "
                f"por m² por año × 44/12). Un árbol recién plantado tarda 15 a 20 años en llegar a ese tamaño."
            )
        st.markdown("**Fuentes**")
        for v in fuentes.values():
            st.markdown(f"- [{v['titulo']}]({v['url']})")


# ============================================================
# TEXTO PARA EL PROMPT DEL MASTERPLAN
# ============================================================

def texto_eventos_para_prompt(ciudad: str = CIUDAD, anio: int = None) -> str:
    """Resumen del registro de eventos para el prompt del Masterplan."""
    eventos = obtener_eventos_huella(ciudad, anio)
    if not eventos:
        return ""
    captura_kg, _ = _captura_por_arbol_kg()
    lineas = []
    total = total_mit = 0.0
    for e in eventos:
        res = e.get('resultado') or {}
        por_fuente = res.get('por_fuente_kg') or {}
        principal = max(por_fuente, key=por_fuente.get) if por_fuente else None
        t, tm = float(e['total_t'] or 0), float(e['total_mitigado_t'] or 0)
        total += t
        total_mit += tm
        fecha = e['fecha_evento'].strftime("%m/%Y") if e.get('fecha_evento') else "s/f"
        principal_txt = f" (principal fuente: {NOMBRE_FUENTE[principal]})" if principal else ""
        lineas.append(
            f"- {e['nombre']} ({fecha}): {_num(res.get('asistencias', 0))} asistencias, {_num(t)} t CO₂e"
            f"{principal_txt}; con mitigación prevista {_num(tm)} t CO₂e"
        )
    arboles = (f" Compensar el total con mitigación equivale a la captura anual de "
               f"{_num(total_mit * 1000 / captura_kg)} árboles adultos de Villa María.") if captura_kg else ""
    return ("HUELLA DE CARBONO DE EVENTOS (registro municipal, estimaciones con supuestos declarados):\n"
            + "\n".join(lineas)
            + f"\nTotal: {_num(total)} t CO₂e; con mitigaciones previstas: {_num(total_mit)} t CO₂e."
            + arboles)


# ============================================================
# RENDER
# ============================================================

def render_huella_eventos():
    """Punto de entrada. Llamar desde render_modulo_villamaria()."""
    st.title("🎪 Huella de carbono de eventos")
    st.caption("Estimación previa del impacto de cada evento en Villa María y simulación de acciones de mitigación")

    datos = _cargar_huella()
    if not datos:
        st.warning("Falta data/huella_eventos.json.")
        return
    captura_kg, copa_media_m2 = _captura_por_arbol_kg()

    guardado = st.session_state.pop("he_guardado", None)
    if guardado:
        st.success(f"✅ Evento #{guardado} guardado en el registro.")

    st.markdown(
        "Elegí una plantilla o un evento nuevo y ajustá los valores. Todos los valores iniciales son "
        "estimaciones editables; los factores de emisión tienen fuente (ver *Método, factores y fuentes*)."
    )
    plantillas = {pl['id']: pl for pl in datos['plantillas']}
    opciones = list(plantillas) + ['nuevo']
    elegida = st.selectbox(
        "Plantilla", opciones,
        format_func=lambda i: "➕ Evento nuevo" if i == 'nuevo'
        else f"{plantillas[i]['nombre']} · {plantillas[i]['mes']}",
        key="he_plantilla",
    )
    if elegida == 'nuevo':
        base = parametros_desde_plantilla(datos, plantillas['recital'])
        base.update({'nombre': 'Evento nuevo', 'plantilla': 'nuevo', 'lugar': '', 'fuente_asistencia': ''})
        base['sectores'] = [{'nombre': 'Público', 'asistentes_dia': 500, 'dias': 1}]
    else:
        base = parametros_desde_plantilla(datos, plantillas[elegida])

    st.markdown("---")
    p = _formulario(datos, base, elegida)
    st.markdown("---")

    res = calcular_huella(p, datos['factores'])
    _render_resultado(res, captura_kg)
    st.markdown("---")
    mit, acciones_ids = _render_mitigacion(datos, p, res, captura_kg)
    _render_guardar(p, res, mit, acciones_ids)
    st.markdown("---")
    _render_balance(res, mit, captura_kg)
    st.markdown("---")
    _render_registro(captura_kg)
    st.markdown("---")
    _render_fuentes(datos, captura_kg, copa_media_m2)
    st.caption(
        "Ciudad Verde AI Agent · Huella de carbono de eventos · Factores: SNIGEI-AR 2025, DEFRA 2025, "
        "BEIS 2021, Poore y Nemecek 2018 · Captura del arbolado: censo Meta/WRI de Villa María y Nowak et al. 2013"
    )
