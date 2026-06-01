"""Templates emails-types Camille — 5-10 modèles réutilisables.

Ces templates sont injectés comme `template_hint` dans le prompt drafting
pour cadrer le style et la structure. Camille les adapte au contexte
(nom destinataire, dossier, échéance, etc.).
"""
from .notaire_qc import TEMPLATES_NOTAIRE_QC
from .solicitor_on import TEMPLATES_SOLICITOR_ON
from .partenaire import TEMPLATES_PARTENAIRE

ALL_TEMPLATES = {
    **TEMPLATES_NOTAIRE_QC,
    **TEMPLATES_SOLICITOR_ON,
    **TEMPLATES_PARTENAIRE,
}


def get_template(template_id: str) -> str:
    """Retourne le contenu d'un template par ID."""
    if template_id not in ALL_TEMPLATES:
        raise KeyError(f"Template inconnu : {template_id}. Dispo : {list(ALL_TEMPLATES)}")
    return ALL_TEMPLATES[template_id]


def list_templates() -> list:
    return sorted(ALL_TEMPLATES.keys())
