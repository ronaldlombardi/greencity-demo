"""
modulo_db.py — Ciudad Verde AI Agent
=====================================
Conexión y operaciones sobre PostgreSQL en Railway.
Registra consumos de Haiku y Opus (tokens, costo, fecha).
"""

import os
import datetime
import psycopg2
from psycopg2.extras import RealDictCursor

DB_URL = os.environ.get("DB_URL", "")

# Costos por millón de tokens (USD) — precios Anthropic 2025
COSTOS = {
    "haiku":  {"input": 0.80,  "output": 4.00},   # claude-haiku-4-5
    "opus":   {"input": 15.00, "output": 75.00},   # claude-opus-4-7
}


def _conn():
    """Abre una conexión a Postgres."""
    return psycopg2.connect(DB_URL)


def inicializar_db():
    """Crea las tablas si no existen. Llamar al inicio de la app."""
    if not DB_URL:
        return
    try:
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS cv_consumos (
                        id          SERIAL PRIMARY KEY,
                        fecha       TIMESTAMP DEFAULT NOW(),
                        usuario     VARCHAR(80),
                        modelo      VARCHAR(40),
                        tipo        VARCHAR(20),   -- 'haiku' | 'opus'
                        pregunta    TEXT,
                        tok_input   INTEGER,
                        tok_output  INTEGER,
                        costo_usd   NUMERIC(10,6)
                    );
                """)
            conn.commit()
    except Exception as e:
        print(f"[cv_db] Error inicializando tabla: {e}")


def registrar_consumo(usuario: str, tipo: str, pregunta: str,
                      tok_input: int, tok_output: int, modelo: str):
    """Inserta un registro de consumo en la base de datos."""
    if not DB_URL:
        return
    try:
        costos = COSTOS.get(tipo, {"input": 0, "output": 0})
        costo  = (tok_input * costos["input"] + tok_output * costos["output"]) / 1_000_000
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO cv_consumos
                        (usuario, modelo, tipo, pregunta, tok_input, tok_output, costo_usd)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (usuario, modelo, tipo, pregunta[:400],
                      tok_input, tok_output, round(costo, 6)))
            conn.commit()
    except Exception as e:
        print(f"[cv_db] Error registrando consumo: {e}")


def obtener_consumos(limit: int = 200):
    """Devuelve los últimos registros de consumo."""
    if not DB_URL:
        return []
    try:
        with _conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT fecha, usuario, tipo, modelo,
                           pregunta, tok_input, tok_output, costo_usd
                    FROM cv_consumos
                    ORDER BY fecha DESC
                    LIMIT %s
                """, (limit,))
                return cur.fetchall()
    except Exception as e:
        print(f"[cv_db] Error leyendo consumos: {e}")
        return []


def obtener_resumen():
    """Devuelve totales agrupados por usuario y tipo."""
    if not DB_URL:
        return []
    try:
        with _conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT
                        usuario,
                        tipo,
                        COUNT(*)            AS consultas,
                        SUM(tok_input)      AS tok_in_total,
                        SUM(tok_output)     AS tok_out_total,
                        SUM(costo_usd)      AS costo_total,
                        MAX(fecha)          AS ultima_consulta
                    FROM cv_consumos
                    GROUP BY usuario, tipo
                    ORDER BY costo_total DESC
                """)
                return cur.fetchall()
    except Exception as e:
        print(f"[cv_db] Error leyendo resumen: {e}")
        return []


def obtener_totales():
    """Devuelve totales globales."""
    if not DB_URL:
        return {}
    try:
        with _conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT
                        COUNT(*)         AS total_consultas,
                        SUM(tok_input)   AS total_tok_in,
                        SUM(tok_output)  AS total_tok_out,
                        SUM(costo_usd)   AS total_costo
                    FROM cv_consumos
                """)
                return dict(cur.fetchone() or {})
    except Exception as e:
        print(f"[cv_db] Error leyendo totales: {e}")
        return {}
