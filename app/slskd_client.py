import os
import requests

HOST = os.getenv("SLSKD_HOST")
API_KEY = os.getenv("SLSKD_API_KEY")

HEADERS = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

def safe_json(r):
    try:
        return r.json()
    except:
        return {}

def search(query):
    return safe_json(
        requests.post(
            f"{HOST}/api/v0/searches",
            headers=HEADERS,
            json={"searchText": query},
        )
    )

def get_search_responses(search_id):
    return safe_json(
        requests.get(
            f"{HOST}/api/v0/searches/{search_id}/responses",
            headers=HEADERS,
        )
    )

def list_downloads():
    return safe_json(
        requests.get(
            f"{HOST}/api/v0/transfers/downloads",
            headers=HEADERS,
        )
    )

def enqueue_download(username, filePath):
    return safe_json(
        requests.post(
            f"{HOST}/api/v0/transfers/downloads/{username}",
            headers=HEADERS,
            json={"filePath": filePath},
        )
    )