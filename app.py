import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import st_folium
import requests
import hashlib

st.set_page_config(
    page_title="BioExplora Chile",
    page_icon="🌿",
    layout="wide"
)

# --- BASE DE DATOS FICTICIA / TEMPORAL DE USUARIOS ---
if "bd_usuarios" not in st.session_state:
    st.session_state.bd_usuarios = {
        "admin@bioexplora.cl": hashlib.sha256("123456".encode()).hexdigest()
    }

if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
if "usuario_actual" not in st.session_state:
    st.session_state.usuario_actual = None
if "tipo_acceso" not in st.session_state:
    st.session_state.tipo_acceso = None

def hash_pass(password):
    return hashlib.sha256(password.encode()).hexdigest()

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
    "ranita de hojarasca de calcarata": "Eupsophus calcaratus",
    "sapito 4 ojos": "Pleurodema thaul",
    "sapito cuatro ojos": "Pleurodema thaul",
    "sapito de cuatro ojos": "Pleurodema thaul",
    "ranita de darwin": "Rhinoderma darwinii",
    "sapo de rhensu": "Insuetophrynus acarpicus",
    "sapo de atacama": "Rhinella atacamensis",
    "sapo espinoso": "Rhinella spinulosa",
    "rana chilena": "Calyptocephalella gayi",
    "zorro culpeo": "Lycalopex culpaeus",
    "zorro chilla": "Lycalopex griseus",
    "zorro de darwin": "Lycalopex fulvipes",
    "puma": "Puma concolor",
    "huemul": "Hippocamelus bisulcus",
    "pudú": "Pudu puda",
    "pudu": "Pudu puda",
    "monito del monte": "Dromiciops gliroides",
    "guanaco": "Lama guanicoe",
    "vicuña": "Vicugna vicugna",
    "chinchilla cordillerana": "Chinchilla chinchilla",
    "taruca": "Hippocamelus antisensis",
    "gato colocolo": "Leopardus colocolo",
    "guiña": "Leopardus guigna",
    "cóndor andino": "Vultur gryphus",
    "condor andino": "Vultur gryphus",
    "condor": "Vultur gryphus",
    "flamenco chileno": "Phoenicopterus chilensis",
    "carpintero negro": "Campephilus magellanicus",
    "pingüino de humboldt": "Spheniscus humboldti",
    "pinguino de humboldt": "Spheniscus humboldti",
    "pingüino de magallanes": "Spheniscus magellanicus",
    "loica": "Leistes loyca",
    "chucao": "Scelorchilus rubecula",
    "hued-hued": "Pteroptochos castaneus",
    "rayadito": "Aphrastura spinicauda",
    "lagartija esbelta": "Liolaemus tenuis",
    "lagartija nítida": "Liolaemus nitidus",
    "culebra de cola larga": "Philodryas chamissonis",
    "araucaria": "Araucaria araucana",
    "copihue": "Lapageria rosea",
    "litre": "Lithraea caustica",
    "alerce": "Fitzroya cupressoides",
    "quillay": "Quillaja saponaria",
    "peumo": "Cryptocarya alba"
}

def obtener_nombre_cientifico_resuelto(nombre_ingresado):
    if not nombre_ingresado:
        return nombre_ingresado
    limpio = str(nombre_ingresado).strip().lower()
    return MAPEO_NOMBRES_CIENTIFICOS.get(limpio, nombre_ingresado)

@st.cache_data
def load_data():
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

        inat_url = f"https://api.inaturalist.org/v1/taxa?q={nombre_query}&per_page=1"
        inat_res = requests.get(inat_url, timeout=4)
        if inat_res.status_code == 200:
            inat_data = inat_res.json().get('results', [])
            if inat_data:
                taxon_obj = inat_data[0]
                if not imagen_url and 'default_photo' in taxon_obj:
                    photo_info = taxon_obj['default_photo']
                    if photo_info and 'medium_url' in photo_info:
                        imagen_url = photo_info['medium_url']
                if not taxonomia:
                    ancestors = taxon_obj.get('ancestors', [])
                    tax_map = {a.get('rank'): a.get('name') for a in ancestors}
                    tax_map[taxon_obj.get('rank')] = taxon_obj.get('name')
                    taxonomia = {
                        "Reino": tax_map.get("kingdom", "Animalia"),
                        "Filo": tax_map.get("phylum", "Chordata"),
                        "Clase": tax_map.get("class", "Desconocido"),
                        "Orden": tax_map.get("order", "Desconocido"),
                        "Familia": tax_map.get("family", "Desconocido"),
                        "Género": tax_map.get("genus", "Desconocido"),
                        "Nombre Científico": taxon_obj.get("name", nombre_query)
                    }
    except Exception:
        pass
    return taxonomia, imagen_url

def crear_mapa_folium(df_puntos, lat_centro, lon_centro, zoom):
    m = folium.Map(location=[lat_centro, lon_centro], zoom_start=zoom, tiles="OpenStreetMap")
    folium.TileLayer('CartoDB positron', name='Claro Minimalista').add_to(m)
    folium.TileLayer('CartoDB dark_matter', name='Oscuro').add_to(m)
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri',
        name='Satelital / Geográfico'
    ).add_to(m)

    for _, row in df_puntos.iterrows():
        color_marker = "green" if row.get("TipoEvento") == "Monitoreo" else "orange"
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
            
            if st.button("Ingresar", use_container_width=True, type="primary"):
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
            try:
                if hasattr(st, "login"):
                    if st.button("🌐 Continuar con Google", use_container_width=True):
                        st.login("google")
                else:
                    st.info("💡 La autenticación nativa de Google está disponible al activar secretos OAuth en Streamlit Cloud.")
            except Exception:
                st.info("💡 Configure los secretos de Google Client OAuth en Streamlit Cloud para activar este botón.")

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
                    st.success("¡Cuenta creada exitosamente! Ya puede iniciar sesión en la pestaña superior.")

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
    with st.sidebar:
        st.markdown(f"👤 **Usuario:** `{st.session_state.usuario_actual}`")
        st.markdown(f"🏷️ **Perfil:** `{st.session_state.tipo_acceso}`")
        st.markdown("---")
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            st.session_state.autenticado = False
            st.session_state.usuario_actual = None
            st.session_state.tipo_acceso = None
            st.rerun()

    st.title("🌿 BioExplora Chile: Portal de Biodiversidad")
    st.markdown("Visualizador interactivo de monitoreo y rescates a nivel nacional.")

    try:
        df = load_data()
        
        tab1, tab2, tab3 = st.tabs(["📌 Mapa Geográfico", "📊 Estadísticas", "🔍 Buscador de Especies"])

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
                st_folium(mapa, use_container_width=True, height=650, returned_objects=[])
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
                        df_esp_chart,
                        x='Cantidad',
                        y='Especie',
                        orientation='h',
                        color='Cantidad',
                        color_continuous_scale='Greens',
                        text_auto=True
                    )
                    fig_esp.update_layout(yaxis={'categoryorder': 'total ascending'}, showlegend=False, height=450)
                    st.plotly_chart(fig_esp, use_container_width=True)

            with c2:
                st.markdown("### Top 10 Comunas con Mayor Actividad")
                df_com_chart = df['Comuna'].value_counts().head(10).reset_index()
                df_com_chart.columns = ['Comuna', 'Cantidad']
                
                if not df_com_chart.empty:
                    fig_com = px.bar(
                        df_com_chart,
                        x='Cantidad',
                        y='Comuna',
                        orientation='h',
                        color='Cantidad',
                        color_continuous_scale='Teal',
                        text_auto=True
                    )
                    fig_com.update_layout(yaxis={'categoryorder': 'total ascending'}, showlegend=False, height=450)
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
                        especie_seleccionada = st.selectbox(
                            "2. Seleccione la especie exacta encontrada:",
                            especies_halladas
                        )
                    else:
                        especie_seleccionada = None
                        st.warning("No se encontraron especies específicas con ese término.")
                
                if especie_seleccionada:
                    df_esp = df[df['NombreComun'] == especie_seleccionada]
                    st.success(f"Mostrando información para **{especie_seleccionada}** ({len(df_esp):,} registros hallados).")
                    
                    st.markdown("---")
                    st.markdown("### 🧬 Ficha Taxonómica y Registro Fotográfico")
                    tax, img_url = obtener_datos_gbif(especie_seleccionada)
                    
                    col_info_a, col_info_b = st.columns([1, 1])
                    
                    with col_info_a:
                        if img_url:
                            st.image(img_url, caption=f"Fotografía de referencia: {especie_seleccionada}", use_container_width=True)
                        else:
                            st.info("📷 No se encontró fotografía pública registrada para esta especie.")
                            
                    with col_info_b:
                        if tax:
                            st.markdown(f"**Nombre Científico:** *{tax.get('Nombre Científico')}*")
                            st.markdown(f"• **Reino:** {tax.get('Reino')}")
                            st.markdown(f"• **Filo:** {tax.get('Filo')}")
                            st.markdown(f"• **Clase:** {tax.get('Clase')}")
                            st.markdown(f"• **Orden:** {tax.get('Orden')}")
                            st.markdown(f"• **Familia:** {tax.get('Familia')}")
                            st.markdown(f"• **Género:** {tax.get('Género')}")
                        else:
                            st.write("Sin datos taxonómicos externos disponibles.")
                    st.markdown("---")
                    
                    col_a, col_b = st.columns([1, 2])
                    
                    with col_a:
                        st.markdown("#### Presencia por Comuna")
                        df_comuna_esp = df_esp['Comuna'].value_counts().reset_index()
                        df_comuna_esp.columns = ['Comuna', 'Registros']
                        st.dataframe(df_comuna_esp, use_container_width=True, height=200)
                        
                        st.markdown("#### Distribución por Región")
                        df_reg_esp = df_esp['Region'].value_counts().reset_index()
                        df_reg_esp.columns = ['Región', 'Registros']
                        st.dataframe(df_reg_esp, use_container_width=True, height=180)

                    with col_b:
                        st.markdown("#### Ubicación de Avistamientos")
                        df_esp_geo = df_esp.dropna(subset=['Latitud', 'Longitud'])
                        
                        if len(df_esp_geo) > 0:
                            lat_c = df_esp_geo['Latitud'].mean()
                            lon_c = df_esp_geo['Longitud'].mean()
                            zoom_dinamico = 9 if len(df_esp_geo) <= 3 else 6
                            
                            mapa_esp = crear_mapa_folium(df_esp_geo, lat_c, lon_c, zoom_dinamico)
                            st_folium(mapa_esp, use_container_width=True, height=450, returned_objects=[])
                        else:
                            st.warning("No fue posible ubicar geográficamente este registro.")

                    st.markdown("#### Detalle de Registros Encontrados")
                    cols_mostrar = [c for c in ['NombreComun', 'Region', 'Comuna', 'TipoEvento', 'Latitud', 'Longitud'] if c in df_esp.columns]
                    st.dataframe(df_esp[cols_mostrar], use_container_width=True)

    except Exception as e:
        st.error(f"Error al cargar la base de datos: {e}")

# --- ENRUTADOR PRINCIPAL ---
if st.session_state.autenticado:
    mostrar_aplicacion_principal()
else:
    mostrar_pantalla_login()
