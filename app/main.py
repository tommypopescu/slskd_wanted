from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import pandas as pd
import uuid
import os

app = FastAPI()

# Serve UI
app.mount("/ui", StaticFiles(directory="static", html=True), name="ui")

CSV_PATH = "wanted.csv"

# Valoare inițială din ENV sau default 30
CYCLE_PAUSE_MINUTES = int(os.getenv("SLSKD_CYCLE_PAUSE_MINUTES", "30"))

# ============ CONFIG ENDPOINTS ============

@app.get("/config")
def get_config():
    return {"cycle_pause_minutes": CYCLE_PAUSE_MINUTES}

@app.post("/config")
def update_config(cfg: dict):
    global CYCLE_PAUSE_MINUTES
    CYCLE_PAUSE_MINUTES = int(cfg.get("cycle_pause_minutes", 30))
    return {"status": "ok", "cycle_pause_minutes": CYCLE_PAUSE_MINUTES}

# ============ WANTED LIST ============

def load_df():
    return pd.read_csv(CSV_PATH)

def save_df(df):
    df.to_csv(CSV_PATH, index=False)

@app.get("/wanted")
def list_wanted():
    df = load_df()
    return df.to_dict(orient="records")

@app.post("/wanted")
def add_wanted(item: dict):
    df = load_df()

    new_row = {
        "id": str(uuid.uuid4()),
        "query": item["query"],
        "status": "new",
        "last_message": "Nou",
        "last_attempt": ""
    }

    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    save_df(df)

    return new_row


@app.delete("/wanted/{item_id}")
def delete_wanted(item_id: str):
    df = load_df()
    df = df[df["id"] != item_id]
    save_df(df)
    return {"deleted": item_id}

from datetime import datetime

@app.post("/wanted/{entry_id}/retry")
def retry_now(entry_id: str):
    df = load_df()
    df.loc[df["id"] == entry_id, "status"] = "new"
    df.loc[df["id"] == entry_id, "last_message"] = "Retry manual"
    df.loc[df["id"] == entry_id, "last_attempt"] = datetime.utcnow().isoformat()
    save_df(df)
    return {"status": "ok"}