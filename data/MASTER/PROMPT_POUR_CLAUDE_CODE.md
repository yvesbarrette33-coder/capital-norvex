# 🎯 PROMPT À COPIER-COLLER DANS CLAUDE CODE

Copie tout ce qui est entre les `===== DÉBUT =====` et `===== FIN =====` ci-dessous, et colle-le dans Claude Code à l'ouverture du dossier `capitalnorvex-site`.

---

===== DÉBUT =====

Bonjour Claude Code. J'ai 281 cibles de prospection pré-recherchées et enrichies dans `data/MASTER/`. Mission : valider les schémas, faire un dry-run d'ingestion Firestore, et préparer les pipelines outreach.

## Données disponibles (3 fichiers JSON)

**1. `data/MASTER/seed_brokers_ALL_2026-05-07.json`** — 117 courtiers hypothécaires commerciaux QC (93) + ON (24)
- 76% avec courriel public, 74% avec téléphone, 94% avec LinkedIn corporatif
- Schéma : `{name, firmName, licenseNumber, region, city, specialty[], title, typicalDealSize{min,max}, relationshipStatus, dealsReceived, dealsClosed, preferredChannel, publicContact{email,phone,linkedin,profile_url}, sourceUrl, notes, _source}`

**2. `data/MASTER/seed_promoters_ALL_2026-05-07.json`** — 101 promoteurs immobiliers QC (58) + ON (43)
- 69% avec courriel, 68% téléphone, 57% LinkedIn
- Schéma : `{name, companyName, region, city, subregion, projectTypes[], projectTypesDetail[], recentProjects, estimatedAnnualVolume, relationshipStatus, score (5-8), contactInfo{email,phone,website,linkedin,contact_person}, sourceUrl, notes, _source}`

**3. `data/MASTER/seed_family_offices_ALL_2026-05-07.json`** — 63 family offices QC (32) + ON (31)
- 49% avec courriel, 63% téléphone, 38% LinkedIn
- Schéma : `{name, organization, title, region, city, language, investmentThesis, approachAngle, ticketRange{min,max}, publicContact{email,phone,linkedin,website}, sourceUrl, notes, _source}`

**4. `data/MASTER/MASTER_capital_norvex_2026-05-07.json`** — TOUT en un seul fichier (vue d'ensemble)

## Filtres déjà appliqués

- ✅ TIER ZERO exclus : Daoust, Boivin, Saputo (tous), Jolina, Italcan, Drouin/Finstar, Peter Quinn (déjà partenaire)
- ✅ Déduplication globale par (nom + firme/companyName/organization)
- ✅ Sources publiques uniquement, AUCUN courriel inventé
- ✅ Champ `_source` sur chaque entrée pour traçabilité (qc_brokers_vague1, qc_brokers_vague2, ontario_brokers, qc_promoters, ontario_promoters, qc_family_offices, ontario_family_offices)

## Tâches à exécuter

### 1. Valider les schémas Firestore
Vérifie que `data/firestore_schema.md` accepte les nouveaux champs :
- `city` (brokers, promoters, family_offices)
- `title` (brokers, family_offices)
- `publicContact{email,phone,linkedin,profile_url,website}` (objet groupé)
- `sourceUrl` (toutes collections — pour audit)
- `subregion`, `score`, `projectTypesDetail` (promoters)
- `language`, `investmentThesis`, `approachAngle`, `ticketRange{min,max}`, `organization` (family_offices)
- `_source` (toutes collections — pour traçabilité)

Si la collection `family_offices` n'existe pas dans Firestore, propose la créer.

### 2. Adapter les scripts seed (si nécessaire)
Vérifie / adapte :
- `agents/courtiers/seed_initial_brokers.py` pour lire le nouveau format
- `agents/promoteurs/seed_initial_promoters.py` pour lire le nouveau format
- Crée `agents/capital/seed_initial_family_offices.py` si pas existant

### 3. Dry-run ingestion (NE PAS écrire à Firestore)

```bash
python -m agents.courtiers.seed_initial_brokers \
    --input data/MASTER/seed_brokers_ALL_2026-05-07.json --dry-run

python -m agents.promoteurs.seed_initial_promoters \
    --input data/MASTER/seed_promoters_ALL_2026-05-07.json --dry-run

python -m agents.capital.seed_initial_family_offices \
    --input data/MASTER/seed_family_offices_ALL_2026-05-07.json --dry-run
```

Montre-moi un échantillon des 5 premières entrées de chaque type telles qu'elles seraient écrites à Firestore. **Ne PAS écrire tant que je n'ai pas validé.**

### 4. Préparer outreach Tier 1

Une fois validé, prépare 3 listes priorisées pour `agents/*/outreach.py` :

**Brokers Tier 1** (à attaquer en premier) :
- QC : Patrice Ménard (PMML), Jeffrey Soliman (VA Capital), Michel Durand (MCommercial), Jonathan Gagnon (Orbis), Cédric Lévesque (Lévesque & Cie), Denis Gagné Nadeau (Multilogements.ca)
- ON : Norman Arychuk (Avison Young), Daniel Vyner (DV Capital), Steve Kates (Northwood), Omid Jalili (OMJ), Jonah Brown (Oakbank)

**Promoteurs Tier 1** (score 8, volume 1B$+) :
- QC : Groupe Mach (info@groupemach.com), Devimco, Brivia, Cogir, Carbonleo, Pomerleau, Groupe Maurice, Groupe Sélection
- ON : Tridel (ask@tridel.com), KingSett Capital, Daniels, Mattamy, Cadillac Fairview, RioCan, SmartCentres, H&R, Oxford Properties

**Family Offices Tier 1** (avec emails publics confirmés) :
- QC : Sagard (info@sagardholdings.com), Claridge (info@claridgeinc.com), Trottier Foundation (info@trottierfoundation.com), TC Transcontinental (communications@tc.tc)
- ON : Kilmer Group (info@kilmergroup.com), Onex (investor@onex.com), Dancap (info@dancap.ca), Thomvest (info@thomvest.com), Northwood Family Office, Picton Mahoney, Tacita, Our Family Office, Prime Quadrant, Dundee, Cardinal, Hillsdale

### 5. Identifier les orphelins

29 entrées n'ont aucun courriel/téléphone/LinkedIn. Génère une liste pour LinkedIn outreach manuel ou recherche complémentaire :
- 1 broker orphelin
- 10 promoteurs orphelins
- 18 family offices orphelins (la plupart sont des FO ultra-privés par design : Telesystem, Palomino, MAVRIK, Wittington, Foster, Walia)

## Limites connues à respecter

- Ne JAMAIS inventer un courriel — utiliser les outreach via téléphone ou LinkedIn pour les entrées sans email
- Les family offices ultra-privés requièrent introduction CAFA / réseau, pas cold outreach
- Vérifier les numéros AMF (lautorite.qc.ca) et FSRA avant de marquer un broker comme "verified"

## Question-réponse attendue

Quand t'as fini, dis-moi :
1. Combien d'entrées ont effectivement été écrites à Firestore en dry-run
2. Quels champs schéma j'ai dû ajouter
3. Échantillon de 5 entrées de chaque type comme Firestore les verrait
4. Plan proposé pour la première vague d'outreach (cibles + canal recommandé)

Merci.

===== FIN =====

---

## Note sur le format de référence

Si Claude Code te demande quoi faire dans le détail, voici le contenu d'une entrée broker exemple :

```json
{
  "name": "Patrice Ménard",
  "firmName": "PMML",
  "licenseNumber": "",
  "region": "QC",
  "city": "Montréal",
  "specialty": ["multilogement", "commercial", "industriel", "construction"],
  "title": "Président & Fondateur, Courtier Commercial",
  "typicalDealSize": {"min": 1000000, "max": 50000000},
  "relationshipStatus": "cold",
  "dealsReceived": 0,
  "dealsClosed": 0,
  "preferredChannel": "email",
  "publicContact": {
    "email": "info@pmml.ca",
    "phone": "514-360-3603",
    "linkedin": "https://www.linkedin.com/in/patricemenardpmml/",
    "profile_url": "https://pmml.ca/en/home"
  },
  "sourceUrl": "https://pmml.ca/en/",
  "notes": "Fondée 2008. 160+ pros, 100+ courtiers commerciaux/hypothécaires. 6B$+ transactions/an. 9 bureaux QC. Spécialité 5+ unités.",
  "_source": "qc_brokers_vague1"
}
```
