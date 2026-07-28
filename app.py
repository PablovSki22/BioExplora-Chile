import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="BioExplora Chile",
    page_icon="🌿",
    layout="wide"
)

@st.cache_data
def load_data():
    # Carga ultrarrápida desde Parquet
    df = pd.read_parquet("datos_bioexplora.parquet")
    
    df['Region'] = df['Region'].astype(str).str.strip().str.title()
    df['Comuna'] = df['Comuna'].astype(str).str.strip().str.title()
    df['NombreComun'] = df['NombreComun'].astype(str).str.strip().str.title()
    
    df['Latitud'] = pd.to_numeric(df['Latitud'], errors='coerce')
    df['Longitud'] = pd.to_numeric(df['Longitud'], errors='coerce')
    
    df = df[~df['NombreComun'].isin(['Nan', 'None', '', 'Sin Información', 'Sin Información '])]
    return df

st.title("🌿 BioExplora Chile: Portal de Biodiversidad")
st.markdown("Visualizador interactivo de monitoreo y rescates a nivel nacional.")

try:
    df = load_data()
    
    tab1, tab2, tab3 = st.tabs(["📌 Mapa Geográfico", "📊 Estadísticas", "🔍 Buscador de Especies"])
    
    with tab1:
        st.subheader("Filtro por Región")
        regiones = ["Todas"] + sorted([r for r in df['Region'].unique() if r not in ['Nan', 'None']])
        selected_region = st.selectbox("Seleccione Región:", regiones)
        
        df_map = df.dropna(subset=['Latitud', 'Longitud'])
        df_map = df_map[(df_map['Latitud'] < 0) & (df_map['Longitud'] < 0)]
        
        if selected_region != "Todas":
            df_map = df_map[df_map['Region'] == selected_region]
            
        st.info(f"Registros georreferenciados: {len(df_map):,}")
        
        sample_size = min(30000, len(df_map))
        if sample_size > 0:
            df_sample = df_map.sample(n=sample_size, random_state=42) if len(df_map) > sample_size else df_map
            
            fig = px.scatter_geo(
                df_sample,
                lat="Latitud",
                lon="Longitud",
                color="TipoEvento_Origen",
                hover_name="NombreComun",
                hover_data=["Comuna", "Region"],
                scope="south america",
                height=600
            )
            fig.update_geos(center=dict(lat=-35.0, lon=-71.0), projection_scale=3.8, showland=True, landcolor="rgb(240, 240, 240)")
            st.plotly_chart(fig, use_container_width=True)
            
    with tab2:
        st.subheader("Métricas Generales")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Registros", f"{len(df):,}")
        col2.metric("Especies Distintas", f"{df['NombreComun'].nunique():,}")
        col3.metric("Comunas Cubiertas", f"{df['Comuna'].nunique():,}")
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### Top 10 Especies Más Frecuentes")
            st.dataframe(df['NombreComun'].value_counts().head(10), use_container_width=True)
        with c2:
            st.markdown("### Top 10 Comunas con Mayor Actividad")
            st.dataframe(df['Comuna'].value_counts().head(10), use_container_width=True)
            
    with tab3:
        st.subheader("Ficha de Especie")
        especie_input = st.text_input("Buscar Especie (ej. Guanaco, Pudú, Zorro, Quisco):", "Guanaco")
        
        if especie_input:
            df_esp = df[df['NombreComun'].str.contains(especie_input, case=False, na=False)]
            st.success(f"Se encontraron {len(df_esp):,} registros para '{especie_input}'.")
            
            if len(df_esp) > 0:
                col_a, col_b = st.columns([1, 2])
                with col_a:
                    st.markdown("#### Presencia por Comuna")
                    st.dataframe(df_esp['Comuna'].value_counts().head(10), use_container_width=True)
                with col_b:
                    df_esp_geo = df_esp.dropna(subset=['Latitud', 'Longitud'])
                    df_esp_geo = df_esp_geo[(df_esp_geo['Latitud'] < 0) & (df_esp_geo['Longitud'] < 0)]
                    if len(df_esp_geo) > 0:
                        fig_esp = px.scatter_geo(
                            df_esp_geo,
                            lat="Latitud",
                            lon="Longitud",
                            color="TipoEvento_Origen",
                            hover_name="NombreComun",
                            hover_data=["Comuna", "Region"],
                            scope="south america",
                            height=500
                        )
                        fig_esp.update_geos(center=dict(lat=-35.0, lon=-71.0), projection_scale=4.0, showland=True)
                        st.plotly_chart(fig_esp, use_container_width=True)

except Exception as e:
    st.error(f"Error al cargar la base de datos: {e}")
