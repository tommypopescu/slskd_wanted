import time
import pandas as pd
from slskd_client import (
    search,
    get_search_responses,
    list_downloads,
    enqueue_download
)

CSV_PATH = "wanted.csv"

# 15 minute între reîncercări dacă nu s-a găsit 320
SEARCH_REPEAT_INTERVAL = 15 * 60

# cât timp pollăm pentru rezultate după ce am pornit search
POLLING_SECONDS = 30


def log(msg):
    """Log out cu flush pentru a apărea în docker logs instant."""
    print(msg, flush=True)


def load_df():
    try:
        df = pd.read_csv(CSV_PATH)
        return df
    except:
        return pd.DataFrame(columns=["id", "query"])


def save_df(df):
    df.to_csv(CSV_PATH, index=False)


def get_completed_filenames():
    """Returnează numele fișierelor complet descărcate."""
    data = list_downloads()
    items = data.get("items", [])
    completed = {
        item.get("fileName", "")
        for item in items
        if item.get("state") == "Completed"
    }
    return completed


def poll_search_for_mp3_320(query):
    """
    Pornește căutarea și poll-ează timp de 30 secunde
    până când apare un rezultat MP3 320kbps.
    """
    log(f"[SEARCH] Pornesc căutare pentru: {query}")

    s = search(query)
    search_id = s.get("id")

    if not search_id:
        log(f"[ERROR] Search ID invalid pentru '{query}'.")
        return None

    log(f"[SEARCH] ID căutare: {search_id}")

    # POLLING REZULTATE
    for sec in range(POLLING_SECONDS):
        time.sleep(1)

        responses = get_search_responses(search_id)
        results = responses.get("items", [])

        if not results:
            log(f"[SEARCH] ({sec+1}/{POLLING_SECONDS}) fără rezultate încă…")
            continue

        log(f"[SEARCH] Am primit {len(results)} rezultate pentru '{query}'")

        # Căutăm MP3 320
        for item in results:
            f = item.get("file", {})
            ext = f.get("extension", "").lower()
            br = f.get("bitRate", 0)

            if ext == "mp3" and br == 320:
                log(f"[FOUND] MP3 320kbps → {f.get('filePath')}")
                return item["username"], f["filePath"]

        log("[SEARCH] Rezultate gasite, dar niciun MP3 320kbps.")

    log(f"[SEARCH] Timpul de 30s s-a terminat fără MP3 320 pentru '{query}'.")
    return None


def download_until_complete(username, filepath, query):
    """Inițiază descărcarea și monitorizează până este completă."""
    log(f"[DOWNLOAD] Pornesc descărcarea: {query} → {filepath}")
    enqueue_download(username, filepath)

    # Poll pentru finalizare
    while True:
        completed = get_completed_filenames()
        if any(query.lower() in x.lower() for x in completed):
            log(f"[COMPLETE] Descărcare completă pentru '{query}'")
            return True
        time.sleep(5)


while True:
    df = load_df()

    if df.empty:
        log("[WORKER] Lista goală. Re-verific peste 1 minut.")
        time.sleep(60)
        continue

    for idx, row in df.iterrows():
        query = row["query"]
        entry_id = row["id"]

        log(f"\n====================")
        log(f"   Procesare: {query}")
        log(f"====================")

        # 1. Verificăm dacă e deja descărcată
        completed = get_completed_filenames()
        if any(query.lower() in x.lower() for x in completed):
            log(f"[SKIP] '{query}' deja descărcat. Îl șterg din listă.")
            df = df[df["id"] != entry_id]
            save_df(df)
            continue

        # 2. Pornim căutarea + polling rezultate
        result = poll_search_for_mp3_320(query)

        if not result:
            log(f"[WAIT] '{query}' nu a fost găsit în 320. Reîncerc peste 15 minute.")
            time.sleep(SEARCH_REPEAT_INTERVAL)
            continue

        username, filepath = result

        # 3. Descărcăm până la finalizare
        ok = download_until_complete(username, filepath, query)

        # 4. Ștergem din CSV
        if ok:
            df = df[df["id"] != entry_id]
            save_df(df)

    log("[LOOP] Runda completă. Revin în 60 secunde.\n")
    time.sleep(60)