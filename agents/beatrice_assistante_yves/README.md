# Béatrice — Assistante exécutive d'Yves Barrette

Agent interne (USAGE INTERNE UNIQUEMENT — Brain dashboard) qui surveille
`yves@capitalnorvex.com`, trie les courriels entrants, et rédige des
réponses en **GHOSTWRITER PUR** au nom d'Yves Barrette.

> Le destinataire ne voit jamais "Béatrice". Tous drafts sont signés
> "Yves Barrette, Directeur-Fondateur" via la signature DARK officielle.

## Architecture

| Composant | Rôle |
|-----------|------|
| `config.py` | Modèles, mailboxes, mutex Camille, détection perso |
| `system_prompts.py` | Triage Sonnet + Drafting Opus (voix Yves) |
| `triage.py` | Sonnet 4.6 → JSON `{category, priority, language, ...}` |
| `drafting.py` | Opus 4.6 + adaptive thinking → JSON draft + signature Yves |
| `audit.py` | Firestore (`beatriceEmails`, `beatriceDrafts`) + notif Yves HMAC |
| `orchestrator.py` | Pipeline complet : Graph → dédup → triage → draft → notif |
| `__main__.py` | CLI |
| `tests_smoke.py` | 6 tests sans réseau |

## Coordination Camille ↔ Béatrice (sur yves@)

- **Camille** a `legal_only_filter: True` sur `yves@`. Elle traite uniquement
  le juridique (notaires QC, avocats QC, solicitors ON, RDPRM).
- **Béatrice** traite TOUT LE RESTE non-juridique non-personnel sur `yves@`.
- **Mutex sémantique** : Béatrice skip automatiquement les catégories
  réservées à Camille (`is_legal_reserved_for_camille`).
- **Dédup Message-ID** : si Camille (ou Sophie) a déjà traité l'email
  (collections `camilleEmails` / `sophieEmails`), Béatrice skip.

## Règles ghostwriter

- ❌ JAMAIS le mot "Béatrice" dans le corps ou la signature des drafts produits
- ❌ JAMAIS "IA", "assistante", "outil", "automatisation"
- ✅ Signature unique : `signature_yves(language)` (style DARK officiel)
- ✅ Voix Yves : Stikeman / BlackRock / Brookfield, FR québécois soutenu / EN canadien neutre
- ✅ Garde-fous AMF : jamais "investisseur", toujours "partenaire"
- ✅ Aucun engagement de taux/montant exact (fourchettes seulement)

## Autonomie

- **Niveau** : MOYEN
- **`autoSendSafe`** : forcé à `False` côté triage. Yves approuve chaque envoi.
- **Workflow** : email entrant → triage → draft Opus → store Firestore → notif
  Yves avec 3 boutons HMAC (Approuver / Modifier / Rejeter) → action humaine.

## CLI

```bash
# Pipeline complet (25 derniers non-lus)
python -m agents.beatrice_assistante_yves run

# 50 derniers
python -m agents.beatrice_assistante_yves run --top 50

# Triage seul (pas de drafting)
python -m agents.beatrice_assistante_yves run --no-draft

# Inclure les déjà-lus
python -m agents.beatrice_assistante_yves run --all

# Marquer lus après drafting
python -m agents.beatrice_assistante_yves run --mark-read
```

## Tests smoke

```bash
cd ~/Desktop/capitalnorvex-site
python3 -m agents.beatrice_assistante_yves.tests_smoke
```

Tests : imports, config, signature ghostwriter (FR+EN), system prompts,
triage parse JSON, drafting append signature.

## Variables d'environnement requises

- `ANTHROPIC_API_KEY` — clé Anthropic (Sonnet + Opus)
- `CAMILLE_HMAC_SECRET` — secret HMAC partagé (≥16 chars)
- `SITE_URL` — base URL site (défaut : `https://capitalnorvex.com`)
- `CAMILLE_APPROVAL_INBOX` — boîte d'approbation Yves (défaut : `yves@capitalnorvex.com`)
- Variables Microsoft Graph (déjà configurées via `~/.capitalnorvex/.env`)

## Firestore — collections

- `beatriceEmails` : emails entrants triés
- `beatriceDrafts` : drafts produits + statut (`pending_yves_approval`,
  `sent`, `rejected`)
- `auditLogs` : log d'actions agent (commun à tous les agents)

## Cron (à activer)

```bash
# Wrapper :
~/.capitalnorvex/scripts/beatrice_run.sh --top 25

# Plist launchd (10 min) :
cp scripts/com.capitalnorvex.beatrice.plist ~/Library/LaunchAgents/
launchctl load -w ~/Library/LaunchAgents/com.capitalnorvex.beatrice.plist
```

## Reste à faire (hors scope build initial)

- Endpoints Netlify : `/api/beatrice-approve`, `/api/beatrice-reject`,
  `/api/beatrice-modify` (réutiliser `_camille-shared.mjs` pour la
  vérification HMAC)
- Dashboard `/beatrice-admin.html` (calque `/sophie-admin.html`)
- Activation launchctl du plist
- Décision : tile Brain pour Béatrice (onglet "Assistante exécutive")
