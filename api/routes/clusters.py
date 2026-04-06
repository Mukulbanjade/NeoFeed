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


WAR_PATTERNS = [
    re.compile(r"\bwar\b", re.I),
    re.compile(r"\bconflict\b", re.I),
    re.compile(r"\bmilitary\b", re.I),
    re.compile(r"\bmissile\b", re.I),
    re.compile(r"\bdrone\b", re.I),
    re.compile(r"\bceasefire\b", re.I),
    re.compile(r"\bsanctions\b", re.I),
    re.compile(r"\bnato\b", re.I),
    re.compile(r"\bdefense\b", re.I),
    re.compile(r"\bdefence\b", re.I),
    re.compile(r"\bairstrike\b", re.I),
    re.compile(r"\bfrontline\b", re.I),
    re.compile(r"\bgeopolitics?\b", re.I),
]


def _is_war_cluster(row: dict) -> bool:
    text = f"{row.get('representative_title', '')} {row.get('summary', '')}"
    return any(p.search(text) for p in WAR_PATTERNS)


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


@router.get("/summary")
async def summarize_feed(
    category: str = Query("all"),
    limit: int = Query(40, ge=5, le=100),
    _auth: bool = Depends(verify_pin),
):
    normalized = category.lower().strip()
    clusters = db.get_clusters(limit=limit, offset=0)

    if normalized == "ai":
        filtered = [c for c in clusters if c.get("category") in {"ai", "both"}]
    elif normalized == "crypto":
        filtered = [c for c in clusters if c.get("category") in {"crypto", "both"}]
    elif normalized == "war":
        filtered = [c for c in clusters if _is_war_cluster(c)]
    else:
        normalized = "all"
        filtered = clusters

    summary = await summarize_feed_digest(normalized, filtered)
    headlines = [c.get("representative_title", "") for c in filtered[:8] if c.get("representative_title")]
    return {"category": normalized, "count": len(filtered), "summary": summary, "headlines": headlines}
