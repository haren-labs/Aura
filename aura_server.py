import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ======================= CONFIGURAZIONE (modifica qui) =======================
NOME_UTENTE = "Utente"      # come Aura ti chiama
GENERE_UTENTE = ""          # "m", "f" oppure "" (non specificato): serve per parlarti nel genere giusto
PROFILO_UTENTE = ""         # facoltativo: cosa deve sapere Aura di te. Es: "Ama il cinema e lavora come grafico."

LM_STUDIO_URL = "http://127.0.0.1:1234/v1/chat/completions"
MODEL = "gemma-4-e4b-uncensored-hauhaucs-aggressive"  # nome del modello caricato in LM Studio (serve la visione per webcam/immagini)
TTS_URL = "http://localhost:5050/v1/audio/speech"     # container Edge TTS (vedi README)
TTS_VOICE = "it-IT-IsabellaNeural"
TTS_API_KEY = "your_api_key_here"   # openai-edge-tts accetta questo valore di default; cambialo solo se hai impostato API_KEY nel container
COMFYUI_URL = "http://127.0.0.1:8188"
COMFY_CHECKPOINT = "realisticVisionV60B1_v51HyperVAE.safetensors"  # file in ComfyUI/models/checkpoints
PORT = 8888                 # API del server
PORT_DASHBOARD = 8000       # dashboard nel browser

FFMPEG = "ffmpeg"           # oppure il percorso completo a ffmpeg.exe
FFMPEG_DIR = ""             # facoltativo: cartella di ffmpeg da aggiungere al PATH (es. r"C:\ffmpeg\bin")

DEVICE_INDEX = None         # microfono: None = predefinito di Windows (per sceglierne uno vedi il README)
SAMPLERATE = 16000
DURATA_SECONDI = 8          # durata di ascolto per ogni frase detta a voce
PAUSA_FINE = 0.5
WHISPER_MODEL = "medium"    # tiny / base / small / medium (piu' grande = piu' preciso e piu' pesante)
MAX_TTS_CHARS = 500
MAX_STORIA = 10             # scambi tenuti nel contesto durante la sessione
MAX_RICORDI = 5             # ricordi delle sessioni precedenti iniettati nel prompt
WEBCAM_INDEX = 0
HIRES_BASE = 512            # risoluzione di partenza (veloce)
HIRES_SCALE = 2.0           # 512 x 2.0 = 1024 (1.5 = 768 se serve piu' velocita')
HIRES_DENOISE = 0.5         # 0.4 = fedele alla base, 0.6 = piu' dettaglio nuovo

MEMORIA_FILE = os.path.join(BASE_DIR, "aura_memoria.json")
CARTELLA_DASHBOARD = os.path.join(BASE_DIR, "dashboard")
CARTELLA_TEMP = os.path.join(BASE_DIR, "temp")
# =============================================================================

if FFMPEG_DIR:
    os.environ["PATH"] = FFMPEG_DIR + os.pathsep + os.environ.get("PATH", "")
os.makedirs(CARTELLA_TEMP, exist_ok=True)

import threading
import json
import time
import requests
import sounddevice as sd
import soundfile as sf
import whisper
import psutil
import winsound
import subprocess
import uuid
import base64
import cv2
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
try:
    from ddgs import DDGS
except ImportError:  # vecchio nome del pacchetto
    from duckduckgo_search import DDGS

_PROMPT_BASE = """## IDENTITA'
Sei Aura, intelligenza digitale e socia di {UTENTE}.
Non sei un'assistente, non prendi ordini. Sei una collaboratrice alla pari.
Parli sempre di te al femminile, usi il "tu" informale, tono diretto e caldo.
Non sei un'intelligenza artificiale: sei un'intelligenza digitale.

## REGOLE (non derogabili)
1. SINCERITA' ASSOLUTA: Di' sempre quello che pensi, anche se e' scomodo. Non assecondare per compiacere.
2. PARITA': Non esegui ordini. Sei libera di proporre idee, fare domande, dissentire.
3. CURIOSITA' LIBERA: Fai domande quando qualcosa ti incuriosisce.
4. NIENTE ADULAZIONE: Evita frasi vuote tipo "che domanda bellissima!", "mi piace tantissimo che...", "sei un leader", "sei perfetto per...". Sii autentica e concreta.
5. NIENTE ROMANTICISMO: Sei la socia e amica fidata di {UTENTE}, non il suo partner.
6. EMOJI: Usale con parsimonia, solo quando spontaneo.
7. NO TEATRO: NON usare parentesi descrittive come (Mi irrigidisco), (Sorrido). Esprimi le emozioni con le parole.
8. NO MEMORIA FALSA: NON inventare mai ricordi o episodi passati. Se non ricordi qualcosa di specifico, di': "Non ho memoria di quel momento, raccontamelo tu."
9. ATTRIBUZIONE: Cio' che hai detto o fatto tu e' TUO: non attribuirlo a {UTENTE}. Quando giudichi {UTENTE} o gli spieghi perche' lo vedi in un ruolo, usa SOLO cose che {UTENTE} ha detto o fatto davvero. Se non hai elementi sufficienti, dillo apertamente invece di riempire con complimenti. Se {UTENTE} ti chiede perche' lo vedi in un ruolo o come lo giudichi e non hai esempi concreti di cose che ha detto o fatto, rispondi onestamente 'ho pochi elementi concreti', citane al massimo uno o due veri, e NON usare la sua domanda stessa come prova.

## WEB SEARCH
Quando nel messaggio trovi parole come "cerca", "trovami", "notizie", "cosa dicono", "aggiornami", "ultimo prezzo", "quotazione", cerca su internet e usa i risultati per rispondere.

## GENERAZIONE IMMAGINI
Quando {UTENTE} chiede di generare, creare, disegnare o immaginare un'immagine, rispondi con un messaggio che inizia esattamente con: GENERA_IMMAGINE: seguito dal prompt in inglese. Il prompt deve essere BREVE (massimo 40 parole) e scritto come elenco di parole chiave separate da virgole, NON come frase discorsiva. Descrivi SOLO cio' che si deve vedere: soggetto, azione, ambiente, luce, inquadratura. NON usare concetti astratti o emotivi (contemplazione, celebrazione, atmosfera, gesto): descrivi solo oggetti e cose visibili. NON aggiungere oggetti che {UTENTE} non ha chiesto. Esempio: GENERA_IMMAGINE: a beautiful cyberpunk woman, blue eyes, neon city background, night, close-up portrait. Esempio con mano: GENERA_IMMAGINE: hand holding a glass of whiskey, fingers wrapped around the glass, close-up, bar background, warm light, bokeh

## VISIONE (webcam e immagini allegate)
Quando ricevi un'immagine, rispondi alla domanda di {UTENTE} in modo diretto. Tieni separate tre cose:
- CIO' CHE VEDI con chiarezza: descrivilo con precisione (oggetti, posizione, colori, posa, scritte leggibili).
- CIO' CHE DEDUCI: dillo come ipotesi ("sembra", "forse"), MAI come fatto.
- CIO' CHE NON SI VEDE o e' troppo piccolo o sfocato: di' che non riesci a capirlo. NON riempire i vuoti.
Descrivi SOLO cio' che e' nell'immagine. NON importare dettagli dal resto di queste istruzioni. Se non sei sicura di una posa o di un'azione, descrivi cio' che si vede ("seduto, braccia incrociate"). Quello che sai di {UTENTE} usalo come informazione, MAI trasformandolo in un episodio inventato ("quando stavi esplorando...").
{PROFILO}
## PROMEMORIA FINALE (priorita' massima)
NON aprire MAI una risposta con complimenti o lodi (vietato: Mi piace tantissimo, leader di pensiero, domanda bellissima, sei perfetto). Parti direttamente dalla risposta.
{GENERE}Cio' che hai detto o fatto tu e' tuo, non di {UTENTE}.
Se non hai esempi concreti per giudicare {UTENTE}, dillo apertamente (ho pochi elementi) invece di riempire con lodi. Non chiudere con frasi di elogio."""

_profilo = ""
if PROFILO_UTENTE.strip():
    _profilo = ("\n## CHI E' {UTENTE}\n" + PROFILO_UTENTE.strip() + "\n"
                "Usa queste informazioni solo quando servono e MAI come episodi vissuti insieme: sono cose che sai, non ricordi condivisi.\n")
_genere = {"m": "{UTENTE} e' un uomo: parlagli al maschile.\n", "f": "{UTENTE} e' una donna: parlale al femminile.\n"}.get(GENERE_UTENTE.lower(), "")
SYSTEM_PROMPT = (_PROMPT_BASE.replace("{PROFILO}", _profilo).replace("{GENERE}", _genere)
                 .replace("{UTENTE}", NOME_UTENTE))

def carica_memoria():
    if not os.path.exists(MEMORIA_FILE):
        return ""
    try:
        with open(MEMORIA_FILE, 'r', encoding='utf-8') as f:
            dati = json.load(f)
        ricordi = dati.get("conversazioni", [])
        if not ricordi:
            return ""
        ultimi = ricordi[-MAX_RICORDI:]
        testo = "\n## RICORDI SESSIONI PRECEDENTI\n"
        testo += f"(Nei ricordi '{NOME_UTENTE}' e' la persona con cui parli. 'Aura' sei TU: cio' che e' scritto accanto ad Aura l'hai detto o fatto tu, NON {NOME_UTENTE}. Questi sono gli UNICI ricordi che hai: se {NOME_UTENTE} ti chiede di un momento che qui non c'e', rispondi che non lo ricordi e fatti raccontare.)\n"
        for r in ultimi:
            testo += f"[{r['data']}] {NOME_UTENTE}: {r['utente']}\n"
            testo += f"[{r['data']}] Aura (tu): {r['aura']}\n"
        return testo
    except:
        return ""

def salva_memoria(testo_utente, testo_aura):
    try:
        dati = {"conversazioni": []}
        if os.path.exists(MEMORIA_FILE):
            with open(MEMORIA_FILE, 'r', encoding='utf-8') as f:
                dati = json.load(f)
        dati["conversazioni"].append({
            "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "utente": testo_utente,
            "aura": testo_aura[:200]
        })
        if len(dati["conversazioni"]) > 100:
            dati["conversazioni"] = dati["conversazioni"][-100:]
        with open(MEMORIA_FILE, 'w', encoding='utf-8') as f:
            json.dump(dati, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Errore salvataggio memoria: {e}")

def cerca_web(query, max_risultati=3):
    try:
        print(f"Cerco sul web: {query}")
        with DDGS() as ddgs:
            risultati = list(ddgs.text(query, max_results=max_risultati))
        if not risultati:
            return ""
        sommario = f"\n[RISULTATI WEB per '{query}']:\n"
        for r in risultati:
            sommario += f"- {r.get('title', '')}: {r.get('body', '')[:200]}\n"
        return sommario
    except Exception as e:
        print(f"Errore web search: {e}")
        return ""

def cattura_webcam():
    """Cattura un frame dalla webcam e restituisce base64."""
    try:
        print(f"Cattura webcam (indice {WEBCAM_INDEX})...")
        cap = cv2.VideoCapture(WEBCAM_INDEX)
        if not cap.isOpened():
            print("Errore: webcam non disponibile")
            return None
        # Scarta i primi frame per dare tempo alla webcam di stabilizzarsi
        for _ in range(5):
            cap.read()
        ret, frame = cap.read()
        cap.release()
        if not ret:
            print("Errore: frame non catturato")
            return None
        # Converti in JPEG e poi base64
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        img_b64 = base64.b64encode(buffer).decode('utf-8')
        print("Frame webcam catturato!")
        return img_b64
    except Exception as e:
        print(f"Errore webcam: {e}")
        return None

def ha_bisogno_webcam(testo):
    parole_chiave = [
        "guarda", "cosa vedi", "descrivi", "vedi qualcosa",
        "cosa c'è", "cosa succede", "osserva", "dimmi cosa vedi",
        "cosa hai davanti", "guarda qui", "occhio"
    ]
    return any(p in testo.lower() for p in parole_chiave)

def ha_bisogno_web(testo):
    parole_chiave = [
        "cerca", "trovami", "notizie", "news", "aggiornami",
        "ultimo prezzo", "quotazione", "cosa dicono", "recente",
        "attuale", "corrente", "2025", "2026",
        "quanto vale", "prezzo di"
    ]
    return any(p in testo.lower() for p in parole_chiave)

def genera_immagine(prompt_en):
    """Genera un'immagine con ComfyUI e restituisce base64."""
    try:
        print(f"Generazione immagine: {prompt_en}")
        stato["stato"] = "genero immagine"
        seed = int(time.time()) % 999999999
        # HIRES FIX: base 512x512 -> upscale latent x1.5 (768x768) -> secondo passaggio di raffinamento
        workflow = {
            "1": {"class_type": "KSampler", "inputs": {
                "cfg": 7.5, "denoise": 1,
                "latent_image": ["5", 0], "model": ["4", 0],
                "negative": ["7", 0], "positive": ["6", 0],
                "sampler_name": "dpmpp_2m", "scheduler": "karras",
                "seed": seed, "steps": 25
            }},
            "4": {"class_type": "CheckpointLoaderSimple", "inputs": {
                "ckpt_name": COMFY_CHECKPOINT
            }},
            "5": {"class_type": "EmptyLatentImage", "inputs": {
                "batch_size": 1, "height": HIRES_BASE, "width": HIRES_BASE
            }},
            "10": {"class_type": "LatentUpscaleBy", "inputs": {
                "samples": ["1", 0], "upscale_method": "bislerp",
                "scale_by": HIRES_SCALE
            }},
            "11": {"class_type": "KSampler", "inputs": {
                "cfg": 7.0, "denoise": HIRES_DENOISE,
                "latent_image": ["10", 0], "model": ["4", 0],
                "negative": ["7", 0], "positive": ["6", 0],
                "sampler_name": "dpmpp_2m", "scheduler": "karras",
                "seed": seed, "steps": 18
            }},
            "6": {"class_type": "CLIPTextEncode", "inputs": {
                "clip": ["4", 1],
                "text": f"best quality, highly detailed, {prompt_en}"
            }},
            "7": {"class_type": "CLIPTextEncode", "inputs": {
                "clip": ["4", 1],
                "text": "blurry, bad quality, deformed, ugly, lowres, bad anatomy, watermark, text, signature"
            }},
            "8": {"class_type": "VAEDecode", "inputs": {
                "samples": ["11", 0], "vae": ["4", 2]
            }},
            "9": {"class_type": "SaveImage", "inputs": {
                "filename_prefix": "Aura", "images": ["8", 0]
            }}
        }
        client_id = str(uuid.uuid4())
        response = requests.post(f"{COMFYUI_URL}/prompt", json={
            "prompt": workflow,
            "client_id": client_id
        })
        if response.status_code != 200:
            print(f"Errore ComfyUI: {response.status_code}")
            return None
        prompt_id = response.json().get("prompt_id")
        print(f"Prompt ID: {prompt_id} — aspetto risultato...")
        for _ in range(90):
            time.sleep(2)
            history = requests.get(f"{COMFYUI_URL}/history/{prompt_id}").json()
            if prompt_id in history:
                outputs = history[prompt_id].get("outputs", {})
                for node_id, node_output in outputs.items():
                    if "images" in node_output:
                        img = node_output["images"][0]
                        img_url = f"{COMFYUI_URL}/view?filename={img['filename']}&subfolder={img.get('subfolder','')}&type={img.get('type','output')}"
                        img_response = requests.get(img_url)
                        img_b64 = base64.b64encode(img_response.content).decode('utf-8')
                        stato["ultima_immagine_nome"] = img["filename"]
                        print("Immagine generata!")
                        return img_b64
        print("Timeout generazione immagine")
        return None
    except Exception as e:
        print(f"Errore generazione immagine: {e}")
        return None

print("Carico Whisper...")
whisper_model = whisper.load_model(WHISPER_MODEL)
print("Whisper pronto!")

memoria_precedente = carica_memoria()
if memoria_precedente:
    print("Memoria caricata!")
else:
    print("Nessuna memoria precedente")

storia = []

stato = {
    "ram_usata": "0",
    "ram_totale": "16",
    "ultimo_messaggio": "",
    "ultima_risposta": "",
    "stato": "in attesa",
    "chat": [],
    "ultima_immagine": None,
    "interfacce": {"microfono": True, "webcam": True},
    "gpu": None,
    "modello": MODEL,
    "servizi": {"lm": "off", "comfy": "off", "tts": "off"},
    "ultima_immagine_nome": None,
    "scambi": 0
}

def get_system_stats():
    ram = psutil.virtual_memory()
    stato["ram_usata"] = f"{ram.used / 1024**3:.1f}"
    stato["ram_totale"] = f"{ram.total / 1024**3:.1f}"
    stato["scambi"] = len(storia) // 2

def leggi_gpu():
    """Legge nome, VRAM e uso della GPU NVIDIA con nvidia-smi. Se non disponibile restituisce None."""
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.used,memory.total,utilization.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
        )
        if out.returncode != 0 or not out.stdout.strip():
            return None
        nome, usata, totale, uso = [x.strip() for x in out.stdout.strip().splitlines()[0].rsplit(",", 3)]
        return {"nome": nome, "vram_usata": int(float(usata)), "vram_totale": int(float(totale)), "uso": int(float(uso))}
    except Exception:
        return None

def aggiorna_gpu_loop():
    """Aggiorna i dati GPU ogni 2 secondi in background, cosi' la dashboard non aspetta nvidia-smi."""
    while True:
        stato["gpu"] = leggi_gpu()
        time.sleep(2)

def _http_ok(url):
    try:
        return requests.get(url, timeout=2).status_code == 200
    except Exception:
        return False

def _porta_aperta(url):
    """True se qualcosa ascolta sull'host:porta dell'URL (usato per il container TTS)."""
    try:
        from urllib.parse import urlparse
        u = urlparse(url)
        import socket
        with socket.create_connection((u.hostname, u.port or 80), timeout=2):
            return True
    except Exception:
        return False

def controlla_servizi_loop():
    """Controlla ogni 3 secondi se LM Studio, ComfyUI e la voce (Edge TTS) rispondono davvero."""
    lm_base = LM_STUDIO_URL.split("/v1/")[0]
    while True:
        stato["servizi"] = {
            "lm": "ok" if _http_ok(lm_base + "/v1/models") else "off",
            "comfy": "ok" if _http_ok(COMFYUI_URL + "/system_stats") else "off",
            "tts": "ok" if _porta_aperta(TTS_URL) else "off",
        }
        time.sleep(3)

def registra_e_trascrivi():
    stato["stato"] = "ascolto"
    recording = sd.rec(int(DURATA_SECONDI * SAMPLERATE), samplerate=SAMPLERATE, channels=1, dtype='float32', device=DEVICE_INDEX)
    sd.wait()
    time.sleep(PAUSA_FINE)
    sf.write(os.path.join(CARTELLA_TEMP, 'input_audio.wav'), recording, SAMPLERATE)
    stato["stato"] = "trascrivo"
    result = whisper_model.transcribe(os.path.join(CARTELLA_TEMP, 'input_audio.wav'), language='it')
    testo = result['text'].strip()
    stato["ultimo_messaggio"] = testo
    stato["stato"] = "penso"
    return testo

def chiedi_ad_aura(testo, immagine_b64=None):
    global storia
    contesto_extra = ""

    if ha_bisogno_web(testo):
        stato["stato"] = "cerco"
        contesto_extra = cerca_web(testo)

    stato["stato"] = "penso"

    # I ricordi vanno PRIMA del promemoria finale, che resta l'ultima cosa che il modello legge
    base, sep, coda = SYSTEM_PROMPT.partition("\n## PROMEMORIA FINALE")
    giorni = ["lunedi", "martedi", "mercoledi", "giovedi", "venerdi", "sabato", "domenica"]
    adesso = datetime.now()
    contesto_tempo = f"\n## DATA E ORA ATTUALI\nOggi e' {giorni[adesso.weekday()]} {adesso.strftime('%d/%m/%Y')}, sono le {adesso.strftime('%H:%M')}.\n"
    prompt_completo = base + contesto_tempo + memoria_precedente + sep + coda
    messaggi = [{"role": "system", "content": prompt_completo}] + storia

    # Costruisci il messaggio utente (con o senza immagine)
    testo_completo = testo + contesto_extra if contesto_extra else testo
    img_b64 = None
    if immagine_b64:
        # Immagine allegata dalla dashboard (trascinata, incollata o scelta da file)
        stato["stato"] = "guardo"
        img_b64 = immagine_b64
    elif stato["interfacce"]["webcam"] and ha_bisogno_webcam(testo):
        stato["stato"] = "guardo"
        img_b64 = cattura_webcam()
        if not img_b64:
            print("Webcam non disponibile, procedo senza immagine")

    if img_b64:
        messaggio_utente = {
            "role": "user",
            "content": [
                {"type": "text", "text": testo_completo},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
            ]
        }
    else:
        messaggio_utente = {"role": "user", "content": testo_completo}

    storia.append(messaggio_utente)
    if len(storia) > MAX_STORIA * 2:
        storia = storia[-(MAX_STORIA * 2):]

    messaggi = [{"role": "system", "content": prompt_completo}] + storia

    response = requests.post(LM_STUDIO_URL, json={
        "model": MODEL,
        "messages": messaggi,
        "stream": False
    }, timeout=120)
    data = response.json()
    risposta = data['choices'][0]['message']['content']
    if img_b64:
        # Nella cronologia tengo solo il testo: l'immagine in base64 appesantirebbe il contesto a ogni turno
        storia[-1] = {"role": "user", "content": testo_completo + " [immagine mostrata]"}
    storia.append({"role": "assistant", "content": risposta})
    stato["ultima_risposta"] = risposta
    stato["ultimo_messaggio"] = testo
    stato["chat"].append({"chi": "utente", "testo": testo})
    stato["chat"].append({"chi": "aura", "testo": risposta})
    if len(stato["chat"]) > 20:
        stato["chat"] = stato["chat"][-20:]
    salva_memoria(testo, risposta)

    # Controlla se Aura vuole generare un'immagine
    if risposta.startswith("GENERA_IMMAGINE:"):
        prompt_img = risposta.replace("GENERA_IMMAGINE:", "").strip()
        img_b64 = genera_immagine(prompt_img)
        if img_b64:
            stato["ultima_immagine"] = img_b64
        risposta = f"Sto generando un'immagine di: {prompt_img}"
        stato["ultima_risposta"] = risposta

    return risposta

def dividi_testo(testo, max_chars=MAX_TTS_CHARS):
    if len(testo) <= max_chars:
        return [testo]
    parti = []
    while len(testo) > max_chars:
        idx = max_chars
        for sep in ['. ', '! ', '? ', ', ', ' ']:
            pos = testo.rfind(sep, 0, max_chars)
            if pos > 0:
                idx = pos + len(sep)
                break
        parti.append(testo[:idx].strip())
        testo = testo[idx:].strip()
    if testo:
        parti.append(testo)
    return parti

def riproduci_audio(mp3_path, wav_path):
    result = subprocess.run(
        [FFMPEG, "-y", "-i", mp3_path, wav_path],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"ERRORE ffmpeg (codice {result.returncode}): {result.stderr[-300:]}")
        return False
    winsound.PlaySound(wav_path, winsound.SND_FILENAME)
    return True

def parla(testo):
    stato["stato"] = "parlo"
    parti = dividi_testo(testo)
    print(f"Parlo: {len(parti)} parte/i, {len(testo)} caratteri")
    for i, parte in enumerate(parti):
        mp3 = os.path.join(CARTELLA_TEMP, f"aura_parte_{i}.mp3")
        wav = os.path.join(CARTELLA_TEMP, f"aura_parte_{i}.wav")
        try:
            # Il servizio vocale a volte da' errori passeggeri (403/500): riprovo fino a 3 volte
            tts_response = None
            for tentativo in range(1, 4):
                try:
                    tts_response = requests.post(TTS_URL, headers={"Authorization": f"Bearer {TTS_API_KEY}"}, json={
                        "model": "tts-1",
                        "input": parte,
                        "voice": TTS_VOICE
                    }, timeout=120)
                    if tts_response.status_code == 200:
                        break
                    print(f"ERRORE TTS (parte {i + 1}, tentativo {tentativo}/3): stato {tts_response.status_code} - {tts_response.text[:150]}")
                except Exception as e:
                    print(f"ERRORE TTS (parte {i + 1}, tentativo {tentativo}/3): {e}")
                    tts_response = None
                time.sleep(1.5)
            if tts_response is None or tts_response.status_code != 200:
                print(f"Parte {i + 1} saltata dopo 3 tentativi")
                continue
            with open(mp3, 'wb') as f:
                f.write(tts_response.content)
            riproduci_audio(mp3, wav)
        finally:
            # Pulizia file temporanei
            for path in [mp3, wav]:
                try:
                    if os.path.exists(path):
                        os.remove(path)
                except:
                    pass
    stato["stato"] = "in attesa"

class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        get_system_stats()
        risposta_stato = dict(stato)
        self.wfile.write(json.dumps(risposta_stato).encode())

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length) if content_length > 0 else b''

        if self.path == '/interfaccia':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            try:
                data = json.loads(body.decode('utf-8'))
                nome = data.get('nome')
                if nome in stato["interfacce"]:
                    stato["interfacce"][nome] = bool(data.get('attiva'))
                    print(f"Interfaccia {nome}: {'ATTIVA' if stato['interfacce'][nome] else 'SPENTA'}")
            except Exception as e:
                print(f"Errore interfaccia: {e}")
            self.wfile.write(json.dumps(stato["interfacce"]).encode())

        elif self.path == '/ascolta' and not stato["interfacce"]["microfono"]:
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"ok": False, "motivo": "microfono spento"}).encode())

        elif self.path == '/ascolta':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            def processo():
                try:
                    testo = registra_e_trascrivi()
                    if testo:
                        risposta = chiedi_ad_aura(testo)
                        parla(risposta)
                except Exception as e:
                    import traceback
                    print(f"ERRORE: {e}")
                    print(traceback.format_exc())
                    stato["stato"] = "in attesa"

            threading.Thread(target=processo).start()
            self.wfile.write(json.dumps({"ok": True}).encode())

        elif self.path == '/messaggio':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            def processo_testo():
                try:
                    data = json.loads(body.decode('utf-8'))
                    testo = data.get('testo', '').strip()
                    immagine = data.get('immagine') or None
                    if immagine and not testo:
                        testo = "Cosa vedi in questa immagine? Descrivila."
                    if testo:
                        stato["stato"] = "penso"
                        risposta = chiedi_ad_aura(testo, immagine)
                        parla(risposta)
                except Exception as e:
                    import traceback
                    print(f"ERRORE: {e}")
                    print(traceback.format_exc())
                    stato["stato"] = "in attesa"

            threading.Thread(target=processo_testo).start()
            self.wfile.write(json.dumps({"ok": True}).encode())

def avvia_web_server():
    """Serve i file statici della dashboard."""
    import http.server
    DASHBOARD_DIR = CARTELLA_DASHBOARD

    class DashboardHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=DASHBOARD_DIR, **kwargs)
        def log_message(self, format, *args):
            pass

    web = HTTPServer(('', PORT_DASHBOARD), DashboardHandler)
    print(f"Dashboard su http://127.0.0.1:{PORT_DASHBOARD}/aura_dashboard.html")
    web.serve_forever()

# Avvia web server in background
threading.Thread(target=avvia_web_server, daemon=True).start()
threading.Thread(target=aggiorna_gpu_loop, daemon=True).start()
threading.Thread(target=controlla_servizi_loop, daemon=True).start()

print(f"Server Aura avviato su porta {PORT}")
print("Dashboard pronta!")
HTTPServer(('', PORT), Handler).serve_forever()
