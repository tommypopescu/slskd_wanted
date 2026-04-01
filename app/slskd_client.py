import requests
import os

HOST = os.getenv("SLSKD_HOST")
API_KEY = os.getenv("SLSKD_API_KEY")

HEADERS = {"Authorization": f"Bearer {API_KEY}"}

# ------------------------
# SEARCH
# ------------------------
def search(query):
    payload = {"searchText": query}
    r = requests.post(f"{HOST}/api/v0/searches", json=payload, headers=HEADERS)
    return r.json()

def get_search_state(search_id):
    r = requests.get(f"{HOST}/api/v0/searches/{search_id}", headers=HEADERS)
    return r.json()

def get_search_responses(search_id):
    r = requests.get(f"{HOST}/api/v0/searches/{search_id}/responses", headers=HEADERS)
    return r.json()

# ------------------------
# DOWNLOADS
# ------------------------
def list_downloads():
    r = requests.get(f"{HOST}/api/v0/transfers/downloads", headers=HEADERS)
    return r.json()

def enqueue_download(username, filepath):
    payload = {"filePath": filepath}
    r = requests.post(
        f"{HOST}/api/v0/transfers/downloads/{username}",
        json=payload,
        headers=HEADERS
    )
    return r.json()