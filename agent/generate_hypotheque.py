"""
generate_hypotheque.py — Capital Norvex
Génère un acte d'hypothèque .docx complété à partir des données d'un dossier.

Usage (ligne de commande) :
    python generate_hypotheque.py --type terrain --lang FR --data dossier.json --out /chemin/sortie/

Usage (depuis l'agent) :
    from generate_hypotheque import generer_acte
    chemin = generer_acte(type_doc="terrain", langue="FR", donnees=dict_donnees, dossier_no="2024-001")
"""

import json
import subprocess
import sys
import os
import argparse
import tempfile
from pathlib import Path

# Répertoire de ce script
SCRIPT_DIR = Path(__file__).parent
# Script JS de génération (même répertoire)
JS_SCRIPT   = SCRIPT_DIR / "gen_hypotheques.js"
NODE_MODULES = Path("/tmp/docx_gen/node_modules")


def _format_montant(valeur: float) -> str:
    """Formate un montant avec séparateur de milliers."""
    return f"{valeur:,.2f}".replace(",", " ").replace(".", ",")


def _format_montant_en(valeur: float) -> str:
    return f"{valeur:,.2f}"


def _prepare_context(type_doc: str, langue: str, donnees: dict) -> dict:
    """
    Aplatit les données imbriquées en un dict simple clé→valeur
    pour remplacement dans le template JS.
    """
    B = "_________________"   # Blanc si données manquantes
    LB = "________________________________________________"

    def g(path: str, default=None):
        """Récupère une valeur depuis le dict imbriqué. ex: 'emprunteur.nom'"""
        parts = path.split(".")
        val = donnees
        for p in parts:
            if isinstance(val, dict):
                val = val.get(p)
            else:
                return default if default is not None else B
        return val if val is not None else (default if default is not None else B)

    ctx = {
        # Parties
        "DISTRICT":         g("notaire.district_judiciaire"),
        "EMP_NOM":          g("emprunteur.raison_sociale"),
        "EMP_REG":          g("emprunteur.numero_registre"),
        "EMP_SIEGE":        g("emprunteur.adresse_siege"),
        "EMP_REP_NOM":      g("emprunteur.representant_nom"),
        "EMP_REP_TITRE":    g("emprunteur.representant_titre"),
        "GARANT":           g("garant.nom_complet", LB),

        # Finances
        "MONTANT_LETTRES":  g("finances.montant_pret_lettres"),
        "MONTANT_NUM":      _format_montant(g("finances.montant_pret", 0)) if langue == "FR"
                            else _format_montant_en(g("finances.montant_pret", 0)),
        "TAUX":             g("finances.taux_interet_annuel"),
        "FRAIS_DOSSIER":    g("finances.frais_dossier_montant"),
        "FRAIS_PCT":        g("finances.frais_dossier_pct"),
        "PAIEMENT":         g("finances.paiement_mensuel"),
        "PAIEMENT_JOUR":    g("finances.paiement_jour_du_mois"),
        "PAIEMENT_DEBUT":   g("finances.paiement_debut"),
        "TAUX_DEFAUT":      g("finances.taux_defaut"),
        "TERME":            g("finances.terme_mois"),
        "DATE_DEBUT":       g("finances.date_debut"),
        "DATE_ECHEANCE":    g("finances.date_echeance"),
        "FINALITE":         g("finalite"),
        "CHARGES":          g("charges_existantes", "aucune"),

        # Hypothèque
        "HYPO_MONTANT_LETTRES": g("hypotheque.montant_hypotheque_lettres",
                                   g("finances.montant_pret_lettres")),
        "HYPO_MONTANT":    g("hypotheque.montant_hypotheque",
                              g("finances.montant_pret", 0)),
        "LTV":             g("hypotheque.ltv_pct"),
        "VALEUR_EVAL":     g("hypotheque.valeur_evaluation"),
        "DATE_EVAL":       g("hypotheque.date_evaluation"),
        "LTV_MAX":         g("hypotheque.ltv_max_pct"),

        # Notaire
        "NOTAIRE_NOM":     g("notaire.nom_notaire"),
        "NO_DOSSIER":      g("notaire.no_dossier_notarial"),
        "VILLE_SIG":       g("notaire.ville_signature"),
        "JOUR_SIG":        g("notaire.jour_signature"),
        "MOIS_SIG":        g("notaire.mois_signature"),
        "ANNEE_SIG":       g("notaire.annee_signature"),
    }

    # Champs spécifiques Terrain
    if type_doc == "terrain":
        ctx.update({
            "TERRAIN_ADRESSE":          g("terrain.adresse"),
            "TERRAIN_SUPERFICIE":       g("terrain.superficie"),
            "TERRAIN_ZONAGE":           g("terrain.zonage"),
            "TERRAIN_DROITS":           g("terrain.droits_developpement"),
            "TERRAIN_LOTS":             g("terrain.lots_cadastre"),
            "TERRAIN_CIRCO":            g("terrain.circonscription_fonciere"),
            "TERRAIN_CADASTRE":         g("terrain.designation_cadastrale"),
            "TERRAIN_VALEUR_FONCIERE":  g("terrain.valeur_fonciere"),
            "STRAT_DESCRIPTION":        g("strategie.description"),
            "STRAT_DELAI":              g("strategie.delai_previsionnel"),
            "STRAT_VALEUR_PROJETEE":    g("strategie.valeur_projetee"),
            "JALON_PERMIS":             g("jalons.date_depot_permis"),
            "JALON_OBTENTION":          g("jalons.date_obtention_permis"),
            "JALON_TRAVAUX":            g("jalons.date_debut_travaux"),
            "DOCS_ENV":                 g("documents_env"),
        })

    # Champs spécifiques Multilogements
    elif type_doc == "multilogements":
        ctx.update({
            "IMM_ADRESSE":              g("immeuble.adresse"),
            "IMM_NB_LOGEMENTS":         g("immeuble.nombre_logements"),
            "IMM_REPARTITION":          g("immeuble.repartition_logements"),
            "IMM_LOT":                  g("immeuble.lot_cadastre"),
            "IMM_CIRCO":                g("immeuble.circonscription_fonciere"),
            "IMM_CADASTRE":             g("immeuble.designation_cadastrale"),
            "IMM_VALEUR_FONCIERE":      g("immeuble.valeur_fonciere"),
            "IMM_REVENUS_BRUTS":        g("immeuble.revenus_locatifs_bruts"),
            "IMM_TAUX_OCCUPATION":      g("immeuble.taux_occupation"),
            "NB_TRANCHES":              g("finances_multilog.nombre_tranches", 1),
            "TRANCHE2_MONTANT":         g("tranche2_montant"),
            "TRANCHE2_CONDITIONS":      g("tranche2_conditions"),
            "RNO":                      g("finances_multilog.rno_annuel"),
            "RCD":                      g("finances_multilog.rcd"),
            "OCCUPATION_MIN":           g("finances_multilog.taux_occupation_min"),
            "TYPE_PAIEMENT":            g("finances_multilog.type_paiement"),
            "STRATEGIE_SORTIE":         g("strategie_sortie"),
            "DOCS_REMIS":               g("documents_remis"),
        })

    # Champs spécifiques Construction
    elif type_doc == "construction":
        ctx.update({
            "IMM_ADRESSE":              g("immeuble.adresse"),
            "IMM_DESCRIPTION":          g("immeuble.description_projet"),
            "IMM_LOT":                  g("immeuble.lot_cadastre"),
            "IMM_CIRCO":                g("immeuble.circonscription_fonciere"),
            "IMM_CADASTRE":             g("immeuble.designation_cadastrale"),
            "IMM_VALEUR_FONCIERE":      g("immeuble.valeur_fonciere_actuelle"),
            "T1_MONTANT":               g("tranches.tranche1_montant"),
            "T1_PCT":                   g("tranches.tranche1_pct_avancement"),
            "T2_MONTANT":               g("tranches.tranche2_montant"),
            "T2_PCT":                   g("tranches.tranche2_pct_avancement"),
            "T3_MONTANT":               g("tranches.tranche3_montant"),
            "T3_PCT":                   g("tranches.tranche3_pct_avancement"),
            "T4_MONTANT":               g("tranches.tranche4_montant"),
            "ENTREPRENEUR_NOM":         g("entrepreneur.nom"),
            "ENTREPRENEUR_RBQ":         g("entrepreneur.no_licence_rbq"),
            "DATE_COMPLETION":          g("date_completion"),
            "STRATEGIE_SORTIE":         g("strategie_sortie"),
            "LTV_APRES":                g("ltv_apres_travaux_pct"),
            "SEUIL_PLANS":              g("seuil_modification_plans"),
            "SEUIL_JUGEMENT":           g("seuil_jugement"),
        })

    return ctx


def generer_acte(
    type_doc: str,
    langue: str,
    donnees: dict,
    dossier_no: str = "",
    repertoire_sortie: str = None
) -> str:
    """
    Génère un acte d'hypothèque .docx complété.

    Args:
        type_doc:           'terrain', 'multilogements' ou 'construction'
        langue:             'FR' ou 'EN'
        donnees:            dict avec les données du dossier (voir hypotheque_schemas.py)
        dossier_no:         numéro de dossier pour le nom du fichier (optionnel)
        repertoire_sortie:  chemin du dossier de sortie (défaut : dossier courant)

    Returns:
        Chemin absolu du fichier .docx généré.

    Raises:
        ValueError: si type_doc ou langue est invalide
        RuntimeError: si la génération échoue
    """
    type_doc = type_doc.lower()
    langue   = langue.upper()

    if type_doc not in ("terrain", "multilogements", "construction"):
        raise ValueError(f"type_doc invalide: {type_doc}")
    if langue not in ("FR", "EN"):
        raise ValueError(f"langue invalide: {langue}")

    # Dossier de sortie
    if repertoire_sortie is None:
        repertoire_sortie = os.getcwd()
    os.makedirs(repertoire_sortie, exist_ok=True)

    # Nom du fichier de sortie
    noms = {
        ("terrain",        "FR"): "Hypotheque_Terrain_Capital_Norvex",
        ("terrain",        "EN"): "Hypotheque_Terrain_Capital_Norvex_EN",
        ("multilogements", "FR"): "Hypotheque_Multilogements_Capital_Norvex",
        ("multilogements", "EN"): "Hypotheque_Multilogements_Capital_Norvex_EN",
        ("construction",   "FR"): "Hypotheque_Construction_Capital_Norvex",
        ("construction",   "EN"): "Hypotheque_Construction_Capital_Norvex_EN",
    }
    suffixe = f"_{dossier_no}" if dossier_no else ""
    nom_fichier = f"{noms[(type_doc, langue)]}{suffixe}.docx"
    chemin_sortie = str(Path(repertoire_sortie) / nom_fichier)

    # Préparer le contexte
    contexte = _prepare_context(type_doc, langue, donnees)

    # Écrire contexte dans fichier temp JSON
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump({
            "type_doc": type_doc,
            "langue": langue,
            "contexte": contexte,
            "sortie": chemin_sortie,
        }, f, ensure_ascii=False, indent=2)
        tmp_config = f.name

    try:
        result = subprocess.run(
            ["node", str(JS_SCRIPT), tmp_config],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Erreur génération .docx:\n{result.stderr}\n{result.stdout}"
            )
        return chemin_sortie
    finally:
        os.unlink(tmp_config)


def main():
    parser = argparse.ArgumentParser(description="Génère un acte d'hypothèque Capital Norvex")
    parser.add_argument("--type",    required=True, choices=["terrain", "multilogements", "construction"])
    parser.add_argument("--lang",    required=True, choices=["FR", "EN"])
    parser.add_argument("--data",    required=True, help="Fichier JSON avec les données du dossier")
    parser.add_argument("--out",     default=".", help="Répertoire de sortie")
    parser.add_argument("--dossier", default="", help="Numéro de dossier (suffixe du fichier)")
    args = parser.parse_args()

    with open(args.data, "r", encoding="utf-8") as f:
        donnees = json.load(f)

    chemin = generer_acte(
        type_doc=args.type,
        langue=args.lang,
        donnees=donnees,
        dossier_no=args.dossier,
        repertoire_sortie=args.out,
    )
    print(f"Acte généré : {chemin}")


if __name__ == "__main__":
    main()
