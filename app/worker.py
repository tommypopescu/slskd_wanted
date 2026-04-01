import time
import pandas as pd
from slskd_client import (
    search,
    get_search_responses,
    list_downloads,
    enqueue_download
)

CSV_PATH = "wanted.csv"

# polling 90 secunde pentru fiecare melodie
POLLING_SECONDS = 90  


def log(msg):
    print(msg, flush=True)


def load_df():
    try:
        return pd.read_csv(CSV_PATH)
    except:
        return pd.DataFrame(columns=["id", "query"])


def save_df(df):
    df.to_csv(CSV_PATH, index=False)


def normalize_downloads_response(data):
    """slskd v0 poate întoarce fie dict, fie listă."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("items", [])
    return []


def get_completed_filenames():
    data = list_downloads()
    items = normalize_downloads_response(data)

    completed = {
        item.get("fileName", "")
        for item in items
        if item.get("state") == "Completed"
    }
    return completed


def normalize_search_response(data):
    """
    slskd v0 poate întoarce:
      -> { "items": [...] }
      -> [ {...}, {...} ]
    """
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        if "items" in data and isinstance(data["items"], list):
            return data["items"]
    return []


def search_for_mp3_320(query):
    log(f"[SEARCH] Pornesc căutare pentru: {query}")

    s = search(query)
    search_id = s.get("id")

    if not search_id:
        log(f"[ERROR] Search ID invalid pentru '{query}'.")
        return None

    log(f"[SEARCH] ID: {search_id}")

    # Poll 90 secunde pentru rezultate
    for sec in range(POLLING_SECONDS):
        time.sleep(1)

        responses = get_search_responses(search_id)
        results = normalize_search_response(responses)

        if not results:
            # log o dată la 5 secunde
            if sec % 5 == 0:
                log(f"[SEARCH] ({sec+1}/{POLLING_SECONDS}) fără rezultate încă…")
            continue

        log(f"[SEARCH] {len(results)} rezultate pentru '{query}'")

        # Filtrăm după MP3 320
        for item in results:
            f = item.get("file", {})
            ext = f.get("extension", "").lower()
            br = f.get("bitRate", 0)

            if ext == "mp3" and br == 320:
                log(f"[FOUND] MP3 320kbps → {f.get('filePath')}")
                return item["username"], f["filePath"]

        log("[SEARCH] Rezultate găsite, dar fără MP3 320.")

    log(f"[TIMEOUT] Nu am găsit MP3 320 pentru '{query}' în 90 secunde.")
    return None


def download_until_complete(username, filepath, query):
    log(f"[DOWNLOAD] Pornesc descărcarea pentru '{query}'")
    enqueue_download(username, filepath)

    while True:
        completed = get_completed_filenames()
        if any(query.lower() in x.lower() for x in completed):
            log(f"[COMPLETE] Descărcare finalizată pentru '{query}'")
            return True
        time.sleep(5)


while True:
    df = load_df()

    if df.empty:
        log("[WORKER] Lista goală. Re-verific în 60 sec.")
        time.sleep(60)
        continue

    for idx, row in df.iterrows():
        query = row["query"]
        entry_id = row["id"]

        log("\n====================")
        log(f"   Procesare: {query}")
        log("====================")

        # Verificăm dacă e deja descărcat
        completed = get_completed_filenames()
        if any(query.lower() in x.lower() for x in completed):
            log(f"[SKIP] '{query}' este deja descărcat — șterg din listă.")
            df = df[df["id"] != entry_id]
            save_df(df)
            continue

        # Căutare 90s
        result = search_for_mp3_320(query)

        if not result:
            log(f"[NEXT] Trec la următoarea melodie.")
            continue

        username, filepath = result

        # Descărcăm și așteptăm finalizarea
        if download_until_complete(username, filepath, query):
            df = df[df["id"] != entry_id]
            save_df(df)

    log("[LOOP] Am terminat runda. Revin în 2 minute.")
    time.sleep(120)