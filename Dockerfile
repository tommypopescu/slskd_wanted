FROM python:3.11
WORKDIR /app

COPY app/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ .

CMD sh -c "uvicorn main:app --host 0.0.0.0 --port 8000 & python worker.py"