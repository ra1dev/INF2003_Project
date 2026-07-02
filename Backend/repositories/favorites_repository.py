# PostgreSQL helpers for reading and updating favorite players and teams.
from psycopg2.extras import RealDictCursor

from Backend.db_conn import get_db


FAVORITE_PLAYER_SELECT = """
    SELECT
        fp.favorite_id,
        fp.player_id,
        fp.notes,
        fp.created_at,
        fp.updated_at,
        p.player_name,
        COALESCE(current_team.team_name, 'Unknown Team') AS current_team_name,
        COALESCE(
            current_team.team_logo,
            'https://ui-avatars.com/api/?name=Unknown+Team&background=1e293b&color=ffffff&size=128'
        ) AS current_team_logo
    FROM favorite_player fp
    INNER JOIN player p ON p.player_id = fp.player_id
    LEFT JOIN LATERAL (
        SELECT
            t.team_name,
            t.team_logo
        FROM player_team_season pts
        INNER JOIN team t ON t.team_id = pts.team_id
        WHERE pts.player_id = p.player_id
        ORDER BY pts.season_id DESC NULLS LAST
        LIMIT 1
    ) current_team ON TRUE
"""


FAVORITE_TEAM_SELECT = """
    SELECT
        ft.favorite_team_id,
        ft.team_id,
        ft.notes,
        ft.created_at,
        ft.updated_at,
        t.team_name,
        COALESCE(
            t.team_logo,
            'https://ui-avatars.com/api/?name=' || REPLACE(t.team_name, ' ', '+') ||
            '&background=1e293b&color=ffffff&size=128'
        ) AS team_logo
    FROM favorite_team ft
    INNER JOIN team t ON t.team_id = ft.team_id
"""


def list_favorite_players():
    conn = get_db()
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(FAVORITE_PLAYER_SELECT + " ORDER BY fp.updated_at DESC, fp.favorite_id DESC")
        return cur.fetchall()


def list_favorite_teams():
    conn = get_db()
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(FAVORITE_TEAM_SELECT + " ORDER BY ft.updated_at DESC, ft.favorite_team_id DESC")
        return cur.fetchall()


def get_favorite_player(favorite_id):
    conn = get_db()
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(FAVORITE_PLAYER_SELECT + " WHERE fp.favorite_id = %s", (favorite_id,))
        return cur.fetchone()


def get_favorite_team(favorite_team_id):
    conn = get_db()
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(FAVORITE_TEAM_SELECT + " WHERE ft.favorite_team_id = %s", (favorite_team_id,))
        return cur.fetchone()


def list_player_options():
    conn = get_db()
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT player_id, player_name
            FROM player
            ORDER BY player_name
            """
        )
        return cur.fetchall()


def list_team_options():
    conn = get_db()
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT team_id, team_name
            FROM team
            ORDER BY team_name
            """
        )
        return cur.fetchall()


def player_exists(player_id):
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM player WHERE player_id = %s", (player_id,))
        return cur.fetchone() is not None


def team_exists(team_id):
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM team WHERE team_id = %s", (team_id,))
        return cur.fetchone() is not None


def create_favorite_player(player_id, notes=""):
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO favorite_player (player_id, notes)
            VALUES (%s, %s)
            ON CONFLICT (player_id) DO NOTHING
            RETURNING favorite_id
            """,
            (player_id, notes),
        )
        row = cur.fetchone()
    conn.commit()
    return row[0] if row else None


def create_favorite_team(team_id, notes=""):
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO favorite_team (team_id, notes)
            VALUES (%s, %s)
            ON CONFLICT (team_id) DO NOTHING
            RETURNING favorite_team_id
            """,
            (team_id, notes),
        )
        row = cur.fetchone()
    conn.commit()
    return row[0] if row else None


def update_favorite_player(favorite_id, notes):
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE favorite_player
            SET notes = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE favorite_id = %s
            """,
            (notes, favorite_id),
        )
        updated = cur.rowcount > 0
    conn.commit()
    return updated


def update_favorite_team(favorite_team_id, notes):
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE favorite_team
            SET notes = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE favorite_team_id = %s
            """,
            (notes, favorite_team_id),
        )
        updated = cur.rowcount > 0
    conn.commit()
    return updated


def delete_favorite_player(favorite_id):
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM favorite_player WHERE favorite_id = %s", (favorite_id,))
        deleted = cur.rowcount > 0
    conn.commit()
    return deleted


def delete_favorite_team(favorite_team_id):
    conn = get_db()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM favorite_team WHERE favorite_team_id = %s", (favorite_team_id,))
        deleted = cur.rowcount > 0
    conn.commit()
    return deleted
