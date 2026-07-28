import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import st_folium

st.set_page_config(
    page_title="BioExplora Chile",
    page_icon="🌿",
    layout="wide"
)

# Diccionario de coordenadas de respaldo por comuna (Chile)
COORDENADAS_COMUNAS = {
    "Arica": (-18.4783, -70.3126), "Iquique": (-20.2133, -70.1503), "Antofagasta": (-23.6509, -70.3975),
    "Calama": (-22.4544, -68.9294), "Copiapó": (-27.3668, -70.3323), "Vallenar": (-28.5751, -70.7581),
    "La Serena": (-29.9027, -71.2520), "Coquimbo": (-29.9533, -71.3436), "Ovalle": (-30.5983, -71.2003),
    "Valparaíso": (-33.0472, -71.6127), "Viña Del Mar": (-33.0245, -71.5518), "Quillota": (-32.8739, -71.2486),
    "San Antonio": (-33.5938, -71.6076), "Santiago": (-33.4489, -70.6693), "Puente Alto": (-33.6117, -70.5758),
    "Maipú": (-33.5112, -70.7580), "Melipilla": (-33.6853, -71.2144), "Rancagua": (-34.1701, -70.7444),
    "San Fernando": (-34.5839, -70.9888), "Curicó": (-34.9828, -71.2394), "Talca": (-35.4264, -71.6554),
    "Linares": (-35.8454, -71.5979), "Cauquenes": (-35.9670, -72.3158), "Chillán": (-36.6063, -72.1023),
    "San Carlos": (-36.4242, -71.9581), "Concepción": (-36.8270, -73.0503), "Los Ángeles": (-37.4697, -72.3537),
    "Chillan": (-36.6063, -72.1023), "San Pedro De La Paz": (-36.8406, -73.1022), "Talcahuano": (-36.7167, -73.1167),
    "Temuco": (-38.7359, -72.5904), "Villarrica": (-39.2822, -72.2272), "Angol": (-37.7944, -72.7164),
    "Valdivia": (-39.8142, -73.2459), "Osorno": (-40.5739, -73.1336), "Puerto Montt": (-41.4689, -72.9411),
    "Puerto Varas": (-41.3195, -72.9854), "Castro": (-42.4721, -73.7732), "Ancud": (-41.8686, -73.8267),
    "Coyhaique": (-45.5752, -72.0662), "Puerto Aysén": (-45.4058, -72.6936), "Punta Arenas": (-53.1638, -70.9171),
    "Natales": (-51.7269, -72.5062), "Puerto Natales": (-51.7269, -72.5062), "Porvenir": (-53.2954, -70.3668)
}

@st.cache_data
def load_data():
    df = pd.read_parquet("datos_bioexplora_light.parquet")
    
    # Normalizar nombres de columnas
    df.columns = [str(c).strip().lower() for c in df.columns]
    
    region_col = next((c for c in df.columns if 'region' in c), None)
    comuna_col = next((c for c in df.columns if 'comuna' in c), None)
    nombre_col = next((c for c in df.columns if 'nombre' in c or 'especie' in c or 'taxa' in c), None)
    lat_col = next((c for c in df.columns if any(term in c for term in ['lat', 'y_coord', 'y'])), None)
    lon_col = next((c for c in df.columns if any(term in c for term in ['lon', 'lng', 'x_coord', 'x'])), None)
    origen_col = next((c for c in df.columns if 'origen' in c or 'tipo' in c or 'evento' in c), None)

    df['Region'] = df[region_col].fillna("Sin Información").astype(str).str.strip().str.title() if region_col else "Sin Información"
    df['Comuna'] = df[comuna_col].fillna("Sin Información").astype(str).str.strip().str.title() if comuna_col else "Sin Información"
    df['NombreComun'] = df[nombre_col].fillna("Especie No Especificada").astype(str).str.strip().str.title() if nombre_col else "Especie No Especificada"
    df['TipoEvento'] = df[origen_col].fillna("Registro").astype(str).str.strip() if origen_col else "Registro"

    invalid_names = ['Nan', 'None', '', 'Null', 'Sin Informacion', 'Sin Información', '<Na>']
    df['NombreComun'] = df['NombreComun'].replace(invalid_names, 'Especie No Especificada')
    df['Region'] = df['Region'].replace(['Nan', 'None', '', 'Null', '<Na>'], 'Sin Información')
    df['Comuna'] = df['Comuna'].replace(['Nan', 'None', '', 'Null', '<Na>'], 'Sin Información')
    
    # Conversión numérica de coordenadas
    df['Latitud'] = pd.to_numeric(df[lat_col], errors='coerce') if lat_col else None
    df['Longitud'] = pd.to_numeric(df[lon_col], errors='coerce') if lon_col else None
    
    # Rellenar coordenadas faltantes usando la Comuna (Fallback Geográfico)
    def asignar_lat(row):
        if pd.notnull(row['Latitud']) and row['Latitud'] != 0:
            return -abs(row['Latitud']) if abs(row['Latitud']) > 10 else row['Latitud']
        comuna = row['Comuna']
        return COORDENADAS_COMUNAS.get(comuna, (None, None))[0]

    def asignar_lon(row):
        if pd.notnull(row['Longitud']) and row['Longitud'] != 0:
            return -abs(row['Longitud']) if abs(row['Longitud']) > 10 else row['Longitud']
        comuna = row['Comuna']
        return COORDENADAS_COMUNAS.get(comuna, (None, None))[1]

    df['Latitud'] = df.apply(asignar_lat, axis=1)
    df['Longitud'] = df.apply(asignar_lon, axis=1)

    return df

def crear_mapa_folium(df_puntos, lat_centro, lon_centro, zoom):
    m = folium.Map(
        location=[lat_centro, lon_centro],
        zoom_start=zoom,
        tiles="OpenStreetMap"
    )
    
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

st.title("🌿 BioExplora Chile: Portal de Biodiversidad")
st.markdown("Visualizador interactivo de monitoreo y rescates a nivel nacional.")

try:
    df = load_data()
    
    tab1, tab2, tab3 = st.tabs(["📌 Mapa Geográfico", "📊 Estadísticas", "🔍 Buscador de Especies"])

    # TAB 1: MAPA GEOGRÁFICO GENERAL
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
            
    # TAB 2: ESTADÍSTICAS Y GRÁFICOS
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

    # TAB 3: BUSCADOR CON GARANTÍA DE MAPA
    with tab3:
        st.subheader("Buscador y Ficha de Especie")
        
        col_search1, col_search2 = st.columns([1, 1])
        
        with col_search1:
            busqueda = st.text_input("1. Buscar por palabra o fragmento de nombre:", "ojos")
        
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
                        st.warning("No fue posible ubicar geográficamente esta comuna.")

                st.markdown("---")
                st.markdown("#### Detalle de Registros Encontrados")
                cols_mostrar = [c for c in ['NombreComun', 'Region', 'Comuna', 'TipoEvento', 'Latitud', 'Longitud'] if c in df_esp.columns]
                st.dataframe(df_esp[cols_mostrar], use_container_width=True)

except Exception as e:
    st.error(f"Error al cargar la base de datos: {e}")
