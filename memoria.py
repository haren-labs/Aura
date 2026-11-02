"""Memoria tra le sessioni: legge e scrive aura_memoria.json."""
import os
import json
from datetime import datetime
from config import MEMORIA_FILE, MAX_RICORDI, NOME_UTENTE

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
            # "utente" e' il formato attuale; i file delle prime versioni usavano un altro nome per questo campo
            frase = r.get('utente') or next((v for k, v in r.items() if k not in ('data', 'aura')), '')
            testo += f"[{r['data']}] {NOME_UTENTE}: {frase}\n"
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
