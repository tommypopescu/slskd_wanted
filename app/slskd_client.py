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
        return {"error": "invalid_json", "text": r.text}

def search(query):
    payload = {
        "searchText": query
    }
    r = requests.post(f"{HOST}/api/v0/searches", json=payload, headers=HEADERS)
    return safe_json(r)

def get_search_responses(search_id):
    r = requests.get(f"{HOST}/api/v0/searches/{search_id}/responses", headers=HEADERS)
    return safe_json(r)

def list_downloads():
    r = requests.get(f"{HOST}/api/v0/transfers/downloads", headers=HEADERS)
    return safe_json(r)

def enqueue_download(username, filepath):
    payload = {"filePath": filepath}
    r = requests.post(
        f"{HOST}/api/v0/transfers/downloads/{username}",
        json=payload,
        headers=HEADERS
    )
    return safe_json(r)