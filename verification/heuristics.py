"""Tier 2: Rule-based heuristics for trust assessment (zero LLM cost)."""

from __future__ import annotations

import re

from database.models import RawArticle, TrustRating

SENSATIONAL_PATTERNS = [
    r"\b(breaking|leaked|rumor|rumour|unconfirmed|alleged|shock)\b",
    r"\b(insider|exclusive|secret|confidential)\b",
    r"\b(moon|skyrocket|crash|plummet|100x|1000x)\b",
    r"[!]{2,}",
    r"\b(guaranteed|proven|will definitely)\b",
]

HIGH_RELIABILITY_SOURCES = {
    "Reuters Tech", "MIT Tech Review AI", "OpenAI Blog",
    "Google AI Blog", "Hugging Face Blog", "Ars Technica AI",
}


def is_sensational(article: RawArticle) -> bool:
    text = f"{article.title} {article.content[:300]}".lower()
    return any(re.search(p, text, re.IGNORECASE) for p in SENSATIONAL_PATTERNS)


def heuristic_trust(
    article: RawArticle,
    cluster_trust: TrustRating,
    source_reliability: float = 0.5,
) -> TrustRating:
    """Refine trust using rule-based signals. Returns updated trust rating."""

    if cluster_trust in (TrustRating.VERIFIED, TrustRating.LIKELY_TRUE):
        if is_sensational(article) and source_reliability < 0.7:
            return TrustRating.LIKELY_TRUE
        return cluster_trust

    if article.source_name in HIGH_RELIABILITY_SOURCES:
        return TrustRating.LIKELY_TRUE

    if source_reliability >= 0.8:
        return TrustRating.LIKELY_TRUE

    if is_sensational(article):
        return TrustRating.UNVERIFIED

    if article.engagement > 500 and source_reliability >= 0.5:
        return TrustRating.LIKELY_TRUE

    return cluster_trust


def needs_llm_verification(
    article: RawArticle,
    cluster_trust: TrustRating,
    source_reliability: float = 0.5,
) -> bool:
    """Determine if this article needs Gemini verification (Tier 3)."""
    if cluster_trust in (TrustRating.VERIFIED,):
        return False

    if is_sensational(article) and cluster_trust == TrustRating.UNVERIFIED:
        return True

    if source_reliability < 0.4 and cluster_trust == TrustRating.UNVERIFIED:
        return True

    return False
