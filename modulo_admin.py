"""
modulo_admin.py — Ciudad Verde AI Agent
=========================================
Panel de administración: consumos de Haiku y Opus.
Acceso protegido por ADMIN_USERNAME / ADMIN_PASSWORD.
"""

import os
import streamlit as st
import pandas as pd
from modulo_db import obtener_consumos, obtener_resumen, obtener_totales

ADMIN_USER = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASSWORD", "admin2025")

# Costo por modelo para display
MODELO_LABEL = {
    "haiku": "Claude Haiku 4.5",
    "opus":  "Claude Opus 4.7",
}


def _render_login_admin():
    st.markdown("""
    <style>
    .cv-admin-login {
        max-width:360px;margin:10vh auto 0 auto;
        background:rgba(10,14,32,0.85);
        border:0.5px solid rgba(120,140,255,0.28);
        border-radius:14px;padding:32px 28px;
        backdrop-filter:blur(18px);
    }
    .cv-admin-login h3 {
        font-family:'Space Mono',monospace !important;
        font-size:13px !important;font-weight:700 !important;
        letter-spacing:0.10em !important;color:#c0b0f0 !important;
        text-align:center;margin-bottom:20px;
    }
    </style>
    <div class="cv-admin-login">
      <h3>🔐 PANEL ADMINISTRACIÓN</h3>
    </div>
    """, unsafe_allow_html=True)

    with st.container():
        u = st.text_input("Usuario admin", key="adm_user", placeholder="Usuario")
        p = st.text_input("Contraseña",    key="adm_pass", placeholder="Contraseña", type="password")
        if st.button("Ingresar →", key="adm_login", use_container_width=True, type="primary"):
            if u == ADMIN_USER and p == ADMIN_PASS:
                st.session_state["cv_admin_auth"] = True
                st.rerun()
            else:
                st.error("Credenciales incorrectas.")


def render_admin():
    """Punto de entrada del módulo admin. Llamar desde app.py."""

    # ── Auth ──
    if not st.session_state.get("cv_admin_auth"):
        _render_login_admin()
        return

    # ── Header ──
    col_h, col_out = st.columns([4, 1])
    with col_h:
        st.markdown(
            """<div style="display:flex;align-items:center;gap:12px;margin-bottom:4px;">
              <div style="width:32px;height:32px;
                   background:linear-gradient(135deg,#6228b4,#00b4dc);
                   border-radius:8px;display:flex;align-items:center;justify-content:center;
                   font-family:'Space Mono',monospace;font-size:14px;font-weight:700;color:#fff;">
                CV</div>
              <div>
                <div style="font-family:'Space Mono',monospace;font-size:13px;
                     font-weight:700;letter-spacing:0.08em;color:#d0d8f8;">
                  PANEL DE ADMINISTRACIÓN</div>
                <div style="font-family:'Space Mono',monospace;font-size:9px;
                     color:rgba(170,176,200,0.5);letter-spacing:0.08em;margin-top:2px;">
                  Ciudad Verde AI Agent · Consumos de IA</div>
              </div>
            </div>""",
            unsafe_allow_html=True,
        )
    with col_out:
        if st.button("Cerrar sesión", key="adm_logout"):
            st.session_state["cv_admin_auth"] = False
            st.rerun()

    st.markdown("---")

    # ── Totales globales ──
    totales = obtener_totales()
    if totales:
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Total consultas",
                      f"{totales.get('total_consultas') or 0:,}")
        with c2:
            tok_in  = totales.get('total_tok_in')  or 0
            tok_out = totales.get('total_tok_out') or 0
            st.metric("Tokens input",  f"{int(tok_in):,}")
        with c3:
            st.metric("Tokens output", f"{int(tok_out):,}")
        with c4:
            costo = float(totales.get('total_costo') or 0)
            st.metric("Costo total", f"USD {costo:.4f}")
    else:
        st.info("Sin datos de consumo aún.")

    st.markdown("---")

    # ── Tabs ──
    tab1, tab2 = st.tabs(["📋 Detalle de consultas", "📊 Resumen por usuario"])

    # ── Tab 1: Detalle ──
    with tab1:
        st.markdown(
            "<div style='font-family:\"Space Mono\",monospace;font-size:9px;"
            "letter-spacing:0.12em;text-transform:uppercase;"
            "color:rgba(160,175,210,0.5);margin-bottom:10px;'>"
            "Últimas 200 consultas · orden cronológico inverso</div>",
            unsafe_allow_html=True,
        )

        registros = obtener_consumos(200)
        if not registros:
            st.info("Sin registros aún.")
        else:
            filas = []
            for r in registros:
                fecha = r["fecha"]
                if hasattr(fecha, "strftime"):
                    fecha_str = fecha.strftime("%Y-%m-%d %H:%M")
                else:
                    fecha_str = str(fecha)[:16]
                costo_r = float(r["costo_usd"] or 0)
                filas.append({
                    "Fecha":       fecha_str,
                    "Usuario":     r["usuario"] or "—",
                    "Modelo":      MODELO_LABEL.get(r["tipo"], r["tipo"] or "—"),
                    "Pregunta":    (r["pregunta"] or "")[:80] + ("…" if len(r["pregunta"] or "") > 80 else ""),
                    "Tok. input":  int(r["tok_input"]  or 0),
                    "Tok. output": int(r["tok_output"] or 0),
                    "Costo USD":   f"{costo_r:.5f}",
                })
            df = pd.DataFrame(filas)
            st.dataframe(df, use_container_width=True, height=420)

            # Descarga CSV
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇️ Exportar CSV",
                data=csv,
                file_name="ciudad_verde_consumos.csv",
                mime="text/csv",
                key="adm_csv",
            )

    # ── Tab 2: Resumen ──
    with tab2:
        st.markdown(
            "<div style='font-family:\"Space Mono\",monospace;font-size:9px;"
            "letter-spacing:0.12em;text-transform:uppercase;"
            "color:rgba(160,175,210,0.5);margin-bottom:10px;'>"
            "Agrupado por usuario y modelo</div>",
            unsafe_allow_html=True,
        )

        resumen = obtener_resumen()
        if not resumen:
            st.info("Sin datos aún.")
        else:
            filas_r = []
            for r in resumen:
                ultima = r["ultima_consulta"]
                if hasattr(ultima, "strftime"):
                    ultima_str = ultima.strftime("%Y-%m-%d %H:%M")
                else:
                    ultima_str = str(ultima)[:16]
                filas_r.append({
                    "Usuario":        r["usuario"] or "—",
                    "Modelo":         MODELO_LABEL.get(r["tipo"], r["tipo"] or "—"),
                    "Consultas":      int(r["consultas"] or 0),
                    "Tok. input":     int(r["tok_in_total"]  or 0),
                    "Tok. output":    int(r["tok_out_total"] or 0),
                    "Costo USD":      f"{float(r['costo_total'] or 0):.4f}",
                    "Última consulta": ultima_str,
                })
            df_r = pd.DataFrame(filas_r)
            st.dataframe(df_r, use_container_width=True)

            # Mini gráfico de costos por usuario
            st.markdown("### Costo acumulado por usuario")
            df_chart = df_r[["Usuario", "Costo USD"]].copy()
            df_chart["Costo USD"] = df_chart["Costo USD"].astype(float)
            df_chart = df_chart.groupby("Usuario")["Costo USD"].sum().reset_index()
            st.bar_chart(df_chart.set_index("Usuario"))

    st.markdown("---")
    st.caption(
        "Ciudad Verde AI Agent · Panel Admin · "
        "Datos almacenados en PostgreSQL Railway · "
        "Costos: Haiku $0.80/$4.00 por MTok · Opus $15/$75 por MTok"
    )
