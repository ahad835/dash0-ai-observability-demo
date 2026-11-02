import os, requests
from flask import Flask, request, jsonify
from opentelemetry import trace
from common import setup_logging

log = setup_logging("payment")
app = Flask(__name__)
GATEWAY = os.getenv("GATEWAY_URL", "http://card-gateway:8084")
TIMEOUT_S = float(os.getenv("GATEWAY_TIMEOUT_S", "2.0"))

@app.post("/charge")
def charge():
    b = request.get_json(force=True)
    span = trace.get_current_span()
    span.set_attribute("order.id", b.get("order_id", ""))
    span.set_attribute("payment.amount", float(b.get("amount") or 0))
    span.set_attribute("payment.gateway.timeout_s", TIMEOUT_S)
    try:
        r = requests.post(f"{GATEWAY}/authorize", json=b, timeout=TIMEOUT_S)
        r.raise_for_status()
    except requests.exceptions.Timeout:
        log.error("card-gateway did not respond within %.1fs (order=%s amount=%s)",
                  TIMEOUT_S, b.get("order_id"), b.get("amount"))
        return jsonify(error="payment gateway timeout"), 504
    except requests.RequestException as e:
        log.error("card-gateway error: %s (order=%s)", e, b.get("order_id"))
        return jsonify(error="payment gateway error"), 502
    log.info("payment approved order=%s amount=%s", b.get("order_id"), b.get("amount"))
    return jsonify(r.json())

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8083)
