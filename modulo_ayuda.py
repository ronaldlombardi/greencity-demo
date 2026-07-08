"""
modulo_ayuda.py
===============
Contenido técnico expandible (ℹ️) para cada sección del dashboard GreenCity.
Destinatario: Director de Ambiente / perfil técnico con formación en ingeniería.
"""

import streamlit as st


def ayuda_cobertura():
    with st.expander("ℹ️ Metodología — Cobertura del suelo"):
        st.markdown("""
        ### Fuente: ESA WorldCover 2020

        **Producto:** ESA WorldCover v100 — mapa global de cobertura del suelo del año 2020.  
        **Organismo:** Agencia Espacial Europea (ESA) — programa Copernicus.  
        **Resolución espacial:** 10 metros por pixel.  
        **Acceso:** Google Earth Engine, colección `ESA/WorldCover/v100/2020`.

        ---

        ### Sensor y adquisición

        El producto se genera a partir de imágenes **Sentinel-1** (radar SAR, banda C, 
        resolución 10m) y **Sentinel-2** (multispectral óptico, 13 bandas, resolución 10-60m).
        La combinación de radar + óptico permite clasificar correctamente áreas con cobertura 
        de nubes persistente y distinguir vegetación de superficies artificiales con mayor 
        precisión que cada sensor por separado.

        ---

        ### Clasificación

        El algoritmo emplea una cadena de clasificación supervisada con **Random Forest** 
        entrenado sobre muestras de referencia globales validadas por fotointerpretación. 
        Las 11 clases del producto son:

        | Código | Clase | Color |
        |--------|-------|-------|
        | 10 | Árboles (Tree cover) | Verde oscuro |
        | 20 | Arbustos (Shrubland) | Ocre |
        | 30 | Pastizales (Grassland) | Amarillo |
        | 40 | Cultivos (Cropland) | Amarillo claro |
        | 50 | Edificado (Built-up) | Rojo |
        | 60 | Suelo desnudo (Bare/sparse) | Beige |
        | 70 | Nieve/hielo | Blanco |
        | 80 | Cuerpos de agua (Permanent water) | Azul |
        | 90 | Humedales (Herbaceous wetland) | Azul claro |
        | 95 | Manglares (Mangroves) | Verde agua |
        | 100 | Musgos/líquenes (Moss and lichen) | Gris |

        ---

        ### Cálculo en GreenCity

        Para cada ciudad se extrae el porcentaje de cada clase sobre el área total:

        ```python
        # Área de estudio definida como polígono WGS84
        area = ee.Geometry.Polygon(coordenadas)
        wc   = ee.Image('ESA/WorldCover/v100/2020').clip(area)

        # Conteo de pixels por clase
        total_pix  = ee.Image.constant(1).reduceRegion(ee.Reducer.sum(), area, scale=10)
        arboles    = wc.eq(10).reduceRegion(ee.Reducer.sum(), area, scale=10)

        # Porcentaje
        pct_arboles = (arboles / total_pix) * 100
        ```

        La escala de 10m significa que cada pixel representa exactamente 100 m² de superficie.

        ---

        ### Limitaciones

        - El mapa corresponde al año **2020** — cambios posteriores no están reflejados.
        - En áreas urbanas densas, el algoritmo puede confundir **arbolado de alineación** 
          (árboles de calle) con áreas edificadas si el dosel es angosto (<10m).
        - Los **cultivos periurbanos** (clase 40) son frecuentemente confundidos con 
          pastizales según el estado fenológico en la fecha de captura.
        - La clase "árboles" incluye tanto arbolado público como privado (patios, jardines).

        ---

        ### Referencias

        - Zanaga, D. et al. (2022). *ESA WorldCover 10m 2020 v100*. Zenodo. 
          https://doi.org/10.5281/zenodo.5571936
        - Sentinel-2 MSI: https://sentinel.esa.int/web/sentinel/missions/sentinel-2
        """)


def ayuda_accesibilidad():
    with st.expander("ℹ️ Metodología — Accesibilidad a espacios verdes"):
        st.markdown("""
        ### Concepto: accesibilidad espacial al verde

        Se mide la distancia euclidiana desde cada pixel de zona edificada hasta el 
        pixel de zona verde más cercano. El estándar internacional utilizado es el de 
        la **Organización Mundial de la Salud (OMS)**: toda la población urbana debería 
        tener acceso a un espacio verde en un radio de **300 metros** desde su vivienda.

        ---

        ### Algoritmo: Distance Transform

        El cálculo se realiza íntegramente en Google Earth Engine con el operador 
        `fastDistanceTransform`, que implementa una transformada de distancia euclidiana 
        sobre imágenes raster:

        ```python
        # 1. Máscara de zonas verdes (clases 10, 20, 30 de WorldCover)
        verde = wc.eq(10).Or(wc.eq(20)).Or(wc.eq(30)).selfMask()

        # 2. Transformada de distancia euclidiana
        #    Retorna distancia en unidades de pixel (10m c/u)
        dist_px = verde.fastDistanceTransform(neighborhood=1000)

        # 3. Conversión a metros
        dist_m = dist_px.sqrt().multiply(10)

        # 4. Aplicar solo sobre pixels edificados
        zona_edificada = wc.eq(50).selfMask()
        dist_edificada = dist_m.updateMask(zona_edificada)
        ```

        El parámetro `neighborhood=1000` define el radio de búsqueda en pixels 
        (1000 × 10m = 10km), suficiente para cualquier contexto urbano analizado.

        ---

        ### Métricas calculadas

        **% de acceso (<300m):**
        ```python
        pixels_con_acceso = dist_edificada.lt(300).reduceRegion(ee.Reducer.sum(), area, 10)
        pixels_edificados  = zona_edificada.reduceRegion(ee.Reducer.sum(), area, 10)
        pct_acceso = (pixels_con_acceso / pixels_edificados) * 100
        ```

        **Distancia media:**
        ```python
        dist_media = dist_edificada.reduceRegion(ee.Reducer.mean(), area, 10)
        ```

        **m² de verde por habitante:**
        ```python
        # Total de pixels verdes × 100m² por pixel / población total
        m2_hab = (pixels_verdes * 100) / poblacion
        ```

        ---

        ### Distribución por rangos

        Se calculan cuatro rangos de distancia sobre los pixels edificados:
        - **0-100m:** verde inmediato, máxima accesibilidad
        - **100-300m:** dentro del estándar OMS (caminata de ~4 minutos)
        - **300-500m:** acceso moderado (caminata de ~6-7 minutos)
        - **>500m:** déficit de acceso

        ---

        ### Limitaciones

        - La distancia es **euclidiana** (línea recta), no distancia de recorrido real 
          por la red vial. La distancia real puede ser 20-40% mayor en ciudades con 
          manzanas grandes o barreras físicas (vías de tren, autopistas, ríos).
        - Se considera "verde accesible" cualquier pixel de las clases 10/20/30, 
          incluyendo vegetación privada. Para verde público real, ver módulo OSM.
        - No considera la **calidad** del espacio verde (equipamiento, seguridad, 
          mantenimiento).

        ---

        ### Referencias

        - OMS (2016). *Urban green spaces and health: a review of evidence*. WHO Regional 
          Office for Europe. https://www.who.int/publications/i/item/urban-green-spaces
        - Gorelick, N. et al. (2017). Google Earth Engine: Planetary-scale geospatial 
          analysis for everyone. *Remote Sensing of Environment*, 202, 18-27.
        """)


def ayuda_temperatura():
    with st.expander("ℹ️ Metodología — Temperatura superficial (LST)"):
        st.markdown("""
        ### Fuente: Landsat 8/9 — Banda térmica TIRS

        **Producto:** Landsat Collection 2, Level 2 — Surface Temperature (ST_B10)  
        **Organismos:** USGS (United States Geological Survey) + NASA  
        **Satélites:** Landsat 8 (lanzado 2013) y Landsat 9 (lanzado 2021)  
        **Resolución espacial:** 30 metros por pixel  
        **Revisita:** cada 16 días por satélite (8 días combinando L8+L9)  
        **Acceso:** Google Earth Engine, colecciones `LANDSAT/LC08/C02/T1_L2` y `LANDSAT/LC09/C02/T1_L2`

        ---

        ### Sensor TIRS (Thermal Infrared Sensor)

        El TIRS mide la radiancia emitida por la superficie terrestre en la **banda 10** 
        (10.6-11.19 μm, infrarrojo térmico). Esta radiancia depende de la temperatura 
        y de la emisividad del material.

        La banda B10 del producto Collection 2 Level 2 ya incluye corrección atmosférica 
        aplicada por el USGS usando el algoritmo **Single Channel** de Jiménez-Muñoz 
        et al. (2014), que corrige el efecto de absorción del vapor de agua atmosférico.

        ---

        ### Cálculo de LST en GreenCity

        **Paso 1 — Temperatura de brillo (TB):**
        ```python
        # Conversión de DN a Kelvin (factores de escala Collection 2)
        TB = ST_B10 × 0.00341802 + 149.0   # en Kelvin
        ```

        **Paso 2 — NDVI para emisividad:**
        ```python
        NDVI = (NIR - RED) / (NIR + RED)   # bandas SR_B5 y SR_B4
        ```

        **Paso 3 — Proporción de vegetación (Pv):**
        ```python
        Pv = ((NDVI - 0.2) / 0.3)²     # clampado entre 0 y 1
        ```

        **Paso 4 — Emisividad (ε):**
        ```python
        ε = 0.004 × Pv + 0.986
        # Valores típicos: asfalto ≈ 0.986, vegetación densa ≈ 0.990
        ```

        **Paso 5 — LST corregida por emisividad (Sobrino et al., 2004):**
        ```
        LST = TB / (1 + (λ × TB / ρ) × ln(ε)) − 273.15
        ```
        Donde:
        - λ = 10.895 μm (longitud de onda central banda B10)
        - ρ = h × c / σ = 14388 μm·K (constante de radiación térmica)
        - El término `−273.15` convierte de Kelvin a Celsius

        **Paso 6 — Composición temporal:**
        ```python
        # Mediana del período verano austral (dic-feb)
        # Filtro: nubosidad < 20%
        lst_mediana = coleccion.select('LST_celsius').median().clip(area)
        ```

        La mediana es más robusta que la media para eliminar valores anómalos 
        por nubes residuales o sombras.

        ---

        ### Isla de calor urbano (UHI)

        El diferencial de temperatura urbano-verde (ΔT) cuantifica el efecto isla de calor:

        ```python
        mask_urbano = WorldCover.eq(50)          # clase edificada
        mask_verde  = WorldCover.eq(10).Or(eq(30))  # árboles + pastizales

        T_urbano = LST.updateMask(mask_urbano).reduceRegion(mean)
        T_verde  = LST.updateMask(mask_verde).reduceRegion(mean)

        ΔT_UHI = T_urbano - T_verde
        ```

        Clasificación de intensidad UHI (literatura internacional):
        - **< 1.5°C:** efecto bajo — vegetación existente regula adecuadamente
        - **1.5 – 3°C:** moderado — intervención recomendada
        - **> 3°C:** alto — urgente incremento de masa verde y superficies permeables

        ---

        ### Correlación NDVI ↔ LST

        Para cuantificar el efecto enfriador de la vegetación densa:

        ```python
        # Zonas con vegetación densa (NDVI > 0.4)
        T_ndvi_alto = LST.updateMask(NDVI.gt(0.4)).reduceRegion(mean)

        # Zonas de suelo desnudo o asfalto (NDVI < 0.2)
        T_ndvi_bajo = LST.updateMask(NDVI.lt(0.2)).reduceRegion(mean)

        enfriamiento = T_ndvi_bajo - T_ndvi_alto   # °C de diferencia
        ```

        ---

        ### Interpretación de valores absolutos

        La LST **NO es la temperatura del aire** (que mide el termómetro a 1.5m de altura). 
        Es la temperatura radiante de la superficie. En verano cordobés:
        - Asfalto en calzada: puede alcanzar 55-65°C de LST
        - Pasto irrigado: 25-32°C de LST
        - Temperatura del aire simultánea: 35-40°C

        Lo analíticamente relevante es la **diferencia relativa entre coberturas** 
        (ΔT UHI), no el valor absoluto de LST.

        ---

        ### Referencias

        - Jiménez-Muñoz, J.C. et al. (2014). Land surface temperature retrieval methods 
          from Landsat-8 thermal infrared sensor data. *IEEE Geoscience and Remote Sensing 
          Letters*, 11(10), 1840-1843.
        - Sobrino, J.A. et al. (2004). Land surface temperature retrieval from LANDSAT TM 5. 
          *Remote Sensing of Environment*, 90(4), 434-440.
        - USGS (2023). *Landsat Collection 2 Level-2 Science Product Guide*. 
          https://www.usgs.gov/landsat-missions/landsat-collection-2-level-2-science-products
        """)


def ayuda_osm():
    with st.expander("ℹ️ Metodología — Verde público (OpenStreetMap)"):
        st.markdown("""
        ### Fuente: OpenStreetMap (OSM)

        **Proyecto:** OpenStreetMap — base de datos geográfica colaborativa y de acceso libre.  
        **API utilizada:** Overpass API — interfaz de consulta de datos OSM por área geográfica.  
        **Acceso:** https://overpass-api.de/api/interpreter  
        **Formato de respuesta:** GeoJSON / JSON  
        **Actualización:** continua (comunidad de voluntarios + organismos oficiales)

        ---

        ### ¿Por qué OSM y no solo el satélite?

        El análisis satelital (WorldCover) detecta **toda la vegetación** presente en el 
        territorio, independientemente de su régimen de propiedad o accesibilidad:
        patios privados, campos de golf privados, terrenos baldíos con pastizales, jardines 
        de empresas y predios agrícolas periurbanos se clasifican igual que una plaza pública.

        OSM, en cambio, contiene **únicamente los espacios catalogados por la comunidad** 
        como de uso público o semipúblico. La diferencia entre ambos valores cuantifica 
        el verde físicamente presente pero **no accesible para los vecinos**.

        ---

        ### Etiquetas OSM consultadas

        La consulta Overpass filtra elementos por las siguientes etiquetas (tags):

        | Categoría GreenCity | Etiquetas OSM | Descripción |
        |---------------------|---------------|-------------|
        | Parques | `leisure=park` | Parques públicos de cualquier escala |
        | Plazas / jardines | `leisure=garden`, `place=square` | Plazas, jardines ornamentales |
        | Deportivo | `leisure=pitch`, `leisure=sports_centre` | Canchas, polideportivos |
        | Juegos | `leisure=playground` | Plazas de juegos infantiles |
        | Áreas verdes | `landuse=grass`, `landuse=recreation_ground`, `landuse=meadow` | Espacios verdes sin equipamiento |
        | Naturaleza | `natural=wood`, `landuse=forest` | Arboledas, bosques urbanos |
        | Cementerios | `landuse=cemetery` | Incluidos por su masa verde |

        Referencia completa: https://wiki.openstreetmap.org/wiki/Key:leisure

        ---

        ### Query Overpass QL

        ```
        [out:json][timeout:60];
        (
          way[leisure=park](-32.44,-63.28,-32.39,-63.20);
          way[leisure=garden](-32.44,-63.28,-32.39,-63.20);
          way[landuse=grass](-32.44,-63.28,-32.39,-63.20);
          // ... resto de etiquetas
          relation[leisure=park](-32.44,-63.28,-32.39,-63.20);
        );
        out body;
        >;
        out skel qt;
        ```

        El bbox (bounding box) corresponde a las coordenadas `(sur, oeste, norte, este)` 
        del área de estudio en WGS84.

        ---

        ### Procesamiento geométrico

        Los elementos OSM se devuelven como nodos, ways (polilíneas/polígonos) y relations. 
        Para calcular superficies:

        ```python
        from shapely.geometry import Polygon
        from shapely.ops import unary_union

        # Construir polígono desde nodos del way
        coords = [(nodo['lon'], nodo['lat']) for nodo in way['nodes']]
        poligono = Polygon(coords)

        # Conversión grados² → m² (aproximación para latitud ~32°S)
        # 1° latitud ≈ 111.320 km; 1° longitud ≈ 111.320 × cos(32°) ≈ 94.4 km
        area_m2 = poligono.area × 111320 × 111320 × cos(32°)
                = poligono.area × 111320 × 111320 × 0.848
        ```

        Para evitar doble conteo de polígonos superpuestos:
        ```python
        union = unary_union([p['geometry'] for p in poligonos])
        area_total_m2 = union.area × 111320 × 111320 × 0.848
        ```

        ---

        ### Indicador OMS

        La OMS recomienda entre **9 y 15 m² de verde público por habitante** 
        (Green Space per Capita). GreenCity calcula:

        ```python
        m2_hab = area_total_m2 / poblacion_total
        ```

        Clasificación:
        - **≥ 15 m²/hab:** cumple umbral óptimo OMS
        - **9 – 15 m²/hab:** dentro del rango recomendado
        - **< 9 m²/hab:** por debajo del mínimo OMS

        ---

        ### Limitaciones

        - La **completitud de OSM** depende de la actividad de la comunidad local. 
          Ciudades con comunidades OSM activas tienen datos más completos.
        - Los espacios sin nombre o sin etiqueta de `leisure/landuse` no son capturados.
        - Espacios de acceso **semipúblico** (clubes, espacios religiosos, colegios) 
          pueden estar catalogados o no según criterio del cartógrafo.
        - La superficie real puede diferir levemente de la calculada por la aproximación 
          en la conversión de coordenadas geográficas a metros planos.

        ---

        ### Referencias

        - OpenStreetMap Wiki: https://wiki.openstreetmap.org/wiki/Map_features
        - OMS (2016). *Urban green spaces and health*. WHO/EURO.
        - Overpass API docs: https://wiki.openstreetmap.org/wiki/Overpass_API
        """)


def ayuda_censo():
    with st.expander("ℹ️ Metodología — Análisis socioespacial (Censo 2022)"):
        st.markdown("""
        ### Fuente: INDEC — Censo Nacional de Población, Hogares y Viviendas 2022

        **Organismo:** Instituto Nacional de Estadística y Censos (INDEC)  
        **Fecha de relevamiento:** 18 de mayo de 2022 (estrategia bimodal: digital + papel)  
        **Publicación definitiva:** enero 2024  
        **Acceso:** https://censo.gob.ar / https://redatam.indec.gob.ar  
        **Escala de datos disponibles en GreenCity:** nivel departamental (San Martín / San Justo)

        ---

        ### Indicadores utilizados

        **Demográficos:**
        - Población total y variación intercensal 2010-2022
        - Estructura etaria: grupos 0-14 años (niños) y 65+ años (adultos mayores)
        - Estos grupos tienen mayor necesidad de verde accesible y de calidad

        **Condiciones habitacionales (proxy de vulnerabilidad):**

        | Indicador | Descripción | Umbral alerta |
        |-----------|-------------|---------------|
        | Piso de tierra | % viviendas con piso de tierra o ladrillo suelto | >5% |
        | Sin agua de red | % sin provisión de agua por red dentro de la vivienda | >10% |
        | Sin inodoro con descarga | % sin saneamiento básico | >3% |
        | Hacinamiento | % hogares con >3 personas por cuarto | >7% |
        | Sin gas de red | % sin acceso a gas natural por red | >40% |

        Estos indicadores son proxies del **Índice de Privación Material de los Hogares 
        (IPMH)** del Censo 2022, que mide privación patrimonial y de recursos corrientes.

        ---

        ### Análisis espacial por grilla

        Dado que los microdatos REDATAM a nivel de radio censal aún no estaban disponibles 
        al momento del análisis, GreenCity implementa un análisis por **grilla de 450m**:

        ```python
        PASO_GRADOS = 0.004   # ≈ 450m a latitud 32°S

        # Para cada celda de la grilla se calcula con GEE:
        # 1. % de superficie edificada (proxy de densidad poblacional)
        # 2. Distancia media al verde más cercano
        # 3. % de pixels edificados con acceso <300m al verde
        ```

        La población se estima proporcionalmente al porcentaje de suelo edificado:
        ```python
        pob_celda = pob_total × (pct_edificado_celda / sum(pct_edificado_todas_celdas))
        ```

        ---

        ### Índice de equidad espacial

        Mide la homogeneidad del acceso al verde entre sectores de la ciudad.  
        Se usa el **Coeficiente de Variación (CV)** de la distancia al verde, 
        ponderado por la población estimada de cada celda:

        ```python
        # Media ponderada por población
        dist_media = Σ(dist_i × pob_i) / Σ(pob_i)

        # Varianza ponderada
        var = Σ(pob_i × (dist_i - dist_media)²) / Σ(pob_i)

        # Coeficiente de variación (%)
        CV = √var / dist_media × 100
        ```

        Interpretación del CV:
        - **CV < 30%:** alta equidad — todos los sectores tienen acceso similar
        - **30% < CV < 60%:** equidad media — existen diferencias sectoriales
        - **CV > 60%:** baja equidad — sectores con acceso muy dispar

        ---

        ### Índice de Vulnerabilidad Ambiental (IVA)

        Indicador compuesto que combina condiciones habitacionales con acceso al verde:

        | Factor | Condición | Puntos |
        |--------|-----------|--------|
        | Piso de tierra | > 5% | +1 |
        | Sin agua de red | > 10% | +1 |
        | Hacinamiento | > 7% | +1 |
        | Acceso al verde | < 90% de pob. con acceso | +2 |
        | Equidad espacial | CV > 60% | +2 |
        | Envejecimiento | > 18% mayores de 65 | +1 |

        **Clasificación:** Bajo (0-1) · Medio (2-3) · Alto (4-8)

        La combinación de privación material + déficit de verde identifica las zonas donde 
        la falta de espacios verdes agrava condiciones de vulnerabilidad preexistentes, 
        priorizando la inversión pública.

        ---

        ### Limitaciones y mejoras futuras

        - Los datos de condiciones habitacionales están disponibles a **nivel departamental**, 
          no a nivel de radio censal. Esto introduce varianza intra-municipal no capturable.
        - Cuando INDEC publique el REDATAM completo con microdatos a nivel de radio censal, 
          el script `paso10_censo2022.py` puede actualizarse para usar los polígonos exactos.
        - El análisis por grilla no captura barreras físicas reales (vías de tren, ríos, 
          autopistas) que segmentan la accesibilidad real.

        ---

        ### Nota sobre disponibilidad de datos

        El **REDATAM del Censo 2022** (microdatos a nivel de radio censal) estaba en proceso 
        de publicación al momento de este análisis. Los shapefiles de radios censales están 
        disponibles en: https://geoestadistica.indec.gob.ar/

        Para activar el análisis por radio censal exacto, descargar el shapefile y nombrarlo 
        `radios_cordoba_2022.shp` en la carpeta del proyecto.

        ---

        ### Referencias

        - INDEC (2023). *Censo Nacional de Población, Hogares y Viviendas 2022 — 
          Resultados definitivos*. https://censo.gob.ar
        - INDEC (2022). *Índice de Privación Material de los Hogares (IPMH)*. 
          https://www.indec.gob.ar
        - Rodríguez, G.M. (2024). *Base cartográfica de radios del censo argentino 2022*. 
          CEUR-CONICET. http://hdl.handle.net/11336/238198
        """)


def ayuda_comparativa():
    with st.expander("ℹ️ Sobre la comparativa entre ciudades"):
        st.markdown("""
        ### Criterios de comparación

        GreenCity compara las ciudades usando indicadores normalizados que permiten 
        comparación independientemente del tamaño o densidad de cada ciudad:

        | Indicador | Unidad | Fuente | Qué mide |
        |-----------|--------|--------|----------|
        | Arbolado urbano | % de superficie | ESA WorldCover | Masa forestal urbana |
        | Acceso <300m | % de población | GEE + WorldCover | Proximidad al verde |
        | m² verde público/hab | m²/hab | OSM + Overpass | Verde realmente accesible |
        | Isla de calor (ΔT) | °C | Landsat 8/9 | Efecto térmico de la urbanización |
        | Enfriamiento potencial | °C | Landsat 8/9 NDVI | Ganancia posible con más arbolado |

        ---

        ### Sistema de calificación

        La calificación final (A-F) se calcula sobre 7 indicadores binarios:

        | Criterio | Condición para punto |
        |----------|---------------------|
        | Acceso universal | ≥ 95% de población a <300m |
        | m² OMS mínimo | ≥ 9 m²/hab (OSM) |
        | m² OMS óptimo | ≥ 15 m²/hab (OSM) |
        | Arbolado mínimo | ≥ 5% de cobertura arbórea |
        | Arbolado bueno | ≥ 10% de cobertura arbórea |
        | UHI controlado | ΔT < 1.5°C |
        | Equidad espacial | CV < 40% |

        **Escala:** A (7/7) · B (6/7) · C (5/7) · D (4/7) · F (<4/7)

        ---

        ### Referencias normativas

        - **OMS:** 9-15 m²/hab de verde público por habitante
        - **UE:** Green Infrastructure Strategy — 300m como distancia máxima aceptable
        - **FAO:** 10% de cobertura arbórea como mínimo urbano recomendado
        - **Argentina:** No existe estándar nacional específico — se aplican estándares OMS
        """)


def ayuda_diagnostico():
    with st.expander("ℹ️ Sobre el diagnóstico y las recomendaciones"):
        st.markdown("""
        ### Metodología del diagnóstico

        El diagnóstico integra los resultados de los cinco módulos de análisis para 
        generar una evaluación cualitativa estructurada en fortalezas y debilidades, 
        priorizando las intervenciones según su impacto potencial y urgencia.

        ---

        ### Priorización de recomendaciones

        Las recomendaciones se clasifican en tres niveles:

        | Nivel | Criterio | Plazo sugerido |
        |-------|----------|----------------|
        | 🔴 Urgente | Déficit crítico o riesgo ambiental alto | 0-2 años |
        | 🟡 Alta prioridad | Mejora significativa posible con recursos moderados | 2-5 años |
        | 🟢 Mejora continua | Optimización de lo existente | 5+ años |

        ---

        ### Marco normativo de referencia

        - **OMS (2016).** *Urban green spaces and health.* WHO/EURO.
        - **ODS 11.7** (ONU): acceso universal a espacios públicos seguros e inclusivos, 
          en particular para mujeres, niños, personas mayores y personas con discapacidad.
        - **FAO (2016).** *Guidelines on urban and peri-urban forestry.* FAO Forestry Paper 178.
        - **Ley 27.592** (Argentina, 2020): Ley Yolanda — formación ambiental integral.
        - **Código Ambiental de la Provincia de Córdoba** — Ley 10.208/2014.

        ---

        ### Limitaciones generales del sistema

        1. **Escala temporal:** los datos satelitales de cobertura corresponden a 2020 
           (WorldCover) y 2023-2024 (Landsat LST). Cambios recientes no están reflejados.
        2. **Escala espacial:** resolución mínima de 10m (WorldCover) — espacios verdes 
           muy pequeños (<100 m²) pueden no ser detectados.
        3. **Calidad del verde:** el sistema mide cantidad y accesibilidad, no calidad 
           (equipamiento, biodiversidad, mantenimiento, seguridad percibida).
        4. **Validación en campo:** los resultados satelitales requieren validación 
           con datos catastrales municipales para confirmar régimen de propiedad.
        5. **OSM incompleto:** la base OSM de ciudades intermedias puede tener espacios 
           verdes no catalogados, subestimando el verde público real.

        ---

        ### Sobre GreenCity

        GreenCity AI Agent es un sistema de análisis geoespacial desarrollado con 
        tecnologías de código abierto y datos públicos. No reemplaza estudios de campo 
        ni planes urbanos formales, sino que provee una **línea de base cuantitativa** 
        para orientar decisiones de planificación ambiental urbana basadas en evidencia.

        **Versión:** MVP 2025  
        **Tecnología:** Python · Google Earth Engine · Streamlit · OpenStreetMap  
        **Contacto técnico:** disponible bajo solicitud
        """)
