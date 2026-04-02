"""Tier 1: Keyword & similarity-based clustering (zero LLM cost)."""

from __future__ import annotations

import logging
import re
from collections import defaultdict

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from database.models import RawArticle, TrustRating

logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD = 0.35


def _clean(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"[^\w\s]", " ", text.lower())
    return re.sub(r"\s+", " ", text).strip()


def cluster_articles(
    articles: list[RawArticle],
) -> list[list[RawArticle]]:
    """Group articles into clusters based on TF-IDF cosine similarity."""
    if len(articles) < 2:
        return [[a] for a in articles]

    docs = [_clean(f"{a.title} {a.content[:500]}") for a in articles]
    docs = [d if d.strip() else "empty" for d in docs]

    vectorizer = TfidfVectorizer(
        max_features=5000,
        stop_words="english",
        ngram_range=(1, 2),
    )
    tfidf_matrix = vectorizer.fit_transform(docs)
    sim_matrix = cosine_similarity(tfidf_matrix)

    visited = set()
    clusters: list[list[RawArticle]] = []

    for i in range(len(articles)):
        if i in visited:
            continue
        cluster = [i]
        visited.add(i)
        for j in range(i + 1, len(articles)):
            if j in visited:
                continue
            if sim_matrix[i][j] >= SIMILARITY_THRESHOLD:
                cluster.append(j)
                visited.add(j)
        clusters.append([articles[idx] for idx in cluster])

    return clusters


def assign_trust_from_cluster(
    cluster: list[RawArticle],
    source_reliability: dict[str, float] | None = None,
) -> TrustRating:
    """Tier 1 trust assignment based on cluster size and source diversity."""
    source_reliability = source_reliability or {}
    unique_sources = {a.source_name for a in cluster}
    source_types = {a.source_type for a in cluster}

    if len(unique_sources) >= 3:
        return TrustRating.VERIFIED
    if len(unique_sources) >= 2:
        max_rel = max(
            source_reliability.get(a.source_name, 0.5) for a in cluster
        )
        if max_rel >= 0.8:
            return TrustRating.VERIFIED
        return TrustRating.LIKELY_TRUE

    single = cluster[0]
    rel = source_reliability.get(single.source_name, 0.5)
    if rel >= 0.85:
        return TrustRating.LIKELY_TRUE

    return TrustRating.UNVERIFIED
