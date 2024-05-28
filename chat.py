import streamlit as st
from google.oauth2 import service_account
from google.cloud import texttospeech_v1 as texttospeech
import google.generativeai as gemini
import tempfile
import PyPDF2
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import SnowballStemmer
from dotenv import load_dotenv
import os

# Configuración de NLTK
nltk.download('punkt')
nltk.download('stopwords')

# Función para cargar el texto del PDF
def extraer_texto_pdf(archivo):
    texto = ""
    if archivo:
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(archivo.read())
            temp_file_path = temp_file.name
        with open(temp_file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page in range(len(reader.pages)):
                texto += reader.pages[page].extract_text()
        os.unlink(temp_file_path)
    return texto

# Función para preprocesar texto
def preprocesar_texto(texto):
    tokens = word_tokenize(texto, language='spanish')
    tokens = [word.lower() for word in tokens if word.isalpha()]
    stopwords_es = set(stopwords.words('spanish'))
    tokens = [word for word in tokens if word not in stopwords_es]
    stemmer = SnowballStemmer('spanish')
    tokens = [stemmer.stem(word) for word in tokens]
    return " ".join(tokens)

# Cargar la clave API desde el archivo .env
load_dotenv()
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "botidinamix-g.json"  # Reemplaza 'botidinamix-g.json' con el nombre de tu archivo de credenciales

# Cargar credenciales de Google desde el archivo de credenciales JSON
credentials = service_account.Credentials.from_service_account_file("botidinamix-g.json")

# Configuración de Google Generative AI
gemini_key = st.secrets["GEMINI_API_KEY"]
gemini.configure(api_key=gemini_key)

# Instancia el cliente de Text-to-Speech
client = texttospeech.TextToSpeechClient(credentials=credentials)

# Función para obtener respuesta usando Google Gemini
def obtener_respuesta_gemini(pregunta, agente, texto_preprocesado):
    try:
        response = gemini.generate_text(
            prompt=f"Eres Ana y trabajas en el restaurante Sazon Burguer, actúa como {agente} y resuelve las inquietudes de los clientes, tienes un tono muy amable y cordial, puedes utilizar emojis.\n\n{pregunta}\n\nContexto: {texto_preprocesado}"
        )
        respuesta = response.generated_text
        return respuesta

    except Exception as e:
        st.error(f"Error al comunicarse con Google Gemini: {e}")
        return "Lo siento, no puedo procesar tu solicitud en este momento."

# Función para reproducir audio con Google Text-to-Speech
def reproducir_audio(texto):
    input_text = texttospeech.SynthesisInput(text=texto)
    voice = texttospeech.VoiceSelectionParams(
        language_code="es-ES", ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )
    response = client.synthesize_speech(
        input=input_text, voice=voice, audio_config=audio_config
    )
    return response.audio_content

def main():
    # --- Diseño general ---
    st.set_page_config(page_title="SAZON BURGUER RESTAURANTE", page_icon="🤖")

    # --- Estilo CSS ---
    st.markdown("""
        <style>
            .stApp {
               background: rgb(241,241,234);
               background: radial-gradient(circle, rgba(241,241,234,1) 6%, rgba(255,127,8,1) 37%, rgba(235,255,8,1) 95%, rgba(0,0,255,1) 99%);
                text-align: center;
            }
            .stChatMessage {
                transition: background-color 0.5s, color 0.5s;
            }
            .stChatMessage[data-role="user"] {
                background-color: rgba(0, 123, 255, 0.1);
                color: #007bff;
            }
            .stChatMessage[data-role="assistant"] {
                background-color: rgba(40, 167, 69, 0.1);
                color: #28a745;
            }
            #video-container {
                position: relative;
                width: 100%;
                padding-bottom: 56.25%;
                background-color: lightblue;
                overflow: hidden;
            }
            #background-video {
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
            }
            .centered-input {
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100px;
                margin-bottom: 20px;
            }
            .centered-input textarea {
                width: 80%;
                height: 100px;
                font-size: 20px;
                padding: 10px;
                border: 2px solid rgba(111, 66, 193, 1); 
            }
            .custom-spinner {
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100%;
            }
            .custom-spinner div {
                width: 20px;
                height: 20px;
                margin: 5px;
                background-color: #007bff;
                border-radius: 50%;
                animation: custom-spinner 1.2s infinite ease-in-out;
            }
            .custom-spinner div:nth-child(1) {
                animation-delay: -0.24s;
            }
            .custom-spinner div:nth-child(2) {
                animation-delay: -0.12s;
            }
            .custom-spinner div:nth-child(3) {
                animation-delay: 0;
            }
            @keyframes custom-spinner {
                0%, 80%, 100% {
                    transform: scale(0);
                } 40% {
                    transform: scale(1);
                }
            }
            button[kind="primary"] {
                background-color: rgba(111, 66, 193, 1); 
                color: white;
                border: none;
            }
        </style>
    """, unsafe_allow_html=True)

    # --- Barra lateral ---
    with st.sidebar:
        st.title("🤖 RESTAURANTE SAZON BURGUER")
        st.markdown('<p style="color:green;">Brindamos la mejor atención</p>', unsafe_allow_html=True)
        st.markdown("---")

        # Selección de agente
        agente = st.radio(
            "Selecciona el agente:",
            ["Asistente de atención al cliente", "Agente Administrativo"],
            index=0,
            help="Elige el agente con el que quieres interactuar."
        )

        # --- Historial de conversaciones ---
        st.markdown("---")
        st.subheader("🗂️ Historial de Conversaciones")
        if 'mensajes' not in st.session_state:
            st.session_state['mensajes'] = []

        historial_conversaciones = st.session_state['mensajes']
        historial_opciones = [f"Conversación {i+1}" for i in range(len(historial_conversaciones))]
        seleccion_historial = st.selectbox("Selecciona una conversación anterior:", ["Seleccionar"] + historial_opciones)
    
    # Carga de archivo PDF
    archivo_pdf = st.file_uploader("📂 Cargar PDF", type='pdf')

    # --- Video de fondo ---
    video_placeholder = st.empty()
    video_html = """
        <div id="video-container">
            <video id="background-video" autoplay loop muted playsinline>
                <source src="https://cdn.leonardo.ai/users/645c3d5c-ca1b-4ce8-aefa-a091494e0d09/generations/dd8e0b28-efa4-4937-aaab-a1a8ffa47568/dd8e0b28-efa4-4937-aaab-a1a8ffa47568.mp4" type="video/mp4">
            </video>
        </div>
    """
    video_placeholder.markdown(video_html, unsafe_allow_html=True)

    # --- Entrada de usuario y manejo de la conversación ---
    st.markdown("## 💬 HABLAR CON EL AGENTE")
    with st.form(key='chat_form'):
        input_usuario = st.text_area("Escribe tu mensaje:", key="input_usuario", height=80)
        submit_button = st.form_submit_button(label='Enviar')

    if submit_button and input_usuario:
        # Procesar el archivo PDF si está cargado
        texto_pdf = extraer_texto_pdf(archivo_pdf) if archivo_pdf else ""
        texto_preprocesado = preprocesar_texto(texto_pdf) if texto_pdf else ""

        # Obtener la respuesta de Google Gemini
        respuesta = obtener_respuesta_gemini(input_usuario, agente, texto_preprocesado)

        # Guardar la conversación en el historial
        st.session_state['mensajes'].append({"usuario": input_usuario, "asistente": respuesta})

        # Mostrar la conversación
        for mensaje in st.session_state['mensajes']:
            st.write(f"**Usuario:** {mensaje['usuario']}")
            st.write(f"**Asistente:** {mensaje['asistente']}")

        # Convertir la respuesta a audio y reproducirla
        audio_content = reproducir_audio(respuesta)
        st.audio(audio_content, format='audio/mp3')

if __name__ == "__main__":
    main()
