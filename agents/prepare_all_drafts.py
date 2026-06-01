"""Prépare TOUS les drafts en bypass des modules buggés.
Lit publicContact.email / contactInfo.email correctement.
Render via templates Python, upload Firebase Storage, set pendingDraft.
"""
from __future__ import annotations
import sys, time
from datetime import datetime, timezone
from agents.shared.firestore_client import db
from agents.courtiers.email_template import render_cold_outreach
from agents.promoteurs.email_template import render_project_announcement
from agents.capital.email_template import render_partnership_intro

def upload_html(coll_label, doc_id, html):
    from firebase_admin import storage as fb_storage
    bucket = fb_storage.bucket()
    storage_path = f"outreach-drafts/{coll_label}/{doc_id}.html"
    blob = bucket.blob(storage_path)
    blob.upload_from_string(html, content_type="text/html; charset=utf-8")
    return storage_path

def get_email(data, contact_field):
    pc = data.get(contact_field) or data.get('contactInfo') or data.get('publicContact') or {}
    if not isinstance(pc, dict): return ''
    return (pc.get('email') or '').strip()

def get_lang(data):
    lang = (data.get('language') or '').lower().strip()
    if lang in ('fr','en'): return lang
    return 'en' if (data.get('region') or '').upper() == 'ON' else 'fr'

def prep_brokers(d):
    docs = list(d.collection('brokers').stream())
    todo = [doc for doc in docs if doc.to_dict().get('status')=='cold' and not doc.to_dict().get('pendingDraft') and not doc.to_dict().get('sentAt')]
    print(f'\n=== brokers : {len(todo)} drafts ===')
    ok=fail=0
    for i, doc in enumerate(todo,1):
        data = doc.to_dict()
        email = get_email(data, 'publicContact')
        if not email or '@' not in email: fail += 1; continue
        try:
            lang = get_lang(data)
            target = {'name': data.get('name',''), 'agency': data.get('firmName','')}
            html = render_cold_outreach(target, lang=lang)
            firm = data.get('firmName','')
            subj = f"Capital Norvex — Partenariat 1.5%/dossier ({firm})" if lang=='fr' else f"Capital Norvex — 1.5% partner referral ({firm})"
            sp = upload_html('brokers', doc.id, html)
            d.collection('brokers').document(doc.id).update({'pendingDraft': {
                'storagePath': sp, 'htmlBytes': len(html.encode('utf-8')),
                'subject': subj, 'to': email, 'toName': data.get('name',''),
                'lang': lang, 'renderedAt': datetime.now(timezone.utc).isoformat(),
                'renderedBy': 'prepare_all_drafts',
            }})
            ok += 1
        except Exception as e:
            fail += 1
            if fail < 5: print(f'  err {doc.id}: {e}')
        if i%30==0: print(f'  {i}/{len(todo)} ok={ok} fail={fail}', flush=True)
    print(f'brokers DONE ok={ok} fail={fail}')

def prep_promoters(d):
    docs = list(d.collection('promoters').stream())
    todo = [doc for doc in docs if doc.to_dict().get('status')=='cold' and not doc.to_dict().get('pendingDraft') and not doc.to_dict().get('sentAt')]
    print(f'\n=== promoters : {len(todo)} drafts ===')
    ok=fail=0
    for i, doc in enumerate(todo,1):
        data = doc.to_dict()
        email = get_email(data, 'contactInfo')
        if not email or '@' not in email: fail += 1; continue
        try:
            lang = get_lang(data)
            promoter = {'name': data.get('name','') or data.get('companyName',''), 'companyName': data.get('companyName',''), 'language': lang}
            project = {'name': (data.get('recentProjects') or '').split(';')[0].strip() or 'Projet à venir'}
            html = render_project_announcement(promoter, project, lang=lang)
            company = data.get('companyName','')
            subj = f"Capital Norvex — Capital privé pour vos projets ({company})" if lang=='fr' else f"Capital Norvex — Private capital for your projects ({company})"
            sp = upload_html('promoters', doc.id, html)
            d.collection('promoters').document(doc.id).update({'pendingDraft': {
                'storagePath': sp, 'htmlBytes': len(html.encode('utf-8')),
                'subject': subj, 'to': email, 'toName': data.get('name','') or company,
                'lang': lang, 'renderedAt': datetime.now(timezone.utc).isoformat(),
                'renderedBy': 'prepare_all_drafts',
            }})
            ok += 1
        except Exception as e:
            fail += 1
            if fail < 5: print(f'  err {doc.id}: {e}')
        if i%30==0: print(f'  {i}/{len(todo)} ok={ok} fail={fail}', flush=True)
    print(f'promoters DONE ok={ok} fail={fail}')

def prep_capital(d):
    docs = list(d.collection('capitalTargets').stream())
    todo = [doc for doc in docs if doc.to_dict().get('status')=='cold' and not doc.to_dict().get('pendingDraft') and not doc.to_dict().get('sentAt')]
    print(f'\n=== capitalTargets : {len(todo)} drafts ===')
    ok=fail=0
    for i, doc in enumerate(todo,1):
        data = doc.to_dict()
        email = get_email(data, 'publicContact')
        if not email or '@' not in email: fail += 1; continue
        try:
            lang = get_lang(data)
            target = {'name': data.get('name',''), 'organization': data.get('organization','')}
            html = render_partnership_intro(target, lang=lang, target_id=doc.id)
            org = data.get('organization','')
            subj = f"Capital Norvex — Proposition de partenariat institutionnel ({org})" if lang=='fr' else f"Capital Norvex — Institutional partnership proposal ({org})"
            sp = upload_html('capital', doc.id, html)
            d.collection('capitalTargets').document(doc.id).update({'pendingDraft': {
                'storagePath': sp, 'htmlBytes': len(html.encode('utf-8')),
                'subject': subj, 'to': email, 'toName': data.get('name','') or org,
                'lang': lang, 'renderedAt': datetime.now(timezone.utc).isoformat(),
                'renderedBy': 'prepare_all_drafts',
            }})
            ok += 1
        except Exception as e:
            fail += 1
            if fail < 5: print(f'  err {doc.id}: {e}')
        if i%10==0: print(f'  {i}/{len(todo)} ok={ok} fail={fail}', flush=True)
    print(f'capitalTargets DONE ok={ok} fail={fail}')

if __name__ == '__main__':
    d = db()
    prep_brokers(d)
    prep_promoters(d)
    prep_capital(d)

    print('\n=== TOTAL DRAFTS PRÊTS ===')
    for coll in ['brokers','promoters','capitalTargets']:
        n = sum(1 for doc in d.collection(coll).stream() if doc.to_dict().get('pendingDraft'))
        print(f'  {coll}: {n}')
