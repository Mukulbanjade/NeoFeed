"""NeoFeed — AI & Crypto News Aggregator with Trust Verification."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from api.routes import articles, auth, clusters, votes, preferences
from scheduler.jobs import scrape_and_process
from notifications.discord_bot import send_digest_to_discord
from notifications.telegram_bot import send_digest_to_telegram
from notifications.email_digest import send_email_digest

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("neofeed")

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Scraping job
    scheduler.add_job(
        scrape_and_process,
        trigger=IntervalTrigger(minutes=settings.scrape_interval_minutes),
        id="scrape",
        name="Scrape and process news",
        replace_existing=True,
    )

    # Digest jobs
    for hour in settings.digest_hour_list:
        scheduler.add_job(
            _send_all_digests,
            trigger=CronTrigger(hour=hour, minute=0),
            id=f"digest_{hour}",
            name=f"Send digest at {hour}:00",
            replace_existing=True,
        )

    scheduler.start()
    logger.info("NeoFeed started — scheduler running")

    # Run initial scrape on startup
    asyncio.create_task(scrape_and_process())

    yield

    scheduler.shutdown()
    logger.info("NeoFeed shutting down")


async def _send_all_digests():
    await send_digest_to_discord()
    await send_digest_to_telegram()
    await send_email_digest()


app = FastAPI(
    title="NeoFeed",
    description="AI & Crypto News Aggregator with Trust Verification",
    version="1.0.0",
    lifespan=lifespan,
)

# allow_credentials=False so allow_origins=["*"] is valid with custom headers (X-Pin).
# Browsers reject * + credentials=true; that broke Vercel → Render fetches.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(articles.router)
app.include_router(clusters.router)
app.include_router(votes.router)
app.include_router(preferences.router)


@app.get("/")
async def root():
    return {
        "name": "NeoFeed",
        "version": "1.0.0",
        "status": "online",
        "message": "The Matrix has your news.",
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


# #region agent log — temporary diagnostic (remove after debugging)
@app.get("/debug/pin-check")
async def debug_pin_check():
    """Temporary endpoint to diagnose PIN_HASH issues on Render."""
    import bcrypt as _bcrypt
    ph = settings.pin_hash
    info = {
        "pin_hash_length": len(ph) if ph else 0,
        "pin_hash_set": bool(ph),
        "pin_hash_starts_with_dollar": ph.startswith("$") if ph else None,
        "pin_hash_prefix": ph[:7] if ph and len(ph) > 7 else ph[:3] if ph else "",
    }
    if ph:
        try:
            result = _bcrypt.checkpw(b"5585", ph.encode())
            info["checkpw_result"] = result
            info["checkpw_error"] = None
        except Exception as e:
            info["checkpw_result"] = None
            info["checkpw_error"] = f"{type(e).__name__}: {e}"
    return info
# #endregion


@app.post("/admin/scrape")
async def trigger_scrape():
    """Manually trigger a scrape cycle."""
    asyncio.create_task(scrape_and_process())
    return {"message": "Scrape cycle started"}


@app.post("/admin/digest")
async def trigger_digest():
    """Manually trigger all digests."""
    asyncio.create_task(_send_all_digests())
    return {"message": "Digest delivery started"}
