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
    {"name": "Bitcoin Magazine", "url": "https://bitcoinmagazine.com/.rss/full/", "category": Category.CRYPTO, "reliability": 0.75},

    # ── Both (need_filter=True means articles are filtered by keyword relevance) ──
    {"name": "Wired", "url": "https://www.wired.com/feed/rss", "category": Category.BOTH, "reliability": 0.8, "needs_filter": True},
    {"name": "Reuters Tech", "url": "https://www.reutersagency.com/feed/?taxonomy=best-topics&post_type=best", "category": Category.BOTH, "reliability": 0.95, "needs_filter": True},
]

REDDIT_SUBS = [
    {"name": "r/artificial", "subreddit": "artificial", "category": Category.AI, "reliability": 0.5},
    {"name": "r/MachineLearning", "subreddit": "MachineLearning", "category": Category.AI, "reliability": 0.6},
    {"name": "r/LocalLLaMA", "subreddit": "LocalLLaMA", "category": Category.AI, "reliability": 0.55},
    {"name": "r/cryptocurrency", "subreddit": "CryptoCurrency", "category": Category.CRYPTO, "reliability": 0.4},
    {"name": "r/ethereum", "subreddit": "ethereum", "category": Category.CRYPTO, "reliability": 0.5},
    {"name": "r/bitcoin", "subreddit": "Bitcoin", "category": Category.CRYPTO, "reliability": 0.5},
    {"name": "r/solana", "subreddit": "solana", "category": Category.CRYPTO, "reliability": 0.45},
]

HN_CONFIG = {
    "name": "Hacker News",
    "reliability": 0.6,
    "max_stories": 30,
    "category": Category.AI,
}

# Nitter instances / RSSHub bridges for Twitter without API
TWITTER_RSS_BRIDGES = [
    {"name": "@sama (Sam Altman)", "url": "https://rsshub.app/twitter/user/sama", "category": Category.AI, "reliability": 0.7},
    {"name": "@AndrewYNg", "url": "https://rsshub.app/twitter/user/AndrewYNg", "category": Category.AI, "reliability": 0.8},
    {"name": "@ylecun (Yann LeCun)", "url": "https://rsshub.app/twitter/user/ylecun", "category": Category.AI, "reliability": 0.8},
    {"name": "@kaborosky (Andrej Karpathy)", "url": "https://rsshub.app/twitter/user/karpathy", "category": Category.AI, "reliability": 0.85},
    {"name": "@VitalikButerin", "url": "https://rsshub.app/twitter/user/VitalikButerin", "category": Category.CRYPTO, "reliability": 0.75},
    {"name": "@caborosky (CZ Binance)", "url": "https://rsshub.app/twitter/user/caborosky", "category": Category.CRYPTO, "reliability": 0.6},
    {"name": "@elaboratesk (Brian Armstrong)", "url": "https://rsshub.app/twitter/user/brian_armstrong", "category": Category.CRYPTO, "reliability": 0.7},
]
