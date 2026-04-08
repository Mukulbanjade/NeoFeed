from __future__ import annotations

import re
from fastapi import APIRouter, Depends, Query

from api.middleware import verify_pin
from database import supabase_client as db
from database.models import Category
from personalization.engine import preference_engine
from verification.gemini import summarize_feed_digest

router = APIRouter(prefix="/clusters", tags=["clusters"])


def _cluster_with_aliases(row: dict) -> dict:
    """Expose trust_level / source_count aliases for clients expecting Lovable-style field names."""
    out = dict(row)
    if "trust_rating" in out and "trust_level" not in out:
        out["trust_level"] = out["trust_rating"]
    if "article_count" in out and "source_count" not in out:
        out["source_count"] = out["article_count"]
    return out


# Strong signals: one match is enough for the war digest (and to keep items out of AI/crypto digests).
_WAR_STRONG = [
    re.compile(r"\bwar\b", re.I),
    re.compile(r"\bconflict\b", re.I),
    re.compile(r"\bmilitary\b", re.I),
    re.compile(r"\bmissile\b", re.I),
    re.compile(r"\bdrone\b", re.I),
    re.compile(r"\bceasefire\b", re.I),
    re.compile(r"\bnato\b", re.I),
    re.compile(r"\bairstrike\b", re.I),
    re.compile(r"\bfrontline\b", re.I),
    re.compile(r"\binvasion\b", re.I),
    re.compile(r"\bartillery\b", re.I),
    # Geopolitical hotspots (headlines often omit “war” / “military”)
    re.compile(r"\biran\b", re.I),
    re.compile(r"\birans\b", re.I),
    re.compile(r"\btehran\b", re.I),
    re.compile(r"\bukraine\b", re.I),
    re.compile(r"\bgaza\b", re.I),
    re.compile(r"\bhamas\b", re.I),
    re.compile(r"\bhezbollah\b", re.I),
    re.compile(r"\bhouthis?\b", re.I),
    # Omit broad “Israel” / “Middle East” here — they catch a lot of tech/business news;
    # Hezbollah/Hamas/Gaza/Iran/Ukraine still cover the geopolitical headlines in practice.
]
# Weak signals: need two matches (or one weak + context) so lone “sanctions” / “defense”
# in crypto or tech headlines do not flood the war digest.
_WAR_WEAK = [
    re.compile(r"\bsanctions\b", re.I),
    re.compile(r"\bdefense\b", re.I),
    re.compile(r"\bdefence\b", re.I),
    re.compile(r"\bgeopolitics?\b", re.I),
]

_AI_DIGEST = [
    re.compile(r"\bai\b", re.I),
    re.compile(r"\bartificial intelligence\b", re.I),
    re.compile(r"\bmachine learning\b", re.I),
    re.compile(r"\bllm\b", re.I),
    re.compile(r"\bgpt\b", re.I),
    re.compile(r"\bopenai\b", re.I),
    re.compile(r"\banthropic\b", re.I),
    re.compile(r"\bclaude\b", re.I),
    re.compile(r"\bgemini\b", re.I),
    re.compile(r"\btransformer\b", re.I),
    re.compile(r"\bneural\b", re.I),
    re.compile(r"\bdeep learning\b", re.I),
    re.compile(r"\bdiffusion\b", re.I),
    re.compile(r"\bcopilot\b", re.I),
    re.compile(r"\bchatgpt\b", re.I),
    re.compile(r"\bfoundation model\b", re.I),
    re.compile(r"\binference\b", re.I),
    re.compile(r"\bsemiconductor\b", re.I),
    re.compile(r"\bchip\b", re.I),
    re.compile(r"\bgpu\b", re.I),
    re.compile(r"\brobot\b", re.I),
    re.compile(r"\bautonomous\b", re.I),
]

_CRYPTO_DIGEST = [
    re.compile(r"\bbitcoin\b", re.I),
    re.compile(r"\bbtc\b", re.I),
    re.compile(r"\bethereum\b", re.I),
    re.compile(r"\beth\b", re.I),
    re.compile(r"\bcrypto\b", re.I),
    re.compile(r"\bblockchain\b", re.I),
    re.compile(r"\bdefi\b", re.I),
    re.compile(r"\bnft\b", re.I),
    re.compile(r"\bweb3\b", re.I),
    re.compile(r"\bstablecoin\b", re.I),
    re.compile(r"\btokeniz", re.I),
    re.compile(r"\bsolana\b", re.I),
    re.compile(r"\bbinance\b", re.I),
    re.compile(r"\bcoinbase\b", re.I),
    re.compile(r"\baltcoin\b", re.I),
]


def _cluster_text(row: dict) -> str:
    return f"{row.get('representative_title', '')} {row.get('summary', '')}"


def _digest_hits(text: str, patterns: list[re.Pattern]) -> int:
    return sum(1 for p in patterns if p.search(text))


def _is_war_cluster(row: dict) -> bool:
    text = _cluster_text(row)
    strong = _digest_hits(text, _WAR_STRONG)
    weak = _digest_hits(text, _WAR_WEAK)
    return strong >= 1 or weak >= 2


def _for_ai_digest(row: dict) -> bool:
    """AI roundup: must mention AI/ML in title+summary (DB labels are often wrong). War/geo wins unless AI clearly dominates."""
    cat = (row.get("category") or "").lower()
    text = _cluster_text(row)
    ai_h = _digest_hits(text, _AI_DIGEST)
    cr_h = _digest_hits(text, _CRYPTO_DIGEST)
    war = _is_war_cluster(row)

    if cat not in {"ai", "both"}:
        return False
    if ai_h < 1:
        return False

    if cat == "ai":
        if war and ai_h <= cr_h + 1:
            return False
        return True
    # both
    if ai_h < cr_h:
        return False
    if war and ai_h <= cr_h + 1:
        return False
    return True


def _for_crypto_digest(row: dict) -> bool:
    """Crypto roundup: must mention crypto/blockchain terms; mislabeled politics/war rows drop out."""
    cat = (row.get("category") or "").lower()
    text = _cluster_text(row)
    ai_h = _digest_hits(text, _AI_DIGEST)
    cr_h = _digest_hits(text, _CRYPTO_DIGEST)
    war = _is_war_cluster(row)

    if cat not in {"crypto", "both"}:
        return False
    if cr_h < 1:
        return False

    if cat == "crypto":
        if war and cr_h <= ai_h + 1:
            return False
        return True
    # both
    if cr_h <= ai_h:
        return False
    if war and cr_h <= ai_h + 1:
        return False
    return True


@router.get("/")
async def list_clusters(
    category: Category | None = None,
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    personalized: bool = Query(False),
    _auth: bool = Depends(verify_pin),
):
    clusters = db.get_clusters(category=category, limit=limit, offset=offset)

    if personalized:
        prefs = db.get_preferences()
        if prefs:
            clusters = preference_engine.rerank_articles(clusters, prefs)

    clusters = [_cluster_with_aliases(c) for c in clusters]
    return {"clusters": clusters, "count": len(clusters)}


def _rank_cluster(c: dict) -> tuple:
    return (-float(c.get("importance_score") or 0), str(c.get("created_at") or ""))


@router.get("/summary")
async def summarize_feed(
    category: str = Query("all"),
    limit: int = Query(40, ge=5, le=100),
    _auth: bool = Depends(verify_pin),
):
    normalized = category.lower().strip()
    # Pull a larger pool so category filters still have enough rows after dropping “both” noise.
    pool = min(max(limit * 5, 150), 400)
    clusters = db.get_clusters(limit=pool, offset=0)

    if normalized == "ai":
        filtered = [c for c in clusters if _for_ai_digest(c)]
    elif normalized == "crypto":
        filtered = [c for c in clusters if _for_crypto_digest(c)]
    elif normalized == "war":
        filtered = [c for c in clusters if _is_war_cluster(c)]
    else:
        normalized = "all"
        filtered = list(clusters)

    filtered.sort(key=_rank_cluster)
    filtered = filtered[:limit]

    summary = await summarize_feed_digest(normalized, filtered)
    headlines = [c.get("representative_title", "") for c in filtered[:8] if c.get("representative_title")]
    return {"category": normalized, "count": len(filtered), "summary": summary, "headlines": headlines}
