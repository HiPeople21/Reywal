"""Institutional body identification — plug-in interface.

STUB: returns fixture bodies for demo. Replace with real document/image
extraction that surfaces government/institutional references from the text.
"""

from app.pipeline.types import IdentifiedBody


def identify_bodies(
    text: str,
    doc_type: str,
    jurisdiction: str,
) -> list[IdentifiedBody]:
    """Identify government/institutional bodies referenced in the document.

    Returns an empty list when no body can be determined; downstream stages
    fall back to doc_type-based registry lookup.
    """
    lowered = text.lower()

    if doc_type == "tenancy" or "rtb" in lowered or "tenancy" in lowered:
        span = _find_span(text, ["Residential Tenancies Board", "RTB", "landlord"])
        return [
            IdentifiedBody(
                body_id="rtb",
                display_name="Residential Tenancies Board",
                confidence=0.85 if span else 0.6,
                source_span=span,
                match_kind="explicit" if span else "inferred",
            )
        ]

    if "citizens information" in lowered:
        return [
            IdentifiedBody(
                body_id="citizens_information",
                display_name="Citizens Information",
                confidence=0.9,
                source_span=_find_span(text, ["Citizens Information"]),
                match_kind="explicit",
            )
        ]

    return []


def _find_span(text: str, needles: list[str]) -> str | None:
    for needle in needles:
        idx = text.lower().find(needle.lower())
        if idx >= 0:
            start = max(0, idx - 20)
            end = min(len(text), idx + len(needle) + 40)
            return text[start:end].strip()
    return None
