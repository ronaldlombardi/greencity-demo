"""
consolidar_zonas.py
Consolida las zonas dibujadas barrio por barrio (editor_zonas.html) y
recalcula en Python el conteo de árboles y la superficie de cada zona.

Entradas (carpeta data/):
  zonas_<barrio>.geojson              -> zonas dibujadas en el editor
  prueba_cimas_<barrio>_r2.geojson    -> cimas detectadas (radio 2 m)

Salidas (carpeta data/):
  zonas_villamaria.geojson            -> todas las zonas juntas (para el mapa)
  zonas_villamaria_resumen.json       -> totales por barrio, por tipo y ciudad

Uso:
  python consolidar_zonas.py
"""

import glob
import json
import os
from datetime import datetime

import geopandas as gpd
import pandas as pd

DATA_DIR = "data"
CRS_GEO = "EPSG:4326"
CRS_METRICO = "EPSG:22174"  # Gauss-Krüger faja 4 (Córdoba)
SALIDA_GEOJSON = os.path.join(DATA_DIR, "zonas_villamaria.geojson")
SALIDA_RESUMEN = os.path.join(DATA_DIR, "zonas_villamaria_resumen.json")

TOLERANCIA_AREA_PCT = 2.0  # diferencia aceptable editor vs recálculo

# --- Estimación de lotes (meta: 1 árbol por casa) ---------------------------
# ESTIMACIÓN PROVISORIA: reemplazar por el catastro municipal cuando esté disponible.
CUADRA_EJE_M = 130.0    # 150 varas (vara cordobesa 0,867 m, ley 1864) - eje a eje de calle
ANCHO_CALLE_M = 19.0    # referencia: ancho medio de calles AM Mendoza (19,07 m)
FRENTE_LOTE_M = 10.0    # frente de lote tipo
MANZANA_NETA_M = CUADRA_EJE_M - ANCHO_CALLE_M
LOTES_POR_MANZANA = 4 * MANZANA_NETA_M / FRENTE_LOTE_M
LOTES_POR_HA = LOTES_POR_MANZANA / (CUADRA_EJE_M ** 2 / 10000)

# Fracción de la superficie de la zona ocupada por lotes con casas
FACTOR_OCUPACION = {
    "urbana_residencial": 1.0,
    "urbana_centrica": 1.0,
    "urbana_mixta": 0.5,      # mezcla casas y espacios no urbanizados
    "bosque_autoctono": 0.0,  # sin casas: fuera de la meta
    "riberena": 0.5,          # casas junto a la ribera arbolada (como mixta)
    "industrial": 0.0,
    "predio_sin_urbanizar": 0.0,  # terreno vacío o loteo sin casas
    "parque_urbano": 0.0,         # suma árboles al barrio, no a la meta
}


def cargar_zonas(ruta):
    """Lee el geojson del editor: metadatos de cabecera + GeoDataFrame."""
    with open(ruta, encoding="utf-8") as f:
        data = json.load(f)
    meta = {k: v for k, v in data.items() if k not in ("type", "features")}
    if data.get("features"):
        gdf = gpd.GeoDataFrame.from_features(data["features"], crs=CRS_GEO)
    else:
        gdf = gpd.GeoDataFrame(columns=["geometry"], geometry="geometry", crs=CRS_GEO)
    return meta, gdf


def cargar_cimas(ruta):
    """Lee las cimas; cuenta solo puntos (el archivo incluye el contorno del barrio)."""
    gdf = gpd.read_file(ruta)
    if gdf.crs is None:
        gdf = gdf.set_crs(CRS_GEO)
    gdf = gdf.to_crs(CRS_GEO)
    gdf = gdf[gdf.geometry.geom_type == "Point"]
    gdf = gdf[["geometry"]].reset_index(drop=True)
    gdf["id_cima"] = gdf.index
    return gdf


def calcular_lotes(gdf):
    """Agrega lotes estimados, % de cumplimiento y déficit de árboles por zona."""
    gdf["factor_ocupacion"] = gdf["tipo"].map(FACTOR_OCUPACION).fillna(0.0)
    gdf["lotes_estimados"] = (
        gdf["area_ha"] * LOTES_POR_HA * gdf["factor_ocupacion"]
    ).round().astype(int)
    con_casas = gdf["lotes_estimados"] > 0
    gdf["cumplimiento_pct"] = (
        gdf["n_arboles"] / gdf["lotes_estimados"].where(con_casas) * 100
    ).round(1)
    gdf["deficit_arboles"] = (
        (gdf["lotes_estimados"] - gdf["n_arboles"]).clip(lower=0).where(con_casas, 0).astype(int)
    )
    return gdf


def resumen_lotes(gdf):
    """Totales de la meta para un conjunto de zonas (barrio o ciudad)."""
    con_casas = gdf[gdf["lotes_estimados"] > 0]
    lotes = int(con_casas["lotes_estimados"].sum())
    arboles = int(con_casas["n_arboles"].sum())
    return {
        "lotes_estimados": lotes,
        "arboles_zonas_casas": arboles,
        "cumplimiento_pct": round(arboles / lotes * 100, 1) if lotes else None,
        "deficit_arboles": int(con_casas["deficit_arboles"].sum()),
    }


def procesar_barrio(slug):
    ruta_zonas = os.path.join(DATA_DIR, f"zonas_{slug}.geojson")
    ruta_cimas = os.path.join(DATA_DIR, f"prueba_cimas_{slug}_r2.geojson")

    meta, zonas = cargar_zonas(ruta_zonas)
    cimas = cargar_cimas(ruta_cimas)
    barrio = meta.get("barrio", slug)
    avisos = []

    total_cimas = len(cimas)
    if meta.get("total_arboles_barrio") is not None and meta["total_arboles_barrio"] != total_cimas:
        avisos.append(
            f"total del barrio: editor {meta['total_arboles_barrio']} vs recálculo {total_cimas}"
        )

    if zonas.empty:
        avisos.append("sin zonas dibujadas")
        return barrio, meta, zonas, total_cimas, 0, total_cimas, avisos

    zonas = zonas.reset_index(drop=True)
    for col in ("tipo", "tipo_nombre", "lcz", "forestacion_incipiente", "n_arboles", "area_ha"):
        if col not in zonas.columns:
            zonas[col] = None
    zonas["forestacion_incipiente"] = zonas["forestacion_incipiente"].fillna(False)
    zonas["lcz"] = zonas["lcz"].fillna("")

    # Superficie en proyección métrica
    zonas["area_ha_calc"] = (zonas.to_crs(CRS_METRICO).geometry.area / 10000).round(2)

    # Asignación de cimas a zonas (punto dentro de polígono)
    union = gpd.sjoin(cimas, zonas[["zona_id", "geometry"]], how="inner", predicate="within")
    repetidas = union[union.duplicated("id_cima", keep=False)]
    if not repetidas.empty:
        n_rep = repetidas["id_cima"].nunique()
        ids = sorted(repetidas["zona_id"].unique().tolist())
        avisos.append(f"{n_rep} árboles en zonas superpuestas (zonas {ids}); se asignan a la de menor zona_id")
    union = union.sort_values("zona_id").drop_duplicates("id_cima", keep="first")

    conteo = union.groupby("zona_id").size()
    zonas["n_arboles_calc"] = zonas["zona_id"].map(conteo).fillna(0).astype(int)
    zonas["arboles_ha_calc"] = (
        zonas["n_arboles_calc"] / zonas["area_ha_calc"].where(zonas["area_ha_calc"] > 0)
    ).round(1).fillna(0)

    # Comparación con los valores del editor
    for _, z in zonas.iterrows():
        n_ed = z.get("n_arboles")
        a_ed = z.get("area_ha")
        if pd.notna(n_ed) and int(n_ed) != z["n_arboles_calc"]:
            avisos.append(
                f"zona {z['zona_id']}: árboles editor {int(n_ed)} vs recálculo {z['n_arboles_calc']}"
            )
        if pd.notna(a_ed) and a_ed > 0:
            dif = abs(z["area_ha_calc"] - a_ed) / a_ed * 100
            if dif > TOLERANCIA_AREA_PCT:
                avisos.append(
                    f"zona {z['zona_id']}: área editor {a_ed} ha vs recálculo {z['area_ha_calc']} ha ({dif:.1f}%)"
                )

    en_zonas = int(zonas["n_arboles_calc"].sum())
    sin_zona = total_cimas - en_zonas
    return barrio, meta, zonas, total_cimas, en_zonas, sin_zona, avisos


def main():
    archivos = sorted(glob.glob(os.path.join(DATA_DIR, "zonas_*.geojson")))
    archivos = [a for a in archivos if os.path.basename(a) not in (
        os.path.basename(SALIDA_GEOJSON),
    )]
    slugs = [os.path.basename(a)[len("zonas_"):-len(".geojson")] for a in archivos]
    print(f"Barrios encontrados: {len(slugs)}\n")

    capas = []
    barrios_resumen = []
    todos_avisos = {}

    for slug in slugs:
        ruta_cimas = os.path.join(DATA_DIR, f"prueba_cimas_{slug}_r2.geojson")
        if not os.path.exists(ruta_cimas):
            print(f"  [FALTA] {slug}: no existe {ruta_cimas}")
            todos_avisos[slug] = ["falta archivo de cimas"]
            continue

        barrio, meta, zonas, total, en_zonas, sin_zona, avisos = procesar_barrio(slug)

        zonas_lista = []
        if not zonas.empty:
            zonas_out = gpd.GeoDataFrame({
                "barrio": barrio,
                "zona_id": zonas["zona_id"],
                "tipo": zonas["tipo"],
                "tipo_nombre": zonas["tipo_nombre"],
                "lcz": zonas["lcz"],
                "forestacion_incipiente": zonas["forestacion_incipiente"].astype(bool),
                "n_arboles": zonas["n_arboles_calc"],
                "area_ha": zonas["area_ha_calc"],
                "arboles_ha": zonas["arboles_ha_calc"],
                        }, geometry=zonas.geometry, crs=CRS_GEO)
            zonas_out = calcular_lotes(zonas_out)
            capas.append(zonas_out)
            zonas_lista = json.loads(zonas_out.drop(columns="geometry").to_json(orient="records"))
            meta_barrio = resumen_lotes(zonas_out)
        else:
            meta_barrio = {"lotes_estimados": 0, "arboles_zonas_casas": 0,
                           "cumplimiento_pct": None, "deficit_arboles": 0}

        barrios_resumen.append({
            "barrio": barrio,
            "slug": slug,
            "total_arboles": int(total),
            "arboles_en_zonas": int(en_zonas),
            "arboles_sin_zona": int(sin_zona),
            "n_zonas": len(zonas_lista),
            "meta_1_arbol_por_casa": meta_barrio,
            "fecha_edicion": meta.get("fecha_edicion"),
            "notas": meta.get("notas", ""),
            "zonas": zonas_lista,
        })

        estado = "OK" if not avisos else "REVISAR"
        cumpl = meta_barrio["cumplimiento_pct"]
        cumpl_txt = f"{cumpl}%" if cumpl is not None else "s/casas"
        print(f"  [{estado}] {barrio}: {total} árboles | en zonas {en_zonas} | sin zona {sin_zona} | {len(zonas_lista)} zonas"
              f" | lotes {meta_barrio['lotes_estimados']} | meta {cumpl_txt}")
        for a in avisos:
            print(f"        - {a}")
        if avisos:
            todos_avisos[barrio] = avisos

    if not capas:
        print("\nNo se generaron zonas. Nada que guardar.")
        return

    # Salida 1: todas las zonas juntas
    todas = gpd.GeoDataFrame(pd.concat(capas, ignore_index=True), crs=CRS_GEO)
    todas.to_file(SALIDA_GEOJSON, driver="GeoJSON")

    # Totales por tipo de zona (ciudad)
    por_tipo = (
        todas.drop(columns="geometry")
        .groupby(["tipo", "tipo_nombre", "lcz"], as_index=False, dropna=False)
                .agg(n_zonas=("zona_id", "count"), n_arboles=("n_arboles", "sum"), area_ha=("area_ha", "sum"),
             lotes_estimados=("lotes_estimados", "sum"))
    )
    por_tipo["area_ha"] = por_tipo["area_ha"].round(2)
    por_tipo["arboles_ha"] = (por_tipo["n_arboles"] / por_tipo["area_ha"]).round(1)

    total_ciudad = sum(b["total_arboles"] for b in barrios_resumen)
    en_zonas_ciudad = sum(b["arboles_en_zonas"] for b in barrios_resumen)
    meta_ciudad = resumen_lotes(todas)

    resumen = {
        "municipio": "Villa María",
        "fuente_puntos": "Meta/WRI Canopy Height — cimas radio 2 m, umbral 2 m",
        "metodo": "Conteo por punto dentro de polígono y superficie en EPSG:22174, recalculados en Python",
        "metodo_lotes": {
            "estado": "Estimación provisoria — reemplazar por el catastro municipal",
            "cuadra_eje_m": CUADRA_EJE_M,
            "ancho_calle_m": ANCHO_CALLE_M,
            "frente_lote_m": FRENTE_LOTE_M,
            "lotes_por_manzana": round(LOTES_POR_MANZANA, 1),
            "lotes_por_ha": round(LOTES_POR_HA, 2),
            "factor_ocupacion": FACTOR_OCUPACION,
            "formula": "lotes = área_ha × lotes_por_ha × factor_ocupacion; "
                       "lotes_por_ha = 4 × (cuadra − calle) / frente ÷ (cuadra² / 10000)",
            "fuentes": [
                "Cuadra de 150 varas ≈ 130 m (vara cordobesa 0,867 m, ley de 1864)",
                "Ancho medio de calles 19,07 m — Área Metropolitana de Mendoza (referencia)",
            ],
        },
        "generado": datetime.now().isoformat(timespec="seconds"),
        "ciudad": {
            "n_barrios": len(barrios_resumen),
            "n_zonas": int(len(todas)),
            "total_arboles": int(total_ciudad),
            "arboles_en_zonas": int(en_zonas_ciudad),
            "arboles_sin_zona": int(total_ciudad - en_zonas_ciudad),
            "area_zonas_ha": round(float(todas["area_ha"].sum()), 2),
            "meta_1_arbol_por_casa": meta_ciudad,
        },
        "por_tipo": json.loads(por_tipo.to_json(orient="records")),
        "barrios": barrios_resumen,
        "avisos": todos_avisos,
    }
    with open(SALIDA_RESUMEN, "w", encoding="utf-8") as f:
        json.dump(resumen, f, ensure_ascii=False, indent=2)

    c = resumen["ciudad"]
    print("\n================ CIUDAD ================")
    print(f"Barrios: {c['n_barrios']} | Zonas: {c['n_zonas']}")
    print(f"Árboles totales: {c['total_arboles']} | en zonas: {c['arboles_en_zonas']} | sin zona: {c['arboles_sin_zona']}")
    print(f"Superficie de zonas: {c['area_zonas_ha']} ha")
    m = c["meta_1_arbol_por_casa"]
    print(f"\nMeta 1 árbol por casa (estimación, {LOTES_POR_HA:.1f} lotes/ha):")
    print(f"  Lotes estimados: {m['lotes_estimados']} | árboles en zonas de casas: {m['arboles_zonas_casas']}"
          f" | cumplimiento: {m['cumplimiento_pct']}% | déficit: {m['deficit_arboles']} árboles")
    print("\nPor tipo de zona:")
    for _, t in por_tipo.iterrows():
        print(f"  {t['tipo_nombre']:<40} {t['n_zonas']:>3} zonas  {t['n_arboles']:>6} árb  {t['area_ha']:>8} ha"
              f"  {t['arboles_ha']:>6} árb/ha  {t['lotes_estimados']:>6} lotes")
    print(f"\nBarrios con avisos: {len(todos_avisos)}")
    print(f"\nGuardado: {SALIDA_GEOJSON}")
    print(f"Guardado: {SALIDA_RESUMEN}")


if __name__ == "__main__":
    main()