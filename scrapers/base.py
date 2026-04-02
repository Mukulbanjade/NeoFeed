from __future__ import annotations

import abc
import logging

from database.models import RawArticle

logger = logging.getLogger(__name__)


class BaseScraper(abc.ABC):
    """Base class for all news scrapers."""

    name: str = "base"

    @abc.abstractmethod
    async def scrape(self) -> list[RawArticle]:
        ...

    async def safe_scrape(self) -> list[RawArticle]:
        try:
            articles = await self.scrape()
            logger.info(f"[{self.name}] scraped {len(articles)} articles")
            return articles
        except Exception as e:
            logger.error(f"[{self.name}] scrape failed: {e}")
            return []
