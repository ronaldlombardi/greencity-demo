# 🌿 GreenCity AI Agent

Diagnóstico inteligente de espacios verdes urbanos usando imágenes satelitales e inteligencia artificial.

## 📍 Ciudades analizadas

- **Villa María - Villa Nueva** (Córdoba, Argentina) — 120.000 hab
- **San Francisco** (Córdoba, Argentina) — 62.000 hab

## 📊 Módulos de análisis

| Módulo | Fuente | Qué mide |
|--------|--------|----------|
| Cobertura del suelo | ESA WorldCover 2020 | % árboles, edificado, cultivos |
| Accesibilidad | GEE + WorldCover | % población a <300m de verde |
| Temperatura (LST) | Landsat 8/9 (USGS) | Isla de calor urbano |
| Verde público | OpenStreetMap | m²/hab accesibles realmente |
| Censo 2022 | INDEC | Vulnerabilidad ambiental |

## 🛠️ Stack tecnológico

- Google Earth Engine API
- ESA WorldCover 2020 · Landsat 8/9 · Sentinel-2
- OpenStreetMap (API Overpass)
- INDEC Censo 2022
- Python · Streamlit · Folium · Shapely

---

## 🚀 Deploy en Railway

### 1. Subir a GitHub

```bash
git init
git add .
git commit -m "GreenCity AI Agent v1"
git remote add origin https://github.com/TU_USUARIO/greencity.git
git push -u origin main
```

> ⚠️ El `.gitignore` ya excluye `service_account.json`. Verificá que NO esté en el commit.

### 2. Crear proyecto en Railway

1. Ir a [railway.app](https://railway.app) → **New Project**
2. Seleccionar **Deploy from GitHub repo**
3. Elegir el repositorio `greencity`
4. Railway detecta automáticamente el `railway.json` y arranca el build

### 3. Configurar la variable de entorno GEE (CRÍTICO)

Las credenciales de Google Earth Engine **no se suben a GitHub**. Se configuran como variable de entorno en Railway:

1. En Railway → tu proyecto → **Variables**
2. Agregar nueva variable:
   - **Name:** `GEE_SERVICE_ACCOUNT_JSON`
   - **Value:** el contenido completo de tu `service_account.json` (todo el JSON en una sola línea)

Para convertir el JSON a una sola línea, correr en la carpeta del proyecto:
```bash
python -c "import json; print(json.dumps(json.load(open('service_account.json'))))"
```
Copiar esa salida y pegarla como valor de la variable en Railway.

### 4. Generar dominio público

En Railway → tu proyecto → **Settings** → **Networking** → **Generate Domain**

Obtenés una URL como: `greencity.up.railway.app`

---

## ▶️ Correr localmente

```bash
# Instalar dependencias
pip install -r requirements.txt

# Correr
python -m streamlit run app.py
```

Requiere `service_account.json` en la carpeta del proyecto.

---

## 📁 Estructura del proyecto

```
greencity/
├── app.py                    # App principal (multi-ciudad)
├── modulo_temperatura.py     # LST — Landsat 8/9
├── modulo_osm.py             # Verde público — OpenStreetMap
├── modulo_censo.py           # Análisis — INDEC Censo 2022
├── datos_ciudades.json       # Configuración base de ciudades
├── requirements.txt          # Dependencias Python
├── railway.json              # Configuración de deploy
├── README.md                 # Este archivo
├── .gitignore                # Excluye credenciales
│
├── # Scripts de análisis (correr localmente):
├── paso8_temperatura.py      # Calcula LST desde GEE
├── paso9_osm_verde_publico.py# Descarga datos OSM
├── paso10_censo2022.py       # Análisis censal por grilla
│
└── # NO subir a GitHub:
    ├── service_account.json  # Credenciales GEE (en .gitignore)
    └── client_secret.json    # Credenciales OAuth (en .gitignore)
```

---

## 📖 Fuentes de datos

- [ESA WorldCover 2020](https://esa-worldcover.org/) — cobertura del suelo 10m
- [Landsat 8/9 C2L2](https://www.usgs.gov/landsat-missions) — temperatura superficial
- [OpenStreetMap](https://www.openstreetmap.org/) — espacios verdes públicos
- [INDEC Censo 2022](https://censo.gob.ar/) — demografía y condiciones habitacionales
- [Google Earth Engine](https://earthengine.google.com/) — procesamiento en nube

---

*GreenCity AI Agent · MVP 2025 · Córdoba, Argentina*
