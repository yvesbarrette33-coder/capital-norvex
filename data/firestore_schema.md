# Schéma Firestore — Norvex Agents™ v1
**Dernière mise à jour:** 2026-04-30
**Status:** Documentation (Firestore est schemaless — ce fichier décrit la structure attendue)

---

## Collections nouvelles (Norvex Agents™)

### `capitalTargets` — Cibles Agent Capital
| Champ | Type | Notes |
|---|---|---|
| `id` | string | id du document |
| `tier` | enum | `ZERO`\|`1A`\|`1B`\|`2`\|`3` |
| `region` | enum | `QC`\|`ON` |
| `language` | enum | `FR`\|`EN`\|`BOTH` |
| `name` | string | Nom complet |
| `title` | string | Titre/fonction |
| `organization` | string | Famille / Family office / firme |
| `capitalEstimate` | object | `{ min, max, currency: "CAD" }` |
| `readinessScore` | int | 1–10 (probabilité d'engagement) |
| `liquidityEvent` | object | `{ type, amount, date, source }` |
| `investmentThesis` | string | 2–3 paragraphes (généré par recherche) |
| `approachAngle` | string | Recommandation IA pour l'approche |
| `protectedFlag` | bool | `true` = TIER ZERO (jamais touché) |
| `introducers` | array | Personnes connectrices |
| `signals` | array | Déclencheurs détectés |
| `status` | enum | `research`\|`ready`\|`approached`\|`engaged`\|`declined`\|`archived` |
| `dossierUrl` | string | Lien Storage vers dossier PDF généré |
| `lastUpdated` | timestamp | Auto |
| `createdAt` | timestamp | Auto |

### `capitalApproaches` — Touchpoints Capital
| Champ | Type | Notes |
|---|---|---|
| `targetId` | ref | → `capitalTargets` |
| `touchpointType` | enum | `letter`\|`video`\|`email`\|`call`\|`meeting` |
| `sentDate` | timestamp | |
| `sentVia` | enum | `postesCanada`\|`graph`\|`twilio`\|`manual` |
| `content` | string \| ref | Texte ou ref Storage |
| `status` | enum | `draft`\|`pending_yves_approval`\|`approved`\|`sent`\|`delivered`\|`responded` |
| `response` | string | Réponse reçue (si applicable) |
| `notes` | string | |
| `yvesApprovedAt` | timestamp | Date approbation par Yves |

### `capitalResearch` — Recherche profonde
| Champ | Type | Notes |
|---|---|---|
| `targetId` | ref | → `capitalTargets` |
| `researchDate` | timestamp | |
| `sources` | array | `[{url, type, snippet, dateAccessed}]` |
| `facts` | array | `[{category, fact, confidence}]` |
| `thesisHypothesis` | string | |
| `approachStrategy` | string | |
| `generatedDossier` | ref | Storage PDF |

### `brokers` — Courtiers commerciaux
| Champ | Type | Notes |
|---|---|---|
| `id`, `name`, `firmName`, `licenseNumber`, `region` | string | |
| `specialty` | array | `[construction, land, commercial, ...]` |
| `typicalDealSize` | object | `{ min, max }` |
| `relationshipStatus` | enum | `cold`\|`warm`\|`active`\|`champion` |
| `dealsReceived` | int | |
| `dealsClosed` | int | |
| `lastTouchpoint` | timestamp | |
| `preferredChannel` | enum | `email`\|`phone`\|`linkedin` |
| `notes` | string | |

### `brokerCommunications` — Touchpoints courtiers
| Champ | Type | Notes |
|---|---|---|
| `brokerId` | ref | → `brokers` |
| `type` | enum | `deal_card`\|`intro`\|`check_in`\|`appreciation` |
| `sentDate` | timestamp | |
| `content` | string | |
| `response` | string | |
| `status` | enum | `draft`\|`pending_yves_approval`\|`approved`\|`sent`\|`responded` |

### `promoters` — Promoteurs immobiliers
| Champ | Type | Notes |
|---|---|---|
| `id`, `name`, `companyName`, `region` | string | |
| `projectTypes` | array | `[multilogement, terrain, commercial]` |
| `recentProjects` | array | `[{name, value, location, status, year}]` |
| `estimatedAnnualVolume` | number | CAD |
| `relationshipStatus` | enum | `cold`\|`researching`\|`approached`\|`active` |
| `score` | int | 1–10 |
| `nextProject` | object | `{ type, estimatedValue, timing }` |
| `contactInfo` | object | `{ email, phone, linkedin }` |

### `promoterApproaches` — Touchpoints promoteurs
| Champ | Type | Notes |
|---|---|---|
| `promoterId` | ref | → `promoters` |
| `sentDate` | timestamp | |
| `content` | string | |
| `response` | string | |
| `status` | enum | `draft`\|`pending_yves_approval`\|`approved`\|`sent`\|`responded` |

### `agentAuditLog` — Journal d'audit central
| Champ | Type | Notes |
|---|---|---|
| `timestamp` | timestamp | Auto |
| `agent` | enum | `capital`\|`courtiers`\|`promoteurs`\|`brain` |
| `action` | string | Ex: `research_target`, `generate_letter`, `tier_zero_block` |
| `targetType` | enum | `capitalTarget`\|`broker`\|`promoter` |
| `targetId` | string | |
| `result` | enum | `success`\|`blocked_tier_zero`\|`error`\|`pending_approval` |
| `details` | object | Métadonnées libres |

---

## Règles d'accès Firestore

Voir `firestore.rules`. Résumé:

- **Collections existantes** (dossiers, transactions, etc.): inchangées
- **Nouvelles collections agents**: `read/write` réservé aux **admins authentifiés** (rôle `admin` dans `utilisateurs`) OU au **Firebase Admin SDK** (qui bypass automatiquement les règles côté serveur Python)
- **agentAuditLog**: lecture admin uniquement, écriture **interdite via client** (Admin SDK seulement)

---

## Déploiement

```bash
firebase deploy --only firestore:rules
```

⚠️ **Pas encore déployé au 2026-04-30.** Approbation Yves requise.
