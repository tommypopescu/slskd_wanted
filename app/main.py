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
    new_id = str(uuid.uuid4())
    df.loc[len(df)] = [new_id, item["query"]]
    save_df(df)
    return {"id": new_id, "query": item["query"]}

@app.delete("/wanted/{item_id}")
def delete_wanted(item_id: str):
    df = load_df()
    df = df[df["id"] != item_id]
    save_df(df)
    return {"deleted": item_id}