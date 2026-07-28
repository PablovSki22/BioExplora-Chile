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
    # 1. Leer encabezados para mapear columnas sin cargar todo en memoria
    preview = pd.read_parquet("datos_bioexplora.parquet")
    cols_map = {col: col.strip().lower() for col in preview.columns}
    
    region_col = next((c for c, l in cols_map.items() if 'region' in l), None)
    comuna_col = next((c for c, l in cols_map.items() if 'comuna' in l), None)
    nombre_col = next((c for c, l in cols_map.items() if 'nombre' in l or 'especie' in l), None)
    lat_col = next((c for c, l in cols_map.items() if 'lat' in l), None)
    lon_col = next((c for c, l in cols_map.items() if 'lon' in l or 'lng' in l), None)
    origen_col = next((c for c, l in cols_map.items() if 'origen' in l or 'tipo' in l or 'evento' in l), None)

    needed_cols = [c for c in [region_col, comuna_col, nombre_col, lat_col, lon_col, origen_col] if c]

    # 2. Leer solo las columnas estrictamente necesarias
    df = pd.read_parquet("datos_bioexplora.parquet", columns=needed_cols)
    
    # 3. Formatear y optimizar uso de RAM
    df['Region'] = df[region_col].astype(str).str.strip().str.title().astype('category') if region_col else "Sin Información"
    df['Comuna'] = df[comuna_col].astype(str).str.strip().str.title().astype('category') if comuna_col else "Sin Información"
    df['NombreComun'] = df[nombre_col].astype(str).str.strip().str.title() if nombre_col else "Sin Información"
    df['TipoEvento'] = df[origen_col].astype(str).str.strip().astype('category') if origen_col else "Registro"
    
    if lat_col:
        df['Latitud'] = pd.to_numeric(df[lat_col], errors='coerce').astype('float32')
    else:
        df['Latitud'] = None
        
    if lon_col:
        df['Longitud'] = pd.to_numeric(df[lon_col], errors='coerce').astype('float32')
    else:
        df['Longitud'] = None

    # Filtrar registros vacíos
    df = df[~df['NombreComun'].isin(['Nan', 'None', '', 'Sin Información'])]
    return df[['Region', 'Comuna', 'NombreComun', 'TipoEvento', 'Latitud', 'Longitud']]

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
            
        st.info(f"Registros georreferenciados disponibles: {len(df_map):,}")
        
        # Muestra ultra liviana (máx 2,500 puntos) para no saturar memoria/GPU
        sample_size = min(2500, len(df_map))
        if sample_size > 0:
            df_sample = df_map.sample(n=sample_size, random_state=42) if len(df_map) > sample_size else df_map
            
            fig = px.scatter_geo(
                df_sample,
                lat="Latitud",
                lon="Longitud",
                color="TipoEvento",
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
                        sample_esp = min(2000, len(df_esp_geo))
                        df_esp_sample = df_esp_geo.sample(n=sample_esp, random_state=42) if len(df_esp_geo) > sample_esp else df_esp_geo
                        
                        fig_esp = px.scatter_geo(
                            df_esp_sample,
                            lat="Latitud",
                            lon="Longitud",
                            color="TipoEvento",
                            hover_name="NombreComun",
                            hover_data=["Comuna", "Region"],
                            scope="south america",
                            height=500
                        )
                        fig_esp.update_geos(center=dict(lat=-35.0, lon=-71.0), projection_scale=4.0, showland=True)
                        st.plotly_chart(fig_esp, use_container_width=True)

except Exception as e:
    st.error(f"Error al cargar la base de datos: {e}")
