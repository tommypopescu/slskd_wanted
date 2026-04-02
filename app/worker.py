import time
import pandas as pd
import requests
from slskd_client import (
    search,
    get_search_responses,
    list_downloads,
    enqueue_download,
)

CSV_PATH = "wanted.csv"
POLLING_SECONDS = 90
API_BASE = "http://127.0.0.1:8000"


def log(msg):
    print(msg, flush=True)


def get_cycle_pause():
    try:
        cfg = requests.get(f"{API_BASE}/config").json()
        return int(cfg.get("cycle_pause_minutes", 30)) * 60
    except:
        return 1800


def load_df():
    try:
        return pd.read_csv(CSV_PATH)
    except:
        return pd.DataFrame(columns=["id", "query"])


def save_df(df):
    df.to_csv(CSV_PATH, index=False)


def normalize_search_response(data):
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("items", [])
    return []


def normalize_downloads_response(data):
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("items", [])
    return []


def get_completed_filenames():
    items = normalize_downloads_response(list_downloads())
    return {
        x.get("fileName", "")
        for x in items
        if x.get("state") == "Completed"
    }


def search_for_good_file(query):
    log(f"[SEARCH] Pornesc căutare pentru: {query}")

    s = search(query)
    search_id = s.get("id")

    if not search_id:
        log("[ERROR] Search ID invalid")
        return None

    log(f"[SEARCH] ID: {search_id}")

    for sec in range(POLLING_SECONDS):
        time.sleep(1)

        results = normalize_search_response(
            get_search_responses(search_id)
        )

        if not results:
            if sec % 5 == 0:
                log(f"[SEARCH] ({sec+1}/{POLLING_SECONDS}) fără rezultate încă…")
            continue

        log(f"[SEARCH] {len(results)} rezultate pentru '{query}'")

        for item in results:
            username = item.get("username")
            for f in item.get("files", []):
                filename = f.get("filename")
                bitrate = f.get("bitRate", 0)
                size = f.get("size", 0)

                if not filename or filename.startswith("#"):
                    continue

                is_mp3 = filename.endswith(".mp3")
                is_flac = filename.endswith(".flac")

                if is_flac or (is_mp3 and (bitrate >= 320 or size >= 6_000_000)):
                    log(f"[FOUND] → {filename}")
                    return username, filename

    log("[TIMEOUT] Nimic acceptabil")
    return None


def download_until_complete(username, filePath, query):
    log(f"[DOWNLOAD] Inițiez descărcarea → {filePath}")
    enqueue_download(username, filePath)

    while True:
        if any(query.lower() in x.lower() for x in get_completed_filenames()):
            log(f"[COMPLETE] Descărcat: {query}")
            return
        time.sleep(5)


while True:
    df = load_df()

    if df.empty:
        log("[WORKER] Lista goală.")
        time.sleep(60)
        continue

    for _, row in df.iterrows():
        query = row["query"]
        entry_id = row["id"]

        log("\n====================")
        log(f" Procesare: {query}")
        log("====================")

        if any(query.lower() in x.lower() for x in get_completed_filenames()):
            df = df[df["id"] != entry_id]
            save_df(df)
            continue

        result = search_for_good_file(query)
        if not result:
            continue

        user, path = result
        download_until_complete(user, path, query)
        df = df[df["id"] != entry_id]
        save_df(df)

    pause = get_cycle_pause()
    log(f"[LOOP] Revin în {pause//60} minute\n")
    time.sleep(pause)