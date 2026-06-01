"""
Enrichissement coordonnées (email + tel) pour brokers / promoters / capitalTargets.
Pour chaque doc sans contact : fetch sourceUrl + /contact + /about, extrait via regex,
fallback info@domain si rien trouvé.
"""
import re
import sys
import time
from urllib.parse import urlparse, urljoin
import requests
from agents.shared.firestore_client import db

EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
PHONE_RE = re.compile(r'(?:\+?1[-.\s]?)?\(?(\d{3})\)?[-.\s]?(\d{3})[-.\s]?(\d{4})')
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; CapitalNorvexBot/1.0)'}
SKIP_EMAIL_DOMAINS = {'sentry.io','wixpress.com','example.com','godaddy.com','gmail.com','yahoo.com','hotmail.com'}
SKIP_EMAIL_LOCAL = {'no-reply','noreply','postmaster','webmaster','privacy','abuse','dmarc','spam'}

def fetch(url, timeout=8):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        if r.status_code == 200 and 'text/html' in r.headers.get('content-type','').lower():
            return r.text
    except Exception:
        pass
    return ''

def extract_contacts(html, domain_hint=''):
    emails = set()
    phones = set()
    for m in EMAIL_RE.findall(html):
        m = m.lower().strip()
        local, _, dom = m.partition('@')
        if dom in SKIP_EMAIL_DOMAINS: continue
        if local in SKIP_EMAIL_LOCAL: continue
        if len(m) > 80: continue
        emails.add(m)
    for m in PHONE_RE.findall(html):
        a, b, c = m
        if a in ('800','888','877','866','855','844','833','822','811'):
            # Garde toll-free aussi mais en dernier recours
            phones.add(f'1-{a}-{b}-{c}')
        else:
            phones.add(f'{a}-{b}-{c}')
    return emails, phones

def domain_of(url):
    try:
        p = urlparse(url if url.startswith('http') else 'https://'+url)
        return p.netloc.lower()
    except: return ''

def best_email(emails, domain_hint=''):
    if not emails: return ''
    # Préférer matching domain
    if domain_hint:
        d = domain_hint.replace('www.','')
        same = [e for e in emails if e.endswith('@'+d)]
        if same:
            # Préférer info@ / contact@
            for prefix in ('info@','contact@','partnerships@','partner@','admin@'):
                for e in same:
                    if e.startswith(prefix): return e
            return sorted(same, key=len)[0]
    # Sinon premier non-générique
    return sorted(emails, key=len)[0]

def best_phone(phones):
    # Préférer non-toll-free
    direct = [p for p in phones if not p.startswith('1-8')]
    if direct:
        return sorted(direct)[0]
    return sorted(phones)[0] if phones else ''

def enrich_doc(doc, contact_field='publicContact'):
    """Returns (email, phone, source_pages_tried)"""
    data = doc.to_dict()
    # URL candidates
    urls = []
    for k in ('sourceUrl','website'):
        v = data.get(k) or ''
        if v: urls.append(v)
    # contactInfo.website
    ci = data.get('contactInfo') or {}
    if isinstance(ci, dict) and ci.get('website'): urls.append(ci['website'])
    pc = data.get('publicContact') or {}
    if isinstance(pc, dict) and pc.get('website'): urls.append(pc['website'])
    if isinstance(pc, dict) and pc.get('profile_url'): urls.append(pc['profile_url'])

    seen = set()
    all_emails = set()
    all_phones = set()
    pages_tried = 0
    for u in urls:
        if u in seen: continue
        seen.add(u)
        if not u.startswith('http'): u = 'https://' + u
        # Page principale + contact + about
        candidates = [u]
        try:
            base = urlparse(u)
            root = f'{base.scheme}://{base.netloc}'
            candidates.extend([
                urljoin(root,'/contact'), urljoin(root,'/contact-us'),
                urljoin(root,'/contactez-nous'), urljoin(root,'/nous-joindre'),
                urljoin(root,'/about'), urljoin(root,'/about-us'),
                urljoin(root,'/a-propos'), urljoin(root,'/equipe'), urljoin(root,'/team'),
            ])
        except: pass
        for c in candidates[:6]:  # cap pour rapidité
            html = fetch(c)
            pages_tried += 1
            if html:
                e, p = extract_contacts(html)
                all_emails |= e
                all_phones |= p
            if all_emails and all_phones: break
        if all_emails and all_phones: break

    domain_hint = domain_of(urls[0]) if urls else ''
    email = best_email(all_emails, domain_hint)
    phone = best_phone(all_phones)
    # Fallback : info@domain si on a un site mais aucun email
    if not email and domain_hint:
        d = domain_hint.replace('www.','')
        if d and '.' in d:
            email = f'info@{d}'  # fallback générique, marqué comme tel
    return email, phone, pages_tried

def run(collection, contact_field, limit=None, dry=False):
    d = db()
    docs = list(d.collection(collection).stream())
    todo = []
    for doc in docs:
        data = doc.to_dict()
        pc = data.get(contact_field) or data.get('contactInfo') or {}
        has = bool((pc.get('email') or '').strip()) or bool((pc.get('phone') or '').strip())
        if not has:
            todo.append(doc)
    if limit: todo = todo[:limit]
    print(f'[{collection}] À enrichir: {len(todo)} docs')
    enriched = 0
    for i, doc in enumerate(todo,1):
        data = doc.to_dict()
        name = data.get('name','?') or data.get('organization','?')
        email, phone, tried = enrich_doc(doc, contact_field)
        is_fallback = bool(email and email.startswith('info@') and not phone)
        if email or phone:
            if not dry:
                pc = data.get(contact_field) or {}
                if not isinstance(pc, dict): pc = {}
                if email and not pc.get('email'): pc['email'] = email
                if phone and not pc.get('phone'): pc['phone'] = phone
                pc['_enrichedAt'] = time.time()
                pc['_enrichedFallback'] = is_fallback
                d.collection(collection).document(doc.id).update({contact_field: pc})
            enriched += 1
            mark = '🟡' if is_fallback else '✅'
            print(f'  {mark} {i}/{len(todo)} {name[:50]:50s} → {email[:35]:35s} {phone}')
        else:
            print(f'  ❌ {i}/{len(todo)} {name[:50]:50s} (rien trouvé, {tried} pages)')
    print(f'\n[{collection}] ENRICHIS: {enriched}/{len(todo)}')

if __name__ == '__main__':
    dry = '--dry' in sys.argv
    coll = None
    for arg in sys.argv[1:]:
        if not arg.startswith('--'): coll = arg
    if coll:
        field = 'contactInfo' if coll == 'promoters' else 'publicContact'
        run(coll, field, dry=dry)
    else:
        run('brokers', 'publicContact', dry=dry)
        run('promoters', 'contactInfo', dry=dry)
        run('capitalTargets', 'publicContact', dry=dry)
