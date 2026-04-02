from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from supabase import create_client, Client

from config import settings
from database.models import (
    Article, ArticleCluster, Category, RawArticle,
    TrustRating, Vote, VoteType, UserPreferences,
)

logger = logging.getLogger(__name__)

_client: Client | None = None


def get_client() -> Client:
    global _client
    if _client is None:
        _client = create_client(settings.supabase_url, settings.supabase_service_role_key)
    return _client


# ── Articles ────────────────────────────────────────────────────────────────

def url_exists(url: str) -> bool:
    res = get_client().table("articles").select("id").eq("url", url).execute()
    return len(res.data) > 0


def get_existing_urls(urls: list[str]) -> set[str]:
    """Batch check which URLs already exist. Much faster than per-URL queries."""
    existing: set[str] = set()
    batch_size = 50
    for i in range(0, len(urls), batch_size):
        batch = urls[i:i + batch_size]
        res = get_client().table("articles").select("url").in_("url", batch).execute()
        existing.update(row["url"] for row in res.data)
    return existing


def insert_article(article: Article) -> dict:
    payload = article.model_dump(exclude={"id", "created_at"}, exclude_none=True)
    if article.published_at:
        payload["published_at"] = article.published_at.isoformat()
    res = get_client().table("articles").insert(payload).execute()
    return res.data[0] if res.data else {}


def bulk_insert_articles(articles: list[Article]) -> list[dict]:
    seen_urls: set[str] = set()
    payloads = []
    for a in articles:
        if a.url in seen_urls:
            continue
        seen_urls.add(a.url)
        p = a.model_dump(exclude={"id", "created_at"}, exclude_none=True)
        if a.published_at:
            p["published_at"] = a.published_at.isoformat()
        payloads.append(p)
    if not payloads:
        return []
    res = get_client().table("articles").upsert(payloads, on_conflict="url").execute()
    return res.data


def get_articles(
    category: Category | None = None,
    trust_rating: TrustRating | None = None,
    limit: int = 50,
    offset: int = 0,
    min_importance: float = 0.0,
) -> list[dict]:
    q = get_client().table("articles").select("*").order("created_at", desc=True)
    if category:
        q = q.eq("category", category.value)
    if trust_rating:
        q = q.eq("trust_rating", trust_rating.value)
    if min_importance > 0:
        q = q.gte("importance_score", min_importance)
    q = q.range(offset, offset + limit - 1)
    return q.execute().data


def get_article_by_id(article_id: str) -> dict | None:
    res = get_client().table("articles").select("*").eq("id", article_id).execute()
    return res.data[0] if res.data else None


def get_recent_articles(hours: int = 48) -> list[dict]:
    cutoff = datetime.now(timezone.utc).isoformat()
    res = (
        get_client()
        .table("articles")
        .select("*")
        .order("created_at", desc=True)
        .limit(500)
        .execute()
    )
    return res.data


def update_article(article_id: str, updates: dict) -> dict:
    res = get_client().table("articles").update(updates).eq("id", article_id).execute()
    return res.data[0] if res.data else {}


# ── Clusters ────────────────────────────────────────────────────────────────

def insert_cluster(cluster: ArticleCluster) -> dict:
    payload = cluster.model_dump(exclude={"id", "created_at"}, exclude_none=True)
    res = get_client().table("clusters").insert(payload).execute()
    return res.data[0] if res.data else {}


def get_clusters(
    category: Category | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    q = get_client().table("clusters").select("*").order("created_at", desc=True)
    if category:
        q = q.eq("category", category.value)
    q = q.range(offset, offset + limit - 1)
    return q.execute().data


def get_cluster_articles(cluster_id: str) -> list[dict]:
    return (
        get_client()
        .table("articles")
        .select("*")
        .eq("cluster_id", cluster_id)
        .order("engagement", desc=True)
        .execute()
        .data
    )


def update_cluster(cluster_id: str, updates: dict) -> dict:
    res = get_client().table("clusters").update(updates).eq("id", cluster_id).execute()
    return res.data[0] if res.data else {}


# ── Votes ───────────────────────────────────────────────────────────────────

def insert_vote(vote: Vote) -> dict:
    payload = vote.model_dump(exclude={"id", "created_at"}, exclude_none=True)
    res = get_client().table("votes").insert(payload).execute()
    return res.data[0] if res.data else {}


def get_votes(limit: int = 200) -> list[dict]:
    return (
        get_client()
        .table("votes")
        .select("*")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
        .data
    )


# ── Preferences ─────────────────────────────────────────────────────────────

def get_preferences() -> dict | None:
    res = get_client().table("preferences").select("*").limit(1).execute()
    return res.data[0] if res.data else None


def update_preferences(prefs: dict) -> dict:
    existing = get_preferences()
    prefs["updated_at"] = datetime.now(timezone.utc).isoformat()
    if existing:
        res = (
            get_client()
            .table("preferences")
            .update(prefs)
            .eq("id", existing["id"])
            .execute()
        )
    else:
        res = get_client().table("preferences").insert(prefs).execute()
    return res.data[0] if res.data else {}


# ── Digests ─────────────────────────────────────────────────────────────────

def log_digest(channel: str, article_ids: list[str]) -> dict:
    payload = {
        "channel": channel,
        "article_ids": article_ids,
        "sent_at": datetime.now(timezone.utc).isoformat(),
    }
    res = get_client().table("digests").insert(payload).execute()
    return res.data[0] if res.data else {}


def get_last_digest(channel: str) -> dict | None:
    res = (
        get_client()
        .table("digests")
        .select("*")
        .eq("channel", channel)
        .order("sent_at", desc=True)
        .limit(1)
        .execute()
    )
    return res.data[0] if res.data else None
