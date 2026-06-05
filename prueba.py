import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd

# 1. CONFIGURACIÓN DE LA PÁGINA WEB (Ancho completo estilo tablero de control)
st.set_page_config(layout="wide", page_title="Sistema de Localización de Fallas - SEIN")

# ==========================================
# 2. BASE DE DATOS SIMULADA DE LÍNEAS (Ejemplo)
# ==========================================
# En el futuro, aquí leerás tu archivo Excel o CSV usando: pd.read_csv() o pd.read_excel()
datos_lineas = {
    'L-2201 (220 kV)': pd.DataFrame({
        'Torre': ['SE Chilca', 'Torre 02', 'Torre 03', 'SE San Juan'],
        'Distancia_km': [0.0, 15.0, 35.0, 52.3],
        'Latitud': [-12.5212, -12.4150, -12.2520, -12.1145],
        'Longitud': [-76.7415, -76.8210, -76.9150, -76.9802]
    })
}

# ==========================================
# 3. DISEÑO DE LA INTERFAZ WEB (FRONTEND)
# ==========================================
st.title("⚡ Centro de Control: Localizador de Fallas Georreferenciado")
st.markdown("Herramienta analítica para la optimización de tiempos de respuesta post-falla.")

# Corrección del error: En Streamlit se usa st.divider() en lugar de st.hr()
st.divider()

# Creamos dos columnas: una barra lateral izquierda para datos (ancho 1) y el mapa a la derecha (ancho 3)
col_control, col_mapa = st.columns([1, 3])

with col_control:
    st.header("📋 Datos del Evento")
    
    # Selector de Línea de Transmisión
    linea_seleccionada = st.selectbox("Seleccione la Línea Afectada:", list(datos_lineas.keys()))
    df_linea = datos_lineas[linea_seleccionada]
    distancia_max = df_linea['Distancia_km'].max()
    
    # Entrada numérica para los kilómetros reportados por el relé de distancia
    distancia_falla = st.number_input(
        f"Distancia de falla según Relé (0 a {distancia_max} km):", 
        min_value=0.0, 
        max_value=float(distancia_max), 
        value=15.0,
        step=0.1
    )
    
    # ==========================================
    # 4. ALGORITMO DE INTERPOLACIÓN DE LA FALLA (CORREGIDO)
    # ==========================================
    # Buscamos las estructuras (torres) que flanquean el punto de la falla
    df_antes = df_linea[df_linea['Distancia_km'] <= distancia_falla]
    df_despues = df_linea[df_linea['Distancia_km'] > distancia_falla]
    
    # Si la falla es exactamente al final de la línea o sobre la última torre
    if df_despues.empty:
        t_anterior = df_antes.iloc[-2] if len(df_antes) > 1 else df_antes.iloc[-1]
        t_posterior = df_antes.iloc[-1]
    else:
        t_anterior = df_antes.iloc[-1]
        t_posterior = df_despues.iloc[0]
    
    # Factor de ponderación para la interpolación lineal
    if t_posterior['Distancia_km'] != t_anterior['Distancia_km']:
        peso = (distancia_falla - t_anterior['Distancia_km']) / (t_posterior['Distancia_km'] - t_anterior['Distancia_km'])
    else:
        peso = 0
        
    lat_falla = t_anterior['Latitud'] + peso * (t_posterior['Latitud'] - t_anterior['Latitud'])
    lon_falla = t_anterior['Longitud'] + peso * (t_posterior['Longitud'] - t_anterior['Longitud'])
    
    # Despliegue de resultados dinámicos
    st.success("**Ubicación Estimada:**")
    st.write(f"📍 **Coordenadas:** `{lat_falla:.5f}, {lon_falla:.5f}`")
    
    if t_anterior['Torre'] == t_posterior['Torre']:
        st.write(f"🏗️ **Estructura afectada:** ¡Falla exacta en **{t_anterior['Torre']}**!")
    else:
        st.write(f"🏗️ **Tramo afectado:** Entre **{t_anterior['Torre']}** y **{t_posterior['Torre']}**")
# ==========================================
# 5. RENDERIZADO DEL MAPA EN LA COLUMNA DERECHA
# ==========================================
with col_mapa:
    # Creamos el mapa base de OpenStreetMap centrado dinámicamente en el punto de la falla
    m = folium.Map(location=[lat_falla, lon_falla], zoom_start=11, tiles="OpenStreetMap")
    
    # Dibujamos el trazo completo de la línea de transmisión (Color azul marino)
    coord_linea = list(zip(df_linea['Latitud'], df_linea['Longitud']))
    folium.PolyLine(coord_linea, color="#1A237E", weight=4, opacity=0.8, tooltip=linea_seleccionada).add_to(m)
    
    # Dibujamos los nodos de las estructuras y subestaciones como círculos pequeños
    for _, fila in df_linea.iterrows():
        folium.CircleMarker(
            location=[fila['Latitud'], fila['Longitud']],
            radius=4, 
            color="black", 
            fill=True, 
            fill_color="white",
            popup=f"{fila['Torre']} (Km {fila['Distancia_km']})"
        ).add_to(m)
        
    # Colocamos el marcador crítico de la falla con un icono de rayo (bolt) rojo
    folium.Marker(
        location=[lat_falla, lon_falla],
        popup=f"<b>ALERTA DE CORTOCIRCUITO: Km {distancia_falla}</b>",
        icon=folium.Icon(color='red', icon='bolt', prefix='fa')
    ).add_to(m)
    
    # Renderizamos el mapa interactivo dentro de la aplicación de Streamlit
    st_folium(m, width="100%", height=600, returned_objects=[])