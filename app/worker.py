import time
import pandas as pd
from slskd_client import (
    search,
    get_search_responses,
    list_downloads,
    enqueue_download
)

CSV_PATH = "wanted.csv"

# 90 secunde polling per query
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


def get_completed_filenames():
    data = list_downloads()

    # slskd v0 poate întoarce listă SAU dict
    if isinstance(data, list):
        items = data
    else:
        items = data.get("items", [])

    completed = {
        item.get("fileName", "")
        for item in items
        if item.get("state") == "Completed"
    }
    return completed


def search_for_mp3_320(query):
    log(f"[SEARCH] Pornesc căutare pentru: {query}")

    s = search(query)
    search_id = s.get("id")

    if not search_id:
        log(f"[ERROR] Search ID invalid pentru '{query}'")
        return None

    log(f"[SEARCH] ID: {search_id}")

    # Poll 90 sec
    for sec in range(POLLING_SECONDS):
        time.sleep(1)

        responses = get_search_responses(search_id)
        results = responses.get("items", [])

        if not results:
            if sec % 5 == 0:
                log(f"[SEARCH] ({sec+1}/{POLLING_SECONDS}) fără rezultate încă…")
            continue

        log(f"[SEARCH] {len(results)} rezultate pentru '{query}'")

        # Filtrăm doar MP3 320
        for item in results:
            f = item.get("file", {})
            ext = f.get("extension", "").lower()
            br = f.get("bitRate", 0)

            if ext == "mp3" and br == 320:
                log(f"[FOUND] MP3 320kbps → {f.get('filePath')}")
                return item["username"], f["filePath"]

        log("[SEARCH] Rezultate, dar fără MP3 320…")

    log(f"[SEARCH] Timeout 90s fără MP3 320 pentru '{query}'")
    return None


def download_until_complete(username, filepath, query):
    log(f"[DOWNLOAD] Pornesc descărcarea pentru '{query}'")
    enqueue_download(username, filepath)

    while True:
        completed = get_completed_filenames()
        if any(query.lower() in x.lower() for x in completed):
            log(f"[COMPLETE] Descărcare finalizată: {query}")
            return True
        time.sleep(5)


while True:
    df = load_df()

    if df.empty:
        log("[WORKER] Lista este goală. Re-verific în 60 sec.")
        time.sleep(60)
        continue

    for idx, row in df.iterrows():
        query = row["query"]
        entry_id = row["id"]

        log("\n====================")
        log(f"   Procesare: {query}")
        log("====================")

        # Verificăm dacă deja este descărcat
        completed = get_completed_filenames()
        if any(query.lower() in x.lower() for x in completed):
            log(f"[SKIP] '{query}' este deja descărcat — șterg din listă.")
            df = df[df["id"] != entry_id]
            save_df(df)
            continue

        # Căutare + polling 90 sec
        result = search_for_mp3_320(query)

        if not result:
            log(f"[NEXT] Nu am găsit MP3 320 pentru '{query}'. Trec la următorul.")
            continue

        username, filepath = result

        # Descărcăm până la completare
        if download_until_complete(username, filepath, query):
            df = df[df["id"] != entry_id]
            save_df(df)

    log("[LOOP] Runda completă terminată. Revin în 2 minute.\n")
    time.sleep(120)