"""Stage 7: draft appeal letters, forms, and deadlines."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from app.clients.qwen import chat_json
from app.pipeline.types import IdentifiedBody
from app.schemas import Action, ExtractedFact, Verification

if TYPE_CHECKING:
    from app.schemas import UserProfile


def _profile_block(profile: "UserProfile") -> str:
    """Return a compact personal-details paragraph for the Qwen prompt."""
    parts: list[str] = [f"Full name: {profile.full_name}"]
    addr_parts = [profile.address_line1]
    if profile.address_line2:
        addr_parts.append(profile.address_line2)
    addr_parts.append(profile.city)
    if profile.county:
        addr_parts.append(profile.county)
    if profile.eircode:
        addr_parts.append(profile.eircode)
    parts.append("Address: " + ", ".join(a for a in addr_parts if a))
    if profile.email:
        parts.append(f"Email: {profile.email}")
    if profile.phone:
        parts.append(f"Phone: {profile.phone}")
    return "\n".join(parts)


def act(
    doc_type: str,
    facts: list[ExtractedFact],
    verifications: list[Verification],
    profile: "UserProfile | None" = None,
    bodies: list[IdentifiedBody] | None = None,
) -> list[Action]:
    try:
        mismatch_summary = "\n".join(
            f"- {v.assertion} vs rule: {v.rule_value} ({v.verdict})"
            for v in verifications
            if v.verdict == "mismatch"
        )
        fact_summary = "\n".join(f"- {f.key}: {f.value}" for f in facts)
        sources_context = _sources_context(verifications)
        bodies_context = ", ".join(b.display_name for b in (bodies or [])) or "unknown"

        today = date.today().strftime("%-d %B %Y")  # e.g. "5 July 2026"

        # Only injects sender header details — Qwen writes its own closing/sign-off.
        # Do NOT append a sign-off here or letters will close twice.
        profile_instruction = (
            (
                "Use the following personal details to fill in the sender's name, "
                "address, email and phone in every letter or email body — never leave "
                f"placeholder tokens like [YOUR NAME]. Today's date is {today}:\n"
                + _profile_block(profile)
            )
            if profile
            else (
                f"Today's date is {today}. Use placeholder tokens such as [YOUR NAME] "
                "and [YOUR ADDRESS] where personal details are needed."
            )
        )

        result = chat_json(
            system=(
                "Draft actionable next steps FOR THE USER to take against the organisation. "
                "You act for the RECIPIENT of the document — the person who received "
                "this letter/notice/bill and wants to understand and respond to it. "
                "Every letter or email must be written FROM the user (recipient) TO the "
                "organisation (issuer): the user is the sender/signatory, the organisation "
                "is the recipient. Never produce a letter addressed to the user, signed by "
                "the organisation, or draft on the issuer's behalf. Return JSON: "
                '{"actions": [{"title": str, "kind": "letter|form|email|deadline|contact", '
                '"body": str, "deadline": str|null}]}. Informational only. '
                f"{profile_instruction}\n"
                "GROUNDING RULES — the recipient may send this to an authority, so "
                "accuracy matters more than sounding authoritative:\n"
                "1. Cite a rule, statute/section number, Act name, form number, "
                "programme, or deadline ONLY if it appears verbatim in VERIFIED SOURCES "
                "or FACTS below. NEVER invent, guess, or recall one from memory.\n"
                "2. If you lack the exact citation, refer to the rule generically "
                "(e.g. 'the applicable statutory notice period') — do NOT fabricate a "
                "number to fill the gap.\n"
                "3. Refer to the authority ONLY by the exact name in ISSUING AUTHORITY; "
                "do not substitute an older, abbreviated, or similar-sounding name.\n"
                "4. Quote a rule value only as given in VERIFIED SOURCES. When unsure, "
                "omit the specific rather than state a wrong one."
            ),
            user=(
                f"doc_type={doc_type}\n"
                f"ISSUING AUTHORITY (use this exact name): {bodies_context}\n\n"
                f"FACTS:\n{fact_summary}\n\n"
                f"MISMATCHES:\n{mismatch_summary or 'none'}\n\n"
                f"VERIFIED SOURCES (the only citations you may quote):\n{sources_context}"
            ),
            stage="act",
        )
        actions: list[Action] = []
        for item in result.get("actions", []):
            kind = item.get("kind", "letter")
            if kind not in ("letter", "form", "email", "deadline", "contact"):
                kind = "letter"
            actions.append(
                Action(
                    title=item.get("title", "Next step"),
                    kind=kind,
                    body=item.get("body", ""),
                    deadline=item.get("deadline"),
                )
            )
        if actions:
            return actions
    except Exception:
        pass

    return _fallback_actions(verifications)


def _sources_context(verifications: list[Verification]) -> str:
    """Render the verified source passages the letter is allowed to cite.

    Only ``Verification`` items with a real ``source`` become citable text, so the
    act stage can quote a genuine passage instead of recalling a statute number or
    body name from (often stale) model memory.
    """
    lines: list[str] = []
    seen: set[tuple[str, str]] = set()
    for v in verifications:
        src = v.source
        if src is None or not src.quote:
            continue
        key = (src.title, src.quote)
        if key in seen:
            continue
        seen.add(key)
        lines.append(f'- rule: "{v.rule_value}" | source: {src.title} — "{src.quote}" ({src.url})')
    return "\n".join(lines) or "none — do not cite any specific rule, statute, or section number"


def _fallback_actions(verifications: list[Verification]) -> list[Action]:
    mismatches = [v for v in verifications if v.verdict == "mismatch"]
    if not mismatches:
        return [
            Action(
                title="Review document with advisor",
                kind="contact",
                body="No clear statutory mismatches were identified. Consider seeking advice.",
                deadline=None,
            )
        ]
    return [
        Action(
            title="Appeal letter citing governing rule",
            kind="letter",
            body=(
                "[YOUR NAME]\n[YOUR ADDRESS]\n[DATE]\n\n"
                "To Whom It May Concern,\n\n"
                "I am writing to challenge the terms stated in the document I received. "
                f"The governing rules indicate: {mismatches[0].rule_value}. "
                "I request that you correct this matter in writing.\n\n"
                "Yours sincerely,\n[YOUR NAME]"
            ),
            deadline=None,
        )
    ]
