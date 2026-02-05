import streamlit as st
import os
from dotenv import load_dotenv
import google.generativeai as genai
from pypdf import PdfReader
import json
from datetime import datetime
import io
import time

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

# --- 3. CEREBRO INTELIGENTE: SISTEMA DE RELEVOS (NUEVO) ---
@st.cache_resource
def get_model_chain():
    """
    Crea una cadena de mando de modelos. Si el general cae, el teniente toma el mando.
    Orden: Flash (Rápido) -> Pro (Potente) -> Legacy (Vieja Guardia)
    """
    try:
        # 1. Obtenemos la lista real de lo que Google nos ofrece hoy
        all_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        chain = []
        
        # 2. Reclutamos al mejor Flash (Velocidad)
        flash = [m for m in all_models if 'flash' in m.lower()]
        if flash: chain.append(flash[0]) # El más moderno suele salir primero
        
        # 3. Reclutamos al mejor Pro (Potencia)
        pro = [m for m in all_models if 'pro' in m.lower() and 'vision' not in m.lower()]
        if pro: chain.append(pro[0])
        
        # 4. Reclutamos al Veterano (Gemini-Pro 1.0) por seguridad
        if 'models/gemini-pro' in all_models and 'models/gemini-pro' not in chain:
            chain.append('models/gemini-pro')
            
        # Si la lista está vacía (raro), ponemos los nombres estándar por defecto
        if not chain: return ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']
        
        return chain
    except:
        return ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']

# Inicializamos la cadena de mando
MODEL_CHAIN = get_model_chain()

def generate_response_with_relay(prompt_text):
    """
    Intenta generar respuesta iterando por la cadena de modelos.
    Si uno falla por cuota (429), salta al siguiente.
    """
    last_error = ""
    
    for model_name in MODEL_CHAIN:
        try:
            # Si estamos reintentando (ya falló uno antes), esperamos 1 seg para dar aire
            if last_error: time.sleep(1)
            
            model = genai.GenerativeModel(model_name)
            return model.generate_content(prompt_text, stream=True)
            
        except Exception as e:
            last_error = str(e)
            # Si el error es de Cuota (429) o Modelo no encontrado (404), CONTINUAMOS
            if "429" in last_error or "quota" in last_error.lower() or "404" in last_error:
                continue 
            # Si es otro tipo de error grave, también probamos suerte con el siguiente
            continue

    # Si llegamos aquí, es que han caído todos los soldados
    return f"Error_Quota: {last_error}"

# --- 4. ARQUITECTURA VISUAL (V13 - CONSERVADA) ---
st.markdown("""
<style>
    /* === 1. LIMPIEZA === */
    [data-testid="stHeader"] { background-color: transparent !important; z-index: 90 !important; }
    [data-testid="stToolbar"] { display: none !important; }
    [data-testid="stDecoration"] { display: none !important; }
    footer { visibility: hidden; }

    /* === 2. BOTÓN MENÚ (SIDEBAR) - BURBUJA FLOTANTE === */
    [data-testid="stSidebarCollapsedControl"] {
        display: block !important;
        background-color: white !important;
        border: 2px solid #16a34a !important;
        color: #16a34a !important;
        border-radius: 50% !important;
        width: 45px !important;
        height: 45px !important;
        padding: 5px !important;
        box-shadow: 0 4px 8px rgba(0,0,0,0.15) !important;
        z-index: 100 !important; 
        position: fixed;
        top: 15px;
        left: 15px;
    }
    [data-testid="stSidebarCollapsedControl"]:hover {
        transform: scale(1.1);
        background-color: #f0fdf4 !important;
    }

    /* === 3. ESTÉTICA === */
    .stApp { background-color: #f0fdf4; font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }

    .header-container {
        background: linear-gradient(90deg, #14532d 0%, #15803d 100%);
        padding: 30px;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin-bottom: 30px;
        box-shadow: 0 10px 25px rgba(21, 128, 61, 0.4);
        border-bottom: 5px solid #4ade80;
        margin-top: 50px; /* Margen extra para no chocar con el botón flotante */
    }
    .header-container h1 { font-size: 2.8rem; margin: 0; text-shadow: 2px 2px 4px rgba(0,0,0,0.3); font-weight: 800;}
    .header-container p { font-size: 1.2rem; opacity: 0.9; margin-top: 10px; font-style: italic; }

    /* Tablas */
    div[data-testid="stMarkdownContainer"] table {
        display: block; overflow-x: auto; width: 100%; border-collapse: collapse; border: 1px solid #bbf7d0;
    }
    div[data-testid="stMarkdownContainer"] th {
        background-color: #14532d; color: white; padding: 12px; min-width: 100px; text-align: left;
    }
    div[data-testid="stMarkdownContainer"] td {
        padding: 10px; border-bottom: 1px solid #eee; min-width: 120px; max-width: 300px; vertical-align: top;
    }

    /* PC */
    @media only screen and (min-width: 769px) {
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #f0fdf4 0%, #dcfce7 100%);
            border-right: 2px solid #4ade80;
        }
        div[role="radiogroup"] > label {
            background-color: white; padding: 12px; border-radius: 8px; margin-bottom: 8px;
            border: 1px solid #bbf7d0; transition: all 0.2s ease; box-shadow: 0 2px 4px rgba(0,0,0,0.02);
        }
        div[role="radiogroup"] > label:hover {
            transform: translateX(5px); border-color: #16a34a; background-color: #f0fdf4; cursor: pointer;
        }
        div.stButton > button {
            background: linear-gradient(45deg, #16a34a, #15803d); color: white; border-radius: 10px;
            padding: 12px; border-bottom: 4px solid #14532d; font-weight: bold; text-transform: uppercase;
        }
        div.stButton > button:hover { transform: translateY(2px); border-bottom: 2px solid #14532d; }
    }

    /* MÓVIL */
    @media only screen and (max-width: 768px) {
        .block-container {
            padding-top: 4rem !important; 
            padding-left: 0.8rem !important; padding-right: 0.8rem !important;
        }
        .header-container { padding: 20px; margin-bottom: 20px; margin-top: 40px; }
        .header-container h1 { font-size: 1.8rem !important; }
        .header-container p { font-size: 0.9rem !important; display: block; }

        div.stButton > button {
            background: linear-gradient(45deg, #16a34a, #15803d); color: white; border-radius: 8px;
            padding: 0.8rem; width: 100%; min-height: 50px; font-weight: bold;
        }
    }

    /* LANDSCAPE */
    @media only screen and (orientation: landscape) and (max-height: 600px) {
        .block-container { padding-top: 1rem !important; }
        .header-container {
            padding: 5px !important; margin-bottom: 10px !important; margin-top: 0px;
            display: flex; align-items: center; justify-content: center; min-height: 40px;
        }
        .header-container h1 { font-size: 1.2rem !important; margin: 0; }
        .header-container p { display: none !important; }
    }
    
    div[data-testid="stChatMessage"]:nth-child(odd) { background-color: #14532d; border: none; }
    div[data-testid="stChatMessage"]:nth-child(odd) * { color: white !important; }
    div[data-testid="stChatMessage"]:nth-child(even) { background-color: white; border: 1px solid #bbf7d0; }
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

def get_system_prompt(mode):
    base = "Eres GodzillaBot. Base: PDFs adjuntos. "
    if "Simulacro" in mode:
        return base + "MODO: Simulacro (Ruleta). SALIDA: Cuestionario numerado y Clave de Respuestas final."
    elif "Excel" in mode:
        return base + "Salida: Tabla compatible con Excel (separador |)."
    else:
        return base + "Responde de forma técnica y estructurada."

# --- 6. MENÚ LATERAL ---
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

# --- 7. ZONA PRINCIPAL ---
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
                # Usamos la nueva lógica de relevo
                with st.spinner("🦖 Procesando..."): 
                    text = extract_text_from_pdfs(files)
                    prompt_final = f"{get_system_prompt(mode)}\nDOCS: {text[:800000]}\nUSER: {prompt}"
                    
                    response_obj = generate_response_with_relay(prompt_final)

                    if isinstance(response_obj, str) and response_obj.startswith("Error_Quota"):
                        st.error("🛑 Todos los modelos están agotados. Espera 1 minuto.")
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