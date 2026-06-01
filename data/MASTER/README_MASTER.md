# MASTER — Toutes les cibles Capital Norvex
**Date :** 7 mai 2026 (mis à jour Round 2)
**Total :** 322 cibles uniques (après dédup globale, Round 1 + Round 2)

---

## Vue d'ensemble

| Type | Total | QC | ON | 📧 Email | 📞 Phone | 🔗 LinkedIn |
|---|---|---|---|---|---|---|
| **Brokers (courtiers hypothécaires)** | 117 | 93 | 24 | 89 (76%) | 87 (74%) | 110 (94%) |
| **Promoteurs immobiliers** | 131 | 88 | 43 | 82 (62%) | 86 (65%) | 61 (46%) |
| **Family Offices** | 74 | 39 | 35 | 32 (43%) | 42 (56%) | 32 (43%) |
| **GRAND TOTAL** | **322** | **220** | **102** | **203** | **215** | **203** |

---

## Round 2 (7 mai après-midi) — additions

- **+30 promoteurs régionaux QC** : Lanaudière (2), Laurentides (4), Montérégie (5 nouveaux), Estrie (4), Capitale-Nationale (5 Lévis), Centre-du-Québec (2), Outaouais (3), Saguenay-Lac-Saint-Jean (2), Bas-Saint-Laurent (1), Abitibi (1), Côte-Nord (Sept-Îles 1)

  Notables : **Investissement Ray Junior** (1B$ Cité Mirabel — score 8), **LOGISCO** (Lévis 7000+ units — score 7), **Parisien Construction** (Aylmer 200M$ Zen Apartments — score 6), **Devcore Sept-Îles** (555 units, score 6)

- **+11 family offices** :
  - QC : **Samara MFO** (Walter GAM partnership), **Patrimonica** (5B$ AUM), **Giverny Capital** (François Rochon), Blue Bridge, Granite FO, Demers Beaulne, **Sweet Park Capital** (Bensadoun)
  - ON : **Obelysk Inc.** (John Bitove, Toronto Raptors founder), **Quantum Valley Investments** (Lazaridis BlackBerry), **Irie Capital** (Jen McCain 3rd gen), **Woodward Capital** (Jeffrey McCain 3rd gen)

- **0 nouveau broker ON** — recherche web publique épuisée pour cette catégorie. Les rosters individuels FSRA ne sont pas accessibles.

---

## Fichiers livrés

| Fichier | Contenu | Taille |
|---|---|---|
| `MASTER_capital_norvex_2026-05-07.json` | TOUT en un seul JSON | 307 KB |
| `seed_brokers_ALL_2026-05-07.json` | 117 brokers | 111 KB |
| `seed_promoters_ALL_2026-05-07.json` | 131 promoteurs | 127 KB |
| `seed_family_offices_ALL_2026-05-07.json` | 74 family offices | 71 KB |
| `Capital_Norvex_322_Cibles_Enrichies_2026-05-07.xlsx` | Excel pour revue | 67 KB |
| `PROMPT_POUR_CLAUDE_CODE.md` | Prompt à coller dans Claude Code | — |
| `README_MASTER.md` | Ce document | — |

⚠️ Le fichier `Capital_Norvex_281_Cibles_Enrichies_2026-05-07.xlsx` (ancien) est obsolète — à supprimer manuellement.

---

## TIER ZERO appliqué

Filtres actifs sur les 322 entrées :
- Daoust, Boivin
- Famille Saputo (Lino, Joey, Francesco), Saputo Inc.
- Jolina Capital, Gestion Jolina, Placements Italcan
- Drouin / Finstar (séquestre)
- Peter Quinn (Multi-Prêts Commercial — déjà partenaire)

**0 rejet** : aucun TIER ZERO dans les segments de prospection.

---

## Top champions Tier 1 par catégorie

### Brokers
- **QC** : Patrice Ménard (PMML), Jeffrey Soliman (VA Capital), Michel Durand (MCommercial), Jonathan Gagnon (Orbis), Cédric Lévesque (Lévesque & Cie), Denis Gagné Nadeau (Multilogements.ca), Véronique Caron (Multi-Prêts), Mathieu Lebrun (Multi-Prêts)
- **ON** : Norman Arychuk (Avison Young), Daniel Vyner (DV Capital), Steve Kates (Northwood), Omid Jalili (OMJ), Jonah Brown (Oakbank), Jason Zuckerman (Orbis), Gregory Hernandez (Orbis)

### Promoteurs
- **QC** : Groupe Mach (Vincent Chiara), Devimco, Brivia, Cogir, Carbonleo, Pomerleau, Groupe Maurice, Groupe Sélection, **LOGISCO** (Lévis), **Investissement Ray Junior** (Mirabel)
- **ON** : Tridel, KingSett Capital, Daniels, Mattamy, Cadillac Fairview, RioCan, SmartCentres, H&R, Oxford Properties

### Family Offices
- **QC** : Sagard (Desmarais III), Claridge (Bronfman), Trottier Foundation, **Samara MFO**, **Patrimonica**, TC Transcontinental
- **ON** : Kilmer (Tanenbaum), Onex (Schwartz), Dancap (Aubrey Dan), Northwood Family Office, Picton Mahoney, Tacita, Our Family Office, Prime Quadrant, **Obelysk** (Bitove), **Quantum Valley** (Lazaridis), Dundee, Cardinal, Hillsdale

---

## Pour Claude Code

Charge en un seul appel :

```bash
python -m agents.courtiers.seed_initial_brokers \
    --input data/MASTER/seed_brokers_ALL_2026-05-07.json --dry-run

python -m agents.promoteurs.seed_initial_promoters \
    --input data/MASTER/seed_promoters_ALL_2026-05-07.json --dry-run

python -m agents.capital.seed_initial_family_offices \
    --input data/MASTER/seed_family_offices_ALL_2026-05-07.json --dry-run
```

---

## Historique

- **6 mai 2026** : Vague 1 QC brokers + promoteurs (recherche initiale + correction courtiers vente → courtiers hypothécaires)
- **7 mai matin** : Phase 2 — Ontario brokers, promoteurs, family offices + QC brokers vague 2 + QC family offices
- **7 mai après-midi** : Round 2 enrichissement — 30 promoteurs régionaux QC + 11 family offices QC/ON additionnels
