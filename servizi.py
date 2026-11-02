"""Controllo dei servizi (LM Studio, ComfyUI, voce), RAM e GPU: i pallini della dashboard."""
import time
import socket
import subprocess
from urllib.parse import urlparse
import psutil
import requests
from config import LM_STUDIO_URL, COMFYUI_URL, TTS_URL
from stato import stato

def get_system_stats(scambi):
    """Aggiorna RAM e numero di scambi nello stato (la dashboard lo legge ogni secondo)."""
    ram = psutil.virtual_memory()
    stato["ram_usata"] = f"{ram.used / 1024**3:.1f}"
    stato["ram_totale"] = f"{ram.total / 1024**3:.1f}"
    stato["scambi"] = scambi

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
        u = urlparse(url)
        with socket.create_connection((u.hostname, u.port or 80), timeout=2):
            return True
    except Exception:
        return False

AVVIO_SERVER = time.time()
GRAZIA_AVVIO = 90   # secondi: subito dopo l'avvio un servizio che non risponde e' "in avvio", non "offline"

def _esito(risponde):
    if risponde:
        return "ok"
    return "avvio" if time.time() - AVVIO_SERVER < GRAZIA_AVVIO else "off"

def controlla_servizi_loop():
    """Controlla ogni 3 secondi se LM Studio, ComfyUI e la voce (Edge TTS) rispondono davvero."""
    lm_base = LM_STUDIO_URL.split("/v1/")[0]
    while True:
        stato["servizi"] = {
            "lm": _esito(_http_ok(lm_base + "/v1/models")),
            "comfy": _esito(_http_ok(COMFYUI_URL + "/system_stats")),
            "tts": _esito(_porta_aperta(TTS_URL)),
        }
        time.sleep(3)
