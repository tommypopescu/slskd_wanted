
import requests, os
HOST=os.getenv('SLSKD_HOST'); API_KEY=os.getenv('SLSKD_API_KEY')
HEADERS={'Authorization': f'Bearer {API_KEY}'} if API_KEY else {}
def search(q): return requests.post(f"{HOST}/api/search", json={'searchText': q}, headers=HEADERS).json()
def get_search_results(i): return requests.get(f"{HOST}/api/search/{i}", headers=HEADERS).json()
def list_downloads(): return requests.get(f"{HOST}/api/downloads", headers=HEADERS).json()
def download(u,f): return requests.post(f"{HOST}/api/downloads", json={'username':u,'filename':f}, headers=HEADERS).json()
