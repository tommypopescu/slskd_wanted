import time
import pandas as pd
from slskd_client import (
    search,
    get_search_responses,
    list_downloads,
    enqueue_download
)

CSV_PATH = "wanted.csv"


def load_queries():
    try:
        df = pd.read_csv(CSV_PATH)
        return df["query"].tolist()
    except:
        return []


def get_completed():
    data = list_downloads()

    # slskd API v0 returns:
    # { "items": [ { "state": "...", "fileName": "...", ... } ] }
    items = data.get("items", [])
    completed = {x.get("fileName", "") for x in items if x.get("state") == "Completed"}

    return completed


while True:
    print("Worker: checking wanted list...")

    wanted = load_queries()
    completed = get_completed()

    for query in wanted:
        # Skip if already downloaded
        if any(query.lower() in c.lower() for c in completed):
            print(f"Already downloaded: {query}")
            continue

        # Start search
        s = search(query)
        search_id = s.get("id")

        if not search_id:
            print(f"Search failed for query: {query}")
            continue

        time.sleep(2)

        # Get results
        responses = get_search_responses(search_id)
        results = responses.get("items", [])

        if not results:
            print(f"No results for: {query}")
            continue

        # Take first result
        item = results[0]
        username = item["username"]
        filepath = item["filePath"]

        print(f"Downloading from {username}: {filepath}")
        enqueue_download(username, filepath)

    time.sleep(600)