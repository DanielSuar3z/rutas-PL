import streamlit as st
import osmnx as ox
import folium
from streamlit_folium import st_folium
import pandas as pd
import networkx as nx
from pulp import *
import time
import numpy as np
import json
import requests
from streamlit_js_eval import streamlit_js_eval

# ============================================================================
# CONFIGURACIÓN INTEGRADA
# ============================================================================

# API Keys
GOOGLE_MAPS_API_KEY = "AIzaSyC1h1axOuTQXqelP3LODEoY6J4iKCr5tuY"
GOOGLE_PLACES_API_KEY = "AIzaSyC1h1axOuTQXqelP3LODEoY6J4iKCr5tuY"

# Categorías de lugares
CATEGORIAS_LUGARES = {
    "🏥 Salud": ["hospital", "pharmacy", "doctor", "dentist", "health", "clinic"],
    "🛒 Comercios": ["store", "supermarket", "shopping_mall", "convenience_store", "grocery_store"],
    "🍽️ Restaurantes": ["restaurant", "cafe", "bakery", "food", "meal_takeaway"],
    "🏫 Educación": ["school", "university", "college", "library"],
    "🏦 Servicios": ["bank", "post_office", "atm", "local_government_office"],
    "⛪ Religión": ["church", "mosque", "synagogue", "hindu_temple", "place_of_worship"],
    "🎭 Entretenimiento": ["movie_theater", "stadium", "amusement_park", "museum", "park"],
    "🏨 Hospedaje": ["hotel", "lodging"],
    "🚗 Transporte": ["gas_station", "car_repair", "car_wash"]
}

# Puntos iniciales
PUNTOS_INICIALES = {
    "🏭 Fábrica Lacteos Amazonia": {
        "coords": (1.6200, -75.6200), 
        "capacidad": 1000, 
        "tipo": "fabrica",
        "costo": 1500
    },
    "🏭 Planta Procesadora Carnes": {
        "coords": (1.6080, -75.6150), 
        "capacidad": 800, 
        "tipo": "fabrica",
        "costo": 1800
    },
    "🏪 Almacén Centro": {
        "coords": (1.6145, -75.6062), 
        "demanda": 300, 
        "tipo": "almacen",
        "costo": 200
    },
    "🏪 Bodega Norte": {
        "coords": (1.6220, -75.6140), 
        "demanda": 400, 
        "tipo": "almacen",
        "costo": 150
    }
}

# ============================================================================
# INICIALIZACIÓN DE SESSION STATE
# ============================================================================

def inicializar_session_state():
    """Inicializa todas las variables de session state"""
    if 'puntos_personalizados' not in st.session_state:
        st.session_state.puntos_personalizados = PUNTOS_INICIALES.copy()
    
    if 'lugares_encontrados' not in st.session_state:
        st.session_state.lugares_encontrados = {}
    
    if 'categorias_activas' not in st.session_state:
        st.session_state.categorias_activas = {categoria: True for categoria in CATEGORIAS_LUGARES.keys()}
    
    if 'resultados_distribucion' not in st.session_state:
        st.session_state.resultados_distribucion = None
    
    if 'matriz_distancias' not in st.session_state:
        st.session_state.matriz_distancias = None
    
    if 'rutas_optimizadas' not in st.session_state:
        st.session_state.rutas_optimizadas = {}

    if 'ultimas_coordenadas' not in st.session_state:
        st.session_state.ultimas_coordenadas = {"lat": 1.6145, "lng": -75.6062}

# ============================================================================
# FUNCIONES DEL SISTEMA
# ============================================================================

@st.cache_resource
def cargar_grafo():
    """Carga el grafo de Florencia"""
    try:
        lugar = "Florencia, Caquetá, Colombia"
        G = ox.graph_from_place(lugar, network_type="drive", simplify=True)
        return G
    except:
        centro_florencia = (1.6145, -75.6062)
        G = ox.graph_from_point(centro_florencia, dist=3000, network_type="drive")
        return G

def buscar_lugares_cercanos(lat, lng, radio=2000, tipo=None):
    """Busca lugares cercanos usando Google Places API"""
    if not GOOGLE_PLACES_API_KEY:
        return []
    
    base_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        'location': f'{lat},{lng}',
        'radius': radio,
        'key': GOOGLE_PLACES_API_KEY
    }
    
    if tipo:
        params['type'] = tipo
    
    try:
        response = requests.get(base_url, params=params)
        data = response.json()
        
        if data['status'] == 'OK':
            lugares = []
            for lugar in data['results']:
                lugares.append({
                    'nombre': lugar.get('name', 'Sin nombre'),
                    'direccion': lugar.get('vicinity', 'Dirección no disponible'),
                    'lat': lugar['geometry']['location']['lat'],
                    'lng': lugar['geometry']['location']['lng'],
                    'tipo': lugar.get('types', [])[0] if lugar.get('types') else 'establishment',
                    'rating': lugar.get('rating', 'N/A'),
                    'total_ratings': lugar.get('user_ratings_total', 0)
                })
            return lugares
        else:
            st.warning(f"Error en Places API: {data['status']}")
            return []
    except Exception as e:
        st.error(f"Error al buscar lugares: {str(e)}")
        return []

def buscar_todos_los_lugares():
    """Busca lugares de todas las categorías activas"""
    centro = (1.6145, -75.6062)
    radio_busqueda = 2000
    
    st.session_state.lugares_encontrados = {}
    
    with st.spinner("Buscando lugares en Florencia..."):
        for categoria, tipos in CATEGORIAS_LUGARES.items():
            if st.session_state.categorias_activas.get(categoria, True):
                lugares_categoria = []
                for tipo in tipos:
                    lugares = buscar_lugares_cercanos(centro[0], centro[1], radio_busqueda, tipo)
                    lugares_categoria.extend(lugares)
                    time.sleep(0.1)
                
                st.session_state.lugares_encontrados[categoria] = lugares_categoria
    
    st.success(f"¡Búsqueda completada! Se encontraron {sum(len(lugares) for lugares in st.session_state.lugares_encontrados.values())} lugares")

def obtener_fabricas_almacenes():
    """Obtiene listas de fábricas y almacenes"""
    fabricas = [k for k, v in st.session_state.puntos_personalizados.items() if v["tipo"] == "fabrica"]
    almacenes = [k for k, v in st.session_state.puntos_personalizados.items() if v["tipo"] == "almacen"]
    return fabricas, almacenes

def calcular_matriz_distancias_y_rutas(G):
    """Calcula distancias y rutas entre fábricas y almacenes"""
    distancias = {}
    rutas = {}
    fabricas, almacenes = obtener_fabricas_almacenes()
    
    for fabrica in fabricas:
        for almacen in almacenes:
            coords_fab = st.session_state.puntos_personalizados[fabrica]["coords"]
            coords_alm = st.session_state.puntos_personalizados[almacen]["coords"]
            
            try:
                nodo_fab = ox.distance.nearest_nodes(G, coords_fab[1], coords_fab[0])
                nodo_alm = ox.distance.nearest_nodes(G, coords_alm[1], coords_alm[0])
                
                distancia_metros = nx.shortest_path_length(G, nodo_fab, nodo_alm, weight='length')
                distancia_km = distancia_metros / 1000.0
                distancias[(fabrica, almacen)] = distancia_km
                
                ruta_nodos = nx.shortest_path(G, nodo_fab, nodo_alm, weight='length')
                coords_ruta = [(G.nodes[nodo]['y'], G.nodes[nodo]['x']) for nodo in ruta_nodos]
                rutas[(fabrica, almacen)] = coords_ruta
                
            except Exception as e:
                # Fallback: distancia euclidiana
                dist_euclid = ((coords_fab[0]-coords_alm[0])**2 + (coords_fab[1]-coords_alm[1])**2)**0.5
                distancia_km = dist_euclid * 111.0
                distancias[(fabrica, almacen)] = distancia_km
                rutas[(fabrica, almacen)] = [coords_fab, coords_alm]
    
    return distancias, rutas

def optimizar_distribucion_mejorada():
    """Resuelve el problema de distribución usando costos ingresados"""
    fabricas, almacenes = obtener_fabricas_almacenes()
    
    if not fabricas or not almacenes:
        st.error("❌ No hay suficientes puntos para optimizar")
        return None
    
    # Crear problema de optimización
    prob = LpProblem("Optimizacion_Distribucion_Mejorada", LpMinimize)
    
    # Variables de decisión
    variables = {}
    for fabrica in fabricas:
        for almacen in almacenes:
            var_name = f"X_{fabrica[:10]}_{almacen[:10]}".replace(" ", "_").replace("🏭", "").replace("🏪", "")
            variables[(fabrica, almacen)] = LpVariable(var_name, lowBound=0, cat='Continuous')
    
    # Función objetivo
    funcion_objetivo = []
    for fabrica in fabricas:
        costo_fabrica = st.session_state.puntos_personalizados[fabrica].get("costo", 0)
        for almacen in almacenes:
            costo_almacen = st.session_state.puntos_personalizados[almacen].get("costo", 0)
            costo_total = costo_fabrica + costo_almacen
            funcion_objetivo.append(costo_total * variables[(fabrica, almacen)])
    
    prob += lpSum(funcion_objetivo)
    
    # Restricciones de capacidad
    for fabrica in fabricas:
        capacidad = st.session_state.puntos_personalizados[fabrica]["capacidad"]
        prob += lpSum([variables[(fabrica, a)] for a in almacenes]) <= capacidad, f"Capacidad_{fabrica}"
    
    # Restricciones de demanda
    for almacen in almacenes:
        demanda = st.session_state.puntos_personalizados[almacen]["demanda"]
        prob += lpSum([variables[(f, almacen)] for f in fabricas]) >= demanda, f"Demanda_{almacen}"
    
    # Resolver
    prob.solve(PULP_CBC_CMD(msg=0))
    
    # Extraer resultados
    resultados = {
        'status': LpStatus[prob.status],
        'costo_total': value(prob.objective),
        'asignaciones': {},
        'utilizacion_fabricas': {},
        'satisfaccion_almacenes': {}
    }
    
    # Recopilar asignaciones óptimas
    for (fabrica, almacen), var in variables.items():
        cantidad = value(var)
        if cantidad > 0.001:
            resultados['asignaciones'][(fabrica, almacen)] = cantidad
    
    # Calcular utilización de fábricas
    for fabrica in fabricas:
        total_enviado = sum(value(variables[(fabrica, a)]) for a in almacenes)
        capacidad = st.session_state.puntos_personalizados[fabrica]["capacidad"]
        porcentaje = (total_enviado / capacidad) * 100 if capacidad > 0 else 0
        resultados['utilizacion_fabricas'][fabrica] = {
            'enviado': total_enviado,
            'capacidad': capacidad,
            'porcentaje': min(porcentaje, 100)
        }
    
    # Calcular satisfacción de almacenes
    for almacen in almacenes:
        total_recibido = sum(value(variables[(f, almacen)]) for f in fabricas)
        demanda = st.session_state.puntos_personalizados[almacen]["demanda"]
        porcentaje = (total_recibido / demanda) * 100 if demanda > 0 else 0
        resultados['satisfaccion_almacenes'][almacen] = {
            'recibido': total_recibido,
            'demanda': demanda,
            'porcentaje': min(porcentaje, 100)
        }
    
    return resultados

def exportar_resultados_csv():
    """Exporta los resultados a CSV"""
    if not st.session_state.resultados_distribucion:
        return None
    
    resultados = st.session_state.resultados_distribucion
    datos_exportacion = []
    
    for (fabrica, almacen), cantidad in resultados.get('asignaciones', {}).items():
        if cantidad > 0:
            distancia = st.session_state.matriz_distancias.get((fabrica, almacen), 0)
            costo_fabrica = st.session_state.puntos_personalizados[fabrica].get("costo", 0)
            costo_almacen = st.session_state.puntos_personalizados[almacen].get("costo", 0)
            costo_total_ruta = (costo_fabrica + costo_almacen) * cantidad
            
            datos_exportacion.append({
                'De': fabrica,
                'A': almacen,
                'Cantidad': cantidad,
                'Distancia': distancia,
                'Costo': costo_total_ruta
            })
    
    return pd.DataFrame(datos_exportacion)

def crear_mapa_google_interactivo():
    """Crea el HTML del mapa interactivo"""
    centro = (1.6145, -75.6062)
    
    # Preparar datos para el template
    lugares_data = []
    for categoria, lugares in st.session_state.lugares_encontrados.items():
        if st.session_state.categorias_activas.get(categoria, True):
            for lugar in lugares:
                lugares_data.append({
                    'nombre': lugar['nombre'],
                    'lat': lugar['lat'],
                    'lng': lugar['lng'],
                    'direccion': lugar['direccion'],
                    'tipo': lugar['tipo'],
                    'rating': lugar['rating'],
                    'categoria': categoria
                })
    
    rutas_data = []
    if st.session_state.rutas_optimizadas:
        for (fabrica, almacen), ruta_info in st.session_state.rutas_optimizadas.items():
            if ruta_info and 'coords' in ruta_info:
                rutas_data.append({
                    'coords': ruta_info['coords'],
                    'fabrica': fabrica,
                    'almacen': almacen,
                    'cantidad': ruta_info.get('cantidad', 0),
                    'costo': ruta_info.get('costo', 0)
                })
    
    puntos_personalizados_data = []
    for nombre, datos in st.session_state.puntos_personalizados.items():
        puntos_personalizados_data.append({
            'nombre': nombre,
            'coords': datos['coords'],
            'tipo': datos['tipo'],
            'capacidad': datos.get('capacidad', 0),
            'demanda': datos.get('demanda', 0),
            'costo': datos.get('costo', 0)
        })
    
    # Leer el template y reemplazar variables
    with open('mapa_template.html', 'r', encoding='utf-8') as f:
        template = f.read()
    
    template = template.replace('{GOOGLE_MAPS_API_KEY}', GOOGLE_MAPS_API_KEY)
    template = template.replace('{centro_lat}', str(centro[0]))
    template = template.replace('{centro_lng}', str(centro[1]))
    template = template.replace('{lugares_data}', json.dumps(lugares_data))
    template = template.replace('{rutas_data}', json.dumps(rutas_data))
    template = template.replace('{puntos_personalizados_data}', json.dumps(puntos_personalizados_data))
    
    return template

def manejar_eventos_mapa():
    """Maneja los eventos de JavaScript desde el mapa - VERSIÓN MEJORADA"""
    try:
        # Usar streamlit_js_eval para capturar eventos
        evento = streamlit_js_eval(
            js_expressions="""(function() {
                if (window.mapEvent) {
                    var event = window.mapEvent;
                    window.mapEvent = null;  // Limpiar después de leer
                    return event;
                }
                return null;
            })()""",
            key=f"map_event_listener_{time.time()}"  # KEY ÚNICA cada vez
        )
        
        if evento:
            st.sidebar.write("🔍 Evento capturado:", evento)
            
            # Procesar el evento según su tipo
            if evento.get("type") == "nuevoMarcador":
                nuevo_punto_str = evento.get("data", "{}")
                try:
                    nuevo_punto = json.loads(nuevo_punto_str)
                    st.sidebar.write("📄 JSON deserializado:", nuevo_punto)
                    
                    # Actualizar las últimas coordenadas automáticamente
                    if "coords" in nuevo_punto:
                        st.session_state.ultimas_coordenadas = {
                            "lat": nuevo_punto["coords"][0],
                            "lng": nuevo_punto["coords"][1]
                        }
                        st.sidebar.success(f"📍 Coordenadas actualizadas: {st.session_state.ultimas_coordenadas}")
                    
                except json.JSONDecodeError as e:
                    st.sidebar.error(f"❌ Error al decodificar JSON: {e}")
                    return
                
                if nuevo_punto:
                    # Convertir a formato correcto
                    punto_formateado = {
                        "coords": (nuevo_punto.get("coords", [0, 0])[0], nuevo_punto.get("coords", [0, 0])[1]),
                        "tipo": nuevo_punto.get("tipo", "almacen"),
                        "costo": float(nuevo_punto.get("costo", 0))
                    }
                    
                    if nuevo_punto.get("tipo") == "fabrica":
                        punto_formateado["capacidad"] = int(nuevo_punto.get("capacidad", 0))
                    else:
                        punto_formateado["demanda"] = int(nuevo_punto.get("demanda", 0))
                    
                    nombre_punto = nuevo_punto.get("nombre", f"Punto_{int(time.time())}")
                    st.session_state.puntos_personalizados[nombre_punto] = punto_formateado
                    
                    st.sidebar.success(f"✅ Punto agregado: {nombre_punto}")
                    st.sidebar.write(f"📊 Total puntos ahora: {len(st.session_state.puntos_personalizados)}")
                    st.rerun()
            
            elif evento.get("type") == "eliminarMarcador":
                data_str = evento.get("data", "{}")
                try:
                    data = json.loads(data_str)
                    nombre = data.get("nombre", "")
                    st.sidebar.write("🗑️ Eliminando punto:", nombre)
                except json.JSONDecodeError as e:
                    st.sidebar.error(f"❌ Error al decodificar JSON: {e}")
                    return
                
                if nombre and nombre in st.session_state.puntos_personalizados:
                    del st.session_state.puntos_personalizados[nombre]
                    st.sidebar.success(f"🗑️ Punto eliminado: {nombre}")
                    st.sidebar.write(f"📊 Total puntos ahora: {len(st.session_state.puntos_personalizados)}")
                    st.rerun()
                    
    except Exception as e:
        st.sidebar.error(f"❌ Error manejando evento: {str(e)}")

# ============================================================================
# INTERFAZ PRINCIPAL
# ============================================================================

def main():
    st.set_page_config(
        page_title="Optimización de Distribución - Florencia",
        page_icon="🚚",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # CSS personalizado
    st.markdown("""
    <style>
        .main-title { text-align: center; color: #1E3A8A; font-size: 2.5rem; font-weight: bold; }
        .sub-title { text-align: center; color: #64748B; font-size: 1.2rem; margin-bottom: 2rem; }
        .metric-card { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1.5rem; border-radius: 10px; color: white; text-align: center; }
        .places-category { background-color: #f8f9fa; padding: 8px 12px; margin: 5px 0; border-radius: 5px; border-left: 4px solid #007bff; }
    </style>
    """, unsafe_allow_html=True)
    
    # Inicializar estado
    inicializar_session_state()
    manejar_eventos_mapa()
    
    # Encabezado
    st.markdown('<p class="main-title">🚚 Sistema de Optimización de Distribución</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-title">Google Maps + Costos Manuales + Optimización Lineal</p>', unsafe_allow_html=True)
    st.markdown("---")
    
    # Cargar grafo
    G = cargar_grafo()
    
    # Barra lateral
    with st.sidebar:
        st.markdown("### 📋 Panel de Control")
        
        # Configuración de búsqueda
        with st.expander("⚙️ Configurar Búsqueda"):
            st.markdown("**Categorías a mostrar:**")
            for categoria in CATEGORIAS_LUGARES.keys():
                st.session_state.categorias_activas[categoria] = st.checkbox(
                    categoria, 
                    value=st.session_state.categorias_activas.get(categoria, True),
                    key=f"cat_{categoria}"
                )
            
            if st.button("🔄 Actualizar Búsqueda", use_container_width=True):
                buscar_todos_los_lugares()
        
        if st.button("🔎 Buscar Todos los Lugares", type="primary", use_container_width=True):
            buscar_todos_los_lugares()
        
        st.markdown("---")
        st.markdown("#### 📍 Gestión de Puntos")
        
        # Formulario para agregar puntos manualmente
        with st.expander("➕ Agregar Punto Manualmente"):
            with st.form("agregar_punto", clear_on_submit=True):
                nombre = st.text_input("Nombre del punto*", placeholder="Ej: Mi Fábrica")
                tipo = st.selectbox("Tipo*", ["fabrica", "almacen"])
                
                lat = st.number_input("Latitud*",
                                      value=st.session_state.ultimas_coordenadas["lat"], 
                                      format="%.6f",
                                      key="input_lat")
                lng = st.number_input("Longitud*",
                                      value=st.session_state.ultimas_coordenadas["lng"], 
                                      format="%.6f", 
                                      key="input_lng")

                
                if tipo == "fabrica":
                    capacidad = st.number_input("Capacidad*", min_value=1, value=1000)
                else:
                    demanda = st.number_input("Demanda*", min_value=1, value=300)
                
                costo = st.number_input("Costo por unidad (COP)*", min_value=0, value=1000, step=100)
                
                if st.form_submit_button("✅ Agregar Punto", use_container_width=True):
                    if nombre and tipo and lat and lng and costo:
                        nuevo_punto = {
                            "coords": (lat, lng),
                            "tipo": tipo,
                            "costo": costo
                        }
                        
                        if tipo == "fabrica":
                            nuevo_punto["capacidad"] = capacidad
                        else:
                            nuevo_punto["demanda"] = demanda
                        
                        st.session_state.puntos_personalizados[nombre] = nuevo_punto
                        st.success(f"✅ Punto '{nombre}' agregado correctamente")
                        st.rerun()
        
        # Eliminar puntos
        with st.expander("🗑️ Eliminar Puntos"):
            if st.session_state.puntos_personalizados:
                puntos_a_eliminar = st.multiselect(
                    "Selecciona puntos para eliminar:",
                    list(st.session_state.puntos_personalizados.keys())
                )
                
                if st.button("🗑️ Eliminar Seleccionados", use_container_width=True) and puntos_a_eliminar:
                    for punto in puntos_a_eliminar:
                        if punto in st.session_state.puntos_personalizados:
                            del st.session_state.puntos_personalizados[punto]
                    st.success(f"✅ {len(puntos_a_eliminar)} puntos eliminados")
                    st.rerun()
            else:
                st.info("No hay puntos para eliminar")
        
        st.markdown("---")
        st.markdown("#### 🎯 Optimización")
        
        fabricas, almacenes = obtener_fabricas_almacenes()
        
        if fabricas and almacenes:
            total_capacidad = sum(st.session_state.puntos_personalizados[f]["capacidad"] for f in fabricas)
            total_demanda = sum(st.session_state.puntos_personalizados[a]["demanda"] for a in almacenes)
            
            st.metric("Total Capacidad", total_capacidad)
            st.metric("Total Demanda", total_demanda)
            
            if total_capacidad < total_demanda:
                st.error("❌ Demanda excede capacidad")
            else:
                st.success("✅ Sistema factible")
            
            if st.button("🚀 EJECUTAR OPTIMIZACIÓN", type="primary", use_container_width=True):
                with st.spinner("Calculando rutas óptimas..."):
                    st.session_state.matriz_distancias, rutas_completas = calcular_matriz_distancias_y_rutas(G)
                    st.session_state.resultados_distribucion = optimizar_distribucion_mejorada()
                    
                    st.session_state.rutas_optimizadas = {}
                    if st.session_state.resultados_distribucion and 'asignaciones' in st.session_state.resultados_distribucion:
                        for (fabrica, almacen), cantidad in st.session_state.resultados_distribucion['asignaciones'].items():
                            if cantidad > 0:
                                costo_fabrica = st.session_state.puntos_personalizados[fabrica].get("costo", 0)
                                costo_almacen = st.session_state.puntos_personalizados[almacen].get("costo", 0)
                                costo_total_ruta = (costo_fabrica + costo_almacen) * cantidad
                                
                                st.session_state.rutas_optimizadas[(fabrica, almacen)] = {
                                    'coords': rutas_completas.get((fabrica, almacen), []),
                                    'cantidad': cantidad,
                                    'costo': costo_total_ruta
                                }
                    
                st.success("✅ Optimización completada!")
                
                df_export = exportar_resultados_csv()
                if df_export is not None and not df_export.empty:
                    csv = df_export.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Descargar Resultados (CSV)",
                        data=csv,
                        file_name=f"optimizacion_distribucion_{pd.Timestamp.now().strftime('%Y-%m-%d_%H-%M')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
        
        st.markdown("---")
        st.markdown("#### 📊 Estadísticas")
        total_lugares = sum(len(lugares) for lugares in st.session_state.lugares_encontrados.values())
        st.info(f"**Fábricas:** {len(fabricas)}\n**Almacenes:** {len(almacenes)}\n**Lugares encontrados:** {total_lugares}")
    
    # Contenido principal
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### 🗺️ Mapa Interactivo - Rutas Optimizadas")
        st.markdown("""
        **Leyenda:**
        - 🏭 **Fábricas**: Iconos de fábrica
        - 🏪 **Almacenes**: Iconos de almacén  
        - 🏥 **Salud**: Rojo | 🛒 **Comercios**: Azul | 🍽️ **Restaurantes**: Verde
        - 🏫 **Educación**: Amarillo | 🏦 **Servicios**: Púrpura | ⛪ **Religión**: Naranja
        - 🎭 **Entretenimiento**: Rosa | 🏨 **Hospedaje**: Azul claro | 🚗 **Transporte**: Blanco
        - **Rutas Optimizadas**: Líneas de colores (haz clic para ver detalles)
        """)
        
        mapa_html = crear_mapa_google_interactivo()
        st.components.v1.html(mapa_html, height=600, scrolling=False)
    
    with col2:
        st.markdown("### 📊 Resultados de Optimización")
        
        if st.session_state.resultados_distribucion:
            resultados = st.session_state.resultados_distribucion
            
            st.success(f"✅ {resultados['status']}")
            st.metric("💰 Costo Total", f"${resultados['costo_total']:,.0f} COP")
            
            # Mostrar asignaciones
            st.markdown("#### 📦 Asignaciones Óptimas")
            if resultados['asignaciones']:
                datos_asignaciones = []
                for (fabrica, almacen), cantidad in resultados['asignaciones'].items():
                    distancia = st.session_state.matriz_distancias.get((fabrica, almacen), 0)
                    costo_fabrica = st.session_state.puntos_personalizados[fabrica].get("costo", 0)
                    costo_almacen = st.session_state.puntos_personalizados[almacen].get("costo", 0)
                    costo_total_ruta = (costo_fabrica + costo_almacen) * cantidad
                    
                    datos_asignaciones.append({
                        'De': fabrica,
                        'A': almacen,
                        'Cantidad': f"{cantidad:.0f}",
                        'Distancia': f"{distancia:.1f} km",
                        'Costo': f"${costo_total_ruta:,.0f} COP"
                    })
                
                df_asignaciones = pd.DataFrame(datos_asignaciones)
                st.dataframe(df_asignaciones, use_container_width=True, height=300)
                
                st.metric("📦 Total Rutas Activas", len(resultados['asignaciones']))
                st.metric("🚚 Total Unidades Transportadas", sum(resultados['asignaciones'].values()))
            
            # Utilización de fábricas
            st.markdown("#### 🏭 Utilización de Fábricas")
            for fabrica, datos in resultados['utilizacion_fabricas'].items():
                porcentaje = datos['porcentaje']
                st.write(f"**{fabrica}**")
                st.progress(porcentaje/100, text=f"{datos['enviado']:.0f}/{datos['capacidad']} ({porcentaje:.1f}%)")
            
            # Satisfacción de demanda
            st.markdown("#### 🏪 Satisfacción de Demanda")
            for almacen, datos in resultados['satisfaccion_almacenes'].items():
                porcentaje = datos['porcentaje']
                st.write(f"**{almacen}**")
                st.progress(porcentaje/100, text=f"{datos['recibido']:.0f}/{datos['demanda']} ({porcentaje:.1f}%)")
        
        else:
            st.info("👈 Configura los puntos y ejecuta la optimización")
            
            # Mostrar puntos actuales
            st.markdown("#### 📍 Puntos Actuales")
            if st.session_state.puntos_personalizados:
                for nombre, datos in st.session_state.puntos_personalizados.items():
                    tipo_icono = "🏭" if datos["tipo"] == "fabrica" else "🏪"
                    st.write(f"{tipo_icono} **{nombre}**")
                    st.write(f"  📍 {datos['coords'][0]:.4f}, {datos['coords'][1]:.4f}")
                    if datos["tipo"] == "fabrica":
                        st.write(f"  📦 Capacidad: {datos['capacidad']}")
                    else:
                        st.write(f"  🎯 Demanda: {datos['demanda']}")
                    st.write(f"  💰 Costo por unidad: ${datos.get('costo', 0):,} COP")
                    st.write("---")
        
        # Mostrar lugares encontrados
        st.markdown("#### 📍 Lugares Encontrados")
        total_lugares = sum(len(lugares) for lugares in st.session_state.lugares_encontrados.values())
        
        if total_lugares > 0:
            for categoria, lugares in st.session_state.lugares_encontrados.items():
                if lugares:
                    with st.expander(f"{categoria} ({len(lugares)} lugares)"):
                        for lugar in lugares[:5]:
                            st.markdown(f"""
                            <div class="places-category">
                                <strong>{lugar['nombre']}</strong><br>
                                <small>📍 {lugar['direccion']}</small><br>
                                <small>⭐ {lugar['rating']} • 🏷️ {lugar['tipo']}</small>
                            </div>
                            """, unsafe_allow_html=True)
                        if len(lugares) > 5:
                            st.info(f"... y {len(lugares) - 5} más")
        else:
            st.info("👈 Haz clic en 'Buscar Todos los Lugares' para cargar los establecimientos")
    
    # Footer
    st.markdown("---")
    st.markdown("**🎓 Universidad de la Amazonia** | **📍 Florencia, Caquetá** | **💰 Pesos Colombianos (COP)**")

if __name__ == "__main__":
    main()