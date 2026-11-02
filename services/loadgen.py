import os, time, random, requests

URL = os.getenv("FRONTEND_URL", "http://frontend:8080")
PRODUCTS = ["hoodie", "mug", "socks", "plushie", "cap", "stickers"]
time.sleep(10)
while True:
    try:
        r = requests.post(f"{URL}/api/buy",
                          json={"product": random.choice(PRODUCTS), "qty": random.randint(1, 3)}, timeout=10)
        print("buy", r.status_code, flush=True)
    except Exception as e:
        print("error", e, flush=True)
    time.sleep(random.uniform(0.3, 1.0))
