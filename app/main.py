
from fastapi import FastAPI,HTTPException
import pandas as pd, uuid
CSV='wanted.csv'; app=FastAPI()
def load(): return pd.read_csv(CSV)
def save(df): df.to_csv(CSV,index=False)
@app.get('/wanted')
def list(): return load().to_dict(orient='records')
@app.post('/wanted')
def add(it:dict):
 df=load(); i=str(uuid.uuid4()); df.loc[len(df)] = [i,it['query']]; save(df); return {'id':i,'query':it['query']}
@app.put('/wanted/{i}')
def upd(i:str,it:dict):
 df=load();
 if i not in df['id'].values: raise HTTPException(404)
 df.loc[df['id']==i,'query']=it['query']; save(df); return {'id':i,'query':it['query']}
@app.delete('/wanted/{i}')
def delete(i:str):
 df=load();
 if i not in df['id'].values: raise HTTPException(404)
 df=df[df['id']!=i]; save(df); return {'deleted':i}
