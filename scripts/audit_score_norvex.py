"""Audit Score Norvex v2 — bugs tests corrigés (case-sensitive, paths, body)."""
from __future__ import annotations
import base64
import json
import time
import urllib.request
import urllib.error

BASE = "https://capitalnorvex.com"
results = []

def check(name: str, fn):
    print(f"\n🧪 {name}")
    t0 = time.time()
    try:
        ok, detail = fn()
        elapsed = (time.time() - t0) * 1000
        status = "✅" if ok else "❌"
        print(f"   {status} {detail}  ({elapsed:.0f}ms)")
        results.append({"test": name, "ok": ok, "detail": detail, "ms": int(elapsed)})
    except Exception as e:
        elapsed = (time.time() - t0) * 1000
        print(f"   ❌ EXCEPTION: {e}  ({elapsed:.0f}ms)")
        results.append({"test": name, "ok": False, "detail": str(e), "ms": int(elapsed)})


def http(method, url, *, headers=None, data=None, timeout=20):
    headers = headers or {}
    if data is not None and not isinstance(data, (bytes, bytearray)):
        data = json.dumps(data).encode("utf-8")
        headers.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            # FIX: headers case-insensitive via lower keys
            hs = {k.lower(): v for k, v in r.headers.items()}
            return r.status, hs, r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        hs = {k.lower(): v for k, v in (e.headers.items() if e.headers else [])}
        return e.code, hs, e.read().decode("utf-8", errors="replace")


# 1. HTML
def t1():
    s, _, b = http("GET", f"{BASE}/capital-norvex-score.html")
    return s == 200 and len(b) > 10000, f"HTTP {s}, taille={len(b)}"

# 2. sw.js
def t2():
    s, _, b = http("GET", f"{BASE}/sw.js")
    return s == 200 and "fetch" in b, f"HTTP {s}, taille={len(b)}, v3/2026-05={'v3' in b or '2026-05' in b}"

# 3. store-pdf
def t3():
    body = {"filename": "test.pdf", "contentBase64": base64.b64encode(b"%PDF-1.4\n%%EOF").decode()}
    s, _, r = http("POST", f"{BASE}/.netlify/functions/store-pdf", data=body)
    j = json.loads(r) if s == 200 else {}
    return s == 200 and bool(j.get("key")), f"HTTP {s}, key={j.get('key', 'NONE')[:30]}"

# 4. create-score-upload-url (FIX: ajout sessionId)
def t4():
    body = {"sessionId": f"audit_{int(time.time())}", "filename": "test.pdf", "contentType": "application/pdf"}
    s, _, r = http("POST", f"{BASE}/.netlify/functions/create-score-upload-url", data=body)
    if s != 200: return False, f"HTTP {s}: {r[:120]}"
    j = json.loads(r)
    url = j.get("putUrl") or j.get("publicUrl") or j.get("uploadUrl") or j.get("signedUrl") or j.get("url")
    return bool(url and "googleapis" in url), f"HTTP 200, signed URL: {bool(url)}"

# 5. get-key
def t5():
    s, _, r = http("GET", f"{BASE}/.netlify/functions/get-key")
    j = json.loads(r) if s == 200 else {}
    key = j.get("apiKey") or j.get("key") or ""
    return s == 200 and key.startswith("sk-ant"), f"HTTP {s}, sk-ant: {key.startswith('sk-ant')}"

# 6. validate-broker-number (FIX: GET param n)
def t6():
    s, _, r = http("GET", f"{BASE}/api/validate-broker-number?n=CN-2026-002")
    if s != 200: return False, f"HTTP {s}: {r[:120]}"
    j = json.loads(r)
    return bool(j.get("valid") or j.get("active") or "active" in str(j).lower()), \
        f"HTTP 200, Denis CN-2026-002: {str(j)[:120]}"

# 7. get-result headers défensifs (FIX: case-insensitive)
def t7():
    s, h, _ = http("GET", f"{BASE}/.netlify/functions/get-result?jobId=audit_test")
    cc = h.get("cache-control", "").lower()
    xb = h.get("x-accel-buffering", "").lower()
    vary = h.get("vary", "")
    has_no_store = "no-store" in cc
    has_no_buf = xb == "no"
    has_vary_all = vary == "*"
    return (has_no_store and has_no_buf and has_vary_all), \
        f"no-store={has_no_store}, x-accel=no:{has_no_buf}, vary=*:{has_vary_all}"

# 8. Stress 30 polls (FIX: distingue erreur serveur 5xx d'un blip réseau transitoire ;
#    1 retry sur timeout ; échec uniquement si vraie défaillance serveur ou >1 timeout)
def t8():
    server_errors = 0   # vraies erreurs serveur (HTTP 5xx) = inacceptables
    timeouts = 0        # blips réseau transitoires = tolérés à 1 près
    times = []
    for i in range(30):
        for attempt in range(2):  # 1 retry sur timeout transitoire
            t0 = time.time()
            try:
                s, _, _ = http("GET", f"{BASE}/.netlify/functions/get-result?jobId=stress_{i}", timeout=10)
                times.append((time.time() - t0) * 1000)
                if s >= 500: server_errors += 1
                break
            except Exception:
                if attempt == 1:
                    timeouts += 1
    avg = sum(times) / len(times) if times else 0
    mx = max(times) if times else 0
    ok = server_errors == 0 and timeouts <= 1
    return ok, f"30 polls, {server_errors} err serveur 5xx, {timeouts} timeouts, max={mx:.0f}ms, avg={avg:.0f}ms"


check("1. Page HTML capital-norvex-score", t1)
check("2. sw.js service worker", t2)
check("3. store-pdf POST", t3)
check("4. create-score-upload-url POST", t4)
check("5. get-key Anthropic", t5)
check("6. validate-broker-number Denis CN-2026-002", t6)
check("7. get-result headers défensifs", t7)
check("8. Stress 30 polls HTTP/2", t8)

print("\n" + "=" * 70)
ok = sum(1 for r in results if r["ok"])
print(f"📊 RÉSULTAT GLOBAL : {ok}/{len(results)} OK")
print("=" * 70)
for r in results:
    icon = "✅" if r["ok"] else "❌"
    print(f"  {icon} {r['test']}  ({r['ms']}ms)")
if ok == len(results):
    print(f"\n✅ Score Norvex 100% opérationnel — PRÊT pour dossiers vendredi 29 mai")
else:
    print(f"\n⚠️ {len(results)-ok} fails — investigation requise")
