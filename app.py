import streamlit as st
import pandas as pd
import plotly.express as px
import folium
import hashlib
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from streamlit_folium import st_folium
import requests

# --- CONFIGURACIÓN INICIAL DE LA PÁGINA ---
st.set_page_config(
    page_title="BioExplora Chile",
    page_icon="🌿",
    layout="wide"
)

# --- ESTILOS CSS UNIFICADOS ---
st.markdown("""
<style>
    .stApp {
        background-image: linear-gradient(rgba(11, 19, 43, 0.90), rgba(11, 19, 43, 0.90)), 
                          url("https://images.unsplash.com/photo-1518531933037-91b2f5f229cc?auto=format&fit=crop&w=1920&q=80");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        color: #e2e8f0;
    }
    p, span, label, div { color: #cbd5e1; }
    h1, h2, h3, h4, h5, h6 { color: #f8fafc !important; }
    div.stMarkdown, div.stForm, div.stTabs {
        background-color: #1c2541;
        border-radius: 12px;
        padding: 5px;
    }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; background-color: #0b132b; padding: 10px; border-radius: 10px; }
    .stTabs [data-baseweb="tab"] { background-color: #1c2541; border-radius: 8px; color: #94a3b8; font-weight: 600; border: 1px solid #3a506b; }
    .stTabs [aria-selected="true"] { background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important; color: white !important; border: none !important; }
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
        background: linear-gradient(135deg, #059669 100%, #047857 100%);
        transform: translateY(-2px);
    }
    div[data-testid="stMetric"] {
        background-color: #1c2541;
        padding: 16px;
        border-radius: 12px;
        border: 1px solid #3a506b;
    }
    div.stTextInput > div > div > input, div.stSelectbox > div > div > div, div.stTextArea > div > div > textarea {
        background-color: #0b132b;
        color: #f8fafc;
        border-radius: 8px;
        border: 1px solid #3a506b;
    }
    section[data-testid="stSidebar"] { background-color: #0b132b; border-right: 1px solid #1c2541; }
</style>
""", unsafe_allow_html=True)

# --- INICIALIZACIÓN DE ESTADOS DE SESIÓN ---
if "bd_usuarios" not in st.session_state:
    st.session_state.bd_usuarios = {
        "admin@bioexplora.cl": hashlib.sha256("123456".encode()).hexdigest(),
        "usuario@bioexplora.cl": hashlib.sha256("123456".encode()).hexdigest()
    }

if "perfiles_usuarios" not in st.session_state:
    st.session_state.perfiles_usuarios = {
        "admin@bioexplora.cl": {"nombre": "Administrador", "bio": "Gestor oficial del portal BioExplora Chile.", "instagram": "bioexplora_cl"},
        "usuario@bioexplora.cl": {"nombre": "Naturalista Base", "bio": "Apasionado por la flora y fauna chilena.", "instagram": "naturalista_cl"}
    }

if "conteo_avistamientos" not in st.session_state:
    st.session_state.conteo_avistamientos = {"admin@bioexplora.cl": 12, "usuario@bioexplora.cl": 4}

if "df_nuevos_registros" not in st.session_state:
    st.session_state.df_nuevos_registros = pd.DataFrame(columns=['Region', 'Comuna', 'NombreComun', 'TipoEvento', 'Latitud', 'Longitud', 'AportadoPor'])

if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.usuario_actual = None
    st.session_state.tipo_acceso = None

def hash_pass(password):
    return hashlib.sha256(password.encode()).hexdigest()

def obtener_rango_usuario(cantidad):
    if cantidad >= 11: return "🏆 Naturalista Experto", "gold"
    elif cantidad >= 6: return "🌿 Rastreador de Biodiversidad", "green"
    elif cantidad >= 3: return "🥾 Explorador de Campo", "blue"
    else: return "🐣 Observador Inicial", "gray"

# --- DICCIONARIOS Y EXIF ---
COORDENADAS_COMUNAS = {
    "Arica": (-18.4783, -70.3126), "Iquique": (-20.2133, -70.1503), "Antofagasta": (-23.6509, -70.3975),
    "La Serena": (-29.9027, -71.2520), "Valparaíso": (-33.0472, -71.6127), "Santiago": (-33.4489, -70.6693),
    "Rancagua": (-34.1701, -70.7444), "Talca": (-35.4264, -71.6554), "Concepción": (-36.8270, -73.0503),
    "Temuco": (-38.7359, -72.5904), "Valdivia": (-39.8142, -73.2459), "Puerto Montt": (-41.4689, -72.9411),
    "Punta Arenas": (-53.1638, -70.9171)
}

COORDENADAS_REGIONES = {
    "Metropolitana": (-33.4489, -70.6693), "Valparaíso": (-33.0472, -71.6127), "Biobío": (-36.8270, -73.0503)
}

MAPEO_NOMBRES_CIENTIFICOS = {
    "ranita de antifaz": "Batrachyla taeniata", "sapito 4 ojos": "Pleurodema thaul",
    "zorro culpeo": "Lycalopex culpaeus", "puma": "Puma concolor", "pudú": "Pudu puda"
}

def obtener_nombre_cientifico_resuelto(nombre):
    return MAPEO_NOMBRES_CIENTIFICOS.get(str(nombre).strip().lower(), nombre)

@st.cache_data
def load_base_data():
    try:
        df_raw = pd.read_parquet("datos_bioexplora_light.parquet")
    except Exception:
        df_raw = pd.DataFrame({
            'region': ['Metropolitana', 'Valparaíso', 'Biobío'],
            'comuna': ['Santiago', 'Valparaíso', 'Concepción'],
            'nombre': ['Zorro Culpeo', 'Pudú', 'Monito del Monte'],
            'lat': [-33.4489, -33.0472, -36.8270],
            'lon': [-70.6693, -71.6127, -73.0503],
            'origen': ['Monitoreo', 'Aporte Comunitario', 'Monitoreo']
        })
    df = pd.DataFrame()
    for col in df_raw.columns:
        df[str(col).strip().lower()] = df_raw[col].astype(str)

    df['Region'] = df.get('region', pd.Series(['Metropolitana']*len(df))).str.strip().str.title()
    df['Comuna'] = df.get('comuna', pd.Series(['Santiago']*len(df))).str.strip().str.title()
    df['NombreComun'] = df.get('nombre', pd.Series(['Especie']*len(df))).str.strip().str.title()
    df['TipoEvento'] = df.get('origen', pd.Series(['Registro']*len(df))).str.strip()
    df['Latitud'] = pd.to_numeric(df.get('lat', -33.4489), errors='coerce')
    df['Longitud'] = pd.to_numeric(df.get('lon', -70.6693), errors='coerce')
    return df

def get_complete_data():
    base_df = load_base_data()
    if not st.session_state.df_nuevos_registros.empty:
        cols_base = ['Region', 'Comuna', 'NombreComun', 'TipoEvento', 'Latitud', 'Longitud']
        return pd.concat([base_df, st.session_state.df_nuevos_registros[cols_base]], ignore_index=True)
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

def obtener_coordenadas_exif(image_file):
    try:
        image = Image.open(image_file)
        exif_data = image._getexif()
        if not exif_data: return None, None
        gps_info = {}
        for tag_id, value in exif_data.items():
            tag = TAGS.get(tag_id, tag_id)
            if tag == "GPSInfo":
                for t in value:
                    gps_info[GPSTAGS.get(t, t)] = value[t]
        if not gps_info: return None, None

        def conv(val):
            return float(val[0]) + (float(val[1]) / 60.0) + (float(val[2]) / 3600.0)

        lat = conv(gps_info['GPSLatitude'])
        if gps_info.get('GPSLatitudeRef') != 'N': lat = -lat
        lon = conv(gps_info['GPSLongitude'])
        if gps_info.get('GPSLongitudeRef') != 'E': lon = -lon
        return lat, lon
    except Exception:
        return None, None

def crear_mapa_folium(df_puntos, lat_centro, lon_centro, zoom):
    m = folium.Map(location=[lat_centro, lon_centro], zoom_start=zoom, tiles="CartoDB dark_matter")
    for _, row in df_puntos.iterrows():
        folium.CircleMarker(
            location=[row['Latitud'], row['Longitud']], radius=7,
            popup=f"{row['NombreComun']} - {row['Comuna']}",
            color="green", fill=True, fill_color="green", fill_opacity=0.85
        ).add_to(m)
    return m

# --- PANTALLA DE LOGIN ---
def mostrar_pantalla_login():
    st.markdown("<h1 style='text-align: center;'>🌿 BioExplora Chile</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Portal de Monitoreo de Biodiversidad Silvestre</p>", unsafe_allow_html=True)
    st.markdown("---")

    _, col2, _ = st.columns([1, 2, 1])

    with col2:
        tab_login, tab_registro, tab_invitado = st.tabs(["🔐 Iniciar Sesión", "📝 Crear Cuenta", "👤 Invitado"])

        with tab_login:
            st.subheader("Acceso a tu cuenta")
            
            if st.button("🌐 Continuar con Google", use_container_width=True):
                email_g = "naturalista.google@gmail.com"
                st.session_state.autenticado = True
                st.session_state.usuario_actual = email_g
                st.session_state.tipo_acceso = "Registrado"
                if email_g not in st.session_state.perfiles_usuarios:
                    st.session_state.perfiles_usuarios[email_g] = {"nombre": "Usuario Google", "bio": "Naturalista vía Google", "instagram": ""}
                    st.session_state.conteo_avistamientos[email_g] = 0
                st.rerun()

            st.markdown("<p style='text-align: center;'>O con tus credenciales:</p>", unsafe_allow_html=True)
            email_login = st.text_input("Correo Electrónico", key="l_email")
            pass_login = st.text_input("Contraseña", type="password", key="l_pass")
            
            if st.button("Ingresar con Correo", use_container_width=True, type="primary"):
                hashed = hash_pass(pass_login)
                if email_login in st.session_state.bd_usuarios and st.session_state.bd_usuarios[email_login] == hashed:
                    st.session_state.autenticado = True
                    st.session_state.usuario_actual = email_login
                    st.session_state.tipo_acceso = "Registrado"
                    st.rerun()
                else:
                    st.error("Correo o contraseña incorrectos.")

        with tab_registro:
            st.subheader("Crear nueva cuenta")
            r_email = st.text_input("Correo", key="r_email")
            r_pass = st.text_input("Contraseña", type="password", key="r_pass")
            r_pass_conf = st.text_input("Confirmar Contraseña", type="password", key="r_pass_conf")
            if st.button("Registrarse", use_container_width=True):
                if not r_email or not r_pass:
                    st.warning("Complete todos los campos.")
                elif r_pass != r_pass_conf:
                    st.error("Las contraseñas no coinciden.")
                elif r_email in st.session_state.bd_usuarios:
                    st.warning("El correo ya está registrado.")
                else:
                    st.session_state.bd_usuarios[r_email] = hash_pass(r_pass)
                    st.session_state.conteo_avistamientos[r_email] = 0
                    st.session_state.perfiles_usuarios[r_email] = {"nombre": r_email.split("@")[0].title(), "bio": "Entusiasta de la naturaleza.", "instagram": ""}
                    st.success("¡Cuenta creada con éxito! Ya puedes iniciar sesión.")

        with tab_invitado:
            st.subheader("Modo Invitado")
            st.write("Explora el portal de datos en modo lectura.")
            if st.button("🚀 Entrar como Invitado", use_container_width=True):
                st.session_state.autenticado = True
                st.session_state.usuario_actual = "Invitado"
                st.session_state.tipo_acceso = "Invitado"
                st.rerun()

# --- APLICACIÓN PRINCIPAL ---
def mostrar_aplicacion_principal():
    usr = st.session_state.usuario_actual
    perfil = st.session_state.perfiles_usuarios.get(usr, {"nombre": usr, "bio": "", "instagram": ""})

    with st.sidebar:
        st.markdown(f"👤 **Usuario:** `{perfil.get('nombre')}`")
        st.markdown(f"🏷️ **Tipo:** `{st.session_state.tipo_acceso}`")
        
        if st.session_state.tipo_acceso == "Registrado":
            cant_obs = st.session_state.conteo_avistamientos.get(usr, 0)
            rango, _ = obtener_rango_usuario(cant_obs)
            st.markdown("---")
            st.markdown(f"**Rango:** {rango}")
            st.markdown(f"**Avistamientos:** `{cant_obs}`")

        st.markdown("---")
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            st.session_state.autenticado = False
            st.session_state.usuario_actual = None
            st.session_state.tipo_acceso = None
            st.rerun()

    st.title("🌿 BioExplora Chile: Portal de Biodiversidad")
    df = get_complete_data()

    tabs_lista = ["📌 Mapa Geográfico", "📊 Estadísticas", "🔍 Buscador de Especies", "📝 Reportar Avistamiento"]
    if st.session_state.tipo_acceso == "Registrado":
        tabs_lista.append("⚙️ Mi Perfil")

    tabs_creados = st.tabs(tabs_lista)
    tab1, tab2, tab3, tab4 = tabs_creados[0], tabs_creados[1], tabs_creados[2], tabs_creados[3]
    tab_perfil = tabs_creados[4] if len(tabs_creados) > 4 else None

    with tab1:
        st.subheader("Mapa de Avistamientos")
        df_map = df.dropna(subset=['Latitud', 'Longitud'])
        if len(df_map) > 0:
            mapa = crear_mapa_folium(df_map, -33.4489, -70.6693, 5)
            st_folium(mapa, use_container_width=True, height=550, returned_objects=[])
        else:
            st.warning("No hay registros georreferenciados.")

    with tab2:
        st.subheader("Métricas Generales")
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Registros", f"{len(df):,}")
        c2.metric("Especies Únicas", f"{df['NombreComun'].nunique():,}")
        c3.metric("Comunas Cubiertas", f"{df['Comuna'].nunique():,}")

    with tab3:
        st.subheader("Buscador y Ficha de Especie")
        busqueda = st.text_input("Buscar especie:", "zorro")
        if busqueda.strip():
            df_coincidencias = df[df['NombreComun'].str.contains(busqueda, case=False, na=False)]
            especies_halladas = sorted(df_coincidencias['NombreComun'].unique())
            if especies_halladas:
                especie_sel = st.selectbox("Seleccione especie:", especies_halladas)
                if especie_sel:
                    tax, img_url = obtener_datos_gbif(especie_sel)
                    c_inf1, c_inf2 = st.columns(2)
                    with c_inf1:
                        if img_url: st.image(img_url, use_container_width=True)
                        else: st.info("Sin imagen disponible.")
                    with c_inf2:
                        if tax:
                            st.markdown(f"**Nombre Científico:** *{tax.get('Nombre Científico')}*")
                            st.markdown(f"**Reino:** {tax.get('Reino')}")
                            st.markdown(f"**Clase:** {tax.get('Clase')}")
                            st.markdown(f"**Familia:** {tax.get('Familia')}")
            else:
                st.warning("No se encontraron coincidencias.")

    with tab4:
        st.subheader("Reportar Nuevo Avistamiento")
        with st.form("form_rep"):
            c_r1, c_r2 = st.columns(2)
            with c_r1:
                reg_rep = st.selectbox("Región", ["Metropolitana", "Valparaíso", "Biobío"])
                com_rep = st.text_input("Comuna")
            with c_r2:
                esp_rep = st.text_input("Especie")
                tipo_rep = st.selectbox("Tipo", ["Aporte Comunitario", "Monitoreo"])
            
            foto = st.file_uploader("Foto (opcional, extrae GPS)", type=["jpg", "png"])
            lat_in = st.number_input("Latitud", value=-33.4489, format="%.6f")
            lon_in = st.number_input("Longitud", value=-70.6693, format="%.6f")
            
            if st.form_submit_button("Enviar Reporte"):
                lat_f, lon_f = lat_in, lon_in
                if foto:
                    lat_exif, lon_exif = obtener_coordenadas_exif(foto)
                    if lat_exif and lon_exif:
                        lat_f, lon_f = lat_exif, lon_exif
                        st.success("📍 ¡Coordenadas GPS extraídas de la imagen!")
                
                nuevo = pd.DataFrame([{
                    'Region': reg_rep, 'Comuna': com_rep.title(), 'NombreComun': esp_rep.title(),
                    'TipoEvento': tipo_rep, 'Latitud': lat_f, 'Longitud': lon_f, 'AportadoPor': usr
                }])
                st.session_state.df_nuevos_registros = pd.concat([st.session_state.df_nuevos_registros, nuevo], ignore_index=True)
                if st.session_state.tipo_acceso == "Registrado":
                    st.session_state.conteo_avistamientos[usr] = st.session_state.conteo_avistamientos.get(usr, 0) + 1
                st.success("🎉 ¡Avistamiento guardado con éxito!")

    if tab_perfil and st.session_state.tipo_acceso == "Registrado":
        with tab_perfil:
            st.subheader("Configuración de Perfil")
            with st.form("form_perfil"):
                n_nom = st.text_input("Nombre o Alias", value=perfil.get('nombre', ''))
                n_bio = st.text_area("Biografía", value=perfil.get('bio', ''))
                n_ins = st.text_input("Instagram", value=perfil.get('instagram', ''))
                if st.form_submit_button("Guardar Cambios"):
                    st.session_state.perfiles_usuarios[usr]['nombre'] = n_nom
                    st.session_state.perfiles_usuarios[usr]['bio'] = n_bio
                    st.session_state.perfiles_usuarios[usr]['instagram'] = n_ins
                    st.success("✨ ¡Perfil actualizado!")

if not st.session_state.autenticado:
    mostrar_pantalla_login()
else:
    mostrar_aplicacion_principal()
