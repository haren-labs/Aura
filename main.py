"""Avvio di Aura: carica i moduli, accende i controlli in background e apre le API.

Avvio:  python main.py   (oppure con avvia_aura.bat)
"""
import threading
import uvicorn

from config import HOST, PORT, PORT_DASHBOARD
from servizi import aggiorna_gpu_loop, controlla_servizi_loop
from api import app, avvia_dashboard

threading.Thread(target=avvia_dashboard, daemon=True).start()
threading.Thread(target=aggiorna_gpu_loop, daemon=True).start()
threading.Thread(target=controlla_servizi_loop, daemon=True).start()

print(f"Dashboard su porta {PORT_DASHBOARD}, API su porta {PORT}")
print(f"Pagina di prova degli endpoint: http://127.0.0.1:{PORT}/docs")
print(f"Dashboard: http://127.0.0.1:{PORT_DASHBOARD}/aura_dashboard.html")
print("Dashboard pronta!")
uvicorn.run(app, host=HOST, port=PORT, log_level="warning")
