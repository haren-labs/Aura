"""Aura su Telegram: inoltra i tuoi messaggi al server di Aura (/chat) e ti manda le risposte.

Avvio:  python aura_telegram.py   (oppure lo avvia avvia_aura.bat, se e' configurato)
Serve che il server di Aura (aura_server.py) sia acceso. Istruzioni nel README, sezione "Telegram".
"""
import os
import json
import time
import base64
import requests

CARTELLA = os.path.dirname(os.path.abspath(__file__))
FILE_CONFIG = os.path.join(CARTELLA, "aura_telegram_config.json")
TELEGRAM_API = "https://api.telegram.org"
MAX_LUNGHEZZA = 4000   # Telegram accetta al massimo 4096 caratteri per messaggio

# ---------------------------------------------------------------- configurazione
CONFIG_VUOTA = {
    "token": "INCOLLA_QUI_IL_TOKEN_DI_BOTFATHER",
    "id_autorizzato": 0,
    "aura_api": "http://127.0.0.1:8888",
    "risposta_vocale": True
}

def carica_config():
    """Legge la configurazione. Se il file non esiste, lo crea vuoto e si ferma."""
    if not os.path.exists(FILE_CONFIG):
        with open(FILE_CONFIG, "w", encoding="utf-8") as f:
            json.dump(CONFIG_VUOTA, f, indent=2)
        print(f"Ho creato {FILE_CONFIG}")
        print("Aprilo con il Blocco note, incolla il token di BotFather al posto del testo e salva.")
        return None
    with open(FILE_CONFIG, "r", encoding="utf-8") as f:
        config = json.load(f)
    config["token"] = str(config.get("token", "")).strip()
    if not config["token"] or "INCOLLA" in config["token"]:
        print(f"Manca il token in {FILE_CONFIG}: incollalo e riavvia.")
        return None
    return config

# ---------------------------------------------------------------- Telegram
def telegram(config, metodo, **dati):
    """Chiama un metodo delle API di Telegram (es. sendMessage) e restituisce la risposta."""
    url = f"{TELEGRAM_API}/bot{config['token']}/{metodo}"
    file = dati.pop("_file", None)
    timeout = dati.pop("_timeout", 30)
    r = requests.post(url, data=dati, files=file, timeout=timeout)
    return r.json()

def manda_testo(config, chat_id, testo):
    """Manda un messaggio, spezzandolo se e' troppo lungo per Telegram."""
    testo = testo or "(risposta vuota)"
    for i in range(0, len(testo), MAX_LUNGHEZZA):
        telegram(config, "sendMessage", chat_id=chat_id, text=testo[i:i + MAX_LUNGHEZZA])

def manda_vocale(config, chat_id, audio_mp3):
    """Manda la voce di Aura come messaggio vocale."""
    esito = telegram(config, "sendVoice", chat_id=chat_id,
                     _file={"voice": ("aura.mp3", audio_mp3, "audio/mpeg")}, _timeout=60)
    if not esito.get("ok"):
        # alcuni client non accettano l'MP3 come "vocale": lo mando come file audio
        telegram(config, "sendAudio", chat_id=chat_id,
                 _file={"audio": ("aura.mp3", audio_mp3, "audio/mpeg")}, _timeout=60)

def scarica_file_telegram(config, file_id):
    """Scarica da Telegram un file ricevuto (es. un vocale) e restituisce i suoi byte."""
    info = telegram(config, "getFile", file_id=file_id)
    percorso = info["result"]["file_path"]
    r = requests.get(f"{TELEGRAM_API}/file/bot{config['token']}/{percorso}", timeout=60)
    r.raise_for_status()
    return r.content

def manda_immagine(config, chat_id, img_b64):
    immagine = base64.b64decode(img_b64)
    telegram(config, "sendPhoto", chat_id=chat_id, _file={"photo": ("aura.png", immagine)}, _timeout=60)

# ---------------------------------------------------------------- Aura
def chiedi_ad_aura(config, testo):
    """Manda il testo a /chat e restituisce la risposta di Aura (testo e immagine)."""
    r = requests.post(f"{config['aura_api']}/chat", json={"testo": testo}, timeout=300)
    return r.json()

def guarda_foto(config, foto, domanda):
    """Manda una foto a /vision con la domanda e restituisce la risposta di Aura."""
    r = requests.post(f"{config['aura_api']}/vision", json={
        "domanda": domanda,
        "immagine": base64.b64encode(foto).decode("utf-8")
    }, timeout=300)
    return r.json()

def trascrivi(config, audio, nome_file):
    """Manda un audio a /transcribe e restituisce il testo (o None)."""
    r = requests.post(f"{config['aura_api']}/transcribe",
                      files={"audio": (nome_file, audio)}, timeout=300)
    dati = r.json()
    return dati.get("testo") if dati.get("ok") else None

def voce_di_aura(config, testo):
    """Chiede a /speak la voce di Aura per questo testo e restituisce l'MP3 (o None)."""
    r = requests.post(f"{config['aura_api']}/speak", json={"testo": testo}, timeout=300)
    if r.headers.get("content-type", "").startswith("audio"):
        return r.content
    return None

# ---------------------------------------------------------------- messaggi
id_gia_avvisati = set()

def gestisci_messaggio(config, messaggio):
    chat_id = messaggio["chat"]["id"]
    mittente = messaggio.get("from", {}).get("id")
    testo = (messaggio.get("text") or "").strip()

    # 1) ID non ancora configurato: dico a chi scrive il suo ID, e basta
    if not config.get("id_autorizzato"):
        if mittente not in id_gia_avvisati:
            id_gia_avvisati.add(mittente)
            manda_testo(config, chat_id,
                        f"Il tuo ID Telegram e' {mittente}.\n"
                        "Copialo in aura_telegram_config.json alla voce \"id_autorizzato\" "
                        "e riavvia il bot per attivarmi.")
            print(f"ID richiesto da {mittente} (bot non ancora attivato)")
        return

    # 2) Filtro di sicurezza: rispondo solo al proprietario del bot
    if str(mittente) != str(config["id_autorizzato"]).strip():
        print(f"Messaggio ignorato da un ID non autorizzato: {mittente}")
        return

    # Vocale (o file audio): lo scarico, lo faccio trascrivere da Aura e ti mostro cosa ha capito
    audio = messaggio.get("voice") or messaggio.get("audio")
    era_vocale = False
    if audio and not testo:
        telegram(config, "sendChatAction", chat_id=chat_id, action="typing")
        try:
            contenuto = scarica_file_telegram(config, audio["file_id"])
            testo = (trascrivi(config, contenuto, "vocale.ogg") or "").strip()
        except Exception as e:
            print(f"ERRORE vocale: {e}")
            manda_testo(config, chat_id, "Non sono riuscita ad ascoltare il vocale: il server sul PC e' acceso?")
            return
        if not testo:
            manda_testo(config, chat_id, "Non ho capito il vocale, puoi ripetere?")
            return
        manda_testo(config, chat_id, f"🎤 Ho capito: {testo}")
        era_vocale = True

    # Foto (o immagine mandata come file): la faccio guardare ad Aura con /vision
    foto_id = None
    if messaggio.get("photo"):
        foto_id = messaggio["photo"][-1]["file_id"]   # l'ultima e' quella a risoluzione piu' alta
    elif str(messaggio.get("document", {}).get("mime_type", "")).startswith("image/"):
        foto_id = messaggio["document"]["file_id"]
    if foto_id:
        domanda = (messaggio.get("caption") or "").strip() or "Cosa vedi in questa foto? Descrivila."
        print(f"Telegram -> Aura (foto): {domanda[:60]}")
        telegram(config, "sendChatAction", chat_id=chat_id, action="typing")
        try:
            foto = scarica_file_telegram(config, foto_id)
            risposta = guarda_foto(config, foto, domanda)
        except Exception as e:
            print(f"ERRORE foto: {e}")
            manda_testo(config, chat_id, "Non sono riuscita a guardare la foto: il server sul PC e' acceso?")
            return
        if not risposta.get("ok"):
            manda_testo(config, chat_id, f"Non ho potuto guardare la foto: {risposta.get('motivo', 'errore sconosciuto')}")
            return
        manda_testo(config, chat_id, risposta.get("risposta", ""))
        return

    if not testo:
        manda_testo(config, chat_id, "Capisco messaggi scritti, vocali e foto: questo tipo di messaggio ancora no.")
        return
    if testo == "/start":
        manda_testo(config, chat_id, "Ciao! Sono Aura. Scrivimi pure.")
        return

    # 3) Messaggio valido: lo giro ad Aura
    print(f"Telegram -> Aura: {testo[:60]}")
    telegram(config, "sendChatAction", chat_id=chat_id, action="typing")
    try:
        risposta = chiedi_ad_aura(config, testo)
    except Exception as e:
        print(f"ERRORE: Aura non raggiungibile ({e})")
        manda_testo(config, chat_id, "Non riesco a raggiungere Aura: il server sul PC e' acceso?")
        return
    if not risposta.get("ok"):
        manda_testo(config, chat_id, f"Aura non ha potuto rispondere: {risposta.get('motivo', 'errore sconosciuto')}")
        return
    testo_risposta = risposta.get("risposta", "")
    manda_testo(config, chat_id, testo_risposta)
    if risposta.get("immagine"):
        manda_immagine(config, chat_id, risposta["immagine"])

    # Ti ho scritto con la voce? Allora ti rispondo anche con la voce
    if era_vocale and config.get("risposta_vocale", True) and testo_risposta and not risposta.get("immagine"):
        telegram(config, "sendChatAction", chat_id=chat_id, action="record_voice")
        try:
            mp3 = voce_di_aura(config, testo_risposta)
            if mp3:
                manda_vocale(config, chat_id, mp3)
        except Exception as e:
            print(f"ERRORE voce: {e}")

# ---------------------------------------------------------------- ciclo principale
def main():
    config = carica_config()
    if not config:
        input("Premi Invio per chiudere...")
        return
    controllo = telegram(config, "getMe")
    if not controllo.get("ok"):
        print("Telegram non accetta il token: controlla di averlo copiato tutto, senza spazi.")
        input("Premi Invio per chiudere...")
        return
    print(f"Bot @{controllo['result']['username']} collegato a Telegram.")
    if config.get("id_autorizzato"):
        print(f"Rispondo solo all'ID {config['id_autorizzato']}.")
    else:
        print("ID non ancora configurato: scrivi al bot per scoprire il tuo.")

    offset = None
    while True:
        try:
            # "Long polling": chiedo a Telegram i messaggi nuovi e aspetto fino a 30 secondi
            dati = {"timeout": 30, "_timeout": 40}
            if offset:
                dati["offset"] = offset
            aggiornamenti = telegram(config, "getUpdates", **dati)
            for agg in aggiornamenti.get("result", []):
                offset = agg["update_id"] + 1
                if "message" in agg:
                    gestisci_messaggio(config, agg["message"])
        except KeyboardInterrupt:
            print("Bot fermato.")
            break
        except Exception as e:
            print(f"Errore di rete ({e}), riprovo tra 5 secondi...")
            time.sleep(5)

if __name__ == "__main__":
    main()
