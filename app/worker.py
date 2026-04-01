import time
import pandas as pd
import requests
import os

from slskd_client import (
    search,
    get_search_responses,
    list_downloads,
    enqueue_download,
    browse_user
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


def find_real_file_path(username, raw_filename):
    """Caut în browse filePath REAL (case‑sensitive, exact)."""
    browse = browse_user(username)

    if not isinstance(browse, dict):
        return None

    files = browse.get("files", [])
    target = os.path.basename(raw_filename).lower()

    for f in files:
        base = os.path.basename(f.get("filename", "")).lower()
        if base == target:
            return f.get("filePath")  # EXACT AȘA! NU MODIFICI NIMIC

    return None


def search_for_good_file(query):
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
            log("[FULL DEBUG ITEM] " + str(item))
            user = item.get("username")
            files = item.get("files", [])

            for f in files:
                filename = f.get("filename", "")
                bitrate  = f.get("bitRate", 0)
                size     = f.get("size", 0)

                # detect extension only from filename
                is_mp3  = filename.lower().endswith(".mp3")
                is_flac = filename.lower().endswith(".flac")

                if filename.startswith("#") or "." not in filename:
                    continue

                # FILTRARE
                if is_flac or (is_mp3 and (bitrate >= 320 or size >= 6000000)):
                    # găsim filePath REAL
                    real_path = find_real_file_path(user, filename)
                    if real_path:
                        log(f"[FOUND] {filename} (path real: {real_path})")
                        return user, real_path
                    else:
                        log(f"[WARN] Nu găsesc filePath real pentru {filename}")

    log(f"[TIMEOUT] Nimic acceptabil pentru '{query}' în 90 sec.")
    return None


def download_until_complete(username, filepath, query):
    log(f"[DOWNLOAD] Inițiez descărcarea → {filepath}")
    enqueue_download(username, filepath)

    while True:
        completed = get_completed_filenames()
        if any(query.lower() in x.lower() for x in completed):
            log(f"[COMPLETE] Descărcat: {query}")
            return True
        time.sleep(5)


while True:
    df = load_df()

    if df.empty:
        log("[WORKER] Lista goală. Reverific în 60 sec.")
        time.sleep(60)
        continue

    for _, row in df.iterrows():
        query = row["query"]
        entry_id = row["id"]

        log("\n====================")
        log(f" Procesare: {query}")
        log("====================")

        completed = get_completed_filenames()
        if any(query.lower() in x.lower() for x in completed):
            log(f"[SKIP] '{query}' deja descărcat — șterg.")
            df = df[df["id"] != entry_id]
            save_df(df)
            continue

        result = search_for_good_file(query)

        if not result:
            log("[NEXT] Trec la următorul.")
            continue

        username, filepath = result
        if download_until_complete(username, filepath, query):
            df = df[df["id"] != entry_id]
            save_df(df)

    pause = get_cycle_pause()
    log(f"[LOOP] Finalizat. Revin în {pause//60} minute.\n")
    time.sleep(pause)