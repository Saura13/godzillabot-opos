import streamlit as st
import os
from dotenv import load_dotenv
import google.generativeai as genai
from pypdf import PdfReader
import json
from datetime import datetime
import io

# --- 1. SEGURIDAD DE LIBRERÍAS (Solo Word) ---
try:
    from docx import Document
    from docx.shared import Pt
    WORD_AVAILABLE = True
except ImportError:
    WORD_AVAILABLE = False

# --- 2. CONFIGURACIÓN ---
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    st.error("⚠️ Error: No se encuentra la API Key en el archivo .env")
    st.stop()

genai.configure(api_key=api_key)

st.set_page_config(
    page_title="GodzillaBot Oposiciones", 
    page_icon="🦖", 
    layout="wide",
    initial_sidebar_state="collapsed" 
)

DOCS_DIR = "documentos"
HISTORY_DIR = "historial_sesiones"
if not os.path.exists(DOCS_DIR): os.makedirs(DOCS_DIR)
if not os.path.exists(HISTORY_DIR): os.makedirs(HISTORY_DIR)

# --- 3. DISEÑO VISUAL "GODZILLA V7 - BUG FIXES" ---
st.markdown("""
<style>
    /* --- ESTILOS BASE (Comunes) --- */
    .stApp {
        background-color: #f0fdf4;
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }
    #MainMenu, footer {visibility: hidden;}
    header {background-color: transparent !important;}

    /* CORRECCIÓN BOTÓN SIDEBAR: Forzamos que sea visible y verde */
    [data-testid="stSidebarCollapsedControl"] {
        color: #14532d !important; /* Color verde oscuro */
        background-color: rgba(255, 255, 255, 0.5); /* Fondo semitransparente */
        border-radius: 50%;
        padding: 5px;
        z-index: 999999 !important; /* Asegura que esté por encima de todo */
    }

    /* --- SOLUCIÓN TABLAS V6: Texto envuelto y scroll equilibrado --- */
    div[data-testid="stMarkdownContainer"] table {
        display: block;
        overflow-x: auto; 
        width: 100%;
        border-collapse: collapse;
        border: 1px solid #bbf7d0;
    }
    
    div[data-testid="stMarkdownContainer"] th {
        background-color: #14532d;
        color: white;
        padding: 12px;
        text-align: left;
        white-space: normal !important;
        min-width: 100px;
    }
    
    div[data-testid="stMarkdownContainer"] td {
        padding: 10px;
        border-bottom: 1px solid #eee;
        vertical-align: top; 
        white-space: normal !important; 
        word-wrap: break-word; 
        min-width: 120px; 
        max-width: 300px; 
        line-height: 1.5; 
    }

    /* --- ESTILOS DE PC (IMPACTO VISUAL) --- */
    @media only screen and (min-width: 769px) {
        
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #f0fdf4 0%, #dcfce7 100%);
            border-right: 2px solid #4ade80; 
            box-shadow: 2px 0 10px rgba(0,0,0,0.05);
        }
        
        div[role="radiogroup"] > label {
            background-color: white;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 8px;
            border: 1px solid #bbf7d0;
            transition: all 0.2s ease;
            box-shadow: 0 2px 4px rgba(0,0,0,0.02);
        }
        div[role="radiogroup"] > label:hover {
            transform: translateX(5px); 
            border-color: #16a34a;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            background-color: #f0fdf4;
            cursor: pointer;
        }

        .header-container {
            background: linear-gradient(90deg, #14532d 0%, #15803d 100%);
            padding: 30px;
            border-radius: 15px;
            color: white;
            text-align: center;
            margin-bottom: 30px;
            box-shadow: 0 10px 25px rgba(21, 128, 61, 0.4);
            border-bottom: 5px solid #4ade80;
        }
        .header-container h1 { font-size: 3rem; margin: 0; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }
        .header-container p { font-size: 1.2rem; opacity: 0.9; margin-top: 10px; letter-spacing: 1px; }

        div.stButton > button {
            background: linear-gradient(45deg, #16a34a, #15803d);
            color: white;
            border: none;
            border-radius: 10px;
            padding: 12px 24px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
            border-bottom: 4px solid #14532d;
            transition: all 0.2s ease;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        div.stButton > button:hover {
            transform: translateY(2px);
            border-bottom: 2px solid #14532d;
            background: linear-gradient(45deg, #22c55e, #16a34a);
        }
        div.stButton > button:active {
            transform: translateY(4px);
            border-bottom: 0px solid transparent;
        }
    }

    /* --- ESTILOS MÓVIL (FUNCIONALIDAD) --- */
    @media only screen and (max-width: 768px) {
        
        .block-container {
            padding-top: 3rem !important; /* Más espacio arriba para que el botón no se monte */
            padding-left: 0.5rem !important; 
            padding-right: 0.5rem !important;
        }

        .header-container {
            background: linear-gradient(90deg, #14532d 0%, #15803d 100%);
            padding: 15px;
            border-radius: 10px;
            color: white;
            text-align: center;
            margin-bottom: 15px;
            border-bottom: 3px solid #4ade80;
        }
        .header-container h1 { font-size: 1.5rem !important; margin: 0; }
        .header-container p { display: none; }

        div.stButton > button {
            background-color: #16a34a;
            color: white;
            border: none;
            border-radius: 8px;
            padding: 0.8rem;
            font-weight: bold;
            width: 100%;
            min-height: 50px;
            margin-bottom: 8px;
        }
        
        div[role="radiogroup"] > label {
            padding: 10px;
            border-bottom: 1px solid #e5e7eb;
        }
    }

    /* --- MODO HORIZONTAL (LANDSCAPE) MÓVIL --- */
    @media only screen and (orientation: landscape) and (max-height: 500px) {
        .header-container {
            padding: 5px !important;
            margin-bottom: 5px !important;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .header-container h1 { font-size: 1rem !important; }
        .header-container p { display: none; }
        .block-container { padding-top: 0.5rem !important; }
        div[data-testid="stSidebar"] { width: 100px !important; } 
    }
    
    div[data-testid="stChatMessage"]:nth-child(odd) { background-color: #14532d; border: none; border-radius: 20px 20px 0 20px;}
    div[data-testid="stChatMessage"]:nth-child(odd) * { color: white !important; }
    div[data-testid="stChatMessage"]:nth-child(even) { background-color: #ffffff; border: 1px solid #bbf7d0; border-radius: 20px 20px 20px 0;}

    div[data-testid="stFileUploader"] {
        background-color: white;
        border: 2px dashed #16a34a;
        border-radius: 12px;
        padding: 15px;
    }
</style>
""", unsafe_allow_html=True)

# --- 4. FUNCIONES LÓGICAS ---
def save_uploaded_file(uploaded_file):
    try:
        with open(os.path.join(DOCS_DIR, uploaded_file.name), "wb") as f:
            f.write(uploaded_file.getbuffer())
        return True
    except: return False

def save_session_history():
    if not st.session_state.messages: return
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    path = os.path.join(HISTORY_DIR, f"Sesion_{timestamp}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(st.session_state.messages, f, ensure_ascii=False, indent=4)
    st.success(f"✅ Sesión Guardada")

def load_session_history(filename):
    path = os.path.join(HISTORY_DIR, filename)
    try:
        with open(path, "r", encoding="utf-8") as f:
            st.session_state.messages = json.load(f)
        st.rerun()
    except: st.error("Error al cargar")

def create_word_docx(text_content):
    if not WORD_AVAILABLE: return None
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Segoe UI'
    style.font.size = Pt(11)
    
    doc.add_heading('Informe GodzillaBot', 0)
    doc.add_paragraph(f"Generado el: {datetime.now().strftime('%d/%m/%Y a las %H:%M')}")
    doc.add_paragraph("_" * 50)
    
    for line in text_content.split('\n'):
        line = line.strip()
        if not line: continue
        if line.startswith('### '): doc.add_heading(line.replace('### ', ''), level=2)
        elif line.startswith('## '): doc.add_heading(line.replace('## ', ''), level=1)
        elif line.startswith('**') and line.endswith('**'): 
            p = doc.add_paragraph(); p.add_run(line.replace('**', '')).bold = True
        else:
            clean_line = line.replace('**', '').replace('__', '')
            p = doc.add_paragraph(clean_line)
            if clean_line.startswith('- ') or clean_line.startswith('* '): p.style = 'List Bullet'
            
    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()

def get_best_available_model():
    try:
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        for m in models: 
            if 'flash' in m: return m
        for m in models: 
            if 'pro' in m: return m
        return models[0] if models else "gemini-pro"
    except: return "gemini-pro"

current_model_name = get_best_available_model()

@st.cache_data(max_entries=3, show_spinner=False)
def extract_text_from_pdfs(file_list):
    text = ""
    for name in file_list:
        try:
            reader = PdfReader(os.path.join(DOCS_DIR, name))
            for page in reader.pages: text += page.extract_text() + "\n"
        except: pass
    return text

def get_system_prompt(mode):
    base = "Eres GodzillaBot, un preparador de oposiciones implacable y experto. Base: Documentos PDF adjuntos. "
    if "Simulacro" in mode:
        return base + "MODO: Simulacro (Ruleta). SALIDA: Cuestionario numerado y Clave de Respuestas final. SIN explicaciones."
    elif "Excel" in mode:
        return base + "Salida: Tabla compatible con Excel (separador |). Concepto | Dato | Art | Nota."
    else:
        return base + "Responde de forma técnica y estructurada. Usa '###' para títulos."

# --- 5. INTERFAZ LATERAL (EL MENÚ) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/1624/1624022.png", width=70) 
    st.markdown("## 🦖 Guarida")
    
    with st.expander("📤 Cargar Temario (PDFs)", expanded=True):
        up = st.file_uploader("Arrastra archivos aquí", type="pdf")
        if up and save_uploaded_file(up): st.rerun()
    
    # Selector de archivos (CORREGIDO: Ya no se seleccionan todos por defecto)
    files_available = [f for f in os.listdir(DOCS_DIR) if f.endswith('.pdf')]
    if files_available:
        files = st.multiselect("📚 Documentos Activos:", files_available, default=[]) # Default vacío
    else:
        files = []
        st.info("ℹ️ Sube PDFs para empezar.")
    
    st.markdown("---")
    st.markdown("### 🎯 Objetivo de Hoy")
    mode = st.radio(
        "Selecciona estrategia:", 
        [
            "💀 Simulacro de Examen (Test)", 
            "💬 Chat Interactivo con Temario", 
            "📝 Resumen de Alto Rendimiento", 
            "📊 Extracción de Datos a Excel"
        ]
    )
    
    st.markdown("---")
    st.markdown("### 🧠 Memoria")
    c1, c2 = st.columns(2)
    if c1.button("💾 Guardar"): save_session_history()
    if c2.button("🗑️ Reiniciar"): st.session_state.messages = []; st.rerun()
    
    sessions = [f for f in os.listdir(HISTORY_DIR) if f.endswith('.json')]
    if sessions:
        st.markdown("###### Recuperar sesión:")
        load = st.selectbox("Selecciona fecha:", ["..."] + sorted(sessions, reverse=True), label_visibility="collapsed")
        if load != "..." and st.button("📂 Abrir Sesión"): load_session_history(load)

# --- 6. ZONA PRINCIPAL ---
st.markdown("""
<div class="header-container">
    <h1>🦖 GodzillaBot</h1>
    <p>Plataforma de Oposiciones de Alto Rendimiento</p>
</div>
""", unsafe_allow_html=True)

if "messages" not in st.session_state: st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

if prompt := st.chat_input("Escribe tu instrucción o pregunta..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    if not files:
        st.warning("⚠️ ¡ALTO! No has seleccionado ningún documento del menú lateral.")
    else:
        with st.chat_message("assistant"):
            placeholder = st.empty()
            full_resp = ""
            
            try:
                with st.spinner("🦖 Analizando normativa y generando respuesta..."): 
                    text = extract_text_from_pdfs(files)
                
                prompt_final = f"{get_system_prompt(mode)}\nDOCS: {text[:800000]}\nUSER: {prompt}"
                model = genai.GenerativeModel(current_model_name)
                stream = model.generate_content(prompt_final, stream=True)
                
                for chunk in stream:
                    if chunk.text:
                        full_resp += chunk.text
                        placeholder.markdown(full_resp + "▌")
                placeholder.markdown(full_resp)
                st.session_state.messages.append({"role": "assistant", "content": full_resp})
                
                st.markdown("---")
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    if WORD_AVAILABLE:
                        docx = create_word_docx(full_resp)
                        st.download_button("📄 Descargar en Word", docx, f"Godzilla_{datetime.now().strftime('%H%M')}.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
                
                with col2:
                    if "Excel" in mode or "|" in full_resp:
                        st.download_button("📊 Exportar a Excel", full_resp, "datos_oposicion.csv", "text/csv")

            except Exception as e: st.error(f"Error del sistema: {e}")