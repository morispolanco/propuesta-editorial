import streamlit as st
import requests
import json
import time
import os
import re
from datetime import datetime
import base64
import markdown

# Configuración de la página
st.set_page_config(
    page_title="Generador de Libros",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Función para capitalizar títulos en español
def capitalizar_titulo_espanol(titulo):
    # Dividir el título en palabras
    palabras = titulo.split()
    # Capitalizar solo la primera palabra y los nombres propios
    if len(palabras) > 0:
        palabras[0] = palabras[0].capitalize()
        # Detectar nombres propios (simplificado - en una implementación real se necesitaría NLP más avanzado)
        nombres_propios = ["España", "América", "Europa", "Asia", "África", "México", "Argentina", "Colombia", "Chile", "Perú"]
        for i in range(1, len(palabras)):
            if palabras[i] in nombres_propios:
                palabras[i] = palabras[i].capitalize()
    return " ".join(palabras)

# Función para llamar a la API de OpenRouter
def llamar_api_openrouter(mensaje, api_key, model="openai/gpt-4o-mini"):
    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://generador-de-libros.streamlit.app",
                "X-Title": "Generador de Libros",
            },
            data=json.dumps({
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": "Eres un asistente experto en escritura de libros. Todas tus respuestas deben estar en español. Sigue estrictamente las instrucciones proporcionadas."
                    },
                    {
                        "role": "user",
                        "content": mensaje
                    }
                ],
            })
        )
        
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            st.error(f"Error en la API: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        st.error(f"Error al llamar a la API: {str(e)}")
        return None

# Función para generar tabla de contenidos
def generar_tabla_contenidos(propuesta, api_key):
    prompt = f"""
    Basado en la siguiente propuesta editorial, genera una tabla de contenidos detallada para un libro.
    
    Propuesta editorial:
    {propuesta}
    
    Requisitos:
    - El libro debe tener entre 9 y 30 capítulos.
    - Cada capítulo debe tener un título descriptivo.
    - Los títulos deben seguir las reglas de capitalización en español (solo la primera palabra y nombres propios con mayúscula inicial).
    - La estructura debe ser coherente y lógica.
    - Proporciona también un título adecuado para el libro.
    
    Formato de respuesta:
    Título del libro: [Título propuesto]
    
    Tabla de contenidos:
    1. [Título del capítulo 1]
    2. [Título del capítulo 2]
    ...
    """
    
    respuesta = llamar_api_openrouter(prompt, api_key)
    return respuesta

# Función para generar un capítulo
def generar_capitulo(titulo_libro, num_capitulo, titulo_capitulo, propuesta, api_key, capitulos_previos=""):
    prompt = f"""
    Escribe el capítulo {num_capitulo} del libro "{titulo_libro}".
    
    Título del capítulo: {titulo_capitulo}
    
    Propuesta editorial original:
    {propuesta}
    
    Requisitos:
    - El capítulo debe tener entre 1200 y 1500 palabras.
    - El contenido debe ser coherente con la propuesta editorial.
    - Si incluyes citas, estas deben ser reales y verificables. No inventes citas.
    - Mantén un estilo consistente con el resto del libro.
    - Escribe completamente en español.
    
    {"Capítulos anteriores para referencia de estilo y continuidad:" if capitulos_previos else ""}
    {capitulos_previos if capitulos_previos else ""}
    
    Por favor, escribe el capítulo completo sin truncar.
    """
    
    respuesta = llamar_api_openrouter(prompt, api_key)
    return respuesta

# Función para guardar progreso
def guardar_progreso(datos, api_key):
    # Crear directorio si no existe
    if not os.path.exists("proyectos_guardados"):
        os.makedirs("proyectos_guardados")
    
    # Generar nombre de archivo basado en timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_archivo = f"proyectos_guardados/proyecto_{timestamp}.json"
    
    # Guardar datos
    with open(nombre_archivo, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
    
    return nombre_archivo

# Función para cargar progreso
def cargar_progreso(archivo, api_key):
    try:
        with open(archivo, "r", encoding="utf-8") as f:
            datos = json.load(f)
        return datos
    except Exception as e:
        st.error(f"Error al cargar el archivo: {str(e)}")
        return None

# Función para exportar a Markdown
def exportar_markdown(titulo_libro, tabla_contenidos, capitulos):
    # Crear contenido Markdown
    contenido_md = f"# {titulo_libro}\n\n"
    
    # Añadir tabla de contenidos
    contenido_md += "## Tabla de Contenidos\n\n"
    contenido_md += tabla_contenidos + "\n\n"
    
    # Añadir capítulos
    for i, capitulo in enumerate(capitulos, 1):
        contenido_md += f"# Capítulo {i}\n\n"
        contenido_md += capitulo + "\n\n"
    
    return contenido_md

# Función para crear enlace de descarga
def crear_enlace_descarga(contenido, nombre_archivo):
    b64 = base64.b64encode(contenido.encode()).decode()
    href = f'<a href="data:file/markdown;base64,{b64}" download="{nombre_archivo}">Descargar archivo Markdown</a>'
    return href

# Interfaz de usuario
st.title("📚 Generador de Libros a partir de Propuestas Editoriales")
st.markdown("Esta aplicación te permite generar libros completos a partir de una propuesta editorial.")

# Barra lateral para configuración
st.sidebar.header("Configuración")

# Input para API Key
api_key = st.sidebar.text_input("Introduce tu API Key de OpenRouter:", type="password")

# Selector de modelo
model_options = [
    "openai/gpt-4o-mini",
    "openai/gpt-3.5-turbo",
    "anthropic/claude-3-haiku",
    "meta-llama/llama-3-8b-instruct"
]
selected_model = st.sidebar.selectbox("Selecciona el modelo:", model_options)

# Opciones de carga/guardado
st.sidebar.subheader("Progreso del proyecto")
cargar_proyecto = st.sidebar.file_uploader("Cargar proyecto guardado", type=["json"])

# Inicializar estado de la sesión
if "propuesta" not in st.session_state:
    st.session_state.propuesta = ""
if "tabla_contenidos" not in st.session_state:
    st.session_state.tabla_contenidos = ""
if "titulo_libro" not in st.session_state:
    st.session_state.titulo_libro = ""
if "capitulos" not in st.session_state:
    st.session_state.capitulos = []
if "capitulo_actual" not in st.session_state:
    st.session_state.capitulo_actual = 0
if "proyecto_cargado" not in st.session_state:
    st.session_state.proyecto_cargado = False

# Cargar proyecto si se selecciona un archivo
if cargar_proyecto and not st.session_state.proyecto_cargado:
    datos_proyecto = cargar_proyecto(cargar_proyecto, api_key)
    if datos_proyecto:
        st.session_state.propuesta = datos_proyecto.get("propuesta", "")
        st.session_state.tabla_contenidos = datos_proyecto.get("tabla_contenidos", "")
        st.session_state.titulo_libro = datos_proyecto.get("titulo_libro", "")
        st.session_state.capitulos = datos_proyecto.get("capitulos", [])
        st.session_state.capitulo_actual = datos_proyecto.get("capitulo_actual", 0)
        st.session_state.proyecto_cargado = True
        st.success("Proyecto cargado correctamente")
        st.rerun()

# Sección 1: Introducción de la propuesta editorial
st.header("1. Introducir Propuesta Editorial")
propuesta = st.text_area(
    "Pega o escribe tu propuesta editorial completa:",
    height=200,
    value=st.session_state.propuesta
)

if st.button("Analizar Propuesta") and api_key:
    if not propuesta.strip():
        st.error("Por favor, introduce una propuesta editorial válida.")
    else:
        st.session_state.propuesta = propuesta
        with st.spinner("Generando tabla de contenidos..."):
            st.session_state.tabla_contenidos = generar_tabla_contenidos(propuesta, api_key)
            
            # Extraer título del libro
            if "Título del libro:" in st.session_state.tabla_contenidos:
                titulo_match = re.search(r"Título del libro: (.+)", st.session_state.tabla_contenidos)
                if titulo_match:
                    st.session_state.titulo_libro = capitalizar_titulo_espanol(titulo_match.group(1).strip())
            
            # Guardar progreso
            datos_proyecto = {
                "propuesta": st.session_state.propuesta,
                "tabla_contenidos": st.session_state.tabla_contenidos,
                "titulo_libro": st.session_state.titulo_libro,
                "capitulos": st.session_state.capitulos,
                "capitulo_actual": st.session_state.capitulo_actual
            }
            guardar_progreso(datos_proyecto, api_key)
        
        st.success("Tabla de contenidos generada correctamente.")
        st.rerun()

# Sección 2: Revisión de la tabla de contenidos
if st.session_state.tabla_contenidos:
    st.header("2. Revisión de la Tabla de Contenidos")
    st.subheader(f"Título Propuesto: {st.session_state.titulo_libro}")
    st.text_area("Tabla de Contenidos:", st.session_state.tabla_contenidos, height=300)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Aprobar Tabla de Contenidos"):
            st.session_state.tabla_aprobada = True
            st.success("Tabla de contenidos aprobada. Pasa a la siguiente sección para generar los capítulos.")
            st.rerun()
    
    with col2:
        if st.button("Regenerar Tabla de Contenidos") and api_key:
            with st.spinner("Regenerando tabla de contenidos..."):
                st.session_state.tabla_contenidos = generar_tabla_contenidos(st.session_state.propuesta, api_key)
                
                # Extraer título del libro
                if "Título del libro:" in st.session_state.tabla_contenidos:
                    titulo_match = re.search(r"Título del libro: (.+)", st.session_state.tabla_contenidos)
                    if titulo_match:
                        st.session_state.titulo_libro = capitalizar_titulo_espanol(titulo_match.group(1).strip())
                
                # Guardar progreso
                datos_proyecto = {
                    "propuesta": st.session_state.propuesta,
                    "tabla_contenidos": st.session_state.tabla_contenidos,
                    "titulo_libro": st.session_state.titulo_libro,
                    "capitulos": st.session_state.capitulos,
                    "capitulo_actual": st.session_state.capitulo_actual
                }
                guardar_progreso(datos_proyecto, api_key)
            
            st.success("Tabla de contenidos regenerada.")
            st.rerun()

# Sección 3: Generación de capítulos
if st.session_state.tabla_contenidos and "tabla_aprobada" in st.session_state and st.session_state.tabla_aprobada:
    st.header("3. Generación de Capítulos")
    
    # Extraer títulos de capítulos de la tabla de contenidos
    lineas = st.session_state.tabla_contenidos.split('\n')
    titulos_capitulos = []
    
    for linea in lineas:
        # Buscar patrones como "1. Título del capítulo"
        match = re.match(r'^\d+\.\s+(.+)$', linea.strip())
        if match:
            titulos_capitulos.append(match.group(1))
    
    # Mostrar progreso
    st.progress(st.session_state.capitulo_actual / len(titulos_capitulos))
    st.write(f"Capítulo actual: {st.session_state.capitulo_actual + 1} de {len(titulos_capitulos)}")
    
    # Generar siguiente capítulo
    if st.session_state.capitulo_actual < len(titulos_capitulos):
        if st.button(f"Generar Capítulo {st.session_state.capitulo_actual + 1}") and api_key:
            titulo_capitulo = titulos_capitulos[st.session_state.capitulo_actual]
            
            # Obtener capítulos anteriores para referencia
            capitulos_previos = ""
            if st.session_state.capitulos:
                # Solo incluir los últimos 2 capítulos para no exceder el límite de tokens
                capitulos_previos = "\n\n".join(st.session_state.capitulos[-2:])
            
            with st.spinner(f"Escribiendo capítulo {st.session_state.capitulo_actual + 1}..."):
                capitulo = generar_capitulo(
                    st.session_state.titulo_libro,
                    st.session_state.capitulo_actual + 1,
                    titulo_capitulo,
                    st.session_state.propuesta,
                    api_key,
                    capitulos_previos
                )
                
                if capitulo:
                    st.session_state.capitulos.append(capitulo)
                    st.session_state.capitulo_actual += 1
                    
                    # Guardar progreso
                    datos_proyecto = {
                        "propuesta": st.session_state.propuesta,
                        "tabla_contenidos": st.session_state.tabla_contenidos,
                        "titulo_libro": st.session_state.titulo_libro,
                        "capitulos": st.session_state.capitulos,
                        "capitulo_actual": st.session_state.capitulo_actual
                    }
                    guardar_progreso(datos_proyecto, api_key)
                    
                    st.success(f"Capítulo {st.session_state.capitulo_actual} generado correctamente.")
                    st.rerun()
    else:
        st.success("¡Todos los capítulos han sido generados!")
        
        # Sección 4: Exportación
        st.header("4. Exportación del Libro")
        
        # Generar contenido Markdown
        contenido_md = exportar_markdown(
            st.session_state.titulo_libro,
            st.session_state.tabla_contenidos,
            st.session_state.capitulos
        )
        
        # Mostrar vista previa
        st.subheader("Vista Previa")
        st.markdown(contenido_md[:1000] + "..." if len(contenido_md) > 1000 else contenido_md)
        
        # Botón de descarga
        nombre_archivo = f"{st.session_state.titulo_libro.replace(' ', '_')}.md"
        st.markdown(crear_enlace_descarga(contenido_md, nombre_archivo), unsafe_allow_html=True)

# Pie de página
st.markdown("---")
st.markdown("Creado con Streamlit y OpenRouter API. Todos los derechos reservados.")
