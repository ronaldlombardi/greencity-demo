"""
modulo_censo_arboreo.py — Ciudad Verde AI Agent
================================================
Censo Arbóreo — Villa María.
Objetivo municipal: 1 árbol por vivienda.

Este módulo se construye paso a paso:
  1. Estructura de pantalla (este commit)
  2. Numerador aproximado — Canopy Height (GEE, 1m) → cobertura/conteo estimado de copas
  3. Denominador — Catastro IDECOR (parcelas edificadas por manzana)
  4. Cruce numerador/denominador → ratio árboles/vivienda por zona

Uso en dashboard:
    from modulo_censo_arboreo import render_censo_arboreo
    render_censo_arboreo()
"""

import streamlit as st


# ============================================================
# ESTADO DE FUENTES (se va actualizando a medida que se conecta cada una)
# ============================================================

FUENTES = [
    {
        'nombre': 'Canopy Height (GEE, 1m)',
        'rol': 'Numerador — estimación de copas/cobertura arbórea',
        'estado': 'pendiente',  # pendiente | en_progreso | conectada
        'detalle': 'Dataset global de altura de dosel a 1m. Permite diferenciar copas '
                    'individuales (vs. 10m de Sentinel-2/WorldCover que ya usamos). '
                    'Error medio ~2.8m en altura — es una aproximación, no un inventario exacto.',
    },
    {
        'nombre': 'Catastro IDECOR (WFS/WMS)',
        'rol': 'Denominador — parcelas edificadas por manzana',
        'estado': 'pendiente',
        'detalle': 'Distingue parcelas baldío/edificado/PH. Da el número real de viviendas '
                    'por manzana para calcular el ratio árboles/vivienda. Requiere consulta '
                    'a idecor@cba.gov.ar para descarga sin filtro por WFS.',
    },
    {
        'nombre': 'OpenStreetMap (natural=tree)',
        'rol': 'Complementaria — árboles individuales cargados por la comunidad',
        'estado': 'descartada_por_ahora',
        'detalle': 'Cobertura comunitaria en Argentina es prácticamente nula para este tag. '
                    'Se deja documentada por si en el futuro se completa.',
    },
]

_COLOR_ESTADO = {
    'pendiente': '#9e9e9e',
    'en_progreso': '#f57c00',
    'conectada': '#2e7d32',
    'descartada_por_ahora': '#616161',
}

_LABEL_ESTADO = {
    'pendiente': '⏳ Pendiente',
    'en_progreso': '🔧 En progreso',
    'conectada': '✅ Conectada',
    'descartada_por_ahora': '⛔ Descartada por ahora',
}


def render_censo_arboreo():
    """Punto de entrada. Llamar desde render_modulo_villamaria()."""

    st.title("🌳 Censo Arbóreo · Villa María")
    st.caption("Objetivo municipal: 1 árbol por vivienda")
    st.markdown("---")

    st.info(
        "📍 Pantalla en construcción. Acá va a vivir el conteo de árboles por manzana "
        "y su comparación contra la cantidad de viviendas edificadas, a medida que "
        "conectemos cada fuente de datos."
    )

    st.markdown("### Fuentes de datos — estado actual")

    for f in FUENTES:
        color = _COLOR_ESTADO[f['estado']]
        st.markdown(
            f"""<div style='border-left:4px solid {color};background:{color}11;
                padding:14px 16px;border-radius:0 10px 10px 0;margin-bottom:10px'>
              <div style='display:flex;justify-content:space-between;align-items:center'>
                <span style='font-size:1em;font-weight:600;color:#fff'>{f['nombre']}</span>
                <span style='font-size:0.82em;font-weight:600;color:{color}'>{_LABEL_ESTADO[f['estado']]}</span>
              </div>
              <div style='font-size:0.85em;color:#ccc;margin-top:2px'>{f['rol']}</div>
              <div style='font-size:0.82em;color:#aaa;margin-top:6px'>{f['detalle']}</div>
            </div>""",
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.caption(
        "Ciudad Verde AI Agent · Villa María · Censo Arbóreo · "
        "En desarrollo — Canopy Height (GEE) + Catastro IDECOR"
    )