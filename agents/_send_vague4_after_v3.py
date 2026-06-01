"""Attend fin vague 3 puis envoie vague 4 (13 FR autres)."""
import os, time, glob, requests
from datetime import datetime
from agents.shared import firestore_client as fs

with open(os.path.expanduser("~/.capitalnorvex/.env")) as f:
    for line in f:
        if line.startswith("INTERNAL_SECRET="):
            SECRET = line.strip().split("=",1)[1]
            break

ENDPOINT = "https://capitalnorvex.com/api/agent-send-outreach"

# Attendre fin V3
print("⏳ Attente fin vague 3…", flush=True)
while True:
    logs = sorted(glob.glob("/tmp/envoi_vague3_*.log"))
    if logs:
        with open(logs[-1]) as f:
            txt = f.read()
        lines = [l for l in txt.split("\n") if "/10 " in l]
        if len(lines) >= 10:
            print(f"✅ Vague 3 terminée", flush=True)
            break
    time.sleep(15)

time.sleep(60)  # cooldown SendGrid

# Récup vague 4 = FR queued qui ne sont PAS Hypotheca/Planiprêt/Multi-Prêts/Ratehub/Orbis/IH
brokers = fs.query("brokers", limit=500)
queued = [b for b in brokers if b.get("pendingDraft") and not b.get("skipOutreach")]
EXCLUDE_FIRMS = {"Hypotheca","Planiprêt","Multi-Prêts Commercial","Multi-Prêts",
                 "Multi-Prêts (Équipe Auria)","Multi-Prêts Hypothèques",
                 "Lévesque & Cie / Multi-Prêts Commercial","Ratehub",
                 "Orbis Mortgage Group","Orbis Commercial","Intelligence Hypothécaire"}
v4 = [b for b in queued if b.get("language")=="fr" and b.get("firmName","") not in EXCLUDE_FIRMS]

print(f"\n📨 VAGUE 4 — {len(v4)} cibles FR autres firmes\n", flush=True)

res = {"sent":0, "skip":0, "err":[]}
log = f"/tmp/envoi_vague4_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
with open(log, "w") as logf:
    for i, b in enumerate(v4, 1):
        nm = b.get("name") or "?"
        em = b["pendingDraft"].get("to","")
        t0 = time.time()
        try:
            r = requests.post(ENDPOINT,
                json={"collection":"brokers","docId":b["id"]},
                headers={"x-internal-secret":SECRET, "Content-Type":"application/json"},
                timeout=60)
            dt = time.time()-t0
            if r.status_code == 200:
                status = "✅"; res["sent"] += 1; msg = r.json().get("via","?")
            elif r.status_code in (409, 429):
                status = "⏭"; res["skip"] += 1; msg = r.json().get("error","")[:80]
            else:
                status = f"❌{r.status_code}"; res["err"].append((em,r.status_code,r.text[:200])); msg = r.text[:80]
        except Exception as ex:
            status = "❌EXC"; res["err"].append((em,"exc",str(ex)[:200])); msg = str(ex)[:80]; dt = time.time()-t0
        line = f"{i:>2}/{len(v4)} {status} {nm[:30]:<32} {em:<40} ({dt:.1f}s) {msg}"
        print(line, flush=True); logf.write(line+"\n"); logf.flush()
        if i < len(v4):
            time.sleep(30)

print(f"\n━━━ BILAN VAGUE 4 ━━━", flush=True)
print(f"✅ Envoyés: {res['sent']}/{len(v4)}  ⏭ Skip: {res['skip']}  ❌ Err: {len(res['err'])}", flush=True)
for em, code, txt in res["err"][:5]:
    print(f"   {em}  [{code}]  {txt[:80]}", flush=True)
print(f"📝 Log : {log}", flush=True)
