-- NeoFeed Supabase Schema
-- Run this in the Supabase SQL Editor to set up your database

-- Sources table
CREATE TABLE IF NOT EXISTS sources (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    source_type TEXT NOT NULL CHECK (source_type IN ('rss', 'reddit', 'hn', 'twitter')),
    url TEXT NOT NULL,
    reliability_score FLOAT DEFAULT 0.5,
    category TEXT DEFAULT 'ai' CHECK (category IN ('ai', 'crypto', 'both')),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Article clusters
CREATE TABLE IF NOT EXISTS clusters (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    representative_title TEXT NOT NULL,
    summary TEXT DEFAULT '',
    category TEXT DEFAULT 'ai' CHECK (category IN ('ai', 'crypto', 'both')),
    importance_score FLOAT DEFAULT 5.0,
    trust_rating TEXT DEFAULT 'unverified' CHECK (trust_rating IN ('verified', 'likely_true', 'unverified', 'likely_false')),
    article_count INT DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Articles table
CREATE TABLE IF NOT EXISTS articles (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    title TEXT NOT NULL,
    summary TEXT DEFAULT '',
    url TEXT NOT NULL UNIQUE,
    source_name TEXT NOT NULL,
    source_type TEXT NOT NULL,
    category TEXT DEFAULT 'ai' CHECK (category IN ('ai', 'crypto', 'both')),
    importance_score FLOAT DEFAULT 5.0,
    trust_rating TEXT DEFAULT 'unverified' CHECK (trust_rating IN ('verified', 'likely_true', 'unverified', 'likely_false')),
    cluster_id UUID REFERENCES clusters(id) ON DELETE SET NULL,
    raw_content TEXT DEFAULT '',
    author TEXT DEFAULT '',
    engagement INT DEFAULT 0,
    published_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Votes table
CREATE TABLE IF NOT EXISTS votes (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    article_id UUID REFERENCES articles(id) ON DELETE CASCADE,
    cluster_id UUID REFERENCES clusters(id) ON DELETE CASCADE,
    vote TEXT NOT NULL CHECK (vote IN ('up', 'down')),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- User preferences (single row for single user)
CREATE TABLE IF NOT EXISTS preferences (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    preference_vector JSONB DEFAULT '{}',
    topic_weights JSONB DEFAULT '{}',
    source_weights JSONB DEFAULT '{}',
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Digest log
CREATE TABLE IF NOT EXISTS digests (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    channel TEXT NOT NULL CHECK (channel IN ('email', 'discord', 'telegram')),
    article_ids UUID[] DEFAULT '{}',
    sent_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_articles_category ON articles(category);
CREATE INDEX IF NOT EXISTS idx_articles_trust ON articles(trust_rating);
CREATE INDEX IF NOT EXISTS idx_articles_cluster ON articles(cluster_id);
CREATE INDEX IF NOT EXISTS idx_articles_created ON articles(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_articles_importance ON articles(importance_score DESC);
CREATE INDEX IF NOT EXISTS idx_clusters_created ON clusters(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_votes_article ON votes(article_id);
CREATE INDEX IF NOT EXISTS idx_votes_cluster ON votes(cluster_id);

-- Insert initial preferences row
INSERT INTO preferences (preference_vector, topic_weights, source_weights)
VALUES ('{}', '{}', '{}')
ON CONFLICT DO NOTHING;

-- RLS policies (since this is single-user with PIN auth handled at API level, we keep it simple)
ALTER TABLE articles ENABLE ROW LEVEL SECURITY;
ALTER TABLE clusters ENABLE ROW LEVEL SECURITY;
ALTER TABLE votes ENABLE ROW LEVEL SECURITY;
ALTER TABLE preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE digests ENABLE ROW LEVEL SECURITY;

-- Allow service role full access (backend uses service role key)
CREATE POLICY "Service role full access" ON articles FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access" ON clusters FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access" ON votes FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access" ON preferences FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access" ON sources FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access" ON digests FOR ALL USING (true) WITH CHECK (true);
