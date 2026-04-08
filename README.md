# NeoFeed

AI & Crypto News Aggregator with Trust Verification.

Scrapes news from RSS feeds, Reddit, Hacker News, and Twitter (via Nitter bridges), cross-verifies claims using a 3-tier pipeline (TF-IDF clustering → heuristics → Gemini LLM), and delivers curated feeds via a web dashboard, Discord, Telegram, and email digests.

## Quick Start

```bash
# Clone and install
cd NeoFeed
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your keys (see Setup below)

# Generate a PIN hash
python -c "import bcrypt; print(bcrypt.hashpw(b'your-pin-here', bcrypt.gensalt()).decode())"
# Add the output to PIN_HASH in .env

# Run the database schema
# Copy database/schema.sql → Supabase SQL Editor → Run

# Start
uvicorn main:app --reload --port 8000
```

## Setup

### Required Keys

| Key | Where to get it |
|---|---|
| `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` | Supabase Dashboard → Settings → API |
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com) → Get API Key |
| `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET` | [reddit.com/prefs/apps](https://reddit.com/prefs/apps) → Create script app |
| `DISCORD_BOT_TOKEN` | [Discord Developer Portal](https://discord.com/developers) → New App → Bot |
| `DISCORD_CHANNEL_ID` | Enable Developer Mode in Discord → Right-click channel → Copy ID |
| `TELEGRAM_BOT_TOKEN` | Message [@BotFather](https://t.me/BotFather) on Telegram → /newbot |
| `TELEGRAM_CHAT_ID` | Message [@userinfobot](https://t.me/userinfobot) on Telegram |
| `RESEND_API_KEY` | [resend.com](https://resend.com) → API Keys |

### API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Status |
| `GET` | `/health` | Health check |
| `GET` | `/admin/scrape-status` | Last scrape metadata (requires `X-Pin` when PIN is configured) |
| `POST` | `/auth/verify` | Verify PIN |
| `POST` | `/auth/setup` | Set/change PIN |
| `GET` | `/articles/` | List articles (filterable) |
| `GET` | `/articles/{id}` | Single article |
| `GET` | `/articles/cluster/{id}` | Articles in a cluster |
| `GET` | `/clusters/` | List clusters |
| `POST` | `/votes/` | Cast upvote/downvote |
| `GET` | `/votes/` | List votes |
| `GET` | `/preferences/` | Get preferences |
| `POST` | `/preferences/rebuild` | Rebuild preferences |
| `POST` | `/admin/scrape` | Trigger manual scrape |
| `POST` | `/admin/digest` | Trigger manual digest |

All `/articles/*`, `/clusters/*`, `/votes/*`, `/preferences/*`, and `/admin/*` routes require the `X-Pin` header when `PIN_HASH` is set. Public: `/`, `/health`, `/docs`, `/auth/verify`, `/auth/setup`.

## Architecture

```
Sources → Scrapers → Verification Pipeline → Supabase
                     (Tier 1: TF-IDF Clustering)
                     (Tier 2: Heuristics)
                     (Tier 3: Gemini — only when needed)
                              ↓
                         FastAPI REST API
                     ↓        ↓        ↓                             ↓
              Web (React/Vite)  Discord  Telegram   Email
```

## Deployment

Deploy backend on [Render](https://render.com) (free tier) using the included `render.yaml`. Frontend: React + Vite (e.g. [Vercel](https://vercel.com)); repo [NeoFeedFrontend](https://github.com/Mukulbanjade/NeoFeedFrontend).

### Keep News Fresh on Render Free Tier

Render free instances can sleep when idle. To avoid stale news:

1. Set external cron (e.g. cron-job.org, UptimeRobot, GitHub Actions schedule) every 10-15 minutes.
2. Hit `POST https://<your-backend>/admin/scrape` with `X-Pin` header.
3. Monitor `GET /health` (no PIN) for uptime, or `GET /admin/scrape-status` with `X-Pin` for scrape metadata.

Recommended env values:

- `SCRAPE_INTERVAL_MINUTES=15`
- `CORS_ORIGINS=*` (or explicit frontend URLs)
