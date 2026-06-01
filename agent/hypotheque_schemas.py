"""
hypotheque_schemas.py — Capital Norvex
Schémas de champs pour les 3 types d'actes d'hypothèque.

L'agent IA utilise ces schémas pour :
1. Savoir quels champs extraire d'un email/dossier
2. Valider que toutes les données requises sont présentes
3. Appeler generate_hypotheque.py pour produire le .docx

Types disponibles : 'terrain', 'multilogements', 'construction'
Langues           : 'FR', 'EN'
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, Literal
from enum import Enum


# ─── Enum ────────────────────────────────────────────────────────────────────

class DocType(str, Enum):
    TERRAIN        = "terrain"
    MULTILOGEMENTS = "multilogements"
    CONSTRUCTION   = "construction"

class Lang(str, Enum):
    FR = "FR"
    EN = "EN"


# ─── Parties communes ─────────────────────────────────────────────────────────

@dataclass
class Emprunteur:
    """Débiteur hypothécaire / Hypothecary Debtor"""
    raison_sociale: str              # Nom de la compagnie
    numero_registre: str             # Numéro au Registre des entreprises
    adresse_siege: str               # Adresse du siège social
    representant_nom: str            # Nom du signataire
    representant_titre: str          # Titre du signataire

@dataclass
class Garant:
    """Caution personnelle — optionnel / Personal Surety — optional"""
    nom_complet: str
    # Ajouter adresse si nécessaire

@dataclass
class ConditionsFinancieres:
    """Conditions financières communes aux 3 types"""
    montant_pret: float              # ex: 500000.0
    montant_pret_lettres: str        # ex: "cinq cent mille"
    taux_interet_annuel: float       # ex: 10.5  (%)
    frais_dossier_montant: float     # ex: 7500.0
    frais_dossier_pct: float         # ex: 1.5   (%)
    taux_defaut: float               # ex: 18.0  (%)
    paiement_mensuel: float          # ex: 4375.0
    paiement_jour_du_mois: int       # ex: 1
    paiement_debut: str              # ex: "2024-02-01"
    terme_mois: int                  # ex: 12
    date_debut: str                  # ex: "2024-01-15"
    date_echeance: str               # ex: "2025-01-15"

@dataclass
class InfoHypotheque:
    """Infos de l'hypothèque constituée"""
    montant_hypotheque: float        # = montant_pret ou supérieur
    montant_hypotheque_lettres: str
    ltv_pct: float                   # ex: 65.0 (%)
    valeur_evaluation: float         # Valeur selon évaluation agréée
    date_evaluation: str             # ex: "2024-01-10"
    ltv_max_pct: float               # ex: 75.0 (%)

@dataclass
class InfoNotaire:
    """Informations de signature et du notaire"""
    district_judiciaire: str         # ex: "Montréal"
    ville_signature: str
    jour_signature: str              # ex: "15"
    mois_signature: str              # ex: "janvier" / "January"
    annee_signature: str             # ex: "2024"
    nom_notaire: str
    no_dossier_notarial: str


# ─── Document 1 : Terrain ─────────────────────────────────────────────────────

@dataclass
class TerrainImmeuble:
    """Description du terrain hypothéqué"""
    adresse: str
    superficie: str                  # ex: "1 200 m²"
    zonage: str                      # ex: "Résidentiel R-3"
    droits_developpement: str
    lots_cadastre: str
    circonscription_fonciere: str
    designation_cadastrale: str
    valeur_fonciere: float

@dataclass
class TerrainStrategie:
    """Stratégie de développement et de sortie"""
    description: str
    delai_previsionnel: str          # ex: "18 mois"
    valeur_projetee: float

@dataclass
class TerrainJalons:
    """Jalons de développement (optionnel)"""
    date_depot_permis: str           # ex: "2024-06-01"
    date_obtention_permis: str
    date_debut_travaux: str

@dataclass
class HypothequeTerrain:
    """
    Schéma complet — Acte d'hypothèque terrain / Land Hypothec Deed
    Type: 'terrain'
    """
    doc_type: str                    = "terrain"
    langue: str                      = "FR"

    # Parties
    emprunteur: Optional[Emprunteur] = None
    garant: Optional[Garant]         = None

    # Finances
    finances: Optional[ConditionsFinancieres] = None

    # Hypothèque
    hypotheque: Optional[InfoHypotheque] = None

    # Terrain
    terrain: Optional[TerrainImmeuble] = None

    # Stratégie
    strategie: Optional[TerrainStrategie] = None

    # Jalons (optionnel)
    jalons: Optional[TerrainJalons] = None

    # Charges existantes
    charges_existantes: str          = ""   # ex: "aucune" ou description

    # Notaire
    notaire: Optional[InfoNotaire]   = None

    # Finalité du prêt
    finalite: str                    = ""   # ex: "acquisition" ou "refinancement"

    # Documents remis (env. / sol)
    documents_env: str               = ""


# ─── Document 2 : Multilogements ─────────────────────────────────────────────

@dataclass
class MultilogImmeuble:
    """Description de l'immeuble multilogements"""
    adresse: str
    nombre_logements: int
    repartition_logements: str       # ex: "6 x 4½; 2 x 3½"
    lot_cadastre: str
    circonscription_fonciere: str
    designation_cadastrale: str
    valeur_fonciere: float
    revenus_locatifs_bruts: float
    taux_occupation: float           # ex: 95.0 (%)

@dataclass
class MultilogFinances:
    """Données financières spécifiques multilogements"""
    rno_annuel: float                # Revenus nets d'exploitation
    rcd: float                       # Ratio de couverture de la dette (ex: 1.35)
    taux_occupation_min: float       # ex: 80.0 (%)
    type_paiement: str               # "intérêts seulement" ou "capital et intérêts"
    nombre_tranches: int             # généralement 1

@dataclass
class HypothequeMultilogements:
    """
    Schéma complet — Acte d'hypothèque multilogements
    Type: 'multilogements'
    """
    doc_type: str                    = "multilogements"
    langue: str                      = "FR"

    # Parties
    emprunteur: Optional[Emprunteur] = None
    garant: Optional[Garant]         = None

    # Finances
    finances: Optional[ConditionsFinancieres] = None
    finances_multilog: Optional[MultilogFinances] = None

    # Hypothèque
    hypotheque: Optional[InfoHypotheque] = None

    # Immeuble
    immeuble: Optional[MultilogImmeuble] = None

    # Stratégie de sortie
    strategie_sortie: str            = ""

    # Finalité
    finalite: str                    = ""   # acquisition / refinancement / rénovation

    # Charges existantes
    charges_existantes: str          = ""

    # Documents remis
    documents_remis: str             = ""

    # Notaire
    notaire: Optional[InfoNotaire]   = None

    # Tranche 2 (si applicable)
    tranche2_montant: Optional[float] = None
    tranche2_conditions: str          = ""


# ─── Document 3 : Construction ───────────────────────────────────────────────

@dataclass
class ConstructionImmeuble:
    """Description de l'immeuble en construction"""
    adresse: str
    description_projet: str          # ex: "immeuble résidentiel de 6 logements"
    lot_cadastre: str
    circonscription_fonciere: str
    designation_cadastrale: str
    valeur_fonciere_actuelle: float

@dataclass
class ConstructionTranches:
    """Calendrier de décaissements"""
    tranche1_montant: float
    tranche1_pct_avancement: int     # ex: 25
    tranche2_montant: float
    tranche2_pct_avancement: int
    tranche3_montant: float
    tranche3_pct_avancement: int
    tranche4_montant: float          # Décaissement final

@dataclass
class ConstructionEntrepreneur:
    """Entrepreneur général"""
    nom: str
    no_licence_rbq: str

@dataclass
class HypothequeConstruction:
    """
    Schéma complet — Acte d'hypothèque construction
    Type: 'construction'
    """
    doc_type: str                    = "construction"
    langue: str                      = "FR"

    # Parties
    emprunteur: Optional[Emprunteur] = None
    garant: Optional[Garant]         = None

    # Finances
    finances: Optional[ConditionsFinancieres] = None

    # Hypothèque
    hypotheque: Optional[InfoHypotheque] = None

    # Immeuble
    immeuble: Optional[ConstructionImmeuble] = None

    # Décaissements
    tranches: Optional[ConstructionTranches] = None

    # Entrepreneur
    entrepreneur: Optional[ConstructionEntrepreneur] = None

    # Calendrier
    date_completion: str             = ""   # ex: "2025-06-30"

    # Stratégie de sortie
    strategie_sortie: str            = ""

    # LTV après travaux
    ltv_apres_travaux_pct: float     = 0.0

    # Seuil modification plans
    seuil_modification_plans: float  = 0.0  # ex: 25000.0

    # Seuil jugement
    seuil_jugement: float            = 0.0  # ex: 10000.0

    # Charges existantes
    charges_existantes: str          = ""

    # Notaire
    notaire: Optional[InfoNotaire]   = None


# ─── Utilitaires pour l'agent ────────────────────────────────────────────────

CHAMPS_REQUIS = {
    "terrain": [
        "emprunteur.raison_sociale",
        "emprunteur.numero_registre",
        "emprunteur.adresse_siege",
        "emprunteur.representant_nom",
        "emprunteur.representant_titre",
        "finances.montant_pret",
        "finances.montant_pret_lettres",
        "finances.taux_interet_annuel",
        "finances.terme_mois",
        "finances.date_echeance",
        "hypotheque.ltv_pct",
        "hypotheque.valeur_evaluation",
        "terrain.adresse",
        "terrain.lots_cadastre",
        "terrain.circonscription_fonciere",
        "terrain.valeur_fonciere",
        "notaire.district_judiciaire",
        "notaire.ville_signature",
    ],
    "multilogements": [
        "emprunteur.raison_sociale",
        "emprunteur.numero_registre",
        "emprunteur.adresse_siege",
        "emprunteur.representant_nom",
        "emprunteur.representant_titre",
        "finances.montant_pret",
        "finances.montant_pret_lettres",
        "finances.taux_interet_annuel",
        "finances.terme_mois",
        "finances.date_echeance",
        "hypotheque.ltv_pct",
        "hypotheque.valeur_evaluation",
        "immeuble.adresse",
        "immeuble.nombre_logements",
        "immeuble.lot_cadastre",
        "immeuble.valeur_fonciere",
        "immeuble.revenus_locatifs_bruts",
        "immeuble.taux_occupation",
        "finances_multilog.rno_annuel",
        "finances_multilog.rcd",
        "notaire.district_judiciaire",
        "notaire.ville_signature",
    ],
    "construction": [
        "emprunteur.raison_sociale",
        "emprunteur.numero_registre",
        "emprunteur.adresse_siege",
        "emprunteur.representant_nom",
        "emprunteur.representant_titre",
        "finances.montant_pret",
        "finances.montant_pret_lettres",
        "finances.taux_interet_annuel",
        "finances.terme_mois",
        "finances.date_echeance",
        "hypotheque.ltv_pct",
        "hypotheque.valeur_evaluation",
        "immeuble.adresse",
        "immeuble.description_projet",
        "immeuble.lot_cadastre",
        "immeuble.circonscription_fonciere",
        "tranches.tranche1_montant",
        "tranches.tranche4_montant",
        "entrepreneur.nom",
        "entrepreneur.no_licence_rbq",
        "date_completion",
        "notaire.district_judiciaire",
        "notaire.ville_signature",
    ],
}

PROMPT_EXTRACTION = {
    "FR": """Tu es l'agent de Capital Norvex. À partir de l'email ou du dossier fourni, extrais les informations pour remplir un acte d'hypothèque de type '{doc_type}'.

Retourne un JSON avec les champs suivants (utilise null si l'information est absente) :
{champs}

Si un champ obligatoire est manquant, liste-le dans un tableau "champs_manquants".
Réponds uniquement avec un JSON valide.""",

    "EN": """You are the Capital Norvex agent. From the provided email or file, extract the information to complete a '{doc_type}' hypothec deed.

Return a JSON with the following fields (use null if information is missing):
{champs}

If a required field is missing, list it in a "missing_fields" array.
Reply only with valid JSON.""",
}


def get_prompt_extraction(doc_type: str, langue: str = "FR") -> str:
    """Génère le prompt d'extraction pour l'agent selon le type de document."""
    champs = "\n".join(f"  - {c}" for c in CHAMPS_REQUIS.get(doc_type, []))
    template = PROMPT_EXTRACTION.get(langue, PROMPT_EXTRACTION["FR"])
    return template.format(doc_type=doc_type, champs=champs)


def valider_donnees(data: dict, doc_type: str) -> list[str]:
    """
    Vérifie que tous les champs requis sont présents.
    Retourne la liste des champs manquants.
    """
    manquants = []
    for champ in CHAMPS_REQUIS.get(doc_type, []):
        parts = champ.split(".")
        val = data
        for part in parts:
            if isinstance(val, dict):
                val = val.get(part)
            else:
                val = None
            if val is None:
                break
        if val is None:
            manquants.append(champ)
    return manquants


if __name__ == "__main__":
    # Test rapide
    print("=== Champs requis — Terrain ===")
    for c in CHAMPS_REQUIS["terrain"]:
        print(f"  {c}")

    print("\n=== Prompt extraction FR — Multilogements ===")
    print(get_prompt_extraction("multilogements", "FR"))
