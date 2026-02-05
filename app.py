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
    initial_sidebar_state="expanded"
)

DOCS_DIR = "documentos"
HISTORY_DIR = "historial_sesiones"
if not os.path.exists(DOCS_DIR): os.makedirs(DOCS_DIR)
if not os.path.exists(HISTORY_DIR): os.makedirs(HISTORY_DIR)

# --- 3. DISEÑO VISUAL "GODZILLA GREEN" ---
st.markdown("""
<style>
    /* Fuente y Fondo General */
    .stApp {
        background-color: #f0fdf4; /* Verde muy pálido de fondo */
        font-family: 'Inter', 'Segoe UI', sans-serif;
    }
    
    /* CORRECCIÓN: OCULTAR SOLO MENÚ Y FOOTER, PERO DEJAR HEADER VISIBLE 
       Esto permite que el botón de "Mostrar Sidebar" siga existiendo */
    #MainMenu, footer {visibility: hidden;}
    
    /* Opcional: Hacer el header transparente para que no moleste visualmente */
    header {
        background-color: transparent !important;
    }

    /* CABECERA GODZILLA */
    .header-container {
        background: linear-gradient(90deg, #14532d 0%, #15803d 100%); /* Degradado Verde Oscuro */
        padding: 25px;
        border-radius: 12px;
        color: white;
        text-align: center;
        margin-bottom: 30px;
        box-shadow: 0 4px 15px rgba(21, 128, 61, 0.3);
        border-bottom: 4px solid #4ade80; /* Línea neón abajo */
    }
    
    /* BURBUJAS DE CHAT */
    /* Usuario: Verde Bosque Profundo */
    div[data-testid="stChatMessage"]:nth-child(odd) {
        background-color: #14532d; 
        color: white;
        border: none;
        border-radius: 20px 20px 0 20px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
    }
    div[data-testid="stChatMessage"]:nth-child(odd) * {
        color: white !important;
    }
    
    /* IA: Blanco Limpio con borde verde sutil */
    div[data-testid="stChatMessage"]:nth-child(even) {
        background-color: #ffffff;
        border: 1px solid #bbf7d0;
        border-radius: 20px 20px 20px 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    
    /* BOTONES */
    div.stButton > button {
        background: linear-gradient(45deg, #16a34a, #15803d);
        color: white;
        border-radius: 12px;
        border: none;
        padding: 12px 20px;
        font-weight: 700;
        transition: all 0.3s ease;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-size: 14px;
        width: 100%;
        border-bottom: 3px solid #14532d; /* Efecto 3D */
    }
    div.stButton > button:hover {
        transform: translateY(-2px);
        background: linear-gradient(45deg, #22c55e, #16a34a);
        box-shadow: 0 5px 15px rgba(22, 163, 74, 0.4);
    }
    
    /* UPLOADER */
    div[data-testid="stFileUploader"] {
        background-color: white;
        border: 2px dashed #16a34a; /* Borde verde */
        border-radius: 15px;
        padding: 20px;
    }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #f0fdf4;
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

# --- 5. INTERFAZ LATERAL ---
with st.sidebar:
    # Icono de Godzilla/Dinosaurio
    st.image("https://cdn-icons-png.flaticon.com/512/1624/1624022.png", width=80) 
    st.markdown("### 🦖 Guarida del Monstruo")
    
    with st.expander("📤 Alimentar con Temario"):
        up = st.file_uploader("Arrastra tus PDFs", type="pdf")
        if up and save_uploaded_file(up): st.rerun()
    
    files = st.multiselect("📚 Archivos para devorar:", [f for f in os.listdir(DOCS_DIR) if f.endswith('.pdf')])
    
    st.markdown("---")
    st.caption("ARMAS DE ESTUDIO")
    mode = st.radio("Selecciona modo:", ["💀 Simulacro Test (Ruleta)", "💬 Chat Libre", "📝 Resumen Alto Rendimiento", "📊 Extracción Tabular (Excel)"])
    
    st.markdown("---")
    st.caption("MEMORIA")
    c1, c2 = st.columns(2)
    if c1.button("💾 Guardar"): save_session_history()
    if c2.button("🗑️ Rugir"): st.session_state.messages = []; st.rerun()
    
    sessions = [f for f in os.listdir(HISTORY_DIR) if f.endswith('.json')]
    if sessions:
        load = st.selectbox("Recuperar:", ["..."] + sorted(sessions, reverse=True))
        if load != "..." and st.button("Abrir"): load_session_history(load)

# --- 6. ZONA PRINCIPAL ---
st.markdown("""
<div class="header-container">
    <h1 style="margin:0; font-size: 2.5em;">🦖 GodzillaBot Oposiciones</h1>
    <p style="margin:5px 0 0 0; opacity: 0.9; font-weight: 300;">Destruyendo tus dudas, dominando el temario.</p>
</div>
""", unsafe_allow_html=True)

if "messages" not in st.session_state: st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

if prompt := st.chat_input("Desafía a GodzillaBot..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    if not files:
        st.warning("⚠️ ¡GRRR! No tengo comida (PDFs). Carga documentos en el menú lateral.")
    else:
        with st.chat_message("assistant"):
            placeholder = st.empty()
            full_resp = ""
            
            try:
                with st.spinner("🦖 Procesando destrucción masiva de datos..."): 
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
                        st.download_button("📄 Descargar Word", docx, f"Godzilla_{datetime.now().strftime('%H%M')}.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
                
                with col2:
                    if "Tabular" in mode or "|" in full_resp:
                        st.download_button("📊 Exportar Excel", full_resp, "datos.csv", "text/csv")

            except Exception as e: st.error(f"Error técnico: {e}")