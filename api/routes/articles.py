from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from api.middleware import verify_pin
from database import supabase_client as db
from database.models import Category, TrustRating
from personalization.engine import preference_engine

router = APIRouter(prefix="/articles", tags=["articles"])


@router.get("/")
async def list_articles(
    category: Category | None = None,
    trust: TrustRating | None = None,
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    min_importance: float = Query(0.0, ge=0, le=10),
    personalized: bool = Query(False),
    _auth: bool = Depends(verify_pin),
):
    articles = db.get_articles(
        category=category,
        trust_rating=trust,
        limit=limit,
        offset=offset,
        min_importance=min_importance,
    )

    if personalized:
        prefs = db.get_preferences()
        if prefs:
            articles = preference_engine.rerank_articles(articles, prefs)

    return {"articles": articles, "count": len(articles)}


@router.get("/cluster/{cluster_id}")
async def get_cluster_articles(cluster_id: str, _auth: bool = Depends(verify_pin)):
    articles = db.get_cluster_articles(cluster_id)
    for row in articles:
        if row.get("source_name") and not row.get("source"):
            row["source"] = row["source_name"]
    return {"articles": articles, "count": len(articles)}


@router.get("/{article_id}")
async def get_article(article_id: str, _auth: bool = Depends(verify_pin)):
    article = db.get_article_by_id(article_id)
    if not article:
        return {"error": "Article not found"}
    return article
