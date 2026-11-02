"""Le API di Aura (FastAPI) e il server della dashboard.

Ogni indirizzo e' una funzione con sopra un'etichetta, es. @app.post("/chat").
Con Aura accesa, http://127.0.0.1:8888/docs mostra l'elenco e permette di provarli.
"""
import os
import tempfile
import threading
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

from config import HOST, PORT_DASHBOARD, CARTELLA_DASHBOARD, CARTELLA_TEMP
from stato import stato
from cervello import chiedi_in_sicurezza, numero_scambi
from voce import registra_e_trascrivi, trascrivi_file, parla, voce_mp3
from visione import cattura_webcam
from immagini import genera_immagine
from ricerca import risultati_web, cerca_lavoro, RICERCHE_LAVORO
from servizi import get_system_stats

# Il server "API" (porta 8888) riceve le richieste della dashboard.
# Il server "dashboard" (porta 8000) mostra solo i file della pagina.
app = FastAPI(title="Aura API", description="Il server di Aura: stato, messaggi, voce, immagini, visione e ricerca.")

# Permette alla dashboard (porta 8000) di parlare con l'API (porta 8888)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

# La scheda video genera un'immagine alla volta
lucchetto_immagini = threading.Lock()

# ---------------------------------------------------------------- com'e' fatta ogni richiesta
# FastAPI controlla i dati e li mostra in /docs
class Interfaccia(BaseModel):
    nome: str       # "microfono" oppure "webcam"
    attiva: bool

class Messaggio(BaseModel):
    testo: str = ""
    immagine: str | None = None

class Chat(BaseModel):
    testo: str
    immagine: str | None = None   # immagine in base64, facoltativa
    voce: bool = False

class Immagine(BaseModel):
    prompt: str

class Visione(BaseModel):
    domanda: str = "Cosa vedi? Descrivilo."
    immagine: str | None = None   # se manca, Aura scatta una foto con la webcam
    voce: bool = False

class Voce(BaseModel):
    testo: str
    riproduci: bool = False

class Ricerca(BaseModel):
    query: str
    max_risultati: int = 5

# ---------------------------------------------------------------- lavori in background
def in_background(funzione, *argomenti):
    """Esegue un lavoro lungo (pensare, parlare) senza far aspettare la dashboard."""
    def lavoro():
        try:
            funzione(*argomenti)
        except Exception as e:
            import traceback
            print(f"ERRORE: {e}")
            print(traceback.format_exc())
            stato["stato"] = "in attesa"
    threading.Thread(target=lavoro, daemon=True).start()

def ascolta_e_rispondi():
    testo = registra_e_trascrivi()
    if testo:
        risposta = chiedi_in_sicurezza(testo)
        parla(risposta)

def rispondi_al_messaggio(testo, immagine):
    if immagine and not testo:
        testo = "Cosa vedi in questa immagine? Descrivila."
    if testo:
        stato["stato"] = "penso"
        risposta = chiedi_in_sicurezza(testo, immagine)
        parla(risposta)

# ---------------------------------------------------------------- indirizzi (endpoint)
@app.get("/")
def leggi_stato():
    """Stato completo di Aura: la dashboard lo chiede ogni secondo."""
    get_system_stats(numero_scambi())
    return dict(stato)

@app.get("/servizi")
def servizi():
    """Stato leggero (senza immagini e chat): lo usa la pagina mobile per i pallini."""
    return {"servizi": stato["servizi"], "modello": stato["modello"], "stato": stato["stato"]}

@app.post("/interfaccia")
def cambia_interfaccia(richiesta: Interfaccia):
    """Accende o spegne microfono e webcam."""
    if richiesta.nome in stato["interfacce"]:
        stato["interfacce"][richiesta.nome] = richiesta.attiva
        print(f"Interfaccia {richiesta.nome}: {'ATTIVA' if richiesta.attiva else 'SPENTA'}")
    return stato["interfacce"]

@app.post("/ascolta")
def ascolta():
    """Registra dal microfono, trascrive, risponde e parla."""
    if not stato["interfacce"]["microfono"]:
        return {"ok": False, "motivo": "microfono spento"}
    in_background(ascolta_e_rispondi)
    return {"ok": True}

@app.post("/messaggio")
def messaggio(richiesta: Messaggio):
    """Riceve un messaggio scritto (con immagine facoltativa), risponde e parla."""
    in_background(rispondi_al_messaggio, richiesta.testo.strip(), richiesta.immagine or None)
    return {"ok": True}

@app.post("/chat")
def chat(richiesta: Chat):
    """Fa una domanda ad Aura e restituisce subito la risposta come testo.
    Se Aura genera un'immagine, la restituisce in base64 nel campo "immagine"."""
    testo = richiesta.testo.strip()
    if not testo:
        return {"ok": False, "motivo": "messaggio vuoto"}
    immagine_prima = stato["ultima_immagine"]
    risposta = chiedi_in_sicurezza(testo, richiesta.immagine or None)
    immagine_nuova = None
    if stato["ultima_immagine"] is not immagine_prima:   # Aura ha appena creato un'immagine
        immagine_nuova = stato["ultima_immagine"]
    if richiesta.voce:
        in_background(parla, risposta)
    else:
        stato["stato"] = "in attesa"
    return {"ok": True, "risposta": risposta, "immagine": immagine_nuova}

@app.post("/image")
def image(richiesta: Immagine):
    """Genera un'immagine con ComfyUI (con hires fix) e la restituisce in base64.
    L'immagine compare anche nella dashboard."""
    prompt = richiesta.prompt.strip()
    if not prompt:
        return {"ok": False, "motivo": "prompt vuoto"}
    with lucchetto_immagini:
        img_b64 = genera_immagine(prompt)
    stato["stato"] = "in attesa"
    if not img_b64:
        return {"ok": False, "motivo": "ComfyUI non ha generato l'immagine (e' acceso?)"}
    stato["ultima_immagine"] = img_b64
    return {"ok": True, "immagine": img_b64, "nome_file": stato["ultima_immagine_nome"]}

@app.post("/vision")
def vision(richiesta: Visione):
    """Aura guarda un'immagine (o scatta una foto con la webcam) e risponde alla domanda.
    Se la foto e' della webcam, la restituisce in base64 nel campo "foto"."""
    domanda = richiesta.domanda.strip() or "Cosa vedi? Descrivilo."
    foto = None
    immagine = richiesta.immagine or None
    if not immagine:
        if not stato["interfacce"]["webcam"]:
            return {"ok": False, "motivo": "webcam spenta dalla dashboard"}
        stato["stato"] = "guardo"
        foto = cattura_webcam()
        if not foto:
            stato["stato"] = "in attesa"
            return {"ok": False, "motivo": "webcam non disponibile"}
        immagine = foto
    risposta = chiedi_in_sicurezza(domanda, immagine)
    if richiesta.voce:
        in_background(parla, risposta)
    else:
        stato["stato"] = "in attesa"
    return {"ok": True, "risposta": risposta, "foto": foto}

@app.post("/transcribe")
def transcribe(audio: UploadFile = File(...)):
    """Riceve un file audio (mp3, wav, ogg, webm, m4a...) e lo trascrive in testo con Whisper."""
    estensione = os.path.splitext(audio.filename or "")[1] or ".wav"
    contenuto = audio.file.read()
    if not contenuto:
        return {"ok": False, "motivo": "file audio vuoto"}
    percorso = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=estensione, dir=CARTELLA_TEMP) as f:
            f.write(contenuto)
            percorso = f.name
        return {"ok": True, "testo": trascrivi_file(percorso)}
    except Exception as e:
        print(f"ERRORE /transcribe: {e}")
        return {"ok": False, "motivo": f"trascrizione non riuscita: {e}"}
    finally:
        if percorso and os.path.exists(percorso):
            os.remove(percorso)

@app.post("/speak", responses={200: {"content": {"audio/mpeg": {}}}})
def speak(richiesta: Voce):
    """Trasforma il testo in voce (TTS_VOICE) e restituisce un file MP3."""
    testo = richiesta.testo.strip()
    if not testo:
        return {"ok": False, "motivo": "testo vuoto"}
    audio = voce_mp3(testo)
    if not audio:
        return {"ok": False, "motivo": "il servizio voce non risponde (Docker e' acceso?)"}
    if richiesta.riproduci:
        in_background(parla, testo)
    return Response(content=audio, media_type="audio/mpeg",
                    headers={"Content-Disposition": 'inline; filename="aura.mp3"'})

@app.post("/search")
def search(richiesta: Ricerca):
    """Cerca sul web (DuckDuckGo) e restituisce i risultati, senza passare da Aura."""
    query = richiesta.query.strip()
    if not query:
        return {"ok": False, "motivo": "ricerca vuota"}
    try:
        return {"ok": True, "risultati": risultati_web(query, max(1, min(richiesta.max_risultati, 10)))}
    except Exception as e:
        print(f"ERRORE /search: {e}")
        return {"ok": False, "motivo": f"ricerca non riuscita: {e}"}

@app.get("/jobs")
def jobs():
    """Cerca offerte di lavoro con le ricerche di RICERCHE_LAVORO (config). Se non sono configurate, e' spento."""
    if not RICERCHE_LAVORO:
        return {"ok": False, "motivo": "ricerca lavoro non configurata (RICERCHE_LAVORO in config_locale.py)"}
    try:
        return {"ok": True, "risultati": cerca_lavoro()}
    except Exception as e:
        print(f"ERRORE /jobs: {e}")
        return {"ok": False, "motivo": f"ricerca non riuscita: {e}"}

# ---------------------------------------------------------------- server della dashboard
# Serve i file della cartella CARTELLA_DASHBOARD
dashboard = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
dashboard.mount("/", StaticFiles(directory=CARTELLA_DASHBOARD, html=True), name="dashboard")

def avvia_dashboard():
    uvicorn.run(dashboard, host=HOST, port=PORT_DASHBOARD, log_level="warning")
