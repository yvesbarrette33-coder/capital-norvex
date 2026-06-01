"""Orchestrateur principal Camille — pipeline complet.

Pipeline :
    1. lire les inboxes (info@, yves@, et bientôt camille@)
    2. pour chaque message non-lu :
        a. triage Sonnet 4.6
        b. stockage Firestore (camilleEmails)
        c. si triage suggère une réponse → drafting Opus 4.6
        d. stockage du draft (camilleDrafts, status=pending_yves_approval)
        e. notification email à yves@ pour approbation
    3. tracé complet dans agentAuditLog

Usage CLI (voir __main__.py) :
    python -m agents.camille_norvex_counsel run         # full pipeline
    python -m agents.camille_norvex_counsel triage-one  # test triage sur 1 email
    python -m agents.camille_norvex_counsel send <draft_id>  # envoie après approbation manuelle
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from agents.shared.agent_dedup import has_existing_draft_for_email
from agents.shared.firestore_client import audit_log, get
from agents.shared.maestro_check import should_skip_per_maestro
from agents.shared.no_reply_filter import is_no_reply_sender, is_auto_reply

from . import audit as camille_audit
from .config import (
    AGENT_NAME,
    COLLECTION_DRAFTS,
    COLLECTION_EMAILS,
    LEGAL_CATEGORIES,
    MAILBOXES,
    get_cc_list,
    get_mailbox_config,
    is_legal_only,
    is_mailbox_active,
)
from .dossier_lookup import (
    can_camille_auto_send,
    lookup_dossier,
    summarize_dossier_for_drafting,
)
from .drafting import draft_reply
from .inbox_reader import (
    get_message_full,
    list_inbox_messages,
    mark_as_read,
    normalize_for_triage,
)
from .sender import send_email_with_cc
from .templates import get_template
from .triage import triage_email


# Catégories qui justifient un draft de réponse automatique (large)
# Les boîtes legal_only_filter=True restreignent à LEGAL_CATEGORIES.
DRAFTABLE_CATEGORIES = {
    "notaire_qc",
    "avocat_qc",
    "solicitor_on",
    "partenaire",
    "courtier",
    "emprunteur",
    "rdprm",
}

# Types de draft qui n'ont pas besoin d'envoi
NO_DRAFT_TYPES = {"no_reply_needed", "escalade_yves"}


def _pick_template_hint(triage: Dict[str, Any]) -> Optional[str]:
    """Mappe le triage sur un template si pertinent."""
    suggested = triage.get("suggestedDraftType", "")
    category = triage.get("category", "")
    jurisdiction = triage.get("jurisdiction", "")

    mapping = {
        ("notaire_qc", "package_notaire"): "notaire_qc_transmission_package",
        ("notaire_qc", "demande_info"): "notaire_qc_demande_rdprm",
        ("notaire_qc", "confirmation_signature"): "notaire_qc_suivi_signature",
        ("notaire_qc", "transmission_doc"): "notaire_qc_demande_projet_acte",
        ("solicitor_on", "package_notaire"): "solicitor_on_file_package",
        ("solicitor_on", "transmission_doc"): "solicitor_on_pre_closing",
        ("solicitor_on", "confirmation_signature"): "solicitor_on_post_closing",
        ("partenaire", "transmission_doc"): "partenaire_envoi_convention",
        ("partenaire", "demande_info"): "partenaire_demande_info",
        ("partenaire", "accuse_reception"): "partenaire_accuse_reception",
    }

    # Redirection juridiction (notaire QC sur dossier ON)
    if category == "notaire_qc" and jurisdiction == "ON":
        return get_template("solicitor_on_jurisdiction_redirect")

    template_id = mapping.get((category, suggested))
    if template_id:
        try:
            return get_template(template_id)
        except KeyError:
            return None
    return None


def process_one_message(
    *,
    mailbox: str,
    raw_graph_message: Dict[str, Any],
    auto_draft: bool = True,
) -> Dict[str, Any]:
    """Traite UN message Graph : triage → store → (draft + notif si pertinent).

    Retourne un dict de résumé de l'action effectuée.
    """
    # 1. Récupération du body complet
    full = get_message_full(mailbox, raw_graph_message["id"])
    normalized = normalize_for_triage(mailbox, full)

    msg_id_internet = normalized.get("internet_message_id")

    # ── Dédup SELF (bug fix 2026-05-10) : Camille a-t-elle déjà drafté ──
    # CE Message-ID ? Si oui, skip silencieux (évite re-triage / re-draft /
    # re-notif aux 10 min). Voir agents/shared/agent_dedup.py.
    if has_existing_draft_for_email(
        internet_message_id=msg_id_internet,
        emails_collection=COLLECTION_EMAILS,
    ):
        audit_log(
            agent=AGENT_NAME, action="skip_dedup_self",
            target_type="incoming_email",
            target_id=msg_id_internet or "unknown",
            result="skipped", details={"mailbox": mailbox},
        )
        return {
            "email_doc_id": None, "mailbox": mailbox,
            "from": normalized.get("from"), "subject": normalized.get("subject"),
            "category": None, "priority": None,
            "draft_id": None, "drafted": False, "sent": False,
            "notified": False, "skip_reason": "already_drafted_by_self",
            "mode": None,
        }

    # ── Maestro V2 : skip si routé ailleurs ───────────────────────
    if should_skip_per_maestro(msg_id_internet, my_route="to_camille"):
        audit_log(
            agent=AGENT_NAME, action="skip_per_maestro",
            target_type="incoming_email",
            target_id=msg_id_internet or "unknown",
            result="skipped", details={"mailbox": mailbox},
        )
        return {
            "email_doc_id": None, "mailbox": mailbox,
            "from": normalized.get("from"), "subject": normalized.get("subject"),
            "category": None, "priority": None,
            "draft_id": None, "drafted": False, "sent": False,
            "notified": False, "skip_reason": "maestro_routed_elsewhere",
            "mode": None,
        }

    # ── Pré-filtre no-reply / notifications / factures auto ───────
    # Yves 2026-05-04 : « pas de réponse à Microsoft, factures, pubs,
    # notifications. » → skip avant LLM (économie API + dashboard propre)
    if is_no_reply_sender(
        from_address=normalized.get("from", ""),
        subject=normalized.get("subject", ""),
    ) or is_auto_reply(subject=normalized.get("subject", "")):
        action_name = (
            "skip_auto_reply"
            if is_auto_reply(subject=normalized.get("subject", ""))
            else "skip_no_reply_pre_filter"
        )
        audit_log(
            agent=AGENT_NAME,
            action=action_name,
            target_type="incoming_email",
            target_id=normalized.get("internet_message_id") or "unknown",
            result="skipped",
            details={
                "mailbox": mailbox,
                "from": normalized.get("from", "")[:200],
                "subject": normalized.get("subject", "")[:200],
            },
        )
        return {
            "email_doc_id": None,
            "mailbox": mailbox,
            "from": normalized["from"],
            "subject": normalized["subject"],
            "category": None,
            "priority": None,
            "draft_id": None,
            "drafted": False,
            "notified": False,
            "skip_reason": "no_reply_sender_pre_filter",
        }

    # 2. Triage Sonnet 4.6
    triage = triage_email(
        from_address=normalized["from"],
        subject=normalized["subject"],
        body_text=normalized["body_text"],
        received_mailbox=mailbox,
        received_at_iso=normalized["received_at_iso"],
    )

    # 3. Stockage Firestore
    email_doc_id = camille_audit.store_incoming_email(
        normalized=normalized, triage=triage
    )

    summary = {
        "email_doc_id": email_doc_id,
        "mailbox": mailbox,
        "from": normalized["from"],
        "subject": normalized["subject"],
        "category": triage["category"],
        "priority": triage["priority"],
        "draft_id": None,
        "drafted": False,
        "notified": False,
        "skip_reason": None,
    }

    # 4. Décision : drafter ou pas ?
    if not auto_draft:
        summary["skip_reason"] = "auto_draft=False"
        return summary

    # Filtre legal-only : sur info@/yves@, Camille ignore tout ce qui n'est pas
    # juridique (notaire/avocat/solicitor/rdprm). Réservé aux futurs agents
    # (général pour info@, perso pour yves@).
    if is_legal_only(mailbox) and triage["category"] not in LEGAL_CATEGORIES:
        summary["skip_reason"] = (
            f"category={triage['category']} hors scope juridique "
            f"sur boîte legal_only ({mailbox}) — réservé futur agent"
        )
        audit_log(
            agent=AGENT_NAME,
            action="skip_non_legal_on_filtered_mailbox",
            target_type="camilleEmails",
            target_id=email_doc_id,
            result="skipped",
            details={"mailbox": mailbox, "category": triage["category"]},
        )
        return summary

    if triage["category"] not in DRAFTABLE_CATEGORIES:
        summary["skip_reason"] = f"category={triage['category']} not draftable"
        return summary

    if triage.get("suggestedDraftType") in NO_DRAFT_TYPES:
        summary["skip_reason"] = f"suggestedDraftType={triage['suggestedDraftType']}"
        return summary

    if "prompt_injection_attempt" in (triage.get("redFlags") or []):
        summary["skip_reason"] = "prompt_injection_detected"
        audit_log(
            agent=AGENT_NAME,
            action="skip_drafting_security",
            target_type="camilleEmails",
            target_id=email_doc_id,
            result="blocked",
            details={"reason": "prompt_injection_attempt"},
        )
        return summary

    # 4.5 Recherche du dossier en Firestore (BONUS pour enrichir drafting,
    # PAS une condition bloquante — règle Yves 2026-05-04 : autonomie day-to-day).
    dossier = lookup_dossier(
        dossier_id_guess=triage.get("dossierIdGuess"),
        hints=triage.get("dossierHints", []),
        from_address=normalized["from"],
    )
    # Auto-send = décision de Sonnet (qui applique la règle complète d'Yves).
    # Si dossier identifié ET en stage litigieux/default → FORCE escalade (sécurité).
    auto_send_effective = bool(triage.get("autoSendSafe"))
    if dossier:
        from .dossier_lookup import ESCALATION_STAGES
        stage = (dossier.get("stage") or dossier.get("etape_actuelle") or "").lower().strip()
        if stage in {"default", "litigation"}:
            auto_send_effective = False
            summary["auto_send_override"] = f"Forced escalation: dossier stage='{stage}'"
    summary["dossier_id"] = dossier.get("_id") if dossier else None
    summary["auto_send_safe"] = auto_send_effective
    summary["auto_send_reason"] = triage.get("autoSendReason") or (
        f"Dossier identifié ({dossier.get('_id')})" if dossier
        else "Pas de dossier identifié — Camille répondra accusé réception + transmission"
    )

    # 5. Drafting Opus 4.6 (avec contexte dossier si trouvé)
    template_hint = _pick_template_hint(triage)
    dossier_summary_text = (
        summarize_dossier_for_drafting(dossier) if dossier else None
    )
    incoming_payload = {
        "from": normalized["from"],
        "to": normalized["to"],
        "cc": normalized["cc"],
        "subject": normalized["subject"],
        "body_text": normalized["body_text"],
    }

    # Injecte autoSendSafe EFFECTIF dans triage_result pour que drafting le voie
    triage_for_drafting = dict(triage)
    triage_for_drafting["autoSendSafe"] = auto_send_effective

    try:
        draft = draft_reply(
            source_mailbox=mailbox,
            incoming_email=incoming_payload,
            triage_result=triage_for_drafting,
            template_hint=template_hint,
            dossier_data=dossier,
            dossier_summary_text=dossier_summary_text,
        )
    except Exception as e:
        summary["skip_reason"] = f"drafting_error: {e}"
        audit_log(
            agent=AGENT_NAME,
            action="drafting_failed",
            target_type="camilleEmails",
            target_id=email_doc_id,
            result="error",
            details={"error": str(e)[:500]},
        )
        return summary

    # 6. Stockage du draft (avec CC + métadonnées autoSend)
    # Architecture scalable Yves 2026-05-04 : Yves CC SEULEMENT sur sensibles
    # (requiresYvesDecision, requiresHumanLawyer, urgent, autre/spam).
    cc_list = get_cc_list(mailbox, triage=triage)
    initial_status = "auto_send_pending" if auto_send_effective else "pending_yves_approval"
    draft_id = camille_audit.store_draft(
        incoming_email_id=email_doc_id,
        source_mailbox=mailbox,
        draft=draft,
        triage=triage,
        to_recipient=normalized["from"],
        cc_recipients=cc_list,
        initial_status=initial_status,
        dossier_id=summary["dossier_id"],
        auto_send_reason=summary["auto_send_reason"],
    )
    summary["drafted"] = True
    summary["draft_id"] = draft_id

    # 7. BRANCHE A : envoi DIRECT si auto_send_effective
    if auto_send_effective:
        send_ok = send_email_with_cc(
            to=normalized["from"],
            subject=draft["subject"],
            html=draft["signed_html"],
            from_user=mailbox,
            cc=cc_list,
        )
        if send_ok:
            camille_audit.mark_draft_sent(draft_id, sent_via="auto_send_camille")
            # Notif Yves : "Camille a envoyé pour info" (PAS approbation)
            notif_ok = camille_audit.notify_yves_camille_auto_sent(
                draft_id=draft_id,
                persona=draft["persona"],
                subject=draft["subject"],
                to_recipient=normalized["from"],
                summary=triage.get("summary", ""),
                body_html_preview=draft.get("signed_html") or draft.get("body_html") or "",
                cc_recipients=cc_list,
                source_mailbox=mailbox,
                dossier_id=summary["dossier_id"],
                auto_send_reason=summary["auto_send_reason"],
            )
            summary["sent"] = True
            summary["notified"] = notif_ok
            summary["mode"] = "auto_send"
        else:
            # Échec envoi → on retombe en mode escalade (notif approbation)
            audit_log(
                agent=AGENT_NAME,
                action="auto_send_failed_fallback_escalation",
                target_type=COLLECTION_DRAFTS,
                target_id=draft_id,
                result="warning",
            )
            notif_ok = camille_audit.notify_yves_for_camille_draft(
                draft_id=draft_id,
                persona=draft["persona"],
                subject=draft["subject"],
                to_recipient=normalized["from"],
                summary=triage.get("summary", "(échec auto-send → approbation requise)"),
                body_html_preview=draft.get("signed_html") or draft.get("body_html") or "",
                cc_recipients=cc_list,
                source_mailbox=mailbox,
            )
            summary["sent"] = False
            summary["notified"] = notif_ok
            summary["mode"] = "auto_send_failed_to_escalation"
        return summary

    # 7. BRANCHE B : ESCALADE — notification approbation Yves (avec 3 boutons HMAC)
    notif_ok = camille_audit.notify_yves_for_camille_draft(
        draft_id=draft_id,
        persona=draft["persona"],
        subject=draft["subject"],
        to_recipient=normalized["from"],
        summary=triage.get("summary", "(résumé indisponible)"),
        body_html_preview=draft.get("signed_html") or draft.get("body_html") or "",
        cc_recipients=cc_list,
        source_mailbox=mailbox,
    )
    summary["notified"] = notif_ok
    summary["mode"] = "escalation"
    return summary


def process_inbox(
    mailbox: str,
    *,
    top: int = 25,
    only_unread: bool = True,
    auto_draft: bool = True,
    mark_read_after: bool = False,
) -> List[Dict[str, Any]]:
    """Traite la inbox d'une boîte. Retourne la liste des résumés."""
    if not is_mailbox_active(mailbox):
        raise RuntimeError(f"Boîte non configurée pour Camille : {mailbox}")

    messages = list_inbox_messages(mailbox, top=top, only_unread=only_unread)
    results = []
    for raw in messages:
        try:
            res = process_one_message(
                mailbox=mailbox, raw_graph_message=raw, auto_draft=auto_draft
            )
            results.append(res)
            if mark_read_after and res.get("drafted"):
                mark_as_read(mailbox, raw["id"])
        except Exception as e:
            audit_log(
                agent=AGENT_NAME,
                action="process_message_error",
                target_type="graph_message",
                target_id=raw.get("id", "unknown"),
                result="error",
                details={"error": str(e)[:500], "mailbox": mailbox},
            )
            results.append(
                {
                    "graph_id": raw.get("id"),
                    "mailbox": mailbox,
                    "error": str(e)[:500],
                }
            )
    return results


def process_all_mailboxes(
    *,
    top: int = 25,
    only_unread: bool = True,
    auto_draft: bool = True,
    mark_read_after: bool = False,
) -> Dict[str, List[Dict[str, Any]]]:
    """Traite TOUTES les boîtes actives."""
    out = {}
    for mailbox in MAILBOXES.keys():
        try:
            out[mailbox] = process_inbox(
                mailbox,
                top=top,
                only_unread=only_unread,
                auto_draft=auto_draft,
                mark_read_after=mark_read_after,
            )
        except Exception as e:
            out[mailbox] = [{"error": str(e)[:500]}]

    # Bonus : envoyer les lettres d'engagement demandées via le bouton Pipeline
    # (Yves clique → flag Firestore → Camille les envoie ici à la prochaine ronde)
    try:
        from .document_dispatcher import process_pending_engagement_letters
        pending = process_pending_engagement_letters()
        if pending:
            out["_engagement_letters_sent"] = pending
    except Exception as e:
        out["_engagement_letters_error"] = [{"error": str(e)[:500]}]

    return out


# ── Envoi après approbation Yves ──────────────────────────────────
def send_approved_draft(draft_id: str, *, force: bool = False) -> bool:
    """Envoie un draft qui a été approuvé. Garde-fou sur status.

    CC automatique = Yves (sauf sur yves@ où il est déjà l'expéditeur).
    Source de vérité du CC = config.get_cc_list(source_mailbox).

    Args:
        force: si True, bypass la vérification status (cas urgence Yves uniquement)
    """
    draft = get(COLLECTION_DRAFTS, draft_id)
    if not draft:
        raise RuntimeError(f"Draft introuvable : {draft_id}")

    status = draft.get("status")
    if not force and status != "approved":
        raise RuntimeError(
            f"Draft {draft_id} status={status} (attendu: approved). "
            f"Utilise force=True pour bypasser (urgence)."
        )

    source_mailbox = draft["fromUser"]
    # CC : valeur stockée au moment du draft (priorité), sinon recalcule depuis config
    cc_list = draft.get("ccRecipients") or get_cc_list(source_mailbox)

    ok = send_email_with_cc(
        to=draft["toRecipient"],
        subject=draft["subject"],
        html=draft["signedHtml"],
        from_user=source_mailbox,
        cc=cc_list,
    )
    if ok:
        camille_audit.mark_draft_sent(
            draft_id,
            sent_via="graph_or_sendgrid",
        )
    else:
        audit_log(
            agent=AGENT_NAME,
            action="send_draft_failed",
            target_type=COLLECTION_DRAFTS,
            target_id=draft_id,
            result="error",
            details={"cc": cc_list},
        )
    return ok
