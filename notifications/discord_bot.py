"""Discord bot for NeoFeed news delivery."""

from __future__ import annotations

import asyncio
import logging

import discord

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
    stars = "\u2b50" * min(int(importance / 2), 5)

    return (
        f"{emoji} **{article['title']}**\n"
        f"{stars} | {article.get('source_name', 'Unknown')} | "
        f"`{article.get('category', 'ai').upper()}`\n"
        f"{article.get('summary', '')[:200]}\n"
        f"{article.get('url', '')}\n"
        f"{'─' * 40}"
    )


async def send_digest_to_discord():
    """Send top articles to the configured Discord channel."""
    if not settings.discord_bot_token or not settings.discord_channel_id:
        logger.warning("Discord not configured, skipping")
        return

    articles = db.get_articles(limit=10, min_importance=5.0)
    if not articles:
        logger.info("No articles for Discord digest")
        return

    intents = discord.Intents.default()
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        try:
            channel = client.get_channel(int(settings.discord_channel_id))
            if not channel:
                channel = await client.fetch_channel(int(settings.discord_channel_id))

            header = (
                "```\n"
                "╔══════════════════════════════════════╗\n"
                "║        N E O F E E D  DIGEST         ║\n"
                "╚══════════════════════════════════════╝\n"
                "```"
            )
            await channel.send(header)

            for article in articles[:10]:
                msg = _format_article(article)
                await channel.send(msg)

            db.log_digest("discord", [a["id"] for a in articles])
            logger.info(f"Discord digest sent: {len(articles)} articles")
        except Exception as e:
            logger.error(f"Discord send failed: {e}")
        finally:
            await client.close()

    await client.start(settings.discord_bot_token)


async def send_breaking_news(article: dict):
    """Send a single breaking news alert to Discord."""
    if not settings.discord_bot_token or not settings.discord_channel_id:
        return

    intents = discord.Intents.default()
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        try:
            channel = client.get_channel(int(settings.discord_channel_id))
            if not channel:
                channel = await client.fetch_channel(int(settings.discord_channel_id))

            msg = f"\U0001f6a8 **BREAKING** \U0001f6a8\n{_format_article(article)}"
            await channel.send(msg)
        except Exception as e:
            logger.error(f"Discord breaking news failed: {e}")
        finally:
            await client.close()

    await client.start(settings.discord_bot_token)
