CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    tg_id BIGINT UNIQUE NOT NULL,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS modes (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    shots INTEGER NOT NULL UNIQUE,
    win_value_min INTEGER NOT NULL DEFAULT 4,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sessions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    mode_id BIGINT NOT NULL REFERENCES modes(id),
    status TEXT NOT NULL DEFAULT 'pending',
    shots INTEGER NOT NULL,
    win_value_min INTEGER NOT NULL,
    hits INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS throws (
    id BIGSERIAL PRIMARY KEY,
    session_id BIGINT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    shot_index INTEGER NOT NULL,
    dice_value INTEGER NOT NULL,
    is_hit BOOLEAN NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_throws_session ON throws(session_id);

INSERT INTO modes (name, shots, win_value_min)
VALUES
    ('2 броска', 2, 4),
    ('3 броска', 3, 4),
    ('4 броска', 4, 4),
    ('6 бросков', 6, 4),
    ('7 бросков', 7, 4),
    ('8 бросков', 8, 4)
ON CONFLICT (shots) DO NOTHING;
