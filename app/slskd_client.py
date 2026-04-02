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
        return {"status": r.status_code, "text": r.text}


def search(query):
    r = requests.post(
        f"{HOST}/api/v0/searches",
        headers=HEADERS,
        json={"searchText": query}
    )
    return safe_json(r)


def get_search_responses(search_id):
    r = requests.get(
        f"{HOST}/api/v0/searches/{search_id}/responses",
        headers=HEADERS
    )
    return safe_json(r)


def list_downloads():
    r = requests.get(
        f"{HOST}/api/v0/transfers/downloads",
        headers=HEADERS
    )
    return safe_json(r)


def enqueue_download(username, filePath):
    """
    slskd așteaptă LISTĂ de QueueDownloadRequest,
    nu obiect singular.
    """
    payload = [
        {
            "username": username,
            "filePath": filePath
        }
    ]

    r = requests.post(
        f"{HOST}/api/v0/transfers/downloads",
        headers=HEADERS,
        json=payload
    )

    return {
        "status": r.status_code,
        "response": safe_json(r)
    }