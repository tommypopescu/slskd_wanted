import subprocess
import threading
import os
import time

env = os.environ.copy()

def run_uvicorn():
    subprocess.call(
        "uvicorn main:app --host 0.0.0.0 --port 8000",
        shell=True,
        env=env
    )

def run_worker():
    subprocess.call(
        "python worker.py",
        shell=True,
        env=env
    )

t1 = threading.Thread(target=run_uvicorn)
t2 = threading.Thread(target=run_worker)

t1.start()
time.sleep(1)
t2.start()

t1.join()
t2.join()