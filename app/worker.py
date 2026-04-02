import time
import pandas as pd
from datetime import datetime, timedelta
from slskd_client import search, get_search_responses, list_downloads, enqueue_download

CSV_PATH = "wanted.csv"
POLLING_SECONDS = 90
COOLDOWN_MINUTES = 30

def log(msg):
    print(msg, flush=True)

def load_df():
    try:
        df = pd.read_csv(CSV_PATH, dtype=str)
    except:
        df = pd.DataFrame(columns=["id","query","status","last_message","last_attempt"])
    return df.fillna("")

def save_df(df):
    df.to_csv(CSV_PATH, index=False)

def update_status(entry_id, status, message):
    df = load_df()
    df.loc[df["id"] == entry_id, "status"] = status
    df.loc[df["id"] == entry_id, "last_message"] = message
    df.loc[df["id"] == entry_id, "last_attempt"] = datetime.utcnow().isoformat()
    save_df(df)

def normalize_search(data):
    if isinstance(data, dict):
        return data.get("items", [])
    return data if isinstance(data, list) else []

def normalize_downloads(data):
    return data.get("items", []) if isinstance(data, dict) else data

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
            if now - datetime.fromisoformat(last_attempt) < timedelta(minutes=COOLDOWN_MINUTES):
                continue

        log(f"\n=== Procesare: {query} ===")
        s = search(query)
        sid = s.get("id")
        if not sid:
            continue

        candidates = []
        for _ in range(POLLING_SECONDS):
            time.sleep(1)
            results = normalize_search(get_search_responses(sid))

            for item in results:
                if not item.get("hasFreeUploadSlot") or item.get("queueLength") != 0:
                    continue

                user = item["username"]
                for f in item.get("files", []):
                    fn = f.get("filename")
                    br = f.get("bitRate", 0)
                    sz = f.get("size", 0)

                    if fn and (fn.endswith(".flac") or (fn.endswith(".mp3") and (br >= 320 or sz >= 6_000_000))):
                        candidates.append((user, fn))

            if candidates:
                break

        for user, fn in candidates:
            log(f"[DOWNLOAD] {user} → {fn}")
            resp = enqueue_download(user, fn)
            update_status(entry_id,"queued","Găsit și pus în coada locală")

            if resp.get("status") in (200,201,202):
                start = time.time()
                while time.time() - start < 90:
                    downloads = normalize_downloads(list_downloads())
                    for d in downloads:
                        if d.get("filename") in fn:
                            st = d.get("state")
                            if st == "Completed":
                                update_status(entry_id,"downloaded","Descărcare finalizată")
                                break
                            if st in ("Failed","Cancelled"):
                                update_status(entry_id,"waiting","Remote a refuzat (File not shared)")
                                break
                    time.sleep(5)
                break

    log("[WORKER] Pauză 5 minute")
    time.sleep(300)
