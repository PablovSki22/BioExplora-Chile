import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import st_folium
import requests
import hashlib
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

st.set_page_config(
    page_title="BioExplora Chile",
    page_icon="🌿",
    layout="wide"
)

# --- ESTILOS CSS PERSONALIZADOS (MODERN APP UI / TEMA OSCURO CIENTÍFICO) ---
st.markdown("""
<style>
    /* Fondo general de la aplicación estilo App de Monitoreo */
    .stApp {
        background-color: #0b132b;
        color: #e2e8f0;
    }
    
    /* Forzar tipografía clara en textos generales */
    p, span, label, div {
        color: #cbd5e1;
    }

    h1, h2, h3, h4, h5, h6 {
        color: #f8fafc !important;
    }

    /* Contenedores principales (Tarjetas flotantes) */
    div.stMarkdown, div.stForm, div.stTabs {
        background-color: #1c2541;
        border-radius: 12px;
        padding: 5px;
    }

    /* Pestañas de navegación estilizadas */
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

    /* Botones principales con aspecto de aplicación moderna */
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
        box-shadow: 0 8px 12px -2px rgba(16, 185, 129, 0.4);
        transform: translateY(-2px);
    }
    
    /* Tarjetas de Métricas con relieve oscuro */
    div[data-testid="stMetric"] {
        background-color: #1c2541;
        padding: 16px;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
        border: 1px solid #3a506b;
    }
    
    div[data-testid="stMetric"] label {
        color: #94a3b8 !important;
    }

    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #38bdf8 !important;
        font-weight: 700;
    }

    /* Cajas de alerta / Info */
    div.stAlert {
        background-color: #1c2541;
        border: 1px solid #3a506b;
        border-radius: 10px;
        color: #e2e8f0;
    }
    
    /* Inputs, Selectbox y Textarea */
    div.stTextInput > div > div > input, div.stSelectbox > div > div > div, div.stTextArea > div > div > textarea {
        background-color: #0b132b;
        color: #f8fafc;
        border-radius: 8px;
        border: 1px solid #3a506b;
    }
    
    /* Sidebar con diseño de panel de control */
    section[data-testid="stSidebar"] {
        background-color: #0b132b;
        border-right: 1px solid #1c2541;
    }
</style>
""", unsafe_allow_html=True)

# --- VERIFICACIÓN Y CONTROL DE SESIÓN GOOGLE NATIVA ---
user_obj = getattr(st, "user", getattr(st, "experimental_user", None))
is_logged_in_google = False
google_email = None

if user_obj:
    if getattr(user_obj, "is_logged_in", False):
        is_logged_in_google = True
        google_email = getattr(user_obj, "email", "Usuario Google")
    elif getattr(user_obj, "email", None):
        is_logged_in_google = True
        google_email = user_obj.email

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

# Si Google confirmó login
if is_logged_in_google:
    st.session_state.autenticado = True
    st.session_state.usuario_actual = google_email
    st.session_state.tipo_acceso = "Registrado"
    if google_email not in st.session_state.conteo_avistamientos:
        st.session_state.conteo_avistamientos[google_email] = 0
    if google_email not in st.session_state.perfiles_usuarios:
        st.session_state.perfiles_usuarios[google_email] = {
            "nombre": google_email.split("@")[0].title(),
            "bio": "Entusiasta de la biodiversidad chilena.",
            "edad": "",
            "genero": "Prefiero no decirlo",
            "instagram": "",
            "facebook": "",
            "avatar": None
        }
elif "autenticado" not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.usuario_actual = None
    st.session_state.tipo_acceso = None

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

# --- EXTRACCIÓN DE GPS DE IMÁGENES (EXIF) ---
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

# --- DICCIONARIOS DE MAPPING ---
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
    "ranita de antifaz": "Batrachyla taeniata",
    "ranita antifaz": "Batrachyla taeniata",
    "ranita de hojarasca": "Batrachyla leptopus",
    "sapito 4 ojos": "Pleurodema thaul",
    "ranita de darwin": "Rhinoderma darwinii",
    "zorro culpeo": "Lycalopex culpaeus",
    "puma": "Puma concolor",
    "huemul": "Hippocamelus bisulcus",
    "pudú": "Pudu puda",
    "cóndor andino": "Vultur gryphus",
    "condor": "Vultur gryphus",
    "loica": "Leistes loyca",
    "chucao": "Scelorchilus rubecula"
}

def obtener_nombre_cientifico_resuelto(nombre_ingresado):
    if not nombre_ingresado:
        return nombre_ingresado
    limpio = str(nombre_ingresado).strip().lower()
    return MAPEO_NOMBRES_CIENTIFICOS.get(limpio, nombre_ingresado)

@st.cache_data
def load_base_data():
    df_raw = pd.read_parquet("datos_bioexplora_light.parquet")
    df = pd.DataFrame()
    for col in df_raw.columns:
        df[str(col).strip().lower()] = df_raw[col].astype(str)

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

    return df

if "df_nuevos_registros" not in st.session_state:
    st.session_state.df_nuevos_registros = pd.DataFrame(columns=['Region', 'Comuna', 'NombreComun', 'TipoEvento', 'Latitud', 'Longitud', 'AportadoPor'])

def get_complete_data():
    base_df = load_base_data()
    if not st.session_state.df_nuevos_registros.empty:
        cols_base = ['Region', 'Comuna', 'NombreComun', 'TipoEvento', 'Latitud', 'Longitud']
        df_clean_nuevos = st.session_state.df_nuevos_registros[cols_base]
        return pd.concat([base_df, df_clean_nuevos], ignore_index=True)
    return base_df

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
    m = folium.Map(location=[lat_centro, lon_centro], zoom_start=zoom, tiles="CartoDB dark_matter")
    folium.TileLayer('OpenStreetMap', name='OpenStreetMap').add_to(m)
    folium.TileLayer('CartoDB positron', name='Claro Minimalista').add_to(m)
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri',
        name='Satelital / Geográfico'
    ).add_to(m)

    for _, row in df_puntos.iterrows():
        color_marker = "green" if row.get("TipoEvento") == "Monitoreo" else ("purple" if row.get("TipoEvento") == "Aporte Comunitario" else "orange")
        popup_txt = f"<b>Especie:</b> {row['NombreComun']}<br><b>Región:</b> {row['Region']}<br><b>Comuna:</b> {row['Comuna']}<br><b>Tipo:</b> {row['TipoEvento']}"
        folium.CircleMarker(
            location=[row['Latitud'], row['Longitud']],
            radius=7,
            popup=folium.Popup(popup_txt, max_width=300),
            tooltip=f"{row['NombreComun']} - {row['Comuna']}",
            color=color_marker,
            fill=True,
            fill_color=color_marker,
            fill_opacity=0.85
        ).add_to(m)

    folium.LayerControl(position='topright').add_to(m)
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

# --- PANTALLA DE AUTENTICACIÓN ---
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
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas. Verifique correo y contraseña.")

            st.markdown("---")
            st.markdown("##### O ingresa directamente con Google:")
            
            if st.button("🌐 Continuar con Google", use_container_width=True):
                try:
                    st.login("google")
                except Exception as err:
                    st.error(f"⚠️ Error al redireccionar a Google: {err}")

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
                        "edad": "",
                        "genero": "Prefiero no decirlo",
                        "instagram": "",
                        "facebook": "",
                        "avatar": None
                    }
                    st.success("¡Cuenta creada exitosamente! Ya puede iniciar sesión.")

        with tab_invitado:
            st.subheader("Acceso Rápido")
            st.write("Explora el portal de datos en modo solo lectura sin crear una cuenta.")
            if st.button("🚀 Entrar como Invitado", use_container_width=True):
                st.session_state.autenticado = True
                st.session_state.usuario_actual = "Invitado"
                st.session_state.tipo_acceso = "Invitado"
                st.rerun()

# --- APLICACIÓN PRINCIPAL ---
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
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            st.session_state.autenticado = False
            st.session_state.usuario_actual = None
            st.session_state.tipo_acceso = None
            if hasattr(st, "logout"):
                try:
                    st.logout()
                except Exception:
                    pass
            st.rerun()

    st.title("🌿 BioExplora Chile: Portal de Biodiversidad")

    try:
        df = get_complete_data()
        
        tabs_lista = [
            "📌 Mapa Geográfico", 
            "📊 Estadísticas", 
            "🔍 Buscador de Especies",
            "📝 Reportar Avistamiento"
        ]
        if st.session_state.tipo_acceso == "Registrado":
            tabs_lista.append("⚙️ Mi Perfil")

        tabs_creados = st.tabs(tabs_lista)
        tab1 = tabs_creados[0]
        tab2 = tabs_creados[1]
        tab3 = tabs_creados[2]
        tab4 = tabs_creados[3]
        tab_perfil = tabs_creados[4] if len(tabs_creados) > 4 else None

        with tab1:
            st.subheader("Filtros del Mapa")
            c_reg, c_est = st.columns(2)
            
            with c_reg:
                regiones = ["Todas"] + sorted([r for r in df['Region'].unique() if r not in ['Sin Información']])
                selected_region = st.selectbox("Seleccione Región:", regiones)
                
            with c_est:
                filtro_identificacion = st.radio(
                    "Estado de Identificación:",
                    ["Todas", "Solo Identificadas", "No Identificadas"],
                    horizontal=True
                )
            
            df_map = df.dropna(subset=['Latitud', 'Longitud'])
            if selected_region != "Todas":
                df_map = df_map[df_map['Region'] == selected_region]
                
            if filtro_identificacion == "Solo Identificadas":
                df_map = df_map[df_map['NombreComun'] != 'Especie No Especificada']
            elif filtro_identificacion == "No Identificadas":
                df_map = df_map[df_map['NombreComun'] == 'Especie No Especificada']
                
            st.info(f"Registros georreferenciados en vista: {len(df_map):,}")
            
            if len(df_map) > 0:
                lat_center = df_map['Latitud'].mean()
                lon_center = df_map['Longitud'].mean()
                zoom_level = 4 if selected_region == "Todas" else 7

                mapa = crear_mapa_folium(df_map, lat_center, lon_center, zoom_level)
                st_folium(mapa, use_container_width=True, height=600, returned_objects=[])
            else:
                st.warning("No hay registros que coincidan con los filtros seleccionados.")
                
        with tab2:
            st.subheader("Métricas Generales")
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Registros", f"{len(df):,}")
            col2.metric("Especies Distintas", f"{df[df['NombreComun'] != 'Especie No Especificada']['NombreComun'].nunique():,}")
            col3.metric("Comunas Cubiertas", f"{df['Comuna'].nunique():,}")
            
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
                        yaxis={'categoryorder': 'total ascending'}, 
                        showlegend=False, 
                        height=400,
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='#cbd5e1')
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
                        yaxis={'categoryorder': 'total ascending'}, 
                        showlegend=False, 
                        height=400,
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='#cbd5e1')
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
                    st.info("🔴 Puntos rojos: Avistamientos de esta especie. ⚫ Puntos grises: Resto de registros en Chile.")
                    mapa_especie = crear_mapa_contraste_especie(df, df_esp)
                    st_folium(mapa_especie, use_container_width=True, height=500, returned_objects=[])

        with tab4:
            st.subheader("📝 Registrar un Nuevo Avistamiento de Biodiversidad")
            
            if st.session_state.tipo_acceso == "Invitado":
                st.warning("🔒 Los invitados están en modo sólo lectura. Para ingresar datos y subir de nivel, por favor cierra sesión e inicia sesión con una cuenta de usuario.")
            else:
                st.markdown("Sube una foto del avistamiento (**con GPS activado en tu cámara**) o indica la comuna. El registro pasará primero por una **fase de revisión y clasificación** en tu perfil.")
                
                with st.form("form_avistamiento"):
                    col_f1, col_f2 = st.columns(2)
                    
                    with col_f1:
                        input_especie = st.text_input("Especie observada (Nombre común o científico):", placeholder="Ej: Ranita de Antafaz, Pudú, Cóndor")
                        lista_regiones = sorted(list(COORDENADAS_REGIONES.keys()))
                        input_region = st.selectbox("Región:", lista_regiones)
                        input_comuna = st.text_input("Comuna:", placeholder="Ej: San Pablo, Hualpén")
                        
                    with col_f2:
                        foto_avistamiento = st.file_uploader("📷 Subir Fotografía (Extrae GPS automático)", type=["jpg", "jpeg", "png"])
                        input_notas = st.text_area("Notas / Observaciones de campo:", placeholder="Ej: Observado cerca de estero al atardecer.")
                    
                    btn_guardar = st.form_submit_button("📥 Enviar a Revisión", type="primary", use_container_width=True)
                    
                    if btn_guardar:
                        if not input_especie.strip() or not input_comuna.strip():
                            st.error("Por favor completa al menos la especie y la comuna.")
                        else:
                            nom_especie_limpio = input_especie.strip().title()
                            comuna_limpia = input_comuna.strip().title()
                            
                            lat_exif, lon_exif = None, None
                            if foto_avistamiento is not None:
                                lat_exif, lon_exif = obtener_coordenadas_exif(foto_avistamiento)

                            if lat_exif and lon_exif:
                                lat_final, lon_final = lat_exif, lon_exif
                            else:
                                lat_final = COORDENADAS_COMUNAS.get(comuna_limpia, COORDENADAS_REGIONES.get(input_region, (-33.4489, -70.6693)))[0]
                                lon_final = COORDENADAS_COMUNAS.get(comuna_limpia, COORDENADAS_REGIONES.get(input_region, (-33.4489, -70.6693)))[1]
                            
                            nuevo_pendiente = pd.DataFrame([{
                                'Region': input_region,
                                'Comuna': comuna_limpia,
                                'NombreComun': nom_especie_limpio,
                                'TipoEvento': 'Aporte Comunitario',
                                'Latitud': lat_final,
                                'Longitud': lon_final,
                                'AportadoPor': usr_actual,
                                'Notas': input_notas,
                                'Estado': 'Pendiente de Revisión'
                            }])
                            
                            st.session_state.df_pendientes_revision = pd.concat([st.session_state.df_pendientes_revision, nuevo_pendiente], ignore_index=True)
                            st.success("📝 ¡Avistamiento guardado en fase de revisión! Ve a tu sección **Mi Perfil** para validarlo y publicarlo.")

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
                            edad_actual = perfil_actual.get("edad", "")
                            nueva_edad = st.text_input("Edad:", value=str(edad_actual) if edad_actual else "")
                        with c_gen:
                            opciones_genero = ["Prefiero no decirlo", "Masculino", "Femenino", "Otro"]
                            gen_guardado = perfil_actual.get("genero", "Prefiero no decirlo")
                            idx_gen = opciones_genero.index(gen_guardado) if gen_guardado in opciones_genero else 0
                            nuevo_genero = st.selectbox("Género:", opciones_genero, index=idx_gen)

                        st.markdown("##### 🔗 Redes Sociales y Enlaces")
                        c_ig, c_fb = st.columns(2)
                        with c_ig:
                            nuevo_ig = st.text_input("Usuario de Instagram (ej: usuario_cl):", value=perfil_actual.get("instagram", ""))
                        with c_fb:
                            nuevo_fb = st.text_input("Perfil de Facebook (URL o nombre):", value=perfil_actual.get("facebook", ""))

                        nueva_foto_avatar = st.file_uploader("Actualizar Fotografía de Perfil:", type=["jpg", "jpeg", "png"])
                        
                        btn_guardar_perfil = st.form_submit_button("💾 Guardar Cambios de Perfil", type="primary", use_container_width=True)
                        
                        if btn_guardar_perfil:
                            avatar_a_guardar = nueva_foto_avatar if nueva_foto_avatar is not None else perfil_actual.get('avatar')
                            st.session_state.perfiles_usuarios[usr_actual] = {
                                "nombre": nuevo_nombre_publico.strip() or usr_actual,
                                "bio": nueva_bio.strip(),
                                "edad": nueva_edad.strip(),
                                "genero": nuevo_genero,
                                "instagram": nuevo_ig.strip().replace("@", ""),
                                "facebook": nuevo_fb.strip(),
                                "avatar": avatar_a_guardar
                            }
                            st.success("¡Perfil actualizado correctamente!")
                            st.rerun()

                st.markdown("---")
                st.markdown("### 📥 Bandeja de Revisión y Clasificación de Avistamientos")
                st.write("Clasifica o ajusta tus registros pendientes antes de publicarlos oficialmente en el mapa general del portal.")
                
                mis_pendientes = st.session_state.df_pendientes_revision[
                    (st.session_state.df_pendientes_revision['AportadoPor'] == usr_actual) & 
                    (st.session_state.df_pendientes_revision['Estado'] == 'Pendiente de Revisión')
                ]
                
                if not mis_pendientes.empty:
                    for idx, row in mis_pendientes.iterrows():
                        with st.expander(f"🔍 Revisar: {row['NombreComun']} ({row['Comuna']}, {row['Region']})"):
                            with st.form(f"form_revision_{idx}"):
                                rev_especie = st.text_input("Confirmar / Corregir Especie:", value=row['NombreComun'], key=f"rev_esp_{idx}")
                                rev_comuna = st.text_input("Confirmar / Corregir Comuna:", value=row['Comuna'], key=f"rev_com_{idx}")
                                rev_notas = st.text_area("Notas de campo:", value=row['Notas'], key=f"rev_not_{idx}")
                                
                                c_btn1, c_btn2 = st.columns(2)
                                with c_btn1:
                                    btn_publicar = st.form_submit_button("🚀 Validar y Publicar Oficialmente", type="primary", use_container_width=True)
                                with c_btn2:
                                    btn_descartar = st.form_submit_button("🗑️ Descartar Registro", use_container_width=True)
                                
                                if btn_publicar:
                                    comuna_limpia = rev_comuna.strip().title()
                                    lat_f = COORDENADAS_COMUNAS.get(comuna_limpia, (row['Latitud'], row['Longitud']))[0]
                                    lon_f = COORDENADAS_COMUNAS.get(comuna_limpia, (row['Latitud'], row['Longitud']))[1]

                                    reg_oficial = pd.DataFrame([{
                                        'Region': row['Region'],
                                        'Comuna': comuna_limpia,
                                        'NombreComun': rev_especie.strip().title(),
                                        'TipoEvento': 'Aporte Comunitario',
                                        'Latitud': lat_f,
                                        'Longitud': lon_f,
                                        'AportadoPor': usr_actual
                                    }])
                                    st.session_state.df_nuevos_registros = pd.concat([st.session_state.df_nuevos_registros, reg_oficial], ignore_index=True)
                                    st.session_state.df_pendientes_revision.loc[idx, 'Estado'] = 'Publicado'
                                    st.session_state.conteo_avistamientos[usr_actual] = st.session_state.conteo_avistamientos.get(usr_actual, 0) + 1
                                    
                                    st.balloons()
                                    st.success("¡Registro validado y publicado con éxito en el mapa!")
                                    st.rerun()

                                if btn_descartar:
                                    st.session_state.df_pendientes_revision.loc[idx, 'Estado'] = 'Descartado'
                                    st.warning("El registro ha sido descartado.")
                                    st.rerun()
                else:
                    st.info("No tienes avistamientos pendientes de revisión en este momento.")

                st.markdown("---")
                st.markdown("### 📋 Tus Avistamientos Publicados Oficialmente")
                if not st.session_state.df_nuevos_registros.empty and 'AportadoPor' in st.session_state.df_nuevos_registros.columns:
                    mis_aportes = st.session_state.df_nuevos_registros[st.session_state.df_nuevos_registros['AportadoPor'] == usr_actual]
                    if not mis_aportes.empty:
                        st.dataframe(mis_aportes[['Region', 'Comuna', 'NombreComun', 'TipoEvento', 'Latitud', 'Longitud']], use_container_width=True)
                    else:
                        st.info("Aún no tienes aportes comunitarios publicados.")
                else:
                    st.info("Aún no tienes aportes comunitarios publicados.")

    except Exception as e:
        st.error(f"Error en la aplicación: {e}")

# --- ENRUTADOR PRINCIPAL ---
if st.session_state.autenticado:
    mostrar_aplicacion_principal()
else:
    mostrar_pantalla_login()
