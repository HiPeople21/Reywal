"""Stage 7: draft appeal letters, forms, and deadlines."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from app.clients.qwen import chat_json
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
) -> list[Action]:
    try:
        mismatch_summary = "\n".join(
            f"- {v.assertion} vs rule: {v.rule_value} ({v.verdict})"
            for v in verifications
            if v.verdict == "mismatch"
        )
        fact_summary = "\n".join(f"- {f.key}: {f.value}" for f in facts)

        today = date.today().strftime("%-d %B %Y")  # e.g. "5 July 2026"

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
                "Draft actionable next steps for the user. Return JSON: "
                '{"actions": [{"title": str, "kind": "letter|form|email|deadline|contact", '
                '"body": str, "deadline": str|null}]}. '
                f"Cite the exact governing rule in letter bodies. {profile_instruction} "
                "Informational only."
            ),
            user=(
                f"doc_type={doc_type}\nFACTS:\n{fact_summary}\n"
                f"MISMATCHES:\n{mismatch_summary or 'none'}"
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
                "I am writing to challenge the terms stated in the document I received. "
                f"Governing rules indicate: {mismatches[0].rule_value}. "
                "I request that you correct this matter in writing."
            ),
            deadline=None,
        )
    ]
