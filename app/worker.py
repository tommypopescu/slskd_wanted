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


# ================= CONFIG =================

def get_cycle_pause():
    try:
        cfg = requests.get(f"{API_BASE}/config").json()
        return int(cfg.get("cycle_pause_minutes", 30)) * 60
    except:
        return 1800   # 30 min fallback


# ================= CSV =================

def load_df():
    try:
        return pd.read_csv(CSV_PATH)
    except:
        return pd.DataFrame(columns=["id", "query"])


def save_df(df):
    df.to_csv(CSV_PATH, index=False)


# ================= DOWNLOAD STATE =================

def normalize_downloads_response(data):
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("items", [])
    return []


def get_active_downloads():
    return normalize_downloads_response(list_downloads())


# ================= SEARCH =================

def normalize_search_response(data):
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("items", [])
    return []


def find_candidates(query):
    """
    Returnează LISTĂ de candidați valizi:
    (username, filePath)
    """
    log(f"[SEARCH] Pornesc căutare pentru: {query}")

    s = search(query)
    search_id = s.get("id")

    if not search_id:
        log("[ERROR] Search ID invalid")
        return []

    log(f"[SEARCH] ID: {search_id}")

    candidates = []

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
            if not item.get("hasFreeUploadSlot", False):
                continue
            if item.get("queueLength", -1) != 0:
                continue

            for f in item.get("files", []):
                filename = f.get("filename")
                bitrate = f.get("bitRate", 0)
                size = f.get("size", 0)

                if not filename or filename.startswith("#"):
                    continue

                is_mp3 = filename.lower().endswith(".mp3")
                is_flac = filename.lower().endswith(".flac")

                # criterii calitate
                if (
                    is_flac
                    or (is_mp3 and bitrate >= 320)
                    or (is_mp3 and bitrate == 0 and size >= 6_000_000)
                ):
                    candidates.append((username, filename))

        if candidates:
            break

    return candidates


# ================= DOWNLOAD =================

def try_download(username, filePath, query):
    log(f"[DOWNLOAD] Încerc descărcarea → {filePath}")

    resp = enqueue_download(username, filePath)
    log(f"[DOWNLOAD RESPONSE] {resp}")

    status = resp.get("status", 0)
    if not (200 <= status < 300):
        return False

    # monitorizăm progresul
    start = time.time()
    timeout = 90

    while time.time() - start < timeout:
        for d in get_active_downloads():
            if (
                d.get("filename", "").lower() == query.lower()
                and d.get("direction") == "Download"
            ):
                state = d.get("state", "")
                if state == "Completed":
                    log(f"[COMPLETE] Descărcat: {query}")
                    return True
                if state in ("Failed", "Cancelled"):
                    return False
        time.sleep(5)

    # dacă nu a pornit (File not shared)
    log("[INFO] Transfer refuzat de remote (File not shared)")
    return False


# ================= MAIN LOOP =================

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

        candidates = find_candidates(query)

        if not candidates:
            log("[INFO] Niciun candidat eligibil acum.")
            continue

        success = False
        for username, path in candidates:
            if try_download(username, path, query):
                success = True
                break

        if success:
            df = df[df["id"] != entry_id]
            save_df(df)
        else:
            log("[INFO] Toți candidații au returnat 'File not shared'.")

    pause = get_cycle_pause()
    log(f"[LOOP] Revin în {pause//60} minute\n")
    time.sleep(pause)