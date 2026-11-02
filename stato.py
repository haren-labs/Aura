"""Lo stato di Aura condiviso tra i moduli: lo legge la dashboard (GET /) e lo aggiornano gli altri file."""
from config import MODEL

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
    "servizi": None,   # None = non ancora controllati: la dashboard aspetta il primo controllo vero
    "ultima_immagine_nome": None,
    "scambi": 0
}
