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
API_BASE = "http://127.0.0.1:8000"  # API-ul rulează în același container


def log(msg):
    print(msg, flush=True)


# ---------------- CONFIG ----------------

def get_cycle_pause():
    """Citește pauza dintre cicluri direct din API /config."""
    try:
        cfg = requests.get(f"{API_BASE}/config").json()
        minutes = int(cfg.get("cycle_pause_minutes", 30))
        return minutes * 60
    except:
        return 1800  # fallback 30 minute


# ---------------- CSV OPERATIONS ----------------

def load_df():
    try:
        return pd.read_csv(CSV_PATH)
    except:
        return pd.DataFrame(columns=["id", "query"])


def save_df(df):
    df.to_csv(CSV_PATH, index=False)


# ---------------- NORMALIZARE RĂSPUNSURI ----------------

def normalize_downloads_response(data):
    """slskd poate întoarce listă sau dict cu 'items'."""
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
    """slskd v0 poate întoarce listă SAU dict {items:[]}"""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("items", [])
    return []


# ---------------- SEARCH + FILTRARE ----------------

def search_for_good_file(query):
    """
    Găsește MP3 320kbps / FLAC / MP3 > 6MB din structura reală
    (items[].files[]), conform debug-ului real furnizat.
    """

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

        # ITERĂM REZULTATELE REALE (user → files[])
        for item in results:
            user = item.get("username")
            files = item.get("files", [])

            for f in files:
                filename = f.get("filename", "").lower()
                bitrate  = f.get("bitRate", 0)
                size     = f.get("size", 0)

                # Detectăm extensia REALĂ din filename
                is_mp3  = filename.endswith(".mp3")
                is_flac = filename.endswith(".flac")

                # -- IGNORĂ PATH-URI INVALIDATE --
                if filename.startswith("#"):
                    continue
                if "." not in filename:
                    continue

                # -- FILTRARE FINALĂ --

                # 1) FLAC — acceptat instant
                if is_flac:
                    filePath = filename.replace("\\", "\\\\")
                    log(f"[FOUND] FLAC → {filePath}")
                    return user, filePath

                # 2) MP3 320kbps confirmat
                if is_mp3 and bitrate >= 320:
                    filePath = filename.replace("\\", "\\\\")
                    log(f"[FOUND] MP3 320kbps → {filePath}")
                    return user, filePath

                # 3) MP3 > 6MB (în 99% cazuri = 320kbps)
                if is_mp3 and bitrate == 0 and size >= 6_000_000:
                    filePath = filename.replace("\\", "\\\\")
                    log(f"[FOUND] MP3 probabil 320kbps (size={size}) → {filePath}")
                    return user, filePath

        log("[SEARCH] Rezultate, dar niciun fișier valid în acest batch.")

    log(f"[TIMEOUT] Nu am găsit fișier acceptat pentru '{query}' în 90 sec.")
    return None


# ---------------- DOWNLOAD ----------------

def download_until_complete(username, filepath, query):
    log(f"[DOWNLOAD] Pornesc descărcarea pentru '{query}' → {filepath}")
    enqueue_download(username, filepath)

    while True:
        completed = get_completed_filenames()
        if any(query.lower() in x.lower() for x in completed):
            log(f"[COMPLETE] Descărcare finalizată: {query}")
            return True
        time.sleep(5)


# ---------------- MAIN LOOP ----------------

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
            log(f"[SKIP] '{query}' deja descărcat — șterg din listă.")
            df = df[df["id"] != entry_id]
            save_df(df)
            continue

        result = search_for_good_file(query)

        if not result:
            log("[NEXT] Trec la următoarea melodie.")
            continue

        username, filepath = result

        if download_until_complete(username, filepath, query):
            df = df[df["id"] != entry_id]
            save_df(df)

    pause = get_cycle_pause()
    log(f"[LOOP] Gata runda. Revin în {pause//60} minute.\n")
    time.sleep(pause)