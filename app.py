import streamlit as st
import os
from dotenv import load_dotenv
import google.generativeai as genai
from pypdf import PdfReader
import json
from datetime import datetime
import io
import time
import random

# --- 1. SEGURIDAD DE LIBRERÍAS ---
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
    initial_sidebar_state="auto"
)

DOCS_DIR = "documentos"
HISTORY_DIR = "historial_sesiones"
if not os.path.exists(DOCS_DIR): os.makedirs(DOCS_DIR)
if not os.path.exists(HISTORY_DIR): os.makedirs(HISTORY_DIR)

# --- 3. ESTÉTICA RESPONSIVA (LA CLAVE) ---
st.markdown("""
<style>
    /* 1. ESTILO BASE DEL TÍTULO (Limpio por defecto para Móvil) */
    .header-container {
        padding: 10px;
        text-align: center;
        margin-bottom: 20px;
    }
    .header-container h1 { 
        margin: 0; 
        font-weight: 800;
        font-size: 2rem;
    }
    .header-container p { 
        font-size: 1rem; 
        opacity: 0.8; 
        margin-top: 5px; 
        font-style: italic;
    }

    /* 2. TRANSFORMACIÓN ÉPICA SOLO PARA PC (Pantallas grandes) */
    @media only screen and (min-width: 769px) {
        .header-container {
            background: linear-gradient(90deg, #14532d 0%, #15803d 100%); /* Verde Godzilla */
            padding: 40px;
            border-radius: 15px;
            color: white !important; /* Texto forzado a blanco en PC */
            box-shadow: 0 4px 15px rgba(20, 83, 45, 0.3);
            border-bottom: 5px solid #4ade80;
            margin-bottom: 40px;
        }
        .header-container h1 { 
            font-size: 3.5rem; 
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
            color: white !important;
        }
        .header-container p { 
            font-size: 1.3rem; 
            color: #dcfce7 !important; /* Verde pálido */
        }
    }

    /* 3. AJUSTES MÓVIL (Para asegurar limpieza) */
    @media only screen and (max-width: 768px) {
        /* En móvil, el contenedor es transparente y respeta el tema (Claro/Oscuro) */
        .header-container {
            background: transparent;
            box-shadow: none;
            border: none;
            padding-top: 0;
        }
        /* El color del texto lo decide Streamlit (Negro en claro, Blanco en oscuro) */
    }
</style>
""", unsafe_allow_html=True)

# --- 4. LÓGICA DEL CEREBRO (INTACTA) ---
if "pdf_text" not in st.session_state:
    st.session_state.pdf_text = ""
if "last_files" not in st.session_state:
    st.session_state.last_files = []
if "messages" not in st.session_state: 
    st.session_state.messages = []

@st.cache_data(show_spinner=False)
def get_pdf_text_fast(file_names):
    text = ""
    for name in file_names:
        try:
            path = os.path.join(DOCS_DIR, name)
            reader = PdfReader(path)
            for page in reader.pages:
                text += page.extract_text() + "\n"
        except: continue
    return text

@st.cache_resource
def get_model_list():
    try:
        all_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        flash_models = [m for m in all_models if 'flash' in m.lower()]
        pro_models = [m for m in all_models if 'pro' in m.lower() and 'vision' not in m.lower()]
        priorities = flash_models + pro_models
        if not priorities: return ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']
        return priorities
    except:
        return ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']

MODELS_AVAILABLE = get_model_list()

def generate_response_with_patience(prompt_text):
    max_retries = 3
    frases_espera = [
        "🦖 Godzilla está recargando...",
        "⏳ Negociando con Google...",
        "🦕 Procesando normativa...",
        "🔥 Un momento..."
    ]
    for attempt in range(max_retries):
        for model_name in MODELS_AVAILABLE:
            try:
                model = genai.GenerativeModel(model_name)
                return model.generate_content(prompt_text, stream=True)
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "quota" in error_msg.lower():
                    wait_time = (attempt + 1) * 2 
                    if attempt >= 0: 
                         msg = random.choice(frases_espera)
                         st.toast(f"{msg} (Reintento {attempt+1})", icon="🦖")
                    time.sleep(wait_time)
                    continue
                if "404" in error_msg:
                    continue
                continue
    return "Error_Quota_Final"

def create_word_docx(text_content):
    if not WORD_AVAILABLE: return None
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Segoe UI'
    style.font.size = Pt(11)
    doc.add_heading('Informe GodzillaBot', 0)
    for line in text_content.split('\n'):
        line = line.strip()
        if not line: continue
        if line.startswith('### '): doc.add_heading(line.replace('### ', ''), level=2)
        elif line.startswith('## '): doc.add_heading(line.replace('## ', ''), level=1)
        elif line.startswith('**') and line.endswith('**'): 
            p = doc.add_paragraph(); p.add_run(line.replace('**', '')).bold = True
        else:
            doc.add_paragraph(line.replace('**', ''))
    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()

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
    st.success(f"✅")

def load_session_history(filename):
    path = os.path.join(HISTORY_DIR, filename)
    try:
        with open(path, "r", encoding="utf-8") as f:
            st.session_state.messages = json.load(f)
        st.rerun()
    except: st.error("Error")

def get_system_prompt(mode):
    base = "Eres GodzillaBot, experto en legislación. Fuente: PDFs adjuntos. "
    if "Simulacro" in mode:
        pers = ["EL MINUCIOSO", "EL CONCEPTUAL", "EL TRAMPOSO", "EL PRÁCTICO"]
        examinador = random.choice(pers)
        return base + f"""
        MODO: SIMULACRO TEST. Personalidad: {examinador}.
        INSTRUCCIONES DE FORMATO:
        1. Opciones (a, b, c, d) en LÍNEAS SEPARADAS (Lista Markdown).
        2. Hoja de Respuestas al final.
        """
    elif "Excel" in mode:
        return base + "Salida: Tabla Markdown cerrada. Concepto | Dato | Art | Nota."
    else:
        return base + "Responde de forma técnica y estructurada."

# --- 5. INTERFAZ ---

# BARRA LATERAL (NATIVA)
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/1624/1624022.png", width=60)
    st.markdown("### 🦖 Guarida")
    
    with st.expander("📤 Cargar Temario"):
        up = st.file_uploader("Subir PDFs", type="pdf")
        if up and save_uploaded_file(up): st.rerun()
    
    files_available = [f for f in os.listdir(DOCS_DIR) if f.endswith('.pdf')]
    if files_available:
        files = st.multiselect("📚 Temario Activo:", files_available, default=[]) 
    else:
        files = []
        st.info("ℹ️ Sube PDFs para empezar.")
    
    st.divider()
    mode = st.radio("Estrategia:", 
        ["💀 Simulacro de Examen (Test)", "💬 Chat Interactivo", 
         "📝 Resumen Alto Rendimiento", "📊 Datos a Excel"])
    
    st.divider()
    c1, c2 = st.columns(2)
    if c1.button("💾 Guardar"): save_session_history()
    if c2.button("🗑️ Borrar"): st.session_state.messages = []; st.rerun()
    
    sessions = [f for f in os.listdir(HISTORY_DIR) if f.endswith('.json')]
    if sessions:
        load = st.selectbox("Historial:", ["..."] + sorted(sessions, reverse=True))
        if load != "..." and st.button("Cargar"): load_session_history(load)

# CABECERA (CON LÓGICA PC/MÓVIL)
st.markdown("""
<div class="header-container">
    <h1>🦖 GodzillaBot Oposiciones</h1>
    <p>Destruyendo tus dudas, dominando el temario.</p>
</div>
""", unsafe_allow_html=True)

# Lógica Principal
if files != st.session_state.last_files:
    if files:
        with st.spinner("Procesando documentos..."):
            st.session_state.pdf_text = get_pdf_text_fast(files)
            st.session_state.last_files = files
    else:
        st.session_state.pdf_text = ""
        st.session_state.last_files = []

for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]): 
        st.markdown(msg["content"])
        if msg["role"] == "assistant":
            key_base = f"btn_{i}"
            c1, c2 = st.columns([1, 4])
            with c1:
                if WORD_AVAILABLE:
                    docx = create_word_docx(msg["content"])
                    st.download_button("📄 Word", docx, f"Godzilla_{i}.docx", 
                                     "application/vnd.openxmlformats-officedocument.wordprocessingml.document", key=f"{key_base}_w")
            with c2:
                if "|" in msg["content"]:
                    st.download_button("📊 Excel", msg["content"], f"datos_{i}.csv", "text/csv", key=f"{key_base}_x")

if prompt := st.chat_input("Escribe tu pregunta..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    if not files:
        st.warning("⚠️ Abre el menú (flecha arriba-izquierda) y selecciona documentos.")
    else:
        with st.chat_message("assistant"):
            placeholder = st.empty()
            full_resp = ""
            try:
                text_context = st.session_state.pdf_text 
                
                with st.spinner("Generando respuesta..."): 
                    prompt_final = f"{get_system_prompt(mode)}\nDOCS: {text_context[:800000]}\nUSER: {prompt}"
                    response_obj = generate_response_with_patience(prompt_final)

                    if isinstance(response_obj, str) and response_obj.startswith("Error_Quota"):
                        st.error("🛑 Agotado. Espera un poco.")
                    else:
                        for chunk in response_obj:
                            if chunk.text:
                                full_resp += chunk.text
                                placeholder.markdown(full_resp + "▌")
                        placeholder.markdown(full_resp)
                        st.session_state.messages.append({"role": "assistant", "content": full_resp})
                        st.rerun() 
            except Exception as e: st.error(f"Error: {e}")