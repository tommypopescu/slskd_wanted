import os
import requests

HOST = os.getenv("SLSKD_HOST")
API_KEY = os.getenv("SLSKD_API_KEY")

HEADERS = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}


def safe_json(response):
    try:
        return response.json()
    except Exception:
        return {
            "error": "invalid_json",
            "status": response.status_code,
            "text": response.text
        }

# -------------------------------------
# APPLICATION
# -------------------------------------

def app_state():
    r = requests.get(f"{HOST}/api/v0/application", headers=HEADERS)
    return safe_json(r)

# -------------------------------------
# SEARCHES
# -------------------------------------

def search(query):
    payload = {
        "searchText": query,
        "options": {"timeout": 15000}
    }
    r = requests.post(f"{HOST}/api/v0/searches", json=payload, headers=HEADERS)
    return safe_json(r)

def get_search_state(search_id):
    r = requests.get(f"{HOST}/api/v0/searches/{search_id}", headers=HEADERS)
    return safe_json(r)

def get_search_responses(search_id):
    r = requests.get(f"{HOST}/api/v0/searches/{search_id}/responses", headers=HEADERS)
    return safe_json(r)

# -------------------------------------
# DOWNLOADS (TRANSFERS)
# -------------------------------------

def list_downloads():
    r = requests.get(f"{HOST}/api/v0/transfers/downloads", headers=HEADERS)
    return safe_json(r)

def enqueue_download(username, file_path):
    payload = {"filePath": file_path}
    r = requests.post(
        f"{HOST}/api/v0/transfers/downloads/{username}",
        json=payload,
        headers=HEADERS
    )
    return safe_json(r)