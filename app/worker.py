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


# ================== CONFIG ==================

def get_cycle_pause():
    try:
        cfg = requests.get(f"{API_BASE}/config").json()
        return int(cfg.get("cycle_pause_minutes", 30)) * 60
    except:
        return 1800  # fallback 30 min


# ================== CSV ==================

def load_df():
    try:
        return pd.read_csv(CSV_PATH)
    except:
        return pd.DataFrame(columns=["id", "query"])


def save_df(df):
    df.to_csv(CSV_PATH, index=False)


# ================== DOWNLOAD STATE ==================

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


# ================== SEARCH ==================

def normalize_search_response(data):
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("items", [])
    return []


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

        # ===== REGULA TA FINALĂ =====
        # free slot + queueLength == 0

        for item in results:
            username = item.get("username")

            has_slot = item.get("hasFreeUploadSlot", False)
            queue_len = item.get("queueLength", -1)

            if not has_slot or queue_len != 0:
                continue  # SKIP total

            for f in item.get("files", []):
                filename = f.get("filename")
                bitrate = f.get("bitRate", 0)
                size = f.get("size", 0)

                if not filename or filename.startswith("#"):
                    continue

                is_mp3 = filename.lower().endswith(".mp3")
                is_flac = filename.lower().endswith(".flac")

                # ✅ FLAC
                if is_flac:
                    log(f"[FOUND] FLAC (slot liber, queue 0) → {filename}")
                    return username, filename

                # ✅ MP3 320 sau mare
                if is_mp3 and (bitrate >= 320 or size >= 6_000_000):
                    log(f"[FOUND] MP3 320 (slot liber, queue 0) → {filename}")
                    return username, filename

    log("[TIMEOUT] Niciun fișier valid"
        " (slot liber + queue 0 + calitate bună)")
    return None


# ================== DOWNLOAD ==================

def download_until_complete(username, filePath, query):
    log(f"[DOWNLOAD] Încerc descărcarea → {filePath}")

    resp = enqueue_download(username, filePath)
    log(f"[DOWNLOAD RESPONSE] {resp}")

    status = resp.get("status", 0)
    body = resp.get("response", "")

    # ✅ 2xx = request acceptat, chiar dacă ulterior e refuzat de remote
    if not (200 <= status < 300):
        log("[ERROR] slskd a respins cererea înainte de transfer.")
        return False

    # ✅ monitorizăm downloadul
    start_time = time.time()
    timeout = 90  # secunde

    while time.time() - start_time < timeout:
        downloads = normalize_downloads_response(list_downloads())

        for d in downloads:
            if (
                d.get("filename", "").lower() == query.lower()
                and d.get("state") not in ("Cancelled", "Failed")
            ):
                if d.get("state") == "Completed":
                    log(f"[COMPLETE] Descărcat: {query}")
                    return True

        time.sleep(5)

    log("[INFO] Transferul nu a pornit sau a fost respins de remote (File not shared).")
    return False

# ================== MAIN LOOP ==================

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