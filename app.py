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
    initial_sidebar_state="collapsed" 
)

DOCS_DIR = "documentos"
HISTORY_DIR = "historial_sesiones"
if not os.path.exists(DOCS_DIR): os.makedirs(DOCS_DIR)
if not os.path.exists(HISTORY_DIR): os.makedirs(HISTORY_DIR)

# --- 3. CEREBRO: CADENA DE MODELOS Y PACIENCIA ---
@st.cache_resource
def get_model_list():
    try:
        all_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        priorities = []
        for m in all_models:
            if 'flash' in m.lower(): priorities.append(m)
        for m in all_models:
            if 'pro' in m.lower() and 'vision' not in m.lower(): priorities.append(m)
        if not priorities: return ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']
        return priorities
    except:
        return ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']

MODELS_AVAILABLE = get_model_list()

def generate_response_with_patience(prompt_text):
    max_retries = 3
    for attempt in range(max_retries):
        for model_name in MODELS_AVAILABLE:
            try:
                model = genai.GenerativeModel(model_name)
                return model.generate_content(prompt_text, stream=True)
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "quota" in error_msg.lower():
                    wait_time = (attempt + 1) * 5
                    time.sleep(wait_time)
                    continue
                if "404" in error_msg:
                    continue
                continue
    return "Error_Quota_Final"

# --- 4. DISEÑO VISUAL "MODO LECTURA LIMPIA" (Blanco y Negro) ---
st.markdown("""
<style>
    /* === 1. LIMPIEZA INTERFAZ === */
    [data-testid="stHeader"] { background-color: transparent !important; z-index: 90 !important; }
    [data-testid="stToolbar"] { display: none !important; }
    [data-testid="stDecoration"] { display: none !important; }
    footer { visibility: hidden; }

    /* === 2. FONDO Y TEXTO (CAMBIO IMPORTANTE) === */
    /* Fondo blanco puro para leer sin cansarse */
    .stApp { 
        background-color: #ffffff !important; 
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* === 3. BURBUJAS DE CHAT === */
    /* Usuario: Verde Godzilla (para diferenciar) */
    div[data-testid="stChatMessage"]:nth-child(odd) { 
        background-color: #15803d; 
        color: white;
        border: none;
    }
    div[data-testid="stChatMessage"]:nth-child(odd) * { 
        color: white !important; 
    }
    
    /* IA: Gris muy suave, casi blanco, con texto negro nítido */
    div[data-testid="stChatMessage"]:nth-child(even) { 
        background-color: #f9fafb; /* Gris humo muy claro */
        border: 1px solid #e5e7eb;
        color: #1f2937; /* Gris muy oscuro (casi negro) para lectura fácil */
    }
    div[data-testid="stChatMessage"]:nth-child(even) * { 
        color: #1f2937 !important;
    }

    /* === 4. BOTÓN MENÚ === */
    [data-testid="stSidebarCollapsedControl"] {
        display: block !important;
        background-color: white !important;
        border: 2px solid #16a34a !important;
        color: #16a34a !important;
        border-radius: 50% !important;
        width: 45px !important;
        height: 45px !important;
        padding: 5px !important;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1) !important;
        z-index: 999999 !important; 
        position: fixed; top: 15px; left: 15px;
    }

    /* === 5. CABECERA (SOLO VISUAL) === */
    .header-container {
        background: linear-gradient(90deg, #14532d 0%, #15803d 100%);
        padding: 30px;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin-bottom: 30px;
        /* Quitamos el verde neón de abajo que cansaba */
        border-bottom: 5px solid #166534; 
        margin-top: 50px;
    }
    .header-container h1 { font-size: 2.5rem; margin: 0; font-weight: 800;}
    .header-container p { font-size: 1.1rem; opacity: 0.9; margin-top: 5px; font-style: italic; }

    /* === 6. TABLAS (Scroll) === */
    div[data-testid="stMarkdownContainer"] table {
        display: block; overflow-x: auto; width: 100%; border-collapse: collapse; 
        border: 1px solid #e5e7eb; /* Borde gris suave */
    }
    div[data-testid="stMarkdownContainer"] th {
        background-color: #f3f4f6; /* Cabecera gris claro */
        color: #111827; /* Texto negro */
        padding: 12px; min-width: 100px; text-align: left; border-bottom: 2px solid #d1d5db;
    }
    div[data-testid="stMarkdownContainer"] td {
        padding: 10px; border-bottom: 1px solid #eee; min-width: 120px; max-width: 300px; vertical-align: top;
    }

    /* Media Queries (Móvil) */
    @media only screen and (max-width: 768px) {
        .block-container { padding-top: 4rem !important; padding-left: 1rem; padding-right: 1rem; }
        .header-container { padding: 20px; margin-bottom: 20px; margin-top: 40px; }
        .header-container h1 { font-size: 1.8rem !important; }
        div.stButton > button { width: 100%; min-height: 50px; }
    }
    /* Media Queries (PC) */
    @media only screen and (min-width: 769px) {
        section[data-testid="stSidebar"] {
            background-color: #f9fafb; border-right: 1px solid #e5e7eb;
        }
        div.stButton > button { width: auto; min-width: 200px; }
    }
    
    /* Landscape */
    @media only screen and (orientation: landscape) and (max-height: 600px) {
        .block-container { padding-top: 1rem !important; }
        .header-container { padding: 5px !important; margin-top: 0px; min-height: 40px; display: flex; align-items: center; justify-content: center;}
        .header-container h1 { font-size: 1.2rem !important; margin: 0; }
        .header-container p { display: none !important; }
    }
</style>
""", unsafe_allow_html=True)

# --- 5. FUNCIONES AUXILIARES ---
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

@st.cache_data(max_entries=3, show_spinner=False)
def extract_text_from_pdfs(file_list):
    text = ""
    for name in file_list:
        try:
            reader = PdfReader(os.path.join(DOCS_DIR, name))
            for page in reader.pages: text += page.extract_text() + "\n"
        except: pass
    return text

# --- 6. CEREBRO: RULETA DE EXAMINADORES (RECUPERADA) ---
def get_system_prompt(mode):
    base = "Eres GodzillaBot, experto en legislación y oposiciones. Usas los PDFs adjuntos como fuente de verdad absoluta. "
    
    if "Simulacro" in mode:
        # RULETA DE PERSONALIDADES ALEATORIA
        personalidades = [
            "EL MINUCIOSO: Te centras en plazos, porcentajes y excepciones raras.",
            "EL CONCEPTUAL: Preguntas sobre la naturaleza jurídica y definiciones exactas.",
            "EL TRAMPOSO: Buscas confundir con términos muy similares y juegos de palabras.",
            "EL PRÁCTICO: Planteas casos prácticos breves aplicados a la realidad administrativa."
        ]
        examinador = random.choice(personalidades)
        
        return base + f"""
        MODO: SIMULACRO DE EXAMEN (TEST).
        PERSONALIDAD ACTIVA: {examinador}
        
        INSTRUCCIONES ESTRICTAS:
        1. Genera preguntas tipo test con EXACTAMENTE 4 opciones (a, b, c, d).
        2. Solo UNA es correcta.
        3. Al final del todo, proporciona la 'HOJA DE RESPUESTAS' con la solución y el artículo de referencia.
        4. No des explicaciones entre preguntas, solo el test puro.
        """
        
    elif "Excel" in mode:
        return base + "Salida: Tabla compatible con Excel (separador |). Concepto | Dato | Art | Nota."
    else:
        return base + "Responde de forma técnica, estructurada y profesional."

# --- 7. INTERFAZ Y LÓGICA ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/1624/1624022.png", width=70) 
    st.markdown("## 🦖 Guarida")
    
    with st.expander("📤 Cargar Temario (PDFs)", expanded=False):
        up = st.file_uploader("Arrastra archivos aquí", type="pdf")
        if up and save_uploaded_file(up): st.rerun()
    
    files_available = [f for f in os.listdir(DOCS_DIR) if f.endswith('.pdf')]
    if files_available:
        files = st.multiselect("📚 Documentos Activos:", files_available, default=[]) 
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
    c1, c2 = st.columns(2)
    if c1.button("💾 Guardar"): save_session_history()
    if c2.button("🗑️ Reiniciar"): st.session_state.messages = []; st.rerun()
    
    sessions = [f for f in os.listdir(HISTORY_DIR) if f.endswith('.json')]
    if sessions:
        load = st.selectbox("Recuperar:", ["..."] + sorted(sessions, reverse=True))
        if load != "..." and st.button("Abrir"): load_session_history(load)

st.markdown("""
<div class="header-container">
    <h1>🦖 GodzillaBot Oposiciones</h1>
    <p>Destruyendo tus dudas, dominando el temario.</p>
</div>
""", unsafe_allow_html=True)

if "messages" not in st.session_state: st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

if prompt := st.chat_input("Escribe tu pregunta..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    if not files:
        st.warning("⚠️ Selecciona documentos en el menú lateral.")
    else:
        with st.chat_message("assistant"):
            placeholder = st.empty()
            full_resp = ""
            
            try:
                with st.spinner("🦖 Procesando (Negociando cuota con Google)..."): 
                    text = extract_text_from_pdfs(files)
                    prompt_final = f"{get_system_prompt(mode)}\nDOCS: {text[:800000]}\nUSER: {prompt}"
                    
                    response_obj = generate_response_with_patience(prompt_final)

                    if isinstance(response_obj, str) and response_obj.startswith("Error_Quota"):
                        st.error("🛑 Agotado total. Google me pide descansar unos minutos.")
                        st.caption("Consejo: Espera 2-3 min para recargar energía.")
                        full_resp = "Error cuota."
                    else:
                        for chunk in response_obj:
                            if chunk.text:
                                full_resp += chunk.text
                                placeholder.markdown(full_resp + "▌")
                        placeholder.markdown(full_resp)
                        st.session_state.messages.append({"role": "assistant", "content": full_resp})
                
                if full_resp and "Error" not in full_resp:
                    st.markdown("---")
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        if WORD_AVAILABLE:
                            docx = create_word_docx(full_resp)
                            st.download_button("📄 Word", docx, f"Godzilla.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
                    with col2:
                        if "Excel" in mode or "|" in full_resp:
                            st.download_button("📊 Excel", full_resp, "datos.csv", "text/csv")

            except Exception as e: st.error(f"Error crítico: {e}")