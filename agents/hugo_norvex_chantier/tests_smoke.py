"""Smoke tests Hugo NORVEX CHANTIER™ — sans appels réseau.

Vérifie :
1. Imports propres
2. Config valide
3. System prompt bien formé
"""
from __future__ import annotations

import sys


def test_imports():
    from agents.hugo_norvex_chantier import (
        config,
        orchestrator,
        system_prompts,
    )
    assert config.AGENT_NAME == "hugo_norvex_chantier"
    assert config.MODEL_SYNTHESIS == "claude-opus-4-6"
    print("✅ test_imports")


def test_endpoints_configured():
    from agents.hugo_norvex_chantier.config import (
        ENDPOINT_INTEL,
        ENDPOINT_TRACK,
        ENDPOINT_COST,
        ENDPOINT_BRAIN_PUSH,
    )
    assert "intel-analyze-dossier" in ENDPOINT_INTEL
    assert "track-analyze-dossier" in ENDPOINT_TRACK
    assert "cost-analyze-dossier" in ENDPOINT_COST
    assert "brain-push-from-hugo" in ENDPOINT_BRAIN_PUSH
    print("✅ test_endpoints_configured")


def test_system_prompt_structure():
    from agents.hugo_norvex_chantier.system_prompts import SYNTHESIS_SYSTEM
    # Vérifie les sections clés
    assert "Hugo" in SYNTHESIS_SYSTEM
    assert "NORVEX CHANTIER" in SYNTHESIS_SYSTEM
    assert "verdict_global" in SYNTHESIS_SYSTEM
    assert "action_recommandee" in SYNTHESIS_SYSTEM
    assert "JSON STRICT" in SYNTHESIS_SYSTEM
    # Vérifie que les actions sont définies
    for action in [
        "AUTHORIZE_DISBURSEMENT",
        "AUTHORIZE_WITH_CONDITIONS",
        "REQUEST_CLARIFICATION",
        "REQUEST_DOCUMENTS",
        "BLOCK_DISBURSEMENT_ESCALATE_YVES",
    ]:
        assert action in SYNTHESIS_SYSTEM, f"Action manquante : {action}"
    print("✅ test_system_prompt_structure")


def test_escalation_triggers():
    from agents.hugo_norvex_chantier.config import (
        ESCALATION_TRIGGERS,
        DISBURSEMENT_BLOCK_VERDICTS,
    )
    assert "Critique" in ESCALATION_TRIGGERS
    assert "Critique" in DISBURSEMENT_BLOCK_VERDICTS
    print("✅ test_escalation_triggers")


def main() -> int:
    tests = [
        test_imports,
        test_endpoints_configured,
        test_system_prompt_structure,
        test_escalation_triggers,
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
