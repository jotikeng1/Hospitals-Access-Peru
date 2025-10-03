Parte 3.1 PARTE DINAMINCA
# =========================================
# 1. Instalar librerías (solo una vez)
# =========================================
!pip install geopandas folium branca shapely requests

# =========================================
# 2. Ajustar visualización en Jupyter
# =========================================
from IPython.display import display, HTML

display(HTML(data="""
<style>
    div#notebook-container    { width: 95%; }
    div#menubar-container     { width: 65%; }
    div#maintoolbar-container { width: 99%; }
</style>
"""))

# =========================================
# 3. Importar librerías
# =========================================
import os
import requests, zipfile, io
import geopandas as gpd
import folium
from folium.plugins import MarkerCluster

# =========================================
# 4. Descargar repo con shapefiles
# =========================================
url = "https://github.com/jotikeng1/Hospitals-Access-Peru/archive/refs/heads/main.zip"
destino = r"C:\Users\econg\Documents\Github\Hospitals-Access-Peru"

# Descargar y extraer ZIP
r = requests.get(url)
z = zipfile.ZipFile(io.BytesIO(r.content))
z.extractall(destino)
print("✅ Repositorio descargado en:", destino)

# =========================================
# 5. Localizar rutas de shapefiles
# =========================================
for root, dirs, files in os.walk(destino):
    if "DISTRITOS.shp" in files:
        ruta_distritos = os.path.join(root, "DISTRITOS.shp")
    if "CCPP_IGN100K.shp" in files:
        ruta_ccpp = os.path.join(root, "CCPP_IGN100K.shp")

print("✅ Ruta distritos:", ruta_distritos)
print("✅ Ruta centros poblados:", ruta_ccpp)

# =========================================
# 6. Leer shapefiles
# =========================================
distritos = gpd.read_file(ruta_distritos)
centro_poblado = gpd.read_file(ruta_ccpp)

print("✅ Distritos cargados:", distritos.shape)
print("✅ Centros poblados cargados:", centro_poblado.shape)

# =========================================
# 7. Construir mapa
# =========================================
m = folium.Map(location=[-9.19, -75.0152], zoom_start=5, tiles="CartoDB positron")

# --- Distritos ---
folium.GeoJson(
    distritos,
    name="Distritos",
    style_function=lambda x: {
        "fillColor": "blue",
        "color": "black",
        "weight": 0.3,
        "fillOpacity": 0.1
    }
).add_to(m)

# --- Centros poblados (muestra de 2000) ---
marker_cluster = MarkerCluster(name="Centros Poblados").add_to(m)

for idx, row in centro_poblado.sample(2000, random_state=1).iterrows():
    folium.CircleMarker(
        location=[row.geometry.y, row.geometry.x],
        radius=2,
        color="red",
        fill=True,
        fill_opacity=0.6,
        popup=row.get("NOMCCPP", "Centro poblado")
    ).add_to(marker_cluster)

# --- Controles de capas ---
folium.LayerControl().add_to(m)

# Mostrar mapa
m

PARTE 3.2 LIMA Y LORETO

import pandas as pd

ruta_csv = r"C:\Users\econg\Documents\Github\Hospitals-Access-Peru\IPRESS.csv"

# Leer CSV con codificación adecuada
df_ipress = pd.read_csv(ruta_csv, encoding="latin1")  # si falla, prueba con cp1252

print("Columnas disponibles en IPRESS:")
print(df_ipress.columns.tolist())   # ver todos los nombres de columnas
print(df_ipress.head())             # muestra primeras filas


import pandas as pd
import geopandas as gpd

# Cargar CSV con encoding adecuado
ruta_csv = r"C:\Users\econg\Documents\Github\Hospitals-Access-Peru\IPRESS.csv"
df_ipress = pd.read_csv(ruta_csv, encoding="latin1")

# Filtrar solo registros con coordenadas válidas
df_ipress = df_ipress.dropna(subset=["ESTE", "NORTE"])

# Convertir a GeoDataFrame
hospitales = gpd.GeoDataFrame(
    df_ipress,
    geometry=gpd.points_from_xy(df_ipress["ESTE"], df_ipress["NORTE"]),
    crs="EPSG:4326"
)

print("✅ Hospitales IPRESS cargados:", hospitales.shape)
print(hospitales[["Nombre del establecimiento", "Departamento", "Provincia", "Distrito"]].head())


# ======================================
# MAPA DE ACCESIBILIDAD HOSPITALARIA
# LIMA vs LORETO
# ======================================

import geopandas as gpd
import pandas as pd
import folium
from IPython.display import display

# ============================
# 1. Cargar datos
# ============================

ruta_distritos = r"C:\Users\econg\Documents\Github\Hospitals-Access-Peru\Hospitals-Access-Peru-main\code\shape_file_distritos\DISTRITOS.shp"
ruta_ccpp = r"C:\Users\econg\Documents\Github\Hospitals-Access-Peru\Hospitals-Access-Peru-main\code\shape_file_CP\CCPP_IGN100K.shp"
ruta_ipress = r"C:\Users\econg\Documents\Github\Hospitals-Access-Peru\IPRESS.csv"

distritos = gpd.read_file(ruta_distritos).to_crs(epsg=4326)
ccpp = gpd.read_file(ruta_ccpp).to_crs(epsg=4326)
df_ipress = pd.read_csv(ruta_ipress, encoding="latin-1")

# Convertir hospitales a GeoDataFrame (columnas invertidas: NORTE=lon, ESTE=lat)
hosp = df_ipress.dropna(subset=["NORTE", "ESTE"])
hosp = gpd.GeoDataFrame(
    hosp,
    geometry=gpd.points_from_xy(hosp["NORTE"], hosp["ESTE"]),
    crs="EPSG:4326"
)

print("✅ Distritos:", distritos.shape)
print("✅ Centros poblados:", ccpp.shape)
print("✅ Hospitales IPRESS:", hosp.shape)

# ============================
# 2. Cálculo de hospitales en 10 km
# ============================

ccpp_utm = ccpp.to_crs(32718)
hosp_utm = hosp.to_crs(32718)

ccpp_buffers = ccpp_utm.copy()
ccpp_buffers["geometry"] = ccpp_buffers.buffer(10000)

join = gpd.sjoin(hosp_utm, ccpp_buffers, how="left", predicate="within")
conteo = join.groupby("index_right").size()

ccpp_buffers["hospitales_10km"] = ccpp_buffers.index.map(conteo).fillna(0).astype(int)
ccpp = ccpp_buffers.to_crs(4326)

# ============================
# 3. Selección Lima y Loreto
# ============================

lima_ccpp = ccpp[ccpp["DEP"] == "LIMA"]
loreto_ccpp = ccpp[ccpp["DEP"] == "LORETO"]

lima_min = lima_ccpp.loc[lima_ccpp["hospitales_10km"].idxmin()]
lima_max = lima_ccpp.loc[lima_ccpp["hospitales_10km"].idxmax()]
loreto_min = loreto_ccpp.loc[loreto_ccpp["hospitales_10km"].idxmin()]
loreto_max = loreto_ccpp.loc[loreto_ccpp["hospitales_10km"].idxmax()]

print("\n=== Resultados ===")
print(f"Lima - Menor acceso: {lima_min['NOM_POBLAD']} ({lima_min['hospitales_10km']} hospitales)")
print(f"Lima - Mayor acceso: {lima_max['NOM_POBLAD']} ({lima_max['hospitales_10km']} hospitales)")
print(f"Loreto - Menor acceso: {loreto_min['NOM_POBLAD']} ({loreto_min['hospitales_10km']} hospitales)")
print(f"Loreto - Mayor acceso: {loreto_max['NOM_POBLAD']} ({loreto_max['hospitales_10km']} hospitales)")

# ============================
# 4. Visualización Folium
# ============================

m = folium.Map(location=[-9.19, -75.0152], zoom_start=5, tiles="cartodbpositron")

def add_circle(row, color, mapa, etiqueta, radius):
    centroid = row.geometry.centroid
    folium.Circle(
        location=[centroid.y, centroid.x],
        radius=radius,
        color=color,
        fill=True,
        fill_opacity=0.35,
        popup=folium.Popup(
            f"<b>{row['NOM_POBLAD']}</b><br>"
            f"Depto: {row['DEP']}<br>"
            f"Prov: {row['PROV']}<br>"
            f"Dist: {row['DIST']}<br>"
            f"Hosp. dentro 10km: {row['hospitales_10km']}<br>"
            f"<i>{etiqueta}</i>",
            max_width=300
        )
    ).add_to(mapa)

add_circle(lima_min, "red", m, "Centro poblado con MENOR acceso hospitalario en Lima", 10000)
add_circle(lima_max, "green", m, "Centro poblado con MAYOR acceso hospitalario en Lima", 10000)
add_circle(loreto_min, "red", m, "Centro poblado con MENOR acceso hospitalario en Loreto", 10000)
add_circle(loreto_max, "green", m, "Centro poblado con MAYOR acceso hospitalario en Loreto", 10000)

folium.GeoJson(
    distritos.to_json(),
    name="Distritos",
    style_function=lambda x: {"color": "black", "weight": 0.5, "fillOpacity": 0}
).add_to(m)

legend_html = """
<div style="
     position: fixed; 
     bottom: 30px; left: 30px; width: 200px; height: 90px; 
     background-color: white; z-index:9999; font-size:14px; 
     border:2px solid grey; border-radius:5px; padding: 10px;">
<b>Leyenda</b><br>
<svg height="10" width="10"><circle cx="5" cy="5" r="5" fill="red"/></svg> Menor acceso<br>
<svg height="10" width="10"><circle cx="5" cy="5" r="5" fill="green"/></svg> Mayor acceso
</div>
"""
m.get_root().html.add_child(folium.Element(legend_html))

# ============================
# 5. Mostrar y guardar
# ============================

m.save("mapa_lima_loreto.html")
display(m)


## 🏥 Task 2: Proximity Visualization — Lima & Loreto

En el siguiente mapa se muestran los centros poblados con **más** (círculo verde) y **menos** (círculo rojo) hospitales en un radio de 10 km para los departamentos de **Lima** y **Loreto**.

---

### ✍️ Análisis comparativo

**Lima**  
- Alta concentración urbana de hospitales y centros de salud.  
- La accesibilidad está reforzada por la proximidad: la mayoría de los centros poblados en el área metropolitana tienen varios establecimientos dentro de un radio de 10 km.  
- Refleja un patrón centralizado y urbano, con mayor densidad hospitalaria.  

**Loreto**  
- Gran dispersión geográfica de los centros poblados, en un contexto amazónico con baja conectividad vial.  
- Muchos centros poblados tienen pocos o ningún hospital en un radio de 10 km.  
- La accesibilidad a servicios de salud está limitada por la distancia y la dependencia de ríos y transporte fluvial, lo que representa un desafío para la cobertura sanitaria.  


