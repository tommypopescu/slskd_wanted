# slskd_wanted – Soulseek Wanted List & Source Discovery

## 1. Ce este acest proiect

`slskd_wanted` este un serviciu auxiliar pentru **slskd (Soulseek daemon)** care ajută la:

- menținerea unei liste de fișiere „wanted”
- descoperirea surselor din rețeaua Soulseek
- memorarea **unde există fișierele** (user + path)
- afișarea clară a informației pentru decizie manuală

❗ Proiectul **NU mai încearcă să forțeze descărcări automate**, deoarece protocolul Soulseek NU permite acest lucru în mod fiabil prin API.

---

## 2. De ce NU funcționează download automat (important)

Soulseek funcționează astfel:

1. Search = „fișierul a existat cândva la acest user”
2. Download = handshake imediat, one‑shot
3. Dacă remote refuză → `File not shared`
4. Nu există „pending remote queue”

Consecințe:
- `Queued, Locally` ≠ download garantat
- `Completed / Rejected` ≠ eroare de cod
- slskd API NU poate replica exact click‑ul din UI

Prin urmare:
✅ retry agresiv este inutil  
✅ forțarea downloadului este greșită  
✅ abordarea corectă este **discovery + human-in-the-loop**

---

## 3. Obiectivul corect al aplicației

Aplicația NU este un downloader automat.

Este un **index de descoperire a surselor** care răspunde la întrebarea:

> „Fișierul există? La cine? Unde? De unde pot încerca manual?”

---

## 4. Starea actuală a proiectului

### ✅ Ce funcționează

- backend FastAPI stabil
- worker care face **doar discovery**
- persistență CSV
- salvare surse per fișier
- API reutilizabil

### ❌ Ce este oprit intenționat

- download automat
- retry agresiv
- tratarea `Completed/Rejected` ca eroare
- UI combinat discovery + download

UI-ul actual a devenit confuz și este **intenționat pus în așteptare**.

---

## 5. Structura proiectului

app/
├── worker.py          # discovery-only (search, collect sources)
├── main.py            # FastAPI backend
├── slskd_client.py    # slskd API wrapper
├── wanted.csv         # persistent state
└── static/
└── index.html     # UI experimental (nefinal)

---

## 6. Model de date – wanted.csv

```csv
id,query,status,last_message,last_attempt,found_sources


Semnificație coloane

id – UUID
query – textul căutării (ex: Artist - Track.mp3)
status – new | found | downloaded | waiting
last_message – mesaj UX
last_attempt – timestamp ISO UTC
found_sources – JSON string cu surse descoperite

7. Structura found_sources
found_sources conține un JSON (string în CSV):

[
  {
    "user": "jemiej",
    "path": "@@rjdnm\\Music\\People.mp3",
    "bitrate": 320,
    "size": 7321483,
    "last_seen": "2026-04-02T10:03:17Z"
  }
]

🔹 Important:
Aceasta este informație, NU instrucțiune de download.

8. Worker – ce face și ce NU face
✅ Face

search prin slskd API
colectează surse audio valide (mp3 / flac)
salvează user + path + metadata
marchează status = found

❌ Nu face

enqueue repetat
retry forțat
download automat
manipularea stării remote

Worker-ul este pasiv și sigur.

9. API – documentație pentru reutilizare
Backend-ul este complet reutilizabil.
GET /wanted
Returnează lista completă.

[
  {
    "id": "uuid",
    "query": "Libianca - People.mp3",
    "status": "found",
    "last_message": "Găsit la 4 surse",
    "last_attempt": "2026-04-02T10:03:17Z",
    "found_sources": "[{...}]"
  }
]

POST /wanted
Adaugă un fișier în listă.
JSON{  "query": "Artist - Track.mp3"

DELETE /wanted/{id}
Șterge un item.

10. De ce UI-ul a fost oprit
Ultimul UI:

afișa prea multe informații simultan
re-reda complet lista
amesteca discovery cu download
devenea inutilizabil cu multe surse

Decizia corectă a fost:
✅ stop
✅ documentare
✅ redesign ulterior, nu patch-uri

11. UX corect pentru viitor (direcție)
Următorul UI trebuie să:

separe lista de fișiere de lista de surse
afișeze sursele doar la cerere (expand)
fie read-only by default
permită doar acțiune manuală


12. Prompt pentru reluarea dezvoltării (FOARTE IMPORTANT)
Copiază exact acest prompt când vrei să continui:
We have a project called slskd_wanted.

Current state:
- FastAPI backend with endpoints:
  GET /wanted
  POST /wanted
  DELETE /wanted/{id}
- wanted.csv stores:
  id, query, status, last_message, last_attempt, found_sources
- worker.py does discovery only:
  - Soulseek search via slskd
  - collects sources (user + path + bitrate + size)
  - stores them in found_sources
- Automatic download retries were intentionally removed.
- File not shared is normal Soulseek behavior.

Goal:
- Build a clean UI focused on discovery and transparency.
- Show where files exist and allow manual action via slskd UI.
- Do NOT force downloads automatically.

Please propose a clean UI architecture and data flow.


13. Concluzie finală
Proiectul:
✅ este funcțional
✅ este corect conceptual
✅ respectă limitările Soulseek
✅ nu mai luptă cu protocolul
Ce lipsește NU este „un fix”, ci un UI curat.
Decizia de a documenta și opri aici este corectă.
