"""Advanced personalization engine with preference learning."""

from __future__ import annotations

import logging
import re
from collections import Counter, defaultdict

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from database import supabase_client as db
from database.models import VoteType

logger = logging.getLogger(__name__)


class PreferenceEngine:
    """Learns user preferences from upvote/downvote history and re-ranks articles."""

    def __init__(self):
        self._vectorizer = TfidfVectorizer(max_features=500, stop_words="english")
        self._preference_vector: np.ndarray | None = None

    async def update_from_votes(self) -> dict:
        """Rebuild preference model from all vote history."""
        votes = db.get_votes(limit=1000)
        if not votes:
            return {}

        up_articles = []
        down_articles = []

        for vote in votes:
            article_id = vote.get("article_id")
            if not article_id:
                continue
            article = db.get_article_by_id(article_id)
            if not article:
                continue
            text = f"{article['title']} {article.get('raw_content', '')[:500]}"
            if vote["vote"] == VoteType.UP.value:
                up_articles.append((text, article))
            else:
                down_articles.append((text, article))

        # Build topic weights from vote patterns
        topic_weights = self._compute_topic_weights(up_articles, down_articles)
        source_weights = self._compute_source_weights(up_articles, down_articles)

        # Build TF-IDF preference vector
        preference_vector = {}
        if up_articles:
            all_texts = [t for t, _ in up_articles + down_articles]
            if all_texts:
                try:
                    tfidf = self._vectorizer.fit_transform(all_texts)
                    feature_names = self._vectorizer.get_feature_names_out()

                    up_mean = tfidf[:len(up_articles)].mean(axis=0).A1
                    if down_articles:
                        down_mean = tfidf[len(up_articles):].mean(axis=0).A1
                        diff = up_mean - down_mean
                    else:
                        diff = up_mean

                    top_indices = diff.argsort()[-50:][::-1]
                    preference_vector = {
                        feature_names[i]: float(diff[i])
                        for i in top_indices
                        if diff[i] > 0
                    }
                except Exception as e:
                    logger.error(f"TF-IDF preference computation failed: {e}")

        prefs = {
            "preference_vector": preference_vector,
            "topic_weights": topic_weights,
            "source_weights": source_weights,
        }
        db.update_preferences(prefs)
        logger.info(f"Updated preferences: {len(preference_vector)} keywords, {len(topic_weights)} topics, {len(source_weights)} sources")
        return prefs

    def _compute_topic_weights(
        self,
        up: list[tuple[str, dict]],
        down: list[tuple[str, dict]],
    ) -> dict[str, float]:
        up_cats = Counter(a.get("category", "ai") for _, a in up)
        down_cats = Counter(a.get("category", "ai") for _, a in down)

        weights = {}
        all_cats = set(list(up_cats.keys()) + list(down_cats.keys()))
        for cat in all_cats:
            u = up_cats.get(cat, 0)
            d = down_cats.get(cat, 0)
            total = u + d
            if total > 0:
                weights[cat] = (u - d) / total
            else:
                weights[cat] = 0.0

        return weights

    def _compute_source_weights(
        self,
        up: list[tuple[str, dict]],
        down: list[tuple[str, dict]],
    ) -> dict[str, float]:
        up_sources = Counter(a.get("source_name", "") for _, a in up)
        down_sources = Counter(a.get("source_name", "") for _, a in down)

        weights = {}
        all_sources = set(list(up_sources.keys()) + list(down_sources.keys()))
        for src in all_sources:
            u = up_sources.get(src, 0)
            d = down_sources.get(src, 0)
            total = u + d
            if total > 0:
                weights[src] = (u - d) / total
            else:
                weights[src] = 0.0

        return weights

    def score_article(self, article: dict, preferences: dict | None = None) -> float:
        """Score an article based on learned preferences. Higher = more relevant."""
        if not preferences:
            return article.get("importance_score", 5.0)

        base_score = article.get("importance_score", 5.0)

        # Topic boost
        topic_weights = preferences.get("topic_weights", {})
        cat = article.get("category", "ai")
        topic_boost = topic_weights.get(cat, 0.0) * 2.0

        # Source boost
        source_weights = preferences.get("source_weights", {})
        src = article.get("source_name", "")
        source_boost = source_weights.get(src, 0.0) * 1.5

        # Keyword boost from preference vector
        pref_vector = preferences.get("preference_vector", {})
        keyword_boost = 0.0
        if pref_vector:
            text = f"{article.get('title', '')} {article.get('summary', '')}".lower()
            for keyword, weight in pref_vector.items():
                if keyword in text:
                    keyword_boost += weight * 0.5

        final = base_score + topic_boost + source_boost + min(keyword_boost, 3.0)
        return max(0.0, min(10.0, final))

    def rerank_articles(self, articles: list[dict], preferences: dict | None = None) -> list[dict]:
        """Re-rank articles list based on user preferences."""
        if not preferences:
            return articles

        for art in articles:
            art["personalized_score"] = self.score_article(art, preferences)

        return sorted(articles, key=lambda a: a.get("personalized_score", 0), reverse=True)


preference_engine = PreferenceEngine()
