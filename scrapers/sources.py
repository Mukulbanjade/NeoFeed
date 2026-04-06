"""Default news sources for NeoFeed."""

from database.models import Category

RSS_FEEDS = [
    # ── AI Sources ──
    {"name": "TechCrunch AI", "url": "https://techcrunch.com/category/artificial-intelligence/feed/", "category": Category.AI, "reliability": 0.8},
    {"name": "The Verge AI", "url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml", "category": Category.AI, "reliability": 0.8},
    {"name": "MIT Tech Review AI", "url": "https://www.technologyreview.com/topic/artificial-intelligence/feed", "category": Category.AI, "reliability": 0.9},
    {"name": "Ars Technica AI", "url": "https://feeds.arstechnica.com/arstechnica/technology-lab", "category": Category.AI, "reliability": 0.85},
    {"name": "VentureBeat AI", "url": "https://venturebeat.com/category/ai/feed/", "category": Category.AI, "reliability": 0.75},
    {"name": "OpenAI Blog", "url": "https://openai.com/blog/rss.xml", "category": Category.AI, "reliability": 0.95},
    {"name": "Google AI Blog", "url": "https://blog.google/technology/ai/rss/", "category": Category.AI, "reliability": 0.95},
    {"name": "Hugging Face Blog", "url": "https://huggingface.co/blog/feed.xml", "category": Category.AI, "reliability": 0.9},

    # ── Crypto Sources ──
    {"name": "CoinDesk", "url": "https://www.coindesk.com/arc/outboundfeeds/rss/", "category": Category.CRYPTO, "reliability": 0.8},
    {"name": "Decrypt", "url": "https://decrypt.co/feed", "category": Category.CRYPTO, "reliability": 0.75},
    {"name": "CoinTelegraph", "url": "https://cointelegraph.com/rss", "category": Category.CRYPTO, "reliability": 0.7},
    {"name": "The Block", "url": "https://www.theblock.co/rss.xml", "category": Category.CRYPTO, "reliability": 0.8},

    # ── Security / Infra / Geopolitics (broad, filtered) ──
    {"name": "BleepingComputer", "url": "https://www.bleepingcomputer.com/feed/", "category": Category.BOTH, "reliability": 0.85, "needs_filter": True},
    {"name": "The Hacker News", "url": "https://feeds.feedburner.com/TheHackersNews", "category": Category.BOTH, "reliability": 0.8, "needs_filter": True},
    {"name": "Krebs on Security", "url": "https://krebsonsecurity.com/feed/", "category": Category.BOTH, "reliability": 0.9, "needs_filter": True},
    {"name": "GitHub Blog", "url": "https://github.blog/feed/", "category": Category.BOTH, "reliability": 0.85, "needs_filter": True},
    {"name": "BBC World", "url": "http://feeds.bbci.co.uk/news/world/rss.xml", "category": Category.BOTH, "reliability": 0.9, "needs_filter": True},
    {"name": "Guardian World", "url": "https://www.theguardian.com/world/rss", "category": Category.BOTH, "reliability": 0.85, "needs_filter": True},
    {"name": "Al Jazeera", "url": "https://www.aljazeera.com/xml/rss/all.xml", "category": Category.BOTH, "reliability": 0.8, "needs_filter": True},
    {"name": "NYTimes World", "url": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml", "category": Category.BOTH, "reliability": 0.9, "needs_filter": True},

    # ── Both (need_filter=True means articles are filtered by keyword relevance) ──
    {"name": "Wired", "url": "https://www.wired.com/feed/rss", "category": Category.BOTH, "reliability": 0.8, "needs_filter": True},
    {"name": "The Register", "url": "https://www.theregister.com/headlines.atom", "category": Category.BOTH, "reliability": 0.8, "needs_filter": True},
]

REDDIT_SUBS = [
    {"name": "r/artificial", "subreddit": "artificial", "category": Category.AI, "reliability": 0.5},
    {"name": "r/MachineLearning", "subreddit": "MachineLearning", "category": Category.AI, "reliability": 0.6},
    {"name": "r/LocalLLaMA", "subreddit": "LocalLLaMA", "category": Category.AI, "reliability": 0.55},
    {"name": "r/cryptocurrency", "subreddit": "CryptoCurrency", "category": Category.CRYPTO, "reliability": 0.4},
    {"name": "r/ethereum", "subreddit": "ethereum", "category": Category.CRYPTO, "reliability": 0.5},
    {"name": "r/bitcoin", "subreddit": "Bitcoin", "category": Category.CRYPTO, "reliability": 0.5},
    {"name": "r/solana", "subreddit": "solana", "category": Category.CRYPTO, "reliability": 0.45},
    {"name": "r/netsec", "subreddit": "netsec", "category": Category.BOTH, "reliability": 0.65},
    {"name": "r/cybersecurity", "subreddit": "cybersecurity", "category": Category.BOTH, "reliability": 0.6},
    {"name": "r/worldnews", "subreddit": "worldnews", "category": Category.BOTH, "reliability": 0.55},
    {"name": "r/geopolitics", "subreddit": "geopolitics", "category": Category.BOTH, "reliability": 0.6},
]

HN_CONFIG = {
    "name": "Hacker News",
    "reliability": 0.6,
    "max_stories": 60,
    "category": Category.AI,
}

# Nitter instances / RSSHub bridges for Twitter without API
TWITTER_RSS_BRIDGES = [
    {"name": "@sama (Sam Altman)", "url": "https://nitter.net/sama/rss", "category": Category.AI, "reliability": 0.7},
    {"name": "@AndrewYNg", "url": "https://nitter.net/AndrewYNg/rss", "category": Category.AI, "reliability": 0.8},
    {"name": "@ylecun (Yann LeCun)", "url": "https://nitter.net/ylecun/rss", "category": Category.AI, "reliability": 0.8},
    {"name": "@karpathy (Andrej Karpathy)", "url": "https://nitter.net/karpathy/rss", "category": Category.AI, "reliability": 0.85},
    {"name": "@VitalikButerin", "url": "https://nitter.net/VitalikButerin/rss", "category": Category.CRYPTO, "reliability": 0.75},
    {"name": "@cz_binance", "url": "https://nitter.net/cz_binance/rss", "category": Category.CRYPTO, "reliability": 0.6},
    {"name": "@brian_armstrong", "url": "https://nitter.net/brian_armstrong/rss", "category": Category.CRYPTO, "reliability": 0.7},
]
