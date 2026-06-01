# HANDOFF — Recherche 6 mai 2026 → Claude Code

**Pour :** Claude Code
**De :** Claude (Cowork) + Yves Barrette
**Objet :** Données de prospection prêtes à charger dans Firestore

---

## TL;DR

Deux fichiers JSON conformes aux schémas existants sont prêts dans ce dossier :

| Fichier | Cibles | Format |
|---|---|---|
| `seed_mortgage_brokers_2026-05-06.json` | **48 courtiers hypothécaires commerciaux** QC | Conforme `data/seed_brokers.json` |
| `seed_promoters_RECHERCHE_2026-05-06.json` | **58 promoteurs immobiliers** QC | Conforme `firestore_schema.md > promoters` |

Les fichiers `_DEPRECATED_*` sont à ignorer/supprimer (recherche initiale erronée — courtiers de vente au lieu de hypothécaires).

---

## Contexte

Capital Norvex Inc. = société de financement / prêteur hypothécaire commercial à Montréal.
Deals typiques : multilogement / construction / commercial 1M-30M$.

Trois agents IA en place :
- **CAPITAL** — recrute family offices QC + ON
- **COURTIERS** — recrute courtiers hypothécaires commerciaux qui réfèrent du financement
- **PROMOTEURS** — recrute promoteurs immobiliers qui cherchent du financement

---

## Schéma JSON livré

### Courtiers hypothécaires (`seed_mortgage_brokers_2026-05-06.json`)

```json
{
  "_meta": { "version": 2, "created": "2026-05-06", ... },
  "brokers": [
    {
      "name": "Patrice Ménard",
      "firmName": "PMML",
      "licenseNumber": "",                  // À valider via AMF Québec
      "region": "QC",
      "city": "Montréal",                   // ✨ ajouté vs schéma original
      "specialty": ["multilogement", "commercial", "industriel", "construction"],
      "title": "Président & Fondateur",     // ✨ ajouté
      "typicalDealSize": {"min": 1000000, "max": 50000000},
      "relationshipStatus": "cold",
      "dealsReceived": 0,
      "dealsClosed": 0,
      "preferredChannel": "email",
      "publicContact": {                    // ✨ ajouté (regroupe contacts publics)
        "email": "info@pmml.ca",
        "phone": "514-360-3603",
        "linkedin": "https://...",
        "profile_url": "https://..."
      },
      "sourceUrl": "https://...",           // ✨ ajouté (pour audit)
      "notes": "..."
    }
  ]
}
```

**Champs ajoutés vs `data/seed_brokers.json` original :**
- `city` (string)
- `title` (string)
- `publicContact` (object — regroupe email/phone/linkedin publics)
- `sourceUrl` (string — URL où l'info a été trouvée)

**À FAIRE côté code :**
- Si Firestore exige le schéma exact original, mapper :
  - `publicContact.email` → champ root `email` (ou `contactEmail`)
  - Reste idem
- Sinon, étendre le schéma Firestore pour accueillir les nouveaux champs (recommandé : utiles pour audit/conformité)

### Promoteurs (`seed_promoters_RECHERCHE_2026-05-06.json`)

```json
{
  "_meta": { "version": 1, "created": "2026-05-06", ... },
  "promoters": [
    {
      "name": "Vincent Chiara",            // Personne (président/CEO) si trouvée
      "companyName": "Groupe Mach",
      "region": "QC",
      "city": "Montréal",
      "subregion": "Grand Montréal",
      "projectTypes": ["multilogement", "commercial"],     // Types simplifiés
      "projectTypesDetail": ["multilogement", "commercial", "bureau", "mixte", "résidentiel"],
      "recentProjects": "Quartier des Lumières (2024); Sun Life Building (2023)",
      "estimatedAnnualVolume": 2500000000,
      "relationshipStatus": "researching",
      "score": 8,                          // 5=base, 6=200M+, 7=500M+, 8=1B+
      "contactInfo": {
        "email": "info@groupemach.com",
        "phone": "+1-514-374-6224",
        "website": "https://www.groupemach.com/en",
        "linkedin": "https://...",
        "contact_person": "Vincent Chiara, Founder & President"
      },
      "sourceUrl": "https://...",
      "notes": "..."
    }
  ]
}
```

---

## Filtres déjà appliqués

✅ **TIER ZERO** : Daoust, Boivin, Saputo (tous), Jolina, Italcan exclus
✅ **Déduplication** : par `(name, firmName)` pour brokers, `(name, companyName)` pour promoters
✅ **Sources publiques uniquement** : pas de scraping privé, pas de courriels inventés

---

## Tâches suggérées pour Claude Code

### Tâche 1 — Dry-run ingestion
```bash
# Tester la lecture du fichier sans écrire à Firestore
python -m agents.courtiers.seed_initial_brokers \
    --input data/research-2026-05-06/seed_mortgage_brokers_2026-05-06.json \
    --dry-run

python -m agents.promoteurs.seed_initial_promoters \
    --input data/research-2026-05-06/seed_promoters_RECHERCHE_2026-05-06.json \
    --dry-run
```

### Tâche 2 — Adapter les scripts seed si schéma diffère
Vérifier que les scripts `seed_initial_*.py` lisent bien :
- Champs additionnels : `city`, `title`, `publicContact`, `sourceUrl`, `subregion`, `score`
- Si oui : nouveau seed enrichi
- Si non : ajouter mapper / étendre schéma Firestore

### Tâche 3 — Filtrer doublons avec base existante
Avant ingestion, comparer avec ce qui est déjà dans Firestore :
- Si un broker/promoter existe déjà → préserver `relationshipStatus`, `dealsReceived`, `dealsClosed`
- Sinon → créer nouveau document

### Tâche 4 — Activer pipelines de prospection
Une fois chargés :
- `agents/courtiers/outreach.py` — pour envoyer la première vague (respecter rules d'or, audit, approbation)
- `agents/promoteurs/outreach.py` — idem
- `agents/capital/target_research.py` — enrichir chaque cible avec triggers récents (financements, deals, signaux liquidity event)

### Tâche 5 — Phase 2 (à demander)
- Recherche **Ontario** pour aligner avec cible CAPITAL QC + ON
- Enrichissement courriels via Hunter.io / Apollo.io / formulaires de contact
- Recherche **family offices QC + ON** (cible CAPITAL = 100 contacts) — non couvert dans cette livraison

---

## Validations recommandées avant production

1. **AMF Québec** — valider numéros de licence des courtiers via [registre public](https://lautorite.qc.ca/grand-public/registres)
2. **Yves valide** Tier 1 manuellement (les 7 champions potentiels listés dans `README_COURTIERS_HYPOTHECAIRES_2026-05-06.md`)
3. **TIER ZERO refresh** — refaire le filtre si Yves ajoute des entrées à `data/tier_zero.json`
4. **Vérification email syntax** — certains champs `email` sont génériques (info@firme.ca) — décider si on les utilise ou si on cherche les emails individuels en Phase 2

---

## Prompt suggéré pour Claude Code

```
Lis le fichier data/research-2026-05-06/HANDOFF_CLAUDE_CODE.md.

Ensuite :
1. Lis data/research-2026-05-06/seed_mortgage_brokers_2026-05-06.json et data/research-2026-05-06/seed_promoters_RECHERCHE_2026-05-06.json
2. Vérifie que les schémas correspondent à data/seed_brokers.json et data/firestore_schema.md (collection promoters)
3. Si les schémas Firestore doivent être étendus pour les nouveaux champs (city, title, publicContact, sourceUrl, subregion, score), propose un plan
4. Adapte agents/courtiers/seed_initial_brokers.py et agents/promoteurs/seed_initial_promoters.py pour lire ces nouveaux fichiers
5. Lance un dry-run et montre-moi un échantillon des 5 premiers brokers et 5 premiers promoters tels qu'ils seraient écrits à Firestore
6. Ne PAS écrire à Firestore tant que je n'ai pas validé le dry-run
```

---

## Fichiers à archiver/supprimer (recherche erronée)

- `_DEPRECATED_README_VENTE_2026-05-06.md`
- `_DEPRECATED_courtiers_VENTE_2026-05-06.xlsx`
- `_DEPRECATED_seed_brokers_VENTE_2026-05-06.json`

Ces fichiers contenaient des courtiers immobiliers de **vente** (CBRE, Colliers, Cushman, RE/MAX, Sotheby's…) — pas des courtiers hypothécaires. Erreur de la recherche initiale, corrigée par Yves.

---

**Fin du handoff. Bonne chance Claude Code !**
