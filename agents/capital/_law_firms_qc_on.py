"""
Liste cabinets d'avocats QC/ON pour Phase 1 « Trusted Advisors ».
Préparée 2026-05-07 pour Yves.

⚠️ EXCLUSION : Langlois Avocats — Yves fait déjà affaire avec eux.

Critères de sélection :
- Pratique active en fiscalité, planification successorale, M&A privé,
  Family Office advisory, ou patrimoine privé (UHNW).
- Présence physique QC ou ON.
- Site web public (Hunter Domain Search nécessite domaine).

Format : (slug, nom_legal, domaine, province, taille, pratiques_cibles)
"""

# Cabinets EXCLUS — Yves a relation existante
EXCLUDED = {
    "langlois.ca",  # Langlois Avocats
}

LAW_FIRMS = [
    # === GRANDS CABINETS NATIONAUX (présence QC + ON) ===
    ("stikeman",         "Stikeman Elliott LLP",                "stikeman.com",         "QC+ON", "national", ["tax", "estate", "private_ma", "family_office"]),
    ("davies",           "Davies Ward Phillips & Vineberg",     "dwpv.com",             "QC+ON", "national", ["tax", "private_ma", "estate"]),
    ("mccarthy",         "McCarthy Tétrault",                   "mccarthy.ca",          "QC+ON", "national", ["tax", "estate", "private_ma"]),
    ("fasken",           "Fasken Martineau DuMoulin",           "fasken.com",           "QC+ON", "national", ["tax", "estate", "family_office"]),
    ("nortonrose",       "Norton Rose Fulbright Canada",        "nortonrosefulbright.com","QC+ON","national", ["tax", "private_ma"]),
    ("blg",              "Borden Ladner Gervais",               "blg.com",              "QC+ON", "national", ["tax", "estate", "private_ma"]),
    ("dentons",          "Dentons Canada",                      "dentons.com",          "QC+ON", "national", ["tax", "estate", "private_ma"]),
    ("gowling",          "Gowling WLG Canada",                  "gowlingwlg.com",       "QC+ON", "national", ["tax", "private_ma"]),
    ("millerthomson",    "Miller Thomson",                      "millerthomson.com",    "QC+ON", "mid",      ["tax", "estate", "family_office"]),
    ("dlapiper",         "DLA Piper Canada",                    "dlapiper.com",         "QC+ON", "national", ["tax", "private_ma"]),

    # === BOUTIQUES QC FORTES EN FISCALITÉ / SUCCESSORAL / M&A PRIVÉ ===
    ("lavery",           "Lavery, de Billy",                    "lavery.ca",            "QC",    "mid",      ["tax", "estate", "private_ma"]),
    ("bcf",              "BCF Avocats d'affaires",              "bcf.ca",               "QC",    "mid",      ["tax", "private_ma", "family_office"]),
    ("therriencouture",  "Therrien Couture Joli-Cœur",          "groupetcj.ca",         "QC",    "mid",      ["tax", "estate", "private_ma"]),
    ("cainlamarre",      "Cain Lamarre",                        "cainlamarre.ca",       "QC",    "mid",      ["tax", "estate"]),
    ("duntonrainville",  "Dunton Rainville",                    "duntonrainville.com",  "QC",    "mid",      ["tax", "estate"]),
    ("rss",              "Robinson Sheppard Shapiro",           "rsslex.com",           "QC",    "mid",      ["tax", "estate", "private_ma"]),
    ("delegatus",        "Delegatus Services Juridiques",       "delegatus.ca",         "QC",    "boutique", ["tax", "private_ma"]),
    ("pratte",           "Pratte Avocats",                      "pratte.ca",            "QC",    "boutique", ["tax", "estate"]),
    ("spiegelsohmer",    "Spiegel Sohmer",                      "spiegelsohmer.com",    "QC",    "boutique", ["tax", "estate"]),
    ("starnino",         "Starnino Mostovac",                   "starninomostovac.com", "QC",    "boutique", ["tax", "estate"]),

    # === GRANDS CABINETS ON (Bay Street, fiscalité + succession + private capital) ===
    ("osler",            "Osler, Hoskin & Harcourt",            "osler.com",            "ON",    "national", ["tax", "estate", "private_ma", "family_office"]),
    ("goodmans",         "Goodmans LLP",                        "goodmans.ca",          "ON",    "mid",      ["tax", "private_ma"]),
    ("torys",            "Torys LLP",                           "torys.com",            "ON",    "national", ["tax", "estate", "private_ma"]),
    ("bennettjones",     "Bennett Jones",                       "bennettjones.com",     "ON",    "national", ["tax", "estate", "family_office"]),
    ("cassels",          "Cassels Brock & Blackwell",           "cassels.com",          "ON",    "mid",      ["tax", "estate", "private_ma"]),
    ("airdberlis",       "Aird & Berlis",                       "airdberlis.com",       "ON",    "mid",      ["tax", "estate", "private_ma"]),
    ("mcmillan",         "McMillan LLP",                        "mcmillan.ca",          "ON",    "national", ["tax", "private_ma", "family_office"]),
    ("mindengross",      "Minden Gross LLP",                    "mindengross.com",      "ON",    "boutique", ["tax", "estate"]),
    ("loopstranixon",    "Loopstra Nixon",                      "loopstranixon.com",    "ON",    "mid",      ["tax", "estate"]),
    ("weirfoulds",       "WeirFoulds LLP",                      "weirfoulds.com",       "ON",    "mid",      ["tax", "estate", "private_ma"]),
]

assert all(f[2] not in EXCLUDED for f in LAW_FIRMS), \
    f"❌ Cabinet exclu trouvé dans la liste : {[f for f in LAW_FIRMS if f[2] in EXCLUDED]}"

print(f"📋 Liste prête : {len(LAW_FIRMS)} cabinets ({len(EXCLUDED)} exclus : {', '.join(EXCLUDED)})")
qc = sum(1 for f in LAW_FIRMS if 'QC' in f[3])
on = sum(1 for f in LAW_FIRMS if 'ON' in f[3])
print(f"   QC : {qc}  |  ON : {on}  |  Multi-province compté 2×")
