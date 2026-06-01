# HANDOFF — Recherche 7 mai 2026 → Claude Code

**Pour :** Claude Code
**De :** Claude (Cowork) + Yves Barrette
**Mission :** Phase 2 prospection Capital Norvex — Ontario (3 fichiers) + QC vague 2 brokers

---

## TL;DR

**4 fichiers JSON livrés** dans `data/research-2026-05-07/` :

| Fichier | Cible | Cible volume | Livré | Schéma |
|---|---|---|---|---|
| `seed_ontario_brokers_2026-05-07.json` | ON commercial mortgage brokers + debt advisory | 150-250 | **27** | `brokers` |
| `seed_ontario_promoters_2026-05-07.json` | ON real estate developers | 100-150 | **44** | `promoters` |
| `seed_ontario_family_offices_2026-05-07.json` | ON family offices + MFOs | 50-80 | **32** | `familyOffices` |
| `seed_qc_brokers_vague2_2026-05-07.json` | QC commercial mortgage brokers vague 2 | 500-800 | **45** | `brokers` |
| **TOTAL** | | **800-1280** | **148** | |

**Volumes sous-cible.** Limitation principale : la recherche web publique ne donne pas accès aux registres FSRA / AMF en bulk, ni aux rosters complets des firmes (la plupart n'affichent qu'un sous-ensemble de leurs courtiers commerciaux). Atteindre les volumes cibles nécessite : (a) Hunter.io / Apollo.io payants pour enrichir, (b) scraping autorisé des pages "Notre équipe", (c) achats de listes professionnelles (CMBA, OMBA membership), ou (d) introduction via réseau.

---

## TIER ZERO appliqué (mis à jour vague 2)

Filtres actifs :
- Daoust, Boivin
- Famille Saputo (Lino, Joey, Francesco), Saputo Inc.
- Jolina Capital, Gestion Jolina, Placements Italcan
- **Drouin / Finstar (séquestre)** — nouveau vague 2
- **Peter Quinn (Multi-Prêts Commercial)** — déjà partenaire, exclu vague 2

Total rejetés : 0 (les TIER ZERO ne sont pas dans les segments recherchés).

---

## Schémas confirmés

### `brokers` (fichiers 1 + 4)

```json
{
  "_meta": {
    "description": "...", "version": 1, "created": "2026-05-07",
    "researcher": "Claude (Cowork)",
    "filtres_appliques": {
      "tier_zero_filter": "OUI", "deduplication": "OUI", "tier_zero_rejected": 0
    }
  },
  "brokers": [
    {
      "name": "Prénom Nom",
      "firmName": "Nom firme",
      "licenseNumber": "",
      "region": "ON" | "QC",
      "city": "Toronto",
      "specialty": ["multilogement", "commercial", "construction"],
      "title": "Titre exact",
      "typicalDealSize": {"min": 1000000, "max": 30000000},
      "relationshipStatus": "cold",
      "dealsReceived": 0,
      "dealsClosed": 0,
      "preferredChannel": "email" | "linkedin" | "phone",
      "publicContact": {
        "email": "", "phone": "", "linkedin": "", "profile_url": ""
      },
      "sourceUrl": "https://...",
      "notes": "Contexte court"
    }
  ]
}
```

### `promoters` (fichier 2)

```json
{
  "_meta": { ... },
  "promoters": [
    {
      "name": "Prénom Nom" | "à identifier",
      "companyName": "...",
      "region": "ON",
      "city": "Toronto",
      "subregion": "GTA",
      "projectTypes": ["multilogement", "commercial", "mixte"],
      "projectTypesDetail": ["condo", "résidentiel", "bureau"],
      "recentProjects": "Projet X (2024); Projet Y (2023)",
      "estimatedAnnualVolume": null | <int>,
      "relationshipStatus": "researching",
      "score": 5 | 6 | 7 | 8,
      "contactInfo": {
        "email": "", "phone": "", "website": "", "linkedin": "",
        "contact_person": "..."
      },
      "sourceUrl": "https://...",
      "notes": "..."
    }
  ]
}
```
Score : 5=base, 6=200M+, 7=500M+, 8=1B+

### `familyOffices` (fichier 3)

```json
{
  "_meta": { ... },
  "familyOffices": [
    {
      "name": "Prénom Nom" | "à identifier",
      "organization": "...",
      "title": "Principal | CEO | Founder | ...",
      "region": "ON",
      "city": "Toronto",
      "language": "en",
      "investmentThesis": "1 phrase",
      "approachAngle": "1 phrase angle d'approche personnalisé",
      "ticketRange": {"min": 1000000, "max": 50000000},
      "publicContact": {
        "email": "", "phone": "", "linkedin": "", "website": ""
      },
      "sourceUrl": "https://...",
      "notes": "Contexte famille / wealth source / signaux"
    }
  ]
}
```

---

## Caveats par fichier

### Fichier 1 — ON brokers (27)
- 4 entrées sont des **lenders/funds** (Trez Capital - Eric Horie, Peakhill Capital - Harley Gold/Isabel Lontoc, MCAP - Leo St. Germain, CMLS - Paul Fallone) : ils peuvent référer mais ce ne sont pas des courtiers traditionnels. Flagger comme `relationshipStatus: "cold"` et noter dans `notes`.
- Hendrik Zessel (Cushman) apparaît aussi dans le fichier QC du 6 mai (couvre tout Canada). Doublon volontaire entre fichiers QC/ON.
- Capital Markets desks (CBRE, JLL, C&W, Avison Young, Colliers) : profils Toronto cherchent surtout des deals **>10M$**. Pour deals 1-3M$ Capital Norvex, privilégier les boutiques (OMJ, GreenBirch, Oakbank, DV Capital, Northwood, CYR).

### Fichier 2 — ON promoteurs (44)
- 27 entrées avec `name: "à identifier"` (le nom du président/CEO n'est pas affiché publiquement sur le site corporatif). À enrichir via LinkedIn outreach.
- Tous les `estimatedAnnualVolume` sont `null` (les promoteurs publient rarement leur volume annuel en $; les chiffres connus comme "8000 homes/an" ne convertissent pas proprement en volume $).
- Score calé sur taille apparente : 6=régional, 7=majeur, 8=1B$+ AUM ou volume.

### Fichier 3 — ON family offices (32)
- Beaucoup de FO sont privés par nature. La plupart des `email` et `linkedin individuel` sont vides.
- Pour outreach : passer par CAFA membership, Canadian Family Office events, ou introductions du réseau Northwood/Prime Quadrant/Our Family Office (les 3 plus gros MFO).
- 4 entrées sont des **wealth managers HNW**, pas des FO purs (Canaccord, Richardson, Jarislowsky, Hillsdale) — utile pour referrals mais pas pour deals directs.

### Fichier 4 — QC brokers vague 2 (45)
- **Tous noms exclus de la vague 1 du 6 mai.**
- ~20 brokers Colliers/Cushman MTL : ce sont des Capital Markets brokers, sweet spot 5M-50M$. Pour deals plus petits Capital Norvex (1-3M$), pas idéal.
- ~15 brokers IMERIS : franchise DLC très active QC, multi-bureaux (MTL, Laval, Montérégie, Laurentides, Outaouais). Sweet spot 500K-25M, parfait fit.
- ~8 brokers PMML : déjà 1 entrée Patrice Ménard en vague 1; ajout équipe complète ici.
- Pour atteindre 500-800, il faudrait scraper individuellement les pages "Notre équipe" de chaque firme et faire des recherches LinkedIn par mot-clé "courtier hypothécaire commercial" + "Québec".

---

## Tâches suggérées Claude Code

### 1. Ingestion dry-run

```bash
# Validation schéma + dry-run sans écrire à Firestore
python -m agents.courtiers.seed_initial_brokers \
    --input data/research-2026-05-07/seed_ontario_brokers_2026-05-07.json \
    --dry-run

python -m agents.courtiers.seed_initial_brokers \
    --input data/research-2026-05-07/seed_qc_brokers_vague2_2026-05-07.json \
    --dry-run

python -m agents.promoteurs.seed_initial_promoters \
    --input data/research-2026-05-07/seed_ontario_promoters_2026-05-07.json \
    --dry-run

# Pour familyOffices, créer si nécessaire un nouveau seed_initial_family_offices.py
# (pas dans la base actuelle de tes scripts)
python -m agents.capital.seed_initial_family_offices \
    --input data/research-2026-05-07/seed_ontario_family_offices_2026-05-07.json \
    --dry-run
```

### 2. Adaptations probables

- **Étendre schéma Firestore** pour accueillir `city`, `title`, `publicContact`, `sourceUrl`, `subregion`, `score`, `language`, `investmentThesis`, `approachAngle`, `ticketRange`, `organization`
- **Créer collection `familyOffices`** si pas déjà existante (vérifier `data/firestore_schema.md`)
- **Mapper `region: "ON"` vs `region: "QC"`** dans agent CAPITAL pour le routing des outreach campaigns

### 3. Enrichissement (Phase 3 suggérée)

Pour combler le gap sur les volumes cibles :
- **Hunter.io / Apollo.io** : enrichir les courriels manquants (~80% des entrées)
- **LinkedIn Sales Navigator** : trouver les noms manquants pour les 27 promoteurs ON "à identifier"
- **AMF lookup individuel** : valider les `licenseNumber` des courtiers QC actifs (visite individuelle de lautorite.qc.ca)
- **FSRA Mortgage Broker Search** : valider les courtiers ON
- **CAFA member directory** (membres only) : compléter family offices ON

### 4. Pipelines de prospection à lancer

Une fois ingéré + validé :
- `agents/courtiers/outreach.py` → première vague Tier 1 (5-7 brokers ON priorité)
- `agents/promoteurs/outreach.py` → top 10 promoteurs ON (Tier 1 score 8)
- `agents/capital/outreach.py` → top 10 family offices ON (Tanenbaum, Weston, Reichmann, Schwartz, Forest Hill Capital pour multifamily fit)

---

## Recommandations de priorité (Tier 1 par fichier)

### Tier 1 — Ontario brokers (5 champions à attaquer en premier)
1. **Norman Arychuk (Avison Young Toronto)** — 30+ ans, structure deals 100M$+
2. **Daniel Vyner (DV Capital)** — boutique, sweet spot 1-25M$ private financing
3. **Steve Kates (Northwood Mortgage)** — 50+ ans expérience cumulée, 100+ agents
4. **Omid Jalili (OMJ Mortgage Capital)** — 20+ ans commercial, 6 ans CMP Top Brokers finalist
5. **Jonah Brown (Oakbank Capital)** — Co-Founder 2022, 6.5B$+ loans arrangés Canada

### Tier 1 — Ontario promoteurs (Top 5 à approcher)
1. **Tridel** — plus grand condo builder GTA (90 000 unités)
2. **KingSett Capital** — 12.5B$ equity, vient d'acquérir First Capital (9.4B$)
3. **Daniels Corporation** — Regent Park revitalization model
4. **Mattamy Asset Management (Peter Gilgan)** — plus grand single-family builder Canada
5. **Centurion Apartment REIT** — plus grand REIT apt privé Canada (7.8B$ AUM, ON focus)

### Tier 1 — Ontario family offices (Top 5 à approcher)
1. **Michael Domb (Forest Hill Capital)** — match parfait : multifamily transit-oriented Toronto
2. **Lawrence Tanenbaum (Kilmer Group)** — 20B$ AUM, RE prouvé
3. **Aubrey Dan (Dancap)** — 3.9B$, private debt expertise
4. **Tom McCullough (Northwood Family Office)** — porte d'entrée à 500+ familles UHNW
5. **Albert Soberano (Sharno Group)** — focus GTA multifamily + commercial 2-20M$ tickets

### Tier 1 — QC brokers vague 2 (boutiques avec haut potentiel)
1. **Henri Zacharie (MCommercial)** — Senior Executive Director, deals 3-50M$
2. **Patrick Girard / Guillaume Menouret (Performance Hypothécaire)** — 32 ans expérience banque commerciale
3. **Catherine St-Pierre (Lévesque & Cie)** — équipe Cédric Lévesque (multilogement spécialisé)

---

## Fin du handoff

Tous les fichiers sont conformes aux schémas exacts définis. Si tes scripts seed plantent, vérifie d'abord :
1. Que la collection Firestore accepte les champs étendus
2. Que `region` filter ON vs QC est implémenté
3. Que les valeurs `score` sont int 5-8 (pas string)
4. Que `ticketRange` accepte `{min, max}` int
5. Que `relationshipStatus` accepte `"cold"` (brokers) et `"researching"` (promoters)

Bonne chasse Claude Code.
