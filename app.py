import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import requests
import random

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="BioExplora Chile: Portal de Biodiversidad",
    page_icon="🌿",
    layout="wide",
)

# --- CSS PERSONALIZADO PARA PESTAÑAS Y DISEÑO ---
st.markdown("""
    <style>
    /* Fondo general de la aplicación */
    .stApp {
        background-color: #0b1310;
        color: #e0e8e2;
    }
    
    /* Contenedores y tarjetas */
    div[data-testid="stVerticalBlock"] > div[style*="background-color"] {
        border-radius: 10px;
    }

    /* ESTILO MEJORADO PARA LAS PESTAÑAS (TABS) */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #121c17;
        padding: 10px;
        border-radius: 12px;
        border: 1px solid #1e3027;
    }

    .stTabs [data-baseweb="tab"] {
        height: 45px;
        background-color: #182821;
        border-radius: 8px;
        color: #a3b8ac;
        font-weight: 600;
        padding: 0 16px;
        border: 1px solid transparent;
        transition: all 0.3s ease;
    }

    /* Pestaña activa claramente destacada con fondo y borde */
    .stTabs [aria-selected="true"] {
        background-color: #2b4d3f !important;
        color: #ffffff !important;
        border: 1px solid #4da679 !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
    }

    .stTabs [data-baseweb="tab"]:hover {
        background-color: #20362c;
        color: #ffffff;
    }
    </style>
""", unsafe_allow_html=True)

# --- CARGA DE DATOS (Simulada / Estructura Base) ---
@st.cache_data
def load_data():
    # Aquí iría tu carga real: pd.read_parquet('tu_archivo.parquet')
    # Generamos un DataFrame de ejemplo robusto si no está presente el archivo
    data = {
        'especie': ['Guanaco', 'Jaiba Marmola', 'Puma', 'Zorro Culpeo', 'Cometocino de Gay', 'Monito del Monte'],
        'region': ['Coquimbo', 'Valparaíso', 'Metropolitana', 'Biobío', 'Araucanía', 'Los Lagos'],
        'comuna': ['Los Vilos', 'Valparaíso', 'San José de Maipo', 'Concepción', 'Temuco', 'Valdivia'],
        'estado': ['Solo Identificadas', 'Solo Identificadas', 'No Identificadas', 'Solo Identificadas', 'Solo Identificadas', 'No Identificadas'],
        'lat': [-31.9, -33.0, -33.8, -36.8, -38.7, -39.8],
        'lon': [-71.5, -71.6, -70.3, -73.0, -72.6, -73.2]
    }
    return pd.DataFrame(data)

df = load_data()

# --- TÍTULO PRINCIPAL ---
st.markdown("## 🌿 BioExplora Chile: Portal de Biodiversidad")
st.markdown("---")

# --- NAVEGACIÓN POR PESTAÑAS ---
tab_mapa, tab_curiosidad, tab_stats, tab_buscador, tab_reportar, tab_perfil = st.tabs([
    "📍 Mapa Geográfico", 
    "✨ Rincón de Curiosidad", 
    "📊 Estadísticas", 
    "🔍 Buscador de Especies", 
    "📝 Reportar Avistamiento", 
    "⚙️ Mi Perfil"
])

# --- 1. MAPA GEOGRÁFICO ---
with tab_mapa:
    st.markdown("### Filtros del Mapa de Avistamientos")
    col1, col2 = st.columns([2, 2])
    with col1:
        regiones = ["Todas"] + list(df['region'].unique())
        sel_region = st.selectbox("Seleccione Región:", regiones)
    with col2:
        sel_estado = st.radio("Estado:", ["Todas", "Solo Identificadas", "No Identificadas"], horizontal=True)
    
    st.info(f"Registros georreferenciados en vista: {len(df):,}".replace(",", "."))
    
    # Mapa base con Folium
    m = folium.Map(location=[-35.6751, -71.5430], zoom_start=5, tiles="CartoDB positron")
    for _, row in df.iterrows():
        folium.CircleMarker(
            location=[row['lat'], row['lon']],
            radius=6,
            color="#2b4d3f",
            fill=True,
            fill_color="#4da679",
            fill_opacity=0.7,
            popup=f"{row['especie']} ({row['comuna']})"
        ).add_to(m)
    st_folium(m, height=450, use_container_width=True)

# --- 2. RINCON DE CURIOSIDAD (Con solución de carga de fotos) ---
with tab_curiosidad:
    st.markdown("### ✨ Rincón de Curiosidad y Descubrimiento Silvestre")
    st.markdown("Cada rincón de Chile guarda secretos naturales fascinantes. Descubre una especie al azar y despierta tu curiosidad:")
    
    if "especie_azar" not in st.session_state:
        st.session_state["especie_azar"] = random.choice(df['especie'].tolist())

    if st.button("🎲 ¡Sorpréndeme con una Especie!"):
        st.session_state["especie_azar"] = random.choice(df['especie'].tolist())
        st.rerun()

    especie_actual = st.session_state["especie_azar"]
    st.markdown(f"#### 🐾 Destacado de Hoy: *{especie_actual}*")

    col_img, col_info = st.columns([1, 1])
    
    with col_img:
        # Función robusta para buscar imagen en GBIF sin quedarse congelado
        def obtener_imagen_gbif(nombre_especie):
            try:
                url_match = f"https://api.gbif.org/v1/species/suggest?q={nombre_especie}&limit=1"
                res = requests.get(url_match, timeout=3).json()
                if res:
                    species_key = res[0].get('key')
                    url_media = f"https://api.gbif.org/v1/species/{species_key}/media"
                    media_res = requests.get(url_media, timeout=3).json()
                    if 'results' in media_res and len(media_res['results']) > 0:
                        return media_res['results'][0].get('identifier')
            except Exception:
                pass
            return None

        # Intentar obtener foto real
        img_url = obtener_imagen_gbif(especie_actual)
        
        if img_url:
            st.image(img_url, caption=f"Registro fotográfico de {especie_actual} (Fuente: GBIF)", use_container_width=True)
        else:
            # Imagen de respaldo temática si la API no devuelve contenido multimedia inmediato
            st.markdown("""
                <div style="background-color: #121c17; border: 1px dashed #4da679; padding: 40px; text-align: center; border-radius: 10px; color: #a3b8ac;">
                    📷 <b>Exploración visual en curso</b><br>
                    <p style="font-size: 0.9em; margin-top: 5px;">No se encontró una vista previa directa en alta resolución para este espécimen en el repositorio abierto, pero forma parte de los registros oficiales de Chile.</p>
                </div>
            """, unsafe_allow_html=True)

    with col_info:
        st.markdown("""
            <div style="background-color: #121c17; padding: 20px; border-radius: 10px; border: 1px solid #1e3027; height: 100%;">
                <h4>💡 Dato Natural</h4>
                <p>¿Sabías que esta especie forma parte de los ecosistemas únicos monitoreados a lo largo de Chile? Usa el Buscador de Especies para ver su distribución exacta en el mapa.</p>
            </div>
        """, unsafe_allow_html=True)

# --- 3. ESTADÍSTICAS ---
with tab_stats:
    st.markdown("### Métricas Generales")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Registros", "15,000")
    c2.metric("Especies Distintas", "1,081")
    c3.metric("Comunas Cubiertas", "247")
    
    st.markdown("---")
    st.markdown("#### Top 10 Especies Más Frecuentes")
    st.bar_chart(df['especie'].value_counts())

# --- 4. BUSCADOR DE ESPECIES ---
with tab_buscador:
    st.markdown("### 🔍 Buscador y Catálogo")
    busqueda = st.text_input("Ingrese el nombre de la especie a buscar:")
    if busqueda:
        filtrado = df[df['especie'].str.contains(busqueda, case=False, na=False)]
        st.dataframe(filtrado, use_container_width=True)
    else:
        st.write("Escriba arriba para filtrar entre los registros disponibles.")

# --- 5. REPORTAR AVISTAMIENTO ---
with tab_reportar:
    st.markdown("### 📝 Reportar Nuevo Avistamiento")
    with st.form("form_reporte"):
        st.text_input("Nombre de la Especie")
        st.text_input("Comuna / Localidad")
        st.date_input("Fecha del Avistamiento")
        st.form_submit_button("Enviar Reporte")

# --- 6. MI PERFIL ---
with tab_perfil:
    st.markdown("### ⚙️ Configuración de Mi Perfil")
    st.write("Administra tus credenciales, modo de sesión y preferencias de visualización.")
    st.text_input("Correo electrónico", value="invitado@bioexplora.cl")
    st.button("Actualizar Perfil")
