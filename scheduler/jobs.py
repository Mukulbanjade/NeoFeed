"""Scheduled jobs for scraping, processing, and notifications."""

from __future__ import annotations

import asyncio
import logging

from scrapers.rss_scraper import RssScraper
from scrapers.reddit_scraper import RedditScraper
from scrapers.hn_scraper import HackerNewsScraper
from verification.pipeline import run_pipeline
from database.models import RawArticle

logger = logging.getLogger(__name__)


async def scrape_and_process():
    """Main job: scrape all sources, run verification pipeline."""
    logger.info("Starting scrape cycle...")

    scrapers = [RssScraper(), RedditScraper(), HackerNewsScraper()]

    all_articles: list[RawArticle] = []
    for scraper in scrapers:
        articles = await scraper.safe_scrape()
        all_articles.extend(articles)

    logger.info(f"Total scraped: {len(all_articles)} articles")

    if all_articles:
        stats = await run_pipeline(all_articles)
        logger.info(f"Pipeline stats: {stats}")
    else:
        logger.info("No articles scraped")


def run_scrape_sync():
    """Sync wrapper for APScheduler."""
    asyncio.run(scrape_and_process())
