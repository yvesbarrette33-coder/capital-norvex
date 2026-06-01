# Camille — NORVEX COUNSEL™

**Coordonnatrice juridique virtuelle** de Capital Norvex Inc.
Architecture Phase 1 — déployée le 2026-05-03.

> ⚠️ Camille n'est **ni avocate ni notaire**. Elle est **coordonnatrice** au
> sens du Code des professions du Québec (art. 132). Aucun avis juridique.
> 100 % des envois sortants validés par Yves Barrette.

---

## Architecture

```
agents/camille_norvex_counsel/
├── __init__.py             — métadonnées agent
├── config.py               — boîtes mail (info@/yves@/+camille@), modèles, signatures
├── system_prompts.py       — 3 prompts : TRIAGE + DRAFT institutional + DRAFT ghostwriter
├── triage.py               — Sonnet 4.6 → JSON structuré
├── drafting.py             — Opus 4.6 + adaptive thinking, routage selon persona
├── signatures.py           — HTML signatures (Camille | Yves) + disclaimer QC
├── inbox_reader.py         — Microsoft Graph (lecture inbox)
├── audit.py                — Firestore : camilleEmails / camilleDrafts / agentAuditLog
├── orchestrator.py         — pipeline complet : lire → trier → drafter → notifier
├── templates/              — 14 templates (notaire QC, solicitor ON, partenaire)
├── __main__.py             — CLI
└── tests_smoke.py          — tests sans réseau
```

---

## Pipeline

```
                      ┌─────────────────────────────┐
                      │  Microsoft Graph Inbox      │
                      │  info@ / yves@ / camille@   │
                      └──────────────┬──────────────┘
                                     │ list_inbox_messages()
                                     ▼
                      ┌─────────────────────────────┐
                      │   TRIAGE (Sonnet 4.6)       │
                      │   → JSON {category,         │
                      │      priority, jurisdiction,│
                      │      suggestedDraftType, …} │
                      └──────────────┬──────────────┘
                                     │ store_incoming_email()
                                     ▼
                      ┌─────────────────────────────┐
                      │   Firestore camilleEmails   │
                      └──────────────┬──────────────┘
                                     │ if draftable
                                     ▼
                      ┌─────────────────────────────┐
                      │  DRAFTING (Opus 4.6)        │
                      │  ┌──────────────┬─────────┐ │
                      │  │ info@/camille│ yves@   │ │
                      │  │ INSTITUTIONAL│ GHOST.  │ │
                      │  └──────────────┴─────────┘ │
                      └──────────────┬──────────────┘
                                     │ store_draft() status=pending_yves_approval
                                     ▼
                      ┌─────────────────────────────┐
                      │   Firestore camilleDrafts   │
                      └──────────────┬──────────────┘
                                     │ notify_yves_for_camille_draft()
                                     ▼
                      ┌─────────────────────────────┐
                      │   yves@capitalnorvex.com    │
                      │   ✅ approve / ✏️ edit /    │
                      │   ❌ reject                 │
                      └──────────────┬──────────────┘
                                     │ send_approved_draft()
                                     ▼
                      ┌─────────────────────────────┐
                      │   Microsoft Graph sendMail  │
                      │   (signature persona-aware) │
                      └─────────────────────────────┘
```

---

## Double persona — règle critique

| Boîte source                      | Persona         | Signature                                    | Visible au destinataire ?       |
|-----------------------------------|-----------------|----------------------------------------------|---------------------------------|
| `info@capitalnorvex.com`          | `institutional` | « Camille — NORVEX COUNSEL™ »                | ✅ Camille parle en son nom      |
| `camille@capitalnorvex.com` (à venir) | `institutional` | idem                                     | ✅                              |
| `yves@capitalnorvex.com`          | `ghostwriter`   | « Yves Barrette, Président »                 | ❌ Camille **invisible**        |

Sur `yves@`, **AUCUNE** mention de « Camille » / « assistante » / « IA ». Le
destinataire doit croire que Yves a écrit lui-même.

---

## Expertise juridique verrouillée

### Droit civil québécois
- CCQ — actes notariés, hypothèques (art. 2660 / 2696-2701 / 2724-2748)
- Bonne foi — art. 1375
- RDPRM (publication, mainlevée, radiation, état certifié)
- Vocabulaire : minute, brevet, rang hypothécaire, subrogation, mainlevée

### Droit ontarien (common law)
- **Pas de notaires** — solicitors uniquement
- Land Titles Act / Registry Act, Teraview, OnLand
- PPSA (sûretés mobilières)
- Vocabulaire : charge, discharge, parcel register, writ search, title insurance

### Knowledge base Capital Norvex (16 PDFs cohérents au 2026-05-04)
- 4 conventions partenariat (Mens FR/EN + Constr FR/EN)
- 1 hypothèque mobilière sur créance individuelle (FR + EN)
- 4 conventions de prêt emprunteur (Pret/Refi FR + Loan Constr/Refi EN)
- 8 lettres d'engagement (4 FR + 4 EN, section "Outils numériques")

---

## CLI

```bash
# Lancer le pipeline complet (toutes boîtes, messages non-lus)
python -m agents.camille_norvex_counsel run

# Une seule boîte
python -m agents.camille_norvex_counsel run --mailbox info@capitalnorvex.com

# Triage seul (pas de drafts)
python -m agents.camille_norvex_counsel run --no-draft

# Approuver et envoyer un draft (après revue)
python -m agents.camille_norvex_counsel approve <draft_id>

# Rejeter un draft
python -m agents.camille_norvex_counsel reject <draft_id> "raison"

# Lister templates / boîtes configurées
python -m agents.camille_norvex_counsel list-templates
python -m agents.camille_norvex_counsel list-mailboxes

# Tests smoke (sans réseau)
python -m agents.camille_norvex_counsel.tests_smoke
```

---

## Variables d'environnement requises

Réutilise le `.env` existant (`Capital Norvex/agent/.env` ou racine projet) :

| Variable                           | Usage                                              |
|------------------------------------|----------------------------------------------------|
| `ANTHROPIC_API_KEY`                | API Anthropic (triage + drafting)                  |
| `AZURE_TENANT_ID`                  | Microsoft Graph                                    |
| `AZURE_CLIENT_ID`                  | Microsoft Graph                                    |
| `AZURE_CLIENT_SECRET`              | Microsoft Graph                                    |
| `GOOGLE_APPLICATION_CREDENTIALS`   | Firebase Admin (Firestore + Storage)               |
| `SENDGRID_API_KEY`                 | Fallback envoi (si Graph KO)                       |
| `CAMILLE_APPROVAL_INBOX` *(opt.)*  | Override (def : `yves@capitalnorvex.com`)          |

**Permission Graph requise** sur Azure App "Norvex-Agent 2026" :
- `Mail.Read` (Application) — lecture inbox info@/yves@/camille@
- `Mail.ReadWrite` (Application, optionnel) — marquer comme lu
- `Mail.Send` (Application) — déjà accordée pour les autres agents

---

## Coûts Anthropic — Phase 1 estimée

| Volume                    | Modèle           | Prix / 1M (in/out) | Coût mensuel estimé |
|---------------------------|------------------|--------------------|---------------------|
| Triage (~10 emails/jour)  | Sonnet 4.6       | $3 / $15           | ~$5-10 USD          |
| Drafting (~7-8/jour)      | Opus 4.6         | $5 / $25           | ~$50-60 USD         |
| **Total Phase 1**         |                  |                    | **~$60-70 USD/mo**  |

Phase 2 (50 emails/jour) : ~$200-300 USD/mo.

---

## Activer `camille@capitalnorvex.com` (demain matin 2026-05-04)

1. Créer la boîte M365 `camille@capitalnorvex.com`
2. Vérifier que l'Azure App a déjà les permissions Mail sur cette boîte (par défaut OUI car `Application` permission = toutes les boîtes du tenant)
3. Décommenter la ligne dans `config.py` :
   ```python
   "camille@capitalnorvex.com": {
       "persona": "institutional",
       "signature_signed_by": "Camille — NORVEX COUNSEL™",
       "always_cc_yves": True,
       ...
   },
   ```
4. Ajouter Yves en CC automatique (déjà géré via `always_cc_yves: True` — à brancher dans `drafting.py` si pas encore fait)
5. Test smoke : `python -m agents.camille_norvex_counsel run --mailbox camille@capitalnorvex.com --no-draft`

---

## Garde-fous appliqués

| Règle                                              | Implémentation                              |
|----------------------------------------------------|---------------------------------------------|
| 100 % approbation Yves                             | `status=pending_yves_approval` obligatoire  |
| Pas d'avis juridique                               | Verrouillé dans les 3 system prompts        |
| Pas de Gmail perso pour notif                      | `CAMILLE_APPROVAL_INBOX = yves@capitalnorvex.com` |
| Suzanne pas en direct                              | Aucune logique d'envoi vers Suzanne         |
| Pas le mot « investisseur »                        | Templates checkés (test smoke)              |
| Bonne foi (CCQ 1375)                               | Persona top-tier, jamais agressive          |
| Disclaimer QC art. 132                             | Auto-injecté dans signature `info@`/`camille@` |
| Détection prompt injection                         | Triage flag → skip drafting + audit         |
| Audit trail complet                                | `agentAuditLog` (collection partagée)       |
