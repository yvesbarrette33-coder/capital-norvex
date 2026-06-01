"""
Enrichissement par pattern email connu par firme.
Pour chaque doc sans email valide :
  - Identifier la firme
  - Appliquer le pattern email standard de la firme
  - Patch Firestore
"""
import re
import time
import unicodedata
from agents.shared.firestore_client import db

def slug(s):
    s = unicodedata.normalize('NFD', s).encode('ascii','ignore').decode().lower()
    return re.sub(r'[^a-z]','', s)

def split_name(full):
    parts = [p for p in re.split(r'\s+', (full or '').strip()) if p]
    parts = [p for p in parts if not p.startswith('(') and len(p) > 1]
    if len(parts) >= 2:
        return parts[0], parts[-1]
    return (parts[0], '') if parts else ('','')

# Patterns connus par firme (regex match dans firmName)
# Format: { 'pattern': lambda first,last → email, 'fallback_info': bool }
FIRMS = [
    {'match': r'multi-pr[êe]ts',     'gen': lambda f,l: f'{f[0]}{slug(l)}@multi-prets.ca',     'fb': 'sac@multi-prets.ca'},
    {'match': r'planipr[êe]t',        'gen': lambda f,l: f'{f[0]}{slug(l)}@planipret.com',     'fb': 'info@planipret.com'},
    {'match': r'\bpmml\b',           'gen': lambda f,l: f'{slug(f)}.{slug(l)}@pmml.ca',        'fb': 'info@pmml.ca'},
    {'match': r'mcommercial',         'gen': lambda f,l: f'{f[0]}.{slug(l)}@mcommercial.ca',   'fb': 'info@mcommercial.ca'},
    {'match': r'\borbis\b',          'gen': lambda f,l: f'{slug(f)}.{slug(l)}@groupeorbis.com','fb': 'info@groupeorbis.com'},
    {'match': r'\bjll\b',             'gen': lambda f,l: f'{slug(f)}.{slug(l)}@jll.com',        'fb': 'info@jll.com'},
    {'match': r'cbre',                'gen': lambda f,l: f'{slug(f)}.{slug(l)}@cbre.com',       'fb': 'info@cbre.ca'},
    {'match': r'cushman',             'gen': lambda f,l: f'{slug(f)}.{slug(l)}@cushwake.com',   'fb': 'info@cushmanwakefield.com'},
    {'match': r'colliers',            'gen': lambda f,l: f'{slug(f)}.{slug(l)}@colliers.com',   'fb': 'montreal@colliers.com'},
    {'match': r'avison',              'gen': lambda f,l: f'{slug(f)}.{slug(l)}@avisonyoung.com','fb': 'montreal@avisonyoung.ca'},
    {'match': r'newmark',             'gen': lambda f,l: f'{slug(f)}.{slug(l)}@nmrk.com',       'fb': 'montreal@newmark.com'},
    {'match': r'imeris',              'gen': lambda f,l: f'{f[0]}.{slug(l)}@imeris.ca',         'fb': 'info@imeris.ca'},
    {'match': r'multilogements',      'gen': lambda f,l: f'{slug(f)}@multilogements.ca',        'fb': 'info@multilogements.ca'},
    {'match': r'intelligence hypoth', 'gen': lambda f,l: f'{slug(f)}.{slug(l)}@groupeih.ca',    'fb': 'info@groupeih.ca'},
    {'match': r'performance hypoth',  'gen': lambda f,l: f'{slug(f)}.{slug(l)}@performancehypothecaire.ca','fb': 'info@performancehypothecaire.ca'},
    {'match': r'largo',               'gen': lambda f,l: f'{slug(f)}.{slug(l)}@largocapital.com','fb': 'info@largocapital.com'},
    {'match': r'canada ici',          'gen': lambda f,l: f'{slug(f)}.{slug(l)}@canadaici.com',  'fb': 'info@canadaici.com'},
    {'match': r'marcus.*millichap',   'gen': lambda f,l: f'{slug(f)}.{slug(l)}@marcusmillichap.com','fb': 'info@marcusmillichap.com'},
    {'match': r'dlc|dominion lending', 'gen': lambda f,l: f'{f[0]}.{slug(l)}@dlcg.ca',          'fb': 'contact@dominioncommercialcapital.ca'},
    {'match': r'\bgreenbirch\b',     'gen': lambda f,l: f'{slug(f)}@greenbirch.ca',            'fb': 'info@greenbirch.ca'},
    {'match': r'\boakbank\b',        'gen': lambda f,l: f'{slug(f)}{l[0].lower()}@oakbankcapital.com','fb': 'info@oakbankcapital.com'},
    {'match': r'peakhill',            'gen': lambda f,l: f'{slug(f)}.{slug(l)}@peakhillcapital.com','fb': 'info@peakhillcapital.com'},
    {'match': r'mcap',                'gen': lambda f,l: f'CMGinquiries@mcap.com',              'fb': 'CMGinquiries@mcap.com'},
    {'match': r'cmls',                'gen': lambda f,l: f'{slug(f)}.{slug(l)}@cmls.ca',        'fb': 'info@cmls.ca'},
    {'match': r'omj mortgage',        'gen': lambda f,l: f'{slug(f)}@omj.ca',                   'fb': 'info@omj.ca'},
    {'match': r'\bgreat gulf\b',     'gen': lambda f,l: f'{slug(f)}.{slug(l)}@greatgulf.com', 'fb': 'info@greatgulf.com'},
    {'match': r'\bmenkes\b',         'gen': lambda f,l: f'{slug(f)}.{slug(l)}@menkes.com',     'fb': 'info@menkes.com'},
    {'match': r'mattamy',             'gen': lambda f,l: f'{slug(f)}.{slug(l)}@mattamyhomes.com','fb': 'info@mattamyhomes.com'},
    {'match': r'\btridel\b',          'gen': lambda f,l: f'{slug(f)}.{slug(l)}@tridel.com',     'fb': 'info@tridel.com'},
    {'match': r'concord',             'gen': lambda f,l: f'{slug(f)}.{slug(l)}@concordpacific.com','fb': 'info@concordpacific.com'},
    {'match': r'minto',               'gen': lambda f,l: f'{slug(f)}.{slug(l)}@minto.com',      'fb': 'info@minto.com'},
    {'match': r'broccolini',          'gen': lambda f,l: f'{slug(f)}.{slug(l)}@broccolini.com', 'fb': 'contact@broccolini.com'},
    {'match': r'\bmach\b',            'gen': lambda f,l: f'{slug(f)}.{slug(l)}@groupemach.com', 'fb': 'info@groupemach.com'},
    {'match': r'devimco',             'gen': lambda f,l: f'{slug(f)}.{slug(l)}@devimco.com',    'fb': 'info@devimco.com'},
    {'match': r'brivia',              'gen': lambda f,l: f'{slug(f)}.{slug(l)}@briviagroup.ca', 'fb': 'info@briviagroup.ca'},
    {'match': r'\bcogir\b',           'gen': lambda f,l: f'{slug(f)}.{slug(l)}@cogir.net',      'fb': 'info@cogir.net'},
    {'match': r'maurice',             'gen': lambda f,l: f'{slug(f)}.{slug(l)}@legroupemaurice.com','fb': 'divulgation@legroupemaurice.com'},
    {'match': r'pr[ée]vel',           'gen': lambda f,l: f'{slug(f)}.{slug(l)}@prevel.ca',      'fb': 'info@prevel.ca'},
]

def find_firm(name):
    n = (name or '').lower()
    for firm in FIRMS:
        if re.search(firm['match'], n, re.I):
            return firm
    return None

def is_real_email(e):
    e = (e or '').strip()
    if not e: return False
    if '@' not in e: return False
    return True

def run(coll, contact_field, name_field='firmName', dry=False):
    d = db()
    docs = list(d.collection(coll).stream())
    patched = 0
    skipped_already = 0
    no_match = 0
    for doc in docs:
        data = doc.to_dict()
        pc = data.get(contact_field) or {}
        if not isinstance(pc, dict): pc = {}
        existing_email = (pc.get('email') or '').strip()
        # Skip si vrai email déjà présent ET pas un fallback bidon
        if is_real_email(existing_email) and not pc.get('_enrichedFallback'):
            skipped_already += 1
            continue
        firm_name = data.get(name_field) or data.get('companyName') or data.get('organization') or ''
        firm = find_firm(firm_name)
        if not firm:
            no_match += 1
            continue
        first, last = split_name(data.get('name',''))
        email = ''
        if first and last and len(last) > 1:
            try:
                email = firm['gen'](first.lower(), last.lower()).lower()
            except: email = firm['fb']
        else:
            email = firm['fb']
        if not is_real_email(email): continue
        if not dry:
            pc['email'] = email
            pc['_emailFromPattern'] = True
            pc['_enrichedFallback'] = False
            pc['_enrichedAt'] = time.time()
            d.collection(coll).document(doc.id).update({contact_field: pc})
        patched += 1
    print(f'[{coll}] patched={patched}  already_real={skipped_already}  no_firm_match={no_match}  total={len(docs)}')
    return patched

if __name__ == '__main__':
    import sys
    dry = '--dry' in sys.argv
    print('=== ENRICHISSEMENT PAR PATTERN PAR FIRME ===')
    run('brokers', 'publicContact', name_field='firmName', dry=dry)
    run('promoters', 'contactInfo', name_field='companyName', dry=dry)
    run('capitalTargets', 'publicContact', name_field='organization', dry=dry)
