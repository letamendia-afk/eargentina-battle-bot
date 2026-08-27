-- eRepublik Country Monitor
-- PostgreSQL schema. Kept provider-neutral so it can run on Supabase, OCI, or any PostgreSQL server.

CREATE TABLE IF NOT EXISTS monitored_countries (
    id BIGSERIAL PRIMARY KEY,
    erepublik_country_id INTEGER NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    telegram_command VARCHAR(50) NOT NULL UNIQUE,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS country_admins (
    id BIGSERIAL PRIMARY KEY,
    monitored_country_id BIGINT NOT NULL
        REFERENCES monitored_countries(id)
        ON DELETE CASCADE,
    telegram_user_id BIGINT NOT NULL,
    telegram_username VARCHAR(100),
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (monitored_country_id, telegram_user_id)
);

CREATE TABLE IF NOT EXISTS campaign_orders (
    id BIGSERIAL PRIMARY KEY,
    monitored_country_id BIGINT NOT NULL
        REFERENCES monitored_countries(id)
        ON DELETE CASCADE,
    opponent_country_id INTEGER NOT NULL,
    winner_side VARCHAR(10) NOT NULL
        CHECK (winner_side IN ('DEFENDER', 'ATTACKER')),
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_by_telegram_id BIGINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (monitored_country_id, opponent_country_id)
);

CREATE TABLE IF NOT EXISTS country_settings (
    id BIGSERIAL PRIMARY KEY,
    monitored_country_id BIGINT NOT NULL
        REFERENCES monitored_countries(id)
        ON DELETE CASCADE,
    setting_key VARCHAR(100) NOT NULL,
    setting_value TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (monitored_country_id, setting_key)
);

CREATE TABLE IF NOT EXISTS chat_country_preferences (
    chat_id BIGINT PRIMARY KEY,
    monitored_country_id BIGINT NOT NULL
        REFERENCES monitored_countries(id)
        ON DELETE CASCADE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS monitor_alert_state (
    monitored_country_id BIGINT NOT NULL
        REFERENCES monitored_countries(id)
        ON DELETE CASCADE,
    battle_id BIGINT NOT NULL,
    status_signature TEXT NOT NULL,
    had_problem BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (monitored_country_id, battle_id)
);

CREATE INDEX IF NOT EXISTS idx_country_admins_telegram
ON country_admins (telegram_user_id);

CREATE INDEX IF NOT EXISTS idx_campaign_orders_country
ON campaign_orders (monitored_country_id);

CREATE INDEX IF NOT EXISTS idx_campaign_orders_opponent
ON campaign_orders (opponent_country_id);

CREATE INDEX IF NOT EXISTS idx_chat_country_preferences_country
ON chat_country_preferences (monitored_country_id);

CREATE INDEX IF NOT EXISTS idx_monitor_alert_state_updated
ON monitor_alert_state (updated_at);

-- Example monitor (uncomment/adapt when provisioning a new country):
-- INSERT INTO monitored_countries (erepublik_country_id, name, telegram_command)
-- VALUES (27, 'Argentina', 'argentina')
-- ON CONFLICT (erepublik_country_id) DO NOTHING;
