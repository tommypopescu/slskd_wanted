import time
import pandas as pd
import requests
from datetime import datetime, timedelta

from slskd_client import (
    search,
    get_search_responses,
    list_downloads,
    enqueue_download,
)

CSV_PATH = "wanted.csv"
POLLING_SECONDS = 90
API_BASE = "http://127.0.0.1:8000"
COOLDOWN_MINUTES = 30


def log(msg):
    print(msg, flush=True)


# ---------------- CSV helpers ----------------

def load_df():
    try:
        df = pd.read_csv(CSV_PATH)
    except:
        df = pd.DataFrame(columns=[
            "id", "query", "status", "last_message", "last_attempt"
        ])

    for col in ["status", "last_message", "last_attempt"]:
        if col not in df.columns:
            df[col] = ""

    return df


def save_df(df):
    df.to_csv(CSV_PATH, index=False)


def update_status(entry_id, status, message):
    df = load_df()
    df.loc[df["id"] == entry_id, "status"] = status
    df.loc[df["id"] == entry_id, "last_message"] = message
    df.loc[df["id"] == entry_id, "last_attempt"] = datetime.utcnow().isoformat()
    save_df(df)


# ---------------- slskd helpers ----------------

def normalize_search_response(data):
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("items", [])
    return []


def normalize_downloads(data):
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("items", [])
    return []


# ---------------- SEARCH ----------------

def find_candidates(query):
    log(f"[SEARCH] Pornesc căutare pentru: {query}")

    s = search(query)
    search_id = s.get("id")

    if not search_id:
        return []

    log(f"[SEARCH] ID: {search_id}")
    candidates = []

    for sec in range(POLLING_SECONDS):
        time.sleep(1)
        results = normalize_search_response(
            get_search_responses(search_id)
        )

        if not results:
            continue

        log(f"[SEARCH] {len(results)} rezultate pentru '{query}'")

        for item in results:
            if not item.get("hasFreeUploadSlot", False):
                continue
            if item.get("queueLength", -1) != 0:
                continue

            username = item.get("username")

            for f in item.get("files", []):
                filename = f.get("filename")
                bitrate = f.get("bitRate", 0)
                size = f.get("size", 0)

                if not filename or filename.startswith("#"):
                    continue

                if (
                    filename.lower().endswith(".flac")
                    or (filename.lower().endswith(".mp3") and bitrate >= 320)
                    or (filename.lower().endswith(".mp3") and size >= 6_000_000)
                ):
                    candidates.append((username, filename))

        if candidates:
            break

    return candidates


# ---------------- DOWNLOAD ----------------

def try_download(entry_id, username, filePath, query):
    log(f"[DOWNLOAD] Trimit cerere → {filePath}")

    resp = enqueue_download(username, filePath)
    log(f"[DOWNLOAD RESPONSE] {resp}")

    status = resp.get("status", 0)
    if not (200 <= status < 300):
        update_status(entry_id, "error", "Eroare API slskd")
        return False

    # enqueue a reușit
    update_status(entry_id, "queued", "Găsit și pus în coada locală")

    start = time.time()
    timeout = 90

    while time.time() - start < timeout:
        downloads = normalize_downloads(list_downloads())
        for d in downloads:
            if d.get("filename", "").lower() == query.lower():
                state = d.get("state", "")
                if state == "Completed":
                    update_status(entry_id, "downloaded", "Descărcare finalizată")
                    return True
                if state in ("Failed", "Cancelled"):
                    update_status(entry_id, "waiting", "Remote a refuzat (File not shared)")
                    return False
        time.sleep(5)

    update_status(entry_id, "waiting", "Remote a refuzat sau nu a răspuns")
    return False


# ---------------- MAIN LOOP ----------------

while True:
    df = load_df()
    if df.empty:
        log("[WORKER] Lista goală.")
        time.sleep(60)
        continue

    now = datetime.utcnow()

    for _, row in df.iterrows():
        entry_id = row["id"]
        query = row["query"]
        status = row["status"]
        last_attempt = row["last_attempt"]

        log("\n====================")
        log(f" Procesare: {query}")
        log("====================")

        if status == "downloaded":
            continue

        if status == "waiting" and last_attempt:
            last = datetime.fromisoformat(last_attempt)
            if now - last < timedelta(minutes=COOLDOWN_MINUTES):
                continue

        candidates = find_candidates(query)
        if not candidates:
            continue

        for username, path in candidates:
            if try_download(entry_id, username, path, query):
                break

    log("[LOOP] Pauză 5 minute\n")
    time.sleep(300)
