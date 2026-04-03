from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from api.middleware import verify_pin
from database import supabase_client as db
from database.models import Category
from personalization.engine import preference_engine

router = APIRouter(prefix="/clusters", tags=["clusters"])


def _cluster_with_aliases(row: dict) -> dict:
    """Expose trust_level / source_count aliases for clients expecting Lovable-style field names."""
    out = dict(row)
    if "trust_rating" in out and "trust_level" not in out:
        out["trust_level"] = out["trust_rating"]
    if "article_count" in out and "source_count" not in out:
        out["source_count"] = out["article_count"]
    return out


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
