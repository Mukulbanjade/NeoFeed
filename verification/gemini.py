"""Tier 3: Gemini-powered verification and summarization."""

from __future__ import annotations

import json
import logging

import google.generativeai as genai

from config import settings
from database.models import RawArticle, TrustRating

logger = logging.getLogger(__name__)

_model = None


def _get_model():
    global _model
    if _model is None:
        genai.configure(api_key=settings.gemini_api_key)
        _model = genai.GenerativeModel("gemini-2.0-flash")
    return _model


async def verify_claim(
    article: RawArticle,
    corroborating: list[RawArticle] | None = None,
) -> TrustRating:
    """Ask Gemini to verify a claim using available evidence."""
    if not settings.gemini_api_key:
        logger.warning("Gemini API key not set, skipping LLM verification")
        return TrustRating.UNVERIFIED

    corr_text = ""
    if corroborating:
        corr_text = "\n".join(
            f"- [{c.source_name}] {c.title}" for c in corroborating[:5]
        )

    prompt = f"""You are a fact-checking assistant. Evaluate the following news claim for accuracy.

CLAIM: {article.title}
SOURCE: {article.source_name} ({article.source_type})
CONTENT: {article.content[:1000]}

{"CORROBORATING SOURCES:" + chr(10) + corr_text if corr_text else "No corroborating sources found."}

Rate this claim as one of:
- "verified" - confirmed by multiple reliable sources
- "likely_true" - some corroboration or from a known reliable source
- "unverified" - cannot confirm, single unverified source
- "likely_false" - contradicted by reliable sources or contains misinformation markers

Respond with ONLY a JSON object: {{"rating": "...", "reason": "one sentence explanation"}}"""

    try:
        model = _get_model()
        response = model.generate_content(prompt)
        text = response.text.strip()
        text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        data = json.loads(text)
        rating = data.get("rating", "unverified")
        logger.info(f"Gemini verdict for '{article.title[:60]}': {rating} - {data.get('reason', '')}")
        return TrustRating(rating)
    except Exception as e:
        logger.error(f"Gemini verification failed: {e}")
        return TrustRating.UNVERIFIED


async def summarize_cluster(
    articles: list[RawArticle],
) -> dict:
    """Summarize a cluster of related articles into a single summary."""
    if not settings.gemini_api_key:
        return {
            "summary": articles[0].title,
            "importance": 5.0,
            "representative_title": articles[0].title,
        }

    sources_text = "\n".join(
        f"- [{a.source_name}] {a.title}\n  {a.content[:300]}" for a in articles[:8]
    )

    prompt = f"""You are a news editor. Given these related articles about the same story, produce a concise summary.

ARTICLES:
{sources_text}

Respond with ONLY a JSON object:
{{
    "representative_title": "clear, factual headline for this story",
    "summary": "2-3 sentence summary covering the key facts",
    "importance": <float 1-10, where 10 is paradigm-shifting news>
}}"""

    try:
        model = _get_model()
        response = model.generate_content(prompt)
        text = response.text.strip()
        text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(text)
    except Exception as e:
        logger.error(f"Gemini summarization failed: {e}")
        return {
            "summary": articles[0].content[:200] if articles[0].content else articles[0].title,
            "importance": 5.0,
            "representative_title": articles[0].title,
        }


async def batch_score_importance(titles: list[str]) -> list[float]:
    """Score importance of multiple articles in a single LLM call."""
    if not settings.gemini_api_key or not titles:
        return [5.0] * len(titles)

    numbered = "\n".join(f"{i+1}. {t}" for i, t in enumerate(titles[:30]))
    prompt = f"""Rate the importance of each headline on a scale of 1-10 (10 = paradigm-shifting, 1 = trivial).
Consider: impact on the industry, novelty, and relevance to AI/crypto professionals.

HEADLINES:
{numbered}

Respond with ONLY a JSON array of numbers, e.g. [7, 3, 8, ...]"""

    try:
        model = _get_model()
        response = model.generate_content(prompt)
        text = response.text.strip()
        text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        scores = json.loads(text)
        if isinstance(scores, list) and len(scores) == len(titles):
            return [float(s) for s in scores]
    except Exception as e:
        logger.error(f"Gemini batch scoring failed: {e}")

    return [5.0] * len(titles)
