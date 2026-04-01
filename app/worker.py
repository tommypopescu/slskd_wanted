import time
import pandas as pd
from slskd_client import (
    search,
    get_search_responses,
    list_downloads,
    enqueue_download
)

CSV_PATH = "wanted.csv"

SEARCH_REPEAT_INTERVAL = 15 * 60   # 15 minute
RESPONSE_WAIT = 2                  # timp de asteptare dupa search


def load_df():
    try:
        return pd.read_csv(CSV_PATH)
    except:
        return pd.DataFrame(columns=["id", "query"])


def save_df(df):
    df.to_csv(CSV_PATH, index=False)


def get_completed_filenames():
    """Returnează fișiere complet descărcate."""
    data = list_downloads()
    items = data.get("items", [])
    completed = {
        item.get("fileName", "")
        for item in items
        if item.get("state") == "Completed"
    }
    return completed


def search_for_mp3_320(query):
    """
    Face o căutare o singură dată.
    Returnează tuple (username, filepath) dacă găsește MP3 320.
    """
    print(f"[SEARCH] Pornesc căutare pentru: {query}")
    s = search(query)
    search_id = s.get("id")

    if not search_id:
        print("[ERROR] Search ID invalid.")
        return None

    time.sleep(RESPONSE_WAIT)

    data = get_search_responses(search_id)
    results = data.get("items", [])

    if not results:
        print("[SEARCH] Nicio potrivire gasita.")
        return None

    # Căutăm MP3 320 Kbps
    for item in results:
        file = item.get("file", {})
        ext = file.get("extension", "").lower()
        bitrate = file.get("bitRate", 0)

        if ext == "mp3" and bitrate == 320:
            return (item["username"], file["filePath"])

    print("[SEARCH] Gasit rezultate, dar nu MP3 320.")
    return None


def download_until_complete(username, filepath, query):
    """Inițiază descărcarea și așteaptă finalizarea."""
    print(f"[DOWNLOAD] Pornesc descărcare pentru {query}: {filepath}")
    enqueue_download(username, filepath)

    # Poll până descărcarea este completă
    while True:
        completed = get_completed_filenames()
        if any(query.lower() in x.lower() for x in completed):
            print(f"[COMPLETE] Descărcare completă: {query}")
            return True
        time.sleep(5)


while True:
    df = load_df()

    if df.empty:
        print("[WORKER] Lista goală. Aștept 1 minut…")
        time.sleep(60)
        continue

    for idx, row in df.iterrows():
        query = row["query"]

        print(f"\n===== Procesare: {query} =====")

        # 1. verificăm dacă deja este descărcată
        completed = get_completed_filenames()
        if any(query.lower() in x.lower() for x in completed):
            print(f"[SKIP] {query} era deja descărcată. O șterg din listă.")
            df = df[df["id"] != row["id"]]
            save_df(df)
            continue

        # 2. Fă SEARCH → o singură încercare
        result = search_for_mp3_320(query)

        # 3. Dacă nu a găsit nimic, mai încearcă PESTE 15 minute
        if not result:
            print(f"[WAIT] Nu am găsit 320 pentru {query}. Revin peste 15 minute.")
            time.sleep(SEARCH_REPEAT_INTERVAL)
            continue

        username, filepath = result

        # 4. descarcă și așteaptă finalizarea
        ok = download_until_complete(username, filepath, query)

        # 5. elimină din listă
        if ok:
            df = df[df["id"] != row["id"]]
            save_df(df)

    print("\n[LOOP] Am terminat runda. Revin în 1 minut.\n")
    time.sleep(60)