"""Tier 3: Gemini-powered verification and summarization."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta, timezone

import google.generativeai as genai
from bs4 import BeautifulSoup

from config import settings
from database.models import RawArticle, TrustRating

logger = logging.getLogger(__name__)

_model = None
_quota_blocked_until: datetime | None = None


def _get_model():
    global _model
    if _model is None:
        genai.configure(api_key=settings.gemini_api_key)
        _model = genai.GenerativeModel("gemini-2.0-flash")
    return _model


def _is_quota_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "429" in msg or "quota" in msg or "rate limit" in msg


def _quota_block_active() -> bool:
    return _quota_blocked_until is not None and datetime.now(timezone.utc) < _quota_blocked_until


def _set_quota_block(seconds: int = 120) -> None:
    global _quota_blocked_until
    _quota_blocked_until = datetime.now(timezone.utc) + timedelta(seconds=seconds)


async def verify_claim(
    article: RawArticle,
    corroborating: list[RawArticle] | None = None,
) -> TrustRating:
    """Ask Gemini to verify a claim using available evidence."""
    if not settings.gemini_api_key:
        logger.warning("Gemini API key not set, skipping LLM verification")
        return TrustRating.UNVERIFIED
    if _quota_block_active():
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
        if _is_quota_error(e):
            _set_quota_block()
        return TrustRating.UNVERIFIED


def _extractive_fallback(articles: list[RawArticle]) -> dict:
    """When Gemini is unavailable, return a longer extractive blurb than a bare title."""
    a = articles[0]
    body = BeautifulSoup((a.content or "").strip(), "html.parser").get_text(" ", strip=True)
    body = re.sub(r"\s+", " ", body).strip()
    title_norm = re.sub(r"\s+", " ", (a.title or "").strip()).lower()
    if body and title_norm and body.lower().startswith(title_norm):
        body = body[len(a.title):].lstrip(" .:-\n\t")
    if body:
        snippet = body[:1200] + ("…" if len(body) > 1200 else "")
        summary = snippet
    else:
        summary = a.title
    return {
        "representative_title": a.title,
        "summary": summary,
        "importance": 5.0,
    }


async def summarize_cluster(
    articles: list[RawArticle],
) -> dict:
    """Summarize a cluster of related articles into a single summary."""
    if not articles:
        return {"summary": "", "importance": 5.0, "representative_title": ""}

    if not settings.gemini_api_key:
        logger.warning("Gemini API key not set, using extractive fallback for summary")
        return _extractive_fallback(articles)
    if _quota_block_active():
        return _extractive_fallback(articles)

    # Enough text for the model to infer facts beyond the headline (RSS often repeats title in description).
    chunk = 2200
    sources_text = "\n".join(
        f"- [{a.source_name}] {a.title}\n  {a.content[:chunk]}" for a in articles[:8]
    )

    prompt = f"""You are a news explainer. Given these article(s) about the same story, write a clear, casual summary for regular readers.

ARTICLES:
{sources_text}

Requirements:
- "representative_title": one clear, factual headline (not clickbait).
- "summary": 4 to 7 sentences in a casual, easy-to-read tone. Include who, what, when, where relevant, numbers, company or person names, and why it matters. Do not repeat the headline only; add information from the body text.
- Avoid raw HTML tags. Output plain text only.
- "importance": float 1-10 (10 = major industry or market-moving news).

Respond with ONLY a JSON object:
{{
    "representative_title": "...",
    "summary": "...",
    "importance": <float>
}}"""

    try:
        model = _get_model()
        response = model.generate_content(prompt)
        text = response.text.strip()
        text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(text)
    except Exception as e:
        logger.error(f"Gemini summarization failed: {e}")
        if _is_quota_error(e):
            _set_quota_block()
        return _extractive_fallback(articles)


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


async def summarize_feed_digest(category: str, clusters: list[dict]) -> str:
    """Create one readable summary for a group of clusters."""
    if not clusters:
        return "No major updates in this category yet."

    lines = []
    for c in clusters[:20]:
        title = (c.get("representative_title") or "").strip()
        summary = (c.get("summary") or "").strip().replace("\n", " ")
        if not title:
            continue
        lines.append(f"- {title}\n  {summary[:260]}")
    source_text = "\n".join(lines).strip()
    if not source_text:
        return "No major updates in this category yet."

    if not settings.gemini_api_key or _quota_block_active():
        # Simple human-readable fallback.
        bullets = [f"- {(c.get('representative_title') or '').strip()}" for c in clusters[:8] if c.get("representative_title")]
        return "Quick roundup:\n" + "\n".join(bullets)

    prompt = f"""You are a helpful news assistant. Summarize this {category.upper()} feed in a casual tone.

INPUT CLUSTERS:
{source_text}

Requirements:
- 6 to 10 short sentences total.
- Start with one 1-sentence big-picture takeaway.
- Then list key updates in plain language, prioritizing important items first.
- Do not output HTML.
- Keep it concise and readable.
"""
    try:
        model = _get_model()
        response = model.generate_content(prompt)
        text = (response.text or "").strip()
        return text.removeprefix("```").removeprefix("text").removesuffix("```").strip()
    except Exception as e:
        logger.error(f"Gemini feed digest failed: {e}")
        if _is_quota_error(e):
            _set_quota_block()
        bullets = [f"- {(c.get('representative_title') or '').strip()}" for c in clusters[:8] if c.get("representative_title")]
        return "Quick roundup:\n" + "\n".join(bullets)
