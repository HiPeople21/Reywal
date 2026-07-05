"""Institutional body identification — plug-in interface.

STUB: returns fixture bodies for demo. Replace with real document/image
extraction that surfaces government/institutional references from the text.
Bodies are always tagged with a jurisdiction so the same name in different
places resolves to different institution records (e.g. IE:rtb vs GB:prt).
"""

from app.pipeline.jurisdiction import normalize_jurisdiction
from app.pipeline.types import IdentifiedBody


def identify_bodies(
    text: str,
    doc_type: str,
    jurisdiction: str,
) -> list[IdentifiedBody]:
    """Identify government/institutional bodies referenced in the document.

    Returns an empty list when no body can be determined; downstream stages
    fall back to doc_type-based registry lookup for the request jurisdiction.
    """
    place = normalize_jurisdiction(jurisdiction)
    lowered = text.lower()

    if place == "IE":
        return _identify_ie(lowered, text, doc_type, place)

    if place == "GB":
        return _identify_gb(lowered, text, doc_type, place)

    return []


def _identify_ie(lowered: str, text: str, doc_type: str, place: str) -> list[IdentifiedBody]:
    if doc_type == "tenancy" or "rtb" in lowered or "tenancy" in lowered:
        span = _find_span(text, ["Residential Tenancies Board", "RTB", "landlord"])
        return [
            IdentifiedBody(
                body_id="rtb",
                display_name="Residential Tenancies Board",
                confidence=0.85 if span else 0.6,
                jurisdiction=place,
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
                jurisdiction=place,
                source_span=_find_span(text, ["Citizens Information"]),
                match_kind="explicit",
            )
        ]

    return []


def _identify_gb(lowered: str, text: str, doc_type: str, place: str) -> list[IdentifiedBody]:
    if doc_type == "tenancy" or "tenancy" in lowered or "landlord" in lowered:
        span = _find_span(
            text,
            ["Tenancy Deposit Scheme", "TDS", "Housing Act", "First-tier Tribunal"],
        )
        return [
            IdentifiedBody(
                body_id="tds",
                display_name="Tenancy Deposit Scheme",
                confidence=0.85 if span else 0.6,
                jurisdiction=place,
                source_span=span,
                match_kind="explicit" if span else "inferred",
            )
        ]

    if "hmrc" in lowered or "revenue" in lowered:
        return [
            IdentifiedBody(
                body_id="hmrc",
                display_name="HM Revenue and Customs",
                confidence=0.9,
                jurisdiction=place,
                source_span=_find_span(text, ["HMRC", "HM Revenue and Customs"]),
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
