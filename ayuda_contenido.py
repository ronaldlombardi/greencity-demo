"""
ayuda_contenido.py — Ciudad Verde AI Agent
==========================================
Base de conocimiento del panel de Ayuda.
Organizada por categorías y términos.
Sin dependencia de modelos de IA.
"""

# Cada entrada: { "titulo", "categoria", "tags", "texto" }
# tags: palabras clave para el buscador (minúsculas)

AYUDA = [

    # ══════════════════════════════════════════════════════════
    # 🛰️ FUENTES DE DATOS
    # ══════════════════════════════════════════════════════════

    {
        "titulo": "ESA WorldCover 2020",
        "categoria": "🛰️ Fuentes de datos",
        "tags": ["worldcover", "esa", "cobertura", "satelite", "sentinel", "10m", "clasificacion"],
        "texto": (
            "Mapa global de cobertura del suelo producido por la Agencia Espacial Europea (ESA) "
            "a partir de imágenes Sentinel-1 (radar) y Sentinel-2 (óptico). Resolución de 10 metros "
            "por pixel — cada pixel representa 100 m² de superficie.\n\n"
            "Clasifica el territorio en 11 categorías: árboles, arbustos, pastizales, cultivos, "
            "edificado, suelo desnudo, nieve, agua, humedales, manglares y musgos.\n\n"
            "Ciudad Verde usa la versión 2020 (v100), disponible en Google Earth Engine. "
            "Corresponde al año 2020: cambios posteriores no están reflejados."
        ),
    },
    {
        "titulo": "Landsat 8 y Landsat 9",
        "categoria": "🛰️ Fuentes de datos",
        "tags": ["landsat", "nasa", "usgs", "temperatura", "termal", "tirs", "satelite", "infrarrojo"],
        "texto": (
            "Satélites de observación de la Tierra operados por NASA y USGS. "
            "Landsat 8 fue lanzado en 2013 y Landsat 9 en 2021. Tienen una resolución de 30 metros "
            "y pasan sobre el mismo punto cada 16 días; combinados, cada 8 días.\n\n"
            "Ciudad Verde usa su banda térmica (TIRS) para calcular la temperatura superficial (LST) "
            "y las bandas ópticas para calcular el índice de vegetación NDVI.\n\n"
            "Se usan imágenes de verano austral (diciembre-febrero) con nubosidad menor al 20%, "
            "y se calcula la mediana de múltiples imágenes para mayor robustez."
        ),
    },
    {
        "titulo": "Google Earth Engine (GEE)",
        "categoria": "🛰️ Fuentes de datos",
        "tags": ["gee", "google earth engine", "nube", "procesamiento", "satelital"],
        "texto": (
            "Plataforma de análisis geoespacial en la nube de Google que permite procesar "
            "petabytes de imágenes satelitales sin descargarlas. Ciudad Verde la usa para "
            "calcular la cobertura del suelo (WorldCover), la temperatura superficial (Landsat), "
            "la accesibilidad al verde y el índice NDVI.\n\n"
            "Todos los cálculos se ejecutan en los servidores de Google; la app solo recibe "
            "los resultados numéricos ya procesados."
        ),
    },
    {
        "titulo": "OpenStreetMap (OSM)",
        "categoria": "🛰️ Fuentes de datos",
        "tags": ["osm", "openstreetmap", "overpass", "mapa colaborativo", "verde publico", "plaza", "parque"],
        "texto": (
            "Base de datos geográfica colaborativa y de acceso libre, construida por voluntarios "
            "de todo el mundo. Ciudad Verde la consulta a través de la API Overpass para obtener "
            "los espacios verdes públicos de cada ciudad: parques, plazas, jardines, canchas, "
            "bosques urbanos y cementerios.\n\n"
            "A diferencia del satélite, OSM solo incluye espacios catalogados como de uso público "
            "o semipúblico. Por eso el m²/hab de OSM es siempre menor al satelital: "
            "la diferencia representa verde físicamente presente pero no accesible."
        ),
    },
    {
        "titulo": "INDEC — Censo Nacional 2022",
        "categoria": "🛰️ Fuentes de datos",
        "tags": ["indec", "censo", "2022", "poblacion", "vivienda", "hogares", "estadistica"],
        "texto": (
            "Censo Nacional de Población, Hogares y Viviendas realizado el 18 de mayo de 2022 "
            "por el Instituto Nacional de Estadística y Censos (INDEC). "
            "Publicación definitiva en enero 2024.\n\n"
            "Ciudad Verde usa los datos del Censo 2022 para: población total por ciudad, "
            "estructura etaria, condiciones habitacionales (piso, agua, saneamiento, hacinamiento) "
            "y cálculo del Índice de Vulnerabilidad Ambiental (IVA).\n\n"
            "Los datos están disponibles a nivel departamental. Los microdatos por radio censal "
            "(REDATAM) estarán disponibles próximamente en https://redatam.indec.gob.ar"
        ),
    },

    # ══════════════════════════════════════════════════════════
    # 🌾 COBERTURA DEL SUELO
    # ══════════════════════════════════════════════════════════

    {
        "titulo": "Cobertura del suelo",
        "categoria": "🌾 Cobertura del suelo",
        "tags": ["cobertura", "suelo", "clasificacion", "worldcover", "uso del suelo"],
        "texto": (
            "Clasificación de la superficie terrestre en categorías según el tipo de material "
            "o uso que ocupa cada pixel satelital. Ciudad Verde usa ESA WorldCover 2020 (10m) "
            "para clasificar cada ciudad en: árboles, pastizales, cultivos, edificado y agua.\n\n"
            "El porcentaje de cada clase se calcula sobre el área total analizada del municipio. "
            "Es la base de todos los demás indicadores: accesibilidad, temperatura y CO₂."
        ),
    },
    {
        "titulo": "Arbolado urbano",
        "categoria": "🌾 Cobertura del suelo",
        "tags": ["arbolado", "arboles", "tree cover", "forestacion", "cobertura arborea", "clase 10"],
        "texto": (
            "Porcentaje de la superficie cubierta por árboles (clase 10 de WorldCover). "
            "Incluye arbolado de calle, parques arbolados, jardines privados con árboles "
            "y vegetación leñosa de más de 5 metros de altura.\n\n"
            "Umbrales de referencia:\n"
            "• FAO: mínimo 10% recomendado para ciudades\n"
            "• Ciudad Verde: ≥10% = bueno | ≥5% = mínimo | <5% = crítico\n\n"
            "Villa María: 8.2% — por debajo del óptimo FAO pero sobre el mínimo.\n"
            "San Francisco: 1.6% — nivel crítico, principal debilidad ambiental."
        ),
    },
    {
        "titulo": "Pastizales urbanos",
        "categoria": "🌾 Cobertura del suelo",
        "tags": ["pastizal", "grassland", "pasto", "clase 30", "verde", "cesped"],
        "texto": (
            "Superficies cubiertas por vegetación herbácea baja: césped, pasto, "
            "praderas y terrenos sin edificar con cobertura vegetal (clase 30 de WorldCover).\n\n"
            "Contribuyen al verde total y a la accesibilidad, aunque su efecto enfriador "
            "y de captura de CO₂ es menor que el arbolado. En Villa María representan el 14.2%."
        ),
    },
    {
        "titulo": "Cultivos urbanos",
        "categoria": "🌾 Cobertura del suelo",
        "tags": ["cultivos", "cropland", "agricultura", "periurbano", "clase 40"],
        "texto": (
            "Tierras con uso agrícola dentro o en el periurbano de la ciudad (clase 40 de WorldCover). "
            "En ciudades de la llanura pampeana como Villa María y San Francisco, esta clase "
            "es muy significativa (23.9% y 24.3% respectivamente).\n\n"
            "Representan una oportunidad de reconversión: son suelos no edificados que podrían "
            "transformarse en verde público o corredores ecológicos en el largo plazo.\n\n"
            "La Ordenanza 7209/2017 de Villa María ('Ruralidad Urbana') reconoce y regula "
            "estos espacios periurbanos."
        ),
    },
    {
        "titulo": "Suelo edificado",
        "categoria": "🌾 Cobertura del suelo",
        "tags": ["edificado", "built-up", "urbano", "asfalto", "construccion", "clase 50"],
        "texto": (
            "Superficie cubierta por construcciones, pavimento, asfalto, techos y otras "
            "estructuras impermeables (clase 50 de WorldCover).\n\n"
            "Es la categoría dominante en ciudades: Villa María 50.6%, San Francisco 56.8%. "
            "Correlaciona directamente con el efecto de isla de calor: a mayor superficie "
            "edificada, mayor temperatura superficial."
        ),
    },

    # ══════════════════════════════════════════════════════════
    # 📏 ACCESIBILIDAD
    # ══════════════════════════════════════════════════════════

    {
        "titulo": "Accesibilidad al verde (<300 m)",
        "categoria": "📏 Accesibilidad",
        "tags": ["accesibilidad", "300m", "oms", "distancia", "acceso", "verde cercano"],
        "texto": (
            "Porcentaje de la superficie edificada (donde vive la gente) que tiene algún "
            "espacio verde a menos de 300 metros en línea recta.\n\n"
            "El estándar de 300 metros es el criterio de la Organización Mundial de la Salud (OMS): "
            "toda la población urbana debería poder llegar a pie a un espacio verde en menos "
            "de 4 minutos caminando.\n\n"
            "Tanto Villa María como San Francisco alcanzan el 100% — valor máximo posible, "
            "posible gracias a la presencia de pastizales y cultivos periurbanos."
        ),
    },
    {
        "titulo": "Distance Transform (algoritmo)",
        "categoria": "📏 Accesibilidad",
        "tags": ["distance transform", "distancia euclidiana", "algoritmo", "gee", "calculo"],
        "texto": (
            "Algoritmo matemático que calcula, para cada pixel del área edificada, "
            "la distancia en línea recta al pixel de zona verde más cercano.\n\n"
            "Ciudad Verde usa el operador fastDistanceTransform de Google Earth Engine, "
            "que procesa la imagen WorldCover pixel a pixel (10m de resolución).\n\n"
            "Limitación importante: la distancia es euclidiana (línea recta), no la distancia "
            "real por calles. La distancia real puede ser 20-40% mayor si hay barreras "
            "físicas como vías de tren, autopistas o ríos."
        ),
    },
    {
        "titulo": "m² de verde por habitante (satelital)",
        "categoria": "📏 Accesibilidad",
        "tags": ["m2", "metro cuadrado", "habitante", "verde por hab", "satelital", "densidad"],
        "texto": (
            "Total de pixels verdes (árboles + pastizales + agua) multiplicado por 100 m² "
            "(área de cada pixel) dividido por la población total del municipio.\n\n"
            "Este indicador satelital incluye todo el verde visible desde el satélite: "
            "patios privados, baldíos, cultivos y verde público. Por eso es siempre mayor "
            "que el m²/hab de OSM.\n\n"
            "Villa María: 93.2 m²/hab satelital vs 65.4 m²/hab OSM público.\n"
            "La diferencia (27.8 m²/hab ≈ 270 ha) es verde no accesible a los vecinos."
        ),
    },
    {
        "titulo": "Distancia promedio al verde",
        "categoria": "📏 Accesibilidad",
        "tags": ["distancia promedio", "metros", "verde cercano", "proximidad"],
        "texto": (
            "Media de la distancia euclidiana desde cada pixel edificado hasta el pixel "
            "de zona verde más cercano. Complementa el indicador de '% a menos de 300m'.\n\n"
            "Villa María: 48 metros promedio — equivale a cruzar media manzana.\n"
            "Distribución: 91.1% a menos de 100m | 8.9% entre 100 y 300m.\n\n"
            "Un valor bajo indica que el verde está bien distribuido por toda la ciudad, "
            "no concentrado en un solo sector."
        ),
    },
    {
        "titulo": "Equidad espacial",
        "categoria": "📏 Accesibilidad",
        "tags": ["equidad", "distribucion", "coeficiente de variacion", "cv", "desigualdad"],
        "texto": (
            "Mide si el acceso al verde está distribuido uniformemente entre todos los sectores "
            "de la ciudad o si hay zonas con mucho menos acceso que otras.\n\n"
            "Se calcula con el Coeficiente de Variación (CV) de la distancia al verde:\n"
            "• CV < 30%: alta equidad\n"
            "• CV 30-60%: equidad media\n"
            "• CV > 60%: baja equidad — zonas con acceso muy desigual\n\n"
            "Para que Ciudad Verde otorgue el punto de equidad, el CV debe ser menor al 40%."
        ),
    },

    # ══════════════════════════════════════════════════════════
    # 🌡️ TEMPERATURA SUPERFICIAL
    # ══════════════════════════════════════════════════════════

    {
        "titulo": "LST — Temperatura Superficial",
        "categoria": "🌡️ Temperatura superficial",
        "tags": ["lst", "temperatura superficial", "land surface temperature", "landsat", "termal"],
        "texto": (
            "Land Surface Temperature (LST): temperatura radiante de la superficie terrestre "
            "medida por el sensor térmico de Landsat (banda B10, infrarrojo térmico).\n\n"
            "Importante: NO es la temperatura del aire que mide un termómetro común. "
            "Es la temperatura del material en la superficie (asfalto, pasto, techo, agua). "
            "En verano cordobés, el asfalto puede tener 55-65°C de LST mientras el aire está a 35-40°C.\n\n"
            "Lo analíticamente relevante no es el valor absoluto sino las diferencias relativas "
            "entre coberturas: zona verde vs zona edificada."
        ),
    },
    {
        "titulo": "NDVI — Índice de Vegetación",
        "categoria": "🌡️ Temperatura superficial",
        "tags": ["ndvi", "indice vegetacion", "verde", "infrarrojo", "banda", "salud vegetal"],
        "texto": (
            "Normalized Difference Vegetation Index: índice que mide la salud y densidad "
            "de la vegetación a partir de la diferencia entre la banda infrarroja cercana (NIR) "
            "y la banda roja (RED) de Landsat.\n\n"
            "Fórmula: NDVI = (NIR - RED) / (NIR + RED)\n\n"
            "Valores:\n"
            "• NDVI > 0.4: vegetación densa y saludable\n"
            "• NDVI 0.2-0.4: vegetación moderada\n"
            "• NDVI < 0.2: suelo desnudo, asfalto, edificios\n\n"
            "Ciudad Verde usa el NDVI para calcular la emisividad de la superficie y comparar "
            "la temperatura de zonas verdes densas vs zonas de asfalto."
        ),
    },
    {
        "titulo": "Isla de calor urbano (UHI / ΔT)",
        "categoria": "🌡️ Temperatura superficial",
        "tags": ["isla de calor", "uhi", "delta t", "temperatura", "urbano", "calor"],
        "texto": (
            "Urban Heat Island (UHI): fenómeno por el cual las ciudades son más calientes "
            "que las áreas rurales o verdes circundantes, debido a la abundancia de superficies "
            "impermeables (asfalto, concreto) que absorben y retienen calor solar.\n\n"
            "Ciudad Verde mide el ΔT UHI como la diferencia de temperatura entre zonas "
            "edificadas y zonas verdes dentro del área analizada:\n\n"
            "• ΔT < 1.5°C: efecto bajo — vegetación regula adecuadamente\n"
            "• ΔT 1.5-3°C: moderado — intervención recomendada\n"
            "• ΔT > 3°C: alto — intervención urgente\n\n"
            "Villa María: ΔT = +0.17°C — excelente (muy baja isla de calor).\n"
            "San Francisco: ΔT = +1.01°C — moderado, requiere atención."
        ),
    },
    {
        "titulo": "Enfriamiento potencial por arbolado",
        "categoria": "🌡️ Temperatura superficial",
        "tags": ["enfriamiento", "arbolado", "temperatura", "grados", "efecto verde", "ndvi"],
        "texto": (
            "Diferencia de temperatura entre las zonas con NDVI bajo (suelo/asfalto, NDVI < 0.2) "
            "y las zonas con NDVI alto (vegetación densa, NDVI > 0.4).\n\n"
            "Cuantifica cuántos grados más fresca está la vegetación densa respecto al asfalto. "
            "Indica el potencial de reducción de temperatura si se incrementa el arbolado.\n\n"
            "Villa María: 1.67°C de diferencia (ya tiene bastante verde).\n"
            "San Francisco: 3.95°C — alto potencial, la forestación tendría mayor impacto."
        ),
    },
    {
        "titulo": "P95 y P5 de temperatura",
        "categoria": "🌡️ Temperatura superficial",
        "tags": ["p95", "p5", "percentil", "temperatura maxima", "temperatura minima", "extremos"],
        "texto": (
            "Percentiles 95 y 5 de la distribución de temperatura superficial en el área analizada.\n\n"
            "• P95: temperatura que supera el 95% de los pixels — los puntos más calientes de la ciudad.\n"
            "• P5: temperatura del 5% más fresco — las zonas más frescas.\n\n"
            "Son útiles para identificar puntos de calor críticos (hotspots) donde intervenir "
            "con plantación de árboles o materiales reflectantes."
        ),
    },
    {
        "titulo": "Captura de CO₂ por arbolado urbano",
        "categoria": "🌡️ Temperatura superficial",
        "tags": ["co2", "carbono", "captura", "secuestro", "arboles", "clima", "nowak"],
        "texto": (
            "Cantidad de dióxido de carbono que el arbolado urbano absorbe por año mediante "
            "la fotosíntesis. Ciudad Verde usa la metodología del USDA Forest Service "
            "(Nowak et al., 2013), basada en datos de campo de 28 ciudades.\n\n"
            "Densidad de secuestro neto aplicada: 0.205 kg C/m²/año de cobertura arbórea.\n\n"
            "Villa María (8.2% arbolado):\n"
            "• CO₂ actual: ~556 toneladas/año ≈ 265 autos fuera de circulación\n"
            "• Con meta 15% arbolado: ~1.017 toneladas/año\n\n"
            "Esta métrica es reportable bajo el Acuerdo de París como sumidero de carbono urbano."
        ),
    },

    # ══════════════════════════════════════════════════════════
    # 🏛️ VERDE PÚBLICO (OSM)
    # ══════════════════════════════════════════════════════════

    {
        "titulo": "Verde público vs verde satelital",
        "categoria": "🏛️ Verde público (OSM)",
        "tags": ["verde publico", "satelital", "brecha", "accesible", "privado", "osm", "diferencia"],
        "texto": (
            "El satélite (WorldCover) detecta toda la vegetación del territorio, "
            "sin importar si es pública o privada: patios, baldíos, campos de golf, "
            "jardines empresariales y cultivos aparecen igual que una plaza.\n\n"
            "OSM solo incluye los espacios catalogados como de uso público o semipúblico.\n\n"
            "La diferencia entre ambos valores es el 'verde inaccesible': vegetación "
            "que existe pero que los vecinos no pueden usar.\n\n"
            "Villa María: 93.2 m²/hab (satelital) vs 65.4 m²/hab (OSM público) → "
            "27.8 m²/hab ≈ 270 ha de verde que los vecinos probablemente no pueden usar."
        ),
    },
    {
        "titulo": "Etiquetas OSM consultadas",
        "categoria": "🏛️ Verde público (OSM)",
        "tags": ["osm", "etiquetas", "tags", "parque", "plaza", "cancha", "leisure", "landuse"],
        "texto": (
            "Ciudad Verde consulta las siguientes categorías de espacios en OpenStreetMap:\n\n"
            "• Parques: leisure=park\n"
            "• Plazas y jardines: leisure=garden, place=square\n"
            "• Deportivo: leisure=pitch, leisure=sports_centre\n"
            "• Juegos infantiles: leisure=playground\n"
            "• Áreas verdes: landuse=grass, landuse=recreation_ground, landuse=meadow\n"
            "• Naturaleza: natural=wood, landuse=forest\n"
            "• Cementerios: landuse=cemetery (incluidos por su masa verde)\n\n"
            "Los espacios sin etiqueta o sin nombre en OSM no son capturados, "
            "lo que puede subestimar el verde público real en ciudades medianas."
        ),
    },
    {
        "titulo": "m² de verde público por habitante (OSM)",
        "categoria": "🏛️ Verde público (OSM)",
        "tags": ["m2", "metro cuadrado", "habitante", "osm", "publico", "oms", "estandar"],
        "texto": (
            "Superficie total de espacios verdes públicos catalogados en OSM dividida "
            "por la población total del municipio.\n\n"
            "Estándares OMS:\n"
            "• ≥ 15 m²/hab: umbral óptimo\n"
            "• 9-15 m²/hab: dentro del rango recomendado\n"
            "• < 9 m²/hab: por debajo del mínimo\n\n"
            "Villa María: 65.4 m²/hab — supera ampliamente el estándar OMS.\n"
            "San Francisco: 13.2 m²/hab — dentro del rango recomendado."
        ),
    },

    # ══════════════════════════════════════════════════════════
    # 👥 CENSO Y VULNERABILIDAD
    # ══════════════════════════════════════════════════════════

    {
        "titulo": "IVA — Índice de Vulnerabilidad Ambiental",
        "categoria": "👥 Censo y vulnerabilidad",
        "tags": ["iva", "vulnerabilidad", "ambiental", "indice", "censo", "privacion", "verde"],
        "texto": (
            "Indicador compuesto que combina condiciones habitacionales del Censo 2022 "
            "con el acceso al verde para identificar las zonas donde la falta de espacios "
            "verdes agrava condiciones de vulnerabilidad preexistentes.\n\n"
            "Puntaje (0-8):\n"
            "• Piso de tierra > 5%: +1\n"
            "• Sin agua de red > 10%: +1\n"
            "• Hacinamiento > 7%: +1\n"
            "• Acceso al verde < 90%: +2\n"
            "• Equidad espacial CV > 60%: +2\n"
            "• Población > 65 años > 18%: +1\n\n"
            "Clasificación: Bajo (0-1) · Medio (2-3) · Alto (4-8)\n\n"
            "Permite priorizar dónde invertir en verde con mayor impacto social."
        ),
    },
    {
        "titulo": "IPMH — Índice de Privación Material",
        "categoria": "👥 Censo y vulnerabilidad",
        "tags": ["ipmh", "privacion", "material", "hogares", "censo", "indec", "pobreza"],
        "texto": (
            "Índice de Privación Material de los Hogares del INDEC. "
            "Mide dos dimensiones de privación:\n\n"
            "• Patrimonial: viviendas con piso de tierra, sin agua de red dentro de la vivienda.\n"
            "• Recursos corrientes: hacinamiento (>3 personas por cuarto), sin saneamiento básico.\n\n"
            "Ciudad Verde lo usa como proxy de vulnerabilidad socioeconómica para cruzar "
            "con el acceso al verde y determinar el IVA."
        ),
    },
    {
        "titulo": "Análisis por grilla de 450m",
        "categoria": "👥 Censo y vulnerabilidad",
        "tags": ["grilla", "450m", "censo", "radio censal", "analisis espacial", "sector"],
        "texto": (
            "Dado que los microdatos del Censo 2022 por radio censal (REDATAM) aún no estaban "
            "disponibles al momento del análisis, Ciudad Verde divide el área urbana en celdas "
            "de aproximadamente 450x450 metros.\n\n"
            "Para cada celda se calcula:\n"
            "• Porcentaje de superficie edificada (proxy de densidad poblacional)\n"
            "• Distancia media al verde más cercano\n"
            "• Porcentaje con acceso a menos de 300m\n\n"
            "La población de cada celda se estima proporcionalmente al suelo edificado."
        ),
    },

    # ══════════════════════════════════════════════════════════
    # 🌍 MARCOS NORMATIVOS
    # ══════════════════════════════════════════════════════════

    {
        "titulo": "OMS — Estándares de verde urbano",
        "categoria": "🌍 Marcos normativos",
        "tags": ["oms", "who", "estandar", "9m2", "15m2", "300m", "salud", "verde publico"],
        "texto": (
            "La Organización Mundial de la Salud establece dos criterios principales "
            "para espacios verdes urbanos:\n\n"
            "1. Cantidad: entre 9 y 15 m² de verde público por habitante (mínimo 9 m²/hab).\n"
            "2. Proximidad: acceso a un espacio verde de al menos 0.5 ha dentro de 300 metros.\n\n"
            "Ambos criterios están integrados en el sistema de calificación A-F de Ciudad Verde. "
            "La evidencia científica asocia el acceso al verde con mejoras en salud mental, "
            "reducción de estrés, actividad física y calidad del aire."
        ),
    },
    {
        "titulo": "C40 — Urban Nature Declaration 2030",
        "categoria": "🌍 Marcos normativos",
        "tags": ["c40", "urban nature", "2030", "qtc", "esd", "30 porciento", "buenos aires"],
        "texto": (
            "Declaración de ciudades de la red C40 que establece dos targets para 2030:\n\n"
            "• QTC (Quality Tree Coverage): al menos 30% de la superficie total de la ciudad "
            "cubierta por verde y agua.\n"
            "• ESD (Equitable Spatial Distribution): al menos 70% de la población con acceso "
            "a verde o agua en 15 minutos a pie.\n\n"
            "Buenos Aires ya firmó la declaración. Villa María puede alinearse a este estándar, "
            "usado por Londres, París, Tokio, Copenhague y Medellín.\n\n"
            "Villa María: QTC actual 23.7% (faltan 6.3 pp para llegar al 30%) · ESD 100% ✅"
        ),
    },
    {
        "titulo": "ODS 11 — Ciudades Sostenibles",
        "categoria": "🌍 Marcos normativos",
        "tags": ["ods", "onu", "agenda 2030", "ciudades sostenibles", "meta 11.7", "inclusion"],
        "texto": (
            "Objetivo de Desarrollo Sostenible 11 de Naciones Unidas: 'Ciudades y comunidades "
            "sostenibles'. La meta 11.7 establece:\n\n"
            "'Para 2030, proporcionar acceso universal a zonas verdes y espacios públicos "
            "seguros, inclusivos y accesibles, en particular para mujeres y niños, "
            "personas de edad y personas con discapacidad.'\n\n"
            "El indicador de accesibilidad al verde de Ciudad Verde (<300m) es directamente "
            "comparable con la meta 11.7 de la Agenda 2030."
        ),
    },
    {
        "titulo": "Acuerdo de París — Sumideros urbanos",
        "categoria": "🌍 Marcos normativos",
        "tags": ["acuerdo de paris", "carbono", "co2", "sumidero", "ndc", "argentina", "clima"],
        "texto": (
            "El Acuerdo de París (2015) obliga a Argentina a reportar sus emisiones y "
            "sumideros de carbono en las Contribuciones Determinadas a Nivel Nacional (NDC).\n\n"
            "El arbolado urbano es un sumidero de carbono cuantificable y reportable. "
            "La captura de CO₂ calculada por Ciudad Verde (~556 ton/año en Villa María) "
            "usa la metodología del USDA Forest Service, reconocida internacionalmente "
            "para inventarios de carbono urbano."
        ),
    },
    {
        "titulo": "Ordenanza 7209 — Ruralidad Urbana (Villa María)",
        "categoria": "🌍 Marcos normativos",
        "tags": ["ordenanza", "7209", "villa maria", "ruralidad urbana", "periurbano", "2017"],
        "texto": (
            "Ordenanza Municipal 7209 de Villa María, sancionada en 2017. "
            "Reconoce los servicios ambientales del territorio periurbano: "
            "producción de alimentos, regulación hídrica, biodiversidad y calidad del aire.\n\n"
            "Establece mecanismos de gestión del territorio rural-urbano y protege "
            "los cinturones verdes periurbanos de la urbanización no planificada.\n\n"
            "Es el principal marco normativo local para cualquier política de expansión "
            "del verde urbano en Villa María."
        ),
    },
    {
        "titulo": "EU Nature Restoration Law — Art. 8",
        "categoria": "🌍 Marcos normativos",
        "tags": ["union europea", "restauracion", "ecosistemas", "urbano", "arbolado", "referencia"],
        "texto": (
            "Ley europea de Restauración de la Naturaleza (2024). El Artículo 8 establece "
            "metas de cobertura arbórea para ciudades de más de 20.000 habitantes "
            "y objetivos de reducción de superficies impermeables.\n\n"
            "Si bien no es de aplicación obligatoria en Argentina, es el estándar "
            "de primer nivel mundial para benchmarking internacional de ciudades verdes. "
            "Ciudad Verde lo usa como referencia comparativa."
        ),
    },

    # ══════════════════════════════════════════════════════════
    # 📊 CALIFICACIÓN Y COMPARATIVA
    # ══════════════════════════════════════════════════════════

    {
        "titulo": "Sistema de calificación A-F",
        "categoria": "📊 Calificación",
        "tags": ["calificacion", "a", "b", "c", "d", "f", "puntaje", "7 puntos", "criterios"],
        "texto": (
            "Ciudad Verde asigna una calificación de A a F basada en 7 criterios binarios "
            "(cada uno vale 1 punto):\n\n"
            "1. Acceso universal: ≥ 95% de la población a menos de 300m\n"
            "2. m² OMS mínimo: ≥ 9 m²/hab (OSM)\n"
            "3. m² OMS óptimo: ≥ 15 m²/hab (OSM)\n"
            "4. Arbolado mínimo: ≥ 5% de cobertura arbórea\n"
            "5. Arbolado bueno: ≥ 10% de cobertura arbórea\n"
            "6. UHI controlado: ΔT < 1.5°C\n"
            "7. Equidad espacial: CV < 40%\n\n"
            "Escala: A (7/7) · B (6/7) · C (5/7) · D (4/7) · F (<4/7)\n\n"
            "Villa María: A - Excelente (7/7) · San Francisco: B - Muy Bueno (6/7)"
        ),
    },
    {
        "titulo": "Brecha satelital vs público",
        "categoria": "📊 Calificación",
        "tags": ["brecha", "satelital", "publico", "osm", "diferencia", "inaccesible"],
        "texto": (
            "Diferencia entre el m²/hab medido por satélite (todo el verde) "
            "y el m²/hab de OSM (solo verde público).\n\n"
            "Cuantifica el verde físicamente presente en la ciudad pero "
            "no accesible para los vecinos: patios privados, campos deportivos cerrados, "
            "predios empresariales y baldíos con vegetación.\n\n"
            "Una brecha grande indica oportunidad de política pública: "
            "relevar esos espacios para evaluar cuáles podrían abrirse al público "
            "o incorporarse al sistema de plazas y parques."
        ),
    },

    # ══════════════════════════════════════════════════════════
    # 🏙️ VILLA MARÍA — CONCEPTOS ESPECÍFICOS
    # ══════════════════════════════════════════════════════════

    {
        "titulo": "Conglomerado Villa María – Villa Nueva",
        "categoria": "🏙️ Villa María",
        "tags": ["villa maria", "villa nueva", "conglomerado", "ctalamochita", "rio", "ecosistema"],
        "texto": (
            "Villa María (~97.000 hab) y Villa Nueva (~23.000 hab) forman un conglomerado "
            "urbano continuo dividido por el Río Ctalamochita. "
            "Total: ~120.000 habitantes en 49.6 km² analizados.\n\n"
            "Ciudad Verde las analiza como una única unidad ecosistémica porque comparten "
            "el corredor ambiental del río y la mancha verde del periurbano.\n\n"
            "Las estrategias y el Masterplan corresponden al Municipio de Villa María "
            "(la cabecera del Departamento General San Martín)."
        ),
    },
    {
        "titulo": "Río Ctalamochita — Corredor ecológico",
        "categoria": "🏙️ Villa María",
        "tags": ["ctalamochita", "rio", "corredor", "ecologico", "parque lineal", "ciclovias"],
        "texto": (
            "El Río Ctalamochita divide el conglomerado: Villa María al oeste y Villa Nueva al este. "
            "Representa el principal activo ambiental compartido del área.\n\n"
            "Potencial como corredor ecológico y recreativo:\n"
            "• ~8 km de frente ribereño aprovechable\n"
            "• Posibles ciclovías y senderos en ambas márgenes\n"
            "• Arbolado ribereño con especies nativas\n"
            "• Conexión continua entre los parques existentes de ambas ciudades\n\n"
            "El parque lineal del Ctalamochita es una de las líneas de acción prioritarias "
            "del Masterplan Ambiental."
        ),
    },
    {
        "titulo": "Zona Noroeste — Área prioritaria de intervención",
        "categoria": "🏙️ Villa María",
        "tags": ["noroeste", "zona", "caliente", "prioritaria", "temperatura", "acceso", "intervencion"],
        "texto": (
            "La zona Noroeste (VM centro-norte) es la de mayor temperatura superficial "
            "del conglomerado: 40.76°C, +0.79°C sobre la media.\n\n"
            "También presenta el menor acceso al verde del conglomerado: 88.3% "
            "(vs 100% en las zonas sur). Tiene 18.4 ha de superficie edificada.\n\n"
            "Es la zona prioritaria para intervención de forestación en Villa María: "
            "allí el arbolado tendría el mayor impacto en reducción de temperatura "
            "y en mejora de equidad de acceso al verde."
        ),
    },
    {
        "titulo": "Zonas de análisis del conglomerado",
        "categoria": "🏙️ Villa María",
        "tags": ["zonas", "noroeste", "noreste", "suroeste", "sureste", "cuadrantes", "analisis"],
        "texto": (
            "El área analizada se divide en 4 cuadrantes para el análisis de temperatura "
            "y accesibilidad:\n\n"
            "• Noroeste (VM centro-norte): 40.76°C | acceso 88.3% ⚠️ PRIORITARIA\n"
            "• Noreste (VN norte): 39.85°C | acceso 96.1%\n"
            "• Suroeste (VM sur): 39.73°C | acceso 100% ✅\n"
            "• Sureste (VN sur): 39.55°C | acceso 100% ✅\n\n"
            "La mayor diferencia de temperatura entre zonas es de 1.21°C "
            "(Noroeste vs Sureste), lo que indica una distribución térmica relativamente uniforme."
        ),
    },
    {
        "titulo": "Target QTC 2030 en Villa María",
        "categoria": "🏙️ Villa María",
        "tags": ["qtc", "c40", "30 porciento", "2030", "verde", "hectareas", "meta"],
        "texto": (
            "Para cumplir el target C40 de 30% de cobertura verde (QTC) al año 2030, "
            "Villa María necesita incorporar aproximadamente 227 hectáreas adicionales de verde.\n\n"
            "Ritmo necesario: 45.4 ha/año durante 5 años (2025-2030).\n"
            "Equivale a plantar ~1.816 árboles por año (copa media de 25 m²).\n\n"
            "El principal reservorio de suelo disponible son los cultivos urbanos (23.9%), "
            "que podrían reconvertirse parcialmente en verde público o corredores ecológicos "
            "dentro del marco de la Ordenanza 7209/2017."
        ),
    },

    # ══════════════════════════════════════════════════════════
    # ℹ️ SOBRE LA PLATAFORMA
    # ══════════════════════════════════════════════════════════

    {
        "titulo": "¿Qué es Ciudad Verde AI Agent?",
        "categoria": "ℹ️ Sobre la plataforma",
        "tags": ["ciudad verde", "plataforma", "que es", "sistema", "agente", "cordoba"],
        "texto": (
            "Ciudad Verde AI Agent es una plataforma de análisis geoespacial ambiental "
            "desarrollada para las ciudades capitales de departamento de la Provincia de Córdoba, Argentina.\n\n"
            "Integra datos satelitales (ESA WorldCover, Landsat 8/9), geográficos colaborativos "
            "(OpenStreetMap) y estadísticos (INDEC Censo 2022) para producir indicadores "
            "ambientales cuantitativos: cobertura verde, accesibilidad, temperatura superficial, "
            "captura de CO₂ y vulnerabilidad socioespacial.\n\n"
            "Tecnología: Python · Google Earth Engine · Streamlit · Folium · PostgreSQL.\n"
            "No reemplaza estudios de campo ni planes urbanos formales. "
            "Provee una línea de base cuantitativa para decisiones de política pública."
        ),
    },
    {
        "titulo": "Limitaciones del sistema",
        "categoria": "ℹ️ Sobre la plataforma",
        "tags": ["limitaciones", "precision", "errores", "campo", "validacion", "escala"],
        "texto": (
            "Ciudad Verde es una herramienta de análisis remoto con limitaciones conocidas:\n\n"
            "1. Escala temporal: WorldCover corresponde a 2020. Cambios recientes no se reflejan.\n"
            "2. Resolución: 10m mínimo — espacios verdes menores a 100 m² pueden no detectarse.\n"
            "3. Distancia euclidiana: la accesibilidad se mide en línea recta, no por calles. "
            "La distancia real puede ser 20-40% mayor.\n"
            "4. Calidad del verde: se mide cantidad y proximidad, no calidad "
            "(equipamiento, biodiversidad, seguridad percibida, mantenimiento).\n"
            "5. OSM incompleto: ciudades medianas pueden tener espacios sin catalogar.\n"
            "6. Validación: los resultados satelitales requieren confirmación con datos catastrales."
        ),
    },
    {
        "titulo": "Módulo Villa María vs Módulo Provincia",
        "categoria": "ℹ️ Sobre la plataforma",
        "tags": ["modulos", "villa maria", "provincia", "cordoba", "ciudades", "navegacion"],
        "texto": (
            "Ciudad Verde tiene dos módulos principales accesibles desde el menú lateral:\n\n"
            "• 🏙️ Villa María: análisis detallado del conglomerado Villa María – Villa Nueva. "
            "Incluye mapa interactivo, indicadores por zonas, diagnóstico, estrategias, "
            "Agenda 2030/C40 y generación de Masterplan (solo administradores).\n\n"
            "• 🌍 Provincia de Córdoba: análisis de las ciudades capitales de departamento "
            "con datos GEE disponibles. Permite comparar indicadores entre ciudades y "
            "navegar por cobertura, accesibilidad, temperatura, OSM, Censo y Diagnóstico.\n\n"
            "• 🔐 Administración: panel de consumo y gestión (solo administradores)."
        ),
    },
]

# ── Categorías en orden para el panel ──────────────────────
CATEGORIAS_ORDEN = [
    "🛰️ Fuentes de datos",
    "🌾 Cobertura del suelo",
    "📏 Accesibilidad",
    "🌡️ Temperatura superficial",
    "🏛️ Verde público (OSM)",
    "👥 Censo y vulnerabilidad",
    "🌍 Marcos normativos",
    "📊 Calificación",
    "🏙️ Villa María",
    "ℹ️ Sobre la plataforma",
]


def buscar(query: str) -> list:
    """Filtra entradas por texto libre en título, tags y texto."""
    if not query or not query.strip():
        return []
    q = query.strip().lower()
    resultados = []
    for entrada in AYUDA:
        if (
            q in entrada["titulo"].lower()
            or q in entrada["texto"].lower()
            or any(q in tag for tag in entrada["tags"])
        ):
            resultados.append(entrada)
    return resultados


def por_categoria(categoria: str) -> list:
    """Devuelve todas las entradas de una categoría."""
    return [e for e in AYUDA if e["categoria"] == categoria]
