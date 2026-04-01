import os
import requests

HOST = os.getenv("SLSKD_HOST")
API_KEY = os.getenv("SLSKD_API_KEY")

# Header corect pentru instanța TA slskd (din Home Assistant config)
HEADERS = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

def safe_json(response):
    """Încearcă să parseze JSON; dacă nu reușește, returnează dict cu eroare."""
    try:
        return response.json()
    except Exception:
        return {
            "error": "invalid_json_response",
            "status_code": response.status_code,
            "text": response.text
        }


# --------------------------------------------
# APPLICATION
# --------------------------------------------

def app_state():
    r = requests.get(f"{HOST}/api/v0/application", headers=HEADERS)
    return safe_json(r)


# --------------------------------------------
# SEARCHES
# --------------------------------------------

def search(query):
    """Start a search in slskd."""
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


# --------------------------------------------
# DOWNLOADS  (Transfers → Downloads)
# --------------------------------------------

def list_downloads():
    """Get all downloads according to /api/v0/transfers/downloads"""
    r = requests.get(f"{HOST}/api/v0/transfers/downloads", headers=HEADERS)
    return safe_json(r)


def enqueue_download(username, file_path):
    """
    Start a download of a remote file.
    API: POST /api/v0/transfers/downloads/{username}
    Body: { "filePath": "<full remote file path>" }
    """
    payload = {"filePath": file_path}
    r = requests.post(
        f"{HOST}/api/v0/transfers/downloads/{username}",
        json=payload,
        headers=HEADERS
    )
    return safe_json(r)


# --------------------------------------------
# BROWSE USERS
# --------------------------------------------

def browse_user(username):
    r = requests.get(f"{HOST}/api/v0/users/{username}/browse", headers=HEADERS)
    return safe_json(r)


def user_info(username):
    r = requests.get(f"{HOST}/api/v0/users/{username}/info", headers=HEADERS)
    return safe_json(r)