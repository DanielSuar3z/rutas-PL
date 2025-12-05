#  Sistema de Optimización de Distribución - Florencia, Caquetá

![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Google Maps](https://img.shields.io/badge/Google_Maps-4285F4?style=for-the-badge&logo=google-maps&logoColor=white)

##  Descripción

Sistema web inteligente para la optimización de rutas de distribución en Florencia, Caquetá, Colombia. Combina algoritmos de programación lineal, integración con Google Maps API y análisis geoespacial para minimizar costos logísticos y maximizar la eficiencia en la distribución de productos.

##  Características Principales

###  **Mapa Interactivo Inteligente**
- Visualización de fábricas, almacenes y puntos de interés
- Marcadores personalizables con clics en el mapa
- Rutas optimizadas visualizadas con colores diferenciados
- Búsqueda automática de establecimientos por categorías

###  **Motor de Optimización Avanzado**
- Modelo de programación lineal para minimización de costos
- Consideración de capacidades de fábricas y demandas de almacenes
- Cálculo de rutas reales usando datos de OpenStreetMap
- Exportación de resultados en formato CSV

###  **Gestión Flexible de Puntos**
- Agregar/eliminar fábricas y almacenes dinámicamente
- Formulario manual para ingreso preciso de datos
- Captura automática de coordenadas desde el mapa
- Costos personalizables por unidad

###  **Panel de Control Integral**
- Configuración de categorías de búsqueda
- Métricas en tiempo real de capacidad y demanda
- Visualización de utilización y satisfacción
- Estadísticas detalladas de optimización

## Tecnologías Utilizadas

| Componente | Tecnología |
|------------|------------|
| **Backend** | Python 3.9+ |
| **Frontend** | Streamlit |
| **Optimización** | PuLP (Programación Lineal) |
| **Mapas** | Google Maps JavaScript API, OSMnx, Folium |
| **Geoespacial** | NetworkX, GeoPandas |
| **Visualización** | Pandas, NumPy, Matplotlib |
| **APIs** | Google Places API |

## Instalación y Configuración

### Prerrequisitos
```bash
Python 3.9 o superior
API Key de Google Maps (con Places API habilitado)
```

### 1. Clonar el repositorio
```bash
git clone https://github.com/tu-usuario/optimizacion-distribucion.git
cd optimizacion-distribucion
```

### 2. Crear entorno virtual
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```


### 3. Configurar API Keys
Crear un archivo `.env` en la raíz del proyecto:
```env
GOOGLE_MAPS_API_KEY=tu_api_key_aqui
GOOGLE_PLACES_API_KEY=tu_api_key_aqui
```

### 4. Ejecutar la aplicación
```bash
streamlit run app.py
```

## 📖 Uso del Sistema

### 1. **Inicialización**
- La aplicación carga con puntos predeterminados en Florencia
- Se muestra un mapa interactivo con fábricas y almacenes base

### 2. **Agregar Nuevos Puntos**
- **Método 1**: Clic en el mapa + completar formulario emergente
- **Método 2**: Formulario manual en la barra lateral
- Especificar: nombre, tipo (fábrica/almacén), capacidad/demanda, costo

### 3. **Buscar Establecimientos**
- Configurar categorías activas en el panel lateral
- Ejecutar búsqueda automática de lugares cercanos
- Los resultados se muestran por categoría con información detallada

### 4. **Ejecutar Optimización**
- Verificar que capacidad total ≥ demanda total
- Ejecutar algoritmo de optimización
- Visualizar rutas óptimas en el mapa
- Analizar resultados en el panel derecho


## 📁 Estructura del Proyecto

```
rutas-PL/
│
├── app.py                    # Aplicación principal Streamlit
├── mapa_template.html        # Template HTML/JavaScript del mapa
├── README.md                # Este archivo

```

## 🔧 Configuración Avanzada

### Personalizar Puntos Iniciales
Modificar el diccionario `PUNTOS_INICIALES` en `app.py`:
```python
PUNTOS_INICIALES = {
    "Nombre del punto": {
        "coords": (latitud, longitud),
        "capacidad": 1000,        # Para fábricas
        "demanda": 300,           # Para almacenes
        "tipo": "fabrica",        # "fabrica" o "almacen"
        "costo": 1500             # Costo por unidad
    }
}
```

### Ajustar Parámetros de Búsqueda
- Radio de búsqueda: Modificar `radio_busqueda` en `buscar_todos_los_lugares()`
- Categorías: Editar `CATEGORIAS_LUGARES` en `app.py`

## 📊 Métricas de Optimización

El sistema calcula y muestra:
- **Costo total mínimo** en pesos colombianos (COP)
- **Utilización de fábricas** (porcentaje de capacidad usada)
- **Satisfacción de demanda** (porcentaje cubierto)
- **Asignaciones óptimas** por ruta
- **Distancias reales** entre nodos

## 🤝 Contribuciones

¡Las contribuciones son bienvenidas! Por favor:

1. Fork el repositorio
2. Crear una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abrir un Pull Request


##  Autores

- **Tu Nombre** - [@tu-usuario](https://github.com/tu-usuario)
- **Universidad de la Amazonia** - Florencia, Caquetá


---

Proyecto Académico - Universidad de la Amazonia  
Ubicación - Florencia, Caquetá, Colombia  

---
*Si este proyecto te resulta útil, ¡considera darle una estrella ⭐ en GitHub!*
