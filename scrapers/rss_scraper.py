from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

import feedparser
import httpx
from bs4 import BeautifulSoup

from database.models import Category, RawArticle
from scrapers.base import BaseScraper
from scrapers.sources import RSS_FEEDS, TWITTER_RSS_BRIDGES

logger = logging.getLogger(__name__)

RELEVANCE_PATTERNS = [
    r"\bai\b", r"\bartificial intelligence\b", r"\bmachine learning\b", r"\bllm\b",
    r"\bgpt\b", r"\bopenai\b", r"\banthropic\b", r"\bclaude\b", r"\bgemini\b",
    r"\btransformer\b", r"\bneural\b", r"\bdeep learning\b", r"\bdiffusion\b",
    r"\bcopilot\b", r"\bchatgpt\b", r"\bmodel\b", r"\btraining\b",
    r"\bcrypto\b", r"\bbitcoin\b", r"\bethereum\b", r"\bblockchain\b",
    r"\bdefi\b", r"\bnft\b", r"\bweb3\b", r"\bstablecoin\b", r"\btokenized\b",
    r"\bmining\b", r"\bsolana\b", r"\bbinance\b", r"\bcoinbase\b",
    r"\bdata center\b", r"\bchip\b", r"\bgpu\b", r"\bsemiconductor\b",
    r"\brobot\b", r"\bautonomous\b", r"\bfoundation model\b",
    r"\bwar\b", r"\bconflict\b", r"\bmilitary\b", r"\bmissile\b", r"\bdrone\b",
    r"\bceasefire\b", r"\bsanctions\b", r"\bnato\b", r"\bdefense\b", r"\bdefence\b",
    r"\bexplosion\b", r"\bstrike\b", r"\bfrontline\b", r"\bintelligence\b",
    r"\bleak\b", r"\bsource code\b", r"\bbreach\b", r"\bexploit\b",
    r"\bvulnerability\b", r"\bzero-day\b", r"\bransomware\b", r"\bmalware\b",
    r"\bgithub\b", r"\bcritical infrastructure\b", r"\bstate actor\b",
]


def _is_relevant(title: str, content: str) -> bool:
    text = f"{title} {content[:500]}".lower()
    return any(re.search(p, text) for p in RELEVANCE_PATTERNS)


def _clean_html(text: str) -> str:
    if not text:
        return ""
    # Convert rich RSS summary HTML into readable plain text.
    plain = BeautifulSoup(text, "html.parser").get_text(" ", strip=True)
    return re.sub(r"\s+", " ", plain).strip()


class RssScraper(BaseScraper):
    """Scrapes RSS feeds including Nitter/RSSHub Twitter bridges."""

    name = "rss"

    def __init__(self, feeds: list[dict] | None = None):
        self.feeds = feeds or RSS_FEEDS + TWITTER_RSS_BRIDGES
        self.entries_per_feed = 50

    async def scrape(self) -> list[RawArticle]:
        articles: list[RawArticle] = []
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            for feed_cfg in self.feeds:
                try:
                    resp = await client.get(feed_cfg["url"])
                    if resp.status_code != 200:
                        logger.warning(f"RSS {feed_cfg['name']}: HTTP {resp.status_code}")
                        continue
                    parsed = feedparser.parse(resp.text)
                    for entry in parsed.entries[: self.entries_per_feed]:
                        article = self._entry_to_article(entry, feed_cfg)
                        if feed_cfg.get("needs_filter") and not _is_relevant(article.title, article.content):
                            continue
                        articles.append(article)
                except Exception as e:
                    logger.warning(f"RSS {feed_cfg['name']}: {e}")
        return articles

    @staticmethod
    def _entry_to_article(entry: dict, feed_cfg: dict) -> RawArticle:
        published = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            except Exception:
                pass

        content = ""
        if hasattr(entry, "summary"):
            content = _clean_html(entry.summary)
        elif hasattr(entry, "content") and entry.content:
            content = _clean_html(entry.content[0].get("value", ""))

        source_type = "twitter" if "rsshub" in feed_cfg["url"] or "nitter" in feed_cfg["url"] else "rss"

        return RawArticle(
            title=entry.get("title", "").strip(),
            url=entry.get("link", ""),
            content=content,
            source_name=feed_cfg["name"],
            source_type=source_type,
            category=feed_cfg.get("category", Category.AI),
            published_at=published,
        )
