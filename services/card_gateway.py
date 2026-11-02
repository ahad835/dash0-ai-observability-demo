import time, random, uuid
from flask import Flask, request, jsonify
from common import setup_logging

log = setup_logging("card-gateway")
app = Flask(__name__)
CHAOS = {"latency_ms": 0}

@app.post("/authorize")
def authorize():
    body = request.get_json(force=True)
    if CHAOS["latency_ms"]:
        time.sleep(CHAOS["latency_ms"] / 1000 * random.uniform(0.8, 1.3))
    else:
        time.sleep(random.uniform(0.03, 0.12))
    log.info("authorized order=%s amount=%s", body.get("order_id"), body.get("amount"))
    return jsonify(approved=True, auth_code=uuid.uuid4().hex[:6].upper())

@app.get("/admin/chaos")
def get_chaos():
    return jsonify(CHAOS)

@app.post("/admin/chaos")
def set_chaos():
    CHAOS["latency_ms"] = max(0, int(request.get_json(force=True).get("latency_ms", 0)))
    log.info("admin: latency injection set to %sms", CHAOS["latency_ms"])
    return jsonify(CHAOS)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8084)
