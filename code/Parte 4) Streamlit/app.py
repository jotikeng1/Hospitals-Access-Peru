import streamlit as st
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import seaborn as sns
from unidecode import unidecode
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster

# --- Configuración de la página de Streamlit ---
st.set_page_config(layout="wide")
st.title('Dashboard Geoespacial de Hospitales en Perú')

# --- Funciones de Carga de Datos (con caché para velocidad) ---
@st.cache_data
def load_data():
    url = "https://datosabiertos.gob.pe/node/2998/download"
    try:
        hospitales = pd.read_csv(url, encoding="latin-1")
    except:
        hospitales = pd.read_csv(url, sep=";", encoding="latin-1")

    hospitales_operativos = hospitales[hospitales["Condición"] == "EN FUNCIONAMIENTO"].copy()
    hospitales_geo = hospitales_operativos[
        (hospitales_operativos["NORTE"].notnull()) & (hospitales_operativos["NORTE"] != 0) &
        (hospitales_operativos["ESTE"].notnull()) &  (hospitales_operativos["ESTE"] != 0)
    ].copy()
    hospitales_geo.rename(columns={"NORTE": "latitud", "ESTE": "longitud"}, inplace=True)
    return hospitales_geo

@st.cache_data
def load_map_data():
    map_url = "https://raw.githubusercontent.com/juaneladio/peru-geojson/master/peru_distrital_simple.geojson"
    df_mapa = gpd.read_file(map_url)
    return df_mapa

# --- Carga Principal de Datos ---
with st.spinner('Cargando datos y mapas...'):
    df_hospitales = load_data()
    df_mapa_distritos = load_map_data()

# --- ANÁLISIS ESTÁTICO POR DISTRITO ---
st.header("1. Análisis Estático por Distrito")

# Calculamos hospitales por distrito
hosp_por_distrito = df_hospitales.groupby(['UBIGEO', 'Distrito', 'Provincia', 'Departamento'], as_index=False).size()
hosp_por_distrito.rename(columns={'size': 'Número de Hospitales'}, inplace=True)
hosp_por_distrito.sort_values('Número de Hospitales', ascending=False, inplace=True)

# Unimos los datos con el mapa para las visualizaciones
df_mapa_distritos['UBIGEO_norm'] = df_mapa_distritos['IDDIST'].astype(str)
hosp_por_distrito['UBIGEO_norm'] = hosp_por_distrito['UBIGEO'].astype(str)

mapa_distrital_con_datos = df_mapa_distritos.merge(
    hosp_por_distrito,
    on='UBIGEO_norm',
    how='left'
)
mapa_distrital_con_datos['Número de Hospitales'] = mapa_distrital_con_datos['Número de Hospitales'].fillna(0)


col1, col2 = st.columns([1, 2]) # Damos más espacio a la columna del gráfico

with col1:
    # Mostramos el Top 10
    st.subheader("Top 10 Distritos con más Hospitales")
    st.dataframe(hosp_por_distrito.head(10))

    # Mostramos los distritos sin hospitales
    st.subheader("Distritos sin Hospitales Operativos")
    distritos_sin_hosp = mapa_distrital_con_datos[mapa_distrital_con_datos['Número de Hospitales'] == 0]
    st.dataframe(distritos_sin_hosp[['NOMBDIST', 'NOMBPROV', 'NOMBDEP']].head(5))
    st.info(f"Se encontraron {len(distritos_sin_hosp)} distritos sin hospitales.")

with col2:
    # Gráfico de barras estático para el Top 20 de distritos
    st.subheader("Gráfico de Barras (Top 20 Distritos)")
    
    # Preparamos los datos para el gráfico (solo los 20 primeros)
    top_20_distritos = hosp_por_distrito.head(20)

    fig_bar, ax_bar = plt.subplots(figsize=(10, 8))
    sns.barplot(
        x='Número de Hospitales',
        y='Distrito',
        data=top_20_distritos,
        ax=ax_bar
    )
    ax_bar.set_title('Top 20 Distritos con más Hospitales', fontsize=16)
    st.pyplot(fig_bar)


st.divider()
st.header("2. Mapa de Coropletas Estático por Distrito")
fig_map, ax_map = plt.subplots(1, 1, figsize=(12, 12))
ax_map.set_axis_off()
mapa_plot_data = mapa_distrital_con_datos.copy()
mapa_plot_data['Número de Hospitales_plot'] = mapa_plot_data['Número de Hospitales'].replace(0, pd.NA)
mapa_plot_data.plot(
    column='Número de Hospitales_plot', cmap='viridis_r', linewidth=0.5, ax=ax_map,
    edgecolor='0.8', legend=True,
    missing_kwds={"color": "lightgrey", "label": "0 Hospitales"}
)
st.pyplot(fig_map)


st.divider()
# --- ANÁLISIS DINÁMICO E INTERACTIVO ---
st.header("3. Análisis Dinámico (Folium)")
# ... (El resto del código para los mapas dinámicos sigue igual) ...
# Mapa Nacional con Marcadores Agrupados
st.subheader("Mapa Nacional con Coropletas y Marcadores")
st.info("Haz zoom para ver los marcadores individuales de los hospitales.")
mapa_nacional = folium.Map(location=[-9.19, -75.01], zoom_start=5)
folium.Choropleth(
    geo_data=mapa_distrital_con_datos, name='choropleth', data=mapa_distrital_con_datos,
    columns=['IDDIST', 'Número de Hospitales'], key_on='feature.properties.IDDIST',
    fill_color='YlOrRd', fill_opacity=0.6, line_opacity=0.2,
    legend_name='Número de Hospitales por Distrito'
).add_to(mapa_nacional)
marker_cluster = MarkerCluster().add_to(mapa_nacional)
for idx, row in df_hospitales.sample(n=1500).iterrows():
    folium.Marker(
        location=[row['latitud'], row['longitud']],
        popup=f"<strong>{row['Nombre del establecimiento']}</strong><br>{row['Distrito']}",
        icon=folium.Icon(color='blue', icon='plus-sign', prefix='glyphicon')
    ).add_to(marker_cluster)
st_folium(mapa_nacional, width='100%', height=600)

# Mapas de Proximidad
st.subheader("Análisis de Proximidad")
opcion_proximidad = st.selectbox(
    'Selecciona una zona para analizar la densidad:',
    ('Lima (Alta Densidad)', 'Loreto (Baja Densidad)')
)
if opcion_proximidad == 'Lima (Alta Densidad)':
    df_zona = df_hospitales[df_hospitales['Departamento'] == 'LIMA']
    mapa_proximidad = folium.Map(location=[-12.0464, -77.0428], zoom_start=10)
else: # Loreto
    df_zona = df_hospitales[df_hospitales['Departamento'] == 'LORETO']
    mapa_proximidad = folium.Map(location=[-4.6, -74.5], zoom_start=7)
for idx, row in df_zona.iterrows():
    folium.Marker(
        location=[row['latitud'], row['longitud']],
        popup=f"<strong>{row['Nombre del establecimiento']}</strong><br>{row['Clasificación']}",
        icon=folium.Icon(color='red', icon='info-sign', prefix='glyphicon')
    ).add_to(mapa_proximidad)
st_folium(mapa_proximidad, width='100%', height=500)