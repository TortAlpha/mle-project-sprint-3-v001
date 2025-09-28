import os
import time
import random
import threading
import requests

API_URL = os.getenv("API_URL", "http://localhost:8765/predict")
USERS = int(os.getenv("USERS", "4"))
DURATION = int(os.getenv("DURATION", "60"))
SLEEP = float(os.getenv("SLEEP", "0.1"))

def make_payload():
    f = {
        "flat_id": random.randint(10_000, 99_999),
        "building_id": random.randint(1000, 9999),
        "total_area": round(random.uniform(20, 120), 1),
        "living_area": round(random.uniform(10, 80), 1),
        "kitchen_area": round(random.uniform(5, 25), 1),
        "floor": random.randint(1, 25),
        "floors_total": random.randint(5, 30),
        "flats_count": random.randint(20, 300),
        "ceiling_height": round(random.uniform(2.5, 3.5), 2),
        "rooms": random.choice([1, 2, 3, 4]),
        "build_year": random.randint(1960, 2022),
        "building_type_int": random.choice([1, 2, 3]),
        "is_apartment": random.choice([0, 1]),
        "studio": 0,
        "has_elevator": random.choice([0, 1]),
        "latitude": round(random.uniform(59.7, 60.1), 5),
        "longitude": round(random.uniform(30.1, 30.6), 5),
    }
    return {"items": [{"user_id": f"u-{random.randint(1, 9999)}", "features": f}]}

def worker(stop_event, wid):
    s = requests.Session()
    sent = ok = 0
    while not stop_event.is_set():
        try:
            r = s.post(API_URL, json=make_payload(), timeout=5)
            sent += 1
            if r.status_code == 200:
                ok += 1
        except Exception:
            pass
        time.sleep(SLEEP)
    print(f"[{wid}] sent={sent}, ok={ok}")

def make_test_load():
    stop = threading.Event()
    threads = [threading.Thread(target=worker, args=(stop, i), daemon=True) for i in range(USERS)]
    for t in threads: t.start()
    time.sleep(DURATION)
    stop.set()
    for t in threads: t.join()
