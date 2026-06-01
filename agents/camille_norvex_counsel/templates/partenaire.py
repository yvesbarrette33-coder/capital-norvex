"""Templates pour partenaires (promoteurs, courtiers accrédités, prêteurs partenaires).

Règles strictes Capital Norvex :
- JAMAIS le mot « investisseur » → toujours « partenaire »
- AUCUNE pénalité financière au partenaire
- Bonne foi absolue (CCQ art. 1375)
- Suzanne Breton : aucun contact direct
"""

TEMPLATES_PARTENAIRE = {
    # 1. Mise à jour dossier au partenaire
    "partenaire_mise_a_jour_dossier": """Bonjour [PRÉNOM],

Mise à jour sur le dossier [NOM EMPRUNTEUR — TYPE] :

▸ Statut actuel    : [Phase — instruction / closing / publication]
▸ Date prévue      : [JJ MOIS AAAA]
▸ Prochaine étape  : [À détailler]

[Si applicable]
Points qui requièrent ton attention :
1. [Point 1]
2. [Point 2]

Nous te tenons informé·e dès la prochaine étape franchie.""",

    # 2. Demande d'information complémentaire
    "partenaire_demande_info": """Bonjour [PRÉNOM],

Pour finaliser le dossier [NOM — TYPE], pourrais-tu nous transmettre :

1. [Document 1 — ex : revenus locatifs des 12 derniers mois]
2. [Document 2 — ex : preuve d'assurance reconstruction valeur à neuf]
3. [Document 3]

Idéalement avant le [JJ MOIS AAAA] pour respecter la date de closing prévue.

N'hésite pas si tu as besoin de précisions sur l'un ou l'autre des points.""",

    # 3. Confirmation reçue / accusé réception
    "partenaire_accuse_reception": """Bonjour [PRÉNOM],

Bien reçu — merci pour [DOCUMENT / INFORMATION].

Le dossier [NOM] est désormais à l'étape suivante : [PROCHAINE ÉTAPE].

Nous reviendrons vers toi dès que [PROCHAIN MILESTONE].""",

    # 4. Envoi convention de partenariat à signer
    "partenaire_envoi_convention": """Bonjour [PRÉNOM],

Tel que convenu, voici en pièce jointe la Convention de partenariat
Capital Norvex correspondant au type [Mens / Construction] et à la langue [FR/EN].

Quelques points clés à valider :
1. Pages identité et coordonnées (à compléter)
2. Annexes (le cas échéant)
3. Page signature

Tu peux nous retourner le document signé à info@capitalnorvex.com (PDF complet
préféré). Nous te confirmerons la prise en charge et l'activation dès réception.

Pour toute question sur les modalités, je reste disponible.""",
}
