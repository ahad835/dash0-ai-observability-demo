import os, requests
from flask import Flask, request, jsonify, Response
from common import setup_logging

log = setup_logging("frontend")
app = Flask(__name__)
CHECKOUT = os.getenv("CHECKOUT_URL", "http://checkout:8082")
GATEWAY = os.getenv("GATEWAY_URL", "http://card-gateway:8084")
PRODUCTS = [
    {"id": "hoodie", "name": "Cloud Hoodie", "price": 49, "emoji": "🧥"},
    {"id": "mug", "name": "On-Call Mug", "price": 18, "emoji": "☕"},
    {"id": "socks", "name": "YAML Socks", "price": 12, "emoji": "🧦"},
    {"id": "plushie", "name": "Pager Plushie", "price": 25, "emoji": "🧸"},
    {"id": "cap", "name": "Rollback Cap", "price": 22, "emoji": "🧢"},
    {"id": "stickers", "name": "SRE Sticker Pack", "price": 8, "emoji": "✨"},
]

STYLE = """<style>
body{margin:0;font-family:system-ui,Ubuntu,sans-serif;background:#0b1020;color:#eef2f8}
header{display:flex;justify-content:space-between;align-items:center;padding:24px 40px;border-bottom:1px solid #1e2a44}
h1{margin:0;font-size:32px}.sub{color:#8ea0bf;font-size:18px}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:24px;padding:36px 40px}
.card{background:#121a30;border:1px solid #1e2a44;border-radius:18px;padding:26px;text-align:center}
.emoji{font-size:64px}.name{font-size:24px;font-weight:700;margin:10px 0 4px}.price{color:#8ea0bf;font-size:20px}
button{margin-top:16px;font:inherit;font-size:20px;font-weight:700;border:0;border-radius:12px;padding:14px 28px;background:#5b7cff;color:#fff;cursor:pointer}
button:disabled{opacity:.6}
#toast{position:fixed;left:50%;bottom:36px;transform:translateX(-50%);padding:18px 30px;border-radius:14px;font-size:22px;font-weight:700;display:none}
.ok{background:#11875d}.bad{background:#d63a4a}
.stats{display:flex;gap:28px;font-size:22px}.stats b{font-size:26px}
.modes{display:flex;flex-direction:column;gap:18px;padding:40px;max-width:640px}
.modes button{font-size:26px;padding:22px;text-align:left}
</style>"""

SHOP_HTML = """<!doctype html><html><head><meta charset="utf-8"><title>OnCall Outfitters</title>""" + STYLE + """</head><body>
<header><div><h1>🛒 OnCall Outfitters</h1><div class="sub">Swag for people who carry the pager</div></div>
<div class="stats"><div>✅ <b id="okN">0</b></div><div>❌ <b id="badN">0</b></div></div></header>
<div class="grid" id="grid"></div><div id="toast"></div>
<script>
let ok=0,bad=0;
fetch('/api/products').then(r=>r.json()).then(ps=>{grid.innerHTML=ps.map(p=>`<div class="card"><div class="emoji">${p.emoji}</div><div class="name">${p.name}</div><div class="price">$${p.price}</div><button onclick="buy('${p.id}',this)">Buy now</button></div>`).join('')});
async function buy(id,btn){btn.disabled=true;btn.textContent='Processing…';const t=performance.now();let msg,cls;
 try{const r=await fetch('/api/buy',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({product:id,qty:1})});
  const d=await r.json();const ms=Math.round(performance.now()-t);
  if(r.ok){ok++;msg=`✅ Order ${d.order_id} confirmed · ${ms} ms`;cls='ok'}
  else{bad++;msg=`❌ Payment failed: ${d.reason||d.error||r.status} · ${ms} ms`;cls='bad'}}
 catch(e){bad++;msg='❌ Store unreachable';cls='bad'}
 okN.textContent=ok;badN.textContent=bad;toast.textContent=msg;toast.className=cls;toast.style.display='block';
 clearTimeout(window.tt);window.tt=setTimeout(()=>toast.style.display='none',4000);
 btn.disabled=false;btn.textContent='Buy now'}
</script></body></html>"""

ADMIN_HTML = """<!doctype html><html><head><meta charset="utf-8"><title>Chaos Control</title>""" + STYLE + """</head><body>
<header><div><h1>🧪 Chaos Control</h1><div class="sub">Inject latency into the card gateway (the "bank")</div></div>
<div class="stats">Current: <b id="cur">…</b></div></header>
<div class="modes">
<button data-ms="0" style="background:#11875d">✅ Healthy</button>
<button data-ms="1800" style="background:#c98a12">🐢 Degraded bank (~40% of payments fail)</button>
<button data-ms="3000" style="background:#d63a4a">🔥 Bank outage (all payments fail)</button>
</div>
<script>
async function load(){const d=await (await fetch('/api/chaos')).json();cur.textContent=d.latency_ms+' ms delay'}
document.querySelectorAll('[data-ms]').forEach(b=>b.onclick=async()=>{
 await fetch('/api/chaos',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({latency_ms:+b.dataset.ms})});load()});
load();
</script></body></html>"""

@app.get("/")
def home():
    return Response(SHOP_HTML, mimetype="text/html")

@app.get("/admin")
def admin():
    return Response(ADMIN_HTML, mimetype="text/html")

@app.get("/api/products")
def products():
    return jsonify(PRODUCTS)

@app.post("/api/buy")
def buy():
    b = request.get_json(force=True)
    p = next((x for x in PRODUCTS if x["id"] == b.get("product")), None)
    if not p:
        return jsonify(error="unknown product"), 404
    qty = int(b.get("qty", 1))
    try:
        r = requests.post(f"{CHECKOUT}/checkout",
                          json={"product": p["id"], "qty": qty, "amount": p["price"] * qty}, timeout=6)
    except requests.RequestException as e:
        log.error("checkout unreachable: %s", e)
        return jsonify(status="failed", reason="checkout unavailable"), 503
    return jsonify(r.json()), r.status_code

@app.get("/api/chaos")
def chaos_get():
    return jsonify(requests.get(f"{GATEWAY}/admin/chaos", timeout=3).json())

@app.post("/api/chaos")
def chaos_set():
    r = requests.post(f"{GATEWAY}/admin/chaos", json=request.get_json(force=True), timeout=3)
    return jsonify(r.json()), r.status_code

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
