# Recherche partenaires Capital Norvex — 6 mai 2026

**Demandeur :** Yves Barrette, Président Capital Norvex Inc.
**Réalisée par :** Claude (Cowork) + 4 sous-agents de recherche parallèle
**Source :** Recherche web publique uniquement (Google, sites corporatifs, LinkedIn pages publiques, presse, OACIQ public, Centris commercial, Constructo, presse régionale)

---

## Résumé

| Catégorie | Bruts | TIER ZERO rejetés | Dédupliqués | Livrés |
|---|---|---|---|---|
| Courtiers commerciaux | 72 | 0 | 0 | **72** |
| Promoteurs immobiliers | 58 | 0 | 0 | **58** |
| **TOTAL** | **130** | **0** | | **130** |

---

## Fichiers livrés

1. **`courtiers_commerciaux_2026-05-06.xlsx`** — Excel pour revue manuelle (avec onglet Statistiques)
2. **`promoteurs_2026-05-06.xlsx`** — Excel pour revue manuelle (avec onglet Statistiques)
3. **`seed_brokers_RECHERCHE_2026-05-06.json`** — Format compatible avec ton `seed_brokers.json` existant
4. **`seed_promoters_RECHERCHE_2026-05-06.json`** — Format compatible avec le schéma `promoters` (firestore_schema.md)
5. **`raw_research_2026-05-06.json`** — Backup données brutes pre-traitement
6. **`README_RECHERCHE_2026-05-06.md`** — Ce document

---

## Couverture courtiers commerciaux

### Firmes nationales (41 courtiers)
- **CBRE Canada** : Pierre Lacroix, Michèle Boutet, Jeremy Kenemy, Bryan Greenberg, David Cervantes
- **Colliers International** : Kevin Marshall (MD), Jean-Marc Dubé, Arnold Fox, Étienne Marcoux
- **Cushman & Wakefield** : Lloyd Cooper, Guy Massé, Erik Langburt, Brent Robinson, Sean Greenspoon, Daniel Goodman, Meggie Bergevin
- **Avison Young** : Jean Laurin (Pres. QC), Mark Sinnett, Sebastien Gatti, Guillaume Monast, Yann Charles, Marie-Claire Laflamme-Sanders, Kevin Dopp, Kieran Rankin, David Major-Lapierre, Olivier Dufault-Gagnon
- **Marcus & Millichap** : Adamo Mariani, Jesse Di Gennaro, Philippe Moisan, Sacha Berdugo, Warren Grzywacz
- **JLL** : Jacob Hayon
- **NAI Terramont Commercial** : Paul-Éric Poitras, Michelle Moller, Jérôme Le Blanc-Ducharme, Richard Sauvé, Laurent Lauzon, Serge Marcotte, Jonathan Cohen, Karl Bernard, Martin Fournier

### Firmes locales / boutiques / spécialistes
- **PMML (Patrice Ménard)** — leader provincial multilogement, 1700+ bâtiments sous mandat
- **DB Multilogement** (Daniel Bergeron, Laval)
- **Multilogements** (Denis Gagné Nadeau — courtier hypothécaire commercial)
- **Intella Inc.** — Vincenti, Blouin, Candib, Pala
- **TRIMONT, FBG, MPLEX, KW Commercial Montréal** — boutiques commerciales
- Couverture régions : Sherbrooke (Custeau, Côté/RCCI, Prisme, Savard & Tran), Gatineau (Bisson, Gauthier, CCI), Trois-Rivières (JME), Lévis (Morin), Québec (GDC)

---

## Couverture promoteurs immobiliers

### Grand Montréal (~37 promoteurs)

**Tier 1 — Volume 1B$+ :**
- **Groupe Mach** (Vincent Chiara) — 2.5B$ portfolio
- **Groupe Maurice** — 2.4B$ (Ventas REIT)
- **Carbonleo** (Royalmount, Dix30) — 2B$
- **Groupe Sélection** — 2B$
- **Pomerleau** — 3B$
- **Broccolini** — 1.5B$
- **Cogir** — 1.5B$
- **Magil Construction** — 1.5B$
- **Devimco** — 1.2B$
- **COPRIM** — 1.2B$

**Tier 2 — Volume 200-1B$ :**
- Brivia, Prével, Quintcap, Groupe HD, Groupe Petra, McGill Immobilier, Asgaard, Cromwell, Construction Musto, Scalia, Placements Sergakis, Pur Immobilia, Groupe Mathieu

**Tier 3 — Boutiques émergentes :**
- Habitations Trigone, Capital Property Developments, Kastello, Métrocité, Maître Carré, Construction Voyer, LSR GesDev/Sotramont

### Régions QC

| Région | Promoteurs |
|---|---|
| **Capitale-Nationale (Québec)** | Trudel, Groupe Dallaire, Groupe Tanguay, Norplex, Immostar, Kevlar |
| **Estrie (Sherbrooke)** | Custeau, Must Urbain, Construction de l'Estrie |
| **Outaouais (Gatineau)** | Brigil, Devcore |
| **Saguenay-Lac-Saint-Jean** | Immeubles MCJR, Groupe JCO, Projet 7 |
| **Mauricie (Trois-Rivières)** | Groupe Robin, Demontigny |
| **Centre-du-Québec** | Habitations Urbania (Bécancour), IDA Développement (Drummondville) |
| **Côte-Nord** | Habitations Manicouagan |
| **Bas-Saint-Laurent** | C4 Immobilier (RDL) |
| **Abitibi-Témiscamingue** | Trans-Action Investissement |

---

## Filtre TIER ZERO appliqué

Aucun TIER ZERO trouvé dans les données brutes (Daoust, Boivin, Saputo, Jolina ne sont pas dans le secteur courtage commercial / promotion immobilière au sens où c'est cherché).

Toutefois, le filtre est en place et journalisé dans `raw_research_2026-05-06.json > tier_zero_rejected`.

---

## Limites & avertissements

1. **Courriels publics** : Beaucoup d'entrées n'ont **pas de courriel publié sur les sites corporatifs**. Pour les firmes nationales (CBRE, Cushman, etc.), la pratique est de ne pas exposer l'email — il faut passer par un formulaire ou LinkedIn. Le champ `email` est laissé vide plutôt qu'inventé.

2. **Numéros de licence OACIQ** : Le champ `licenseNumber` est vide. Pour valider un courtier, Yves peut consulter le registre public OACIQ à https://oaciq.com/fr/courtiers et confirmer les certifications.

3. **Doublons potentiels** : Des courtiers de firmes nationales peuvent apparaître à la fois dans la catégorie "nationale" et "locale" (la dédup par nom+firme attrape la plupart, mais certaines variantes orthographiques peuvent passer).

4. **Volumes annuels** : Estimés à partir de communiqués publics et présence média. À traiter comme indicatif, pas comptable.

5. **Tier 0 verification** : Le filtre couvre les noms et organisations de TIER ZERO listés dans `data/tier_zero.json`. Si Yves ajoute des entrées, refaire le filtrage.

---

## Prochaines étapes recommandées

1. **Yves valide manuellement** une dizaine de courtiers et promoteurs prioritaires (revue Excel ~30 min)
2. **Charger en mode dry-run** : `python -m agents.courtiers.seed_initial_brokers --dry-run` (en pointant vers `seed_brokers_RECHERCHE_2026-05-06.json`)
3. **Activer recherche enrichie** : faire passer chaque cible par `agents.capital.target_research.py` pour récupérer triggers récents, deals signalés, signaux de liquidity event
4. **Phase 2 — Courtiers hypothécaires commerciaux** (non couvert dans cette recherche, mais demandé) : on lance ça quand tu valides cette livraison
5. **Phase 3 — Région Ontario (Toronto)** : à enclencher pour aligner avec la cible CAPITAL (QC + ON)

---

**Question pour toi Yves :** Veux-tu que je lance immédiatement (a) la recherche **courtiers hypothécaires commerciaux QC**, (b) la couverture **Ontario** pour les promoteurs et courtiers, ou (c) que tu fasses d'abord ta revue manuelle avant qu'on continue ?
