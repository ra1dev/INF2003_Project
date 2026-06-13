from psycopg2.extras import RealDictCursor


PLAYER_STAT_FIELDS = [
    "appearances",
    "clean_sheets",
    "goals_conceded",
    "tackles",
    "tackle_success_pct",
    "blocked_shots",
    "interceptions",
    "clearances",
    "recoveries",
    "duels_won",
    "duels_lost",
    "aerial_battles_won",
    "aerial_battles_lost",
    "assists",
    "passes",
    "big_chances_created",
    "crosses",
    "cross_accuracy_pct",
    "through_balls",
    "accurate_long_balls",
    "yellow_cards",
    "red_cards",
    "fouls",
    "offsides",
    "goals",
    "headed_goals",
    "hit_woodwork",
    "penalties_scored",
    "freekicks_scored",
    "shots",
    "shots_on_target",
    "shooting_accuracy_pct",
    "big_chances_missed",
    "saves",
    "penalties_saved",
    "punches",
    "high_claims",
    "catches",
    "sweeper_clearances",
]


def get_players(conn, search=None, team=None):
    query = """
        WITH player_clubs AS (
            SELECT
                p.player_id,
                p.player_name,
                t.team_id,
                t.team_name,
                COALESCE(
                    t.team_logo,
                    'https://ui-avatars.com/api/?name=' || REPLACE(COALESCE(t.team_name, 'Unknown Team'), ' ', '+') ||
                    '&background=1e293b&color=ffffff&size=128'
                ) AS team_logo,
                pts.season_id,
                ROW_NUMBER() OVER (
                    PARTITION BY p.player_id
                    ORDER BY pts.season_id DESC NULLS LAST
                ) AS club_rank
            FROM player p
            LEFT JOIN player_team_season pts
                ON p.player_id = pts.player_id
            LEFT JOIN team t
                ON pts.team_id = t.team_id
            WHERE 1=1
    """
    params = []

    if search:
        query += " AND p.player_name ILIKE %s"
        params.append(f"%{search}%")

    query += """
        ),
        matching_players AS (
            SELECT DISTINCT player_id
            FROM player_clubs
            WHERE 1=1
    """

    if team:
        query += " AND team_name = %s"
        params.append(team)

    query += """
        ),
        current_club AS (
            SELECT
                player_id,
                team_name AS current_team_name,
                team_logo AS current_team_logo
            FROM player_clubs
            WHERE club_rank = 1
        ),
        previous_clubs AS (
            SELECT
                pc.player_id,
                STRING_AGG(DISTINCT pc.team_name, ', ' ORDER BY pc.team_name) AS previous_team_names
            FROM player_clubs pc
            LEFT JOIN current_club cc
                ON pc.player_id = cc.player_id
            WHERE pc.club_rank > 1
              AND pc.team_name IS NOT NULL
              AND pc.team_name <> cc.current_team_name
            GROUP BY pc.player_id
        )
        SELECT
            pc.player_id,
            pc.player_name,
            COALESCE(cc.current_team_name, 'Unknown Team') AS current_team_name,
            COALESCE(
                cc.current_team_logo,
                'https://ui-avatars.com/api/?name=Unknown+Team&background=1e293b&color=ffffff&size=128'
            ) AS current_team_logo,
            COALESCE(prev.previous_team_names, '-') AS previous_team_names
        FROM (
            SELECT DISTINCT player_id, player_name
            FROM player_clubs
        ) pc
        INNER JOIN matching_players mp
            ON pc.player_id = mp.player_id
        LEFT JOIN current_club cc
            ON pc.player_id = cc.player_id
        LEFT JOIN previous_clubs prev
            ON pc.player_id = prev.player_id
        ORDER BY pc.player_name;
    """

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query, params)
        return cur.fetchall()


def get_team_options(conn):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT team_name
            FROM team
            ORDER BY team_name;
        """)
        return cur.fetchall()


def get_player_season_stats(conn, player_id):
    player_stat_columns = ",\n            ".join(
        f"pss.{field}" for field in PLAYER_STAT_FIELDS
    )
    query = """
        SELECT
            p.player_id,
            p.player_name,
            p.player_image,
            p.player_photo_url,
            s.season_name,
            t.team_name,
            COALESCE(
                t.team_logo,
                'https://ui-avatars.com/api/?name=' || REPLACE(COALESCE(t.team_name, 'Unknown Team'), ' ', '+') ||
                '&background=1e293b&color=ffffff&size=128'
            ) AS team_logo,
            pos.position_name,
            {player_stat_columns}
        FROM player p
        INNER JOIN player_season_stats pss
            ON p.player_id = pss.player_id
        INNER JOIN season s
            ON pss.season_id = s.season_id
        LEFT JOIN player_team_season pts
            ON p.player_id = pts.player_id
           AND pss.season_id = pts.season_id
        LEFT JOIN team t
            ON pts.team_id = t.team_id
        LEFT JOIN position pos
            ON pss.position_id = pos.position_id
        WHERE p.player_id = %s
        ORDER BY s.season_name;
    """.format(player_stat_columns=player_stat_columns)

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query, (player_id,))
        return cur.fetchall()
