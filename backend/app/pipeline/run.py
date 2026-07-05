"""Pipeline entry point — chains classify → identify → extract → retrieve → ground → verify → act → refer."""

import logging
import uuid

from app.pipeline.act import act
from app.pipeline.classify import classify
from app.pipeline.extract import extract
from app.pipeline.ground import ground
from app.pipeline.identify import identify_bodies
from app.pipeline.institution_resolve import (
    build_institution_prompt,
    institution_from_user_input,
)
from app.pipeline.jurisdiction import infer_jurisdiction_from_text
from app.pipeline.refer_lawyers import refer_lawyers
from app.pipeline.retrieve import retrieve
from app.pipeline.verify import verify
from app.schemas import DecodeResponse, DecodeResult, LawyerSearchLocation, UserProvidedInstitution

logger = logging.getLogger(__name__)

DISCLAIMER = "Information, not legal advice."


def run_decode(
    text: str,
    jurisdiction: str | None = None,
    institution: UserProvidedInstitution | None = None,
    location: LawyerSearchLocation | None = None,
) -> DecodeResponse:
    """Run the decode pipeline with graceful degradation per stage."""
    doc_type = "other"
    resolved_jurisdiction = jurisdiction or ""
    bodies = []
    facts = []
    plain_summary = "Document received for analysis."
    claims = []
    verifications = []
    actions = []
    lawyer_referrals = []

    try:
        doc_type, resolved_jurisdiction = classify(text, resolved_jurisdiction or None)
    except Exception:
        logger.exception("classify failed")
        if not resolved_jurisdiction:
            resolved_jurisdiction = infer_jurisdiction_from_text(text) or "UNK"

    try:
        bodies = identify_bodies(text, doc_type, resolved_jurisdiction)
    except Exception:
        logger.exception("identify_bodies failed")

    if not bodies:
        if institution is None:
            return DecodeResponse(
                status="needs_institution",
                institution_prompt=build_institution_prompt(doc_type, resolved_jurisdiction),
            )
        try:
            bodies = [institution_from_user_input(institution, resolved_jurisdiction)]
        except ValueError:
            return DecodeResponse(
                status="needs_institution",
                institution_prompt=build_institution_prompt(doc_type, resolved_jurisdiction),
            )

    try:
        facts, plain_summary = extract(text, doc_type)
    except Exception:
        logger.exception("extract failed")

    urls: list[str] = []
    try:
        urls = retrieve(bodies, doc_type, facts, resolved_jurisdiction)
    except Exception:
        logger.exception("retrieve failed")

    passages = []
    try:
        passages = ground(urls, bodies=bodies, jurisdiction=resolved_jurisdiction)
    except Exception:
        logger.exception("ground failed")

    try:
        claims, verifications = verify(facts, passages)
    except Exception:
        logger.exception("verify failed")

    try:
        actions = act(doc_type, facts, verifications)
    except Exception:
        logger.exception("act failed")

    try:
        lawyer_referrals = refer_lawyers(
            doc_type,
            resolved_jurisdiction,
            location,
            plain_summary,
            facts,
            passages=passages,
            claims=claims,
            verifications=verifications,
        )
    except Exception:
        logger.exception("refer_lawyers failed")

    return DecodeResponse(
        status="complete",
        result=DecodeResult(
            id=str(uuid.uuid4()),
            doc_type=doc_type,
            jurisdiction=resolved_jurisdiction,
            plain_summary=plain_summary,
            extracted_facts=facts,
            claims=claims,
            verification=verifications,
            actions=actions,
            lawyer_referrals=lawyer_referrals,
            disclaimer=DISCLAIMER,
        ),
    )
