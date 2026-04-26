# Capital Norvex — Contexte pour Claude

## Vue d'ensemble

Plateforme de financement hypothécaire commercial. Stack : pages HTML statiques + fonctions Netlify + Firestore + Firebase Storage + un agent Python externe (`agent_docs.py`) qui orchestre les courriels et les analyses.

Domaine de production : **capitalnorvex.com**.

## Architecture des données

**Firestore** (`capital-norvex` project) — source de vérité pour les dossiers
- Collection `dossiers` : un document par demande client. Champs clés : `id`, `stage`, `created_at`, `welcomeEmailSent`, `uploadedDocs`, `docsReady`, `scoreNorvex`, `decision`.
- Pipeline des stages : `nouvelle → analyse → loi → docs → final → notaire → decaisse` (+ `refuse` terminal).

**Firebase Storage** — fichiers uploadés
- `dossier-docs/{dossierID}/...` — documents que les clients envoient via la lettre de bienvenue.
- `score-pdfs/...` — PDFs uploadés sur la page Score Norvex (analyse immédiate).
- Règles publiées : `allow read, write: if true` sur ces deux paths, `if false` partout ailleurs.

**Netlify Blobs** — stores secondaires
- `upload-tokens` : tokens d'upload signés (14 jours).
- `pdfs` : ancien store du Score Norvex (legacy, plus utilisé après migration vers Firebase Storage).

## Fonctions Netlify

Toutes dans `netlify/functions/`. Toutes les fonctions agent sont protégées par `x-internal-secret: NorvexSecret2026`.

| Fonction | Rôle | Auth |
|---|---|---|
| `anthropic.js` | Proxy vers `api.anthropic.com` (compositeur d'e-mails dans `index.html`) | Aucune (clé serveur) |
| `analyze-background.js` | Proxy d'analyse Claude — accepte `pdfKeys` (Blobs), `inlinePdfs` (base64), `storageFiles` (Firebase Storage) | Aucune (clé serveur) |
| `store-pdf.js` | Upload PDF → Blobs `pdfs` (legacy) | Aucune |
| `upload-doc.js` | Upload doc client → Blobs `dossier-docs` (legacy, `upload.html` n'utilise plus ça) | Token |
| `get-token-info.js` | Lit un token d'upload depuis Blobs | Token |
| `create-upload-token.js` | Génère un token + URL `/upload.html?t=XXX` | `x-internal-secret` |
| `register-uploads.js` | Enregistre les chemins Firebase Storage dans Firestore après upload client | Aucune (validation par token) |
| `mark-welcome-sent.js` | Marque `welcomeEmailSent=true` dans Firestore (évite la boucle d'envoi) | `x-internal-secret` |
| `mark-analysis-done.js` | Enregistre Score Norvex + décision + change de stage | `x-internal-secret` |
| `get-new-dossiers.js` | Dossiers à qui envoyer la lettre de bienvenue (stages `nouvelle/analyse/docs` ET `!welcomeEmailSent`) | `x-internal-secret` |
| `get-pending-analysis.js` | Dossiers prêts à scorer (`stage=docs` ET `welcomeEmailSent` ET `!scoreNorvex`) | `x-internal-secret` |
| `list-pending.js` | Tous les dossiers en attente (stages `nouvelle/analyse/docs`) | `x-internal-secret` |
| `get-approved-dossiers.js` | Dossiers approuvés (stages `loi/final/notaire/decaisse`) | `x-internal-secret` |
| `trackAlerts.js` | Alertes internes agent (Blobs) | `x-internal-secret` |
| `submit-analysis.js`, `get-token-info.js` | Système de jobs polling (legacy mais en place) | — |

`netlify/lib/firestore.js` est le wrapper REST API Firestore utilisé par toutes les fonctions agent. Il lit `FIREBASE_API_KEY` ou `FIREBASE_SERVICE_ACCOUNT` (les deux contiennent la clé Web API Firebase, pas un service account JSON).

## Pages HTML

- `index.html` : marketing + formulaire de demande + compositeur d'e-mails (passe par `/anthropic`).
- `capital-norvex-score.html` : analyse Score Norvex. Upload PDF → Firebase Storage `score-pdfs/` → `analyze-background` avec `storageFiles`. Sauvegarde le dossier dans Firestore (`saveToPipeline`).
- `capital-norvex-pipeline.html` : tableau de bord. Lit Firestore en temps réel (sans `orderBy`, tri client-side, montre tous les dossiers même sans `created_at`).
- `capital-norvex-portail-client.html`, `capital-norvex-portail-partenaire.html` : portails authentifiés Firebase Auth.
- `upload.html` : page d'upload client (lien dans la lettre de bienvenue). Token via `?t=XXX`. Upload direct vers Firebase Storage (jusqu'à 500 MB par fichier). Appelle `register-uploads` à la fin pour mettre à jour Firestore.

## Variables d'environnement Netlify

- `ANTHROPIC_API_KEY` — clé Claude (utilisée par `anthropic.js` et `analyze-background.js`)
- `FIREBASE_SERVICE_ACCOUNT` — clé Web API Firebase (sert pour Firestore REST + Firebase Storage REST)
- `INTERNAL_SECRET` — `NorvexSecret2026` (auth agent)
- `MAIL_USER`, `MAIL_PASSWORD` — SendGrid (placeholder, pas encore branché à une fonction `send-email`)
- `NETLIFY_NEXT_MAX_REQUEST_SIZE` — 20480000 (20 MB, mais les fonctions Netlify standard restent à 6 MB)
- ❌ `BLOBS_TOKEN` — supprimée (plus nécessaire depuis migration)

## Boucle de l'agent Python

```
1.  GET  /get-new-dossiers          → dossiers sans welcomeEmailSent
2.  POST /create-upload-token        → reçoit { uploadUrl: https://capitalnorvex.com/upload.html?t=XXX }
3.       Envoie la lettre de bienvenue (avec uploadUrl)
4.  POST /mark-welcome-sent          → marque welcomeEmailSent=true
5.       Client clique le lien, upload ses docs → Firebase Storage + Firestore.uploadedDocs
6.  GET  /get-pending-analysis      → voit le dossier (stage=docs, welcomeEmailSent, !scoreNorvex)
7.  POST /analyze-background        → analyse les PDFs Firebase Storage avec Claude
8.  POST /mark-analysis-done        → enregistre scoreNorvex + decision + stage='final'
```

## Modèles Claude utilisés

- `claude-opus-4-7` — analyse Score Norvex avec PDFs (analyse approfondie)
- `claude-sonnet-4-6` — analyse formulaire seul + compositeur d'e-mails (rapide)

## Tests à faire ensemble

1. Lancer l'agent Python (`agent_docs.py`) et regarder les logs Netlify
2. Submit un dossier via `index.html` → vérifier qu'il apparaît dans Firestore + pipeline
3. Tester Score Norvex avec un PDF de 50+ MB
4. Cliquer un lien d'upload pour upload un gros document
5. Vérifier la chaîne complète : nouvelle demande → courriel → upload → score → décision

## Points d'attention connus

- 18 anciens dossiers tests étaient invisibles dans le pipeline parce qu'ils n'avaient pas de champ `created_at`. Corrigé — ils devraient maintenant tous apparaître.
- L'agent Python n'est pas dans ce repo (vit ailleurs sur la machine de l'utilisateur).
- Les clés API ont été partagées en clair dans une capture d'écran lors de l'audit ; à rotater quand l'utilisateur aura le temps.
- Plan Firebase = Spark (gratuit, 5 GB Storage). Surveiller la consommation si beaucoup de gros fichiers.

## Branche et PR

- Branche de travail (mergée) : `claude/audit-fixes-2026-04-25` → PR #8 squash-merged dans `main` (commit `7e79efb`).
- Repo : `yvesbarrette33-coder/capital-norvex` (instructions GitHub MCP limitent les opérations à ce repo).

## Style de communication

L'utilisateur préfère le **français**. Réponses courtes et directes. Il dicte souvent vocalement, donc les messages sont longs et conversationnels — répondre de façon concise et structurée.
