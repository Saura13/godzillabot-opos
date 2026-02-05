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

# --- 3. DISEÑO VISUAL "HÍBRIDO: POTENCIA PC + COMODIDAD MÓVIL" ---
st.markdown("""
<style>
    /* --- ESTILOS BASE (Comunes) --- */
    .stApp {
        background-color: #f0fdf4;
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }
    #MainMenu, footer {visibility: hidden;}
    header {background-color: transparent !important;}

    /* --- ESTILOS DE PC (IMPACTO VISUAL) --- */
    @media only screen and (min-width: 769px) {
        
        /* Cabecera Épica */
        .header-container {
            background: linear-gradient(90deg, #14532d 0%, #15803d 100%);
            padding: 30px;
            border-radius: 15px;
            color: white;
            text-align: center;
            margin-bottom: 30px;
            box-shadow: 0 10px 25px rgba(21, 128, 61, 0.4); /* Sombra potente */
            border-bottom: 5px solid #4ade80; /* Neón */
        }
        .header-container h1 { font-size: 3rem; margin: 0; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); }
        .header-container p { font-size: 1.2rem; opacity: 0.9; margin-top: 10px; letter-spacing: 1px; }

        /* Botones con Efecto 3D y Degradados */
        div.stButton > button {
            background: linear-gradient(45deg, #16a34a, #15803d);
            color: white;
            border: none;
            border-radius: 10px;
            padding: 12px 24px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
            border-bottom: 4px solid #14532d; /* El borde que da efecto 3D */
            transition: all 0.2s ease;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        
        div.stButton > button:hover {
            transform: translateY(2px); /* Se hunde un poco al pasar el ratón */
            border-bottom: 2px solid #14532d;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            background: linear-gradient(45deg, #22c55e, #16a34a); /* Brilla más */
        }
        
        div.stButton > button:active {
            transform: translateY(4px); /* Se hunde del todo al clicar */
            border-bottom: 0px solid transparent;
        }

        /* Burbujas de chat elegantes */
        div[data-testid="stChatMessage"] {
            padding: 1.5rem;
            border-radius: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }
    }

    /* --- ESTILOS MÓVIL (COMODIDAD TÁCTIL) --- */
    @media only screen and (max-width: 768px) {
        
        .block-container {
            padding-top: 2rem !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }

        /* Cabecera Compacta */
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

        /* Botones Planos y Grandes (Touch Friendly) */
        div.stButton > button {
            background-color: #16a34a;
            color: white;
            border: none;
            border-radius: 8px;
            padding: 0.8rem;
            font-weight: bold;
            width: 100%;
            min-height: 50px; /* Altura mínima para el dedo */
            margin-bottom: 8px;
            box-shadow: none; /* Quitamos sombras complejas en móvil */
        }
        
        div.stButton > button:active {
            background-color: #14532d; /* Oscuro al tocar */
        }

        /* Chat Legible */
        div[data-testid="stChatMessage"] {
            padding: 0.8rem;
            margin-bottom: 0.5rem;
            border-radius: 12px;
        }
        div[data-testid="stChatMessage"] p {
            font-size: 16px !important;
            line-height: 1.4;
        }
    }
    
    /* COLORES DE CHAT (COMUNES) */
    div[data-testid="stChatMessage"]:nth-child(odd) { background-color: #14532d; border: none; }
    div[data-testid="stChatMessage"]:nth-child(odd) * { color: white !important; }
    div[data-testid="stChatMessage"]:nth-child(even) { background-color: #ffffff; border: 1px solid #bbf7d0; }

    /* UPLOADER */
    div[data-testid="stFileUploader"] {
        background-color: white;
        border: 2px dashed #16a34a;
        border-radius: 10px;
        padding: 10px;
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
    st.success(f"✅ Guardado")

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
    st.image("https://cdn-icons-png.flaticon.com/512/1624/1624022.png", width=60) 
    st.markdown("### 🦖 GodzillaBot")
    
    with st.expander("📤 PDFs"):
        up = st.file_uploader("Subir archivos", type="pdf")
        if up and save_uploaded_file(up): st.rerun()
    
    files = st.multiselect("📚 Archivos:", [f for f in os.listdir(DOCS_DIR) if f.endswith('.pdf')])
    
    st.markdown("---")
    mode = st.radio("Modo:", ["💀 Simulacro", "💬 Chat", "📝 Resumen", "📊 Excel"])
    
    st.markdown("---")
    c1, c2 = st.columns(2)
    if c1.button("💾 Guardar"): save_session_history()
    if c2.button("🗑️ Borrar"): st.session_state.messages = []; st.rerun()
    
    sessions = [f for f in os.listdir(HISTORY_DIR) if f.endswith('.json')]
    if sessions:
        load = st.selectbox("Historial:", ["..."] + sorted(sessions, reverse=True))
        if load != "..." and st.button("Cargar"): load_session_history(load)

# --- 6. ZONA PRINCIPAL ---
st.markdown("""
<div class="header-container">
    <h1>🦖 GodzillaBot</h1>
    <p>Oposiciones - Versión Híbrida</p>
</div>
""", unsafe_allow_html=True)

if "messages" not in st.session_state: st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

if prompt := st.chat_input("Escribe aquí..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    if not files:
        st.warning("⚠️ Carga PDFs en el menú (arriba izquierda).")
    else:
        with st.chat_message("assistant"):
            placeholder = st.empty()
            full_resp = ""
            
            try:
                with st.spinner("🦖 Pensando..."): 
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
                        st.download_button("📄 Word", docx, f"Godzilla_{datetime.now().strftime('%H%M')}.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
                
                with col2:
                    if "Tabular" in mode or "|" in full_resp:
                        st.download_button("📊 Excel", full_resp, "datos.csv", "text/csv")

            except Exception as e: st.error(f"Error: {e}")