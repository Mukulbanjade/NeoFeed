"""Main verification pipeline — orchestrates all 3 tiers."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from database.models import (
    Article, ArticleCluster, Category, RawArticle, TrustRating,
)
from database import supabase_client as db
from scrapers.sources import RSS_FEEDS, REDDIT_SUBS, TWITTER_RSS_BRIDGES
from verification.clustering import cluster_articles, assign_trust_from_cluster
from verification.heuristics import heuristic_trust, needs_llm_verification
from verification.gemini import verify_claim, summarize_cluster

logger = logging.getLogger(__name__)


def _build_reliability_map() -> dict[str, float]:
    mapping = {}
    for src in RSS_FEEDS + TWITTER_RSS_BRIDGES:
        mapping[src["name"]] = src.get("reliability", 0.5)
    for src in REDDIT_SUBS:
        mapping[src["name"]] = src.get("reliability", 0.5)
    mapping["Hacker News"] = 0.6
    return mapping


SOURCE_RELIABILITY = _build_reliability_map()
MAX_LLM_SUMMARIES_PER_RUN = 20


def _compute_recency_boost(cluster_group: list[RawArticle]) -> float:
    """Returns 0.0-2.0 points based on newest article age."""
    now = datetime.now(timezone.utc)
    published = [a.published_at for a in cluster_group if a.published_at]
    if not published:
        return 0.2
    newest = max(published)
    age_hours = max(0.0, (now - newest).total_seconds() / 3600.0)
    if age_hours <= 3:
        return 2.0
    if age_hours <= 12:
        return 1.5
    if age_hours <= 24:
        return 1.0
    if age_hours <= 72:
        return 0.6
    return 0.2


def _final_importance(base_importance: float, cluster_group: list[RawArticle], cluster_trust: TrustRating) -> float:
    """
    Blend model score with corroboration, source reliability, recency, and engagement.
    Keeps score bounded to [1, 10].
    """
    source_corroboration = min(2.0, 0.45 * (len(cluster_group) - 1))
    reliability_avg = sum(SOURCE_RELIABILITY.get(a.source_name, 0.5) for a in cluster_group) / max(len(cluster_group), 1)
    reliability_boost = (reliability_avg - 0.5) * 2.0  # approx -1..+1
    engagement_boost = min(1.0, sum(max(a.engagement, 0) for a in cluster_group) / 800.0)
    recency_boost = _compute_recency_boost(cluster_group)
    trust_boost = {
        TrustRating.VERIFIED: 0.6,
        TrustRating.LIKELY_TRUE: 0.3,
        TrustRating.UNVERIFIED: 0.0,
        TrustRating.LIKELY_FALSE: -0.7,
    }[cluster_trust]
    score = base_importance + source_corroboration + reliability_boost + engagement_boost + recency_boost + trust_boost
    return max(1.0, min(10.0, score))


def _extractive_summary(cluster_group: list[RawArticle]) -> dict:
    representative = max(cluster_group, key=lambda a: (a.engagement, len(a.content or "")))
    body = (representative.content or "").strip()
    snippet = body[:900] + ("…" if len(body) > 900 else "")
    summary = f"{representative.title}\n\n{snippet}" if snippet else representative.title
    return {
        "representative_title": representative.title,
        "summary": summary,
        "importance": 5.0,
    }


async def run_pipeline(raw_articles: list[RawArticle]) -> dict:
    """
    Full verification pipeline:
    1. Deduplicate against existing DB
    2. Cluster by similarity (Tier 1)
    3. Apply heuristics (Tier 2)
    4. LLM verify if needed (Tier 3)
    5. Summarize clusters
    6. Store everything
    """
    stats = {"total": len(raw_articles), "new": 0, "clusters": 0, "llm_calls": 0}

    # ── Step 1: Deduplicate (batch query) ──
    valid_articles = [a for a in raw_articles if a.url and a.title]
    all_urls = [a.url for a in valid_articles]
    existing_urls = db.get_existing_urls(all_urls) if all_urls else set()
    new_articles = [a for a in valid_articles if a.url not in existing_urls]

    stats["new"] = len(new_articles)
    if not new_articles:
        logger.info("No new articles to process")
        return stats

    # ── Step 2: Cluster (Tier 1) ──
    clusters = cluster_articles(new_articles)
    clusters.sort(key=lambda grp: max((a.engagement for a in grp), default=0), reverse=True)
    stats["clusters"] = len(clusters)
    logger.info(f"Formed {len(clusters)} clusters from {len(new_articles)} articles")

    # ── Process each cluster ──
    for cluster_group in clusters:
        cluster_trust = assign_trust_from_cluster(cluster_group, SOURCE_RELIABILITY)

        # ── Step 3: Heuristics (Tier 2) ──
        needs_llm = False
        for art in cluster_group:
            rel = SOURCE_RELIABILITY.get(art.source_name, 0.5)
            refined = heuristic_trust(art, cluster_trust, rel)
            if refined != cluster_trust:
                cluster_trust = refined
            if needs_llm_verification(art, cluster_trust, rel):
                needs_llm = True

        # ── Step 4: LLM Verification (Tier 3) — only if needed ──
        if needs_llm and cluster_trust == TrustRating.UNVERIFIED:
            stats["llm_calls"] += 1
            representative = max(cluster_group, key=lambda a: a.engagement)
            others = [a for a in cluster_group if a != representative]
            cluster_trust = await verify_claim(representative, others)

        # ── Step 5: Summarize cluster with LLM budget control ──
        should_llm_summarize = (
            stats["llm_calls"] < MAX_LLM_SUMMARIES_PER_RUN
            and (len(cluster_group) > 1 or max((a.engagement for a in cluster_group), default=0) >= 30)
        )
        if should_llm_summarize:
            summary_data = await summarize_cluster(cluster_group)
            stats["llm_calls"] += 1
        else:
            summary_data = _extractive_summary(cluster_group)
        base_importance = float(summary_data.get("importance", 5.0))
        cluster_importance = _final_importance(base_importance, cluster_group, cluster_trust)

        # ── Step 6: Determine category ──
        categories = [a.category for a in cluster_group]
        if Category.BOTH in categories:
            cluster_cat = Category.BOTH
        elif Category.AI in categories and Category.CRYPTO in categories:
            cluster_cat = Category.BOTH
        else:
            cluster_cat = categories[0]

        # ── Step 7: Store cluster ──
        db_cluster = db.insert_cluster(ArticleCluster(
            representative_title=summary_data.get("representative_title", cluster_group[0].title),
            summary=summary_data.get("summary", ""),
            category=cluster_cat,
            importance_score=cluster_importance,
            trust_rating=cluster_trust,
            article_count=len(cluster_group),
        ))

        cluster_id = db_cluster.get("id")

        # ── Step 8: Store articles ──
        db_articles = []
        for art in cluster_group:
            db_articles.append(Article(
                title=art.title,
                summary=summary_data.get("summary", ""),
                url=art.url,
                source_name=art.source_name,
                source_type=art.source_type,
                category=art.category,
                importance_score=cluster_importance,
                trust_rating=cluster_trust,
                cluster_id=cluster_id,
                raw_content=art.content[:5000],
                author=art.author,
                engagement=art.engagement,
                published_at=art.published_at,
            ))

        db.bulk_insert_articles(db_articles)

    logger.info(
        f"Pipeline complete: {stats['new']} new articles, "
        f"{stats['clusters']} clusters, {stats['llm_calls']} LLM calls"
    )
    return stats
