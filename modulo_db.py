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

# Costos por millón de tokens (USD) — verificar contra la facturación de Anthropic
COSTOS = {
    "haiku":  {"input": 0.80,  "output": 4.00},   # claude-haiku-4-5
    "opus":   {"input": 15.00, "output": 75.00},   # claude-opus-4-7 (Asistente)
    "opus55": {"input": 4.00,  "output": 20.00},  # claude-opus-5-5 (Masterplan)
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
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS cv_masteplans (
                        id          SERIAL PRIMARY KEY,
                        fecha       TIMESTAMP DEFAULT NOW(),
                        usuario     VARCHAR(80),
                        ciudad      VARCHAR(80)  DEFAULT 'Villa María',
                        foco        TEXT,
                        texto       TEXT,
                        tok_input   INTEGER,
                        tok_output  INTEGER,
                                                costo_usd   NUMERIC(10,6),
                        palabras    INTEGER
                    );
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS cv_decisiones_c40 (
                        id          SERIAL PRIMARY KEY,
                        ciudad      VARCHAR(80)  NOT NULL DEFAULT 'Villa María',
                        id_linea    VARCHAR(60)  NOT NULL,
                        prioridad   VARCHAR(20)  NOT NULL,
                        nota        TEXT,
                        usuario     VARCHAR(80),
                        fecha       TIMESTAMP DEFAULT NOW(),
                                                UNIQUE (ciudad, id_linea)
                    );
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS cv_eventos_huella (
                        id                SERIAL PRIMARY KEY,
                        fecha_registro    TIMESTAMP DEFAULT NOW(),
                        ciudad            VARCHAR(80)  NOT NULL DEFAULT 'Villa María',
                        nombre            VARCHAR(200) NOT NULL,
                        fecha_evento      DATE,
                        plantilla         VARCHAR(60),
                        parametros        TEXT,
                        resultado         TEXT,
                        acciones          TEXT,
                        total_t           NUMERIC(12,3),
                        total_mitigado_t  NUMERIC(12,3),
                                                usuario           VARCHAR(80)
                    );
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS cv_requisitos_financiamiento (
                        id            SERIAL PRIMARY KEY,
                        ciudad        VARCHAR(80)  NOT NULL DEFAULT 'Villa María',
                        id_requisito  VARCHAR(60)  NOT NULL,
                        estado        VARCHAR(20)  NOT NULL,
                        valor         TEXT,
                        fuente        TEXT,
                        usuario       VARCHAR(80),
                        fecha         TIMESTAMP DEFAULT NOW(),
                        UNIQUE (ciudad, id_requisito)
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


def guardar_masterplan(usuario: str, foco: str, texto: str,
                       tok_input: int, tok_output: int, ciudad: str = "Villa María"):
    """Guarda un Masterplan generado en la base de datos."""
    if not DB_URL:
        return None
    try:
        costos = COSTOS.get("opus55", {"input": 4.0, "output": 20.0})
        costo  = (tok_input * costos["input"] + tok_output * costos["output"]) / 1_000_000
        palabras = len(texto.split())
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO cv_masteplans
                        (usuario, ciudad, foco, texto, tok_input, tok_output, costo_usd, palabras)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (usuario, ciudad, foco[:500], texto,
                      tok_input, tok_output, round(costo, 6), palabras))
                nuevo_id = cur.fetchone()[0]
            conn.commit()
        return nuevo_id
    except Exception as e:
        print(f"[cv_db] Error guardando masterplan: {e}")
        return None


def obtener_masteplans(usuario: str = None, limit: int = 10, ciudad: str = None):
    """Devuelve los últimos Masteplans. Si usuario es None, devuelve todos.
    Si ciudad se especifica, filtra solo los de esa ciudad (separación VM/VN)."""
    if not DB_URL:
        return []
    try:
        with _conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                condiciones = []
                params = []
                if usuario:
                    condiciones.append("usuario = %s")
                    params.append(usuario)
                if ciudad:
                    condiciones.append("ciudad = %s")
                    params.append(ciudad)

                where = f"WHERE {' AND '.join(condiciones)}" if condiciones else ""
                params.append(limit)

                cur.execute(f"""
                    SELECT id, fecha, usuario, ciudad, foco, texto,
                           tok_input, tok_output, costo_usd, palabras
                    FROM cv_masteplans
                    {where}
                    ORDER BY fecha DESC
                    LIMIT %s
                """, tuple(params))
                return cur.fetchall()
    except Exception as e:
        print(f"[cv_db] Error leyendo masteplans: {e}")
        return []


def obtener_masterplan_por_id(masterplan_id: int):
    """Devuelve un Masterplan específico por ID."""
    if not DB_URL:
        return None
    try:
        with _conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT id, fecha, usuario, ciudad, foco, texto,
                           tok_input, tok_output, costo_usd, palabras
                    FROM cv_masteplans
                    WHERE id = %s
                """, (masterplan_id,))
                return cur.fetchone()
    except Exception as e:
        print(f"[cv_db] Error leyendo masterplan {masterplan_id}: {e}")
        return None


def eliminar_masterplan(masterplan_id: int) -> bool:
    """Borra un masterplan guardado por id. Devuelve True si borró algo."""
    conn = _conn()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM cv_masteplans WHERE id = %s", (masterplan_id,))
            borrado = cur.rowcount > 0
        conn.commit()
        return borrado
    finally:
        conn.close()


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


# ============================================================
# DECISIONES PARA VILLA MARÍA EN LÍNEA CON C40
# ============================================================

def guardar_decision(ciudad: str, id_linea: str, prioridad: str,
                     nota: str, usuario: str) -> bool:
    """Guarda (o actualiza) la prioridad de una línea de acción C40 para una ciudad."""
    if not DB_URL:
        return False
    try:
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO cv_decisiones_c40
                        (ciudad, id_linea, prioridad, nota, usuario, fecha)
                    VALUES (%s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (ciudad, id_linea) DO UPDATE SET
                        prioridad = EXCLUDED.prioridad,
                        nota      = EXCLUDED.nota,
                        usuario   = EXCLUDED.usuario,
                        fecha     = NOW()
                """, (ciudad, id_linea, prioridad, (nota or "")[:1000], usuario))
            conn.commit()
        return True
    except Exception as e:
        print(f"[cv_db] Error guardando decisión C40: {e}")
        return False


def obtener_decisiones(ciudad: str = "Villa María") -> dict:
    """Devuelve las decisiones C40 guardadas para una ciudad, como {id_linea: fila}."""
    if not DB_URL:
        return {}
    try:
        with _conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT id_linea, prioridad, nota, usuario, fecha
                    FROM cv_decisiones_c40
                    WHERE ciudad = %s
                """, (ciudad,))
                return {fila["id_linea"]: dict(fila) for fila in cur.fetchall()}
    except Exception as e:
        print(f"[cv_db] Error leyendo decisiones C40: {e}")
        return {}


# ============================================================
# HUELLA DE CARBONO DE EVENTOS
# ============================================================

def guardar_evento_huella(ciudad: str, nombre: str, fecha_evento, plantilla: str,
                          parametros: dict, resultado: dict, acciones: list,
                          total_t: float, total_mitigado_t: float, usuario: str):
    """Guarda un evento con su huella calculada. Devuelve el id o None."""
    if not DB_URL:
        return None
    import json as _json
    try:
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO cv_eventos_huella
                        (ciudad, nombre, fecha_evento, plantilla, parametros, resultado,
                         acciones, total_t, total_mitigado_t, usuario)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (ciudad, nombre[:200], fecha_evento, plantilla,
                      _json.dumps(parametros, ensure_ascii=False),
                      _json.dumps(resultado, ensure_ascii=False),
                      _json.dumps(acciones, ensure_ascii=False),
                      round(total_t, 3), round(total_mitigado_t, 3), usuario))
                nuevo_id = cur.fetchone()[0]
            conn.commit()
        return nuevo_id
    except Exception as e:
        print(f"[cv_db] Error guardando evento: {e}")
        return None


def obtener_eventos_huella(ciudad: str = "Villa María", anio: int = None) -> list:
    """Devuelve los eventos guardados de una ciudad (opcionalmente de un año), por fecha."""
    if not DB_URL:
        return []
    import json as _json
    try:
        with _conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if anio:
                    cur.execute("""
                        SELECT * FROM cv_eventos_huella
                        WHERE ciudad = %s AND EXTRACT(YEAR FROM fecha_evento) = %s
                        ORDER BY fecha_evento, id
                    """, (ciudad, anio))
                else:
                    cur.execute("""
                        SELECT * FROM cv_eventos_huella
                        WHERE ciudad = %s
                        ORDER BY fecha_evento, id
                    """, (ciudad,))
                filas = []
                for f in cur.fetchall():
                    f = dict(f)
                    for campo in ("parametros", "resultado", "acciones"):
                        try:
                            f[campo] = _json.loads(f[campo]) if f.get(campo) else None
                        except Exception:
                            f[campo] = None
                    filas.append(f)
                return filas
    except Exception as e:
        print(f"[cv_db] Error leyendo eventos: {e}")
        return []


def eliminar_evento_huella(evento_id: int) -> bool:
    """Borra un evento guardado. Devuelve True si borró algo."""
    if not DB_URL:
        return False
    try:
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM cv_eventos_huella WHERE id = %s", (evento_id,))
                borrado = cur.rowcount > 0
            conn.commit()
        return borrado
        except Exception as e:
        print(f"[cv_db] Error borrando evento: {e}")
        return False


# ============================================================
# BONOS VERDES — REQUISITOS DE FINANCIAMIENTO (carga del admin)
# ============================================================

def guardar_requisito(ciudad: str, id_requisito: str, estado: str,
                      valor: str, fuente: str, usuario: str) -> bool:
    """Guarda (o actualiza) el estado de un requisito que evalúa el municipio.
    estado: 'cumple' | 'parcial' | 'falta'. fuente: documento o norma que lo respalda."""
    if not DB_URL:
        return False
    try:
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO cv_requisitos_financiamiento
                        (ciudad, id_requisito, estado, valor, fuente, usuario, fecha)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (ciudad, id_requisito) DO UPDATE SET
                        estado  = EXCLUDED.estado,
                        valor   = EXCLUDED.valor,
                        fuente  = EXCLUDED.fuente,
                        usuario = EXCLUDED.usuario,
                        fecha   = NOW()
                """, (ciudad, id_requisito, estado, (valor or "")[:500],
                      (fuente or "")[:1000], usuario))
            conn.commit()
        return True
    except Exception as e:
        print(f"[cv_db] Error guardando requisito: {e}")
        return False


def obtener_requisitos(ciudad: str = "Villa María") -> dict:
    """Devuelve los requisitos cargados por el admin, como {id_requisito: fila}."""
    if not DB_URL:
        return {}
    try:
        with _conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT id_requisito, estado, valor, fuente, usuario, fecha
                    FROM cv_requisitos_financiamiento
                    WHERE ciudad = %s
                """, (ciudad,))
                return {fila["id_requisito"]: dict(fila) for fila in cur.fetchall()}
    except Exception as e:
        print(f"[cv_db] Error leyendo requisitos: {e}")
        return {}
