-- PostgreSQL CRUD feature: favorite players and teams.
-- These tables store user-created records linked to existing EPL data.

CREATE TABLE IF NOT EXISTS favorite_player (
    favorite_id SERIAL PRIMARY KEY,
    player_id INTEGER NOT NULL,
    notes TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_favorite_player_player
        FOREIGN KEY (player_id)
        REFERENCES player(player_id)
        ON DELETE CASCADE,
    CONSTRAINT uq_favorite_player_player
        UNIQUE (player_id)
);

CREATE TABLE IF NOT EXISTS favorite_team (
    favorite_team_id SERIAL PRIMARY KEY,
    team_id INTEGER NOT NULL,
    notes TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_favorite_team_team
        FOREIGN KEY (team_id)
        REFERENCES team(team_id)
        ON DELETE CASCADE,
    CONSTRAINT uq_favorite_team_team
        UNIQUE (team_id)
);

CREATE INDEX IF NOT EXISTS idx_favorite_player_player_id
ON favorite_player(player_id);

CREATE INDEX IF NOT EXISTS idx_favorite_team_team_id
ON favorite_team(team_id);
