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
    # 1. Leer el archivo liviano
    df = pd.read_parquet("datos_bioexplora_light.parquet")
    
    # 2. Convertir columnas a objetos estándar para evitar problemas con 'category'
    for col in df.columns:
        if isinstance(df[col].dtype, pd.CategoricalDtype):
            df[col] = df[col].astype(str)
        else:
            df[col] = df[col].astype(object)

    # 3. Estandarizar nombres de columnas a minúsculas
    df.columns = [str(c).strip().lower() for c in df.columns]
    
    # Mapeo dinámico de columnas
    region_col = next((c for c in df.columns if 'region' in c), None)
    comuna_col = next((c for c in df.columns if 'comuna' in c), None)
    nombre_col = next((c for c in df.columns if 'nombre' in c or 'especie' in c or 'taxa' in c), None)
    lat_col = next((c for c in df.columns if 'lat' in c), None)
    lon_col = next((c for c in df.columns if 'lon' in c or 'lng' in c), None)
    origen_col = next((c for c in df.columns if 'origen' in c or 'tipo' in c or 'evento' in c), None)

    # 4. Procesar y limpiar Region
    if region_col:
        df['Region'] = df[region_col].fillna("Sin Información").astype(str).str.strip().str.title()
    else:
        df['Region'] = "Sin Información"

    # 5. Procesar y limpiar Comuna
    if comuna_col:
        df['Comuna'] = df[comuna_col].fillna("Sin Información").astype(str).str.strip().str.title()
    else:
        df['Comuna'] = "Sin Información"
    
    # 6. Procesar y limpiar NombreComun
    if nombre_col:
        df['NombreComun'] = df[nombre_col].fillna("Especie No Especificada").astype(str).str.strip().str.title()
    else:
        df['NombreComun'] = "Especie No Especificada"

    # 7. Procesar TipoEvento
    if origen_col:
        df['TipoEvento'] = df[origen_col].fillna("Registro").astype(str).str.strip()
    else:
        df['TipoEvento'] = "Registro"

    # 8. Reemplazos de cadenas vacías/nulas residuales
    invalid_names = ['Nan', 'None', '', 'Null', 'Sin Informacion', 'Sin Información', '<Na>']
    df['NombreComun'] = df['NombreComun'].replace(invalid_names, 'Especie No Especificada')
    df['Region'] = df['Region'].replace(['Nan', 'None', '', 'Null', '<Na>'], 'Sin Información')
    df['Comuna'] = df['Comuna'].replace(['Nan', 'None', '', 'Null', '<Na>'], 'Sin Información')
    df['TipoEvento'] = df['TipoEvento'].replace(['Nan', 'None', '', 'Null', '<Na>'], 'Registro')
    
    # 9. Coordenadas numéricas
    df['Latitud'] = pd.to_numeric(df[lat_col], errors='coerce') if lat_col else None
    df['Longitud'] = pd.to_numeric(df[lon_col], errors='coerce') if lon_col else None
    
    return df

st.title("🌿 BioExplora Chile: Portal de Biodiversidad")
st.markdown("Visualizador interactivo de monitoreo y rescates a nivel nacional.")

try:
    df = load_data()
    
    tab1, tab2, tab3 = st.tabs(["📌 Mapa Geográfico", "📊 Estadísticas", "🔍 Buscador de Especies"])
    
    with tab1:
        st.subheader("Filtros del Mapa")
        col_reg, col_est = st.columns(2)
        
        with col_reg:
            regiones = ["Todas"] + sorted([r for r in df['Region'].unique() if r not in ['Sin Información']])
            selected_region = st.selectbox("Seleccione Región:", regiones)
            
        with col_est:
            filtro_identificacion = st.radio(
                "Estado de Identificación:",
                ["Todas", "Solo Identificadas", "No Identificadas"],
                horizontal=True
            )
        
        # Filtrado de coordenadas válidas
        df_map = df.dropna(subset=['Latitud', 'Longitud'])
        df_map = df_map[(df_map['Latitud'] < 0) & (df_map['Longitud'] < 0)]
        
        # Aplicar filtro regional
        if selected_region != "Todas":
            df_map = df_map[df_map['Region'] == selected_region]
            
        # Aplicar filtro de identificación de especie
        if filtro_identificacion == "Solo Identificadas":
            df_map = df_map[df_map['NombreComun'] != 'Especie No Especificada']
        elif filtro_identificacion == "No Identificadas":
            df_map = df_map[df_map['NombreComun'] == 'Especie No Especificada']
            
        st.info(f"Registros georreferenciados en vista: {len(df_map):,}")
        
        if len(df_map) > 0:
            fig = px.scatter_geo(
                df_map,
                lat="Latitud",
                lon="Longitud",
                color="TipoEvento",
                hover_name="NombreComun",
                hover_data={"Region": True, "Comuna": True, "Latitud": ":.4f", "Longitud": ":.4f", "TipoEvento": True},
                scope="south america",
                height=600
            )
            fig.update_geos(center=dict(lat=-35.0, lon=-71.0), projection_scale=3.8, showland=True, landcolor="rgb(240, 240, 240)")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No hay registros que coincidan con los filtros seleccionados.")
            
    with tab2:
        st.subheader("Métricas Generales")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Registros", f"{len(df):,}")
        col2.metric("Especies Distintas", f"{df[df['NombreComun'] != 'Especie No Especificada']['NombreComun'].nunique():,}")
        col3.metric("Comunas Cubiertas", f"{df['Comuna'].nunique():,}")
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### Top 10 Especies Más Frecuentes")
            top_esp = df[df['NombreComun'] != 'Especie No Especificada']['NombreComun'].value_counts().head(10)
            st.dataframe(top_esp if not top_esp.empty else "No hay especies catalogadas", use_container_width=True)
        with c2:
            st.markdown("### Top 10 Comunas con Mayor Actividad")
            st.dataframe(df['Comuna'].value_counts().head(10), use_container_width=True)
            
    with tab3:
        st.subheader("Ficha de Especie")
        especie_input = st.text_input("Buscar Especie (ej. Guanaco, Pudú, Zorro, Quisco, Lagartija):", "Lagartija")
        
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
                            color="TipoEvento",
                            hover_name="NombreComun",
                            hover_data={"Region": True, "Comuna": True, "TipoEvento": True},
                            scope="south america",
                            height=500
                        )
                        fig_esp.update_geos(center=dict(lat=-35.0, lon=-71.0), projection_scale=4.0, showland=True)
                        st.plotly_chart(fig_esp, use_container_width=True)

except Exception as e:
    st.error(f"Error al cargar la base de datos: {e}")
