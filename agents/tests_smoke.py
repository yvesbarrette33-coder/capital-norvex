"""Smoke tests pour les modules Norvex Agents™ — sans Firestore live.

Vérifie:
1. tier_zero_guard charge correctement data/tier_zero.json
2. is_protected() reconnaît bien Daoust / Boivin / Saputo
3. check_before_action() lève sur une cible TIER ZERO
4. email_template.render_variation_a() produit du HTML valide
5. Le logo officiel est bien encodé en base64 dans le template

Usage:
    python -m agents.tests_smoke
"""
from __future__ import annotations

import sys


def test_tier_zero_loads():
    from agents.shared import tier_zero_guard as tz

    protected = tz.list_protected()
    names = [p["name"] for p in protected]
    assert "Serge Daoust" in names, "Daoust manquant"
    assert "Pierre Boivin" in names, "Boivin manquant"
    assert "Famille Saputo" in names, "Famille Saputo manquante"
    print("✅ test_tier_zero_loads")


def test_is_protected_matches():
    from agents.shared import tier_zero_guard as tz

    assert tz.is_protected("Serge Daoust") == "Serge Daoust"
    assert tz.is_protected("serge daoust") == "Serge Daoust"
    assert tz.is_protected("DAOUST") == "Serge Daoust"
    assert tz.is_protected("Famille Daoust Holdings") == "Serge Daoust"
    assert tz.is_protected("Jane Random") is None
    # Jacques Robitaille débloqué le 2026-05-05 — ne doit plus matcher
    assert tz.is_protected("Jacques Robitaille") is None
    assert tz.is_protected(None) is None
    assert tz.is_protected("") is None
    print("✅ test_is_protected_matches")


def test_check_before_action_blocks():
    from agents.shared import tier_zero_guard as tz

    target = {
        "id": "test123",
        "name": "Pierre Boivin",
        "_agent": "test",
        "_target_type": "test",
    }
    raised = False
    try:
        tz.check_before_action(target)
    except tz.TierZeroBlocked as e:
        raised = True
        assert e.matched_name == "Pierre Boivin"
    assert raised, "TierZeroBlocked aurait dû être levée"
    print("✅ test_check_before_action_blocks")


def test_check_before_action_allows():
    from agents.shared import tier_zero_guard as tz

    target = {
        "id": "test456",
        "name": "Jane Smith",
        "organization": "Nothing To See Here Inc.",
        "_agent": "test",
    }
    tz.check_before_action(target)  # ne doit rien lever
    print("✅ test_check_before_action_allows")


def test_email_template_renders():
    from agents.shared.email_template import render_variation_a

    html = render_variation_a(
        body_html="<p>Test message.</p>",
        recipient_name="Madame, Monsieur",
        title_line="Capital structuré. Ambition maîtrisée.",
    )
    assert "<!DOCTYPE html>" in html
    assert "F5EFE0" in html, "Couleur crème manquante"
    assert "C8B070" in html, "Couleur or manquante"
    assert "0A0A0A" in html, "Couleur encre manquante"
    assert "Capital Norvex Inc." in html
    assert "2705-1000 André-Prévost" in html
    assert "Île-des-Sœurs" in html
    assert "Test message." in html
    print("✅ test_email_template_renders")


def test_logo_base64_embedded():
    from agents.shared.email_template import _logo_data_uri, render_variation_a

    uri = _logo_data_uri()
    assert uri.startswith("data:image/png;base64,"), "Logo PNG base64 manquant"
    assert len(uri) > 10000, "Logo base64 trop court (image vide?)"

    html = render_variation_a(body_html="<p>x</p>")
    assert "data:image/png;base64," in html, "Logo non injecté dans le rendu"
    print("✅ test_logo_base64_embedded")


def test_seed_targets_valid_json():
    import json
    import os

    path = os.path.join(
        os.path.dirname(__file__), "..", "data", "seed_targets.json"
    )
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    targets = data.get("targets", [])
    assert len(targets) >= 10, f"Attendu ≥ 10 cibles, obtenu {len(targets)}"
    for t in targets:
        assert t.get("name", "").endswith("(FICTIF)") or "(FICTIF)" in t.get("name", "")
        assert t.get("tier") in ("ZERO", "1A", "1B", "2", "3")
        assert t.get("region") in ("QC", "ON")
    print(f"✅ test_seed_targets_valid_json — {len(targets)} cibles fictives")


def test_seed_brokers_valid_json():
    import json
    import os

    path = os.path.join(
        os.path.dirname(__file__), "..", "data", "seed_brokers.json"
    )
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    brokers = data.get("brokers", [])
    assert len(brokers) >= 5, f"Attendu ≥ 5 brokers, obtenu {len(brokers)}"
    for b in brokers:
        assert "(FICTIF)" in b.get("name", "")
    print(f"✅ test_seed_brokers_valid_json — {len(brokers)} brokers fictifs")


def main() -> int:
    tests = [
        test_tier_zero_loads,
        test_is_protected_matches,
        test_check_before_action_blocks,
        test_check_before_action_allows,
        test_email_template_renders,
        test_logo_base64_embedded,
        test_seed_targets_valid_json,
        test_seed_brokers_valid_json,
    ]
    failures = 0
    for t in tests:
        try:
            t()
        except AssertionError as e:
            failures += 1
            print(f"❌ {t.__name__}: {e}")
        except Exception as e:
            failures += 1
            print(f"💥 {t.__name__}: {type(e).__name__}: {e}")

    print(
        f"\n{'='*48}\n"
        f"Total: {len(tests)} | OK: {len(tests) - failures} | FAIL: {failures}"
    )
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
