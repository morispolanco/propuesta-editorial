import streamlit as st
import os
import json
import re
from datetime import datetime
import base64
import markdown
# Importaciones de la API de Google
from google import genai
from google.genai import types

# Configuración de la página
st.set_page_config(
    page_title="Generador de Libros",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- NUEVA FUNCIÓN PARA CONTAR PALABRAS ---
def contar_palabras(texto):
    """Cuenta el número de palabras en un texto."""
    if not texto:
        return 0
    texto_limpio = texto.replace('\n', ' ')
    return len(texto_limpio.split())

# --- FUNCIÓN DE API MODIFICADA ---
# Ahora recibe el cliente como parámetro en lugar de crearlo.
def llamar_api_gemini(mensaje, client):
    """
    Llama a la API de Gemini con streaming y habilita Google Search.
    """
    if not client:
        st.error("El cliente de Gemini no está inicializado. Introduce tu API Key.")
        return None
    try:
        model = "gemini-flash-latest"
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=mensaje),
                ],
            ),
        ]
        tools = [
            types.Tool(googleSearch=types.GoogleSearch()),
        ]
        generate_content_config = types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_budget=-1),
            tools=tools,
        )

        stream = client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=generate_content_config,
        )
        return stream
    except Exception as e:
        st.error(f"Error al llamar a la API de Gemini: {str(e)}")
        return None

# Función para capitalizar títulos en español
def capitalizar_titulo_espanol(titulo):
    palabras = titulo.split()
    if len(palabras) > 0:
        palabras[0] = palabras[0].capitalize()
        nombres_propios = ["España", "América", "Europa", "Asia", "África", "México", "Argentina", "Colombia", "Chile", "Perú"]
        for i in range(1, len(palabras)):
            if palabras[i] in nombres_propios:
                palabras[i] = palabras[i].capitalize()
    return " ".join(palabras)

# --- FUNCIONES DE GENERACIÓN AHORA USAN EL CLIENTE DE LA SESIÓN ---
def generar_tabla_contenidos(propuesta, client):
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
    return llamar_api_gemini(prompt, client)

def modificar_tabla_contenidos(propuesta, tabla_actual, cambios_solicitados, client):
    prompt = f"""
    A continuación, te presento una propuesta editorial y una tabla de contenidos generada previamente.
    
    Propuesta editorial original:
    {propuesta}
    
    Tabla de contenidos actual:
    {tabla_actual}
    
    El usuario ha solicitado los siguientes cambios:
    {cambios_solicitados}
    
    Por favor, modifica la tabla de contenidos para incorporar estos cambios de manera coherente.
    
    Requisitos:
    - Mantén el número de capítulos entre 9 y 30.
    - Asegúrate de que los títulos sigan las reglas de capitalización en español.
    - La estructura resultante debe ser lógica y reflejar tanto la propuesta original como los cambios solicitados.
    - Si los cambios lo justifican, puedes proponer un nuevo título para el libro.
    
    Formato de respuesta:
    Título del libro: [Título propuesto]
    
    Tabla de contenidos:
    1. [Título del capítulo 1]
    2. [Título del capítulo 2]
    ...
    """
    return llamar_api_gemini(prompt, client)

def modificar_capitulo(contenido_actual, titulo_libro, num_capitulo, titulo_capitulo, propuesta, cambios, client):
    prompt = f"""
    Eres un editor experto. A continuación, te presento el capítulo {num_capitulo} de un libro.
    
    Título del libro: {titulo_libro}
    Título del capítulo: {titulo_capitulo}
    
    Contenido actual del capítulo:
    ---
    {contenido_actual}
    ---
    
    Propuesta editorial original para contexto:
    {propuesta}
    
    El usuario ha solicitado los siguientes cambios para este capítulo:
    {cambios}
    
    Por favor, reescribe el capítulo aplicando los cambios solicitados.
    
    Requisitos:
    - Mantén la extensión del capítulo entre 2000 y 2500 palabras.
    - El contenido modificado debe ser coherente con el resto del libro.
    - Si incluyes citas, estas deben ser reales y verificables. Usa la búsqueda si es necesario.
    - **CRÍTICO: Asegúrate de que el capítulo esté completo y no termine a mitad de una frase o idea. La respuesta debe ser el capítulo completo, desde el principio hasta el final, sin truncamientos.**
    """
    return llamar_api_gemini(prompt, client)

def generar_capitulo(titulo_libro, num_capitulo, titulo_capitulo, propuesta, client, capitulos_previos=""):
    prompt = f"""
    Escribe el capítulo {num_capitulo} del libro "{titulo_libro}".
    
    Título del capítulo: {titulo_capitulo}
    
    Propuesta editorial original:
    {propuesta}
    
    Requisitos:
    - El capítulo debe tener entre 2000 y 2500 palabras.
    - El contenido debe ser coherente con la propuesta editorial y el título del capítulo.
    - Si incluyes citas, estas deben ser reales y verificables. Usa la búsqueda de Google para encontrar y verificar información si es necesario.
    - Mantén un estilo consistente con el resto del libro.
    - Escribe completamente en español.
    - **CRÍTICO: Asegúrate de que el capítulo esté completo y no termine a mitad de una frase o idea. La respuesta debe ser el capítulo completo, desde el principio hasta el final, sin truncamientos.**
    
    {"Capítulos anteriores para referencia de estilo y continuidad:" if capitulos_previos else ""}
    {capitulos_previos if capitulos_previos else ""}
    
    Por favor, escribe el capítulo completo sin truncar.
    """
    return llamar_api_gemini(prompt, client)

# --- FUNCIÓN DE GUARDADO MODIFICADA ---
# Función para guardar progreso
def guardar_progreso(datos):
    if not os.path.exists("proyectos_guardados"):
        os.makedirs("proyectos_guardados")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_archivo = f"proyectos_guardados/proyecto_{timestamp}.json"
    
    # --- SOLUCIÓN: Filtrar objetos no serializables ---
    # Crear una copia de los datos para no modificar el original
    datos_a_guardar = datos.copy()
    
    # Eliminar las claves que no son serializables en JSON
    if 'gemini_client' in datos_a_guardar:
        del datos_a_guardar['gemini_client']
    
    with open(nombre_archivo, "w", encoding="utf-8") as f:
        json.dump(datos_a_guardar, f, ensure_ascii=False, indent=2)
    
    st.toast("Progreso guardado automáticamente.", icon="💾")
    return nombre_archivo

# Función para cargar progreso
def cargar_progreso(archivo):
    try:
        with open(archivo, "r", encoding="utf-8") as f:
            datos = json.load(f)
        return datos
    except Exception as e:
        st.error(f"Error al cargar el archivo: {str(e)}")
        return None

# Función para exportar a Markdown
def exportar_markdown(titulo_libro, tabla_contenidos, capitulos):
    contenido_md = f"# {titulo_libro}\n\n"
    contenido_md += "## Tabla de Contenidos\n\n"
    contenido_md += tabla_contenidos + "\n\n"
    
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
st.markdown("Esta aplicación te permite generar libros completos a partir de una propuesta editorial utilizando la API de Gemini con Google Search.")

# Barra lateral para configuración
st.sidebar.header("Configuración")
api_key = st.sidebar.text_input("Introduce tu API Key de Gemini:", type="password")

# --- LÓGICA CLAVE PARA EL CLIENTE PERSISTENTE ---
# Crear el cliente y guardarlo en st.session_state si no existe o si la API key cambia.
if "gemini_client" not in st.session_state or st.session_state.api_key != api_key:
    if api_key:
        st.session_state.gemini_client = genai.Client(api_key=api_key)
        st.session_state.api_key = api_key
        st.sidebar.success("Cliente de Gemini inicializado.", icon="🤖")
    else:
        st.session_state.gemini_client = None
        st.session_state.api_key = None

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
if "pedir_cambios" not in st.session_state:
    st.session_state.pedir_cambios = False
if "editando_capitulo_idx" not in st.session_state:
    st.session_state.editando_capitulo_idx = -1
if "pidiendo_cambios_capitulo_idx" not in st.session_state:
    st.session_state.pidiendo_cambios_capitulo_idx = -1

# Cargar proyecto si se selecciona un archivo
if cargar_proyecto and not st.session_state.proyecto_cargado:
    datos_proyecto = cargar_progreso(cargar_proyecto)
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

if st.button("Analizar Propuesta") and st.session_state.gemini_client:
    if not propuesta.strip():
        st.error("Por favor, introduce una propuesta editorial válida.")
    else:
        st.session_state.propuesta = propuesta
        placeholder = st.empty()
        full_response = ""
        stream = generar_tabla_contenidos(propuesta, st.session_state.gemini_client)
        if stream:
            with placeholder.container():
                st.write("Generando tabla de contenidos...")
                for chunk in stream:
                    content = chunk.text or ""
                    full_response += content
                    st.markdown(full_response + "▌")
            placeholder.markdown(full_response)
            st.session_state.tabla_contenidos = full_response
            
            if "Título del libro:" in st.session_state.tabla_contenidos:
                titulo_match = re.search(r"Título del libro: (.+)", st.session_state.tabla_contenidos)
                if titulo_match:
                    st.session_state.titulo_libro = capitalizar_titulo_espanol(titulo_match.group(1).strip())
            
            guardar_progreso(st.session_state.to_dict())
            st.success("Tabla de contenidos generada correctamente.")
            st.rerun()

# Sección 2: Revisión de la tabla de contenidos
if st.session_state.tabla_contenidos:
    st.header("2. Revisión de la Tabla de Contenidos")
    st.subheader(f"Título Propuesto: {st.session_state.titulo_libro}")

    lineas_toc = st.session_state.tabla_contenidos.split('\n')
    num_capitulos = len([linea for linea in lineas_toc if re.match(r'^\d+\.\s+(.+)$', linea.strip())])
    if num_capitulos > 0:
        min_palabras_totales = num_capitulos * 2000
        max_palabras_totales = num_capitulos * 2500
        st.info(f"Se estima que el libro tendrá entre **{min_palabras_totales:,} y {max_palabras_totales:,} palabras** en {num_capitulos} capítulos.")
    
    st.text_area("Tabla de Contenidos:", st.session_state.tabla_contenidos, height=300)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("✅ Aprobar Tabla de Contenidos"):
            st.session_state.tabla_aprobada = True
            st.session_state.pedir_cambios = False
            st.success("Tabla de contenidos aprobada. Pasa a la siguiente sección para generar los capítulos.")
            st.rerun()

    with col2:
        if st.button("🔄 Regenerar Tabla de Contenidos") and st.session_state.gemini_client:
            st.session_state.pedir_cambios = False
            placeholder = st.empty()
            full_response = ""
            stream = generar_tabla_contenidos(st.session_state.propuesta, st.session_state.gemini_client)
            if stream:
                with placeholder.container():
                    st.write("Regenerando tabla de contenidos...")
                    for chunk in stream:
                        content = chunk.text or ""
                        full_response += content
                        st.markdown(full_response + "▌")
                placeholder.markdown(full_response)
                st.session_state.tabla_contenidos = full_response
                
                if "Título del libro:" in st.session_state.tabla_contenidos:
                    titulo_match = re.search(r"Título del libro: (.+)", st.session_state.tabla_contenidos)
                    if titulo_match:
                        st.session_state.titulo_libro = capitalizar_titulo_espanol(titulo_match.group(1).strip())
                
                guardar_progreso(st.session_state.to_dict())
                st.success("Tabla de contenidos regenerada.")
                st.rerun()
    
    with col3:
        if st.button("✏️ Pedir Cambios"):
            st.session_state.pedir_cambios = True
            st.rerun()

    if st.session_state.pedir_cambios:
        st.markdown("---")
        st.subheader("Solicitar Cambios en la Tabla de Contenidos")
        cambios_solicitados = st.text_area(
            "Describe los cambios que deseas realizar en la tabla de contenidos.",
            height=150
        )
        
        if st.button("Aplicar Cambios") and st.session_state.gemini_client:
            if not cambios_solicitados.strip():
                st.error("Por favor, describe los cambios que deseas realizar.")
            else:
                placeholder = st.empty()
                full_response = ""
                stream = modificar_tabla_contenidos(
                    st.session_state.propuesta,
                    st.session_state.tabla_contenidos,
                    cambios_solicitados,
                    st.session_state.gemini_client
                )
                if stream:
                    with placeholder.container():
                        st.write("Aplicando cambios...")
                        for chunk in stream:
                            content = chunk.text or ""
                            full_response += content
                            st.markdown(full_response + "▌")
                    placeholder.markdown(full_response)
                    st.session_state.tabla_contenidos = full_response
                    
                    if "Título del libro:" in st.session_state.tabla_contenidos:
                        titulo_match = re.search(r"Título del libro: (.+)", st.session_state.tabla_contenidos)
                        if titulo_match:
                            st.session_state.titulo_libro = capitalizar_titulo_espanol(titulo_match.group(1).strip())
                    
                    guardar_progreso(st.session_state.to_dict())
                    st.success("Cambios aplicados correctamente. Revisa la nueva tabla de contenidos.")
                    st.session_state.pedir_cambios = False
                    st.rerun()

# Sección 3: Gestión de Capítulos
if st.session_state.tabla_contenidos and "tabla_aprobada" in st.session_state and st.session_state.tabla_aprobada:
    st.header("3. Gestión de Capítulos")
    
    lineas = st.session_state.tabla_contenidos.split('\n')
    titulos_capitulos = []
    
    for linea in lineas:
        match = re.match(r'^\d+\.\s+(.+)$', linea.strip())
        if match:
            titulos_capitulos.append(match.group(1))
    
    if not titulos_capitulos:
        st.error("No se pudieron extraer los títulos de los capítulos. Por favor, revisa el formato y regenérala.")
    else:
        st.progress(st.session_state.capitulo_actual / len(titulos_capitulos))
        st.write(f"Progreso: {st.session_state.capitulo_actual} de {len(titulos_capitulos)} capítulos completados.")
        
        for i, titulo_capitulo in enumerate(titulos_capitulos):
            st.markdown(f"---")
            
            if i < len(st.session_state.capitulos):
                contenido_capitulo = st.session_state.capitulos[i]
                word_count = contar_palabras(contenido_capitulo)
                
                st.subheader(f"Capítulo {i+1}: {titulo_capitulo}")
                st.write(f"**Palabras generadas:** {word_count} (Objetivo: 2000-2500)")

                if st.session_state.editando_capitulo_idx == i:
                    contenido_editado = st.text_area(
                        "Edita el contenido del capítulo:",
                        value=contenido_capitulo,
                        height=500,
                        key=f"editor_capitulo_{i}"
                    )
                    col_save, col_cancel = st.columns(2)
                    with col_save:
                        if st.button("💾 Guardar Cambios Manuales", key=f"save_manual_{i}"):
                            st.session_state.capitulos[i] = contenido_editado
                            st.session_state.editando_capitulo_idx = -1
                            guardar_progreso(st.session_state.to_dict())
                            st.success("Cambios guardados correctamente.")
                            st.rerun()
                    with col_cancel:
                        if st.button("❌ Cancelar Edición", key=f"cancel_manual_{i}"):
                            st.session_state.editando_capitulo_idx = -1
                            st.rerun()
                
                elif st.session_state.pidiendo_cambios_capitulo_idx == i:
                    cambios = st.text_area(
                        "Describe los cambios que quieres que la IA realice en este capítulo:",
                        height=150,
                        key=f"cambios_capitulo_{i}"
                    )
                    if st.button("🤖 Aplicar Cambios con IA", key=f"apply_ai_{i}") and st.session_state.gemini_client:
                        if not cambios.strip():
                            st.error("Por favor, describe los cambios.")
                        else:
                            placeholder = st.empty()
                            full_response = ""
                            stream = modificar_capitulo(
                                contenido_capitulo,
                                st.session_state.titulo_libro,
                                i + 1,
                                titulo_capitulo,
                                st.session_state.propuesta,
                                cambios,
                                st.session_state.gemini_client
                            )
                            if stream:
                                with placeholder.container():
                                    st.write("Aplicando cambios...")
                                    for chunk in stream:
                                        content = chunk.text or ""
                                        full_response += content
                                        st.markdown(full_response + "▌")
                                placeholder.markdown(full_response)
                                st.session_state.capitulos[i] = full_response
                                st.session_state.pidiendo_cambios_capitulo_idx = -1
                                guardar_progreso(st.session_state.to_dict())
                                st.success("Capítulo modificado correctamente.")
                                st.rerun()
                    if st.button("❌ Cancelar Solicitud de Cambios", key=f"cancel_ai_{i}"):
                        st.session_state.pidiendo_cambios_capitulo_idx = -1
                        st.rerun()
                
                else:
                    with st.expander(f"Ver contenido del Capítulo {i+1}", expanded=(i == st.session_state.capitulo_actual - 1)):
                        st.markdown(contenido_capitulo)
                    
                    col_regenerar, col_cambios, col_editar = st.columns(3)
                    with col_regenerar:
                        if st.button("🔄 Regenerar", key=f"regenerar_{i}") and st.session_state.gemini_client:
                            with st.spinner("Regenerando capítulo..."):
                                capitulos_previos = "\n\n".join(st.session_state.capitulos[:i] + st.session_state.capitulos[i+1:])
                                placeholder = st.empty()
                                full_response = ""
                                stream = generar_capitulo(
                                    st.session_state.titulo_libro,
                                    i + 1,
                                    titulo_capitulo,
                                    st.session_state.propuesta,
                                    st.session_state.gemini_client,
                                    capitulos_previos
                                )
                                if stream:
                                    with placeholder.container():
                                        st.write("Regenerando capítulo...")
                                        for chunk in stream:
                                            content = chunk.text or ""
                                            full_response += content
                                            st.markdown(full_response + "▌")
                                    placeholder.markdown(full_response)
                                    st.session_state.capitulos[i] = full_response
                                    guardar_progreso(st.session_state.to_dict())
                                    st.success(f"Capítulo {i + 1} regenerado. Revisa la nueva versión.")
                                    st.rerun()
                    with col_cambios:
                        if st.button("✏️ Pedir Cambios", key=f"pedir_cambios_{i}"):
                            st.session_state.pidiendo_cambios_capitulo_idx = i
                            st.rerun()
                    with col_editar:
                        if st.button("🖊️ Editar Manualmente", key=f"editar_{i}"):
                            st.session_state.editando_capitulo_idx = i
                            st.rerun()

            elif i == st.session_state.capitulo_actual:
                st.subheader(f"Capítulo {i+1}: {titulo_capitulo}")
                if st.button(f"Generar Capítulo {i+1}", key=f"generar_{i}") and st.session_state.gemini_client:
                    placeholder = st.empty()
                    full_response = ""
                    capitulos_previos = "\n\n".join(st.session_state.capitulos)
                    stream = generar_capitulo(
                        st.session_state.titulo_libro,
                        i + 1,
                        titulo_capitulo,
                        st.session_state.propuesta,
                        st.session_state.gemini_client,
                        capitulos_previos
                    )
                    if stream:
                        with placeholder.container():
                            st.write(f"Escribiendo capítulo {i+1}...")
                            for chunk in stream:
                                content = chunk.text or ""
                                full_response += content
                                st.markdown(full_response + "▌")
                        placeholder.markdown(full_response)
                        st.session_state.capitulos.append(full_response)
                        st.session_state.capitulo_actual += 1
                        guardar_progreso(st.session_state.to_dict())
                        st.success(f"Capítulo {i + 1} generado. Ya puedes editarlo si lo deseas.")
                        st.rerun()
            else:
                st.subheader(f"Capítulo {i+1}: {titulo_capitulo} (Pendiente)")
                st.info("Este capítulo se generará cuando se completen los anteriores.")

        if st.session_state.capitulo_actual == len(titulos_capitulos):
            st.markdown("---")
            st.success("¡Todos los capítulos han sido generados!")
            
            st.header("4. Exportación del Libro")
            
            contenido_md = exportar_markdown(
                st.session_state.titulo_libro,
                st.session_state.tabla_contenidos,
                st.session_state.capitulos
            )
            
            st.subheader("Vista Previa")
            st.markdown(contenido_md[:1000] + "..." if len(contenido_md) > 1000 else contenido_md)
            
            nombre_archivo = f"{st.session_state.titulo_libro.replace(' ', '_')}.md"
            st.markdown(crear_enlace_descarga(contenido_md, nombre_archivo), unsafe_allow_html=True)

st.markdown("---")
st.markdown("Creado con Streamlit y la API de Gemini. Todos los derechos reservados.")
