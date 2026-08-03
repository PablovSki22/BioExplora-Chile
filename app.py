import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import st_folium
import requests
import hashlib
import io
import uuid
from PIL import Image, ImageOps, UnidentifiedImageError
from PIL.ExifTags import TAGS, GPSTAGS
from supabase import create_client, Client
import gc

gc.collect()

icono_app = Image.open("favicon_512.png")

st.set_page_config(
    page_title="BioExplora Chile",
    page_icon=icono_app,
    layout="wide"
)
# --- CONEXIÓN CON SUPABASE ---
@st.cache_resource
def obtener_cliente_supabase() -> Client:
    try:
        supabase_url = st.secrets["supabase"]["url"]
        supabase_key = st.secrets["supabase"]["key"]

        return create_client(
            supabase_url,
            supabase_key
        )

    except KeyError as error:
        st.error(
            f"Falta una configuración de Supabase "
            f"en los Secrets privados: {error}"
        )
        st.stop()

    except Exception as error:
        st.error(
            f"No fue posible conectar con Supabase: {error}"
        )
        st.stop()


supabase = obtener_cliente_supabase()
# --- VERIFICACIÓN DE CONEXIÓN CON SUPABASE ---
try:
    prueba_supabase = (
        supabase
        .table("avistamientos")
        .select("id")
        .limit(1)
        .execute()
    )

    conexion_supabase_activa = True

except Exception as error:
    conexion_supabase_activa = False
    st.error(
        f"No fue posible consultar la tabla de avistamientos: {error}"
    )
    st.stop()
# --- ESTILOS CSS PERSONALIZADOS ---
st.markdown("""
<style>
    .stApp {
        background-color: #0b132b;
        color: #e2e8f0;
    }
    p, span, label, div {
        color: #cbd5e1;
    }
    h1, h2, h3, h4, h5, h6 {
        color: #f8fafc !important;
    }
    div.stMarkdown, div.stForm, div.stTabs {
        background-color: #1c2541;
        border-radius: 12px;
        padding: 5px;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #0b132b;
        padding: 10px;
        border-radius: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #1c2541;
        border-radius: 8px;
        color: #94a3b8;
        font-weight: 600;
        border: 1px solid #3a506b;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
        color: white !important;
        border: none !important;
    }
    div.stButton > button {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 600;
        box-shadow: 0 4px 6px -1px rgba(16, 185, 129, 0.3);
        transition: all 0.3s ease;
    }
    div.stButton > button:hover {
        background: linear-gradient(135deg, #059669 0%, #047857 100%);
        transform: translateY(-2px);
    }
    div[data-testid="stMetric"] {
        background-color: #1c2541;
        padding: 16px;
        border-radius: 12px;
        border: 1px solid #3a506b;
    }
    div[data-testid="stMetric"] label {
        color: #94a3b8 !important;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #38bdf8 !important;
        font-weight: 700;
    }
    div.stAlert {
        background-color: #1c2541;
        border: 1px solid #3a506b;
        border-radius: 10px;
        color: #e2e8f0;
    }
    div.stTextInput > div > div > input, div.stSelectbox > div > div > div, div.stTextArea > div > div > textarea {
        background-color: #0b132b;
        color: #f8fafc;
        border-radius: 8px;
        border: 1px solid #3a506b;
    }
    section[data-testid="stSidebar"] {
        background-color: #0b132b;
        border-right: 1px solid #1c2541;
    }
</style>
""", unsafe_allow_html=True)

# --- INICIALIZACIÓN DE ESTADOS DE SESIÓN ---
if "bd_usuarios" not in st.session_state:
    st.session_state.bd_usuarios = {
        "admin@bioexplora.cl": hashlib.sha256("123456".encode()).hexdigest()
    }

if "perfiles_usuarios" not in st.session_state:
    st.session_state.perfiles_usuarios = {
        "admin@bioexplora.cl": {
            "nombre": "Administrador",
            "bio": "Gestor oficial del portal BioExplora Chile.",
            "edad": 35,
            "genero": "No especificado",
            "instagram": "bioexplora_cl",
            "facebook": "",
            "avatar": None
        }
    }
if "conteo_avistamientos" not in st.session_state:
    st.session_state.conteo_avistamientos = {
        "admin@bioexplora.cl": 12
    }

if "df_pendientes_revision" not in st.session_state:
    st.session_state.df_pendientes_revision = pd.DataFrame(columns=['Region', 'Comuna', 'NombreComun', 'TipoEvento', 'Latitud', 'Longitud', 'AportadoPor', 'Notas', 'Estado'])

if "df_nuevos_registros" not in st.session_state:
    st.session_state.df_nuevos_registros = pd.DataFrame(columns=['Region', 'Comuna', 'NombreComun', 'TipoEvento', 'Latitud', 'Longitud', 'AportadoPor'])

if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if "usuario_actual" not in st.session_state:
    st.session_state.usuario_actual = None

if "tipo_acceso" not in st.session_state:
    st.session_state.tipo_acceso = None

if "acceso_google" not in st.session_state:
    st.session_state.acceso_google = False

# Procesar una sesión iniciada mediante Google OIDC.
if st.user.is_logged_in:
    google_email = getattr(st.user, "email", None)

    if google_email:
        google_nombre = getattr(
            st.user,
            "name",
            google_email.split("@")[0].title()
        )
        google_avatar = getattr(st.user, "picture", None)

        st.session_state.autenticado = True
        st.session_state.usuario_actual = google_email
        st.session_state.tipo_acceso = "Registrado"
        st.session_state.acceso_google = True

        if google_email not in st.session_state.conteo_avistamientos:
            st.session_state.conteo_avistamientos[google_email] = 0

        if google_email not in st.session_state.perfiles_usuarios:
            st.session_state.perfiles_usuarios[google_email] = {
                "nombre": google_nombre,
                "bio": "Entusiasta de la biodiversidad chilena.",
                "edad": "",
                "genero": "Prefiero no decirlo",
                "instagram": "",
                "facebook": "",
                "avatar": google_avatar
            }

def hash_pass(password):
    return hashlib.sha256(password.encode()).hexdigest()

def obtener_rango_usuario(cantidad):
    if cantidad >= 11:
        return "🏆 Naturalista Experto", "gold"
    elif cantidad >= 6:
        return "🌿 Rastreador de Biodiversidad", "green"
    elif cantidad >= 3:
        return "🥾 Explorador de Campo", "blue"
    else:
        return "🐣 Observador Inicial", "gray"

def obtener_coordenadas_exif(image_file):
    try:
        image = Image.open(image_file)
        exif_data = image._getexif()
        if not exif_data:
            return None, None
        gps_info = {}
        for tag_id, value in exif_data.items():
            tag = TAGS.get(tag_id, tag_id)
            if tag == "GPSInfo":
                for t in value:
                    sub_tag = GPSTAGS.get(t, t)
                    gps_info[sub_tag] = value[t]
        if not gps_info:
            return None, None

        def convertir_a_grados(valor_gps):
            d = float(valor_gps[0])
            m = float(valor_gps[1])
            s = float(valor_gps[2])
            return d + (m / 60.0) + (s / 3600.0)

        lat = convertir_a_grados(gps_info['GPSLatitude'])
        if gps_info.get('GPSLatitudeRef') != 'N':
            lat = -lat
        lon = convertir_a_grados(gps_info['GPSLongitude'])
        if gps_info.get('GPSLongitudeRef') != 'E':
            lon = -lon
        return lat, lon
    except Exception:
        return None, None

COORDENADAS_COMUNAS = {
    "Arica": (-18.4783, -70.3126), "Iquique": (-20.2133, -70.1503), "Antofagasta": (-23.6509, -70.3975),
    "Calama": (-22.4544, -68.9294), "Copiapó": (-27.3668, -70.3323), "Vallenar": (-28.5751, -70.7581),
    "La Serena": (-29.9027, -71.2520), "Coquimbo": (-29.9533, -71.3436), "Ovalle": (-30.5983, -71.2003),
    "Valparaíso": (-33.0472, -71.6127), "Viña Del Mar": (-33.0245, -71.5518), "Quillota": (-32.8739, -71.2486),
    "San Antonio": (-33.5938, -71.6076), "Santiago": (-33.4489, -70.6693), "Puente Alto": (-33.6117, -70.5758),
    "Maipú": (-33.5112, -70.7580), "Melipilla": (-33.6853, -71.2144), "Rancagua": (-34.1701, -70.7444),
    "San Fernando": (-34.5839, -70.9888), "Curicó": (-34.9828, -71.2394), "Talca": (-35.4264, -71.6554),
    "Linares": (-35.8454, -71.5979), "Cauquenes": (-35.9670, -72.3158), "Chillán": (-36.6063, -72.1023),
    "San Carlos": (-36.4242, -71.9581), "Concepción": (-36.8270, -73.0503), "Hualpén": (-36.7925, -73.1118),
    "Hualpen": (-36.7925, -73.1118), "Talcahuano": (-36.7167, -73.1167), "San Pedro De La Paz": (-36.8406, -73.1022),
    "Los Ángeles": (-37.4697, -72.3537), "Temuco": (-38.7359, -72.5904), "Villarrica": (-39.2822, -72.2272),
    "Angol": (-37.7944, -72.7164), "Valdivia": (-39.8142, -73.2459), "Osorno": (-40.5739, -73.1336),
    "San Pablo": (-40.4042, -73.0308), "Puerto Montt": (-41.4689, -72.9411), "Puerto Varas": (-41.3195, -72.9854),
    "Castro": (-42.4721, -73.7732), "Ancud": (-41.8686, -73.8267), "Coyhaique": (-45.5752, -72.0662),
    "Puerto Aysén": (-45.4058, -72.6936), "Punta Arenas": (-53.1638, -70.9171), "Natales": (-51.7269, -72.5062),
    "Puerto Natales": (-51.7269, -72.5062), "Porvenir": (-53.2954, -70.3668)
}

COORDENADAS_REGIONES = {
    "Arica Y Parinacota": (-18.4783, -70.3126), "Tarapacá": (-20.2133, -70.1503),
    "Antofagasta": (-23.6509, -70.3975), "Atacama": (-27.3668, -70.3323),
    "Coquimbo": (-29.9027, -71.2520), "Valparaíso": (-33.0472, -71.6127),
    "Metropolitana": (-33.4489, -70.6693), "Región Metropolitana De Santiago": (-33.4489, -70.6693),
    "O'Higgins": (-34.1701, -70.7444), "Maule": (-35.4264, -71.6554),
    "Ñuble": (-36.6063, -72.1023), "Biobío": (-36.8270, -73.0503), "Biobio": (-36.8270, -73.0503),
    "Araucanía": (-38.7359, -72.5904), "La Araucanía": (-38.7359, -72.5904),
    "Los Ríos": (-39.8142, -73.2459), "Los Rios": (-39.8142, -73.2459),
    "Los Lagos": (-41.4689, -72.9411), "Aysén": (-45.5752, -72.0662), "Aysen": (-45.5752, -72.0662),
    "Magallanes": (-53.1638, -70.9171), "Magallanes Y De La Antártica Chilena": (-53.1638, -70.9171)
}

MAPEO_NOMBRES_CIENTIFICOS = {
    "ranita de antifaz": "Batrachyla taeniata", "ranita antifaz": "Batrachyla taeniata",
    "ranita de hojarasca": "Batrachyla leptopus", "sapito 4 ojos": "Pleurodema thaul",
    "ranita de darwin": "Rhinoderma darwinii", "zorro culpeo": "Lycalopex culpaeus",
    "puma": "Puma concolor", "huemul": "Hippocamelus bisulcus", "pudú": "Pudu puda",
    "cóndor andino": "Vultur gryphus", "condor": "Vultur gryphus", "loica": "Leistes loyca",
    "chucao": "Scelorchilus rubecula"
}

def obtener_nombre_cientifico_resuelto(nombre_ingresado):
    if not nombre_ingresado:
        return nombre_ingresado
    limpio = str(nombre_ingresado).strip().lower()
    return MAPEO_NOMBRES_CIENTIFICOS.get(limpio, nombre_ingresado)

@st.cache_data(max_entries=1, show_spinner=False)
def load_base_data():
    try:
        df_raw = pd.read_parquet("datos_bioexplora_light.parquet")
    except Exception:
        df_raw = pd.read_parquet("datos_bioexplora.parquet")
        
    df = pd.DataFrame()
    for col in df_raw.columns:
        col_lower = str(col).strip().lower()
        if col_lower in ['latitud', 'longitud', 'lat', 'lon']:
            df[col_lower] = pd.to_numeric(df_raw[col], errors='coerce')
        else:
            df[col_lower] = df_raw[col].astype(str)

    region_col = next((c for c in df.columns if 'region' in c), None)
    comuna_col = next((c for c in df.columns if 'comuna' in c), None)
    nombre_col = next((c for c in df.columns if 'nombre' in c or 'especie' in c or 'taxa' in c), None)
    lat_col = next((c for c in df.columns if any(term in c for term in ['lat', 'y_coord', 'y'])), None)
    lon_col = next((c for c in df.columns if any(term in c for term in ['lon', 'lng', 'x_coord', 'x'])), None)
    origen_col = next((c for c in df.columns if 'origen' in c or 'tipo' in c or 'evento' in c), None)

    df['Region'] = df[region_col].str.strip().str.title() if region_col else "Sin Información"
    df['Comuna'] = df[comuna_col].str.strip().str.title() if comuna_col else "Sin Información"
    df['NombreComun'] = df[nombre_col].str.strip().str.title() if nombre_col else "Especie No Especificada"
    df['TipoEvento'] = df[origen_col].str.strip() if origen_col else "Registro"

    invalid_values = ['nan', 'none', '', 'null', 'sin informacion', 'sin información', '<na>']
    df['NombreComun'] = df['NombreComun'].apply(lambda x: 'Especie No Especificada' if str(x).lower() in invalid_values else x)
    df['Region'] = df['Region'].apply(lambda x: 'Sin Información' if str(x).lower() in invalid_values else x)
    df['Comuna'] = df['Comuna'].apply(lambda x: 'Sin Información' if str(x).lower() in invalid_values else x)

    df['Latitud'] = pd.to_numeric(df[lat_col], errors='coerce') if lat_col else None
    df['Longitud'] = pd.to_numeric(df[lon_col], errors='coerce') if lon_col else None

    def obtener_lat(row):
        lat = row['Latitud']
        if pd.notnull(lat) and lat != 0:
            return -abs(lat) if abs(lat) > 10 else lat
        if row['Comuna'] in COORDENADAS_COMUNAS:
            return COORDENADAS_COMUNAS[row['Comuna']][0]
        return COORDENADAS_REGIONES.get(row['Region'], (None, None))[0]

    def obtener_lon(row):
        lon = row['Longitud']
        if pd.notnull(lon) and lon != 0:
            return -abs(lon) if abs(lon) > 10 else lon
        if row['Comuna'] in COORDENADAS_COMUNAS:
            return COORDENADAS_COMUNAS[row['Comuna']][1]
        return COORDENADAS_REGIONES.get(row['Region'], (None, None))[1]

    df['Latitud'] = df.apply(obtener_lat, axis=1)
    df['Longitud'] = df.apply(obtener_lon, axis=1)
    
    df['Latitud'] = df['Latitud'].fillna(-33.4489)
    df['Longitud'] = df['Longitud'].fillna(-70.6693)

    return df

@st.cache_data(ttl=60, show_spinner=False)
def cargar_aportes_comunitarios_publicos():
    """Carga solo aportes comunitarios aptos para la vista pública."""
    try:
        respuesta = (
            supabase
            .table("avistamientos")
            .select(
                "id, region, comuna, nombre_comun, tipo_evento, "
                "latitud_publica, longitud_publica, "
                "precision_publica_metros, estado_validacion, "
                "nivel_visibilidad, especie_sensible"
            )
            .eq("estado", "Publicado")
            .eq("origen_registro", "Comunitario")
            .eq("especie_sensible", False)
            .not_.is_("latitud_publica", "null")
            .not_.is_("longitud_publica", "null")
            .execute()
        )
    except Exception:
        return pd.DataFrame(
            columns=[
                "Region", "Comuna", "NombreComun", "TipoEvento",
                "Latitud", "Longitud", "OrigenRegistro",
                "EstadoValidacion", "NivelVisibilidad",
                "PrecisionPublicaMetros"
            ]
        )

    registros = respuesta.data or []
    if not registros:
        return pd.DataFrame(
            columns=[
                "Region", "Comuna", "NombreComun", "TipoEvento",
                "Latitud", "Longitud", "OrigenRegistro",
                "EstadoValidacion", "NivelVisibilidad",
                "PrecisionPublicaMetros"
            ]
        )

    df_comunitario = pd.DataFrame(registros).rename(columns={
        "region": "Region",
        "comuna": "Comuna",
        "nombre_comun": "NombreComun",
        "tipo_evento": "TipoEvento",
        "latitud_publica": "Latitud",
        "longitud_publica": "Longitud",
        "estado_validacion": "EstadoValidacion",
        "nivel_visibilidad": "NivelVisibilidad",
        "precision_publica_metros": "PrecisionPublicaMetros"
    })
    df_comunitario["OrigenRegistro"] = "Comunitario"
    return df_comunitario


def get_complete_data():
    """Combina registros históricos oficiales y aportes públicos."""
    base_df = load_base_data().copy()
    base_df["OrigenRegistro"] = "Oficial"
    base_df["EstadoValidacion"] = "Oficial"
    base_df["NivelVisibilidad"] = "Público"
    base_df["PrecisionPublicaMetros"] = None

    df_comunitario = cargar_aportes_comunitarios_publicos()
    if df_comunitario.empty:
        return base_df

    columnas = [
        "Region", "Comuna", "NombreComun", "TipoEvento",
        "Latitud", "Longitud", "OrigenRegistro",
        "EstadoValidacion", "NivelVisibilidad",
        "PrecisionPublicaMetros"
    ]
    return pd.concat(
        [base_df[columnas], df_comunitario[columnas]],
        ignore_index=True
    )


@st.cache_data(ttl=3600)
def obtener_datos_gbif(nombre_especie):
    nombre_query = obtener_nombre_cientifico_resuelto(nombre_especie)
    url = f"https://api.gbif.org/v1/species/match?name={nombre_query}"
    taxonomia, imagen_url = None, None
    try:
        res = requests.get(url, timeout=4)
        if res.status_code == 200:
            data = res.json()
            usage_key = data.get('usageKey')
            if data.get("matchType") != "NONE":
                taxonomia = {
                    "Reino": data.get("kingdom", "Desconocido"),
                    "Filo": data.get("phylum", "Desconocido"),
                    "Clase": data.get("class", "Desconocido"),
                    "Orden": data.get("order", "Desconocido"),
                    "Familia": data.get("family", "Desconocido"),
                    "Género": data.get("genus", "Desconocido"),
                    "Nombre Científico": data.get("scientificName", nombre_query)
                }
            if usage_key:
                occ_url = f"https://api.gbif.org/v1/occurrence/search?taxonKey={usage_key}&mediaType=StillImage&limit=1"
                occ_res = requests.get(occ_url, timeout=4)
                if occ_res.status_code == 200:
                    results = occ_res.json().get('results', [])
                    if results and 'media' in results[0]:
                        for m in results[0]['media']:
                            if m.get('type') == 'StillImage' and 'identifier' in m:
                                imagen_url = m['identifier']
                                break
    except Exception:
        pass
    return taxonomia, imagen_url

def crear_mapa_folium(df_puntos, lat_centro, lon_centro, zoom):
    m = folium.Map(
        location=[lat_centro, lon_centro],
        zoom_start=zoom,
        tiles="CartoDB dark_matter"
    )
    folium.TileLayer(
        "OpenStreetMap",
        name="OpenStreetMap"
    ).add_to(m)
    folium.TileLayer(
        "CartoDB positron",
        name="Claro Minimalista"
    ).add_to(m)
    folium.TileLayer(
        tiles=(
            "https://server.arcgisonline.com/ArcGIS/rest/services/"
            "World_Imagery/MapServer/tile/{z}/{y}/{x}"
        ),
        attr="Esri",
        name="Satelital / Geográfico"
    ).add_to(m)

    capa_oficial = folium.FeatureGroup(
        name="Registros oficiales",
        show=True
    )
    capa_comunitaria = folium.FeatureGroup(
        name="Aportes comunitarios publicados",
        show=True
    )

    for _, row in df_puntos.iterrows():
        es_comunitario = row.get("OrigenRegistro") == "Comunitario"

        if es_comunitario:
            color_marker = "purple"
            etiqueta_origen = "Aporte comunitario publicado"
            precision = row.get("PrecisionPublicaMetros")
            precision_txt = (
                f"Aproximadamente {int(precision):,} metros"
                if pd.notnull(precision)
                else "Ubicación generalizada"
            )
            destino = capa_comunitaria
        else:
            color_marker = (
                "green"
                if row.get("TipoEvento") == "Monitoreo"
                else "orange"
            )
            etiqueta_origen = "Registro oficial"
            precision_txt = "Según fuente histórica"
            destino = capa_oficial

        popup_txt = (
            f"<b>Especie:</b> {row['NombreComun']}<br>"
            f"<b>Región:</b> {row['Region']}<br>"
            f"<b>Comuna:</b> {row['Comuna']}<br>"
            f"<b>Categoría:</b> {etiqueta_origen}<br>"
            f"<b>Precisión pública:</b> {precision_txt}"
        )

        folium.CircleMarker(
            location=[row["Latitud"], row["Longitud"]],
            radius=8 if es_comunitario else 7,
            popup=folium.Popup(popup_txt, max_width=320),
            tooltip=(
                f"{row['NombreComun']} - {etiqueta_origen}"
            ),
            color=color_marker,
            fill=True,
            fill_color=color_marker,
            fill_opacity=0.9 if es_comunitario else 0.85,
            weight=2
        ).add_to(destino)

    capa_oficial.add_to(m)
    capa_comunitaria.add_to(m)
    folium.LayerControl(position="topright").add_to(m)
    return m


def crear_mapa_contraste_especie(df_completo, df_especie):
    lat_c = df_especie['Latitud'].mean() if not df_especie.empty else -33.4489
    lon_c = df_especie['Longitud'].mean() if not df_especie.empty else -70.6693
    zoom = 6 if not df_especie.empty else 4

    m = folium.Map(location=[lat_c, lon_c], zoom_start=zoom, tiles="CartoDB dark_matter")
    folium.TileLayer('OpenStreetMap', name='OpenStreetMap').add_to(m)
    folium.TileLayer('CartoDB positron', name='Claro Minimalista').add_to(m)

    df_otros = df_completo[~df_completo.index.isin(df_especie.index)].dropna(subset=['Latitud', 'Longitud'])
    for _, row in df_otros.iterrows():
        folium.CircleMarker(
            location=[row['Latitud'], row['Longitud']],
            radius=3,
            color='gray',
            fill=True,
            fill_color='gray',
            fill_opacity=0.25,
            tooltip=f"Otro registro: {row['NombreComun']}"
        ).add_to(m)

    for _, row in df_especie.dropna(subset=['Latitud', 'Longitud']).iterrows():
        popup_txt = f"<b>Especie:</b> {row['NombreComun']}<br><b>Región:</b> {row['Region']}<br><b>Comuna:</b> {row['Comuna']}"
        folium.CircleMarker(
            location=[row['Latitud'], row['Longitud']],
            radius=8,
            color='crimson',
            fill=True,
            fill_color='crimson',
            fill_opacity=0.9,
            popup=folium.Popup(popup_txt, max_width=300),
            tooltip=f"¡{row['NombreComun']} aquí! ({row['Comuna']})"
        ).add_to(m)

    folium.LayerControl(position='topright').add_to(m)
    return m

BUCKET_FOTOS = "fotos-avistamientos"
MAX_DIMENSION_FOTO = 1600
MIN_LADO_MAYOR_FOTO = 320
CALIDAD_JPEG = 85
FORMATOS_ENTRADA_PERMITIDOS = {"JPEG", "PNG", "WEBP"}
MIME_POR_FORMATO = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp"
}


def obtener_consentimiento_vigente(usuario_email):
    """Devuelve el consentimiento vigente de la cuenta o None."""
    if not usuario_email or usuario_email == "Invitado":
        return None

    respuesta = (
        supabase
        .table("consentimientos_usuarios")
        .select("id, version_consentimiento")
        .eq("usuario_email", usuario_email)
        .eq("confirma_autoria", True)
        .eq("autoriza_almacenamiento", True)
        .eq("autoriza_publicacion", True)
        .eq("autoriza_uso_institucional", True)
        .eq("version_consentimiento", VERSION_CONSENTIMIENTO)
        .eq("vigente", True)
        .limit(1)
        .execute()
    )

    return respuesta.data[0] if respuesta.data else None


def procesar_fotografia(foto_archivo):
    """Valida, orienta, redimensiona y convierte una imagen a JPEG sin EXIF."""
    datos_originales = foto_archivo.getvalue()
    bytes_originales = len(datos_originales)

    if not datos_originales:
        raise ValueError("La fotografía está vacía.")

    if bytes_originales > 10 * 1024 * 1024:
        raise ValueError("La fotografía supera el límite de 10 MB.")

    try:
        with Image.open(io.BytesIO(datos_originales)) as imagen_original:
            formato_original = (imagen_original.format or "").upper()

            if formato_original not in FORMATOS_ENTRADA_PERMITIDOS:
                raise ValueError(
                    "Formato no permitido. Usa una imagen JPEG, PNG o WebP."
                )

            ancho_original, alto_original = imagen_original.size
            lado_mayor = max(ancho_original, alto_original)

            if lado_mayor < MIN_LADO_MAYOR_FOTO:
                raise ValueError(
                    "La fotografía es demasiado pequeña. El lado mayor debe "
                    f"tener al menos {MIN_LADO_MAYOR_FOTO} píxeles."
                )

            # Corrige la orientación antes de retirar los metadatos EXIF.
            imagen = ImageOps.exif_transpose(imagen_original)

            # JPEG no admite transparencia. Se compone sobre fondo blanco.
            if imagen.mode in ("RGBA", "LA") or (
                imagen.mode == "P" and "transparency" in imagen.info
            ):
                rgba = imagen.convert("RGBA")
                fondo = Image.new("RGB", rgba.size, (255, 255, 255))
                fondo.paste(rgba, mask=rgba.getchannel("A"))
                imagen = fondo
            else:
                imagen = imagen.convert("RGB")

            # Reduce proporcionalmente; nunca amplía imágenes pequeñas.
            imagen.thumbnail(
                (MAX_DIMENSION_FOTO, MAX_DIMENSION_FOTO),
                Image.Resampling.LANCZOS
            )
            ancho_final, alto_final = imagen.size

            salida = io.BytesIO()
            # No se pasa exif, icc_profile ni xmp: la copia queda sanitizada.
            imagen.save(
                salida,
                format="JPEG",
                quality=CALIDAD_JPEG,
                optimize=True,
                progressive=True
            )
            datos_finales = salida.getvalue()

    except UnidentifiedImageError as error:
        raise ValueError(
            "El archivo no es una imagen válida o está dañado."
        ) from error

    return {
        "bytes": datos_finales,
        "nombre_original": foto_archivo.name,
        "mime_original": MIME_POR_FORMATO[formato_original],
        "mime_final": "image/jpeg",
        "ancho_original": ancho_original,
        "alto_original": alto_original,
        "ancho_final": ancho_final,
        "alto_final": alto_final,
        "bytes_original": bytes_originales,
        "bytes_final": len(datos_finales),
        "hash_sha256": hashlib.sha256(datos_finales).hexdigest()
    }


def crear_ruta_fotografia(usuario_email):
    """Genera una ruta privada sin exponer el correo de la cuenta."""
    usuario_hash = hashlib.sha256(
        usuario_email.lower().encode("utf-8")
    ).hexdigest()[:16]
    return f"pendientes/{usuario_hash}/{uuid.uuid4().hex}.jpg"


def subir_fotografia_privada(ruta, datos):
    """Sube el JPEG sanitizado al bucket privado."""
    return (
        supabase.storage
        .from_(BUCKET_FOTOS)
        .upload(
            path=ruta,
            file=datos,
            file_options={
                "content-type": "image/jpeg",
                "upsert": "false"
            }
        )
    )


def eliminar_fotografia_privada(ruta):
    """Elimina una imagen si falla la creación del avistamiento."""
    if ruta:
        supabase.storage.from_(BUCKET_FOTOS).remove([ruta])


def crear_url_firmada_fotografia(ruta, duracion_segundos=900):
    """Genera una URL temporal para visualizar una fotografía privada."""
    if not ruta:
        return None

    try:
        respuesta = (
            supabase.storage
            .from_(BUCKET_FOTOS)
            .create_signed_url(ruta, duracion_segundos)
        )

        if isinstance(respuesta, str):
            return respuesta

        if isinstance(respuesta, dict):
            return (
                respuesta.get("signedURL")
                or respuesta.get("signedUrl")
                or respuesta.get("signed_url")
            )

        return getattr(respuesta, "signed_url", None)
    except Exception:
        return None


VERSION_CONSENTIMIENTO = "BIOEXPLORA-CONSENTIMIENTO-2026-01"


def usuario_tiene_consentimiento_vigente(usuario_email):
    """Comprueba si la cuenta aceptó las cuatro autorizaciones vigentes."""
    if not usuario_email or usuario_email == "Invitado":
        return False

    try:
        respuesta = (
            supabase
            .table("consentimientos_usuarios")
            .select("id")
            .eq("usuario_email", usuario_email)
            .eq("confirma_autoria", True)
            .eq("autoriza_almacenamiento", True)
            .eq("autoriza_publicacion", True)
            .eq("autoriza_uso_institucional", True)
            .eq("version_consentimiento", VERSION_CONSENTIMIENTO)
            .eq("vigente", True)
            .limit(1)
            .execute()
        )
        return bool(respuesta.data)
    except Exception as error:
        st.error(
            "No fue posible verificar las autorizaciones de la cuenta: "
            f"{error}"
        )
        return False


def guardar_consentimiento_usuario(usuario_email):
    """Crea o actualiza la aceptación general de aportes de una cuenta."""
    registro = {
        "usuario_email": usuario_email,
        "confirma_autoria": True,
        "autoriza_almacenamiento": True,
        "autoriza_publicacion": True,
        "autoriza_uso_institucional": True,
        "version_consentimiento": VERSION_CONSENTIMIENTO,
        "vigente": True,
        "fecha_retiro": None
    }

    return (
        supabase
        .table("consentimientos_usuarios")
        .upsert(registro, on_conflict="usuario_email")
        .execute()
    )


def mostrar_autorizacion_aportes(usuario_email):
    """Muestra la aceptación única que habilita el menú de aportes."""
    st.subheader("🔐 Autorización para realizar aportes comunitarios")
    st.info(
        "Puedes seguir usando mapas, estadísticas y el buscador sin aceptar. "
        "Para enviar avistamientos debes aceptar una sola vez las cuatro "
        "autorizaciones asociadas a tu cuenta."
    )

    with st.expander("📄 Leer condiciones del aporte comunitario", expanded=True):
        st.markdown(
            """
Los aportes enviados mediante BioExplora Chile serán identificados como
**registros comunitarios** y no adquirirán carácter oficial por el solo
hecho de ser revisados, aprobados o publicados.

Las fotografías podrán ser validadas, corregidas de orientación,
redimensionadas hasta un máximo de **1600 × 1600 píxeles**, convertidas a
un formato admitido, comprimidas y limpiadas de metadatos antes de su
almacenamiento.

BioExplora Chile podrá generalizar la ubicación mostrada públicamente para
proteger la privacidad de las personas y la conservación de especies
sensibles. La ubicación precisa podrá conservarse con acceso restringido
para análisis institucionales autorizados.

Esta aceptación se aplicará a los aportes futuros realizados con esta
cuenta mientras permanezca vigente esta versión de las condiciones.
            """
        )

    with st.form("form_consentimiento_aportes"):
        confirma_autoria = st.checkbox(
            "Confirmo que soy autor de las fotografías que compartiré o "
            "que cuento con autorización suficiente para aportarlas."
        )
        autoriza_almacenamiento = st.checkbox(
            "Autorizo a BioExplora Chile a procesar, almacenar y revisar "
            "las fotografías y los datos asociados a mis avistamientos."
        )
        autoriza_publicacion = st.checkbox(
            "Autorizo que los aportes aprobados sean publicados como "
            "registros comunitarios, diferenciados de los oficiales."
        )
        autoriza_uso_institucional = st.checkbox(
            "Autorizo que los antecedentes técnicos, incluida la ubicación "
            "precisa cuando sea necesaria, sean compartidos de forma "
            "restringida con organismos públicos e instituciones "
            "colaboradoras autorizadas para fines de conservación, "
            "investigación, fiscalización, planificación o gestión ambiental."
        )

        aceptar = st.form_submit_button(
            "✅ Aceptar autorizaciones y habilitar aportes",
            type="primary",
            use_container_width=True
        )

        if aceptar:
            autorizaciones = [
                confirma_autoria,
                autoriza_almacenamiento,
                autoriza_publicacion,
                autoriza_uso_institucional
            ]

            if not all(autorizaciones):
                st.error(
                    "Para habilitar los aportes debes aceptar las cuatro "
                    "autorizaciones."
                )
            else:
                try:
                    respuesta = guardar_consentimiento_usuario(usuario_email)
                    if respuesta.data:
                        st.session_state.consentimiento_aportes = True
                        st.success(
                            "Autorizaciones guardadas. El formulario de "
                            "avistamientos ya está habilitado."
                        )
                        st.rerun()
                    else:
                        st.error(
                            "Supabase no confirmó el registro de las "
                            "autorizaciones."
                        )
                except Exception as error:
                    st.error(
                        "No fue posible guardar las autorizaciones: "
                        f"{error}"
                    )


def mostrar_pantalla_login():
    st.markdown("<h1 style='text-align: center;'>🌿 BioExplora Chile</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Portal de Monitoreo de Biodiversidad Silvestre</p>", unsafe_allow_html=True)
    st.markdown("---")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab_login, tab_registro, tab_invitado = st.tabs(["🔐 Iniciar Sesión", "📝 Crear Cuenta", "👤 Acceso Invitado"])

        with tab_login:
            st.subheader("Acceso para Usuarios Registrados")
            email_login = st.text_input("Correo Electrónico", key="login_email")
            pass_login = st.text_input("Contraseña", type="password", key="login_pass")
            
            if st.button("Ingresar con correo", use_container_width=True, type="primary"):
                hashed = hash_pass(pass_login)
                if email_login in st.session_state.bd_usuarios and st.session_state.bd_usuarios[email_login] == hashed:
                    st.session_state.autenticado = True
                    st.session_state.usuario_actual = email_login
                    st.session_state.tipo_acceso = "Registrado"
                    st.session_state.acceso_google = False
                    st.session_state.pop("consentimiento_aportes", None)
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas. Verifique correo y contraseña.")

            st.markdown("---")
            st.markdown("#### Acceso con Google")
            if st.button(
                "🔐 Ingresar con Google",
                use_container_width=True,
                key="btn_login_google"
            ):
                st.login()

        with tab_registro:
            st.subheader("Crear una nueva cuenta")
            nuevo_email = st.text_input("Correo Electrónico", key="reg_email")
            nuevo_pass = st.text_input("Contraseña", type="password", key="reg_pass")
            nuevo_pass_confirm = st.text_input("Confirmar Contraseña", type="password", key="reg_pass_conf")

            if st.button("Registrar Cuenta", use_container_width=True):
                if not nuevo_email or not nuevo_pass:
                    st.warning("Por favor complete todos los campos.")
                elif nuevo_pass != nuevo_pass_confirm:
                    st.error("Las contraseñas no coinciden.")
                elif nuevo_email in st.session_state.bd_usuarios:
                    st.warning("Este correo ya se encuentra registrado.")
                else:
                    st.session_state.bd_usuarios[nuevo_email] = hash_pass(nuevo_pass)
                    st.session_state.conteo_avistamientos[nuevo_email] = 0
                    st.session_state.perfiles_usuarios[nuevo_email] = {
                        "nombre": nuevo_email.split("@")[0].title(),
                        "bio": "Entusiasta de la naturaleza.",
                        "edad": "", "genero": "Prefiero no decirlo", "instagram": "", "facebook": "", "avatar": None
                    }
                    st.success("¡Cuenta creada exitosamente! Ya puede iniciar sesión.")

        with tab_invitado:
            st.subheader("Acceso Rápido")
            st.write("Explora el portal de datos en modo solo lectura sin crear una cuenta.")
            if st.button("🚀 Entrar como Invitado", use_container_width=True):
                st.session_state.autenticado = True
                st.session_state.usuario_actual = "Invitado"
                st.session_state.tipo_acceso = "Invitado"
                st.session_state.acceso_google = False
                st.session_state.pop("consentimiento_aportes", None)
                st.rerun()

def mostrar_aplicacion_principal():
    usr_actual = st.session_state.usuario_actual
    perfil_actual = st.session_state.perfiles_usuarios.get(usr_actual, {
        "nombre": usr_actual, "bio": "Sin biografía", "edad": "", "genero": "No especificado", "instagram": "", "facebook": "", "avatar": None
    })

    with st.sidebar:
        if perfil_actual.get('avatar') is not None:
            st.image(perfil_actual.get('avatar'), width=80)
        
        st.markdown(f"👤 **Nombre:** `{perfil_actual.get('nombre')}`")
        st.markdown(f"📧 **Cuenta:** `{usr_actual}`")
        st.markdown(f"🏷️ **Perfil:** `{st.session_state.tipo_acceso}`")
        
        if perfil_actual.get('instagram'):
            st.markdown(f"📸 **Instagram:** [@{perfil_actual.get('instagram')}](https://instagram.com/{perfil_actual.get('instagram').replace('@','')})")
        
        if st.session_state.tipo_acceso == "Registrado":
            cant_obs = st.session_state.conteo_avistamientos.get(usr_actual, 0)
            rango, color_badge = obtener_rango_usuario(cant_obs)
            st.markdown("---")
            st.markdown("### 🏅 Tu Reputación")
            st.markdown(f"**Rango:** {rango}")
            st.markdown(f"**Avistamientos aportados:** `{cant_obs}`")
            st.progress(min(cant_obs / 15, 1.0))
        else:
            st.markdown("---")
            st.info("💡 Regístrate para personalizar tu perfil, sumar puntos y desbloquear rangos.")

        st.markdown("---")
        if st.button(
            "🚪 Cerrar Sesión",
            use_container_width=True,
            key="btn_cerrar_sesion"
        ):
            sesion_google = (
                st.session_state.get("acceso_google", False)
                or st.user.is_logged_in
            )

            st.session_state.autenticado = False
            st.session_state.usuario_actual = None
            st.session_state.tipo_acceso = None
            st.session_state.acceso_google = False
            st.session_state.pop("consentimiento_aportes", None)

            if sesion_google and st.user.is_logged_in:
                st.logout()
            else:
                st.rerun()

    st.title("🌿 BioExplora Chile: Portal de Biodiversidad")

    try:
        df = get_complete_data()
        
        if st.session_state.tipo_acceso == "Registrado":
            tab1, tab2, tab3, tab4, tab_perfil = st.tabs([
                "📌 Mapa Geográfico", 
                "📊 Estadísticas", 
                "🔍 Buscador de Especies",
                "📝 Reportar Avistamiento",
                "⚙️ Mi Perfil"
            ])
        else:
            tab1, tab2, tab3, tab4 = st.tabs([
                "📌 Mapa Geográfico", 
                "📊 Estadísticas", 
                "🔍 Buscador de Especies",
                "📝 Reportar Avistamiento"
            ])
            tab_perfil = None

        with tab1:
            st.subheader("Filtros del Mapa")
            c_reg, c_est, c_origen = st.columns(3)

            with c_reg:
                regiones = ["Todas"] + sorted([
                    r for r in df["Region"].unique()
                    if r not in ["Sin Información"]
                ])
                selected_region = st.selectbox(
                    "Seleccione Región:",
                    regiones
                )

            with c_est:
                filtro_identificacion = st.radio(
                    "Estado de Identificación:",
                    ["Todas", "Solo Identificadas", "No Identificadas"],
                    horizontal=True
                )

            with c_origen:
                filtro_origen = st.selectbox(
                    "Origen del registro:",
                    ["Todos", "Oficial", "Comunitario"]
                )

            df_map = df.dropna(subset=["Latitud", "Longitud"])

            if selected_region != "Todas":
                df_map = df_map[df_map["Region"] == selected_region]

            if filtro_identificacion == "Solo Identificadas":
                df_map = df_map[
                    df_map["NombreComun"] != "Especie No Especificada"
                ]
            elif filtro_identificacion == "No Identificadas":
                df_map = df_map[
                    df_map["NombreComun"] == "Especie No Especificada"
                ]

            if filtro_origen != "Todos":
                df_map = df_map[
                    df_map["OrigenRegistro"] == filtro_origen
                ]

            oficiales_vista = int(
                (df_map["OrigenRegistro"] == "Oficial").sum()
            )
            comunitarios_vista = int(
                (df_map["OrigenRegistro"] == "Comunitario").sum()
            )

            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("Registros visibles", f"{len(df_map):,}")
            col_m2.metric("Oficiales", f"{oficiales_vista:,}")
            col_m3.metric(
                "Comunitarios publicados",
                f"{comunitarios_vista:,}"
            )

            st.caption(
                "🟢/🟠 Registros oficiales según su fuente histórica. "
                "🟣 Aportes comunitarios publicados con ubicación "
                "generalizada. Las especies sensibles no se muestran en "
                "el mapa público."
            )

            if len(df_map) > 0:
                lat_center = df_map["Latitud"].mean()
                lon_center = df_map["Longitud"].mean()
                zoom_level = 4 if selected_region == "Todas" else 7
                mapa = crear_mapa_folium(
                    df_map,
                    lat_center,
                    lon_center,
                    zoom_level
                )
                st_folium(
                    mapa,
                    use_container_width=True,
                    height=600,
                    returned_objects=[]
                )
            else:
                st.warning(
                    "No hay registros que coincidan con los filtros "
                    "seleccionados."
                )

        with tab2:
            st.subheader("Métricas Generales")
            total_oficiales = int(
                (df["OrigenRegistro"] == "Oficial").sum()
            )
            total_comunitarios = int(
                (df["OrigenRegistro"] == "Comunitario").sum()
            )

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Registros oficiales", f"{total_oficiales:,}")
            col2.metric(
                "Aportes comunitarios publicados",
                f"{total_comunitarios:,}"
            )
            col3.metric("Total visible", f"{len(df):,}")
            col4.metric(
                "Especies distintas",
                f"{df[df['NombreComun'] != 'Especie No Especificada']['NombreComun'].nunique():,}"
            )

            st.caption(
                "Las métricas comunitarias incluyen solo aportes publicados "
                "y aptos para la vista pública. Los registros sensibles o "
                "restringidos no se contabilizan aquí."
            )
            st.markdown("---")
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("### Top 10 Especies Más Frecuentes")
                df_esp_chart = df[df['NombreComun'] != 'Especie No Especificada']['NombreComun'].value_counts().head(10).reset_index()
                df_esp_chart.columns = ['Especie', 'Cantidad']
                if not df_esp_chart.empty:
                    fig_esp = px.bar(
                        df_esp_chart, x='Cantidad', y='Especie',
                        orientation='h', color='Cantidad', color_continuous_scale='Greens', text_auto=True
                    )
                    fig_esp.update_layout(
                        yaxis={'categoryorder': 'total ascending'}, showlegend=False, height=400,
                        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#cbd5e1')
                    )
                    st.plotly_chart(fig_esp, use_container_width=True)

            with c2:
                st.markdown("### Top 10 Comunas con Mayor Actividad")
                df_com_chart = df['Comuna'].value_counts().head(10).reset_index()
                df_com_chart.columns = ['Comuna', 'Cantidad']
                if not df_com_chart.empty:
                    fig_com = px.bar(
                        df_com_chart, x='Cantidad', y='Comuna',
                        orientation='h', color='Cantidad', color_continuous_scale='Teal', text_auto=True
                    )
                    fig_com.update_layout(
                        yaxis={'categoryorder': 'total ascending'}, showlegend=False, height=400,
                        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#cbd5e1')
                    )
                    st.plotly_chart(fig_com, use_container_width=True)

        with tab3:
            st.subheader("Buscador y Ficha de Especie")
            col_search1, col_search2 = st.columns([1, 1])
            with col_search1:
                busqueda = st.text_input("1. Buscar por palabra o fragmento de nombre:", "ranita")
            
            if busqueda.strip():
                df_coincidencias = df[df['NombreComun'].str.contains(busqueda, case=False, na=False)]
                especies_halladas = sorted([e for e in df_coincidencias['NombreComun'].unique() if e != 'Especie No Especificada'])
                
                with col_search2:
                    if especies_halladas:
                        especie_seleccionada = st.selectbox("2. Seleccione la especie exacta encontrada:", especies_halladas)
                    else:
                        especie_seleccionada = None
                        st.warning("No se encontraron especies específicas.")
                
                if especie_seleccionada:
                    df_esp = df[df['NombreComun'] == especie_seleccionada]
                    st.success(f"Mostrando información para **{especie_seleccionada}** ({len(df_esp):,} registros).")
                    
                    st.markdown("---")
                    st.markdown("### 🧬 Ficha Taxonómica y Registro Fotográfico")
                    tax, img_url = obtener_datos_gbif(especie_seleccionada)
                    
                    col_info_a, col_info_b = st.columns([1, 1])
                    with col_info_a:
                        if img_url:
                            st.image(img_url, caption=f"Fotografía: {especie_seleccionada}", use_container_width=True)
                        else:
                            st.info("📷 No hay fotografía disponible.")
                    with col_info_b:
                        if tax:
                            st.markdown(f"**Nombre Científico:** *{tax.get('Nombre Científico')}*")
                            st.markdown(f"• **Reino:** {tax.get('Reino')}")
                            st.markdown(f"• **Filo:** {tax.get('Filo')}")
                            st.markdown(f"• **Clase:** {tax.get('Clase')}")
                            st.markdown(f"• **Orden:** {tax.get('Orden')}")
                            st.markdown(f"• **Familia:** {tax.get('Familia')}")
                        else:
                            st.write("Sin datos taxonómicos externos.")

                    st.markdown("---")
                    st.markdown("### 🗺️ Mapa de Contraste: Distribución de la Especie vs. Resto de Registros")
                    mapa_especie = crear_mapa_contraste_especie(df, df_esp)
                    st_folium(mapa_especie, use_container_width=True, height=500, returned_objects=[])

        with tab4:
            st.subheader("📝 Registrar un Nuevo Avistamiento de Biodiversidad")

            if st.session_state.tipo_acceso == "Invitado":
                st.warning(
                    "🔒 Los invitados están en modo sólo lectura. "
                    "Inicia sesión con una cuenta para reportar avistamientos."
                )
            else:
                if "consentimiento_aportes" not in st.session_state:
                    st.session_state.consentimiento_aportes = (
                        usuario_tiene_consentimiento_vigente(usr_actual)
                    )

                if not st.session_state.consentimiento_aportes:
                    mostrar_autorizacion_aportes(usr_actual)
                else:
                    st.success(
                        "✅ Tu cuenta tiene las autorizaciones vigentes para "
                        "realizar aportes comunitarios."
                    )
                    st.markdown(
                        "Puedes adjuntar una fotografía JPEG, PNG o WebP de "
                        "hasta 10 MB. BioExplora la orientará, redimensionará "
                        "hasta 1600 × 1600 píxeles, convertirá a JPEG y "
                        "eliminará sus metadatos antes de almacenarla."
                    )

                    with st.form("form_avistamiento"):
                        col_f1, col_f2 = st.columns(2)

                        with col_f1:
                            input_especie = st.text_input(
                                "Especie observada:",
                                placeholder="Ej: Pudú, Cóndor"
                            )
                            lista_regiones = sorted(
                                list(COORDENADAS_REGIONES.keys())
                            )
                            input_region = st.selectbox(
                                "Región:",
                                lista_regiones
                            )
                            input_comuna = st.text_input(
                                "Comuna:",
                                placeholder="Ej: San Pablo"
                            )

                        with col_f2:
                            foto_avistamiento = st.file_uploader(
                                "📷 Subir fotografía (opcional)",
                                type=["jpg", "jpeg", "png", "webp"],
                                help=(
                                    "Máximo 10 MB. La copia almacenada se "
                                    "guardará como JPEG, sin metadatos."
                                )
                            )
                            input_notas = st.text_area(
                                "Notas / Observaciones de campo:"
                            )

                        btn_guardar = st.form_submit_button(
                            "📥 Enviar a Revisión",
                            type="primary",
                            use_container_width=True
                        )

                        if btn_guardar:
                            if (
                                not input_especie.strip()
                                or not input_comuna.strip()
                            ):
                                st.error(
                                    "Por favor completa al menos la especie "
                                    "y la comuna."
                                )
                            else:
                                ruta_foto = None
                                foto_procesada = None

                                try:
                                    consentimiento = (
                                        obtener_consentimiento_vigente(
                                            usr_actual
                                        )
                                    )
                                    if not consentimiento:
                                        st.session_state.consentimiento_aportes = False
                                        raise ValueError(
                                            "La autorización de aportes no está "
                                            "vigente. Vuelve a aceptar las "
                                            "condiciones."
                                        )

                                    lat_exif, lon_exif = None, None
                                    if foto_avistamiento is not None:
                                        # Extraer GPS de la copia temporal antes
                                        # de sanitizar y subir la fotografía.
                                        lat_exif, lon_exif = (
                                            obtener_coordenadas_exif(
                                                foto_avistamiento
                                            )
                                        )
                                        foto_avistamiento.seek(0)
                                        foto_procesada = procesar_fotografia(
                                            foto_avistamiento
                                        )

                                    if (
                                        lat_exif is not None
                                        and lon_exif is not None
                                    ):
                                        lat_final = lat_exif
                                        lon_final = lon_exif
                                    else:
                                        coordenadas_finales = (
                                            COORDENADAS_COMUNAS.get(
                                                input_comuna.strip().title(),
                                                COORDENADAS_REGIONES.get(
                                                    input_region,
                                                    (-33.4489, -70.6693)
                                                )
                                            )
                                        )
                                        lat_final = coordenadas_finales[0]
                                        lon_final = coordenadas_finales[1]

                                    if foto_procesada is not None:
                                        ruta_foto = crear_ruta_fotografia(
                                            usr_actual
                                        )
                                        subir_fotografia_privada(
                                            ruta_foto,
                                            foto_procesada["bytes"]
                                        )

                                    registro_supabase = {
                                        "region": input_region,
                                        "comuna": input_comuna.strip().title(),
                                        "nombre_comun": (
                                            input_especie.strip().title()
                                        ),
                                        "nombre_cientifico": (
                                            obtener_nombre_cientifico_resuelto(
                                                input_especie.strip()
                                            )
                                        ),
                                        "tipo_evento": "Aporte Comunitario",
                                        "latitud": float(lat_final),
                                        "longitud": float(lon_final),
                                        "aportado_por": usr_actual,
                                        "notas": input_notas.strip(),
                                        "estado": "Pendiente de Revisión",
                                        "foto_url": ruta_foto,
                                        "consentimiento_id": consentimiento["id"],
                                        "version_consentimiento": (
                                            consentimiento[
                                                "version_consentimiento"
                                            ]
                                        ),
                                        "origen_registro": "Comunitario",
                                        "estado_validacion": "Pendiente",
                                        "nivel_visibilidad": (
                                            "Privado durante revisión"
                                        ),
                                        "especie_sensible": False,
                                        "foto_ruta": ruta_foto,
                                        "foto_nombre_original": (
                                            foto_procesada["nombre_original"]
                                            if foto_procesada else None
                                        ),
                                        "foto_mime_original": (
                                            foto_procesada["mime_original"]
                                            if foto_procesada else None
                                        ),
                                        "foto_mime_final": (
                                            foto_procesada["mime_final"]
                                            if foto_procesada else None
                                        ),
                                        "foto_ancho_original": (
                                            foto_procesada["ancho_original"]
                                            if foto_procesada else None
                                        ),
                                        "foto_alto_original": (
                                            foto_procesada["alto_original"]
                                            if foto_procesada else None
                                        ),
                                        "foto_ancho_final": (
                                            foto_procesada["ancho_final"]
                                            if foto_procesada else None
                                        ),
                                        "foto_alto_final": (
                                            foto_procesada["alto_final"]
                                            if foto_procesada else None
                                        ),
                                        "foto_bytes_original": (
                                            foto_procesada["bytes_original"]
                                            if foto_procesada else None
                                        ),
                                        "foto_bytes_final": (
                                            foto_procesada["bytes_final"]
                                            if foto_procesada else None
                                        ),
                                        "foto_hash_sha256": (
                                            foto_procesada["hash_sha256"]
                                            if foto_procesada else None
                                        )
                                    }

                                    respuesta_supabase = (
                                        supabase
                                        .table("avistamientos")
                                        .insert(registro_supabase)
                                        .execute()
                                    )

                                    if respuesta_supabase.data:
                                        if foto_procesada:
                                            reduccion = 100 * (
                                                1 - (
                                                    foto_procesada[
                                                        "bytes_final"
                                                    ]
                                                    / foto_procesada[
                                                        "bytes_original"
                                                    ]
                                                )
                                            )
                                            st.success(
                                                "📝 ¡Avistamiento y fotografía "
                                                "guardados permanentemente y "
                                                "enviados a revisión!"
                                            )
                                            st.caption(
                                                "Imagen procesada: "
                                                f"{foto_procesada['ancho_final']} × "
                                                f"{foto_procesada['alto_final']} px, "
                                                f"reducción aproximada de "
                                                f"{max(reduccion, 0):.1f}%."
                                            )
                                        else:
                                            st.success(
                                                "📝 ¡Avistamiento guardado "
                                                "permanentemente y enviado "
                                                "a revisión!"
                                            )
                                    else:
                                        eliminar_fotografia_privada(ruta_foto)
                                        st.error(
                                            "Supabase no confirmó la creación "
                                            "del avistamiento."
                                        )

                                except Exception as error:
                                    try:
                                        eliminar_fotografia_privada(ruta_foto)
                                    except Exception:
                                        pass
                                    st.error(
                                        "No fue posible guardar el aporte: "
                                        f"{error}"
                                    )

        if tab_perfil and st.session_state.tipo_acceso == "Registrado":
            with tab_perfil:
                st.subheader("⚙️ Configuración y Personalización del Perfil")
                col_p1, col_p2 = st.columns([1, 2])
                with col_p1:
                    if perfil_actual.get('avatar') is not None:
                        st.image(perfil_actual.get('avatar'), caption="Tu Foto de Perfil", use_container_width=True)
                    else:
                        st.info("📷 Sin foto de perfil cargada.")
                with col_p2:
                    with st.form("form_perfil"):
                        nuevo_nombre_publico = st.text_input("Nombre Público / Alias:", value=perfil_actual.get("nombre", ""))
                        nueva_bio = st.text_area("Biografía o Descripción personal:", value=perfil_actual.get("bio", ""))
                        c_edad, c_gen = st.columns(2)
                        with c_edad:
                            nueva_edad = st.text_input("Edad:", value=str(perfil_actual.get("edad", "")))
                        with c_gen:
                            opciones_genero = ["Prefiero no decirlo", "Masculino", "Femenino", "Otro"]
                            gen_guardado = perfil_actual.get("genero", "Prefiero no decirlo")
                            idx_gen = opciones_genero.index(gen_guardado) if gen_guardado in opciones_genero else 0
                            nuevo_genero = st.selectbox("Género:", opciones_genero, index=idx_gen)
                        
                        nuevo_ig = st.text_input("Instagram:", value=perfil_actual.get("instagram", ""))
                        nuevo_fb = st.text_input("Facebook:", value=perfil_actual.get("facebook", ""))
                        nueva_foto_avatar = st.file_uploader("Actualizar Avatar:", type=["jpg", "jpeg", "png"])
                        
                        btn_guardar_perfil = st.form_submit_button("💾 Guardar Cambios de Perfil", type="primary", use_container_width=True)
                        if btn_guardar_perfil:
                            st.session_state.perfiles_usuarios[usr_actual] = {
                                "nombre": nuevo_nombre_publico.strip() or usr_actual,
                                "bio": nueva_bio.strip(),
                                "edad": nueva_edad.strip(),
                                "genero": nuevo_genero,
                                "instagram": nuevo_ig.strip().replace("@", ""),
                                "facebook": nuevo_fb.strip(),
                                "avatar": nueva_foto_avatar if nueva_foto_avatar is not None else perfil_actual.get('avatar')
                            }
                            st.success("¡Perfil actualizado correctamente!")
                            st.rerun()

                st.markdown("---")
                st.markdown(
                    "### 📥 Mis Aportes Pendientes y Clasificación Comunitaria"
                )
                st.caption(
                    "Esta sección administra aportes comunitarios. Publicar "
                    "un aporte no le otorga carácter oficial ni constituye "
                    "validación institucional."
                )

                try:
                    respuesta_pendientes = (
                        supabase
                        .table("avistamientos")
                        .select(
                            "id, fecha_creacion, region, comuna, "
                            "nombre_comun, nombre_cientifico, tipo_evento, "
                            "latitud, longitud, aportado_por, notas, estado, "
                            "estado_validacion, nivel_visibilidad, "
                            "especie_sensible, foto_ruta, foto_ancho_final, "
                            "foto_alto_final, foto_bytes_final"
                        )
                        .eq("aportado_por", usr_actual)
                        .eq("estado", "Pendiente de Revisión")
                        .order("fecha_creacion", desc=True)
                        .execute()
                    )
                    mis_pendientes = respuesta_pendientes.data or []
                except Exception as error:
                    mis_pendientes = []
                    st.error(
                        "No fue posible cargar los aportes pendientes: "
                        f"{error}"
                    )

                if mis_pendientes:
                    st.info(
                        f"Tienes {len(mis_pendientes)} aporte(s) pendiente(s)."
                    )

                    for registro in mis_pendientes:
                        registro_id = registro["id"]
                        especie_actual = registro.get(
                            "nombre_comun",
                            "Especie no especificada"
                        )
                        comuna_actual = registro.get(
                            "comuna",
                            "Sin comuna"
                        )

                        with st.expander(
                            f"🔍 Aporte #{registro_id}: "
                            f"{especie_actual} ({comuna_actual})"
                        ):
                            col_foto, col_datos = st.columns([1, 2])

                            with col_foto:
                                foto_ruta = registro.get("foto_ruta")
                                if foto_ruta:
                                    url_firmada = (
                                        crear_url_firmada_fotografia(
                                            foto_ruta,
                                            duracion_segundos=900
                                        )
                                    )
                                    if url_firmada:
                                        st.image(
                                            url_firmada,
                                            caption=(
                                                "Fotografía privada. Enlace "
                                                "temporal de 15 minutos."
                                            ),
                                            use_container_width=True
                                        )
                                    else:
                                        st.warning(
                                            "No fue posible generar la vista "
                                            "temporal de la fotografía."
                                        )
                                else:
                                    st.info("Este aporte no tiene fotografía.")

                            with col_datos:
                                st.markdown(
                                    f"**Origen:** "
                                    f"{registro.get('tipo_evento', 'Comunitario')}"
                                )
                                st.markdown(
                                    f"**Región:** {registro.get('region', '')}"
                                )
                                st.markdown(
                                    f"**Coordenadas privadas:** "
                                    f"{registro.get('latitud')}, "
                                    f"{registro.get('longitud')}"
                                )
                                st.markdown(
                                    f"**Notas:** "
                                    f"{registro.get('notas') or 'Sin notas'}"
                                )

                            with st.form(
                                f"form_revision_supabase_{registro_id}"
                            ):
                                rev_especie = st.text_input(
                                    "Especie:",
                                    value=especie_actual,
                                    key=f"rev_esp_{registro_id}"
                                )
                                rev_comuna = st.text_input(
                                    "Comuna:",
                                    value=comuna_actual,
                                    key=f"rev_com_{registro_id}"
                                )
                                rev_sensible = st.checkbox(
                                    "Marcar como especie sensible",
                                    value=bool(
                                        registro.get("especie_sensible", False)
                                    ),
                                    key=f"rev_sensible_{registro_id}"
                                )

                                c_btn1, c_btn2 = st.columns(2)
                                with c_btn1:
                                    btn_publicar = st.form_submit_button(
                                        "🚀 Publicar como aporte comunitario",
                                        type="primary",
                                        use_container_width=True
                                    )
                                with c_btn2:
                                    btn_descartar = st.form_submit_button(
                                        "🗑️ Descartar",
                                        use_container_width=True
                                    )

                                if btn_publicar:
                                    especie_limpia = rev_especie.strip().title()
                                    comuna_limpia = rev_comuna.strip().title()

                                    if not especie_limpia or not comuna_limpia:
                                        st.error(
                                            "La especie y la comuna son "
                                            "obligatorias."
                                        )
                                    else:
                                        coordenadas = COORDENADAS_COMUNAS.get(
                                            comuna_limpia,
                                            (
                                                registro.get("latitud"),
                                                registro.get("longitud")
                                            )
                                        )

                                        if rev_sensible:
                                            visibilidad = (
                                                "Restringido institucional"
                                            )
                                            latitud_publica = None
                                            longitud_publica = None
                                            precision_publica = None
                                        else:
                                            visibilidad = (
                                                "Público con ubicación "
                                                "aproximada"
                                            )
                                            latitud_publica = round(
                                                float(coordenadas[0]),
                                                2
                                            )
                                            longitud_publica = round(
                                                float(coordenadas[1]),
                                                2
                                            )
                                            precision_publica = 1500

                                        actualizacion = {
                                            "comuna": comuna_limpia,
                                            "nombre_comun": especie_limpia,
                                            "nombre_cientifico": (
                                                obtener_nombre_cientifico_resuelto(
                                                    especie_limpia
                                                )
                                            ),
                                            "latitud": float(coordenadas[0]),
                                            "longitud": float(coordenadas[1]),
                                            "estado": "Publicado",
                                            "estado_validacion": (
                                                "Validado comunitario"
                                            ),
                                            "nivel_visibilidad": visibilidad,
                                            "especie_sensible": rev_sensible,
                                            "origen_registro": "Comunitario",
                                            "latitud_publica": latitud_publica,
                                            "longitud_publica": longitud_publica,
                                            "precision_publica_metros": (
                                                precision_publica
                                            )
                                        }

                                        try:
                                            respuesta_actualizacion = (
                                                supabase
                                                .table("avistamientos")
                                                .update(actualizacion)
                                                .eq("id", registro_id)
                                                .eq(
                                                    "aportado_por",
                                                    usr_actual
                                                )
                                                .execute()
                                            )

                                            if respuesta_actualizacion.data:
                                                cargar_aportes_comunitarios_publicos.clear()
                                                st.success(
                                                    "Aporte comunitario "
                                                    "publicado correctamente."
                                                )
                                                st.rerun()
                                            else:
                                                st.error(
                                                    "Supabase no confirmó la "
                                                    "publicación del aporte."
                                                )
                                        except Exception as error:
                                            st.error(
                                                "No fue posible publicar el "
                                                f"aporte: {error}"
                                            )

                                if btn_descartar:
                                    try:
                                        respuesta_descarte = (
                                            supabase
                                            .table("avistamientos")
                                            .update({
                                                "estado": "Descartado",
                                                "estado_validacion": (
                                                    "Rechazado"
                                                ),
                                                "nivel_visibilidad": (
                                                    "Privado durante revisión"
                                                )
                                            })
                                            .eq("id", registro_id)
                                            .eq("aportado_por", usr_actual)
                                            .execute()
                                        )

                                        if respuesta_descarte.data:
                                            st.warning(
                                                "Aporte descartado. La "
                                                "fotografía permanece privada "
                                                "hasta aplicar la política de "
                                                "retención y eliminación."
                                            )
                                            st.rerun()
                                        else:
                                            st.error(
                                                "Supabase no confirmó el "
                                                "descarte del aporte."
                                            )
                                    except Exception as error:
                                        st.error(
                                            "No fue posible descartar el "
                                            f"aporte: {error}"
                                        )
                else:
                    st.info(
                        "No tienes avistamientos pendientes de revisión."
                    )

    except Exception as e:
        st.error(f"Error en la aplicación: {e}")

# --- ENRUTADOR PRINCIPAL ---
if st.user.is_logged_in:
    st.session_state.autenticado = True
    st.session_state.acceso_google = True

if st.session_state.get("autenticado", False):
    mostrar_aplicacion_principal()
else:
    mostrar_pantalla_login()
