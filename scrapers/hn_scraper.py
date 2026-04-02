from __future__ import annotations

import logging
from datetime import datetime, timezone

import re

import httpx

from database.models import Category, RawArticle
from scrapers.base import BaseScraper
from scrapers.sources import HN_CONFIG

logger = logging.getLogger(__name__)

HN_TOP_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{}.json"

AI_KEYWORDS = [
    r"\bai\b", r"\bartificial intelligence\b", r"\bmachine learning\b", r"\bllm\b", r"\bgpt\b",
    r"\bopenai\b", r"\banthropic\b", r"\bclaude\b", r"\bgemini\b", r"\btransformer\b", r"\bneural\b",
    r"\bdeep learning\b", r"\bdiffusion\b", r"\bstable diffusion\b", r"\bmidjourney\b",
    r"\bcopilot\b", r"\bchatgpt\b", r"\blangchain\b", r"\bhugging face\b", r"\bmeta ai\b",
    r"\bllama\b", r"\bmistral\b", r"\btraining\b", r"\binference\b", r"\bagi\b",
    r"\bfoundation model\b", r"\bgenerative\b", r"\bsora\b", r"\bgemma\b",
]

CRYPTO_KEYWORDS = [
    r"\bcrypto\b", r"\bbitcoin\b", r"\bbtc\b", r"\bethereum\b", r"\beth\b", r"\bsolana\b",
    r"\bblockchain\b", r"\bdefi\b", r"\bnft\b", r"\bweb3\b", r"\bmining\b",
    r"\bwallet\b", r"\bbinance\b", r"\bcoinbase\b", r"\bstablecoin\b",
    r"\bdao\b", r"\bairdrop\b", r"\bhalving\b", r"\blayer 2\b", r"\brollup\b",
    r"\bonchain\b", r"\bon-chain\b", r"\btokenized\b", r"\busdc\b", r"\busdt\b",
]


def _classify(title: str) -> Category | None:
    t = title.lower()
    is_ai = any(re.search(kw, t) for kw in AI_KEYWORDS)
    is_crypto = any(re.search(kw, t) for kw in CRYPTO_KEYWORDS)
    if is_ai and is_crypto:
        return Category.BOTH
    if is_ai:
        return Category.AI
    if is_crypto:
        return Category.CRYPTO
    return None


class HackerNewsScraper(BaseScraper):
    name = "hackernews"

    async def scrape(self) -> list[RawArticle]:
        articles: list[RawArticle] = []
        max_stories = HN_CONFIG["max_stories"]

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(HN_TOP_URL)
            story_ids = resp.json()[:max_stories * 3]

            for sid in story_ids:
                if len(articles) >= max_stories:
                    break
                try:
                    item_resp = await client.get(HN_ITEM_URL.format(sid))
                    item = item_resp.json()
                    if not item or item.get("type") != "story":
                        continue

                    title = item.get("title", "")
                    category = _classify(title)
                    if category is None:
                        continue

                    url = item.get("url", f"https://news.ycombinator.com/item?id={sid}")
                    articles.append(RawArticle(
                        title=title,
                        url=url,
                        content="",
                        source_name="Hacker News",
                        source_type="hn",
                        category=category,
                        published_at=datetime.fromtimestamp(item.get("time", 0), tz=timezone.utc),
                        author=item.get("by", ""),
                        engagement=item.get("score", 0),
                    ))
                except Exception as e:
                    logger.debug(f"HN item {sid}: {e}")

        return articles
