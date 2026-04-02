from __future__ import annotations

from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class Category(str, Enum):
    AI = "ai"
    CRYPTO = "crypto"
    BOTH = "both"


class TrustRating(str, Enum):
    VERIFIED = "verified"
    LIKELY_TRUE = "likely_true"
    UNVERIFIED = "unverified"
    LIKELY_FALSE = "likely_false"


class VoteType(str, Enum):
    UP = "up"
    DOWN = "down"


class Source(BaseModel):
    id: str | None = None
    name: str
    source_type: str  # rss, reddit, hn, twitter
    url: str
    reliability_score: float = 0.5
    category: Category = Category.AI


class RawArticle(BaseModel):
    """Intermediate representation before DB insert."""
    title: str
    url: str
    content: str = ""
    source_name: str
    source_type: str
    category: Category = Category.AI
    published_at: datetime | None = None
    author: str = ""
    engagement: int = 0


class Article(BaseModel):
    id: str | None = None
    title: str
    summary: str = ""
    url: str
    source_name: str
    source_type: str
    category: Category = Category.AI
    importance_score: float = 5.0
    trust_rating: TrustRating = TrustRating.UNVERIFIED
    cluster_id: str | None = None
    raw_content: str = ""
    author: str = ""
    engagement: int = 0
    published_at: datetime | None = None
    created_at: datetime | None = None


class ArticleCluster(BaseModel):
    id: str | None = None
    representative_title: str
    summary: str = ""
    category: Category = Category.AI
    importance_score: float = 5.0
    trust_rating: TrustRating = TrustRating.UNVERIFIED
    article_count: int = 1
    created_at: datetime | None = None


class Vote(BaseModel):
    id: str | None = None
    article_id: str | None = None
    cluster_id: str | None = None
    vote: VoteType
    created_at: datetime | None = None


class UserPreferences(BaseModel):
    id: str | None = None
    preference_vector: dict = Field(default_factory=dict)
    topic_weights: dict = Field(default_factory=dict)
    source_weights: dict = Field(default_factory=dict)
    updated_at: datetime | None = None
