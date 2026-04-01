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
    d = list_downloads()
    # responses look like { "items": [...] }
    items = d.get("items", [])
    return { x.get("fileName","") for x in items if x.get("state") == "Completed" }

while True:
    wanted = load_queries()
    completed = get_completed()

    for query in wanted:
        if any(query.lower() in c.lower() for c in completed):
            continue

        s = search(query)
        search_id = s.get("id")

        time.sleep(2)

        resp = get_search_responses(search_id)
        results = resp.get("items", [])

        if not results:
            continue

        file_item = results[0]
        username = file_item["username"]
        fullpath = file_item["filePath"]

        enqueue_download(username, fullpath)

    time.sleep(600)