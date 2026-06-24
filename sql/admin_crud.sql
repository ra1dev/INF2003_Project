-- PostgreSQL CRUD feature: notes attached to EPL matches.
-- The existing project table is named match_record (with an underscore).

CREATE TABLE IF NOT EXISTS match_note (
    note_id SERIAL PRIMARY KEY,
    match_id INTEGER NOT NULL,
    note_title VARCHAR(150) NOT NULL,
    note_content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_match_note_match
        FOREIGN KEY (match_id)
        REFERENCES match_record(match_id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_match_note_match_id
ON match_note(match_id);
