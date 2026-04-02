from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from api.middleware import verify_pin
from database import supabase_client as db
from database.models import Category
from personalization.engine import preference_engine

router = APIRouter(prefix="/clusters", tags=["clusters"])


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

    return {"clusters": clusters, "count": len(clusters)}
