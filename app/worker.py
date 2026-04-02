import time
import pandas as pd
from datetime import datetime, timedelta

from slskd_client import (
    search,
    get_search_responses,
    list_downloads,
    enqueue_download,
)

CSV_PATH = "wanted.csv"
POLLING_SECONDS = 90
COOLDOWN_MINUTES = 30


# -------------------------------------------------
# Utils
# -------------------------------------------------

def log(msg: str):
    print(msg, flush=True)


def load_df():
    try:
        df = pd.read_csv(CSV_PATH, dtype=str)
    except:
        df = pd.DataFrame(
            columns=["id", "query", "status", "last_message", "last_attempt"]
        )
    return df.fillna("")


def save_df(df):
    df.to_csv(CSV_PATH, index=False)


def update_status(entry_id: str, status: str, message: str):
    df = load_df()
    df.loc[df["id"] == entry_id, "status"] = status
    df.loc[df["id"] == entry_id, "last_message"] = message
    df.loc[df["id"] == entry_id, "last_attempt"] = datetime.utcnow().isoformat()
    save_df(df)


def normalize_search(data):
    if isinstance(data, dict):
        return data.get("items", [])
    if isinstance(data, list):
        return data
    return []


def normalize_downloads(data):
    if isinstance(data, dict):
        return data.get("items", [])
    if isinstance(data, list):
        return data
    return []


# -------------------------------------------------
# Search phase
# -------------------------------------------------

def find_candidates(query: str):
    log(f"[SEARCH] Pornesc căutare pentru: {query}")

    s = search(query)
    search_id = s.get("id")
    if not search_id:
        return []

    log(f"[SEARCH] ID: {search_id}")
    candidates = []

    for sec in range(POLLING_SECONDS):
        time.sleep(1)
        results = normalize_search(get_search_responses(search_id))

        if not results:
            continue

        log(f"[SEARCH] {len(results)} rezultate pentru '{query}'")

        for item in results:
            if not item.get("hasFreeUploadSlot"):
                continue
            if item.get("queueLength", -1) != 0:
                continue

            username = item.get("username")

            for f in item.get("files", []):
                filename = f.get("filename")
                if not filename or filename.startswith("#"):
                    continue

                bitrate = f.get("bitRate", 0)
                size = f.get("size", 0)

                is_mp3 = filename.lower().endswith(".mp3")
                is_flac = filename.lower().endswith(".flac")

                if (
                    is_flac
                    or (is_mp3 and bitrate >= 320)
                    or (is_mp3 and bitrate == 0 and size >= 6_000_000)
                ):
                    candidates.append((username, filename))

        if candidates:
            break

    return candidates


# -------------------------------------------------
# Download phase
# -------------------------------------------------

def try_download(entry_id: str, username: str, file_path: str, query: str) -> bool:
    """
    Încearcă download pentru un singur candidat.
    Returnează True dacă s-a descărcat complet.
    False în caz de refuz / waiting.
    """
    log(f"[DOWNLOAD] {username} → {file_path}")

    resp = enqueue_download(username, file_path)
    log(f"[DOWNLOAD RESPONSE] {resp}")

    status = resp.get("status", 0)
    if not (200 <= status < 300):
        update_status(entry_id, "error", "Eroare API slskd")
        return False

    update_status(entry_id, "queued", "Găsit și pus în coada locală")

    start_time = time.time()
    timeout = 90  # secunde

    while time.time() - start_time < timeout:
        downloads = normalize_downloads(list_downloads())

        for d in downloads:
            dname = d.get("filename")
            if not dname:
                continue

            if file_path.endswith(dname):
                state = d.get("state", "")

                if state == "Completed":
                    update_status(entry_id, "downloaded", "Descărcare finalizată")
                    return True

                if state in ("Failed", "Cancelled"):
                    update_status(entry_id, "waiting", "Remote a refuzat (File not shared)")
                    return False

        time.sleep(5)

    update_status(entry_id, "waiting", "Așteaptă disponibilitatea remote")
    return False


# -------------------------------------------------
# Main loop
# -------------------------------------------------

while True:
    df = load_df()
    now = datetime.utcnow()

    if df.empty:
        log("[WORKER] Lista goală")
        time.sleep(60)
        continue

    for _, row in df.iterrows():
        entry_id = row["id"]
        query = row["query"]
        status = row["status"]
        last_attempt = row["last_attempt"]

        if status == "downloaded":
            continue

        if status == "waiting" and last_attempt:
            last = datetime.fromisoformat(last_attempt)
            if now - last < timedelta(minutes=COOLDOWN_MINUTES):
                continue

        log(f"\n=== Procesare: {query} ===")

        candidates = find_candidates(query)
        if not candidates:
            continue

        for username, path in candidates:
            completed = try_download(entry_id, username, path, query)
            if completed:
                break

    log("[WORKER] Pauză 5 minute")
    time.sleep(300)