from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import pandas as pd
import uuid

app = FastAPI()

# Mutăm UI-ul la /ui, ca să nu suprascriem rutele API
app.mount("/ui", StaticFiles(directory="static", html=True), name="ui")

CSV_PATH = "wanted.csv"


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


@app.put("/wanted/{item_id}")
def update_wanted(item_id: str, item: dict):
    df = load_df()
    if item_id not in df["id"].values:
        return {"error": "not_found"}
    df.loc[df["id"] == item_id, "query"] = item["query"]
    save_df(df)
    return {"id": item_id, "query": item["query"]}


@app.delete("/wanted/{item_id}")
def delete_wanted(item_id: str):
    df = load_df()
    if item_id not in df["id"].values:
        return {"error": "not_found"}
    df = df[df["id"] != item_id]
    save_df(df)
    return {"deleted": item_id}