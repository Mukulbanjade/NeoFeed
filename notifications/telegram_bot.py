"""Telegram bot for NeoFeed news delivery."""

from __future__ import annotations

import logging

from telegram import Bot
from telegram.constants import ParseMode

from config import settings
from database import supabase_client as db

logger = logging.getLogger(__name__)

TRUST_EMOJI = {
    "verified": "\u2705",
    "likely_true": "\U0001f7e2",
    "unverified": "\U0001f7e1",
    "likely_false": "\U0001f534",
}


def _format_article(article: dict) -> str:
    trust = article.get("trust_rating", "unverified")
    emoji = TRUST_EMOJI.get(trust, "\u2753")
    importance = article.get("importance_score", 5)

    title = article.get("title", "").replace("<", "&lt;").replace(">", "&gt;")
    summary = article.get("summary", "")[:200].replace("<", "&lt;").replace(">", "&gt;")
    url = article.get("url", "")

    return (
        f"{emoji} <b>{title}</b>\n"
        f"{'⭐' * min(int(importance / 2), 5)} | {article.get('source_name', 'Unknown')} | "
        f"<code>{article.get('category', 'ai').upper()}</code>\n"
        f"{summary}\n"
        f"<a href=\"{url}\">Read more →</a>"
    )


async def send_digest_to_telegram():
    """Send top articles to the configured Telegram chat."""
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        logger.warning("Telegram not configured, skipping")
        return

    articles = db.get_articles(limit=10, min_importance=5.0)
    if not articles:
        logger.info("No articles for Telegram digest")
        return

    bot = Bot(token=settings.telegram_bot_token)

    header = (
        "╔══════════════════════════════════════╗\n"
        "║        N E O F E E D  DIGEST         ║\n"
        "╚══════════════════════════════════════╝"
    )

    try:
        await bot.send_message(
            chat_id=settings.telegram_chat_id,
            text=f"<pre>{header}</pre>",
            parse_mode=ParseMode.HTML,
        )

        for article in articles[:10]:
            msg = _format_article(article)
            await bot.send_message(
                chat_id=settings.telegram_chat_id,
                text=msg,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=False,
            )

        db.log_digest("telegram", [a["id"] for a in articles])
        logger.info(f"Telegram digest sent: {len(articles)} articles")
    except Exception as e:
        logger.error(f"Telegram send failed: {e}")


async def send_breaking_news(article: dict):
    """Send a single breaking news alert via Telegram."""
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        return

    bot = Bot(token=settings.telegram_bot_token)
    msg = f"🚨 <b>BREAKING</b> 🚨\n\n{_format_article(article)}"

    try:
        await bot.send_message(
            chat_id=settings.telegram_chat_id,
            text=msg,
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        logger.error(f"Telegram breaking news failed: {e}")
