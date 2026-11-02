"""Configurazione di Aura.

Qui ci sono i valori predefiniti. Per cambiarli sul tuo PC NON modificare questo file:
crea accanto un file "config_locale.py" e scrivici solo i valori che vuoi diversi, per esempio:

    NOME_UTENTE = "Marco"
    GENERE_UTENTE = "m"
    HOST = "0.0.0.0"

config_locale.py e' escluso da GitHub (vedi .gitignore): resta solo sul tuo PC.
"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- chi sei -----------------------------------------------------------------
NOME_UTENTE = "Utente"      # come Aura ti chiama
GENERE_UTENTE = ""          # "m", "f" oppure "" (non specificato): serve per parlarti nel genere giusto
PROFILO_UTENTE = ""         # facoltativo: cosa deve sapere Aura di te. Es: "Ama il cinema e lavora come grafico."

# --- servizi -----------------------------------------------------------------
LM_STUDIO_URL = "http://127.0.0.1:1234/v1/chat/completions"
MODEL = "gemma-4-e4b-uncensored-hauhaucs-aggressive"  # nome del modello caricato in LM Studio (serve la visione per webcam/immagini)
TTS_URL = "http://localhost:5050/v1/audio/speech"     # container Edge TTS (vedi README)
TTS_VOICE = "it-IT-IsabellaNeural"
TTS_API_KEY = "your_api_key_here"   # openai-edge-tts accetta questo valore di default; cambialo solo se hai impostato API_KEY nel container
COMFYUI_URL = "http://127.0.0.1:8188"
COMFY_CHECKPOINT = "realisticVisionV60B1_v51HyperVAE.safetensors"  # file in ComfyUI/models/checkpoints

# --- rete --------------------------------------------------------------------
PORT = 8888                 # API del server
PORT_DASHBOARD = 8000       # dashboard nel browser
HOST = "127.0.0.1"          # "127.0.0.1" = solo questo PC; "0.0.0.0" = anche altri dispositivi della rete (vedi README)

# --- audio -------------------------------------------------------------------
FFMPEG = "ffmpeg"           # oppure il percorso completo a ffmpeg.exe
FFMPEG_DIR = ""             # facoltativo: cartella di ffmpeg da aggiungere al PATH (es. r"C:\ffmpeg\bin")
DEVICE_INDEX = None         # microfono: None = predefinito di Windows (per sceglierne uno vedi il README)
SAMPLERATE = 16000
DURATA_SECONDI = 8          # durata di ascolto per ogni frase detta a voce
PAUSA_FINE = 0.5
WHISPER_MODEL = "medium"    # tiny / base / small / medium (piu' grande = piu' preciso e piu' pesante)
MAX_TTS_CHARS = 500

# --- memoria e contesto ------------------------------------------------------
MAX_STORIA = 10             # scambi tenuti nel contesto durante la sessione
MAX_RICORDI = 5             # ricordi delle sessioni precedenti iniettati nel prompt

# --- visione e immagini ------------------------------------------------------
WEBCAM_INDEX = 0
HIRES_BASE = 512            # risoluzione di partenza (veloce)
HIRES_SCALE = 2.0           # 512 x 2.0 = 1024 (1.5 = 768 se serve piu' velocita')
HIRES_DENOISE = 0.5         # 0.4 = fedele alla base, 0.6 = piu' dettaglio nuovo

# --- ricerca web -------------------------------------------------------------
PAROLE_WEB_EXTRA = []       # altre parole che fanno partire una ricerca web (es. ["oggi", "adesso"])
RICERCHE_LAVORO = {}        # facoltativo: ricerche di offerte di lavoro per /jobs, es.
                            # {"remote": ("prompt engineer remote job", 3), "italia": ("prompt engineer lavoro Italia", 2)}

# --- cartelle ----------------------------------------------------------------
MEMORIA_FILE = os.path.join(BASE_DIR, "aura_memoria.json")
CARTELLA_DASHBOARD = os.path.join(BASE_DIR, "dashboard")
CARTELLA_TEMP = os.path.join(BASE_DIR, "temp")

# --- valori personali (se esiste config_locale.py) ---------------------------
try:
    from config_locale import *   # noqa: F401,F403
    print("Configurazione personale caricata (config_locale.py)")
except ImportError:
    pass

# --- preparazione ------------------------------------------------------------
if FFMPEG_DIR:
    os.environ["PATH"] = FFMPEG_DIR + os.pathsep + os.environ.get("PATH", "")
os.makedirs(CARTELLA_TEMP, exist_ok=True)
