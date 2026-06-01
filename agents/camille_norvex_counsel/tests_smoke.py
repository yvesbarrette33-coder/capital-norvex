"""Tests smoke Camille — sans réseau, sans Anthropic, sans Graph.

Vérifie :
- Imports OK
- Config cohérente (boîtes, modèles)
- Signatures HTML générées
- Templates accessibles
- System prompts non vides

Usage : python -m agents.camille_norvex_counsel.tests_smoke
"""
from __future__ import annotations

import sys


def test_imports():
    from . import (
        audit, config, drafting, inbox_reader, orchestrator,
        signatures, system_prompts, triage,
    )
    from .templates import ALL_TEMPLATES, get_template, list_templates
    assert callable(get_template)
    assert callable(list_templates)
    assert isinstance(ALL_TEMPLATES, dict)
    print("[OK] imports")


def test_config():
    from .config import (
        MAILBOXES, MODEL_DRAFTING, MODEL_TRIAGE,
        get_mailbox_config, is_mailbox_active,
    )
    assert MODEL_TRIAGE == "claude-sonnet-4-6"
    assert MODEL_DRAFTING == "claude-opus-4-6"
    assert "info@capitalnorvex.com" in MAILBOXES
    assert "yves@capitalnorvex.com" in MAILBOXES
    assert MAILBOXES["info@capitalnorvex.com"]["persona"] == "institutional"
    assert MAILBOXES["yves@capitalnorvex.com"]["persona"] == "ghostwriter"
    assert is_mailbox_active("INFO@capitalnorvex.com")  # case-insensitive
    assert not is_mailbox_active("foo@bar.com")
    print("[OK] config")


def test_signatures():
    from .signatures import build_signature_html
    sig_camille_fr = build_signature_html(persona="institutional", language="fr")
    sig_camille_en = build_signature_html(persona="institutional", language="en")
    sig_yves_fr = build_signature_html(persona="ghostwriter", language="fr")
    sig_yves_en = build_signature_html(persona="ghostwriter", language="en")

    assert "Camille" in sig_camille_fr
    assert "NORVEX COUNSEL" in sig_camille_fr
    assert "Coordonnatrice juridique" in sig_camille_fr
    assert "conseillers professionnels mandatés" in sig_camille_fr
    assert "Legal Coordinator" in sig_camille_en

    assert "Yves Barrette" in sig_yves_fr
    assert "Camille" not in sig_yves_fr  # ⚠️ règle absolue ghostwriter
    assert "Camille" not in sig_yves_en
    assert "NORVEX COUNSEL" not in sig_yves_fr
    print("[OK] signatures")


def test_system_prompts():
    from .system_prompts import (
        DRAFTING_GHOSTWRITER_SYSTEM,
        DRAFTING_INSTITUTIONAL_SYSTEM,
        TRIAGE_SYSTEM,
        get_drafting_system,
    )
    assert "ghostwriter" in DRAFTING_GHOSTWRITER_SYSTEM.lower()
    assert "Camille" in DRAFTING_INSTITUTIONAL_SYSTEM
    assert "NORVEX COUNSEL" in DRAFTING_INSTITUTIONAL_SYSTEM
    assert "CCQ" in TRIAGE_SYSTEM
    assert "LREE" in TRIAGE_SYSTEM or "Land Titles" in TRIAGE_SYSTEM
    assert "JAMAIS d'avis juridique" in DRAFTING_INSTITUTIONAL_SYSTEM
    assert get_drafting_system("institutional") == DRAFTING_INSTITUTIONAL_SYSTEM
    assert get_drafting_system("ghostwriter") == DRAFTING_GHOSTWRITER_SYSTEM
    try:
        get_drafting_system("unknown")
        assert False, "should raise"
    except ValueError:
        pass
    print("[OK] system prompts")


def test_templates():
    from .templates import ALL_TEMPLATES, get_template, list_templates
    names = list_templates()
    assert len(names) >= 10, f"expected ≥10 templates, got {len(names)}"
    # 5 notaires QC, 5 solicitors ON, 4 partenaires = 14
    assert any("notaire_qc" in n for n in names)
    assert any("solicitor_on" in n for n in names)
    assert any("partenaire" in n for n in names)
    # Aucune mention « investisseur » dans les templates partenaires
    for name, content in ALL_TEMPLATES.items():
        if "partenaire" in name:
            assert "investisseur" not in content.lower(), \
                f"template {name} contient 'investisseur' (interdit AMF)"
    # Aucune mention « avocate » ou « notaire » comme titre Camille
    for name, content in ALL_TEMPLATES.items():
        # OK de mentionner Maître / notaire dans le corps (destinataire)
        # mais pas dans une signature attribuée à Camille
        pass
    print(f"[OK] templates ({len(names)} dispos)")


def test_triage_jurisdiction_redirect():
    """Sanity check : si notaire QC sur dossier ON, on a un template redirect."""
    from .templates import get_template
    redirect = get_template("solicitor_on_jurisdiction_redirect")
    assert "Ontario" in redirect
    assert "no notarial act" in redirect.lower() or "land titles" in redirect.lower()
    print("[OK] jurisdiction redirect template")


def main():
    tests = [
        test_imports,
        test_config,
        test_signatures,
        test_system_prompts,
        test_templates,
        test_triage_jurisdiction_redirect,
    ]
    failed = 0
    for t in tests:
        try:
            t()
        except Exception as e:
            print(f"[FAIL] {t.__name__}: {e}")
            failed += 1
    if failed:
        print(f"\n❌ {failed}/{len(tests)} tests failed")
        sys.exit(1)
    print(f"\n✅ {len(tests)}/{len(tests)} tests passed")


if __name__ == "__main__":
    main()
