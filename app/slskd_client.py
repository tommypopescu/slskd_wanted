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
    Încearcă AMBELE variante de endpoint.
    Returnează primul răspuns de succes.
    """
    # Varianta A (generică – preferată în multe build-uri)
    payload = {
        "username": username,
        "filePath": filePath
    }
    r1 = requests.post(
        f"{HOST}/api/v0/transfers/downloads",
        headers=HEADERS,
        json=payload
    )

    if r1.status_code in (200, 201, 202, 204):
        return {"ok": True, "endpoint": "generic", "resp": safe_json(r1)}

    # Varianta B (per-user)
    r2 = requests.post(
        f"{HOST}/api/v0/transfers/downloads/{username}",
        headers=HEADERS,
        json={"filePath": filePath}
    )

    if r2.status_code in (200, 201, 202, 204):
        return {"ok": True, "endpoint": "per-user", "resp": safe_json(r2)}

    # Nimic nu a mers
    return {
        "ok": False,
        "respA": {"status": r1.status_code, "text": r1.text},
        "respB": {"status": r2.status_code, "text": r2.text},
    }