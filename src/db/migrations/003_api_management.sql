-- Migration 003: API Management — API Keys + Usage Tracking
-- 執行環境：Supabase SQL Editor
-- 執行時間：Phase 3 重構

-- ── API Keys ────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS api_keys (
    id SERIAL PRIMARY KEY,
    key_hash TEXT UNIQUE NOT NULL,       -- SHA-256 hash of the raw key
    name TEXT NOT NULL,                  -- Human-readable name (e.g., "My App")
    owner_email TEXT,                    -- Key owner's email
    plan TEXT NOT NULL DEFAULT 'free',   -- free / pro / enterprise
    rate_limit_per_min INT DEFAULT 60,   -- Per-minute request limit
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    last_used_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash ON api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_plan ON api_keys(plan);

-- ── API Usage ───────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS api_usage (
    id SERIAL PRIMARY KEY,
    api_key_id INT REFERENCES api_keys(id) ON DELETE SET NULL,
    endpoint TEXT NOT NULL,
    method TEXT NOT NULL,
    status_code INT,
    response_time_ms FLOAT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_api_usage_key_id ON api_usage(api_key_id);
CREATE INDEX IF NOT EXISTS idx_api_usage_created_at ON api_usage(created_at);
CREATE INDEX IF NOT EXISTS idx_api_usage_endpoint ON api_usage(endpoint);

-- ── 預設開發用 API Key ──────────────────────────────────────────
-- key: utc-dev-key → SHA-256 hash

INSERT INTO api_keys (key_hash, name, owner_email, plan, rate_limit_per_min)
VALUES (
    '8f14e45fceea167a5a36dedd4bea2543',  -- Placeholder hash
    'Development Key',
    'dev@utc.local',
    'pro',
    120
) ON CONFLICT (key_hash) DO NOTHING;

-- ── 自動清理舊使用記錄（可選，需 pg_cron 擴充）──────────────────
-- 保留最近 90 天的使用記錄
-- SELECT cron.schedule('cleanup-api-usage', '0 3 * * *',
--   $$DELETE FROM api_usage WHERE created_at < now() - interval '90 days'$$
-- );
