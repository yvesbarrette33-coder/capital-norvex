# Capital Norvex — Norvex Agents™ v1

**Version :** v1.0 (squelette) — 30 avril 2026
**Auteur :** Yves Barrette + Claude Code
**Statut :** Code en place. **Aucun déploiement effectué.**

---

## 🎯 But

Trois agents IA opérationnels qui travaillent **uniquement sous l'approbation d'Yves** :

| Agent | Mission | Cibles |
|---|---|---|
| **CAPITAL** | Recruter des family offices QC + ON | Lettres premium + dossiers PDF |
| **COURTIERS** | Activer le réseau de courtiers commerciaux | Deal cards mensuelles + suivis |
| **PROMOTEURS** (v0) | Identifier les promoteurs en besoin | Squelette seulement, v1 prévu 7 mai |

Tous orchestrés (à terme) par **Norvex Brain** (`agents/brain/`).

---

## 🛡️ Règles d'or — verrouillées dans le code

| ID | Règle | Où ? |
|---|---|---|
| **R-BRAND-1** | Logo officiel `assets/logo-norvex-officiel.png` — JAMAIS recréé en SVG | `agents/shared/email_template.py` |
| **R-TIER-ZERO** | Daoust / Boivin / Saputo / Jolina invisibles aux 3 agents | `agents/shared/tier_zero_guard.py` + `data/tier_zero.json` |
| **R-APPROVAL** | Aucun envoi sans `status=approved` | `agents/shared/approval_workflow.py` |
| **R-VIRGIN** | Cibles Capital vierges → aucune référence aux autres business | logique dans `letter_generator.py` |
| **R-AUDIT** | Toute action loggée dans `agentAuditLog` | `audit_log()` dans `firestore_client.py` |
| **R-CADENCE** | Capital max 5/sem, Courtiers max 2/mois, Promoteurs cool-down 6 mois | enforcement dans `monthly_workflow.py` + `check_existing_client.py` |
| **R-TEMPLATE** | Tous les courriels = Variation A (crème/encre/or, Georgia 13.5px) | `email_template.py` + `templates/email_variation_a.html` |

---

## 📁 Structure

```
capitalnorvex-site/
├── assets/
│   └── logo-norvex-officiel.png        ← logo officiel (R-BRAND-1)
├── data/
│   ├── tier_zero.json                  ← R-TIER-ZERO (modifiable par Yves)
│   ├── seed_targets.json               ← 10 cibles FICTIVES (à remplacer)
│   └── seed_brokers.json               ← 5 courtiers FICTIFS (à remplacer)
├── templates/
│   └── email_variation_a.html          ← référence design Variation A
├── agents/
│   ├── requirements.txt                ← deps Python pour les agents
│   ├── tests_smoke.py                  ← smoke tests sans Firestore
│   ├── shared/
│   │   ├── auth.py                     ← Graph token + Firebase Admin
│   │   ├── firestore_client.py         ← helpers + audit_log
│   │   ├── tier_zero_guard.py          ← R-TIER-ZERO enforcement
│   │   ├── approval_workflow.py        ← draft → pending → approved → sent
│   │   ├── email_sender.py             ← Graph d'abord, SendGrid fallback
│   │   └── email_template.py           ← Variation A render
│   ├── capital/
│   │   ├── target_research.py          ← recherche profonde via Claude API
│   │   ├── approach_dossier.py         ← PDF dossier 2-4 pages (reportlab)
│   │   ├── letter_generator.py         ← drafte lettre premium → pending
│   │   ├── seed_initial_targets.py     ← script one-shot (charge seed)
│   │   └── daily_brief.py              ← section Capital du brief
│   ├── courtiers/
│   │   ├── broker_finder.py
│   │   ├── deal_cards_generator.py
│   │   ├── relationship_manager.py
│   │   ├── seed_initial_brokers.py
│   │   └── monthly_workflow.py
│   ├── promoteurs/                     ← v0 — squelette
│   │   ├── seed_initial_promoters.py
│   │   ├── email_template.py
│   │   └── check_existing_client.py
│   └── brain/
│       └── daily_brief.py              ← orchestrateur 7h00 EST
├── capital-norvex-agents.html          ← UI dédié 3 onglets (NOUVEAU)
├── capital-norvex-pipeline.html        ← inchangé
├── firestore.rules                     ← MAJ avec nouvelles collections
└── firestore.rules.backup-2026-04-30-AVANT-AGENTS  ← backup
```

---

## 🚀 Comment lancer

### 1. Installer les dépendances Python (une fois)

```bash
cd ~/Desktop/capitalnorvex-site
pip install -r agents/requirements.txt
```

### 2. Vérifier que les variables d'environnement sont prêtes

Le `.env` existant dans `Capital Norvex/agent/.env` doit contenir :
- `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`
- `MAIL_USER` (= `info@capitalnorvex.com`)
- `ANTHROPIC_API_KEY`
- `SENDGRID_API_KEY` (fallback)
- `GOOGLE_APPLICATION_CREDENTIALS` (clé JSON service account Firebase) — **à ajouter si manquant**

### 3. Smoke tests (sans Firestore — sécuritaire)

```bash
cd ~/Desktop/capitalnorvex-site
python -m agents.tests_smoke
```

### 4. Déploiement Firestore rules (après validation)

```bash
firebase deploy --only firestore:rules
```

### 5. Charger les données seed (en mode dry-run d'abord)

```bash
# DRY-RUN — montre ce qui serait créé sans rien écrire
python -m agents.capital.seed_initial_targets --dry-run
python -m agents.courtiers.seed_initial_brokers --dry-run

# Pour vrai (écrit dans Firestore) — décide après revue
python -m agents.capital.seed_initial_targets
python -m agents.courtiers.seed_initial_brokers
```

### 6. Brief matinal (test)

```bash
# Prévisualise sans envoyer (écrit data/brief_preview.html)
python -m agents.brain.daily_brief --dry-run

# Envoie pour de vrai à yvesbarrette33@gmail.com
python -m agents.brain.daily_brief
```

---

## 👀 Comment auditer

Toutes les actions des agents passent par `audit_log()` qui écrit dans **Firestore → `agentAuditLog`**.

Champs : `timestamp`, `agent`, `action`, `targetType`, `targetId`, `result`, `details`.

Yves peut consulter via la console Firebase ou via l'UI `capital-norvex-agents.html` (à étendre).

---

## ➕ Comment ajouter une cible TIER ZERO

Modifier `data/tier_zero.json` directement — ajouter un objet dans `protected_individuals` :

```json
{
  "name": "Nouveau Nom",
  "added": "2026-05-XX",
  "added_by": "Yves Barrette",
  "reason": "Pourquoi protégé",
  "aliases": [],
  "known_emails": [],
  "known_organizations": []
}
```

Le cache se rafraîchit automatiquement chaque heure, ou immédiatement via `tier_zero_guard.invalidate_cache()`.

---

## ⚠️ Ce qui n'est PAS encore fait

1. **Firestore rules : non déployées.** Il faut `firebase deploy --only firestore:rules` après revue d'Yves.
2. **Seed Firestore : pas chargé.** Les `seed_*.json` sont fictifs ; il faut soit y mettre de vraies données, soit lancer en dry-run pour voir l'effet.
3. **Données réelles : à fournir par Yves** (100 cibles Capital, 30-50 courtiers, 10 promoteurs).
4. **Cron du brief matinal : pas planifié.** Doit être exécuté manuellement ou via cron Mac (`launchd`) ou hébergé.
5. **Pipeline UI** : la nouvelle page `capital-norvex-agents.html` est **séparée** du pipeline existant pour zéro risque. Intégration ultérieure quand les données réelles seront en place.
6. **`broker_finder.identify_brokers()`** : utilise l'API Claude web search ; pas branché à un cron pour l'instant.
7. **Promoteurs v1** : scraping permis municipaux + Constructo + JBC + scoring IA → **mercredi 7 mai**.

---

## 🔁 Rollback

Tout est réversible :

- Restaurer firestore.rules : `cp firestore.rules.backup-2026-04-30-AVANT-AGENTS firestore.rules`
- Supprimer `agents/`, `data/`, `templates/`, `capital-norvex-agents.html` : aucune dépendance avec le pipeline existant.
- Backup complet du projet avant agents : `~/Desktop/capitalnorvex-site-BACKUP-2026-04-30-AVANT-AGENTS/`

---

## 📞 Adresse officielle (intégrée dans tous les courriels)

> Capital Norvex Inc.
> 2705-1000 André-Prévost
> Île-des-Sœurs (Verdun)
> Montréal, QC H3E 0G2
> Tél : 514-NORVEX-1 · info@capitalnorvex.com
