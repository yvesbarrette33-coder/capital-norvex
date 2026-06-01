"""Templates pour notaires québécois (CCQ, RDPRM, actes notariés)."""

TEMPLATES_NOTAIRE_QC = {
    # 1. Transmission package notarié
    "notaire_qc_transmission_package": """Maître,

Veuillez trouver ci-joint le package complet pour le dossier suivant :

▸ Dossier         : Emprunteur [NOM] — [Construction / Acquisition / Refinancement]
▸ Lot / Cadastre  : [LOT] — Cadastre du Québec, circonscription foncière de [VILLE]
▸ Adresse         : [ADRESSE]
▸ Date de closing : [JJ MOIS AAAA]

Documents transmis :
1. Convention de prêt signée par l'emprunteur
2. Lettre d'engagement contresignée
3. Annexe B (le cas échéant)
4. Hypothèque mobilière sur créance individuelle (signée — pour radiation/cession)
5. Pièces d'identité de l'emprunteur

Nous vous saurions gré de bien vouloir nous transmettre :
- Le projet d'acte hypothécaire au moins 72 h avant le closing
- L'état certifié du RDPRM la veille du closing
- La confirmation de publication dans les 24 h suivant la signature

Pour toute question relative à la coordination du dossier, n'hésitez pas à nous écrire.""",

    # 2. Demande état RDPRM
    "notaire_qc_demande_rdprm": """Maître,

Dans le cadre du dossier [NOM EMPRUNTEUR — TYPE], pourriez-vous nous transmettre :

1. L'état certifié du RDPRM établi à la date de closing
2. La confirmation que l'avis de publication de notre hypothèque mobilière
   sur créance a été préparé conformément aux articles 2696 et suivants CCQ
3. Le numéro de réquisition une fois la publication effectuée

Échéance souhaitée : [JJ MOIS AAAA]

Merci d'avance pour votre diligence.""",

    # 3. Suivi closing / signature
    "notaire_qc_suivi_signature": """Maître,

Nous faisons suite au dossier [NOM EMPRUNTEUR — TYPE], dont la date de signature
était fixée au [JJ MOIS AAAA].

Pourriez-vous nous confirmer :
1. Que la signature a bien eu lieu à la date prévue
2. Le numéro de minute de l'acte notarié
3. Que la publication au RDPRM (et au registre foncier le cas échéant) a été
   effectuée dans les délais
4. Le numéro de réquisition

Si un retard ou une complication est survenu, merci de nous en informer dans
les meilleurs délais afin que nous puissions ajuster nos suivis internes.""",

    # 4. Demande projet d'acte (review pré-closing)
    "notaire_qc_demande_projet_acte": """Maître,

Dans le cadre de la coordination du dossier [NOM — TYPE], pourriez-vous nous
transmettre le projet d'acte hypothécaire au moins 72 h avant la date de closing
prévue ([JJ MOIS AAAA]) ?

Cela nous permettra d'effectuer une dernière vérification de cohérence avec :
- Le montant de la convention de prêt signée
- Le rang hypothécaire convenu
- Les modalités de remboursement et d'échéance
- Les références cadastrales

Toute clause divergente devra naturellement faire l'objet d'une discussion
préalable avec votre cabinet.""",

    # 5. Radiation hypothèque
    "notaire_qc_radiation": """Maître,

Suite au remboursement intégral du prêt accordé à [NOM EMPRUNTEUR] dans le
dossier [DOSSIER], nous vous confirmons notre consentement à la mainlevée et
à la radiation de l'hypothèque publiée sous le numéro de réquisition
[NUMÉRO RDPRM] du [JJ MOIS AAAA].

Pourriez-vous procéder à la radiation consensuelle au RDPRM dans les meilleurs
délais et nous transmettre :
1. Copie de la quittance / acte de mainlevée
2. Confirmation de la radiation effective au registre
3. État certifié post-radiation""",
}
