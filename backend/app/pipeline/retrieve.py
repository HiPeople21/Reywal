"""Stage 4: retrieve candidate governing-rule URLs."""

from app.clients.exa import search
from app.pipeline.body_registry import (
    collect_domains,
    collect_search_queries,
    collect_seed_urls,
    get_bodies_for_doc_type,
)
from app.pipeline.types import IdentifiedBody
from app.schemas import ExtractedFact


def retrieve(
    bodies: list[IdentifiedBody],
    doc_type: str,
    facts: list[ExtractedFact],
    jurisdiction: str,
) -> list[str]:
    """Merge registry seed URLs with Exa domain-filtered search results."""
    body_ids = _resolve_body_ids(bodies, doc_type, jurisdiction)

    urls: list[str] = collect_seed_urls(body_ids)
    seen = set(urls)

    domains = collect_domains(body_ids)
    queries = _build_queries(body_ids, doc_type, facts, jurisdiction)

    for query in queries:
        try:
            results = search(query, include_domains=domains or None, num_results=3)
            for item in results:
                url = item.get("url", "")
                if url and url not in seen:
                    seen.add(url)
                    urls.append(url)
        except Exception:
            continue

    return urls


def _resolve_body_ids(
    bodies: list[IdentifiedBody],
    doc_type: str,
    jurisdiction: str,
) -> list[str]:
    if bodies:
        return [b.body_id for b in bodies]
    return [body_id for body_id, _ in get_bodies_for_doc_type(doc_type, jurisdiction)]


def _build_queries(
    body_ids: list[str],
    doc_type: str,
    facts: list[ExtractedFact],
    jurisdiction: str,
) -> list[str]:
    queries = collect_search_queries(body_ids)
    if not queries:
        queries = [f"{doc_type} rights regulations {jurisdiction}"]

    fact_terms = " ".join(f.value for f in facts[:3] if f.value)
    if fact_terms:
        queries = [f"{q} {fact_terms}" for q in queries[:2]] + queries[2:]

    return queries[:4]
