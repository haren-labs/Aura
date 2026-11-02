"""Voce di Aura: ascolto (Whisper) e parlato (Edge TTS)."""
import os
import time
import threading
import subprocess
import requests
import sounddevice as sd
import soundfile as sf
import whisper
import winsound
from config import (DEVICE_INDEX, SAMPLERATE, DURATA_SECONDI, PAUSA_FINE, WHISPER_MODEL,
                    MAX_TTS_CHARS, TTS_URL, TTS_VOICE, TTS_API_KEY, FFMPEG, CARTELLA_TEMP)
from stato import stato

print("Carico Whisper...")
whisper_model = whisper.load_model(WHISPER_MODEL)
print("Whisper pronto!")

# Whisper trascrive un audio alla volta
lucchetto_whisper = threading.Lock()

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

def trascrivi_file(percorso):
    """Trascrive un file audio gia' salvato su disco (lo usa /transcribe)."""
    with lucchetto_whisper:
        risultato = whisper_model.transcribe(percorso, language='it')
    return risultato['text'].strip()

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

def voce_mp3(testo):
    """Trasforma il testo in voce (TTS_VOICE) e restituisce l'audio MP3 (bytes), o None."""
    audio = b""
    for i, parte in enumerate(dividi_testo(testo)):
        for tentativo in range(1, 4):
            try:
                r = requests.post(TTS_URL, headers={"Authorization": f"Bearer {TTS_API_KEY}"}, json={
                    "model": "tts-1", "input": parte, "voice": TTS_VOICE
                }, timeout=120)
                if r.status_code == 200:
                    audio += r.content
                    break
                print(f"ERRORE TTS /speak (parte {i + 1}, tentativo {tentativo}/3): stato {r.status_code}")
            except Exception as e:
                print(f"ERRORE TTS /speak (parte {i + 1}, tentativo {tentativo}/3): {e}")
            time.sleep(1.5)
        else:
            return None   # una parte non e' riuscita dopo 3 tentativi
    return audio or None
