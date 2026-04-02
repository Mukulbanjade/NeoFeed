from __future__ import annotations

import logging
from datetime import datetime, timezone

import asyncpraw

from config import settings
from database.models import Category, RawArticle
from scrapers.base import BaseScraper
from scrapers.sources import REDDIT_SUBS

logger = logging.getLogger(__name__)


class RedditScraper(BaseScraper):
    name = "reddit"

    def __init__(self, subs: list[dict] | None = None):
        self.subs = subs or REDDIT_SUBS

    async def scrape(self) -> list[RawArticle]:
        if not settings.reddit_client_id or not settings.reddit_client_secret:
            logger.warning("Reddit credentials not configured, skipping")
            return []

        articles: list[RawArticle] = []
        reddit = asyncpraw.Reddit(
            client_id=settings.reddit_client_id,
            client_secret=settings.reddit_client_secret,
            user_agent=settings.reddit_user_agent,
        )

        try:
            for sub_cfg in self.subs:
                try:
                    subreddit = await reddit.subreddit(sub_cfg["subreddit"])
                    async for post in subreddit.hot(limit=15):
                        if post.stickied:
                            continue
                        articles.append(RawArticle(
                            title=post.title,
                            url=f"https://reddit.com{post.permalink}" if not post.is_self else post.url,
                            content=post.selftext[:2000] if post.is_self else "",
                            source_name=sub_cfg["name"],
                            source_type="reddit",
                            category=sub_cfg.get("category", Category.AI),
                            published_at=datetime.fromtimestamp(post.created_utc, tz=timezone.utc),
                            author=str(post.author) if post.author else "",
                            engagement=post.score,
                        ))
                except Exception as e:
                    logger.warning(f"Reddit {sub_cfg['subreddit']}: {e}")
        finally:
            await reddit.close()

        return articles
