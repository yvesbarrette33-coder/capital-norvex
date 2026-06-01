"""Tests smoke Béatrice — sans réseau, sans Anthropic, sans Graph.

Vérifie :
- Imports OK (config, system_prompts, triage, drafting, audit, orchestrator)
- Mutex Camille : is_legal_reserved_for_camille() OK
- Signature ghostwriter : signature_yves() rend "Yves Barrette" + "Directeur-Fondateur",
  ZÉRO mention de Béatrice / IA / assistante
- System prompts importables et non-vides
- Triage parse JSON (avec mock client)
- Drafting append signature Yves au body

Usage : python -m agents.beatrice_assistante_yves.tests_smoke
"""
from __future__ import annotations

import json
import sys
from unittest.mock import MagicMock, patch


def test_imports():
    from . import audit, config, drafting, orchestrator, system_prompts, triage
    assert callable(triage.triage_email)
    assert callable(drafting.draft_reply)
    assert callable(orchestrator.process_one_message)
    print("[OK] imports")


def test_config():
    from .config import (
        AGENT_NAME,
        BEATRICE_DRAFTABLE_CATEGORIES,
        CC_YVES_CATEGORIES,
        COLLECTION_DRAFTS,
        COLLECTION_EMAILS,
        LEGAL_CATEGORIES_RESERVED_FOR_CAMILLE,
        MAILBOXES,
        MODEL_DRAFTING,
        MODEL_TRIAGE,
        get_mailbox_config,
        is_legal_reserved_for_camille,
        is_mailbox_active,
        is_personal_yves,
    )
    assert MODEL_TRIAGE == "claude-sonnet-4-6"
    assert MODEL_DRAFTING == "claude-opus-4-6"
    assert AGENT_NAME == "beatrice"
    assert COLLECTION_EMAILS == "beatriceEmails"
    assert COLLECTION_DRAFTS == "beatriceDrafts"
    assert "yves@capitalnorvex.com" in MAILBOXES
    assert MAILBOXES["yves@capitalnorvex.com"]["persona"] == "beatrice_executive"
    assert MAILBOXES["yves@capitalnorvex.com"]["ghostwriter"] is True
    assert MAILBOXES["yves@capitalnorvex.com"]["auto_send_default"] is False
    assert is_mailbox_active("YVES@capitalnorvex.com")  # case-insensitive
    assert not is_mailbox_active("foo@bar.com")

    # CC vide (c'est sa propre boîte)
    assert CC_YVES_CATEGORIES == set()

    # Mutex Camille
    assert is_legal_reserved_for_camille("notaire_qc")
    assert is_legal_reserved_for_camille("avocat_qc")
    assert is_legal_reserved_for_camille("solicitor_on")
    assert is_legal_reserved_for_camille("rdprm")
    assert not is_legal_reserved_for_camille("courtier_dossier")
    assert not is_legal_reserved_for_camille("autre_general")

    # Catégories Béatrice
    assert "courtier_dossier" in BEATRICE_DRAFTABLE_CATEGORIES
    assert "promoteur_dossier" in BEATRICE_DRAFTABLE_CATEGORIES
    assert "client_emprunteur" in BEATRICE_DRAFTABLE_CATEGORIES
    assert "partenariat_capital" in BEATRICE_DRAFTABLE_CATEGORIES
    assert "rdv_administratif" in BEATRICE_DRAFTABLE_CATEGORIES
    # Pas de chevauchement avec catégories juridiques Camille
    assert not (BEATRICE_DRAFTABLE_CATEGORIES & LEGAL_CATEGORIES_RESERVED_FOR_CAMILLE)

    # is_personal_yves heuristique
    assert is_personal_yves(subject="Joyeux anniversaire papa", body_text="")
    assert is_personal_yves(subject="", body_text="On se voit pour le souper de famille dimanche")
    assert not is_personal_yves(
        from_address="courtier@example.com",
        subject="Dossier 5M$ Montréal",
        body_text="Voici la documentation pour le dossier en cours.",
    )

    # get_mailbox_config raises sur boîte inconnue
    try:
        get_mailbox_config("foo@bar.com")
        assert False, "should raise KeyError"
    except KeyError:
        pass

    print("[OK] config")


def _strip_data_uris(html: str) -> str:
    """Retire les blobs base64 (data URIs) avant inspection textuelle.

    Les images PNG embarquées (logo, scan signature) contiennent des bytes
    base64 aléatoires qui peuvent matcher n'importe quelle séquence de
    lettres ('IA', 'AI', etc.) sans valeur sémantique.
    """
    import re
    return re.sub(r"data:image/[^;]+;base64,[A-Za-z0-9+/=]+", "[IMG]", html)


def test_signature_ghostwriter():
    """⚠️ TEST CRITIQUE : la signature ne DOIT mentionner ni Béatrice, ni IA,
    ni assistante. C'est la garantie ghostwriter pure.

    On strip les data URIs (logos PNG) avant inspection — les bytes base64
    aléatoires ne sont pas du texte humain visible."""
    from .drafting import _build_signature_html

    sig_fr_raw = _build_signature_html("fr")
    sig_fr = _strip_data_uris(sig_fr_raw)
    assert "Yves Barrette" in sig_fr, "Yves Barrette manque en FR"
    assert "Directeur-Fondateur" in sig_fr, "Directeur-Fondateur manque en FR"
    # Garde-fous ghostwriter (sur texte humain uniquement)
    assert "Béatrice" not in sig_fr, "Béatrice détectée en FR (interdit)"
    assert "Beatrice" not in sig_fr, "Beatrice (sans accent) détectée en FR"
    assert "assistante" not in sig_fr.lower(), "assistante détectée en FR"
    assert "coordonnatrice IA" not in sig_fr, "mention IA détectée en FR"
    assert "automatisé" not in sig_fr.lower(), "automatisé détecté en FR"

    sig_en_raw = _build_signature_html("en")
    sig_en = _strip_data_uris(sig_en_raw)
    assert "Yves Barrette" in sig_en, "Yves Barrette manque en EN"
    assert "Béatrice" not in sig_en, "Béatrice détectée en EN"
    assert "Beatrice" not in sig_en, "Beatrice détectée en EN"
    assert "AI " not in sig_en, "AI mention détectée en EN"
    assert "AI legal" not in sig_en.lower(), "AI legal détectée en EN"
    assert "assistant" not in sig_en.lower(), "assistant détecté en EN"
    print("[OK] signature ghostwriter (FR + EN, zéro fuite identité)")


def test_system_prompts():
    from .system_prompts import (
        DRAFTING_BEATRICE_SYSTEM,
        KNOWLEDGE_BLOCK,
        TRIAGE_SYSTEM,
        get_drafting_system,
    )
    # Triage
    assert "yves@capitalnorvex.com" in TRIAGE_SYSTEM
    assert "Camille" in TRIAGE_SYSTEM
    assert "isPersonal" in TRIAGE_SYSTEM
    assert "JSON" in TRIAGE_SYSTEM
    assert "courtier_dossier" in TRIAGE_SYSTEM

    # Drafting (ghostwriter)
    assert "GHOSTWRITER" in DRAFTING_BEATRICE_SYSTEM
    assert "Yves Barrette" in DRAFTING_BEATRICE_SYSTEM
    assert "Béatrice" in DRAFTING_BEATRICE_SYSTEM  # référence interne (limites IA)
    assert "investisseur" in DRAFTING_BEATRICE_SYSTEM  # interdit AMF mentionné
    assert "Score Norvex" in DRAFTING_BEATRICE_SYSTEM
    assert "Stikeman" in DRAFTING_BEATRICE_SYSTEM  # niveau institutionnel

    # Knowledge block
    assert "Capital Norvex" in KNOWLEDGE_BLOCK
    assert "2,5 M$" in KNOWLEDGE_BLOCK
    assert "10–12" in KNOWLEDGE_BLOCK or "10-12" in KNOWLEDGE_BLOCK
    assert "3 % à 3,5 %" in KNOWLEDGE_BLOCK or "3%" in KNOWLEDGE_BLOCK

    # API symétrie
    assert get_drafting_system("beatrice_executive") == DRAFTING_BEATRICE_SYSTEM
    try:
        get_drafting_system("inconnu")
        assert False, "should raise"
    except ValueError:
        pass

    print("[OK] system prompts")


def test_triage_parses_json():
    """Triage parse correctement la réponse JSON du LLM (avec mock client)."""
    fake_resp = MagicMock()
    fake_block = MagicMock()
    fake_block.type = "text"
    fake_block.text = json.dumps({
        "category": "courtier_dossier",
        "priority": "haute",
        "language": "fr",
        "isPersonal": False,
        "autoSendSafe": True,  # Sera forcé à False par triage.py
        "summary": "Courtier demande un suivi sur dossier 5M$",
        "actionRequested": "Confirmer disponibilité fonds",
        "deadlineMentioned": None,
        "redFlags": [],
    })
    fake_resp.content = [fake_block]

    fake_client = MagicMock()
    fake_client.messages.create.return_value = fake_resp

    fake_anthropic_module = MagicMock()
    fake_anthropic_module.Anthropic.return_value = fake_client

    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-test"}):
        with patch.dict("sys.modules", {"anthropic": fake_anthropic_module}):
            from .triage import triage_email
            result = triage_email(
                from_address="courtier@example.com",
                subject="Dossier 5M$",
                body_text="Bonjour Yves, suivi sur le dossier...",
                received_mailbox="yves@capitalnorvex.com",
                received_at_iso="2026-05-04T10:00:00Z",
            )
    assert result["category"] == "courtier_dossier"
    assert result["priority"] == "haute"
    assert result["language"] == "fr"
    # Béatrice force toujours autoSendSafe=False
    assert result["autoSendSafe"] is False
    assert result["isPersonal"] is False
    print("[OK] triage parse JSON + force autoSendSafe=False")


def test_drafting_appends_signature():
    """Drafting concatène body_html + signature Yves dans signed_html."""
    fake_resp = MagicMock()
    fake_block = MagicMock()
    fake_block.type = "text"
    fake_block.text = json.dumps({
        "subject": "Re: Dossier 5M$",
        "language": "fr",
        "body_html": "<p>Bonjour Pierre,</p><p>Bien reçu votre courriel.</p>",
        "internal_note_for_yves": "Courtier connu, dossier sur la table",
        "needs_yves_input_before_send": False,
        "open_questions": [],
    })
    fake_resp.content = [fake_block]

    fake_client = MagicMock()
    fake_client.messages.create.return_value = fake_resp

    fake_anthropic_module = MagicMock()
    fake_anthropic_module.Anthropic.return_value = fake_client

    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-test"}):
        with patch.dict("sys.modules", {"anthropic": fake_anthropic_module}):
            from .drafting import draft_reply
            result = draft_reply(
                source_mailbox="yves@capitalnorvex.com",
                incoming_email={
                    "from": "courtier@example.com",
                    "to": "yves@capitalnorvex.com",
                    "cc": "",
                    "subject": "Dossier 5M$",
                    "body_text": "Bonjour Yves...",
                },
                triage_result={
                    "category": "courtier_dossier",
                    "language": "fr",
                    "priority": "haute",
                    "summary": "Suivi dossier",
                    "actionRequested": "Confirmer",
                    "deadlineMentioned": None,
                    "redFlags": [],
                },
            )
    assert result["subject"] == "Re: Dossier 5M$"
    assert result["language"] == "fr"
    assert "<p>Bonjour Pierre" in result["body_html"]
    assert "<p>Bonjour Pierre" in result["signed_html"]
    # Signature Yves doit être appendée
    assert "Yves Barrette" in result["signed_html"]
    # Garde-fou ghostwriter sur le résultat final
    assert "Béatrice" not in result["signed_html"]
    assert "Beatrice" not in result["signed_html"]
    assert result["persona"] == "beatrice_executive"
    assert result["from_user"] == "yves@capitalnorvex.com"
    print("[OK] drafting append signature Yves (ghostwriter)")


def main():
    tests = [
        test_imports,
        test_config,
        test_signature_ghostwriter,
        test_system_prompts,
        test_triage_parses_json,
        test_drafting_appends_signature,
    ]
    failed = 0
    for t in tests:
        try:
            t()
        except Exception as e:
            import traceback
            print(f"[FAIL] {t.__name__}: {e}")
            traceback.print_exc()
            failed += 1
    if failed:
        print(f"\nKO {failed}/{len(tests)} tests failed")
        sys.exit(1)
    print(f"\nOK {len(tests)}/{len(tests)} tests passed")


if __name__ == "__main__":
    main()
