import time
import pandas as pd
import requests
import os
from slskd_client import (
    search,
    get_search_responses,
    list_downloads,
    enqueue_download
)

CSV_PATH = "wanted.csv"
POLLING_SECONDS = 90

API_BASE = "http://127.0.0.1:8000"   # worker și API sunt în același container


def log(msg):
    print(msg, flush=True)


def get_cycle_pause():
    """Citește pauza direct din API /config."""
    try:
        cfg = requests.get(f"{API_BASE}/config").json()
        minutes = int(cfg.get("cycle_pause_minutes", 30))
        return minutes * 60
    except:
        return 1800  # fallback


def load_df():
    try:
        return pd.read_csv(CSV_PATH)
    except:
        return pd.DataFrame(columns=["id", "query"])


def save_df(df):
    df.to_csv(CSV_PATH, index=False)


def normalize_downloads_response(data):
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("items", [])
    return []


def get_completed_filenames():
    data = list_downloads()
    items = normalize_downloads_response(data)
    return {
        item.get("fileName", "")
        for item in items
        if item.get("state") == "Completed"
    }


def normalize_search_response(data):
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("items", [])
    return []


def search_for_mp3_320(query):
    log(f"[SEARCH] Pornesc căutare pentru: {query}")

    s = search(query)
    search_id = s.get("id")
    if not search_id:
        log(f"[ERROR] Search ID invalid pentru '{query}'.")
        return None

    log(f"[SEARCH] ID: {search_id}")

    for sec in range(POLLING_SECONDS):
        time.sleep(1)

        responses = get_search_responses(search_id)
        results = normalize_search_response(responses)

        if not results:
            if sec % 5 == 0:
                log(f"[SEARCH] ({sec+1}/{POLLING_SECONDS}) fără rezultate încă…")
            continue

        log(f"[SEARCH] {len(results)} rezultate pentru '{query}'")

        for item in results:
            f = item.get("file", {})
            attrs = item.get("attributes", {})

            ext = f.get("extension", "").lower()
            br = attrs.get("bitRate", 0)

            if ext == "mp3" and br == 320:
                log(f"[FOUND] MP3 320kbps → {f.get('filePath')}")
                return item["username"], f["filePath"]

        log("[SEARCH] Rezultate, dar fără MP3 320.")

    log(f"[TIMEOUT] Nu am găsit MP3 320 pentru '{query}' în 90 sec.")
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
        log("[WORKER] Lista goală. Reverific în 60 sec.")
        time.sleep(60)
        continue

    for idx, row in df.iterrows():
        query = row["query"]
        entry_id = row["id"]

        log("\n====================")
        log(f"   Procesare: {query}")
        log("====================")

        completed = get_completed_filenames()
        if any(query.lower() in x.lower() for x in completed):
            log(f"[SKIP] '{query}' este deja descărcat — șterg din listă.")
            df = df[df["id"] != entry_id]
            save_df(df)
            continue

        result = search_for_mp3_320(query)

        if not result:
            log(f"[NEXT] Trec la următorul.")
            continue

        username, filepath = result

        if download_until_complete(username, filepath, query):
            df = df[df["id"] != entry_id]
            save_df(df)

    pause = get_cycle_pause()
    log(f"[LOOP] Am terminat runda. Revin în {pause//60} minute.\n")
    time.sleep(pause)