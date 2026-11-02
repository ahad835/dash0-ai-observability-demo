import os, time, random, uuid, requests
from flask import Flask, request, jsonify
from opentelemetry import trace, metrics
from common import setup_logging

log = setup_logging("checkout")
app = Flask(__name__)
PAYMENT = os.getenv("PAYMENT_URL", "http://payment:8083")
orders = metrics.get_meter("oncall.checkout").create_counter(
    "shop.orders", unit="{order}", description="Orders by outcome")

@app.post("/checkout")
def checkout():
    b = request.get_json(force=True)
    order_id = uuid.uuid4().hex[:8]
    span = trace.get_current_span()
    span.set_attribute("order.id", order_id)
    span.set_attribute("order.product", b.get("product", ""))
    span.set_attribute("order.amount", float(b.get("amount") or 0))
    time.sleep(random.uniform(0.01, 0.04))  # inventory check
    try:
        r = requests.post(f"{PAYMENT}/charge",
                          json={"order_id": order_id, "amount": b.get("amount")}, timeout=5)
    except requests.RequestException as e:
        log.error("order %s failed: payment unreachable (%s)", order_id, e)
        orders.add(1, {"status": "failed"})
        return jsonify(order_id=order_id, status="failed", reason="payment unavailable"), 503
    if r.status_code != 200:
        reason = r.json().get("error", "payment declined")
        log.error("order %s failed: payment returned %s (%s)", order_id, r.status_code, reason)
        orders.add(1, {"status": "failed"})
        return jsonify(order_id=order_id, status="failed", reason=reason), 502
    orders.add(1, {"status": "confirmed"})
    log.info("order %s confirmed product=%s amount=%s", order_id, b.get("product"), b.get("amount"))
    return jsonify(order_id=order_id, status="confirmed")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8082)
