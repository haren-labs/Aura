"""Ricerca sul web con DuckDuckGo (e, se configurata, ricerca di offerte di lavoro)."""
from config import PAROLE_WEB_EXTRA, RICERCHE_LAVORO
try:
    from ddgs import DDGS
except ImportError:  # vecchio nome del pacchetto
    from duckduckgo_search import DDGS

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

def risultati_web(query, quanti):
    """Cerca su DuckDuckGo e restituisce una lista ordinata di risultati."""
    with DDGS() as ddgs:
        trovati = list(ddgs.text(query, max_results=quanti))
    return [{"titolo": r.get("title", ""), "testo": r.get("body", ""), "link": r.get("href", "")}
            for r in trovati]

def ha_bisogno_web(testo):
    parole_chiave = [
        "cerca", "trovami", "notizie", "news", "aggiornami",
        "ultimo prezzo", "quotazione", "cosa dicono", "recente",
        "attuale", "corrente", "2025", "2026",
        "quanto vale", "prezzo di"
    ]
    parole_chiave += PAROLE_WEB_EXTRA
    return any(p in testo.lower() for p in parole_chiave)

PAROLE_LAVORO = [
    "lavoro ai", "lavoro nell'ai", "cerca lavoro", "offerte lavoro",
    "posizioni ai", "trova posizioni", "opportunità ai", "job ai",
    "prompt engineer", "ai specialist", "carriera ai", "trovami lavoro"
]

def ha_bisogno_lavoro(testo):
    """True se il messaggio chiede offerte di lavoro (solo se RICERCHE_LAVORO e' configurato)."""
    return bool(RICERCHE_LAVORO) and any(p in testo.lower() for p in PAROLE_LAVORO)

def cerca_lavoro():
    """Esegue le ricerche di RICERCHE_LAVORO e restituisce {gruppo: [risultati]}."""
    return {nome: risultati_web(q, n) for nome, (q, n) in RICERCHE_LAVORO.items()}

def cerca_lavoro_testo():
    """Come cerca_lavoro(), ma come testo da aggiungere al messaggio per il modello."""
    try:
        print("Agente lavoro attivato...")
        testo = ""
        for nome, risultati in cerca_lavoro().items():
            if risultati:
                testo += f"\n[POSIZIONI {nome.upper()}]:\n"
                for r in risultati:
                    testo += f"- {r['titolo']}: {r['testo'][:150]}\n"
        return testo
    except Exception as e:
        print(f"Errore agente lavoro: {e}")
        return ""
