"""Visione: foto dalla webcam."""
import base64
import cv2
from config import WEBCAM_INDEX

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
