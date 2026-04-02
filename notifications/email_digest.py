"""Email digest via Resend."""

from __future__ import annotations

import logging

import resend

from config import settings
from database import supabase_client as db

logger = logging.getLogger(__name__)

TRUST_LABELS = {
    "verified": "✅ Verified",
    "likely_true": "🟢 Likely True",
    "unverified": "🟡 Unverified",
    "likely_false": "🔴 Likely False",
}


def _build_html(articles: list[dict]) -> str:
    rows = ""
    for a in articles:
        trust = TRUST_LABELS.get(a.get("trust_rating", "unverified"), "❓")
        importance = a.get("importance_score", 5)
        stars = "⭐" * min(int(importance / 2), 5)

        rows += f"""
        <tr style="border-bottom: 1px solid #003B00;">
            <td style="padding: 16px; color: #00FF41;">
                <div style="font-size: 11px; color: #00AA30; margin-bottom: 4px;">
                    {trust} | {a.get('source_name', '')} | {a.get('category', 'ai').upper()} | {stars}
                </div>
                <a href="{a.get('url', '#')}" style="color: #00FF41; font-size: 16px; text-decoration: none; font-weight: bold;">
                    {a.get('title', '')}
                </a>
                <div style="color: #008830; margin-top: 8px; font-size: 13px;">
                    {a.get('summary', '')[:250]}
                </div>
            </td>
        </tr>
        """

    return f"""
    <html>
    <body style="background-color: #0D0D0D; color: #00FF41; font-family: 'Courier New', monospace; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto;">
            <h1 style="text-align: center; color: #00FF41; border: 1px solid #003B00; padding: 20px; letter-spacing: 8px;">
                N E O F E E D
            </h1>
            <p style="text-align: center; color: #008830;">Your AI & Crypto Intelligence Briefing</p>
            <table style="width: 100%; border-collapse: collapse;">
                {rows}
            </table>
            <p style="text-align: center; color: #003B00; margin-top: 30px; font-size: 11px;">
                NeoFeed — The Matrix has your news.
            </p>
        </div>
    </body>
    </html>
    """


async def send_email_digest():
    """Send email digest of top articles."""
    if not settings.resend_api_key or not settings.email_to:
        logger.warning("Email not configured, skipping")
        return

    articles = db.get_articles(limit=15, min_importance=4.0)
    if not articles:
        logger.info("No articles for email digest")
        return

    resend.api_key = settings.resend_api_key

    try:
        html = _build_html(articles)
        resend.Emails.send({
            "from": "NeoFeed <neofeed@resend.dev>",
            "to": [settings.email_to],
            "subject": "⚡ NeoFeed Digest — AI & Crypto Intelligence",
            "html": html,
        })
        db.log_digest("email", [a["id"] for a in articles])
        logger.info(f"Email digest sent to {settings.email_to}")
    except Exception as e:
        logger.error(f"Email digest failed: {e}")
