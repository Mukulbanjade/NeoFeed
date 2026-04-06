"""Scheduled jobs for scraping, processing, and notifications."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from scrapers.rss_scraper import RssScraper
from scrapers.reddit_scraper import RedditScraper
from scrapers.hn_scraper import HackerNewsScraper
from verification.pipeline import run_pipeline
from database.models import RawArticle

logger = logging.getLogger(__name__)

_last_scrape_started_at: datetime | None = None
_last_scrape_completed_at: datetime | None = None
_last_scrape_success: bool | None = None
_last_scrape_error: str = ""
_last_pipeline_stats: dict = {}


async def scrape_and_process():
    """Main job: scrape all sources, run verification pipeline."""
    global _last_scrape_started_at
    global _last_scrape_completed_at
    global _last_scrape_success
    global _last_scrape_error
    global _last_pipeline_stats

    _last_scrape_started_at = datetime.now(timezone.utc)
    _last_scrape_error = ""
    _last_pipeline_stats = {}
    logger.info("Starting scrape cycle...")

    try:
        scrapers = [RssScraper(), RedditScraper(), HackerNewsScraper()]
        source_counts: dict[str, int] = {}
        all_articles: list[RawArticle] = []
        for scraper in scrapers:
            articles = await scraper.safe_scrape()
            source_counts[scraper.name] = len(articles)
            all_articles.extend(articles)

        logger.info(f"Total scraped: {len(all_articles)} articles")

        if all_articles:
            stats = await run_pipeline(all_articles)
            _last_pipeline_stats = {
                "scraped_total": len(all_articles),
                "source_counts": source_counts,
                **stats,
            }
            logger.info(f"Pipeline stats: {_last_pipeline_stats}")
        else:
            _last_pipeline_stats = {
                "scraped_total": 0,
                "source_counts": source_counts,
                "total": 0,
                "new": 0,
                "clusters": 0,
                "llm_calls": 0,
            }
            logger.info("No articles scraped")
        _last_scrape_success = True
    except Exception as e:
        _last_scrape_success = False
        _last_scrape_error = str(e)
        logger.exception("Scrape cycle failed")
        raise
    finally:
        _last_scrape_completed_at = datetime.now(timezone.utc)


def run_scrape_sync():
    """Sync wrapper for APScheduler."""
    asyncio.run(scrape_and_process())


def get_scrape_status() -> dict:
    return {
        "last_scrape_started_at": _last_scrape_started_at.isoformat() if _last_scrape_started_at else None,
        "last_scrape_completed_at": _last_scrape_completed_at.isoformat() if _last_scrape_completed_at else None,
        "last_scrape_success": _last_scrape_success,
        "last_scrape_error": _last_scrape_error,
        "last_pipeline_stats": _last_pipeline_stats,
    }
