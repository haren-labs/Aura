"""Il "cervello" di Aura: costruisce il prompt, parla con LM Studio e ricorda la conversazione."""
import threading
from datetime import datetime
import requests
from config import LM_STUDIO_URL, MODEL, MAX_STORIA
from prompt import SYSTEM_PROMPT
from stato import stato
from memoria import carica_memoria, salva_memoria
from ricerca import ha_bisogno_web, cerca_web, ha_bisogno_lavoro, cerca_lavoro_testo
from visione import ha_bisogno_webcam, cattura_webcam
from immagini import genera_immagine

memoria_precedente = carica_memoria()
if memoria_precedente:
    print("Memoria caricata!")
else:
    print("Nessuna memoria precedente")

storia = []

# Aura pensa una cosa alla volta: se arrivano due domande insieme
# (dashboard e telefono), la seconda aspetta che finisca la prima
lucchetto_aura = threading.Lock()

def numero_scambi():
    return len(storia) // 2

def chiedi_ad_aura(testo, immagine_b64=None):
    global storia
    contesto_extra = ""

    if ha_bisogno_lavoro(testo):
        stato["stato"] = "cerco offerte di lavoro"
        contesto_extra = cerca_lavoro_testo()
    elif ha_bisogno_web(testo):
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

def chiedi_in_sicurezza(testo, immagine=None):
    with lucchetto_aura:
        return chiedi_ad_aura(testo, immagine)
