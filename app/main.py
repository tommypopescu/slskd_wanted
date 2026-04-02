from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import pandas as pd
import uuid
from datetime import datetime

CSV_PATH = "wanted.csv"
app = FastAPI()
app.mount("/ui", StaticFiles(directory="static", html=True), name="ui")

def load_df():
    try:
        df = pd.read_csv(CSV_PATH, dtype=str)
    except:
        df = pd.DataFrame(columns=["id","query","status","last_message","last_attempt"])
    return df.fillna("")

def save_df(df):
    df.to_csv(CSV_PATH,index=False)

@app.get("/wanted")
def list_wanted():
    return load_df().to_dict(orient="records")

@app.post("/wanted")
def add_wanted(item:dict):
    df = load_df()
    new = {
        "id": str(uuid.uuid4()),
        "query": item["query"],
        "status":"new",
        "last_message":"Nou",
        "last_attempt":""
    }
    df = pd.concat([df,pd.DataFrame([new])])
    save_df(df)
    return new

@app.post("/wanted/{entry_id}/retry")
def retry(entry_id:str):
    df = load_df()
    df.loc[df["id"]==entry_id,"status"]="new"
    df.loc[df["id"]==entry_id,"last_message"]="Retry manual"
    df.loc[df["id"]==entry_id,"last_attempt"]=datetime.utcnow().isoformat()
    save_df(df)
    return {"ok":True}

@app.delete("/wanted/{entry_id}")
def delete(entry_id:str):
    df = load_df()
    df = df[df["id"]!=entry_id]
    save_df(df)
    return {"ok":True}