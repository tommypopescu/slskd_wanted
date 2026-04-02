import json
import time
import pandas as pd
from datetime import datetime

from slskd_client import search, get_search_responses

CSV_PATH = "wanted.csv"
POLLING_SECONDS = 60


def log(msg):
    print(msg, flush=True)


def load_df():
    try:
        df = pd.read_csv(CSV_PATH, dtype=str)
    except:
        df = pd.DataFrame(
            columns=["id","query","status","last_message","last_attempt","found_sources"]
        )
    return df.fillna("")


def save_df(df):
    df.to_csv(CSV_PATH, index=False)


def update_sources(entry_id, sources):
    df = load_df()

    df.loc[df["id"] == entry_id, "found_sources"] = json.dumps(sources)
    df.loc[df["id"] == entry_id, "status"] = "found"
    df.loc[df["id"] == entry_id, "last_message"] = f"Găsit la {len(sources)} surse"
    df.loc[df["id"] == entry_id, "last_attempt"] = datetime.utcnow().isoformat()

    save_df(df)


def normalize_search(data):
    if isinstance(data, dict):
        return data.get("items", [])
    if isinstance(data, list):
        return data
    return []


def discover_sources(query):
    log(f"[SEARCH] Caut: {query}")
    s = search(query)
    sid = s.get("id")
    if not sid:
        return []

    sources = []
    seen = set()

    for _ in range(POLLING_SECONDS):
        time.sleep(1)
        results = normalize_search(get_search_responses(sid))

        for item in results:
            user = item.get("username")
            for f in item.get("files", []):
                fn = f.get("filename")
                if not fn:
                    continue

                is_audio = fn.lower().endswith(".mp3") or fn.lower().endswith(".flac")
                if not is_audio:
                    continue

                key = f"{user}|{fn}"
                if key in seen:
                    continue
                seen.add(key)

                sources.append({
                    "user": user,
                    "path": fn,
                    "bitrate": f.get("bitRate", 0),
                    "size": f.get("size", 0),
                    "last_seen": datetime.utcnow().isoformat()
                })

        if len(sources) >= 5:   # limită backbone
            break

    return sources


# ---------------- MAIN LOOP ----------------

while True:
    df = load_df()

    for _, row in df.iterrows():
        if row["status"] in ("found", "downloaded"):
            continue

        sources = discover_sources(row["query"])
        if sources:
            update_sources(row["id"], sources)

    log("[WORKER] Pauză 10 minute")
    time.sleep(600)
